import json
from datetime import UTC, datetime

from storage.in_memory import InMemoryStorage
from trading_core.research.models import ResearchBacktestResult, ResearchRun, ResearchStatus
from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


def seed_research(storage: InMemoryStorage) -> ResearchRun:
    run = ResearchRun(
        id="research-1",
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        instrument_id="moex:SiH6",
        interval="1m",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        parameter_grid={"opening_range_minutes": [2]},
        data_quality_gate={},
        status=ResearchStatus.COMPLETED,
    )
    result = ResearchBacktestResult(
        id="result-1",
        research_run_id=run.id,
        backtest_run_id="bt-1",
        strategy_id=run.strategy_id,
        canonical_symbol=run.canonical_symbol,
        instrument_id=run.instrument_id,
        interval=run.interval,
        start=run.start,
        end=run.end,
        params={"opening_range_minutes": 2},
        metrics={"profit_factor": "1.5", "expectancy": "0.5", "total_pnl": "10", "max_drawdown": "0.01"},
        quality_report={"warnings": []},
        status=ResearchStatus.COMPLETED,
    )
    storage.save_research_run(run)
    storage.save_research_backtest_result(result)
    return run


def test_cli_research_report_json(monkeypatch) -> None:
    storage = InMemoryStorage()
    seed_research(storage)
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(cli_main.app, ["research", "report", "--research-run-id", "research-1"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["research_run_id"] == "research-1"
    assert body["best_by_profit_factor"]["params"] == {"opening_range_minutes": 2}


def test_cli_research_report_markdown(monkeypatch) -> None:
    storage = InMemoryStorage()
    seed_research(storage)
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        ["research", "report", "--research-run-id", "research-1", "--format", "markdown"],
    )

    assert result.exit_code == 0
    assert "# Research Report: opening_range_breakout" in result.stdout
    assert "opening_range_minutes" in result.stdout
