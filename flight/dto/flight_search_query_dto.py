from dataclasses import dataclass
from datetime import date

from airport.helpers import parse_iata
from flight.helpers import parse_date


@dataclass(frozen=True, slots=True)
class FlightSearchQuery:
    """Validated, immutable round-trip search request.

    Built from raw request parameters via :meth:`from_raw`, which is the single
    source of the search's domain rules (valid IATA codes, distinct endpoints,
    non-past departure, return on or after departure). The DRF serializer owns
    request *shape*; this DTO owns request *meaning*, so both the HTTP layer and
    any other caller validate identically.
    """

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
        """Validate and normalize raw parameters into a FlightSearchQuery.

        IATA codes are upper-cased and stripped; dates accept either ``date``
        objects or ISO ``YYYY-MM-DD`` strings. ``today`` is injectable so the
        "no past departures" rule is deterministic in tests; it defaults to the
        current date.

        Raises:
            ValueError: with a human-readable reason for any invalid field, so
                the caller can surface a 400 with a clear message.
        """
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
