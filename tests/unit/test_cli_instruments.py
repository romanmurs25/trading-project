import json
from decimal import Decimal

from adapters.moex_iss.instruments import MoexInstrumentSyncResult
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import ContractSpec, Instrument
from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


class FakeMoexInstrumentsService:
    calls = 0

    async def sync_futures_instruments(self, storage: InMemoryStorage) -> MoexInstrumentSyncResult:
        type(self).calls += 1
        storage.save_instrument(make_instrument("moex:SiH6", "SiH6"))
        storage.save_contract_spec(make_contract_spec("moex:SiH6"))
        return MoexInstrumentSyncResult(instruments_count=1, contract_specs_count=1)


def make_instrument(instrument_id: str = "moex:SiH6", native_symbol: str = "SiH6") -> Instrument:
    return Instrument(
        id=instrument_id,
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=native_symbol,
        canonical_symbol=f"MOEX:{native_symbol}",
        name="USD/RUB Futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def make_contract_spec(instrument_id: str = "moex:SiH6") -> ContractSpec:
    return ContractSpec(
        instrument_id=instrument_id,
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def test_cli_instruments_list_reads_storage(monkeypatch) -> None:
    storage = InMemoryStorage()
    storage.save_instruments(
        [
            make_instrument("moex:SiH6", "SiH6"),
            make_instrument("moex:BRH6", "BRH6"),
        ]
    )
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        ["instruments", "list", "--venue", "MOEX", "--asset-class", "FUTURES"],
    )

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert [item["canonical_symbol"] for item in body["instruments"]] == ["MOEX:BRH6", "MOEX:SiH6"]


def test_cli_instruments_get_reads_by_canonical_symbol(monkeypatch) -> None:
    storage = InMemoryStorage()
    storage.save_instrument(make_instrument())
    storage.save_contract_spec(make_contract_spec())
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(cli_main.app, ["instruments", "get", "--canonical-symbol", "MOEX:SiH6"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["instrument"]["id"] == "moex:SiH6"
    assert body["contract_spec"]["instrument_id"] == "moex:SiH6"


def test_cli_sync_moex_instruments_defaults_to_no_network() -> None:
    result = runner.invoke(cli_main.app, ["data", "sync-moex-instruments"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["status"] == "skipped"
    assert body["allow_network"] is False
    assert body["dry_run"] is True
    assert body["instruments_count"] == 0
    assert body["contract_specs_count"] == 0


def test_cli_sync_moex_instruments_writes_with_mocked_service(monkeypatch) -> None:
    FakeMoexInstrumentsService.calls = 0
    storage = InMemoryStorage()
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)
    monkeypatch.setattr(cli_main, "MoexIssInstrumentsService", FakeMoexInstrumentsService)

    result = runner.invoke(cli_main.app, ["data", "sync-moex-instruments", "--allow-network", "--write"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert FakeMoexInstrumentsService.calls == 1
    assert body["status"] == "saved"
    assert body["instruments_count"] == 1
    assert storage.get_instrument_by_canonical_symbol("MOEX:SiH6") is not None
