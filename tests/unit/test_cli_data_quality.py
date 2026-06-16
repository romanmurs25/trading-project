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


def make_candle(minute: int, volume: Decimal = Decimal("100")) -> Candle:
    start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return Candle(
        instrument_id="moex:SiH6",
        venue=Venue.MOEX,
        interval="1m",
        ts_start=start,
        ts_end=start + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=volume,
        source="test-db",
    )


def test_cli_data_quality_loads_candles_from_storage(monkeypatch) -> None:
    storage = InMemoryStorage()
    storage.save_instrument(make_instrument())
    storage.save_candles([make_candle(0), make_candle(2, Decimal("0"))])
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        [
            "data",
            "quality",
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
    assert body["canonical_symbol"] == "MOEX:SiH6"
    assert body["report"]["candles_count"] == 2
    assert body["report"]["missing_intervals_count"] == 1
    assert body["report"]["zero_volume_count"] == 1


def test_cli_data_quality_rejects_unknown_instrument(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: InMemoryStorage())

    result = runner.invoke(
        cli_main.app,
        [
            "data",
            "quality",
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
