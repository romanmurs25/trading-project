import pytest
from trading_core.domain.errors import DataValidationError
from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy
from trading_core.strategy.registry import (
    available_strategies,
    create_strategy,
    get_strategy_metadata,
    list_strategy_metadata,
)
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


def test_opening_range_breakout_metadata_exists() -> None:
    metadata = get_strategy_metadata("opening_range_breakout")

    assert metadata.strategy_id == "opening_range_breakout"
    assert metadata.class_name == "OpeningRangeBreakoutStrategy"
    assert "opening_range_minutes" in metadata.supported_params
    assert metadata.default_params["opening_range_minutes"] == 5


def test_vwap_reclaim_metadata_exists() -> None:
    metadata = get_strategy_metadata("vwap_reclaim")

    assert metadata.strategy_id == "vwap_reclaim"
    assert metadata.class_name == "VWAPReclaimStrategy"
    assert "take_profit_r_multiple" in metadata.supported_params


def test_list_strategy_metadata_returns_all_registered_strategies() -> None:
    metadata = list_strategy_metadata()

    assert [item.strategy_id for item in metadata] == ["opening_range_breakout", "vwap_reclaim"]


def test_strategy_metadata_rejects_unknown_strategy() -> None:
    with pytest.raises(DataValidationError, match="Unknown strategy"):
        get_strategy_metadata("unknown")
