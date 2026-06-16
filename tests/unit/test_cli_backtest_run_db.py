import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument
from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


def make_instrument() -> Instrument:
    return Instrument(
        id="moex:SiH6",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol="SiH6",
        canonical_symbol="MOEX:SiH6",
        name="USD/RUB Futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def make_candles(instrument_id: str) -> list[Candle]:
    start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
    return [
        Candle(
            instrument_id=instrument_id,
            venue=Venue.MOEX,
            interval="1m",
            ts_start=start + timedelta(minutes=i),
            ts_end=start + timedelta(minutes=i + 1),
            open=Decimal("100") + Decimal(i),
            high=Decimal("101") + Decimal(i),
            low=Decimal("99") + Decimal(i),
            close=Decimal("100") + Decimal(i),
            volume=Decimal("1000"),
            source="test-db",
        )
        for i in range(6)
    ]


def test_cli_backtest_run_db_loads_storage_candles_and_saves_run(monkeypatch) -> None:
    storage = InMemoryStorage()
    instrument = make_instrument()
    storage.save_instrument(instrument)
    storage.save_candles(make_candles(instrument.id))
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        [
            "backtest",
            "run-db",
            "--strategy",
            "opening_range_breakout",
            "--canonical-symbol",
            "MOEX:SiH6",
            "--interval",
            "1m",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-02",
            "--initial-cash",
            "100000",
        ],
    )

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["strategy_id"] == "opening_range_breakout"
    assert body["canonical_symbol"] == "MOEX:SiH6"
    assert body["candles_count"] == 6
    assert Decimal(body["metrics"]["final_equity"]) > Decimal("0")
    assert len(storage.backtest_runs) == 1


def test_cli_backtest_run_db_rejects_unknown_instrument(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: InMemoryStorage())

    result = runner.invoke(
        cli_main.app,
        [
            "backtest",
            "run-db",
            "--strategy",
            "opening_range_breakout",
            "--canonical-symbol",
            "MOEX:UNKNOWN",
            "--interval",
            "1m",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-02",
        ],
    )

    assert result.exit_code != 0
    assert "instrument not found: MOEX:UNKNOWN" in result.output


def test_cli_backtest_run_db_rejects_missing_candles(monkeypatch) -> None:
    storage = InMemoryStorage()
    storage.save_instrument(make_instrument())
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        [
            "backtest",
            "run-db",
            "--strategy",
            "opening_range_breakout",
            "--canonical-symbol",
            "MOEX:SiH6",
            "--interval",
            "1m",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-02",
        ],
    )

    assert result.exit_code != 0
    assert "no candles found" in result.output
