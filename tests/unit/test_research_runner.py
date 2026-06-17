from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from adapters.paper.broker import PaperBroker
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle, Instrument
from trading_core.research.data_quality_gate import DataQualityGateConfig
from trading_core.research.runner import ResearchRunner


def make_instrument() -> Instrument:
    return Instrument(
        id="moex:SiH6",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol="SiH6",
        canonical_symbol="MOEX:SiH6",
        name="Si futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def make_candles(count: int = 8) -> list[Candle]:
    start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
    return [
        Candle(
            instrument_id="moex:SiH6",
            venue=Venue.MOEX,
            interval="1m",
            ts_start=start + timedelta(minutes=i),
            ts_end=start + timedelta(minutes=i + 1),
            open=Decimal("100") + Decimal(i),
            high=Decimal("101") + Decimal(i),
            low=Decimal("99") + Decimal(i),
            close=Decimal("100") + Decimal(i),
            volume=Decimal("100"),
            source="test",
        )
        for i in range(count)
    ]


def seeded_storage(candles: list[Candle] | None = None) -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.save_instrument(make_instrument())
    storage.save_candles(candles if candles is not None else make_candles())
    return storage


def broker_factory(initial_cash: Decimal):
    return PaperBroker(initial_cash=initial_cash)


def test_research_runner_successful_run_with_two_parameter_combinations() -> None:
    storage = seeded_storage()
    runner = ResearchRunner(storage=storage, broker_factory=broker_factory)

    summary = runner.run(
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        interval="1m",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        parameter_grid={"opening_range_minutes": [2, 3]},
        initial_cash=Decimal("100000"),
        data_quality_gate_config=DataQualityGateConfig(),
    )

    assert summary.parameter_combinations == 2
    assert summary.completed_backtests == 2
    assert summary.failed_backtests == 0
    assert storage.get_research_run(summary.research_run_id) is not None
    assert len(storage.list_research_backtest_results(summary.research_run_id)) == 2
    assert storage.backtest_runs
    assert storage.backtest_equity_points


def test_research_runner_data_quality_rejection_prevents_backtest_execution() -> None:
    calls = 0

    def counting_broker_factory(initial_cash: Decimal):
        nonlocal calls
        calls += 1
        return PaperBroker(initial_cash=initial_cash)

    storage = seeded_storage([])
    runner = ResearchRunner(storage=storage, broker_factory=counting_broker_factory)

    summary = runner.run(
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        interval="1m",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        parameter_grid={"opening_range_minutes": [2]},
        initial_cash=Decimal("100000"),
        data_quality_gate_config=DataQualityGateConfig(),
    )

    assert calls == 0
    assert summary.failed_backtests == 1
    run = storage.get_research_run(summary.research_run_id)
    assert run is not None
    assert run.status.value == "FAILED"


def test_research_runner_rejects_unknown_instrument() -> None:
    runner = ResearchRunner(storage=InMemoryStorage(), broker_factory=broker_factory)

    with pytest.raises(DataValidationError, match="instrument not found"):
        runner.run(
            strategy_id="opening_range_breakout",
            canonical_symbol="MOEX:UNKNOWN",
            interval="1m",
            start=datetime(2026, 1, 1, tzinfo=UTC),
            end=datetime(2026, 1, 2, tzinfo=UTC),
            parameter_grid={},
            initial_cash=Decimal("100000"),
            data_quality_gate_config=DataQualityGateConfig(),
        )


def test_research_runner_rejects_unknown_strategy() -> None:
    runner = ResearchRunner(storage=seeded_storage(), broker_factory=broker_factory)

    with pytest.raises(DataValidationError, match="Unknown strategy"):
        runner.run(
            strategy_id="unknown",
            canonical_symbol="MOEX:SiH6",
            interval="1m",
            start=datetime(2026, 1, 1, tzinfo=UTC),
            end=datetime(2026, 1, 2, tzinfo=UTC),
            parameter_grid={},
            initial_cash=Decimal("100000"),
            data_quality_gate_config=DataQualityGateConfig(),
        )


def test_research_runner_records_partial_failure() -> None:
    storage = seeded_storage()
    runner = ResearchRunner(storage=storage, broker_factory=broker_factory)

    summary = runner.run(
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        interval="1m",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        parameter_grid={"opening_range_minutes": [2], "unsupported_param": ["bad"]},
        initial_cash=Decimal("100000"),
        data_quality_gate_config=DataQualityGateConfig(),
    )

    assert summary.completed_backtests == 0
    assert summary.failed_backtests == 1
    run = storage.get_research_run(summary.research_run_id)
    assert run is not None
    assert run.status.value == "FAILED"
    assert storage.list_research_backtest_results(summary.research_run_id)[0].error_message is not None
