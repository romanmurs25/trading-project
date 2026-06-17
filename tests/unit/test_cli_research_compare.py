import json
from datetime import UTC, datetime

from storage.in_memory import InMemoryStorage
from trading_core.research.models import ResearchBacktestResult, ResearchRun, ResearchStatus
from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


def seed_results(storage: InMemoryStorage) -> None:
    run = ResearchRun(
        id="research-1",
        strategy_id="opening_range_breakout",
        canonical_symbol="MOEX:SiH6",
        instrument_id="moex:SiH6",
        interval="1m",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 2, tzinfo=UTC),
        parameter_grid={},
        data_quality_gate={},
        status=ResearchStatus.COMPLETED,
    )
    storage.save_research_run(run)
    for result_id, profit_factor in [("a", "1.1"), ("b", "2.2")]:
        storage.save_research_backtest_result(
            ResearchBacktestResult(
                id=result_id,
                research_run_id=run.id,
                backtest_run_id=f"bt-{result_id}",
                strategy_id=run.strategy_id,
                canonical_symbol=run.canonical_symbol,
                instrument_id=run.instrument_id,
                interval=run.interval,
                start=run.start,
                end=run.end,
                params={"id": result_id},
                metrics={
                    "profit_factor": profit_factor,
                    "expectancy": profit_factor,
                    "total_pnl": profit_factor,
                },
                quality_report={},
                status=ResearchStatus.COMPLETED,
            )
        )


def test_cli_research_compare_sorts_rows(monkeypatch) -> None:
    storage = InMemoryStorage()
    seed_results(storage)
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        ["research", "compare", "--research-run-id", "research-1", "--sort-by", "profit_factor"],
    )

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["rows"][0]["params"] == {"id": "b"}
    assert body["best_row"]["params"] == {"id": "b"}
