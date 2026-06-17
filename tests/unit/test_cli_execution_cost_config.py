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
                open=Decimal("100") + Decimal(i),
                high=Decimal("101") + Decimal(i),
                low=Decimal("99") + Decimal(i),
                close=Decimal("100") + Decimal(i),
                volume=Decimal("100"),
                source="test",
            )
            for i in range(5)
        ]
    )
    return storage


def test_cli_backtest_run_db_passes_execution_cost_config(monkeypatch) -> None:
    captured: dict[str, Decimal] = {}
    original_paper_broker = cli_main.PaperBroker

    def broker_factory(*args, **kwargs):
        captured["commission_rate"] = kwargs["commission_rate"]
        captured["slippage"] = kwargs["slippage"]
        return original_paper_broker(*args, **kwargs)

    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: make_storage())
    monkeypatch.setattr(cli_main, "PaperBroker", broker_factory)

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
            "2026-01-05",
            "--to",
            "2026-01-06",
            "--commission-rate",
            "0.001",
            "--slippage-ticks",
            "2",
            "--spread-bps",
            "5",
        ],
    )

    assert result.exit_code == 0
    assert captured == {"commission_rate": Decimal("0.001"), "slippage": Decimal("2")}
