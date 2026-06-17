import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument
from trading_core.market.calendar import MarketCalendarService
from trading_core.market.moex_templates import default_moex_futures_session_templates
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
    calendar = MarketCalendarService(default_moex_futures_session_templates())
    timestamps = calendar.expected_candle_timestamps(
        datetime(2026, 1, 5, tzinfo=UTC),
        datetime(2026, 1, 7, tzinfo=UTC),
        "1m",
    )
    candles = [candle(ts, str(100 + index)) for index, ts in enumerate(timestamps)]
    storage.save_candles(candles)
    return storage


def candle(ts_start: datetime, close: str) -> Candle:
    return Candle(
        instrument_id="moex:SiH6",
        venue=Venue.MOEX,
        interval="1m",
        ts_start=ts_start,
        ts_end=ts_start + timedelta(minutes=1),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal("100"),
        source="test",
    )


def test_cli_research_run_session_aware_quality_succeeds_on_overnight_gap(monkeypatch) -> None:
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
            "2026-01-05",
            "--to",
            "2026-01-07",
            "--param",
            "opening_range_minutes=2",
            "--session-aware-quality",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["completed_backtests"] == 1
    research_result = storage.list_research_backtest_results(payload["research_run_id"])[0]
    assert research_result.quality_report["quality_mode"] == "session_aware"
