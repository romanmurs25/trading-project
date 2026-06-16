from datetime import datetime

from trading_core.domain.models import Candle, Instrument


class BybitMarketDataAdapter:
    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        raise NotImplementedError("TODO: implement read-only/testnet-safe Bybit market data adapter")

    async def stream_klines(self, instrument: Instrument, interval: str) -> None:
        raise NotImplementedError("TODO: implement WebSocket kline skeleton without tests hitting network")
