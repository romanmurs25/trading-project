from dataclasses import dataclass, field
from datetime import datetime

from trading_core.domain.models import Instrument
from trading_core.ports.market_data import MarketDataPort
from trading_core.ports.storage import StoragePort

from adapters.moex_iss.market_data_adapter import MoexIssMarketDataAdapter


@dataclass
class MoexBackfillService:
    market_data_adapter: MarketDataPort = field(default_factory=MoexIssMarketDataAdapter)

    async def backfill_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
        storage: StoragePort,
    ) -> int:
        candles = await self.market_data_adapter.get_historical_candles(instrument, interval, start, end)
        storage.save_candles(candles)
        return len(candles)
