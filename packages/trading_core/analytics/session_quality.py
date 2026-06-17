from datetime import datetime
from typing import Any

from pydantic import Field

from trading_core.domain.models import Candle, DomainModel
from trading_core.market.calendar import MarketCalendarService


class SessionAwareCandleQualityReport(DomainModel):
    candles_count: int
    start: datetime | None
    end: datetime | None
    expected_candles_count: int
    missing_expected_candles_count: int
    unexpected_out_of_session_count: int
    duplicates_count: int
    non_monotonic_count: int
    zero_volume_count: int
    session_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class SessionAwareDataQualityGateConfig(DomainModel):
    fail_on_no_candles: bool = True
    max_duplicates_count: int = 0
    max_missing_expected_candles_count: int = 0
    max_unexpected_out_of_session_count: int = 0
    max_zero_volume_count: int | None = None
    allow_non_monotonic: bool = False


class SessionAwareDataQualityGateDecision(DomainModel):
    approved: bool
    reason: str
    report: SessionAwareCandleQualityReport
    checks: dict[str, Any]


def analyze_candle_series_session_aware(
    candles: list[Candle],
    interval: str,
    calendar: MarketCalendarService,
    start: datetime,
    end: datetime,
) -> SessionAwareCandleQualityReport:
    expected = set(calendar.expected_candle_timestamps(start, end, interval))
    timestamps = [candle.ts_start for candle in candles]
    timestamp_counts: dict[datetime, int] = {}
    session_counts: dict[str, int] = {}
    unexpected_out_of_session_count = 0
    zero_volume_count = 0
    non_monotonic_count = 0
    previous: datetime | None = None

    for candle in candles:
        timestamp_counts[candle.ts_start] = timestamp_counts.get(candle.ts_start, 0) + 1
        classification = calendar.classify_timestamp(candle.ts_start)
        session_counts[classification.session_type.value] = (
            session_counts.get(classification.session_type.value, 0) + 1
        )
        if not classification.is_trading_time:
            unexpected_out_of_session_count += 1
        if candle.volume == 0:
            zero_volume_count += 1
        if previous is not None and candle.ts_start < previous:
            non_monotonic_count += 1
        previous = candle.ts_start

    duplicates_count = sum(count - 1 for count in timestamp_counts.values() if count > 1)
    actual_trading_timestamps = {
        candle.ts_start for candle in candles if calendar.is_trading_time(candle.ts_start)
    }
    missing_expected = expected - actual_trading_timestamps
    warnings: list[str] = []
    if missing_expected:
        warnings.append(f"missing expected session candles: {len(missing_expected)}")
    if unexpected_out_of_session_count:
        warnings.append(f"out-of-session candles: {unexpected_out_of_session_count}")

    return SessionAwareCandleQualityReport(
        candles_count=len(candles),
        start=min(timestamps) if timestamps else None,
        end=max((candle.ts_end for candle in candles), default=None),
        expected_candles_count=len(expected),
        missing_expected_candles_count=len(missing_expected),
        unexpected_out_of_session_count=unexpected_out_of_session_count,
        duplicates_count=duplicates_count,
        non_monotonic_count=non_monotonic_count,
        zero_volume_count=zero_volume_count,
        session_counts=session_counts,
        warnings=warnings,
    )


def evaluate_session_aware_data_quality_gate(
    candles: list[Candle],
    interval: str,
    calendar: MarketCalendarService,
    start: datetime,
    end: datetime,
    config: SessionAwareDataQualityGateConfig,
) -> SessionAwareDataQualityGateDecision:
    report = analyze_candle_series_session_aware(candles, interval, calendar, start, end)
    checks = {
        "has_candles": report.candles_count > 0,
        "duplicates_ok": report.duplicates_count <= config.max_duplicates_count,
        "missing_expected_ok": (
            report.missing_expected_candles_count <= config.max_missing_expected_candles_count
        ),
        "unexpected_out_of_session_ok": (
            report.unexpected_out_of_session_count <= config.max_unexpected_out_of_session_count
        ),
        "non_monotonic_ok": config.allow_non_monotonic or report.non_monotonic_count == 0,
        "zero_volume_ok": (
            True
            if config.max_zero_volume_count is None
            else report.zero_volume_count <= config.max_zero_volume_count
        ),
    }
    if config.fail_on_no_candles and not checks["has_candles"]:
        return _decision(False, "no candles", report, checks)
    if not checks["duplicates_ok"]:
        return _decision(False, "duplicates exceed limit", report, checks)
    if not checks["missing_expected_ok"]:
        return _decision(False, "missing expected session candles exceed limit", report, checks)
    if not checks["unexpected_out_of_session_ok"]:
        return _decision(False, "out-of-session candles exceed limit", report, checks)
    if not checks["non_monotonic_ok"]:
        return _decision(False, "non-monotonic candles", report, checks)
    if not checks["zero_volume_ok"]:
        return _decision(False, "zero-volume candles exceed limit", report, checks)
    return _decision(True, "approved", report, checks)


def _decision(
    approved: bool,
    reason: str,
    report: SessionAwareCandleQualityReport,
    checks: dict[str, Any],
) -> SessionAwareDataQualityGateDecision:
    return SessionAwareDataQualityGateDecision(
        approved=approved,
        reason=reason,
        report=report,
        checks=checks,
    )
