from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import Protocol

from trading_core.domain.models import Candle, Instrument, OrderBookSnapshot, TickTrade


class MarketDataPort(Protocol):
    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]: ...

    def stream_candles(
        self,
        instruments: Sequence[Instrument],
        interval: str,
    ) -> AsyncIterator[Candle]: ...

    async def get_order_book(self, instrument: Instrument) -> OrderBookSnapshot: ...

    async def get_last_trade(self, instrument: Instrument) -> TickTrade: ...

    async def get_trading_status(self, instrument: Instrument) -> str: ...
