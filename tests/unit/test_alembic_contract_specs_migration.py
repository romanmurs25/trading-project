from pathlib import Path


def test_alembic_0002_contract_specs_migration_exists() -> None:
    versions = list(Path("packages/storage/migrations/versions").glob("*contract_specs*.py"))
    assert len(versions) == 1

    migration_text = versions[0].read_text(encoding="utf-8")
    assert '"contract_specs"' in migration_text
    assert "ix_instruments_venue_asset_class_native_symbol" in migration_text
    assert "uq_contract_specs_instrument_id" in migration_text
