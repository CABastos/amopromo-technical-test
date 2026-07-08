from dataclasses import dataclass

from .flight_option_dto import FlightOptionDTO


@dataclass(frozen=True, slots=True)
class RoundTripOptionDTO:
    """One round-trip itinerary: an outbound leg paired with a return leg.

    The combined price is the plain sum of the two legs' price blocks. We do
    *not* re-run the ``max(fare * 0.10, 40)`` fee rule on the combined fare:
    each leg has already priced its own fee (including the R$40 floor), and
    re-pricing the pair would silently discount a leg whose fee sat on that
    floor. This is a documented ambiguity in the challenge (see README).
    """

    outbound: FlightOptionDTO
    inbound: FlightOptionDTO
    fare: float
    fee: float
    total: float

    @classmethod
    def combine(cls, outbound: FlightOptionDTO, inbound: FlightOptionDTO) -> "RoundTripOptionDTO":
        """Pair two legs, summing their price fields into the round-trip price.

        By construction ``total == outbound.total + inbound.total`` (subject to
        two-decimal rounding), so the aggregate stays consistent with its legs.
        """
        return cls(
            outbound=outbound,
            inbound=inbound,
            fare=round(outbound.fare + inbound.fare, 2),
            fee=round(outbound.fee + inbound.fee, 2),
            total=round(outbound.total + inbound.total, 2),
        )
