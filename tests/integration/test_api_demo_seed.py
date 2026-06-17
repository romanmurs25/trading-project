from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_api_demo_seed_populates_read_only_dashboard_data(monkeypatch) -> None:
    monkeypatch.setenv("APP_SEED_DEMO_DATA", "true")
    app = create_app()
    client = TestClient(app)

    instruments_response = client.get("/api/instruments")
    runs_response = client.get("/api/research/runs")
    series_response = client.get("/api/continuous-series")
    sessions_response = client.get("/api/market/sessions")
    live_state_response = client.get("/api/live-data/state")
    live_candles_response = client.get("/api/live-data/candles")

    assert instruments_response.status_code == 200
    assert runs_response.status_code == 200
    assert series_response.status_code == 200
    assert sessions_response.status_code == 200
    assert live_state_response.status_code == 200
    assert live_candles_response.status_code == 200
    assert [item["canonical_symbol"] for item in instruments_response.json()] == [
        "MOEX:RIH6",
        "MOEX:SiH6",
        "MOEX:SiM6",
    ]
    assert runs_response.json()
    assert series_response.json()[0]["canonical_symbol"] == "MOEX:Si:CONT:1m"
    assert sessions_response.json()
    assert live_state_response.json()["latest_candles_count"] == 5
    assert live_candles_response.json()["candles"]

    run_id = runs_response.json()[0]["id"]
    equity_response = client.get(f"/api/research/runs/{run_id}/equity")
    trades_response = client.get(f"/api/research/runs/{run_id}/trades")

    assert equity_response.status_code == 200
    assert trades_response.status_code == 200
    assert equity_response.json()["points"]
    assert trades_response.json()["trades"]
    assert runs_response.json()[0]["metadata"]["demo"] is True


def test_api_demo_seed_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("APP_SEED_DEMO_DATA", raising=False)
    app = create_app()
    client = TestClient(app)

    assert client.get("/api/instruments").json() == []
    assert client.get("/api/research/runs").json() == []
    assert client.get("/api/continuous-series").json() == []
    assert client.get("/api/market/sessions").json() == []


def test_api_demo_seed_is_disabled_when_env_is_false(monkeypatch) -> None:
    monkeypatch.setenv("APP_SEED_DEMO_DATA", "false")
    app = create_app()
    client = TestClient(app)

    assert client.get("/api/instruments").json() == []
    assert client.get("/api/research/runs").json() == []
