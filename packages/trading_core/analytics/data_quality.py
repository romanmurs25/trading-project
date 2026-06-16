from datetime import datetime, timedelta
from itertools import pairwise

from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle, DomainModel

INTERVALS = {
    "1m": timedelta(minutes=1),
    "10m": timedelta(minutes=10),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}


class CandleQualityReport(DomainModel):
    candles_count: int
    start: datetime | None
    end: datetime | None
    duplicates_count: int
    non_monotonic_count: int
    missing_intervals_count: int
    zero_volume_count: int
    warnings: list[str]


def analyze_candle_series(candles: list[Candle], interval: str) -> CandleQualityReport:
    step = _interval_step(interval)
    if not candles:
        return CandleQualityReport(
            candles_count=0,
            start=None,
            end=None,
            duplicates_count=0,
            non_monotonic_count=0,
            missing_intervals_count=0,
            zero_volume_count=0,
            warnings=["no candles available"],
        )

    starts = [candle.ts_start for candle in candles]
    duplicates_count = len(starts) - len(set(starts))
    non_monotonic_count = _non_monotonic_count(starts)
    missing_intervals_count = _missing_intervals_count(sorted(set(starts)), step)
    zero_volume_count = sum(1 for candle in candles if candle.volume == 0)
    warnings = _warnings(
        duplicates_count=duplicates_count,
        non_monotonic_count=non_monotonic_count,
        missing_intervals_count=missing_intervals_count,
        zero_volume_count=zero_volume_count,
    )
    return CandleQualityReport(
        candles_count=len(candles),
        start=min(starts),
        end=max(candle.ts_end for candle in candles),
        duplicates_count=duplicates_count,
        non_monotonic_count=non_monotonic_count,
        missing_intervals_count=missing_intervals_count,
        zero_volume_count=zero_volume_count,
        warnings=warnings,
    )


def _interval_step(interval: str) -> timedelta:
    try:
        return INTERVALS[interval]
    except KeyError as exc:
        raise DataValidationError(f"Unsupported candle interval for quality report: {interval}") from exc


def _non_monotonic_count(starts: list[datetime]) -> int:
    return sum(1 for previous, current in pairwise(starts) if current < previous)


def _missing_intervals_count(sorted_unique_starts: list[datetime], step: timedelta) -> int:
    missing = 0
    for previous, current in pairwise(sorted_unique_starts):
        gap = current - previous
        if gap > step:
            missing += int(gap / step) - 1
    return missing


def _warnings(
    *,
    duplicates_count: int,
    non_monotonic_count: int,
    missing_intervals_count: int,
    zero_volume_count: int,
) -> list[str]:
    warnings: list[str] = []
    if duplicates_count:
        warnings.append("duplicate candle timestamps detected")
    if non_monotonic_count:
        warnings.append("non-monotonic candle order detected")
    if missing_intervals_count:
        warnings.append("missing candle intervals detected")
    if zero_volume_count:
        warnings.append("zero-volume candles detected")
    return warnings
