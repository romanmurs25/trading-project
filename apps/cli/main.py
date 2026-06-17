import asyncio
import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

import typer
from adapters.moex_iss.instruments import MoexIssInstrumentsService
from adapters.moex_iss.market_data_adapter import MoexIssMarketDataAdapter
from adapters.paper.broker import PaperBroker
from storage.in_memory import InMemoryStorage
from storage.sqlalchemy_repositories import SQLAlchemyStorage
from trading_core.analytics.data_quality import analyze_candle_series
from trading_core.backtest.engine import BacktestEngine
from trading_core.config import AppConfig
from trading_core.domain.enums import AssetClass, TradingMode, Venue
from trading_core.domain.models import BacktestRun, Candle, ContractSpec, DomainModel, Instrument, RiskConfig
from trading_core.ports.storage import StoragePort
from trading_core.risk.engine import RiskEngine
from trading_core.risk.kill_switch import KillSwitch
from trading_core.strategy.opening_range_breakout import OpeningRangeBreakoutStrategy
from trading_core.strategy.registry import create_strategy

app = typer.Typer(help="Safety-first trading platform CLI")
config_app = typer.Typer(help="Конфигурация")
risk_app = typer.Typer(help="Risk controls")
backtest_app = typer.Typer(help="Backtesting")
db_app = typer.Typer(help="Database helpers")
data_app = typer.Typer(help="Market data helpers")
instruments_app = typer.Typer(help="Instrument registry")

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


@backtest_app.command("run-db")
def run_db_backtest(
    strategy_id: str = typer.Option(..., "--strategy"),
    canonical_symbol: str = typer.Option(..., "--canonical-symbol"),
    interval: str = typer.Option("1m", "--interval"),
    from_date: str = typer.Option(..., "--from"),
    to_date: str = typer.Option(..., "--to"),
    storage: Literal["in-memory", "db"] = typer.Option("in-memory", "--storage"),
    initial_cash: str = typer.Option("100000", "--initial-cash"),
) -> None:
    target_storage = _resolve_storage(storage)
    instrument = target_storage.get_instrument_by_canonical_symbol(canonical_symbol)
    if instrument is None:
        raise typer.BadParameter(f"instrument not found: {canonical_symbol}")

    start = _parse_cli_date(from_date)
    end = _parse_cli_date(to_date)
    candles = target_storage.load_candles(instrument.id, interval, start, end)
    if not candles:
        raise typer.BadParameter(f"no candles found for {canonical_symbol} {interval} {from_date}..{to_date}")

    parsed_initial_cash = _parse_decimal_option(initial_cash, "initial-cash")
    strategy = create_strategy(strategy_id)
    risk_config = RiskConfig(
        trading_mode=TradingMode.PAPER,
        instrument_allowlist=[instrument.id, instrument.canonical_symbol],
    )
    paper_instrument = instrument.model_copy(update={"venue": Venue.PAPER})
    paper_candles = [candle.model_copy(update={"venue": Venue.PAPER}) for candle in candles]
    engine = BacktestEngine(
        strategy=strategy,
        risk_engine=RiskEngine(risk_config, KillSwitch(risk_config)),
        broker=PaperBroker(initial_cash=parsed_initial_cash),
    )
    result = engine.run(candles=paper_candles, instrument=paper_instrument)
    run = BacktestRun(
        strategy_id=strategy_id,
        strategy_config={},
        risk_config=risk_config.model_dump(mode="json"),
        instruments=[instrument.id],
        start=start,
        end=end,
        initial_cash=parsed_initial_cash,
        final_equity=result.final_equity,
        total_pnl=result.total_pnl,
        max_drawdown=result.max_drawdown,
        win_rate=result.win_rate,
        profit_factor=result.profit_factor,
        expectancy=result.expectancy,
        avg_r=result.avg_r,
        trades_count=result.trades_count,
    )
    target_storage.save_backtest_run(run)
    _echo_json(
        {
            "run_id": run.id,
            "strategy_id": strategy_id,
            "canonical_symbol": canonical_symbol,
            "instrument_id": instrument.id,
            "interval": interval,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "candles_count": len(candles),
            "metrics": {key: str(value) for key, value in result.metrics.items()},
        }
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


@instruments_app.command("list")
def instruments_list(
    venue: str | None = typer.Option(None, "--venue"),
    asset_class: str | None = typer.Option(None, "--asset-class"),
    is_active: bool | None = typer.Option(None, "--active/--inactive"),
    storage: Literal["in-memory", "db"] = typer.Option("in-memory", "--storage"),
) -> None:
    target_storage = _resolve_storage(storage)
    instruments = target_storage.list_instruments(
        venue=_optional_venue(venue),
        asset_class=_optional_asset_class(asset_class),
        is_active=is_active,
    )
    _echo_json({"instruments": [_model_json(instrument) for instrument in instruments]})


@instruments_app.command("get")
def instruments_get(
    canonical_symbol: str = typer.Option(..., "--canonical-symbol"),
    storage: Literal["in-memory", "db"] = typer.Option("in-memory", "--storage"),
) -> None:
    target_storage = _resolve_storage(storage)
    instrument = target_storage.get_instrument_by_canonical_symbol(canonical_symbol)
    if instrument is None:
        raise typer.BadParameter(f"instrument not found: {canonical_symbol}")
    _echo_json(
        {
            "instrument": _model_json(instrument),
            "contract_spec": _contract_spec_json(target_storage.get_contract_spec(instrument.id)),
        }
    )


@data_app.command("backfill-moex")
def backfill_moex(
    symbol: str | None = typer.Option(None, "--symbol"),
    instrument_id: str | None = typer.Option(None, "--instrument-id"),
    canonical_symbol: str | None = typer.Option(None, "--canonical-symbol"),
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
    instrument = _resolve_moex_backfill_instrument(canonical_symbol, symbol, instrument_id, storage)
    display_symbol = instrument.canonical_symbol

    if not allow_network:
        warnings.append("external network is disabled by default; pass --allow-network explicitly")
        _echo_backfill_result(
            display_symbol,
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

    adapter = MoexIssMarketDataAdapter()
    candles = asyncio.run(adapter.get_historical_candles(instrument, interval, start, end))
    candles_loaded = len(candles)
    if not dry_run:
        target_storage = _resolve_storage(storage)
        target_storage.save_candles(candles)
        candles_saved = len(candles)
    _echo_backfill_result(
        display_symbol,
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


@data_app.command("sync-moex-instruments")
def sync_moex_instruments(
    asset_class: Literal["futures"] = typer.Option("futures", "--asset-class"),
    storage: Literal["in-memory", "db"] = typer.Option("in-memory", "--storage"),
    dry_run: bool = typer.Option(True, "--dry-run/--write"),
    allow_network: bool = typer.Option(False, "--allow-network"),
) -> None:
    warnings: list[str] = []
    if not allow_network:
        warnings.append("external network is disabled by default; pass --allow-network explicitly")
        _echo_json(
            {
                "status": "skipped",
                "asset_class": asset_class,
                "storage": storage,
                "dry_run": dry_run,
                "allow_network": allow_network,
                "instruments_count": 0,
                "contract_specs_count": 0,
                "warnings": warnings,
            }
        )
        return

    service = MoexIssInstrumentsService()
    if dry_run:
        instruments = asyncio.run(service.get_futures_instruments())
        contract_specs = asyncio.run(service.get_futures_contract_specs())
        status = "dry_run"
        instruments_count = len(instruments)
        contract_specs_count = len(contract_specs)
    else:
        sync_result = asyncio.run(service.sync_futures_instruments(_resolve_storage(storage)))
        status = "saved"
        instruments_count = sync_result.instruments_count
        contract_specs_count = sync_result.contract_specs_count

    _echo_json(
        {
            "status": status,
            "asset_class": asset_class,
            "storage": storage,
            "dry_run": dry_run,
            "allow_network": allow_network,
            "instruments_count": instruments_count,
            "contract_specs_count": contract_specs_count,
            "warnings": warnings,
        }
    )


@data_app.command("quality")
def data_quality(
    canonical_symbol: str = typer.Option(..., "--canonical-symbol"),
    interval: str = typer.Option("1m", "--interval"),
    from_date: str = typer.Option(..., "--from"),
    to_date: str = typer.Option(..., "--to"),
    storage: Literal["in-memory", "db"] = typer.Option("in-memory", "--storage"),
) -> None:
    target_storage = _resolve_storage(storage)
    instrument = target_storage.get_instrument_by_canonical_symbol(canonical_symbol)
    if instrument is None:
        raise typer.BadParameter(f"instrument not found: {canonical_symbol}")
    start = _parse_cli_date(from_date)
    end = _parse_cli_date(to_date)
    candles = target_storage.load_candles(instrument.id, interval, start, end)
    report = analyze_candle_series(candles, interval)
    _echo_json(
        {
            "canonical_symbol": canonical_symbol,
            "instrument_id": instrument.id,
            "interval": interval,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "report": _model_json(report),
        }
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


def _resolve_moex_backfill_instrument(
    canonical_symbol: str | None,
    symbol: str | None,
    instrument_id: str | None,
    storage: str,
) -> Instrument:
    if canonical_symbol is not None:
        instrument = _resolve_storage(storage).get_instrument_by_canonical_symbol(canonical_symbol)
        if instrument is None:
            raise typer.BadParameter(f"instrument not found: {canonical_symbol}")
        return instrument
    if symbol is None or instrument_id is None:
        raise typer.BadParameter("pass either --canonical-symbol or both --symbol and --instrument-id")
    return _moex_instrument(symbol, instrument_id)


def _parse_cli_date(value: str) -> datetime:
    return datetime.combine(date.fromisoformat(value), time.min, tzinfo=UTC)


def _parse_decimal_option(value: str, option_name: str) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise typer.BadParameter(f"{option_name} must be Decimal-compatible") from exc


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


def _resolve_storage(storage_name: str) -> StoragePort:
    if storage_name == "in-memory":
        return InMemoryStorage()
    if storage_name == "db":
        return SQLAlchemyStorage.from_url(AppConfig().database_url)
    raise typer.BadParameter(f"unsupported storage: {storage_name}")


def _optional_venue(value: str | None) -> Venue | None:
    return Venue(value) if value is not None else None


def _optional_asset_class(value: str | None) -> AssetClass | None:
    return AssetClass(value) if value is not None else None


def _model_json(model: DomainModel) -> dict[str, object]:
    payload = model.model_dump(mode="json")
    return payload if isinstance(payload, dict) else {}


def _contract_spec_json(contract_spec: ContractSpec | None) -> dict[str, object] | None:
    return _model_json(contract_spec) if contract_spec is not None else None


def _echo_json(payload: dict[str, object]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


app.add_typer(config_app, name="config")
app.add_typer(risk_app, name="risk")
app.add_typer(backtest_app, name="backtest")
app.add_typer(db_app, name="db")
app.add_typer(data_app, name="data")
app.add_typer(instruments_app, name="instruments")


if __name__ == "__main__":
    app()
