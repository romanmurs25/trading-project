from pathlib import Path


def test_alembic_market_sessions_continuous_migration_exists_and_references_tables() -> None:
    migration_files = list(
        Path("packages/storage/migrations/versions").glob("*market_sessions_continuous*.py")
    )

    assert len(migration_files) == 1
    text = migration_files[0].read_text(encoding="utf-8")
    for table_name in [
        "market_sessions",
        "continuous_series",
        "continuous_series_components",
        "roll_events",
    ]:
        assert table_name in text
    for index_name in [
        "ix_market_sessions_venue",
        "ix_market_sessions_market",
        "ix_continuous_series_canonical_symbol",
        "ix_continuous_series_components_continuous_series_id",
        "ix_roll_events_underlying_symbol",
    ]:
        assert index_name in text
