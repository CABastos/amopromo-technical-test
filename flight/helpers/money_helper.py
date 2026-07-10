from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def to_money(value: object) -> Decimal:
    """Coerce a numeric value to a 2-decimal Decimal, rounding half up.

    Non-Decimal inputs are routed through ``str`` first so a binary float like
    218.66 becomes exactly Decimal("218.66") rather than its float artifact.
    """
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)
