from decimal import Decimal

from adapters.moex_iss.instruments import MoexInstrumentSyncResult
from fastapi.testclient import TestClient
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import ContractSpec, Instrument

from apps.api.main import create_app


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


def test_api_instruments_list_and_get_from_storage() -> None:
    app = create_app()
    storage = InMemoryStorage()
    storage.save_instruments([make_instrument("moex:SiH6", "SiH6"), make_instrument("moex:BRH6", "BRH6")])
    storage.save_contract_spec(make_contract_spec())
    app.state.storage = storage
    client = TestClient(app)

    list_response = client.get("/api/instruments", params={"venue": "MOEX", "asset_class": "FUTURES"})
    get_response = client.get("/api/instruments/moex:SiH6")
    symbol_response = client.get("/api/instruments/by-symbol/MOEX:SiH6")

    assert list_response.status_code == 200
    assert [item["canonical_symbol"] for item in list_response.json()] == ["MOEX:BRH6", "MOEX:SiH6"]
    assert get_response.status_code == 200
    assert get_response.json()["instrument"]["canonical_symbol"] == "MOEX:SiH6"
    assert symbol_response.status_code == 200
    assert symbol_response.json()["contract_spec"]["instrument_id"] == "moex:SiH6"


def test_api_instruments_get_returns_404_for_unknown_symbol() -> None:
    client = TestClient(create_app())

    response = client.get("/api/instruments/by-symbol/MOEX:UNKNOWN")

    assert response.status_code == 404


def test_api_sync_moex_instruments_defaults_to_no_network() -> None:
    client = TestClient(create_app())

    response = client.post("/api/instruments/sync/moex", json={})

    assert response.status_code == 200
    assert response.json() == {
        "status": "skipped",
        "instruments_count": 0,
        "contract_specs_count": 0,
        "dry_run": True,
        "allow_network": False,
        "warnings": ["external network is disabled by default; pass allow_network=true explicitly"],
    }


def test_api_sync_moex_instruments_writes_with_mocked_service() -> None:
    FakeMoexInstrumentsService.calls = 0
    app = create_app()
    app.state.storage = InMemoryStorage()
    app.state.moex_instruments_service = FakeMoexInstrumentsService()
    client = TestClient(app)

    response = client.post(
        "/api/instruments/sync/moex",
        json={"allow_network": True, "dry_run": False},
    )

    assert response.status_code == 200
    assert FakeMoexInstrumentsService.calls == 1
    assert response.json()["status"] == "saved"
    assert response.json()["instruments_count"] == 1
    assert app.state.storage.get_instrument_by_canonical_symbol("MOEX:SiH6") is not None
