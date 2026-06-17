from datetime import UTC, datetime, timedelta
from decimal import Decimal

from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument
from trading_core.live_data.ingestion import ReadOnlyMarketDataIngestionService
from trading_core.live_data.models import (
    MarketDataEventType,
    MarketDataFreshness,
    MarketDataIngestionStatus,
    MarketDataSource,
)


def ts(minute: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, minute, tzinfo=UTC)


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


def candle(minute: int = 0) -> Candle:
    return Candle(
        instrument_id="moex:SiH6",
        venue=Venue.MOEX,
        interval="1m",
        ts_start=ts(minute),
        ts_end=ts(minute + 1),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=Decimal("10"),
        value=Decimal("1010"),
        trades_count=5,
        source="demo-live-replay",
    )


def test_ingestion_service_starts_read_only_run_and_records_candles() -> None:
    storage = InMemoryStorage()
    service = ReadOnlyMarketDataIngestionService(storage=storage, clock=lambda: ts())

    run = service.start_run(
        source=MarketDataSource.DEMO_REPLAY,
        venue=Venue.MOEX,
        instruments=["MOEX:SiH6"],
        interval="1m",
        allow_network=False,
    )
    snapshots = service.ingest_candles(
        run_id=run.id,
        source=MarketDataSource.DEMO_REPLAY,
        instrument=instrument(),
        candles=[candle()],
    )

    updated_run = storage.get_market_data_ingestion_run(run.id)
    events = storage.list_market_data_events()
    assert updated_run is not None
    assert updated_run.read_only is True
    assert updated_run.allow_network is False
    assert updated_run.status == MarketDataIngestionStatus.RUNNING
    assert updated_run.candles_count == 1
    assert snapshots[0].canonical_symbol == "MOEX:SiH6"
    assert snapshots[0].freshness == MarketDataFreshness.FRESH
    assert {event.event_type for event in events} == {
        MarketDataEventType.INGESTION_STARTED,
        MarketDataEventType.CANDLE_CLOSED,
    }


def test_ingestion_service_state_recomputes_stale_candles_from_current_time() -> None:
    storage = InMemoryStorage()
    service = ReadOnlyMarketDataIngestionService(
        storage=storage,
        clock=lambda: ts(2),
        stale_after_seconds=30,
    )
    run = service.start_run(
        source=MarketDataSource.DEMO_REPLAY,
        venue=Venue.MOEX,
        instruments=["MOEX:SiH6"],
        interval="1m",
    )
    service.ingest_candles(
        run_id=run.id,
        source=MarketDataSource.DEMO_REPLAY,
        instrument=instrument(),
        candles=[candle()],
    )
    stored = storage.get_latest_live_candle_snapshot("MOEX:SiH6", "1m")
    assert stored is not None
    stale_snapshot = stored.model_copy(update={"updated_at": ts() - timedelta(minutes=5)})
    storage.save_live_candle_snapshot(stale_snapshot)

    state = service.state()

    assert state.status == MarketDataIngestionStatus.RUNNING
    assert state.latest_candles_count == 1
    assert state.stale_candles_count == 1
