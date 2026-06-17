from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle, Instrument

from adapters.moex_iss.market_data_adapter import MoexIssMarketDataAdapter


class HistoricalCandleAdapter(Protocol):
    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]: ...


@dataclass
class MoexIssPollingMarketDataAdapter:
    historical_adapter: HistoricalCandleAdapter = field(default_factory=MoexIssMarketDataAdapter)

    async def poll_latest_candles_once(
        self,
        instrument: Instrument,
        interval: str,
        end: datetime,
        lookback_minutes: int = 5,
    ) -> list[Candle]:
        if end.tzinfo is None:
            raise DataValidationError("MOEX polling end timestamp must be timezone-aware")
        if lookback_minutes < 1:
            raise DataValidationError("MOEX polling lookback_minutes must be positive")
        start = end - timedelta(minutes=lookback_minutes)
        return await self.historical_adapter.get_historical_candles(
            instrument=instrument,
            interval=interval,
            start=start,
            end=end,
        )
