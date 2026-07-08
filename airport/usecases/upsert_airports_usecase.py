import logging
import re
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

from django.db import transaction

from airport.dto import AirportDTO
from airport.repositories import AirportRepository
from airport.services import DomesticApiService

logger = logging.getLogger(__name__)

_IATA_RE = re.compile(r"^[A-Z]{3}$")
_LAT_RANGE = (-90.0, 90.0)
_LON_RANGE = (-180.0, 180.0)


class NoValidAirportsError(Exception):
    """Raised when a fetched payload yields zero valid airports.

    Aborting here prevents an empty or structurally changed payload from
    soft-deleting every airport in the database.
    """


@dataclass(frozen=True, slots=True)
class ImportSummary:
    """Counts describing the outcome of a single import run."""

    created: int
    updated: int
    deactivated: int
    skipped: int


class UpsertAirportsUseCase:
    """Orchestrates a full airport import.

    Collaborators are injected so the use case can be unit-tested with fakes and
    without a database: ``service`` fetches the payload, ``repository`` persists,
    and ``atomic`` provides the transaction boundary (defaults to
    ``transaction.atomic``; tests pass ``contextlib.nullcontext``). The use case
    itself deals only in DTOs and never touches the ORM directly.
    """

    def __init__(
        self,
        service: DomesticApiService | None = None,
        repository: AirportRepository | None = None,
        atomic: Callable[[], AbstractContextManager] | None = None,
    ) -> None:
        self._service = service if service is not None else DomesticApiService()
        self._repository = repository if repository is not None else AirportRepository()
        self._atomic = atomic if atomic is not None else transaction.atomic

    def execute(self) -> ImportSummary:
        """Fetch, validate, and persist airports; return a summary of counts.

        Raises:
            DomesticApiError: if the fetch fails (the database is left untouched).
            NoValidAirportsError: if no record survives validation.
        """
        payload = self._service.fetch_airports()

        dtos: list[AirportDTO] = []
        skipped = 0
        for code, raw in payload.items():
            try:
                dtos.append(self._to_dto(code, raw))
            except ValueError as exc:
                skipped += 1
                logger.warning("Skipping airport %s: %s", code, exc)

        if not dtos:
            raise NoValidAirportsError(
                "No valid airports in payload; aborting to avoid mass-deactivation"
            )

        active_iatas = [dto.iata for dto in dtos]
        with self._atomic():
            result = self._repository.upsert_many(dtos)
            deactivated = self._repository.deactivate_missing(active_iatas)

        summary = ImportSummary(
            created=result.created,
            updated=result.updated,
            deactivated=deactivated,
            skipped=skipped,
        )
        logger.info(
            "Import complete: %d created, %d updated, %d deactivated, %d skipped",
            summary.created,
            summary.updated,
            summary.deactivated,
            summary.skipped,
        )
        return summary

    @staticmethod
    def _to_dto(code: str, raw: object) -> AirportDTO:
        """Validate a single raw record and build an AirportDTO.

        The dict key is the authoritative IATA code. Raises ``ValueError`` with a
        human-readable reason for any invalid or missing field.
        """
        iata = str(code).strip().upper()
        if not _IATA_RE.match(iata):
            raise ValueError(f"invalid IATA code {code!r}")

        if not isinstance(raw, dict):
            raise ValueError("record is not an object")

        try:
            city = str(raw["city"]).strip()
            state = str(raw["state"]).strip().upper()
            lat = float(raw["lat"])
            lon = float(raw["lon"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"missing or invalid field: {exc}") from exc

        if not city:
            raise ValueError("empty city")
        if len(state) != 2:
            raise ValueError(f"invalid state {state!r}")
        if not (_LAT_RANGE[0] <= lat <= _LAT_RANGE[1]):
            raise ValueError(f"lat out of range: {lat}")
        if not (_LON_RANGE[0] <= lon <= _LON_RANGE[1]):
            raise ValueError(f"lon out of range: {lon}")

        return AirportDTO(iata=iata, city=city, state=state, lat=lat, lon=lon)
