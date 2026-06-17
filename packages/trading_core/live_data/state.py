from datetime import datetime, timedelta

from trading_core.live_data.models import MarketDataFreshness


def classify_freshness(updated_at: datetime, now: datetime, stale_after_seconds: int) -> MarketDataFreshness:
    if updated_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("freshness timestamps must be timezone-aware")
    if stale_after_seconds < 0:
        raise ValueError("stale_after_seconds must be non-negative")
    if now - updated_at <= timedelta(seconds=stale_after_seconds):
        return MarketDataFreshness.FRESH
    return MarketDataFreshness.STALE
