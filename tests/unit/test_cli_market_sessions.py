import json

from storage.in_memory import InMemoryStorage
from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


def test_cli_market_sessions_outputs_and_writes(monkeypatch) -> None:
    storage = InMemoryStorage()
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        [
            "market",
            "sessions",
            "--from",
            "2026-01-05",
            "--to",
            "2026-01-06",
            "--venue",
            "MOEX",
            "--market",
            "forts",
            "--write",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["sessions_count"] > 0
    assert payload["trading_sessions_count"] > 0
    assert payload["clearing_sessions_count"] > 0
    assert payload["written"] is True
    assert storage.market_sessions
