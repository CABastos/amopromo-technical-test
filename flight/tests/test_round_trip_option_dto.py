from decimal import Decimal

from flight.dto import FlightOptionDTO, RoundTripOptionDTO


def _leg(fare, distance_km=300.0):
    raw = {
        "departure_time": "2026-07-10T08:00:00",
        "arrival_time": "2026-07-10T10:00:00",
        "price": {"fare": fare, "fees": 0, "total": 0},
        "aircraft": {"model": "A320", "manufacturer": "Airbus"},
    }
    return FlightOptionDTO.from_raw(raw, distance_km=distance_km)


def test_combine_sums_leg_price_fields():
    outbound = _leg(500.0)  # fee 50 (10% > floor), total 550
    inbound = _leg(300.0)  # fee 40 (10% of 300 = 30 < floor), total 340

    rt = RoundTripOptionDTO.combine(outbound, inbound)

    assert rt.outbound is outbound
    assert rt.inbound is inbound
    assert rt.fare == 800.0
    assert rt.fee == 90.0
    assert rt.total == 890.0
    assert rt.total == round(outbound.total + inbound.total, 2)


def test_combine_keeps_both_leg_floors_without_repricing():
    # Both legs sit on the 40 floor; the combined fee must be 80, not a
    # re-priced max(300 * 0.10, 40) = 40.
    outbound = _leg(100.0)  # 10% = 10 < 40 -> fee 40
    inbound = _leg(200.0)  # 10% = 20 < 40 -> fee 40

    rt = RoundTripOptionDTO.combine(outbound, inbound)

    assert outbound.fee == 40.0
    assert inbound.fee == 40.0
    assert rt.fee == 80.0
    assert rt.fare == 300.0
    assert rt.total == 380.0


def test_combine_rounds_to_two_decimals():
    # 100.10 + 200.20 is 300.29999999999995 in float; combine must round it.
    outbound = _leg(100.10)  # fee 40, total 140.10
    inbound = _leg(200.20)  # fee 40, total 240.20

    rt = RoundTripOptionDTO.combine(outbound, inbound)

    assert rt.fare == Decimal("300.30")
    assert rt.fee == 80.0
    assert rt.total == Decimal("380.30")
