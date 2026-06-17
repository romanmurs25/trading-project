from datetime import UTC, datetime
from decimal import Decimal

import pytest
from adapters.moex_iss.live_polling import MoexIssPollingMarketDataAdapter
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle, Instrument


def instrument() -> Instrument:
    return Instrument(
        id="moex:SiH6",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol="SiH6",
        canonical_symbol="MOEX:SiH6",
        name="Si futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
    )


def candle() -> Candle:
    return Candle(
        instrument_id="moex:SiH6",
        venue=Venue.MOEX,
        interval="1m",
        ts_start=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        ts_end=datetime(2026, 1, 1, 10, 1, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal("10"),
        source="fake-moex",
    )


class FakeHistoricalAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[datetime, datetime]] = []

    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        self.calls.append((start, end))
        return [candle()]


@pytest.mark.asyncio
async def test_moex_polling_once_uses_historical_adapter_without_execution_surface() -> None:
    fake = FakeHistoricalAdapter()
    adapter = MoexIssPollingMarketDataAdapter(historical_adapter=fake)
    end = datetime(2026, 1, 1, 10, 5, tzinfo=UTC)

    candles = await adapter.poll_latest_candles_once(
        instrument=instrument(),
        interval="1m",
        end=end,
        lookback_minutes=5,
    )

    assert candles == [candle()]
    assert fake.calls == [(datetime(2026, 1, 1, 10, 0, tzinfo=UTC), end)]
    assert not hasattr(adapter, "place_order")
    assert not hasattr(adapter, "submit_order")


@pytest.mark.asyncio
async def test_moex_polling_requires_timezone_aware_end() -> None:
    adapter = MoexIssPollingMarketDataAdapter(historical_adapter=FakeHistoricalAdapter())

    with pytest.raises(DataValidationError):
        await adapter.poll_latest_candles_once(
            instrument=instrument(),
            interval="1m",
            end=datetime(2026, 1, 1, 10, 5),
            lookback_minutes=5,
        )
