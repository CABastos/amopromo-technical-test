import logging
from dataclasses import dataclass

from airport.dto import AirportDTO
from airport.models import Airport

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpsertResult:
    """Outcome of an upsert: how many rows were inserted vs. updated."""

    created: int
    updated: int


class AirportRepository:
    """Persistence for Airport rows."""

    _UPDATE_FIELDS = ["city", "state", "lat", "lon", "is_active", "updated_at"]

    def upsert_many(self, dtos: list[AirportDTO]) -> UpsertResult:
        """Insert new airports and update existing ones in a single upsert."""
        if not dtos:
            return UpsertResult(created=0, updated=0)

        incoming_iatas = [dto.iata for dto in dtos]
        existing_iatas = set(
            Airport.objects.filter(iata__in=incoming_iatas).values_list("iata", flat=True)
        )
        created = sum(1 for iata in incoming_iatas if iata not in existing_iatas)
        updated = len(incoming_iatas) - created

        airports = [
            Airport(
                iata=dto.iata,
                city=dto.city,
                state=dto.state,
                lat=dto.lat,
                lon=dto.lon,
                is_active=True,
            )
            for dto in dtos
        ]
        Airport.objects.bulk_create(
            airports,
            update_conflicts=True,
            unique_fields=["iata"],
            update_fields=self._UPDATE_FIELDS,
        )

        logger.info("Upserted airports: %d created, %d updated", created, updated)
        return UpsertResult(created=created, updated=updated)

    def get_active_by_iatas(self, iatas: list[str]) -> dict[str, AirportDTO]:
        """Return active airports for the given IATA codes, keyed by code."""
        rows = Airport.objects.filter(iata__in=iatas, is_active=True)
        return {
            row.iata: AirportDTO(
                iata=row.iata,
                city=row.city,
                state=row.state,
                lat=row.lat,
                lon=row.lon,
            )
            for row in rows
        }

    def deactivate_missing(self, active_iatas: list[str]) -> int:
        """Soft-delete airports absent from the payload."""
        deactivated = (
            Airport.objects.filter(is_active=True)
            .exclude(iata__in=active_iatas)
            .update(is_active=False)
        )
        logger.info("Deactivated %d airports missing from payload", deactivated)
        return deactivated
