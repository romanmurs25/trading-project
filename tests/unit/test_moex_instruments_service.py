from decimal import Decimal
from typing import Any

import pytest
from adapters.moex_iss.instruments import MoexIssInstrumentsService
from storage.in_memory import InMemoryStorage


class FakeMoexClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        self.calls.append((path, params or {}))
        return self.payload


def futures_payload() -> dict[str, object]:
    return {
        "securities": {
            "columns": ["SECID", "SECNAME", "LOTSIZE", "MINSTEP", "STEPPRICE", "FACEUNIT", "MATDATE"],
            "data": [
                ["SiH6", "USD/RUB Futures", "1", "1", "1", "RUB", "2026-03-19"],
                ["BRH6", "Brent Futures", "10", "0.01", "10", "RUB", "2026-03-02"],
            ],
        }
    }


@pytest.mark.asyncio
async def test_moex_instruments_service_loads_futures_instruments_without_real_http() -> None:
    client = FakeMoexClient(futures_payload())
    service = MoexIssInstrumentsService(client=client)

    instruments = await service.get_futures_instruments()

    assert [instrument.canonical_symbol for instrument in instruments] == ["MOEX:SiH6", "MOEX:BRH6"]
    assert instruments[1].lot_size == Decimal("10")
    assert client.calls == [
        (
            "engines/futures/markets/forts/securities.json",
            {"iss.meta": "off", "iss.only": "securities"},
        )
    ]


@pytest.mark.asyncio
async def test_moex_instruments_service_syncs_instruments_and_contract_specs() -> None:
    storage = InMemoryStorage()
    service = MoexIssInstrumentsService(client=FakeMoexClient(futures_payload()))

    result = await service.sync_futures_instruments(storage)

    assert result.instruments_count == 2
    assert result.contract_specs_count == 2
    assert storage.get_instrument_by_canonical_symbol("MOEX:SiH6") is not None
    assert storage.get_contract_spec("moex:BRH6") is not None


@pytest.mark.asyncio
async def test_moex_instruments_service_contract_specs_reuse_read_only_endpoint() -> None:
    service = MoexIssInstrumentsService(client=FakeMoexClient(futures_payload()))

    specs = await service.get_futures_contract_specs()

    assert [spec.instrument_id for spec in specs] == ["moex:SiH6", "moex:BRH6"]
