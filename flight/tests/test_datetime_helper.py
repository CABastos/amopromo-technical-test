from datetime import date, datetime

import pytest

from flight.helpers import parse_date, parse_datetime


# --- parse_date -------------------------------------------------------------


def test_parse_date_parses_iso_string():
    assert parse_date("2026-07-10", "departure_date") == date(2026, 7, 10)


def test_parse_date_passes_through_date_object():
    value = date(2026, 7, 10)

    # An existing date is returned unchanged, never re-parsed.
    assert parse_date(value, "departure_date") is value


def test_parse_date_passes_through_datetime_object():
    # datetime is a subclass of date, so a datetime satisfies the type check
    # and flows through as-is rather than being truncated to a date.
    value = datetime(2026, 7, 10, 8, 30)

    assert parse_date(value, "departure_date") is value


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("not-a-date", id="non-date-string"),
        pytest.param("2026-13-01", id="month-out-of-range"),
        pytest.param("2026-07-10T08:30:00", id="datetime-string"),
        pytest.param("", id="empty-string"),
        pytest.param(None, id="none"),
        pytest.param(42, id="integer"),
    ],
)
def test_parse_date_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_date(value, "departure_date")


def test_parse_date_error_names_the_field_and_value():
    with pytest.raises(ValueError, match=r"invalid departure_date 'nope'"):
        parse_date("nope", "departure_date")


# --- parse_datetime ---------------------------------------------------------


def test_parse_datetime_parses_iso_string():
    assert parse_datetime("2026-07-10T08:30:00", "departure_time") == datetime(
        2026, 7, 10, 8, 30
    )


def test_parse_datetime_passes_through_datetime_object():
    value = datetime(2026, 7, 10, 8, 30)

    # An existing datetime is returned unchanged, never re-parsed.
    assert parse_datetime(value, "departure_time") is value


def test_parse_datetime_accepts_date_only_string_as_midnight():
    # A date-only ISO string parses to midnight of that day.
    assert parse_datetime("2026-07-10", "departure_time") == datetime(2026, 7, 10, 0, 0)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("not-a-datetime", id="non-datetime-string"),
        pytest.param("2026-07-10T25:00:00", id="hour-out-of-range"),
        pytest.param("", id="empty-string"),
        pytest.param(None, id="none"),
        pytest.param(42, id="integer"),
    ],
)
def test_parse_datetime_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_datetime(value, "departure_time")


def test_parse_datetime_error_names_the_field_and_value():
    with pytest.raises(ValueError, match=r"invalid departure_time 'nope'"):
        parse_datetime("nope", "departure_time")
