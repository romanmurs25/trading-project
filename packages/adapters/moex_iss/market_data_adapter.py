from datetime import datetime

from trading_core.domain.models import Candle, Instrument


class MoexIssMarketDataAdapter:
    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        raise NotImplementedError("TODO: implement read-only MOEX ISS market data adapter")
