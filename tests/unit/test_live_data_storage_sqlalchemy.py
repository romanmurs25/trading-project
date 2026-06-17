from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from storage.sqlalchemy_models import Base
from storage.sqlalchemy_repositories import SQLAlchemyStorage
from trading_core.domain.enums import Venue
from trading_core.live_data.models import (
    LiveCandleSnapshot,
    MarketDataEvent,
    MarketDataEventType,
    MarketDataFreshness,
    MarketDataIngestionRun,
    MarketDataIngestionStatus,
    MarketDataSource,
)


def make_storage() -> SQLAlchemyStorage:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SQLAlchemyStorage(sessionmaker(bind=engine))


def ts(minute: int = 0) -> datetime:
    return datetime(2026, 1, 1, 10, minute, tzinfo=UTC)


def run() -> MarketDataIngestionRun:
    return MarketDataIngestionRun(
        id="run-1",
        source=MarketDataSource.DEMO_REPLAY,
        status=MarketDataIngestionStatus.RUNNING,
        venue=Venue.MOEX,
        instruments=["MOEX:SiH6"],
        interval="1m",
        started_at=ts(),
        read_only=True,
        allow_network=False,
    )


def event(event_id: str = "event-1") -> MarketDataEvent:
    return MarketDataEvent(
        id=event_id,
        source=MarketDataSource.DEMO_REPLAY,
        event_type=MarketDataEventType.CANDLE_RECEIVED,
        venue=Venue.MOEX,
        instrument_id="moex:SiH6",
        canonical_symbol="MOEX:SiH6",
        interval="1m",
        ts=ts(),
        received_at=ts(),
        payload={"close": "100"},
    )


def snapshot(close: str = "100", updated_at: datetime | None = None) -> LiveCandleSnapshot:
    return LiveCandleSnapshot(
        id="snapshot-1",
        source=MarketDataSource.DEMO_REPLAY,
        venue=Venue.MOEX,
        instrument_id="moex:SiH6",
        canonical_symbol="MOEX:SiH6",
        interval="1m",
        ts_start=ts(),
        ts_end=ts() + timedelta(minutes=1),
        open=Decimal("99"),
        high=Decimal("101"),
        low=Decimal("98"),
        close=Decimal(close),
        volume=Decimal("1000"),
        updated_at=updated_at or ts(),
        is_closed=True,
        freshness=MarketDataFreshness.FRESH,
    )


def test_sqlalchemy_market_data_runs_events_and_snapshots() -> None:
    storage = make_storage()

    storage.save_market_data_ingestion_run(run())
    storage.save_market_data_event(event())
    storage.save_live_candle_snapshot(snapshot())

    assert storage.get_market_data_ingestion_run("run-1") == run()
    assert storage.list_market_data_ingestion_runs() == [run()]
    assert storage.list_market_data_events() == [event()]
    assert storage.list_live_candle_snapshots() == [snapshot()]


def test_sqlalchemy_live_candle_snapshot_upserts_by_market_key() -> None:
    storage = make_storage()
    storage.save_live_candle_snapshot(snapshot("100", ts()))
    updated = snapshot("105", ts(1))

    storage.save_live_candle_snapshot(updated)

    assert storage.list_live_candle_snapshots() == [updated]
    assert storage.get_latest_live_candle_snapshot("MOEX:SiH6", "1m") == updated
