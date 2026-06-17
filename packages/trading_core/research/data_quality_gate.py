from trading_core.analytics.data_quality import CandleQualityReport, analyze_candle_series
from trading_core.domain.models import Candle, DomainModel


class DataQualityGateConfig(DomainModel):
    fail_on_no_candles: bool = True
    max_duplicates_count: int = 0
    max_missing_intervals_count: int = 0
    max_zero_volume_count: int | None = None
    allow_non_monotonic: bool = False


class DataQualityGateDecision(DomainModel):
    approved: bool
    reason: str
    report: CandleQualityReport
    checks: dict[str, bool]


def evaluate_data_quality_gate(
    candles: list[Candle],
    interval: str,
    config: DataQualityGateConfig,
) -> DataQualityGateDecision:
    report = analyze_candle_series(candles, interval)
    checks = {
        "has_candles": bool(candles) or not config.fail_on_no_candles,
        "duplicates_within_limit": report.duplicates_count <= config.max_duplicates_count,
        "missing_intervals_within_limit": (
            report.missing_intervals_count <= config.max_missing_intervals_count
        ),
        "zero_volume_within_limit": (
            True
            if config.max_zero_volume_count is None
            else report.zero_volume_count <= config.max_zero_volume_count
        ),
        "non_monotonic_allowed": config.allow_non_monotonic or report.non_monotonic_count == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return DataQualityGateDecision(
        approved=not failed,
        reason="approved" if not failed else f"failed checks: {', '.join(failed)}",
        report=report,
        checks=checks,
    )
