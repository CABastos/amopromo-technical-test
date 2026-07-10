import re

_IATA_RE = re.compile(r"^[A-Z]{3}$")


def parse_iata(value: object, field: str = "IATA code") -> str:
    """Normalize and validate an IATA airport code (three ASCII letters)."""
    code = str(value).strip().upper()
    if not _IATA_RE.match(code):
        raise ValueError(f"invalid {field} {value!r}")
    return code
