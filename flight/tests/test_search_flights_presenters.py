from datetime import date, datetime

from airport.dto import AirportDTO
from flight.api.search_flights_view import (
    _serialize_airport,
    _serialize_flight,
    _serialize_price,
    _serialize_result,
    _serialize_round_trip,
)
from flight.dto import FlightOptionDTO, RoundTripOptionDTO
from flight.usecases import FlightSearchResult

GRU = AirportDTO(iata="GRU", city="Sao Paulo", state="SP", lat=-23.435, lon=-46.473)
GIG = AirportDTO(iata="GIG", city="Rio de Janeiro", state="RJ", lat=-22.810, lon=-43.251)


def _option(
    *,
    fare=100.0,
    fee=40.0,
    total=140.0,
    departure=datetime(2026, 7, 10, 8, 0),
    arrival=datetime(2026, 7, 10, 10, 0),
    model="A320",
    manufacturer="Airbus",
    range_km=338.0,
    cruise_speed_kmh=169.0,
    cost_per_km=0.3,
) -> FlightOptionDTO:
    return FlightOptionDTO(
        departure_time=departure,
        arrival_time=arrival,
        fare=fare,
        fee=fee,
        total=total,
        aircraft_model=model,
        aircraft_manufacturer=manufacturer,
        range_km=range_km,
        cruise_speed_kmh=cruise_speed_kmh,
        cost_per_km=cost_per_km,
    )


# --- _serialize_airport -----------------------------------------------------


def test_serialize_airport_maps_all_fields():
    assert _serialize_airport(GRU) == {
        "iata": "GRU",
        "city": "Sao Paulo",
        "state": "SP",
        "lat": -23.435,
        "lon": -46.473,
    }


# --- _serialize_price -------------------------------------------------------


def test_serialize_price_renames_fee_to_fees():
    # The provider's contract name is ``fees`` (plural); our DTO field is ``fee``.
    assert _serialize_price(100.0, 40.0, 140.0) == {
        "fare": 100.0,
        "fees": 40.0,
        "total": 140.0,
    }


# --- _serialize_flight ------------------------------------------------------


def test_serialize_flight_maps_full_structure():
    option = _option()

    assert _serialize_flight(option) == {
        "departure_time": "2026-07-10T08:00:00",
        "arrival_time": "2026-07-10T10:00:00",
        "aircraft": {"model": "A320", "manufacturer": "Airbus"},
        "price": {"fare": 100.0, "fees": 40.0, "total": 140.0},
        "meta": {
            "range": 338.0,
            "cruise_speed_kmh": 169.0,
            "cost_per_km": 0.3,
        },
    }


def test_serialize_flight_renders_timestamps_as_isoformat():
    option = _option(
        departure=datetime(2026, 7, 10, 8, 30, 15),
        arrival=datetime(2026, 7, 10, 11, 45),
    )

    serialized = _serialize_flight(option)

    assert serialized["departure_time"] == "2026-07-10T08:30:15"
    assert serialized["arrival_time"] == "2026-07-10T11:45:00"


def test_serialize_flight_exposes_range_under_meta_range_key():
    # Per-flight distance is exposed as ``range`` (provider contract name),
    # unlike the top-level summary which uses ``range_km``.
    serialized = _serialize_flight(_option(range_km=512.5))

    assert serialized["meta"]["range"] == 512.5
    assert "range_km" not in serialized["meta"]


# --- _serialize_round_trip --------------------------------------------------


def test_serialize_round_trip_uses_aggregate_price_and_nests_legs():
    outbound = _option(fare=100.0, fee=40.0, total=140.0)
    inbound = _option(
        fare=110.0,
        fee=40.0,
        total=150.0,
        departure=datetime(2026, 7, 15, 18, 0),
        arrival=datetime(2026, 7, 15, 20, 0),
    )
    # Aggregate fields deliberately distinct from the legs' sums to prove the
    # presenter reads the round-trip's own price, not a re-derived total.
    round_trip = RoundTripOptionDTO(
        outbound=outbound, inbound=inbound, fare=210.0, fee=80.0, total=290.0
    )

    assert _serialize_round_trip(round_trip) == {
        "price": {"fare": 210.0, "fees": 80.0, "total": 290.0},
        "outbound": _serialize_flight(outbound),
        "inbound": _serialize_flight(inbound),
    }


# --- _serialize_result ------------------------------------------------------


def _result(options):
    return FlightSearchResult(
        origin=GRU,
        destination=GIG,
        departure_date=date(2026, 7, 10),
        return_date=date(2026, 7, 15),
        currency="BRL",
        range_km=338.0,
        options=tuple(options),
    )


def test_serialize_result_builds_summary_with_top_level_range_km():
    result = _result([])

    assert _serialize_result(result)["summary"] == {
        "from": _serialize_airport(GRU),
        "to": _serialize_airport(GIG),
        "departure_date": "2026-07-10",
        "return_date": "2026-07-15",
        "currency": "BRL",
        "range_km": 338.0,
    }


def test_serialize_result_counts_and_serializes_each_option():
    round_trip = RoundTripOptionDTO(
        outbound=_option(), inbound=_option(), fare=210.0, fee=80.0, total=290.0
    )
    result = _result([round_trip, round_trip])

    serialized = _serialize_result(result)

    assert serialized["count"] == 2
    assert serialized["options"] == [
        _serialize_round_trip(round_trip),
        _serialize_round_trip(round_trip),
    ]


def test_serialize_result_with_no_options_is_count_zero():
    serialized = _serialize_result(_result([]))

    assert serialized["count"] == 0
    assert serialized["options"] == []
