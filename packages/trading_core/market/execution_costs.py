from decimal import Decimal

from trading_core.domain.models import DomainModel


class BacktestExecutionCostConfig(DomainModel):
    commission_rate: Decimal = Decimal("0")
    fixed_commission_per_order: Decimal = Decimal("0")
    slippage_ticks: Decimal = Decimal("0")
    spread_bps: Decimal = Decimal("0")


def estimate_backtest_costs(order_notional: Decimal, config: BacktestExecutionCostConfig) -> Decimal:
    commission = order_notional * config.commission_rate
    spread_cost = order_notional * config.spread_bps / Decimal("10000")
    return commission + config.fixed_commission_per_order + spread_cost
