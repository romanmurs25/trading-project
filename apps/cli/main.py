import asyncio
import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal

import typer
from adapters.moex_iss.market_data_adapter import MoexIssMarketDataAdapter
from adapters.paper.broker import PaperBroker
from storage.in_memory import InMemoryStorage
from storage.sqlalchemy_repositories import SQLAlchemyStorage
from trading_core.backtest.engine import BacktestEngine
from trading_core.config import AppConfig
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument, RiskConfig
from trading_core.ports.storage import StoragePort
from trading_core.risk.engine import RiskEngine
from trading_core.risk.kill_switch import KillSwitch
from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy

app = typer.Typer(help="Safety-first trading platform CLI")
config_app = typer.Typer(help="Конфигурация")
risk_app = typer.Typer(help="Risk controls")
backtest_app = typer.Typer(help="Backtesting")
db_app = typer.Typer(help="Database helpers")
data_app = typer.Typer(help="Market data helpers")

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
        "SQLAlchemy models and Alembic initial migration are available. "
        "Use `alembic upgrade head` for real DB migration. "
        "Repository tests use SQLite in-memory."
    )


@data_app.command("backfill-moex")
def backfill_moex(
    symbol: str = typer.Option(..., "--symbol"),
    instrument_id: str = typer.Option(..., "--instrument-id"),
    interval: str = typer.Option("1m", "--interval"),
    from_date: str = typer.Option(..., "--from"),
    to_date: str = typer.Option(..., "--to"),
    storage: Literal["in-memory", "db"] = typer.Option("in-memory", "--storage"),
    dry_run: bool = typer.Option(True, "--dry-run/--write"),
    allow_network: bool = typer.Option(False, "--allow-network"),
) -> None:
    start = _parse_cli_date(from_date)
    end = _parse_cli_date(to_date)
    warnings: list[str] = []
    candles_loaded = 0
    candles_saved = 0

    if not allow_network:
        warnings.append("external network is disabled by default; pass --allow-network explicitly")
        _echo_backfill_result(
            symbol,
            interval,
            start,
            end,
            candles_loaded,
            candles_saved,
            storage,
            dry_run,
            allow_network,
            warnings,
        )
        return

    instrument = _moex_instrument(symbol, instrument_id)
    adapter = MoexIssMarketDataAdapter()
    candles = asyncio.run(adapter.get_historical_candles(instrument, interval, start, end))
    candles_loaded = len(candles)
    if not dry_run:
        target_storage: StoragePort
        if storage == "in-memory":
            target_storage = InMemoryStorage()
        else:
            target_storage = SQLAlchemyStorage.from_url(AppConfig().database_url)
        target_storage.save_candles(candles)
        candles_saved = len(candles)
    _echo_backfill_result(
        symbol,
        interval,
        start,
        end,
        candles_loaded,
        candles_saved,
        storage,
        dry_run,
        allow_network,
        warnings,
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


def _moex_instrument(symbol: str, instrument_id: str) -> Instrument:
    return Instrument(
        id=instrument_id,
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=symbol,
        canonical_symbol=f"MOEX:{symbol}",
        name=symbol,
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def _parse_cli_date(value: str) -> datetime:
    return datetime.combine(date.fromisoformat(value), time.min, tzinfo=UTC)


def _echo_backfill_result(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    candles_loaded: int,
    candles_saved: int,
    storage: str,
    dry_run: bool,
    allow_network: bool,
    warnings: list[str],
) -> None:
    typer.echo(
        json.dumps(
            {
                "symbol": symbol,
                "interval": interval,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "candles_loaded": candles_loaded,
                "candles_saved": candles_saved,
                "storage": storage,
                "dry_run": dry_run,
                "allow_network": allow_network,
                "warnings": warnings,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


app.add_typer(config_app, name="config")
app.add_typer(risk_app, name="risk")
app.add_typer(backtest_app, name="backtest")
app.add_typer(db_app, name="db")
app.add_typer(data_app, name="data")


if __name__ == "__main__":
    app()
