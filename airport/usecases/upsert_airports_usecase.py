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
    """Raised when a fetched payload yields zero valid airports."""


@dataclass(frozen=True, slots=True)
class ImportSummary:
    """Counts describing the outcome of a single import run."""

    created: int
    updated: int
    deactivated: int
    skipped: int


class UpsertAirportsUseCase:
    """Orchestrates a full airport import."""

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
        """Fetch, validate, and persist airports; return a summary of counts."""
        payload = self._service.fetch_airports()

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
