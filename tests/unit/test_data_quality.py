from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from trading_core.analytics.data_quality import analyze_candle_series
from trading_core.domain.enums import Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle


def candle(minute: int, volume: Decimal = Decimal("100")) -> Candle:
    start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return Candle(
        instrument_id="moex:SiH6",
        venue=Venue.MOEX,
        interval="1m",
        ts_start=start,
        ts_end=start + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=volume,
        source="test",
    )


def test_analyze_candle_series_reports_clean_series() -> None:
    report = analyze_candle_series([candle(0), candle(1), candle(2)], "1m")

    assert report.candles_count == 3
    assert report.duplicates_count == 0
    assert report.non_monotonic_count == 0
    assert report.missing_intervals_count == 0
    assert report.zero_volume_count == 0
    assert report.warnings == []


def test_analyze_candle_series_detects_quality_issues() -> None:
    report = analyze_candle_series(
        [
            candle(0),
            candle(3, volume=Decimal("0")),
            candle(3),
            candle(2),
        ],
        "1m",
    )

    assert report.candles_count == 4
    assert report.duplicates_count == 1
    assert report.non_monotonic_count == 1
    assert report.missing_intervals_count == 1
    assert report.zero_volume_count == 1
    assert "duplicate candle timestamps detected" in report.warnings
    assert "non-monotonic candle order detected" in report.warnings
    assert "missing candle intervals detected" in report.warnings
    assert "zero-volume candles detected" in report.warnings


def test_analyze_candle_series_supports_empty_input() -> None:
    report = analyze_candle_series([], "1m")

    assert report.candles_count == 0
    assert report.start is None
    assert report.end is None
    assert report.warnings == ["no candles available"]


def test_analyze_candle_series_rejects_unsupported_interval() -> None:
    with pytest.raises(DataValidationError):
        analyze_candle_series([candle(0)], "5m")
