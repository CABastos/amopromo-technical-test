from datetime import datetime

import pytest

from flight.dto import FlightOptionDTO


def _raw(
    departure_time="2026-07-10T08:00:00",
    arrival_time="2026-07-10T10:00:00",
    fare=500.0,
    model="A320",
    manufacturer="Airbus",
):
    """A well-formed raw provider option (fees/total/meta zeroed, as upstream)."""
    return {
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "price": {"fare": fare, "fees": 0, "total": 0},
        "aircraft": {"model": model, "manufacturer": manufacturer},
        "meta": {"range": 0, "cruise_speed_kmh": 0, "cost_per_km": 0},
    }


def test_from_raw_computes_price_and_meta():
    # 300 km flown in 2 h at a 500 fare.
    dto = FlightOptionDTO.from_raw(_raw(fare=500.0), distance_km=300.0)

    assert dto.departure_time == datetime(2026, 7, 10, 8, 0, 0)
    assert dto.arrival_time == datetime(2026, 7, 10, 10, 0, 0)
    assert dto.fare == 500.0
    assert dto.fee == 50.0  # 10% of 500 exceeds the 40 floor
    assert dto.total == 550.0
    assert dto.range_km == 300.0
    assert dto.cruise_speed_kmh == 150.0  # 300 km / 2 h
    assert dto.cost_per_km == 1.67  # 500 / 300, rounded
    assert dto.aircraft_model == "A320"
    assert dto.aircraft_manufacturer == "Airbus"


def test_fee_uses_forty_floor_when_ten_percent_is_smaller():
    # 10% of 218.66 = 21.866 < 40, so the floor applies.
    dto = FlightOptionDTO.from_raw(_raw(fare=218.66), distance_km=300.0)

    assert dto.fee == 40.0
    assert dto.total == round(218.66 + 40.0, 2)


def test_fee_at_boundary_equals_ten_percent():
    # 10% of 400 == 40 exactly; the max picks 40 on either interpretation.
    dto = FlightOptionDTO.from_raw(_raw(fare=400.0), distance_km=300.0)

    assert dto.fee == 40.0
    assert dto.total == 440.0


@pytest.mark.parametrize(
    ("raw", "distance_km"),
    [
        pytest.param("not-a-dict", 300.0, id="raw-not-object"),
        pytest.param(_raw(departure_time="nope"), 300.0, id="unparseable-departure"),
        pytest.param(_raw(arrival_time="nope"), 300.0, id="unparseable-arrival"),
        pytest.param(
            _raw(departure_time="2026-07-10T10:00:00", arrival_time="2026-07-10T08:00:00"),
            300.0,
            id="arrival-before-departure",
        ),
        pytest.param(
            _raw(departure_time="2026-07-10T08:00:00", arrival_time="2026-07-10T08:00:00"),
            300.0,
            id="arrival-equals-departure",
        ),
        pytest.param(
            {"departure_time": "2026-07-10T08:00:00", "arrival_time": "2026-07-10T10:00:00"},
            300.0,
            id="missing-price",
        ),
        pytest.param(_raw(fare=0.0), 300.0, id="fare-zero"),
        pytest.param(_raw(fare=-10.0), 300.0, id="fare-negative"),
        pytest.param(_raw(fare="abc"), 300.0, id="fare-non-numeric"),
        pytest.param(_raw(), 0.0, id="distance-zero"),
        pytest.param(_raw(), -5.0, id="distance-negative"),
    ],
)
def test_from_raw_rejects_invalid_input(raw, distance_km):
    with pytest.raises(ValueError):
        FlightOptionDTO.from_raw(raw, distance_km=distance_km)
