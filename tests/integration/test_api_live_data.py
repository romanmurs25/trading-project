from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_api_live_data_replay_demo_writes_read_only_snapshots() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/live-data/replay-demo",
        json={"canonical_symbol": "MOEX:SiH6", "interval": "1m", "count": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "saved"
    assert body["source"] == "DEMO_REPLAY"
    assert body["read_only"] is True
    assert body["snapshots_count"] == 2

    state = client.get("/api/live-data/state").json()
    candles = client.get("/api/live-data/candles", params={"canonical_symbol": "MOEX:SiH6"}).json()
    events = client.get("/api/live-data/events").json()
    assert state["latest_candles_count"] == 2
    assert candles["candles"]
    assert events["events"]


def test_api_live_data_poll_moex_once_defaults_to_no_network() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/live-data/poll/moex-once",
        json={"symbol": "SiH6", "instrument_id": "moex:SiH6", "interval": "1m"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"
    assert body["allow_network"] is False
    assert body["candles_loaded"] == 0
