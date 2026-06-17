import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, ContractSpec, Instrument
from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


def instrument(symbol: str, expiry: date) -> Instrument:
    return Instrument(
        id=f"moex:{symbol}",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=symbol,
        canonical_symbol=f"MOEX:{symbol}",
        name=symbol,
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry,
    )


def spec(symbol: str, expiry: date) -> ContractSpec:
    return ContractSpec(
        instrument_id=f"moex:{symbol}",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry,
        last_trade_date=expiry,
        underlying_symbol="Si",
    )


def candle(symbol: str, ts_start: datetime, close: str) -> Candle:
    return Candle(
        instrument_id=f"moex:{symbol}",
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


def make_storage() -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.save_instruments([instrument("SiH6", date(2026, 3, 19)), instrument("SiM6", date(2026, 6, 18))])
    storage.save_contract_spec(spec("SiH6", date(2026, 3, 19)))
    storage.save_contract_spec(spec("SiM6", date(2026, 6, 18)))
    storage.save_candles(
        [
            candle("SiH6", datetime(2026, 3, 13, 7, 0, tzinfo=UTC), "100"),
            candle("SiM6", datetime(2026, 3, 16, 7, 0, tzinfo=UTC), "200"),
        ]
    )
    return storage


def test_cli_build_continuous_builds_and_writes(monkeypatch) -> None:
    storage = make_storage()
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        [
            "data",
            "build-continuous",
            "--underlying",
            "Si",
            "--interval",
            "1m",
            "--from",
            "2026-03-13",
            "--to",
            "2026-03-17",
            "--write",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["canonical_symbol"] == "MOEX:Si:CONT"
    assert payload["candles_count"] == 2
    assert payload["components_count"] == 2
    assert payload["written"] is True
    assert storage.get_continuous_series_by_canonical_symbol("MOEX:Si:CONT") is not None
