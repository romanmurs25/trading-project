from typing import Any

from trading_core.domain.models import Candle
from trading_core.market.calendar import MarketCalendarService
from trading_core.market.continuous import ContinuousSeriesComponent


def summarize_candles_by_session(candles: list[Candle], calendar: MarketCalendarService) -> dict[str, Any]:
    session_counts: dict[str, int] = {}
    for candle in candles:
        classification = calendar.classify_timestamp(candle.ts_start)
        session_counts[classification.session_type.value] = (
            session_counts.get(classification.session_type.value, 0) + 1
        )
    return {"candles_count": len(candles), "session_counts": session_counts}


def summarize_results_by_contract_or_component(
    results: list[object],
    components: list[ContinuousSeriesComponent],
) -> dict[str, Any]:
    return {
        "results_count": len(results),
        "components": [
            {
                "instrument_id": component.instrument_id,
                "canonical_symbol": component.canonical_symbol,
                "start": component.start.isoformat(),
                "end": component.end.isoformat(),
                "roll_date": component.roll_date.isoformat() if component.roll_date is not None else None,
            }
            for component in components
        ],
    }


def add_session_summary_to_report(report: dict[str, Any], session_summary: dict[str, Any]) -> dict[str, Any]:
    return {**report, "session_summary": session_summary}
