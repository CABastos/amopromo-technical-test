from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def to_money(value: object) -> Decimal:
    """Coerce a numeric value to a 2-decimal Decimal, rounding half up."""
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)
