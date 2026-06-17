from typing import Any

from trading_core.domain.errors import DataValidationError
from trading_core.strategy.base import Strategy
from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy
from trading_core.strategy.vwap_reclaim import VWAPReclaimStrategy


def available_strategies() -> dict[str, type[Strategy]]:
    return {
        OpeningRangeBreakoutStrategy.strategy_id: OpeningRangeBreakoutStrategy,
        VWAPReclaimStrategy.strategy_id: VWAPReclaimStrategy,
    }


def create_strategy(strategy_id: str, params: dict[str, Any] | None = None) -> Strategy:
    strategies = available_strategies()
    strategy_cls = strategies.get(strategy_id)
    if strategy_cls is None:
        raise DataValidationError(f"Unknown strategy: {strategy_id}")
    return strategy_cls(**(params or {}))
