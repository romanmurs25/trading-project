from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from trading_core.domain.enums import Venue
from trading_core.live_data.models import (
    LiveCandleSnapshot,
    MarketDataFreshness,
    MarketDataIngestionRun,
    MarketDataIngestionStatus,
    MarketDataSource,
)


def aware() -> datetime:
    return datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def test_market_data_ingestion_run_is_always_read_only() -> None:
    run = MarketDataIngestionRun(
        source=MarketDataSource.DEMO_REPLAY,
        status=MarketDataIngestionStatus.RUNNING,
        venue=Venue.MOEX,
        instruments=["MOEX:SiH6"],
        interval="1m",
        started_at=aware(),
        read_only=True,
        allow_network=False,
    )

    assert run.read_only is True


def test_market_data_ingestion_run_rejects_non_read_only() -> None:
    with pytest.raises(ValidationError):
        MarketDataIngestionRun(
            source=MarketDataSource.DEMO_REPLAY,
            status=MarketDataIngestionStatus.RUNNING,
            venue=Venue.MOEX,
            instruments=["MOEX:SiH6"],
            interval="1m",
            started_at=aware(),
            read_only=False,
            allow_network=False,
        )


def test_live_candle_snapshot_rejects_float_decimal_fields() -> None:
    with pytest.raises(ValidationError):
        LiveCandleSnapshot(
            source=MarketDataSource.DEMO_REPLAY,
            venue=Venue.MOEX,
            instrument_id="moex:SiH6",
            canonical_symbol="MOEX:SiH6",
            interval="1m",
            ts_start=aware(),
            ts_end=aware(),
            open=1.0,
            high=Decimal("2"),
            low=Decimal("1"),
            close=Decimal("2"),
            volume=Decimal("100"),
            updated_at=aware(),
            is_closed=True,
            freshness=MarketDataFreshness.FRESH,
        )
