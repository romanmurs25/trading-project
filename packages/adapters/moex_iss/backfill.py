from datetime import datetime

from trading_core.domain.models import Candle, Instrument


class MoexBackfillService:
    async def backfill(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        raise NotImplementedError("TODO: implement read-only MOEX ISS backfill with pagination and retry")
