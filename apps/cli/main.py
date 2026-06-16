import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import typer
from adapters.paper.broker import PaperBroker
from trading_core.backtest.engine import BacktestEngine
from trading_core.config import AppConfig
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument, RiskConfig
from trading_core.risk.engine import RiskEngine
from trading_core.risk.kill_switch import KillSwitch
from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy

app = typer.Typer(help="Safety-first trading platform CLI")
config_app = typer.Typer(help="Конфигурация")
risk_app = typer.Typer(help="Risk controls")
backtest_app = typer.Typer(help="Backtesting")
db_app = typer.Typer(help="Database helpers")

_kill_switch = KillSwitch(AppConfig().risk)


@config_app.command("show-safe")
def show_safe_config() -> None:
    typer.echo(json.dumps(AppConfig().safe_dict(), ensure_ascii=False, indent=2, default=str))


@risk_app.command("status")
def risk_status() -> None:
    typer.echo(
        json.dumps(
            {"kill_switch_active": _kill_switch.active, "reason": _kill_switch.reason},
            ensure_ascii=False,
            indent=2,
        )
    )


@risk_app.command("kill")
def risk_kill() -> None:
    _kill_switch.activate("cli manual activation")
    risk_status()


@backtest_app.command("run-synthetic")
def run_synthetic_backtest() -> None:
    instrument = _synthetic_instrument()
    candles = _synthetic_candles(instrument.id)
    engine = BacktestEngine(
        strategy=OpeningRangeBreakoutStrategy(opening_range_minutes=2),
        risk_engine=RiskEngine(RiskConfig(instrument_allowlist=[instrument.id]), KillSwitch()),
        broker=PaperBroker(initial_cash=Decimal("100000")),
    )
    result = engine.run(candles=candles, instrument=instrument)
    typer.echo(
        json.dumps(
            {
                "trades_count": result.trades_count,
                "closed_trades_count": result.closed_trades_count,
                "executions_count": result.executions_count,
                "final_equity": str(result.final_equity),
                "total_pnl": str(result.total_pnl),
                "profit_factor": str(result.profit_factor),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@db_app.command("check-config")
def db_check_config() -> None:
    config = AppConfig()
    typer.echo(json.dumps({"database_url": config.safe_dict()["database_url"]}, ensure_ascii=False, indent=2))


@db_app.command("init-placeholder")
def db_init_placeholder() -> None:
    typer.echo(
        "SQLAlchemy models are defined in packages/storage/sqlalchemy_models.py; "
        "Alembic migration will be added in the next storage cycle."
    )


def _synthetic_instrument() -> Instrument:
    return Instrument(
        id="synthetic",
        venue=Venue.PAPER,
        asset_class=AssetClass.FUTURES,
        native_symbol="SYN",
        canonical_symbol="PAPER:SYN",
        name="Synthetic futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def _synthetic_candles(instrument_id: str) -> list[Candle]:
    start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    return [
        Candle(
            instrument_id=instrument_id,
            venue=Venue.PAPER,
            interval="1m",
            ts_start=start + timedelta(minutes=i),
            ts_end=start + timedelta(minutes=i + 1),
            open=Decimal("100") + Decimal(i),
            high=Decimal("101") + Decimal(i),
            low=Decimal("99") + Decimal(i),
            close=Decimal("100") + Decimal(i),
            volume=Decimal("1000"),
            source="synthetic-cli",
        )
        for i in range(6)
    ]


app.add_typer(config_app, name="config")
app.add_typer(risk_app, name="risk")
app.add_typer(backtest_app, name="backtest")
app.add_typer(db_app, name="db")


if __name__ == "__main__":
    app()
