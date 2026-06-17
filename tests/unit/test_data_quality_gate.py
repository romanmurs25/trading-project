from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_core.domain.enums import Venue
from trading_core.domain.models import Candle
from trading_core.research.data_quality_gate import DataQualityGateConfig, evaluate_data_quality_gate


def make_candle(minute: int, volume: Decimal = Decimal("100")) -> Candle:
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


def test_data_quality_gate_approves_good_data() -> None:
    decision = evaluate_data_quality_gate([make_candle(0), make_candle(1)], "1m", DataQualityGateConfig())

    assert decision.approved is True
    assert decision.reason == "approved"
    assert all(decision.checks.values())


def test_data_quality_gate_rejects_no_candles() -> None:
    decision = evaluate_data_quality_gate([], "1m", DataQualityGateConfig())

    assert decision.approved is False
    assert decision.checks["has_candles"] is False


def test_data_quality_gate_rejects_duplicates() -> None:
    decision = evaluate_data_quality_gate([make_candle(0), make_candle(0)], "1m", DataQualityGateConfig())

    assert decision.approved is False
    assert decision.checks["duplicates_within_limit"] is False


def test_data_quality_gate_rejects_missing_intervals() -> None:
    decision = evaluate_data_quality_gate([make_candle(0), make_candle(2)], "1m", DataQualityGateConfig())

    assert decision.approved is False
    assert decision.checks["missing_intervals_within_limit"] is False


def test_data_quality_gate_rejects_zero_volume_when_threshold_exceeded() -> None:
    decision = evaluate_data_quality_gate(
        [make_candle(0, Decimal("0"))],
        "1m",
        DataQualityGateConfig(max_zero_volume_count=0),
    )

    assert decision.approved is False
    assert decision.checks["zero_volume_within_limit"] is False


def test_data_quality_gate_rejects_non_monotonic_when_not_allowed() -> None:
    decision = evaluate_data_quality_gate([make_candle(1), make_candle(0)], "1m", DataQualityGateConfig())

    assert decision.approved is False
    assert decision.checks["non_monotonic_allowed"] is False
