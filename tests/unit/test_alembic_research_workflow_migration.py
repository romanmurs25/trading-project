from pathlib import Path


def test_alembic_research_workflow_migration_exists_and_references_required_tables() -> None:
    migration_files = list(Path("packages/storage/migrations/versions").glob("*research_workflow*.py"))

    assert len(migration_files) == 1
    text = migration_files[0].read_text(encoding="utf-8")
    for table_name in [
        "research_runs",
        "research_backtest_results",
        "backtest_equity_points",
        "backtest_trade_records",
    ]:
        assert table_name in text
    for index_name in [
        "ix_research_runs_strategy_id",
        "ix_research_runs_canonical_symbol",
        "ix_research_backtest_results_research_run_id",
        "ix_backtest_equity_points_backtest_run_id",
        "ix_backtest_trade_records_backtest_run_id",
    ]:
        assert index_name in text
