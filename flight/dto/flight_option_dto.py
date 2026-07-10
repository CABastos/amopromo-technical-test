from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from flight.helpers import parse_datetime, to_money

_FEE_RATE = Decimal("0.10")
_MIN_FEE = Decimal("40.00")


@dataclass(frozen=True, slots=True)
class FlightOptionDTO:
    """A single, fully-enriched flight leg."""

    departure_time: datetime
    arrival_time: datetime
    fare: Decimal
    fee: Decimal
    total: Decimal
    aircraft_model: str
    aircraft_manufacturer: str
    range_km: float
    cruise_speed_kmh: float
    cost_per_km: float

    @classmethod
    def from_raw(cls, raw: object, *, distance_km: float) -> "FlightOptionDTO":
        """Validate a raw provider option and compute its price and meta blocks."""
        if not isinstance(raw, dict):
            raise ValueError("option is not an object")
        if distance_km <= 0:
            raise ValueError(f"distance_km must be positive, got {distance_km}")

        departure = parse_datetime(raw.get("departure_time"), "departure_time")
        arrival = parse_datetime(raw.get("arrival_time"), "arrival_time")
        if arrival <= departure:
            raise ValueError("arrival_time must be after departure_time")

        try:
            fare = to_money(raw["price"]["fare"])
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
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
            fare=fare,
            fee=to_money(fee),
            total=to_money(fare + fee),
            aircraft_model=model,
            aircraft_manufacturer=manufacturer,
            range_km=round(distance_km, 2),
            cruise_speed_kmh=round(distance_km / duration_hours, 2),
            cost_per_km=round(float(fare) / distance_km, 2),
        )
