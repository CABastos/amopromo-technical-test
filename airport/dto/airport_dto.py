from dataclasses import dataclass

from airport.helpers import parse_iata

_LAT_RANGE = (-90.0, 90.0)
_LON_RANGE = (-180.0, 180.0)


@dataclass(frozen=True, slots=True)
class AirportDTO:
    """Validated, immutable airport value object."""

    iata: str
    city: str
    state: str
    lat: float
    lon: float

    @classmethod
    def from_raw(cls, code: str, raw: object) -> "AirportDTO":
        """Validate and normalize a single raw record into an AirportDTO."""
        iata = parse_iata(code)

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

        return cls(iata=iata, city=city, state=state, lat=lat, lon=lon)
