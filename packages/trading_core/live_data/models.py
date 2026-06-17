from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from trading_core.domain.enums import Venue
from trading_core.domain.models import DomainModel, new_id, utc_now


class MarketDataSource(StrEnum):
    DEMO_REPLAY = "DEMO_REPLAY"
    MOEX_ISS_POLLING = "MOEX_ISS_POLLING"
    MANUAL_IMPORT = "MANUAL_IMPORT"


class MarketDataEventType(StrEnum):
    CANDLE_RECEIVED = "CANDLE_RECEIVED"
    CANDLE_UPDATED = "CANDLE_UPDATED"
    CANDLE_CLOSED = "CANDLE_CLOSED"
    INGESTION_STARTED = "INGESTION_STARTED"
    INGESTION_STOPPED = "INGESTION_STOPPED"
    INGESTION_ERROR = "INGESTION_ERROR"
    HEARTBEAT = "HEARTBEAT"


class MarketDataIngestionStatus(StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class MarketDataFreshness(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class _UtcDomainModel(DomainModel):
    @field_validator("*", mode="before")
    @classmethod
    def validate_utc_datetimes(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("datetime must be timezone-aware UTC")
            if value.utcoffset() != timedelta(0):
                raise ValueError("datetime must be UTC")
        return value


class MarketDataEvent(_UtcDomainModel):
    id: str = Field(default_factory=new_id)
    source: MarketDataSource
    event_type: MarketDataEventType
    venue: Venue
    instrument_id: str
    canonical_symbol: str
    interval: str
    ts: datetime
    received_at: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveCandleSnapshot(_UtcDomainModel):
    id: str = Field(default_factory=new_id)
    source: MarketDataSource
    venue: Venue
    instrument_id: str
    canonical_symbol: str
    interval: str
    ts_start: datetime
    ts_end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    value: Decimal | None = None
    trades_count: int | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    is_closed: bool
    freshness: MarketDataFreshness
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketDataIngestionRun(_UtcDomainModel):
    id: str = Field(default_factory=new_id)
    source: MarketDataSource
    status: MarketDataIngestionStatus
    venue: Venue
    instruments: list[str]
    interval: str
    started_at: datetime
    stopped_at: datetime | None = None
    last_event_at: datetime | None = None
    events_count: int = 0
    candles_count: int = 0
    errors_count: int = 0
    read_only: bool = True
    allow_network: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("read_only")
    @classmethod
    def validate_read_only(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("market data ingestion runs must be read-only")
        return value


class MarketDataState(_UtcDomainModel):
    status: MarketDataIngestionStatus
    sources: list[MarketDataSource] = Field(default_factory=list)
    active_runs: list[MarketDataIngestionRun] = Field(default_factory=list)
    latest_event_at: datetime | None = None
    latest_candles_count: int = 0
    stale_candles_count: int = 0
    warnings: list[str] = Field(default_factory=list)
