from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument
from trading_core.live_data.ingestion import ReadOnlyMarketDataIngestionService
from trading_core.live_data.models import (
    LiveCandleSnapshot,
    MarketDataIngestionRun,
    MarketDataIngestionStatus,
    MarketDataSource,
)
from trading_core.ports.storage import StoragePort


@dataclass(frozen=True)
class DemoReplayResult:
    run: MarketDataIngestionRun
    snapshots: list[LiveCandleSnapshot]


def replay_demo_candles_once(
    storage: StoragePort,
    canonical_symbol: str = "MOEX:SiH6",
    interval: str = "1m",
    count: int = 20,
    start: datetime | None = None,
) -> DemoReplayResult:
    started_at = (start or datetime.now(UTC)).astimezone(UTC)
    instrument = demo_instrument(canonical_symbol)
    candles = generate_demo_candles(instrument, interval, started_at, count)
    service = ReadOnlyMarketDataIngestionService(storage=storage, clock=lambda: started_at)
    run = service.start_run(
        source=MarketDataSource.DEMO_REPLAY,
        venue=instrument.venue,
        instruments=[instrument.canonical_symbol],
        interval=interval,
        allow_network=False,
        metadata={"source": "demo-live-replay"},
    )
    snapshots = service.ingest_candles(
        run_id=run.id,
        source=MarketDataSource.DEMO_REPLAY,
        instrument=instrument,
        candles=candles,
    )
    stopped = service.stop_run(run.id, status=MarketDataIngestionStatus.STOPPED)
    return DemoReplayResult(run=stopped, snapshots=snapshots)


def demo_instrument(canonical_symbol: str = "MOEX:SiH6") -> Instrument:
    venue_value, native_symbol = canonical_symbol.split(":", maxsplit=1)
    return Instrument(
        id=f"{venue_value.lower()}:{native_symbol}",
        venue=Venue(venue_value),
        asset_class=AssetClass.FUTURES,
        native_symbol=native_symbol,
        canonical_symbol=canonical_symbol,
        name=f"Demo {native_symbol} futures",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        metadata={"source": "demo-live-replay"},
    )


def generate_demo_candles(
    instrument: Instrument,
    interval: str,
    start: datetime,
    count: int,
) -> list[Candle]:
    if count < 1:
        return []
    duration = _interval_duration(interval)
    base = Decimal("100")
    candles: list[Candle] = []
    for index in range(count):
        ts_start = start + duration * index
        open_price = base + Decimal(index)
        close_price = open_price + Decimal("0.5")
        candles.append(
            Candle(
                instrument_id=instrument.id,
                venue=instrument.venue,
                interval=interval,
                ts_start=ts_start,
                ts_end=ts_start + duration,
                open=open_price,
                high=close_price + Decimal("0.5"),
                low=open_price - Decimal("0.5"),
                close=close_price,
                volume=Decimal("10") + Decimal(index),
                value=close_price * (Decimal("10") + Decimal(index)),
                trades_count=10 + index,
                source="demo-live-replay",
            )
        )
    return candles


def _interval_duration(interval: str) -> timedelta:
    if interval.endswith("m"):
        return timedelta(minutes=int(interval[:-1]))
    if interval.endswith("h"):
        return timedelta(hours=int(interval[:-1]))
    if interval.endswith("d"):
        return timedelta(days=int(interval[:-1]))
    return timedelta(minutes=1)
