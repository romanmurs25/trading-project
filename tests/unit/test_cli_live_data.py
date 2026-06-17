import json

from typer.testing import CliRunner

import apps.cli.main as cli_main

runner = CliRunner()


def test_cli_live_data_replay_demo_writes_read_only_snapshots(monkeypatch) -> None:
    storage = cli_main.InMemoryStorage()
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(
        cli_main.app,
        [
            "live-data",
            "replay-demo",
            "--canonical-symbol",
            "MOEX:SiH6",
            "--interval",
            "1m",
            "--count",
            "2",
        ],
    )

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["status"] == "saved"
    assert body["source"] == "DEMO_REPLAY"
    assert body["read_only"] is True
    assert body["snapshots_count"] == 2
    assert storage.get_latest_live_candle_snapshot("MOEX:SiH6", "1m") is not None


def test_cli_live_data_state_lists_stored_snapshots(monkeypatch) -> None:
    storage = cli_main.InMemoryStorage()
    cli_main.replay_demo_candles_once(storage=storage, canonical_symbol="MOEX:SiH6", interval="1m", count=1)
    monkeypatch.setattr(cli_main, "_resolve_storage", lambda storage_name: storage)

    result = runner.invoke(cli_main.app, ["live-data", "state"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["status"] == "IDLE"
    assert body["latest_candles_count"] == 1
    assert body["sources"] == ["DEMO_REPLAY"]


def test_cli_live_data_poll_moex_once_defaults_to_no_network() -> None:
    result = runner.invoke(
        cli_main.app,
        [
            "live-data",
            "poll-moex-once",
            "--symbol",
            "SiH6",
            "--instrument-id",
            "moex:SiH6",
            "--interval",
            "1m",
        ],
    )

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["status"] == "skipped"
    assert body["allow_network"] is False
    assert body["candles_loaded"] == 0
