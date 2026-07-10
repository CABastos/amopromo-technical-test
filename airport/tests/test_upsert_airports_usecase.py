from contextlib import nullcontext

import pytest

from airport.repositories import UpsertResult
from airport.services import DomesticApiError
from airport.usecases import (
    ImportSummary,
    NoValidAirportsError,
    UpsertAirportsUseCase,
)


class FakeService:
    """Stand-in for DomesticApiService."""

    def __init__(self, payload=None, error=None):
        self._payload = payload if payload is not None else {}
        self._error = error
        self.calls = 0

    def fetch_airports(self):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._payload


class FakeRepository:
    """Stand-in for AirportRepository."""

    def __init__(self, upsert_result=None, deactivated=0):
        self._upsert_result = upsert_result if upsert_result is not None else UpsertResult(0, 0)
        self._deactivated = deactivated
        self.upsert_calls = []
        self.deactivate_calls = []

    def upsert_many(self, dtos):
        self.upsert_calls.append(list(dtos))
        return self._upsert_result

    def deactivate_missing(self, active_iatas):
        self.deactivate_calls.append(list(active_iatas))
        return self._deactivated


def _airport(iata="GRU", city="Sao Paulo", state="SP", lat=-23.4, lon=-46.4):
    return {"iata": iata, "city": city, "state": state, "lat": lat, "lon": lon}


def _make_use_case(service, repository):
    return UpsertAirportsUseCase(service=service, repository=repository, atomic=nullcontext)


def test_execute_happy_path_returns_summary_and_persists():
    payload = {"GRU": _airport("GRU"), "GIG": _airport("GIG", "Rio", "RJ", -22.8, -43.2)}
    service = FakeService(payload=payload)
    repository = FakeRepository(upsert_result=UpsertResult(created=1, updated=1), deactivated=3)

    summary = _make_use_case(service, repository).execute()

    assert summary == ImportSummary(created=1, updated=1, deactivated=3, skipped=0)
    assert len(repository.upsert_calls) == 1
    assert {dto.iata for dto in repository.upsert_calls[0]} == {"GRU", "GIG"}
    assert set(repository.deactivate_calls[0]) == {"GRU", "GIG"}


def test_execute_skips_invalid_records_but_keeps_valid_ones():
    payload = {
        "GRU": _airport("GRU"),
        "XX": _airport(city="BadIata"),
        "ZZZ": _airport("ZZZ", lat=999.0),
        "QQQ": _airport("QQQ", city=""),
        "WWW": _airport("WWW", state="Sao Paulo"),
    }
    service = FakeService(payload=payload)
    repository = FakeRepository(upsert_result=UpsertResult(created=1, updated=0))

    summary = _make_use_case(service, repository).execute()

    assert summary.skipped == 4
    assert {dto.iata for dto in repository.upsert_calls[0]} == {"GRU"}


def test_execute_deduplicates_case_variant_iata_keys_keeping_the_later():
    payload = {"gru": _airport(city="First"), "GRU": _airport(city="Second")}
    service = FakeService(payload=payload)
    repository = FakeRepository(upsert_result=UpsertResult(created=1, updated=0))

    summary = _make_use_case(service, repository).execute()

    assert summary.skipped == 0
    upserted = repository.upsert_calls[0]
    assert [dto.iata for dto in upserted] == ["GRU"]
    assert upserted[0].city == "Second"


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="empty-payload"),
        pytest.param({"XX": _airport(), "1": _airport()}, id="all-invalid"),
    ],
)
def test_execute_aborts_without_touching_repository_when_no_valid_records(payload):
    service = FakeService(payload=payload)
    repository = FakeRepository()

    with pytest.raises(NoValidAirportsError):
        _make_use_case(service, repository).execute()

    assert repository.upsert_calls == []
    assert repository.deactivate_calls == []


def test_execute_propagates_service_error_without_touching_repository():
    service = FakeService(error=DomesticApiError("boom"))
    repository = FakeRepository()

    with pytest.raises(DomesticApiError):
        _make_use_case(service, repository).execute()

    assert service.calls == 1
    assert repository.upsert_calls == []
    assert repository.deactivate_calls == []
