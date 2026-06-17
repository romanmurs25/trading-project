from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_core.domain.enums import Venue
from trading_core.domain.models import Candle
from trading_core.market.calendar import MarketCalendarService
from trading_core.market.continuous import ContinuousSeriesComponent
from trading_core.market.moex_templates import default_moex_futures_session_templates
from trading_core.research.session_reports import (
    add_session_summary_to_report,
    summarize_candles_by_session,
    summarize_results_by_contract_or_component,
)


def candle(ts_start: datetime) -> Candle:
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
        volume=Decimal("100"),
        source="test",
    )


def test_candle_counts_by_main_and_evening_session() -> None:
    calendar = MarketCalendarService(default_moex_futures_session_templates())

    summary = summarize_candles_by_session(
        [
            candle(datetime(2026, 1, 5, 7, 0, tzinfo=UTC)),
            candle(datetime(2026, 1, 5, 16, 0, tzinfo=UTC)),
        ],
        calendar,
    )

    assert summary["session_counts"]["MAIN"] == 1
    assert summary["session_counts"]["EVENING"] == 1


def test_contract_component_summary_and_report_extension() -> None:
    component = ContinuousSeriesComponent(
        continuous_series_id="series-1",
        instrument_id="moex:SiH6",
        canonical_symbol="MOEX:SiH6",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 2, 1, tzinfo=UTC),
    )

    contract_summary = summarize_results_by_contract_or_component([], [component])
    report = add_session_summary_to_report({"research_run_id": "run-1"}, {"MAIN": 10})

    assert contract_summary["components"][0]["instrument_id"] == "moex:SiH6"
    assert report["session_summary"] == {"MAIN": 10}
