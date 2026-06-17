from datetime import UTC, datetime
from decimal import Decimal

from trading_core.research.models import ResearchBacktestResult, ResearchRun, ResearchStatus
from trading_core.research.reporting import build_markdown_research_report, build_research_report


def make_run() -> ResearchRun:
    return ResearchRun(
        id="research-1",
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        instrument_id="moex:SiH6",
        interval="1m",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        parameter_grid={"opening_range_minutes": [5, 15]},
        data_quality_gate={"max_missing_intervals_count": 0},
        status=ResearchStatus.COMPLETED,
    )


def make_result(
    result_id: str,
    params: dict[str, object],
    profit_factor: str,
    expectancy: str,
) -> ResearchBacktestResult:
    return ResearchBacktestResult(
        id=result_id,
        research_run_id="research-1",
        backtest_run_id=f"bt-{result_id}",
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        instrument_id="moex:SiH6",
        interval="1m",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        params=params,
        metrics={
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "total_pnl": "10",
            "max_drawdown": "0.05",
            "trades_count": "2",
        },
        quality_report={"warnings": []},
        status=ResearchStatus.COMPLETED,
    )


def test_json_report_includes_best_results() -> None:
    report = build_research_report(
        make_run(),
        [
            make_result("1", {"opening_range_minutes": 5}, "1.2", "0.5"),
            make_result("2", {"opening_range_minutes": 15}, "2.0", "0.7"),
        ],
    )

    assert report["research_run_id"] == "research-1"
    assert report["best_by_profit_factor"]["params"] == {"opening_range_minutes": 15}
    assert report["best_by_expectancy"]["params"] == {"opening_range_minutes": 15}


def test_markdown_report_includes_strategy_and_top_parameter_table() -> None:
    markdown = build_markdown_research_report(
        make_run(),
        [make_result("1", {"opening_range_minutes": 5}, "1.2", "0.5")],
    )

    assert "# Research Report: opening_range_breakout" in markdown
    assert "| Rank | Params | Profit Factor | Expectancy | Total PnL | Max Drawdown | Trades |" in markdown
    assert "opening_range_minutes" in markdown


def test_report_generates_warnings_for_no_trades_and_failed_results() -> None:
    failed = make_result("failed", {"opening_range_minutes": 5}, "0", "0")
    failed.status = ResearchStatus.FAILED
    failed.error_message = "bad params"
    failed.metrics["trades_count"] = "0"

    report = build_research_report(make_run(), [failed])

    assert "no trades" in " ".join(report["warnings"])
    assert "failed parameter combinations" in " ".join(report["warnings"])


def test_report_accepts_decimal_metrics() -> None:
    result = make_result("decimal", {"opening_range_minutes": 5}, "1.0", "0.1")
    result.metrics["profit_factor"] = Decimal("1.5")

    report = build_research_report(make_run(), [result])

    assert report["best_by_profit_factor"]["metrics"]["profit_factor"] == "1.5"
