from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AirportDTO:
    """Validated, immutable airport record exchanged between layers.

    Produced by the use case after validating the raw API payload and consumed
    by the repository for persistence. Being frozen keeps it a safe value
    object; the repository maps it onto the Airport ORM model.
    """

    iata: str
    city: str
    state: str
    lat: float
    lon: float
