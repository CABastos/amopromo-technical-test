import logging
from dataclasses import dataclass
from datetime import date

from airport.dto import AirportDTO
from airport.repositories import AirportRepository
from flight.dto import FlightOptionDTO, FlightSearchQuery, RoundTripOptionDTO
from flight.helpers import haversine_km
from flight.services import MockAirlinesApiService

logger = logging.getLogger(__name__)


class UnknownAirportError(Exception):
    """Raised when the origin or destination is not a known active airport."""


@dataclass(frozen=True, slots=True)
class FlightSearchResult:
    """Outcome of a round-trip search."""

    origin: AirportDTO
    destination: AirportDTO
    departure_date: date
    return_date: date
    currency: str
    range_km: float
    options: tuple[RoundTripOptionDTO, ...]


class SearchRoundTripUseCase:
    """Orchestrates a round-trip flight search."""

    _DEFAULT_CURRENCY = "BRL"

    def __init__(
        self,
        service: MockAirlinesApiService | None = None,
        repository: AirportRepository | None = None,
    ) -> None:
        self._service = service if service is not None else MockAirlinesApiService()
        self._repository = repository if repository is not None else AirportRepository()

    def execute(self, query: FlightSearchQuery) -> FlightSearchResult:
        """Search both legs, enrich and combine them, and return sorted results."""
        airports = self._repository.get_active_by_iatas([query.origin, query.destination])
        missing = [code for code in (query.origin, query.destination) if code not in airports]
        if missing:
            raise UnknownAirportError(f"unknown or inactive airport(s): {', '.join(missing)}")

        origin = airports[query.origin]
        destination = airports[query.destination]
        distance_km = round(
            haversine_km(origin.lat, origin.lon, destination.lat, destination.lon), 2
        )

        outbound_payload = self._service.search_flights(
            query.origin, query.destination, query.departure_date
        )
        inbound_payload = self._service.search_flights(
            query.destination, query.origin, query.return_date
        )

        outbound_options = self._parse_options(outbound_payload, distance_km, "outbound")
        inbound_options = self._parse_options(inbound_payload, distance_km, "inbound")

        options = tuple(
            sorted(
                (
                    RoundTripOptionDTO.combine(outbound, inbound)
                    for outbound in outbound_options
                    for inbound in inbound_options
                ),
                key=lambda option: option.total,
            )
        )

        logger.info(
            "Round-trip %s<->%s: %d outbound x %d inbound -> %d combinations",
            query.origin,
            query.destination,
            len(outbound_options),
            len(inbound_options),
            len(options),
        )
        return FlightSearchResult(
            origin=origin,
            destination=destination,
            departure_date=query.departure_date,
            return_date=query.return_date,
            currency=self._currency(outbound_payload),
            range_km=distance_km,
            options=options,
        )

    def _parse_options(
        self, payload: dict, distance_km: float, label: str
    ) -> list[FlightOptionDTO]:
        """Enrich a payload's options, skipping (and logging) invalid ones."""
        parsed: list[FlightOptionDTO] = []
        for index, raw in enumerate(payload.get("options", [])):
            try:
                parsed.append(FlightOptionDTO.from_raw(raw, distance_km=distance_km))
            except ValueError as exc:
                logger.warning("Skipping %s option %d: %s", label, index, exc)
        return parsed

    def _currency(self, payload: dict) -> str:
        """Read the currency from a payload's summary, defaulting to BRL."""
        summary = payload.get("summary")
        if isinstance(summary, dict):
            currency = summary.get("currency")
            if isinstance(currency, str) and currency.strip():
                return currency.strip()
        return self._DEFAULT_CURRENCY
