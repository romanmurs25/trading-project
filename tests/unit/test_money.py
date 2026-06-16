from decimal import Decimal

import pytest
from trading_core.domain.money import MoneyError, as_decimal, quantize_price


def test_decimal_helper_keeps_exact_arithmetic() -> None:
    total = as_decimal("0.1") + as_decimal("0.2")

    assert total == Decimal("0.3")


def test_decimal_helper_rejects_float_input() -> None:
    with pytest.raises(MoneyError):
        as_decimal(0.1)


def test_quantize_price_uses_tick_size() -> None:
    assert quantize_price("101.237", "0.05") == Decimal("101.25")
