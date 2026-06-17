from decimal import Decimal

import pytest
from pydantic import ValidationError
from trading_core.market.execution_costs import BacktestExecutionCostConfig, estimate_backtest_costs


def test_execution_cost_config_rejects_float_fields() -> None:
    with pytest.raises(ValidationError, match="float is forbidden"):
        BacktestExecutionCostConfig(commission_rate=0.001)


def test_estimate_backtest_costs_uses_decimal_inputs() -> None:
    cost = estimate_backtest_costs(
        Decimal("100000"),
        BacktestExecutionCostConfig(
            commission_rate=Decimal("0.001"),
            fixed_commission_per_order=Decimal("2"),
            spread_bps=Decimal("5"),
        ),
    )

    assert cost == Decimal("152.000")
