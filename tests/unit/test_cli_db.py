from typer.testing import CliRunner

from apps.cli.main import app


def test_db_init_placeholder_mentions_current_alembic_migration_command() -> None:
    result = CliRunner().invoke(app, ["db", "init-placeholder"])

    assert result.exit_code == 0
    assert "Alembic initial migration" in result.stdout
    assert "alembic upgrade head" in result.stdout
    assert "next storage cycle" not in result.stdout
