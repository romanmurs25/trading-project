from datetime import UTC, datetime, timedelta
from decimal import Decimal

from adapters.paper.broker import PaperBroker
from fastapi import APIRouter
from trading_core.backtest.engine import BacktestEngine
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument, RiskConfig
from trading_core.risk.engine import RiskEngine
from trading_core.risk.kill_switch import KillSwitch
from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.post("/run")
def run_backtest() -> dict[str, object]:
    instrument = Instrument(
        id="synthetic",
        venue=Venue.PAPER,
        asset_class=AssetClass.FUTURES,
        native_symbol="SYN",
        canonical_symbol="PAPER:SYN",
        name="Synthetic instrument",
        lot_size=Decimal("1"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1"),
        currency="RUB",
    )
    start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    candles = [
        Candle(
            instrument_id=instrument.id,
            venue=Venue.PAPER,
            interval="1m",
            ts_start=start + timedelta(minutes=i),
            ts_end=start + timedelta(minutes=i + 1),
            open=Decimal("100") + Decimal(i),
            high=Decimal("101") + Decimal(i),
            low=Decimal("99") + Decimal(i),
            close=Decimal("100") + Decimal(i),
            volume=Decimal("1000"),
            source="synthetic-api",
        )
        for i in range(6)
    ]
    engine = BacktestEngine(
        strategy=OpeningRangeBreakoutStrategy(opening_range_minutes=2),
        risk_engine=RiskEngine(RiskConfig(instrument_allowlist=[instrument.id]), KillSwitch()),
        broker=PaperBroker(initial_cash=Decimal("100000")),
    )
    result = engine.run(candles=candles, instrument=instrument)
    return {
        "trades_count": result.trades_count,
        "closed_trades_count": result.closed_trades_count,
        "executions_count": result.executions_count,
        "rejected_signals_count": result.rejected_signals_count,
        "final_equity": str(result.final_equity),
        "total_pnl": str(result.total_pnl),
        "metrics": {key: str(value) for key, value in result.metrics.items()},
    }


@router.get("/{backtest_id}")
def get_backtest(backtest_id: str) -> dict[str, str]:
    return {"id": backtest_id, "status": "not_persisted_in_mvp"}


@router.get("")
def list_backtests() -> list[dict[str, str]]:
    return []
