import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

from django.db import transaction

from airport.dto import AirportDTO
from airport.repositories import AirportRepository
from airport.services import DomesticApiService

logger = logging.getLogger(__name__)


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

        # Key by the normalized IATA so case-variant keys (e.g. "gru" and "GRU")
        # collapse to one record. Feeding duplicate conflict keys to a single
        # INSERT ... ON CONFLICT would otherwise abort the whole import.
        by_iata: dict[str, AirportDTO] = {}
        skipped = 0
        for code, raw in payload.items():
            try:
                dto = AirportDTO.from_raw(code, raw)
            except ValueError as exc:
                skipped += 1
                logger.warning("Skipping airport %s: %s", code, exc)
                continue
            if dto.iata in by_iata:
                logger.warning(
                    "Duplicate IATA %s (from key %r); keeping the later record", dto.iata, code
                )
            by_iata[dto.iata] = dto

        dtos = list(by_iata.values())
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
