import json

from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


def test_cli_research_walk_forward_splits() -> None:
    result = runner.invoke(
        app,
        [
            "research",
            "walk-forward-splits",
            "--from",
            "2026-01-01",
            "--to",
            "2026-04-01",
            "--train-days",
            "30",
            "--test-days",
            "10",
            "--step-days",
            "20",
        ],
    )

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert len(body["splits"]) == 3
    assert body["splits"][0]["train_start"] == "2026-01-01T00:00:00+00:00"
