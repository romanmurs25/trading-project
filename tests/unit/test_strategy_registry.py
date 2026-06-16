import pytest
from trading_core.domain.errors import DataValidationError
from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy
from trading_core.strategy.registry import available_strategies, create_strategy
from trading_core.strategy.vwap_reclaim import VWAPReclaimStrategy


def test_available_strategies_includes_mvp_strategies() -> None:
    assert available_strategies() == {
        "opening_range_breakout": OpeningRangeBreakoutStrategy,
        "vwap_reclaim": VWAPReclaimStrategy,
    }


def test_create_strategy_instantiates_with_params() -> None:
    strategy = create_strategy("opening_range_breakout", {"opening_range_minutes": 2})

    assert isinstance(strategy, OpeningRangeBreakoutStrategy)
    assert strategy.opening_range_minutes == 2


def test_create_strategy_rejects_unknown_strategy() -> None:
    with pytest.raises(DataValidationError, match="Unknown strategy"):
        create_strategy("unknown")
