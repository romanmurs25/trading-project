import json
from datetime import date
from decimal import Decimal

from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import ContractSpec, Instrument
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


def make_storage() -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.save_instruments([instrument("SiM6", date(2026, 6, 18)), instrument("SiH6", date(2026, 3, 19))])
    storage.save_contract_spec(spec("SiM6", date(2026, 6, 18)))
    storage.save_contract_spec(spec("SiH6", date(2026, 3, 19)))
    return storage


def test_cli_futures_chain_sorts_contracts(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: make_storage())

    result = runner.invoke(cli_main.app, ["futures", "chain", "--underlying", "Si"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [contract["canonical_symbol"] for contract in payload["contracts"]] == ["MOEX:SiH6", "MOEX:SiM6"]


def test_cli_futures_select_front(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: make_storage())

    result = runner.invoke(
        cli_main.app,
        ["futures", "select-front", "--underlying", "Si", "--as-of", "2026-03-16"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["selected_canonical_symbol"] == "MOEX:SiM6"
