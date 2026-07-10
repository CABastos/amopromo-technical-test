from dataclasses import dataclass
from decimal import Decimal

from flight.helpers import to_money

from .flight_option_dto import FlightOptionDTO


@dataclass(frozen=True, slots=True)
class RoundTripOptionDTO:
    """One round-trip itinerary: an outbound leg paired with a return leg."""

    outbound: FlightOptionDTO
    inbound: FlightOptionDTO
    fare: Decimal
    fee: Decimal
    total: Decimal

    @classmethod
    def combine(cls, outbound: FlightOptionDTO, inbound: FlightOptionDTO) -> "RoundTripOptionDTO":
        """Pair two legs, summing their price fields into the round-trip price."""
        return cls(
            outbound=outbound,
            inbound=inbound,
            fare=to_money(outbound.fare + inbound.fare),
            fee=to_money(outbound.fee + inbound.fee),
            total=to_money(outbound.total + inbound.total),
        )
