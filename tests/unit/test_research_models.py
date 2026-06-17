from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from trading_core.domain.enums import Side
from trading_core.research.models import (
    BacktestEquityPoint,
    BacktestTradeRecord,
    ResearchBacktestResult,
    ResearchRun,
    ResearchStatus,
)


def aware() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def test_research_models_reject_float_decimal_fields() -> None:
    with pytest.raises(ValidationError):
        BacktestEquityPoint(backtest_run_id="bt-1", ts=aware(), equity=100.0, drawdown=Decimal("0"))


def test_research_models_reject_naive_datetimes() -> None:
    with pytest.raises(ValidationError):
        ResearchRun(
            strategy_id="opening_range_breakout",
            canonical_symbol="MOEX:SiH6",
            instrument_id="moex:SiH6",
            interval="1m",
            start=datetime(2026, 1, 1),
            end=aware(),
            parameter_grid={},
            data_quality_gate={},
            status=ResearchStatus.CREATED,
        )


def test_research_models_accept_json_safe_fields() -> None:
    run = ResearchRun(
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        instrument_id="moex:SiH6",
        interval="1m",
        start=aware(),
        end=aware(),
        parameter_grid={"opening_range_minutes": [5, 15]},
        data_quality_gate={"max_missing_intervals_count": 0},
        status=ResearchStatus.CREATED,
        notes="cycle 5",
        metadata={"source": "test"},
    )
    result = ResearchBacktestResult(
        research_run_id=run.id,
        backtest_run_id="bt-1",
        strategy_id=run.strategy_id,
        canonical_symbol=run.canonical_symbol,
        instrument_id=run.instrument_id,
        interval=run.interval,
        start=run.start,
        end=run.end,
        params={"opening_range_minutes": 5},
        metrics={"profit_factor": "1.2"},
        quality_report={"candles_count": 10},
        status=ResearchStatus.COMPLETED,
    )
    trade = BacktestTradeRecord(
        backtest_run_id="bt-1",
        instrument_id="moex:SiH6",
        side=Side.BUY,
        entry_ts=aware(),
        exit_ts=aware(),
        entry_price=Decimal("100"),
        exit_price=Decimal("102"),
        qty=Decimal("1"),
        gross_pnl=Decimal("2"),
        net_pnl=Decimal("2"),
        r_multiple=Decimal("1"),
        reason="test",
    )

    assert run.status == ResearchStatus.CREATED
    assert result.research_run_id == run.id
    assert trade.net_pnl == Decimal("2")
