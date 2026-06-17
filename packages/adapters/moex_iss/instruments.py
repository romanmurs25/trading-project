from dataclasses import dataclass, field
from typing import Protocol

from trading_core.config import AppConfig
from trading_core.domain.models import ContractSpec, Instrument
from trading_core.ports.storage import StoragePort

from adapters.moex_iss.client import MoexIssClient, MoexPayload
from adapters.moex_iss.instrument_mapper import map_futures_contract_specs, map_futures_instruments

FUTURES_SECURITIES_PATH = "engines/futures/markets/forts/securities.json"
FUTURES_SECURITIES_PARAMS = {"iss.meta": "off", "iss.only": "securities"}


class MoexInstrumentsClientProtocol(Protocol):
    async def get(self, path: str, params: dict[str, str] | None = None) -> MoexPayload: ...


@dataclass(frozen=True)
class MoexInstrumentSyncResult:
    instruments_count: int
    contract_specs_count: int


@dataclass
class MoexIssInstrumentsService:
    client: MoexInstrumentsClientProtocol | None = None
    config: AppConfig = field(default_factory=AppConfig)

    async def get_futures_instruments(self) -> list[Instrument]:
        payload = await self._get_futures_payload()
        return map_futures_instruments(payload)

    async def get_futures_contract_specs(self) -> list[ContractSpec]:
        payload = await self._get_futures_payload()
        return map_futures_contract_specs(payload)

    async def sync_futures_instruments(self, storage: StoragePort) -> MoexInstrumentSyncResult:
        payload = await self._get_futures_payload()
        instruments = map_futures_instruments(payload)
        contract_specs = map_futures_contract_specs(payload)
        storage.save_instruments(instruments)
        for contract_spec in contract_specs:
            storage.save_contract_spec(contract_spec)
        return MoexInstrumentSyncResult(
            instruments_count=len(instruments),
            contract_specs_count=len(contract_specs),
        )

    async def _get_futures_payload(self) -> MoexPayload:
        client = self.client or MoexIssClient(base_url=self.config.moex_iss_base_url)
        return await client.get(FUTURES_SECURITIES_PATH, params=FUTURES_SECURITIES_PARAMS)
