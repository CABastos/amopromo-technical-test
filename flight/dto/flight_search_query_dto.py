from dataclasses import dataclass
from datetime import date

from airport.helpers import parse_iata
from flight.helpers import parse_date


@dataclass(frozen=True, slots=True)
class FlightSearchQuery:
    """Validated, immutable round-trip search request."""

    origin: str
    destination: str
    departure_date: date
    return_date: date

    @classmethod
    def from_raw(
        cls,
        origin: object,
        destination: object,
        departure_date: object,
        return_date: object,
        *,
        today: date | None = None,
    ) -> "FlightSearchQuery":
        """Validate and normalize raw parameters into a FlightSearchQuery."""
        today = today if today is not None else date.today()

        origin_code = parse_iata(origin, "origin IATA code")
        destination_code = parse_iata(destination, "destination IATA code")
        if origin_code == destination_code:
            raise ValueError("origin and destination must be different airports")

        departure = parse_date(departure_date, "departure_date")
        returning = parse_date(return_date, "return_date")
        if departure < today:
            raise ValueError(f"departure_date {departure.isoformat()} is in the past")
        if returning < departure:
            raise ValueError("return_date must be on or after departure_date")

        return cls(
            origin=origin_code,
            destination=destination_code,
            departure_date=departure,
            return_date=returning,
        )
