from collections.abc import Callable
from datetime import date, datetime


def parse_date(value: object, field: str) -> date:
    """Coerce a raw value into a ``date``.

    Accepts existing ``date`` instances as-is and parses ISO ``YYYY-MM-DD``
    strings. ``field`` names the value so the error message points at the
    offending input.

    Raises:
        ValueError: if the value is not a valid ISO date.
    """
    return _parse(value, field, date, date.fromisoformat)


def parse_datetime(value: object, field: str) -> datetime:
    """Coerce a raw value into a ``datetime``.

    Accepts existing ``datetime`` instances as-is and parses ISO-8601 strings.
    ``field`` names the value so the error message points at the offending
    input.

    Raises:
        ValueError: if the value is not a valid ISO datetime.
    """
    return _parse(value, field, datetime, datetime.fromisoformat)


def _parse[T: (date, datetime)](
    value: object, field: str, expected_type: type[T], parser: Callable[[str], T]
) -> T:
    if isinstance(value, expected_type):
        return value
    try:
        return parser(str(value))
    except ValueError as exc:
        raise ValueError(f"invalid {field} {value!r}: {exc}") from exc
