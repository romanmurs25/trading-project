from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy
from trading_core.strategy.vwap_reclaim import VWAPReclaimStrategy


def available_strategies() -> dict[str, type[OpeningRangeBreakoutStrategy] | type[VWAPReclaimStrategy]]:
    return {
        OpeningRangeBreakoutStrategy.strategy_id: OpeningRangeBreakoutStrategy,
        VWAPReclaimStrategy.strategy_id: VWAPReclaimStrategy,
    }
