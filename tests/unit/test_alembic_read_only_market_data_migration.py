from pathlib import Path


def test_alembic_read_only_market_data_migration_references_required_tables_and_indexes() -> None:
    migration_files = list(
        Path("packages/storage/migrations/versions").glob("*read_only_market_data*.py")
    )

    assert len(migration_files) == 1
    text = migration_files[0].read_text(encoding="utf-8")
    for table_name in [
        "market_data_ingestion_runs",
        "market_data_events",
        "live_candle_snapshots",
    ]:
        assert table_name in text
    for required_name in [
        "uq_live_candle_snapshots_market_key",
        "ix_market_data_events_source_instrument_interval_received",
        "ix_market_data_ingestion_runs_source_status_started",
    ]:
        assert required_name in text
