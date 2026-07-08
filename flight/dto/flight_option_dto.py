from dataclasses import dataclass
from datetime import datetime

# The provider populates only ``fare``; the fee (and everything derived from it)
# is ours to compute. A booking fee is 10% of the fare with a R$40 floor.
_FEE_RATE = 0.10
_MIN_FEE = 40.0


@dataclass(frozen=True, slots=True)
class FlightOptionDTO:
    """A single, fully-enriched flight leg.

    The provider returns each option with a fare but zeroed fee/total and an
    empty meta block. :meth:`from_raw` validates the raw option and fills in the
    price and meta fields, so every value object leaving this layer is complete
    and internally consistent. Distance is supplied by the caller (computed once
    per route) rather than re-derived per option.
    """

    departure_time: datetime
    arrival_time: datetime
    fare: float
    fee: float
    total: float
    aircraft_model: str
    aircraft_manufacturer: str
    range_km: float
    cruise_speed_kmh: float
    cost_per_km: float

    @classmethod
    def from_raw(cls, raw: object, *, distance_km: float) -> "FlightOptionDTO":
        """Validate a raw provider option and compute its price and meta blocks.

        ``distance_km`` is the route's great-circle distance, injected so it is
        computed once per route instead of once per option. All monetary and
        meta values are rounded to two decimals.

        Raises:
            ValueError: if the option is not an object, the timestamps are
                unparseable or non-increasing, the fare is not positive, or
                ``distance_km`` is not positive (these guard against zero/
                negative durations and division by zero). The caller skips and
                logs invalid options rather than failing the whole search.
        """
        if not isinstance(raw, dict):
            raise ValueError("option is not an object")
        if distance_km <= 0:
            raise ValueError(f"distance_km must be positive, got {distance_km}")

        departure = cls._parse_datetime(raw.get("departure_time"), "departure_time")
        arrival = cls._parse_datetime(raw.get("arrival_time"), "arrival_time")
        if arrival <= departure:
            raise ValueError("arrival_time must be after departure_time")

        try:
            fare = float(raw["price"]["fare"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"missing or invalid fare: {exc}") from exc
        if fare <= 0:
            raise ValueError(f"fare must be positive, got {fare}")

        aircraft = raw.get("aircraft")
        if not isinstance(aircraft, dict):
            aircraft = {}
        model = str(aircraft.get("model", "")).strip()
        manufacturer = str(aircraft.get("manufacturer", "")).strip()

        duration_hours = (arrival - departure).total_seconds() / 3600
        fee = max(fare * _FEE_RATE, _MIN_FEE)

        return cls(
            departure_time=departure,
            arrival_time=arrival,
            fare=round(fare, 2),
            fee=round(fee, 2),
            total=round(fare + fee, 2),
            aircraft_model=model,
            aircraft_manufacturer=manufacturer,
            range_km=round(distance_km, 2),
            cruise_speed_kmh=round(distance_km / duration_hours, 2),
            cost_per_km=round(fare / distance_km, 2),
        )

    @staticmethod
    def _parse_datetime(value: object, field: str) -> datetime:
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"invalid {field} {value!r}: {exc}") from exc
