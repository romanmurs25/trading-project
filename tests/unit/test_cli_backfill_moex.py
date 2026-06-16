import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_core.domain.enums import Venue
from trading_core.domain.models import Candle, Instrument
from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


class FakeMoexAdapter:
    calls = 0

    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        type(self).calls += 1
        candle_start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
        return [
            Candle(
                instrument_id=instrument.id,
                venue=Venue.MOEX,
                interval=interval,
                ts_start=candle_start,
                ts_end=candle_start + timedelta(minutes=1),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
                volume=Decimal("10"),
                value=Decimal("1000"),
                source="fake-moex",
            )
        ]


def test_cli_backfill_moex_defaults_to_no_network_and_dry_run() -> None:
    result = runner.invoke(
        cli_main.app,
        [
            "data",
            "backfill-moex",
            "--symbol",
            "SiH6",
            "--instrument-id",
            "moex-si",
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
    assert body["allow_network"] is False
    assert body["dry_run"] is True
    assert body["candles_loaded"] == 0
    assert body["candles_saved"] == 0


def test_cli_backfill_moex_uses_mocked_adapter_when_network_explicitly_allowed(monkeypatch) -> None:
    FakeMoexAdapter.calls = 0
    monkeypatch.setattr(cli_main, "MoexIssMarketDataAdapter", FakeMoexAdapter)

    result = runner.invoke(
        cli_main.app,
        [
            "data",
            "backfill-moex",
            "--symbol",
            "SiH6",
            "--instrument-id",
            "moex-si",
            "--interval",
            "1m",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-02",
            "--allow-network",
            "--write",
            "--storage",
            "in-memory",
        ],
    )

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert FakeMoexAdapter.calls == 1
    assert body["allow_network"] is True
    assert body["dry_run"] is False
    assert body["candles_loaded"] == 1
    assert body["candles_saved"] == 1
