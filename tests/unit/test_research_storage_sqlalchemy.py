from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from storage.sqlalchemy_models import Base
from storage.sqlalchemy_repositories import SQLAlchemyStorage
from trading_core.domain.enums import Side
from trading_core.research.models import (
    BacktestEquityPoint,
    BacktestTradeRecord,
    ResearchBacktestResult,
    ResearchRun,
    ResearchStatus,
)


def make_storage() -> SQLAlchemyStorage:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SQLAlchemyStorage(sessionmaker(bind=engine))


def aware() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def make_run(status: ResearchStatus = ResearchStatus.CREATED) -> ResearchRun:
    return ResearchRun(
        id="research-1",
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        instrument_id="moex:SiH6",
        interval="1m",
        start=aware(),
        end=aware(),
        parameter_grid={"opening_range_minutes": [5]},
        data_quality_gate={},
        status=status,
    )


def make_result() -> ResearchBacktestResult:
    return ResearchBacktestResult(
        id="result-1",
        research_run_id="research-1",
        backtest_run_id="bt-1",
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        instrument_id="moex:SiH6",
        interval="1m",
        start=aware(),
        end=aware(),
        params={"opening_range_minutes": 5},
        metrics={"profit_factor": "1"},
        quality_report={"warnings": []},
        status=ResearchStatus.COMPLETED,
    )


def test_sqlalchemy_storage_saves_lists_and_gets_research_run() -> None:
    storage = make_storage()
    run = make_run(ResearchStatus.COMPLETED)

    storage.save_research_run(run)

    assert storage.get_research_run("research-1") == run
    assert storage.list_research_runs(strategy_id="opening_range_breakout") == [run]
    assert storage.list_research_runs(canonical_symbol="MOEX:SiH6", status=ResearchStatus.COMPLETED) == [run]


def test_sqlalchemy_storage_saves_and_loads_research_results_equity_and_trades() -> None:
    storage = make_storage()
    result = make_result()
    point = BacktestEquityPoint(
        id="eq-1",
        backtest_run_id="bt-1",
        ts=aware(),
        equity=Decimal("100000"),
        drawdown=Decimal("0"),
    )
    record = BacktestTradeRecord(
        id="trade-1",
        backtest_run_id="bt-1",
        instrument_id="moex:SiH6",
        side=Side.BUY,
        entry_ts=aware(),
        exit_ts=aware(),
        entry_price=Decimal("100"),
        exit_price=Decimal("101"),
        qty=Decimal("1"),
        gross_pnl=Decimal("1"),
        net_pnl=Decimal("1"),
    )

    storage.save_research_backtest_result(result)
    storage.save_backtest_equity_points([point])
    storage.save_backtest_trade_records([record])

    assert storage.get_research_backtest_result("result-1") == result
    assert storage.list_research_backtest_results("research-1") == [result]
    assert storage.load_backtest_equity_points("bt-1") == [point]
    assert storage.load_backtest_trade_records("bt-1") == [record]
