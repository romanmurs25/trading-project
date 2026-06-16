from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_api_health_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["live_trading_enabled"] is False


def test_api_backtest_returns_metrics() -> None:
    client = TestClient(create_app())

    response = client.post("/api/backtests/run")

    assert response.status_code == 200
    body = response.json()
    assert "metrics" in body
    assert "closed_trades_count" in body


def test_api_kill_switch_activate_and_deactivate_changes_state() -> None:
    client = TestClient(create_app())

    activated = client.post("/api/risk/kill-switch/activate")
    deactivated = client.post("/api/risk/kill-switch/deactivate")

    assert activated.status_code == 200
    assert activated.json()["kill_switch_active"] is True
    assert deactivated.status_code == 200
    assert deactivated.json()["kill_switch_active"] is False
