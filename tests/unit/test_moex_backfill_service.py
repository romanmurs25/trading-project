from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from adapters.moex_iss.backfill import MoexBackfillService
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument


class FakeMarketDataAdapter:
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = candles
        self.calls = 0

    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        self.calls += 1
        return self.candles


def make_instrument() -> Instrument:
    return Instrument(
        id="moex-si",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol="SiH6",
        canonical_symbol="MOEX:SIH6",
        name="Si futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def make_candle(instrument_id: str) -> Candle:
    start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
    return Candle(
        instrument_id=instrument_id,
        venue=Venue.MOEX,
        interval="1m",
        ts_start=start,
        ts_end=start + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal("10"),
        value=Decimal("1000"),
        source="moex-iss",
    )


@pytest.mark.asyncio
async def test_moex_backfill_service_saves_candles_and_returns_count() -> None:
    instrument = make_instrument()
    candle = make_candle(instrument.id)
    adapter = FakeMarketDataAdapter([candle])
    storage = InMemoryStorage()
    service = MoexBackfillService(adapter)

    saved = await service.backfill_candles(
        instrument,
        "1m",
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 2, tzinfo=UTC),
        storage,
    )

    assert saved == 1
    assert adapter.calls == 1
    assert storage.candles == [candle]
