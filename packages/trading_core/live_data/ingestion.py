from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from trading_core.domain.enums import Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle, Instrument
from trading_core.live_data.models import (
    LiveCandleSnapshot,
    MarketDataEvent,
    MarketDataEventType,
    MarketDataFreshness,
    MarketDataIngestionRun,
    MarketDataIngestionStatus,
    MarketDataSource,
    MarketDataState,
)
from trading_core.live_data.state import classify_freshness
from trading_core.ports.storage import StoragePort


class ReadOnlyMarketDataIngestionService:
    def __init__(
        self,
        storage: StoragePort,
        clock: Callable[[], datetime] | None = None,
        stale_after_seconds: int = 60,
    ) -> None:
        self.storage = storage
        self.clock = clock or (lambda: datetime.now(UTC))
        self.stale_after_seconds = stale_after_seconds

    def start_run(
        self,
        source: MarketDataSource,
        venue: Venue,
        instruments: list[str],
        interval: str,
        allow_network: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> MarketDataIngestionRun:
        now = self._now()
        run = MarketDataIngestionRun(
            source=source,
            status=MarketDataIngestionStatus.RUNNING,
            venue=venue,
            instruments=instruments,
            interval=interval,
            started_at=now,
            last_event_at=now,
            events_count=1,
            read_only=True,
            allow_network=allow_network,
            metadata=metadata or {},
        )
        self.storage.save_market_data_ingestion_run(run)
        self.storage.save_market_data_event(
            MarketDataEvent(
                source=source,
                event_type=MarketDataEventType.INGESTION_STARTED,
                venue=venue,
                instrument_id=",".join(instruments),
                canonical_symbol=",".join(instruments),
                interval=interval,
                ts=now,
                received_at=now,
                payload={"run_id": run.id, "read_only": True, "allow_network": allow_network},
                metadata=metadata or {},
            )
        )
        return run

    def stop_run(
        self,
        run_id: str,
        status: MarketDataIngestionStatus = MarketDataIngestionStatus.STOPPED,
    ) -> MarketDataIngestionRun:
        run = self._require_run(run_id)
        now = self._now()
        stopped = run.model_copy(
            update={
                "status": status,
                "stopped_at": now,
                "last_event_at": now,
                "events_count": run.events_count + 1,
            }
        )
        self.storage.save_market_data_ingestion_run(stopped)
        self.storage.save_market_data_event(
            MarketDataEvent(
                source=stopped.source,
                event_type=MarketDataEventType.INGESTION_STOPPED,
                venue=stopped.venue,
                instrument_id=",".join(stopped.instruments),
                canonical_symbol=",".join(stopped.instruments),
                interval=stopped.interval,
                ts=now,
                received_at=now,
                payload={"run_id": run_id, "status": status.value},
            )
        )
        return stopped

    def record_error(
        self,
        run_id: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> MarketDataEvent:
        run = self._require_run(run_id)
        now = self._now()
        event = MarketDataEvent(
            source=run.source,
            event_type=MarketDataEventType.INGESTION_ERROR,
            venue=run.venue,
            instrument_id=",".join(run.instruments),
            canonical_symbol=",".join(run.instruments),
            interval=run.interval,
            ts=now,
            received_at=now,
            payload={"run_id": run_id, "message": message},
            metadata=metadata or {},
        )
        updated = run.model_copy(
            update={
                "status": MarketDataIngestionStatus.FAILED,
                "last_event_at": now,
                "events_count": run.events_count + 1,
                "errors_count": run.errors_count + 1,
            }
        )
        self.storage.save_market_data_ingestion_run(updated)
        self.storage.save_market_data_event(event)
        return event

    def ingest_candles(
        self,
        run_id: str,
        source: MarketDataSource,
        instrument: Instrument,
        candles: list[Candle],
        is_closed: bool = True,
    ) -> list[LiveCandleSnapshot]:
        run = self._require_run(run_id)
        if run.source != source:
            raise DataValidationError("run source does not match candle source")
        now = self._now()
        snapshots = [
            self._snapshot(source, instrument, candle, now, is_closed)
            for candle in candles
        ]
        events = [
            self._event(source, instrument, candle, now, is_closed, run_id)
            for candle in candles
        ]
        self.storage.save_live_candle_snapshots(snapshots)
        self.storage.save_market_data_events(events)
        self.storage.save_market_data_ingestion_run(
            run.model_copy(
                update={
                    "last_event_at": now if events else run.last_event_at,
                    "events_count": run.events_count + len(events),
                    "candles_count": run.candles_count + len(snapshots),
                }
            )
        )
        return snapshots

    def state(self) -> MarketDataState:
        now = self._now()
        runs = self.storage.list_market_data_ingestion_runs(limit=100)
        active_runs = [run for run in runs if run.status == MarketDataIngestionStatus.RUNNING]
        snapshots = self.storage.list_live_candle_snapshots(limit=10_000)
        events = self.storage.list_market_data_events(limit=1)
        latest_event_at = events[0].received_at if events else None
        stale_count = sum(
            1
            for snapshot in snapshots
            if classify_freshness(snapshot.updated_at, now, self.stale_after_seconds)
            == MarketDataFreshness.STALE
        )
        status = MarketDataIngestionStatus.RUNNING if active_runs else MarketDataIngestionStatus.IDLE
        sources = sorted({run.source for run in runs}, key=lambda source: source.value)
        return MarketDataState(
            status=status,
            sources=sources,
            active_runs=active_runs,
            latest_event_at=latest_event_at,
            latest_candles_count=len(snapshots),
            stale_candles_count=stale_count,
            warnings=[] if snapshots else ["no live candle snapshots"],
        )

    def with_current_freshness(self, snapshot: LiveCandleSnapshot) -> LiveCandleSnapshot:
        return snapshot.model_copy(
            update={
                "freshness": classify_freshness(
                    snapshot.updated_at,
                    self._now(),
                    self.stale_after_seconds,
                )
            }
        )

    def _snapshot(
        self,
        source: MarketDataSource,
        instrument: Instrument,
        candle: Candle,
        now: datetime,
        is_closed: bool,
    ) -> LiveCandleSnapshot:
        return LiveCandleSnapshot(
            source=source,
            venue=candle.venue,
            instrument_id=instrument.id,
            canonical_symbol=instrument.canonical_symbol,
            interval=candle.interval,
            ts_start=candle.ts_start,
            ts_end=candle.ts_end,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            value=candle.value,
            trades_count=candle.trades_count,
            updated_at=now,
            is_closed=is_closed,
            freshness=classify_freshness(now, now, self.stale_after_seconds),
            metadata={"source_candle_source": candle.source},
        )

    def _event(
        self,
        source: MarketDataSource,
        instrument: Instrument,
        candle: Candle,
        now: datetime,
        is_closed: bool,
        run_id: str,
    ) -> MarketDataEvent:
        event_type = MarketDataEventType.CANDLE_CLOSED if is_closed else MarketDataEventType.CANDLE_UPDATED
        return MarketDataEvent(
            source=source,
            event_type=event_type,
            venue=candle.venue,
            instrument_id=instrument.id,
            canonical_symbol=instrument.canonical_symbol,
            interval=candle.interval,
            ts=candle.ts_start,
            received_at=now,
            payload={
                "run_id": run_id,
                "open": str(candle.open),
                "high": str(candle.high),
                "low": str(candle.low),
                "close": str(candle.close),
                "volume": str(candle.volume),
                "is_closed": is_closed,
            },
            metadata={"source": "read_only_market_data_ingestion"},
        )

    def _require_run(self, run_id: str) -> MarketDataIngestionRun:
        run = self.storage.get_market_data_ingestion_run(run_id)
        if run is None:
            raise DataValidationError(f"market data ingestion run not found: {run_id}")
        return run

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError("clock must return timezone-aware UTC datetime")
        return now.astimezone(UTC)
