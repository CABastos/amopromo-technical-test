from collections.abc import Callable
from datetime import date, datetime


def parse_date(value: object, field: str) -> date:
    """Coerce a raw value into a ``date``."""
    return _parse(value, field, date, date.fromisoformat)


def parse_datetime(value: object, field: str) -> datetime:
    """Coerce a raw value into a ``datetime``."""
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
