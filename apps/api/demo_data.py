from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from trading_core.domain.enums import AssetClass, Side, Venue
from trading_core.domain.models import BacktestRun, Candle, ContractSpec, Instrument
from trading_core.live_data.ingestion import ReadOnlyMarketDataIngestionService
from trading_core.live_data.models import MarketDataIngestionStatus, MarketDataSource
from trading_core.market.calendar import MarketCalendarService
from trading_core.market.continuous import ContinuousSeries, ContinuousSeriesComponent
from trading_core.market.moex_templates import default_moex_futures_session_templates
from trading_core.market.roll import RollEvent
from trading_core.market.sessions import MarketSession
from trading_core.ports.storage import StoragePort
from trading_core.research.models import (
    BacktestEquityPoint,
    BacktestTradeRecord,
    ResearchBacktestResult,
    ResearchRun,
    ResearchStatus,
)

DEMO_SOURCE = "demo"
DEMO_METADATA: dict[str, Any] = {"source": DEMO_SOURCE, "demo": True}
DEMO_RESEARCH_RUN_ID = "demo-research-orb-si-1m"


def seed_demo_data(storage: StoragePort) -> None:
    """Seed small deterministic fake data for local read-only dashboard QA."""
    instruments = _demo_instruments()
    candles = _demo_candles()
    storage.save_instruments(instruments)
    for spec in _demo_contract_specs():
        storage.save_contract_spec(spec)
    storage.save_candles(candles)
    _seed_demo_live_data(storage, instruments[0], candles[:5])
    storage.save_market_sessions(_demo_market_sessions())
    storage.save_continuous_series(_demo_continuous_series())
    storage.save_continuous_series_components(_demo_continuous_components())
    storage.save_roll_events(_demo_roll_events())
    storage.save_research_run(_demo_research_run())
    for run in _demo_backtest_runs():
        storage.save_backtest_run(run)
    for result in _demo_research_results():
        storage.save_research_backtest_result(result)
    storage.save_backtest_equity_points(_demo_equity_points())
    storage.save_backtest_trade_records(_demo_trade_records())


def _seed_demo_live_data(storage: StoragePort, instrument: Instrument, candles: list[Candle]) -> None:
    clock_value = datetime(2026, 1, 1, 4, 5, tzinfo=UTC)
    service = ReadOnlyMarketDataIngestionService(storage=storage, clock=lambda: clock_value)
    run = service.start_run(
        source=MarketDataSource.DEMO_REPLAY,
        venue=instrument.venue,
        instruments=[instrument.canonical_symbol],
        interval="1m",
        allow_network=False,
        metadata=dict(DEMO_METADATA),
    )
    service.ingest_candles(
        run_id=run.id,
        source=MarketDataSource.DEMO_REPLAY,
        instrument=instrument,
        candles=candles,
    )
    service.stop_run(run.id, status=MarketDataIngestionStatus.STOPPED)


def _demo_instruments() -> list[Instrument]:
    return [
        _instrument("SiH6", "USD/RUB Futures March 2026", date(2026, 3, 19), is_active=True),
        _instrument("SiM6", "USD/RUB Futures June 2026", date(2026, 6, 18), is_active=True),
        _instrument("RIH6", "RTS Index Futures March 2026", date(2026, 3, 19), is_active=True),
    ]


def _instrument(symbol: str, name: str, expiry_date: date, *, is_active: bool) -> Instrument:
    return Instrument(
        id=f"moex:{symbol}",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=symbol,
        canonical_symbol=f"MOEX:{symbol}",
        name=name,
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry_date,
        is_active=is_active,
        metadata=dict(DEMO_METADATA),
    )


def _demo_contract_specs() -> list[ContractSpec]:
    return [
        _contract_spec("SiH6", date(2026, 3, 19), "Si"),
        _contract_spec("SiM6", date(2026, 6, 18), "Si"),
        _contract_spec("RIH6", date(2026, 3, 19), "RI"),
    ]


def _contract_spec(symbol: str, expiry_date: date, underlying_symbol: str) -> ContractSpec:
    return ContractSpec(
        instrument_id=f"moex:{symbol}",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry_date,
        first_trade_date=date(2025, 12, 15),
        last_trade_date=expiry_date,
        underlying_symbol=underlying_symbol,
        metadata=dict(DEMO_METADATA),
    )


def _demo_candles() -> list[Candle]:
    candles: list[Candle] = []
    candles.extend(
        _minute_candles(
            symbol="SiH6",
            start=datetime(2026, 1, 1, 4, 0, tzinfo=UTC),
            count=12,
            base_price=Decimal("90000"),
            volume=Decimal("120"),
        )
    )
    candles.append(
        _candle(
            "SiH6",
            datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
            Decimal("89990"),
            Decimal("25"),
        )
    )
    candles.append(
        _candle(
            "SiH6",
            datetime(2026, 1, 1, 4, 12, tzinfo=UTC),
            Decimal("90015"),
            Decimal("0"),
        )
    )
    candles.extend(
        _minute_candles(
            symbol="SiH6",
            start=datetime(2026, 3, 13, 4, 0, tzinfo=UTC),
            count=8,
            base_price=Decimal("91200"),
            volume=Decimal("150"),
        )
    )
    candles.extend(
        _minute_candles(
            symbol="SiM6",
            start=datetime(2026, 3, 16, 4, 0, tzinfo=UTC),
            count=8,
            base_price=Decimal("91800"),
            volume=Decimal("180"),
        )
    )
    return candles


def _minute_candles(
    *,
    symbol: str,
    start: datetime,
    count: int,
    base_price: Decimal,
    volume: Decimal,
) -> list[Candle]:
    return [
        _candle(
            symbol,
            start + timedelta(minutes=index),
            base_price + Decimal(index),
            volume + Decimal(index),
        )
        for index in range(count)
    ]


def _candle(symbol: str, ts_start: datetime, price: Decimal, volume: Decimal) -> Candle:
    return Candle(
        instrument_id=f"moex:{symbol}",
        venue=Venue.MOEX,
        interval="1m",
        ts_start=ts_start,
        ts_end=ts_start + timedelta(minutes=1),
        open=price,
        high=price + Decimal("2"),
        low=price - Decimal("2"),
        close=price + Decimal("1"),
        volume=volume,
        value=price * volume,
        trades_count=int(volume),
        source=DEMO_SOURCE,
    )


def _demo_market_sessions() -> list[MarketSession]:
    calendar = MarketCalendarService(default_moex_futures_session_templates())
    ranges = [
        (datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 3, tzinfo=UTC)),
        (datetime(2026, 3, 13, tzinfo=UTC), datetime(2026, 3, 18, tzinfo=UTC)),
    ]
    sessions = [
        session
        for start, end in ranges
        for session in calendar.generate_sessions(start, end)
    ]
    return [
        session.model_copy(update={"metadata": {**session.metadata, **DEMO_METADATA}})
        for session in sessions
    ]


def _demo_continuous_series() -> ContinuousSeries:
    return ContinuousSeries(
        id="demo-continuous-si-1m",
        venue="MOEX",
        underlying_symbol="Si",
        canonical_symbol="MOEX:Si:CONT:1m",
        interval="1m",
        roll_rule={"roll_days_before_expiry": 5, "source": DEMO_SOURCE, "demo": True},
        adjustment_method="none",
        start=datetime(2026, 3, 13, tzinfo=UTC),
        end=datetime(2026, 3, 17, tzinfo=UTC),
        created_at=datetime(2026, 1, 1, 4, 0, tzinfo=UTC),
        metadata={**DEMO_METADATA, "note": "Synthetic no-adjustment continuous futures demo"},
    )


def _demo_continuous_components() -> list[ContinuousSeriesComponent]:
    return [
        ContinuousSeriesComponent(
            id="demo-continuous-si-1m-component-h6",
            continuous_series_id="demo-continuous-si-1m",
            instrument_id="moex:SiH6",
            canonical_symbol="MOEX:SiH6",
            start=datetime(2026, 3, 13, tzinfo=UTC),
            end=datetime(2026, 3, 16, tzinfo=UTC),
            roll_date=date(2026, 3, 14),
            metadata=dict(DEMO_METADATA),
        ),
        ContinuousSeriesComponent(
            id="demo-continuous-si-1m-component-m6",
            continuous_series_id="demo-continuous-si-1m",
            instrument_id="moex:SiM6",
            canonical_symbol="MOEX:SiM6",
            start=datetime(2026, 3, 16, tzinfo=UTC),
            end=datetime(2026, 3, 17, tzinfo=UTC),
            roll_date=date(2026, 3, 14),
            metadata=dict(DEMO_METADATA),
        ),
    ]


def _demo_roll_events() -> list[RollEvent]:
    return [
        RollEvent(
            id="demo-roll-si-h6-m6",
            venue="MOEX",
            underlying_symbol="Si",
            from_instrument_id="moex:SiH6",
            to_instrument_id="moex:SiM6",
            roll_date=date(2026, 3, 14),
            reason="demo roll 5 days before expiry",
            metadata=dict(DEMO_METADATA),
        )
    ]


def _demo_research_run() -> ResearchRun:
    return ResearchRun(
        id=DEMO_RESEARCH_RUN_ID,
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        instrument_id="moex:SiH6",
        interval="1m",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        parameter_grid={
            "opening_range_minutes": [5, 15],
            "risk_reward": [Decimal("1.5"), Decimal("2.0")],
        },
        data_quality_gate={
            "mode": "session_aware",
            "source": DEMO_SOURCE,
            "demo": True,
        },
        status=ResearchStatus.COMPLETED,
        created_at=datetime(2026, 1, 1, 5, 0, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, 5, 2, tzinfo=UTC),
        notes="Synthetic local demo run for read-only dashboard QA.",
        metadata=dict(DEMO_METADATA),
    )


def _demo_backtest_runs() -> list[BacktestRun]:
    return [
        _backtest_run("demo-backtest-orb-5", Decimal("101250"), Decimal("1250"), Decimal("180")),
        _backtest_run("demo-backtest-orb-15", Decimal("100640"), Decimal("640"), Decimal("120")),
    ]


def _backtest_run(
    run_id: str,
    final_equity: Decimal,
    total_pnl: Decimal,
    max_drawdown: Decimal,
) -> BacktestRun:
    return BacktestRun(
        id=run_id,
        strategy_id="opening_range_breakout",
        strategy_config={"source": DEMO_SOURCE, "demo": True},
        risk_config={"source": DEMO_SOURCE, "demo": True},
        instruments=["moex:SiH6"],
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        initial_cash=Decimal("100000"),
        final_equity=final_equity,
        total_pnl=total_pnl,
        max_drawdown=max_drawdown,
        win_rate=Decimal("0.66"),
        profit_factor=Decimal("1.85"),
        expectancy=Decimal("416.67"),
        avg_r=Decimal("1.20"),
        trades_count=3,
        created_at=datetime(2026, 1, 1, 5, 1, tzinfo=UTC),
    )


def _demo_research_results() -> list[ResearchBacktestResult]:
    return [
        _research_result(
            result_id="demo-result-orb-5",
            backtest_run_id="demo-backtest-orb-5",
            opening_range_minutes=5,
            total_pnl=Decimal("1250"),
            final_equity=Decimal("101250"),
            max_drawdown=Decimal("180"),
            profit_factor=Decimal("1.85"),
            expectancy=Decimal("416.67"),
        ),
        _research_result(
            result_id="demo-result-orb-15",
            backtest_run_id="demo-backtest-orb-15",
            opening_range_minutes=15,
            total_pnl=Decimal("640"),
            final_equity=Decimal("100640"),
            max_drawdown=Decimal("120"),
            profit_factor=Decimal("1.42"),
            expectancy=Decimal("213.33"),
        ),
    ]


def _research_result(
    *,
    result_id: str,
    backtest_run_id: str,
    opening_range_minutes: int,
    total_pnl: Decimal,
    final_equity: Decimal,
    max_drawdown: Decimal,
    profit_factor: Decimal,
    expectancy: Decimal,
) -> ResearchBacktestResult:
    return ResearchBacktestResult(
        id=result_id,
        research_run_id=DEMO_RESEARCH_RUN_ID,
        backtest_run_id=backtest_run_id,
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        instrument_id="moex:SiH6",
        interval="1m",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        params={
            "opening_range_minutes": opening_range_minutes,
            "risk_reward": Decimal("1.5"),
            "source": DEMO_SOURCE,
            "demo": True,
        },
        metrics={
            "total_pnl": total_pnl,
            "final_equity": final_equity,
            "max_drawdown": max_drawdown,
            "win_rate": Decimal("0.66"),
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "avg_win": Decimal("700"),
            "avg_loss": Decimal("-150"),
            "trades_count": 3,
        },
        quality_report={
            "mode": "session_aware",
            "warnings": ["demo data is sparse by design"],
            "source": DEMO_SOURCE,
            "demo": True,
        },
        status=ResearchStatus.COMPLETED,
        created_at=datetime(2026, 1, 1, 5, 1, tzinfo=UTC),
    )


def _demo_equity_points() -> list[BacktestEquityPoint]:
    return [
        _equity_point("demo-eq-5-1", "demo-backtest-orb-5", "04:00", Decimal("100000"), Decimal("0")),
        _equity_point("demo-eq-5-2", "demo-backtest-orb-5", "05:00", Decimal("100420"), Decimal("0")),
        _equity_point("demo-eq-5-3", "demo-backtest-orb-5", "06:00", Decimal("100240"), Decimal("180")),
        _equity_point("demo-eq-5-4", "demo-backtest-orb-5", "07:00", Decimal("101250"), Decimal("0")),
        _equity_point("demo-eq-15-1", "demo-backtest-orb-15", "04:00", Decimal("100000"), Decimal("0")),
        _equity_point("demo-eq-15-2", "demo-backtest-orb-15", "05:00", Decimal("100220"), Decimal("0")),
        _equity_point("demo-eq-15-3", "demo-backtest-orb-15", "06:00", Decimal("100100"), Decimal("120")),
        _equity_point("demo-eq-15-4", "demo-backtest-orb-15", "07:00", Decimal("100640"), Decimal("0")),
    ]


def _equity_point(
    point_id: str,
    backtest_run_id: str,
    hh_mm: str,
    equity: Decimal,
    drawdown: Decimal,
) -> BacktestEquityPoint:
    hour, minute = (int(part) for part in hh_mm.split(":"))
    return BacktestEquityPoint(
        id=point_id,
        backtest_run_id=backtest_run_id,
        ts=datetime(2026, 1, 1, hour, minute, tzinfo=UTC),
        equity=equity,
        drawdown=drawdown,
    )


def _demo_trade_records() -> list[BacktestTradeRecord]:
    return [
        _trade(
            trade_id="demo-trade-5-1",
            backtest_run_id="demo-backtest-orb-5",
            side=Side.BUY,
            entry_price=Decimal("90010"),
            exit_price=Decimal("90620"),
            qty=Decimal("1"),
            gross_pnl=Decimal("610"),
            net_pnl=Decimal("600"),
            r_multiple=Decimal("1.50"),
        ),
        _trade(
            trade_id="demo-trade-5-2",
            backtest_run_id="demo-backtest-orb-5",
            side=Side.SELL,
            entry_price=Decimal("90500"),
            exit_price=Decimal("89830"),
            qty=Decimal("1"),
            gross_pnl=Decimal("670"),
            net_pnl=Decimal("650"),
            r_multiple=Decimal("1.62"),
        ),
        _trade(
            trade_id="demo-trade-15-1",
            backtest_run_id="demo-backtest-orb-15",
            side=Side.BUY,
            entry_price=Decimal("90020"),
            exit_price=Decimal("90680"),
            qty=Decimal("1"),
            gross_pnl=Decimal("660"),
            net_pnl=Decimal("640"),
            r_multiple=Decimal("1.35"),
        ),
    ]


def _trade(
    *,
    trade_id: str,
    backtest_run_id: str,
    side: Side,
    entry_price: Decimal,
    exit_price: Decimal,
    qty: Decimal,
    gross_pnl: Decimal,
    net_pnl: Decimal,
    r_multiple: Decimal,
) -> BacktestTradeRecord:
    return BacktestTradeRecord(
        id=trade_id,
        backtest_run_id=backtest_run_id,
        instrument_id="moex:SiH6",
        side=side,
        entry_ts=datetime(2026, 1, 1, 4, 3, tzinfo=UTC),
        exit_ts=datetime(2026, 1, 1, 6, 45, tzinfo=UTC),
        entry_price=entry_price,
        exit_price=exit_price,
        qty=qty,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        r_multiple=r_multiple,
        reason="synthetic demo closed trade",
        metadata=dict(DEMO_METADATA),
    )
