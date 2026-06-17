from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from trading_core.analytics.session_quality import (
    SessionAwareDataQualityGateConfig,
    analyze_candle_series_session_aware,
    evaluate_session_aware_data_quality_gate,
)
from trading_core.domain.enums import Venue
from trading_core.domain.models import Candle
from trading_core.market.calendar import MarketCalendarService
from trading_core.market.moex_templates import default_moex_futures_session_templates


def make_calendar() -> MarketCalendarService:
    return MarketCalendarService(default_moex_futures_session_templates())


def make_candle(ts_start: datetime, volume: Decimal = Decimal("100")) -> Candle:
    return Candle(
        instrument_id="moex:SiH6",
        venue=Venue.MOEX,
        interval="1m",
        ts_start=ts_start,
        ts_end=ts_start + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=volume,
        source="test",
    )


def test_overnight_gap_not_counted_as_missing() -> None:
    calendar = make_calendar()
    candles = [
        make_candle(datetime(2026, 1, 5, 20, 49, tzinfo=UTC)),
        make_candle(datetime(2026, 1, 6, 4, 0, tzinfo=UTC)),
    ]

    report = analyze_candle_series_session_aware(
        candles,
        "1m",
        calendar,
        datetime(2026, 1, 5, 20, 49, tzinfo=UTC),
        datetime(2026, 1, 6, 4, 1, tzinfo=UTC),
    )

    assert report.missing_expected_candles_count == 0


def test_clearing_gap_not_counted_as_missing() -> None:
    calendar = make_calendar()
    candles = [
        make_candle(datetime(2026, 1, 5, 10, 59, tzinfo=UTC)),
        make_candle(datetime(2026, 1, 5, 11, 5, tzinfo=UTC)),
    ]

    report = analyze_candle_series_session_aware(
        candles,
        "1m",
        calendar,
        datetime(2026, 1, 5, 10, 59, tzinfo=UTC),
        datetime(2026, 1, 5, 11, 6, tzinfo=UTC),
    )

    assert report.missing_expected_candles_count == 0


def test_missing_candle_inside_session_counted() -> None:
    calendar = make_calendar()
    candles = [
        make_candle(datetime(2026, 1, 5, 7, 0, tzinfo=UTC)),
        make_candle(datetime(2026, 1, 5, 7, 2, tzinfo=UTC)),
    ]

    report = analyze_candle_series_session_aware(
        candles,
        "1m",
        calendar,
        datetime(2026, 1, 5, 7, 0, tzinfo=UTC),
        datetime(2026, 1, 5, 7, 3, tzinfo=UTC),
    )

    assert report.missing_expected_candles_count == 1


def test_out_of_session_duplicate_and_zero_volume_detected() -> None:
    calendar = make_calendar()
    candles = [
        make_candle(datetime(2026, 1, 5, 15, 50, tzinfo=UTC), volume=Decimal("0")),
        make_candle(datetime(2026, 1, 5, 15, 50, tzinfo=UTC)),
    ]

    report = analyze_candle_series_session_aware(
        candles,
        "1m",
        calendar,
        datetime(2026, 1, 5, 15, 50, tzinfo=UTC),
        datetime(2026, 1, 5, 15, 51, tzinfo=UTC),
    )

    assert report.unexpected_out_of_session_count == 2
    assert report.duplicates_count == 1
    assert report.zero_volume_count == 1


def test_session_aware_gate_approves_good_data_and_rejects_missing() -> None:
    calendar = make_calendar()
    good = [make_candle(datetime(2026, 1, 5, 7, minute, tzinfo=UTC)) for minute in range(3)]
    bad = [good[0], good[2]]

    approved = evaluate_session_aware_data_quality_gate(
        good,
        "1m",
        calendar,
        datetime(2026, 1, 5, 7, 0, tzinfo=UTC),
        datetime(2026, 1, 5, 7, 3, tzinfo=UTC),
        SessionAwareDataQualityGateConfig(),
    )
    rejected = evaluate_session_aware_data_quality_gate(
        bad,
        "1m",
        calendar,
        datetime(2026, 1, 5, 7, 0, tzinfo=UTC),
        datetime(2026, 1, 5, 7, 3, tzinfo=UTC),
        SessionAwareDataQualityGateConfig(),
    )

    assert approved.approved is True
    assert rejected.approved is False
    assert "missing" in rejected.reason


def test_session_quality_rejects_naive_start() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        analyze_candle_series_session_aware(
            [],
            "1m",
            make_calendar(),
            datetime(2026, 1, 5),
            datetime(2026, 1, 6, tzinfo=UTC),
        )
