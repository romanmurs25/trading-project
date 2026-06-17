import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument
from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


def make_storage(candles: list[Candle] | None = None) -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.save_instrument(
        Instrument(
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
    )
    storage.save_candles(candles if candles is not None else make_candles())
    return storage


def make_candles() -> list[Candle]:
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
        for i in range(8)
    ]


def test_cli_research_run_with_params(monkeypatch) -> None:
    storage = make_storage()
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        [
            "research",
            "run",
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
            "--param",
            "opening_range_minutes=2,3",
            "--param",
            "take_profit_r_multiple=1.5,2",
        ],
    )

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["parameter_combinations"] == 4
    assert body["completed_backtests"] == 4
    assert len(storage.research_runs) == 1


def test_cli_research_run_rejects_unknown_instrument(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: InMemoryStorage())

    result = runner.invoke(
        cli_main.app,
        [
            "research",
            "run",
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
    assert "instrument not found" in result.output


def test_cli_research_run_data_quality_failure_stops_run(monkeypatch) -> None:
    storage = make_storage([])
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        [
            "research",
            "run",
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

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["failed_backtests"] == 1
    assert storage.research_runs[0].status.value == "FAILED"
