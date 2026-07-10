import re

_IATA_RE = re.compile(r"^[A-Z]{3}$")


def parse_iata(value: object, field: str = "IATA code") -> str:
    """Normalize and validate an IATA airport code (three ASCII letters).

    Strips surrounding whitespace and upper-cases the value, then checks it is
    exactly three A-Z letters. ``field`` names the value so the error message
    points at the offending input.

    Raises:
        ValueError: if the normalized value is not three A-Z letters.
    """
    code = str(value).strip().upper()
    if not _IATA_RE.match(code):
        raise ValueError(f"invalid {field} {value!r}")
    return code
