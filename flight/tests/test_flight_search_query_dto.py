from datetime import date

import pytest

from flight.dto import FlightSearchQuery

TODAY = date(2026, 7, 8)


def test_from_raw_builds_query_from_valid_input():
    query = FlightSearchQuery.from_raw("GRU", "GIG", "2026-07-10", "2026-07-15", today=TODAY)

    assert query == FlightSearchQuery(
        origin="GRU",
        destination="GIG",
        departure_date=date(2026, 7, 10),
        return_date=date(2026, 7, 15),
    )


def test_from_raw_normalizes_iata_and_accepts_date_objects():
    query = FlightSearchQuery.from_raw(
        "  gru ", "gig", date(2026, 7, 10), date(2026, 7, 15), today=TODAY
    )

    assert query.origin == "GRU"
    assert query.destination == "GIG"
    assert query.departure_date == date(2026, 7, 10)
    assert query.return_date == date(2026, 7, 15)


def test_from_raw_allows_departure_today_and_return_equal_to_departure():
    # Both boundaries are inclusive: departure == today and return == departure.
    query = FlightSearchQuery.from_raw("GRU", "GIG", TODAY, TODAY, today=TODAY)

    assert query.departure_date == TODAY
    assert query.return_date == TODAY


@pytest.mark.parametrize(
    ("origin", "destination", "departure_date", "return_date"),
    [
        pytest.param("GR", "GIG", "2026-07-10", "2026-07-15", id="origin-too-short"),
        pytest.param("GRUX", "GIG", "2026-07-10", "2026-07-15", id="origin-too-long"),
        pytest.param("G1U", "GIG", "2026-07-10", "2026-07-15", id="origin-not-letters"),
        pytest.param("GRU", "GI", "2026-07-10", "2026-07-15", id="destination-invalid"),
        pytest.param("GRU", "gru", "2026-07-10", "2026-07-15", id="same-origin-destination"),
        pytest.param("GRU", "GIG", "not-a-date", "2026-07-15", id="unparseable-departure"),
        pytest.param("GRU", "GIG", "2026-07-10", "nope", id="unparseable-return"),
        pytest.param("GRU", "GIG", "2026-07-07", "2026-07-15", id="departure-in-past"),
        pytest.param("GRU", "GIG", "2026-07-15", "2026-07-10", id="return-before-departure"),
    ],
)
def test_from_raw_rejects_invalid_input(origin, destination, departure_date, return_date):
    with pytest.raises(ValueError):
        FlightSearchQuery.from_raw(origin, destination, departure_date, return_date, today=TODAY)
