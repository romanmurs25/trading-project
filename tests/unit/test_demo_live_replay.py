from datetime import UTC, datetime
from decimal import Decimal

from adapters.demo.live_replay import replay_demo_candles_once
from storage.in_memory import InMemoryStorage
from trading_core.live_data.models import (
    MarketDataEventType,
    MarketDataIngestionStatus,
    MarketDataSource,
)


def test_demo_live_replay_persists_read_only_snapshots_and_events() -> None:
    storage = InMemoryStorage()

    result = replay_demo_candles_once(
        storage=storage,
        canonical_symbol="MOEX:SiH6",
        interval="1m",
        count=3,
        start=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
    )

    assert result.run.source == MarketDataSource.DEMO_REPLAY
    assert result.run.status == MarketDataIngestionStatus.STOPPED
    assert result.run.read_only is True
    assert result.run.allow_network is False
    assert len(result.snapshots) == 3
    assert result.snapshots[0].close == Decimal("100.5")
    assert storage.get_latest_live_candle_snapshot("MOEX:SiH6", "1m") is not None
    assert {event.event_type for event in storage.list_market_data_events()} == {
        MarketDataEventType.INGESTION_STARTED,
        MarketDataEventType.CANDLE_CLOSED,
        MarketDataEventType.INGESTION_STOPPED,
    }
