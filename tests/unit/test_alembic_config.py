from pathlib import Path


def test_alembic_initial_migration_files_exist_and_reference_required_tables() -> None:
    assert Path("alembic.ini").exists()
    assert Path("packages/storage/migrations/env.py").exists()
    versions = list(Path("packages/storage/migrations/versions").glob("*_initial_schema.py"))
    assert len(versions) == 1
    migration_text = versions[0].read_text(encoding="utf-8")
    assert "op.create_table" in migration_text
    for table_name in [
        "instruments",
        "candles",
        "signals",
        "order_intents",
        "risk_decisions",
        "orders",
        "executions",
        "positions",
        "backtest_runs",
        "audit_logs",
        "system_events",
    ]:
        assert f'"{table_name}"' in migration_text
