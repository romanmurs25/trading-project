from decimal import ROUND_HALF_UP, Decimal
from typing import Any


class MoneyError(ValueError):
    """Ошибка преобразования финансового значения."""


def as_decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        return Decimal(value)
    raise MoneyError("Financial values must be Decimal, int, or str; float is forbidden")


def ensure_decimal(value: Any) -> Decimal:
    return as_decimal(value)


def quantize_price(value: Decimal | int | str, tick_size: Decimal | int | str) -> Decimal:
    price = as_decimal(value)
    tick = as_decimal(tick_size)
    if tick <= 0:
        raise MoneyError("tick_size must be positive")
    steps = (price / tick).to_integral_value(rounding=ROUND_HALF_UP)
    return steps * tick
