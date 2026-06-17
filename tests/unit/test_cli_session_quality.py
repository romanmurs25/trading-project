import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument
from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


def make_storage() -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.save_instrument(
        Instrument(
            id="moex:SiH6",
            venue=Venue.MOEX,
            asset_class=AssetClass.FUTURES,
            native_symbol="SiH6",
            canonical_symbol="MOEX:SiH6",
            name="Si",
            lot_size=Decimal("1"),
            tick_size=Decimal("1"),
            tick_value=Decimal("1"),
            currency="RUB",
        )
    )
    start = datetime(2026, 1, 5, 7, 0, tzinfo=UTC)
    storage.save_candles(
        [
            Candle(
                instrument_id="moex:SiH6",
                venue=Venue.MOEX,
                interval="1m",
                ts_start=start + timedelta(minutes=i),
                ts_end=start + timedelta(minutes=i + 1),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("100"),
                source="test",
            )
            for i in range(3)
        ]
    )
    return storage


def test_cli_session_aware_quality_outputs_report(monkeypatch) -> None:
    storage = make_storage()
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        [
            "data",
            "quality-session-aware",
            "--canonical-symbol",
            "MOEX:SiH6",
            "--interval",
            "1m",
            "--from",
            "2026-01-05",
            "--to",
            "2026-01-06",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["report"]["candles_count"] == 3
    assert payload["report"]["session_counts"]["MAIN"] == 3
