from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from trading_core.research.models import ResearchBacktestResult, ResearchRun, ResearchStatus


def build_research_report(
    research_run: ResearchRun,
    results: list[ResearchBacktestResult],
    format: Literal["json", "markdown"] = "json",
) -> dict[str, Any] | str:
    if format == "markdown":
        return build_markdown_research_report(research_run, results)

    rows = [_result_row(result) for result in results]
    return {
        "research_run_id": research_run.id,
        "strategy_id": research_run.strategy_id,
        "canonical_symbol": research_run.canonical_symbol,
        "interval": research_run.interval,
        "start": research_run.start.isoformat(),
        "end": research_run.end.isoformat(),
        "parameter_grid": research_run.parameter_grid,
        "data_quality_gate": research_run.data_quality_gate,
        "results_count": len(results),
        "failed_results_count": sum(1 for result in results if result.status == ResearchStatus.FAILED),
        "best_by_profit_factor": _best_row(rows, "profit_factor", reverse=True),
        "best_by_expectancy": _best_row(rows, "expectancy", reverse=True),
        "best_by_total_pnl": _best_row(rows, "total_pnl", reverse=True),
        "best_by_max_drawdown": _best_row(rows, "max_drawdown", reverse=False),
        "top_by_profit_factor": _sorted_rows(rows, "profit_factor", reverse=True)[:10],
        "top_by_expectancy": _sorted_rows(rows, "expectancy", reverse=True)[:10],
        "warnings": _warnings(rows, results),
    }


def build_markdown_research_report(
    research_run: ResearchRun,
    results: list[ResearchBacktestResult],
) -> str:
    report = build_research_report(research_run, results, format="json")
    if not isinstance(report, dict):
        return report
    lines = [
        f"# Research Report: {research_run.strategy_id}",
        "",
        f"- Symbol: `{research_run.canonical_symbol}`",
        f"- Interval: `{research_run.interval}`",
        f"- Period: `{research_run.start.isoformat()}` - `{research_run.end.isoformat()}`",
        f"- Results: `{report['results_count']}`",
        "",
        "## Top By Profit Factor",
        "",
        "| Rank | Params | Profit Factor | Expectancy | Total PnL | Max Drawdown | Trades |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(report["top_by_profit_factor"], start=1):
        lines.append(_markdown_row(rank, row))
    lines.extend(["", "## Warnings", ""])
    warnings = report["warnings"]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- none")
    return "\n".join(lines)


def _result_row(result: ResearchBacktestResult) -> dict[str, Any]:
    return {
        "id": result.id,
        "backtest_run_id": result.backtest_run_id,
        "status": result.status.value,
        "params": result.params,
        "metrics": _json_metrics(result.metrics),
        "quality_report": result.quality_report,
        "error_message": result.error_message,
    }


def _json_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in metrics.items()}


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def _best_row(rows: list[dict[str, Any]], metric: str, *, reverse: bool) -> dict[str, Any] | None:
    sorted_rows = _sorted_rows(rows, metric, reverse=reverse)
    return sorted_rows[0] if sorted_rows else None


def _sorted_rows(rows: list[dict[str, Any]], metric: str, *, reverse: bool) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: _metric_decimal(row, metric),
        reverse=reverse,
    )


def _metric_decimal(row: dict[str, Any], metric: str) -> Decimal:
    raw = row.get("metrics", {}).get(metric, "0")
    if isinstance(raw, Decimal):
        return raw
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _warnings(rows: list[dict[str, Any]], results: list[ResearchBacktestResult]) -> list[str]:
    warnings: list[str] = []
    if any(result.status == ResearchStatus.FAILED for result in results):
        warnings.append("failed parameter combinations detected")
    if any(_metric_decimal(row, "trades_count") == 0 for row in rows):
        warnings.append("no trades for at least one parameter set")
    if any(_metric_decimal(row, "max_drawdown") > Decimal("0.2") for row in rows):
        warnings.append("high drawdown detected")
    if any(_metric_decimal(row, "trades_count") < Decimal("3") for row in rows):
        warnings.append("too few trades for at least one parameter set")
    for result in results:
        quality_warnings = result.quality_report.get("warnings", [])
        if quality_warnings:
            warnings.append("data-quality warnings detected")
            break
    return warnings


def _markdown_row(rank: int, row: dict[str, Any]) -> str:
    metrics = row["metrics"]
    return (
        f"| {rank} | `{row['params']}` | {metrics.get('profit_factor', '0')} | "
        f"{metrics.get('expectancy', '0')} | {metrics.get('total_pnl', '0')} | "
        f"{metrics.get('max_drawdown', '0')} | {metrics.get('trades_count', '0')} |"
    )
