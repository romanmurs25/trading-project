from typing import Any

from trading_core.domain.errors import DataValidationError
from trading_core.research.models import StrategyMetadata
from trading_core.strategy.base import Strategy
from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy
from trading_core.strategy.vwap_reclaim import VWAPReclaimStrategy

STRATEGY_METADATA = {
    OpeningRangeBreakoutStrategy.strategy_id: StrategyMetadata(
        strategy_id=OpeningRangeBreakoutStrategy.strategy_id,
        class_name="OpeningRangeBreakoutStrategy",
        default_params={
            "opening_range_minutes": 5,
            "min_volume_multiplier": "1",
            "direction": "both",
            "stop_mode": "opposite_range",
            "take_profit_r_multiple": "2",
            "max_trades_per_session": 1,
        },
        supported_params=[
            "opening_range_minutes",
            "min_volume_multiplier",
            "direction",
            "stop_mode",
            "take_profit_r_multiple",
            "max_trades_per_session",
        ],
        description="Opening range breakout strategy for intraday research.",
    ),
    VWAPReclaimStrategy.strategy_id: StrategyMetadata(
        strategy_id=VWAPReclaimStrategy.strategy_id,
        class_name="VWAPReclaimStrategy",
        default_params={
            "vwap_mode": "session",
            "vwap_window": 20,
            "min_volume_multiplier": "1",
            "reclaim_confirmation_bars": 1,
            "stop_ticks": "2",
            "take_profit_r_multiple": "2",
        },
        supported_params=[
            "vwap_mode",
            "vwap_window",
            "min_volume_multiplier",
            "reclaim_confirmation_bars",
            "stop_ticks",
            "take_profit_r_multiple",
        ],
        description="VWAP reclaim/rejection skeleton strategy for research.",
    ),
}


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
    return strategy_cls(**_coerce_params(strategy_id, params or {}))


def get_strategy_metadata(strategy_id: str) -> StrategyMetadata:
    metadata = STRATEGY_METADATA.get(strategy_id)
    if metadata is None:
        raise DataValidationError(f"Unknown strategy: {strategy_id}")
    return metadata


def list_strategy_metadata() -> list[StrategyMetadata]:
    return [STRATEGY_METADATA[strategy_id] for strategy_id in available_strategies()]


def _coerce_params(strategy_id: str, params: dict[str, Any]) -> dict[str, Any]:
    metadata = get_strategy_metadata(strategy_id)
    coerced = dict(params)
    for key, default in metadata.default_params.items():
        if key not in coerced:
            continue
        value = coerced[key]
        if isinstance(default, int) and not isinstance(default, bool):
            coerced[key] = int(value)
    return coerced
