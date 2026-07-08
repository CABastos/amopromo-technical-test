from datetime import date

import pytest

from airport.dto import AirportDTO
from flight.dto import FlightSearchQuery
from flight.services import MockAirlinesApiError
from flight.usecases import SearchRoundTripUseCase, UnknownAirportError

# Real-ish coordinates; the GRU<->GIG great-circle distance is roughly 338 km.
GRU = AirportDTO(iata="GRU", city="Sao Paulo", state="SP", lat=-23.435, lon=-46.473)
GIG = AirportDTO(iata="GIG", city="Rio de Janeiro", state="RJ", lat=-22.810, lon=-43.251)
TODAY = date(2026, 7, 1)


class FakeMockAirlinesApiService:
    """Returns preset payloads in call order and records each call's arguments."""

    def __init__(self, payloads=None, error=None):
        self._payloads = list(payloads or [])
        self._error = error
        self.calls = []

    def search_flights(self, origin, destination, flight_date):
        self.calls.append((origin, destination, flight_date))
        if self._error is not None:
            raise self._error
        return self._payloads[len(self.calls) - 1]


class FakeAirportRepository:
    """Resolves only the airports it was seeded with; records lookups."""

    def __init__(self, airports=None):
        self._airports = airports or {}
        self.calls = []

    def get_active_by_iatas(self, iatas):
        self.calls.append(list(iatas))
        return {code: self._airports[code] for code in iatas if code in self._airports}


def _option(fare, departure="2026-07-10T08:00:00", arrival="2026-07-10T10:00:00"):
    return {
        "departure_time": departure,
        "arrival_time": arrival,
        "price": {"fare": fare, "fees": 0, "total": 0},
        "aircraft": {"model": "A320", "manufacturer": "Airbus"},
    }


def _payload(options, currency="BRL"):
    return {"summary": {"currency": currency}, "options": options}


def _query():
    return FlightSearchQuery.from_raw("GRU", "GIG", "2026-07-10", "2026-07-15", today=TODAY)


def _use_case(service, repository):
    return SearchRoundTripUseCase(service=service, repository=repository)


def _both_airports():
    return FakeAirportRepository({"GRU": GRU, "GIG": GIG})


def test_execute_builds_sorted_round_trip_combinations():
    # Outbound totals: 300 -> 340 (fee floored to 40), 500 -> 550.
    # Inbound totals: 400 -> 440, 1000 -> 1100.
    outbound = _payload([_option(500.0), _option(300.0)])
    inbound = _payload([_option(400.0), _option(1000.0)])
    service = FakeMockAirlinesApiService(payloads=[outbound, inbound])

    result = _use_case(service, _both_airports()).execute(_query())

    # 2 x 2 combinations, ascending by total: 780, 990, 1440, 1650.
    assert [option.total for option in result.options] == [780.0, 990.0, 1440.0, 1650.0]
    assert result.origin.iata == "GRU"
    assert result.destination.iata == "GIG"
    assert result.currency == "BRL"
    assert result.range_km == pytest.approx(338, rel=0.02)
    # The cheapest combo pairs the cheapest legs (out 340 + in 440).
    cheapest = result.options[0]
    assert cheapest.outbound.total == 340.0
    assert cheapest.inbound.total == 440.0


def test_execute_calls_provider_with_swapped_airports_for_return_leg():
    service = FakeMockAirlinesApiService(payloads=[_payload([_option(500.0)]), _payload([])])

    _use_case(service, _both_airports()).execute(_query())

    assert service.calls[0] == ("GRU", "GIG", date(2026, 7, 10))
    assert service.calls[1] == ("GIG", "GRU", date(2026, 7, 15))


def test_execute_raises_for_unknown_airport_without_calling_provider():
    service = FakeMockAirlinesApiService(payloads=[])
    repository = FakeAirportRepository({"GRU": GRU})  # GIG is unknown

    with pytest.raises(UnknownAirportError):
        _use_case(service, repository).execute(_query())

    assert service.calls == []


def test_execute_skips_invalid_options():
    # Second outbound option has a non-positive fare and is dropped.
    outbound = _payload([_option(500.0), _option(-1.0)])
    inbound = _payload([_option(400.0)])
    service = FakeMockAirlinesApiService(payloads=[outbound, inbound])

    result = _use_case(service, _both_airports()).execute(_query())

    assert len(result.options) == 1
    assert result.options[0].total == 990.0  # 550 + 440


def test_execute_returns_no_options_when_a_leg_is_empty():
    service = FakeMockAirlinesApiService(payloads=[_payload([_option(500.0)]), _payload([])])

    result = _use_case(service, _both_airports()).execute(_query())

    assert result.options == ()
    assert result.currency == "BRL"


def test_execute_propagates_provider_error():
    service = FakeMockAirlinesApiService(error=MockAirlinesApiError("boom"))

    with pytest.raises(MockAirlinesApiError):
        _use_case(service, _both_airports()).execute(_query())


def test_execute_falls_back_to_brl_when_currency_missing():
    outbound = {"summary": {}, "options": [_option(500.0)]}
    inbound = {"summary": {}, "options": [_option(400.0)]}
    service = FakeMockAirlinesApiService(payloads=[outbound, inbound])

    result = _use_case(service, _both_airports()).execute(_query())

    assert result.currency == "BRL"
