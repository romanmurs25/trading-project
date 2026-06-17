from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, Instrument

from apps.api.main import create_app


def make_storage() -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.save_instrument(
        Instrument(
            id="moex:SiH6",
            venue=Venue.MOEX,
            asset_class=AssetClass.FUTURES,
            native_symbol="SiH6",
            canonical_symbol="MOEX:SiH6",
            name="Si futures",
            lot_size=Decimal("1"),
            tick_size=Decimal("1"),
            tick_value=Decimal("1"),
            currency="RUB",
        )
    )
    start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
    storage.save_candles(
        [
            Candle(
                instrument_id="moex:SiH6",
                venue=Venue.MOEX,
                interval="1m",
                ts_start=start + timedelta(minutes=i),
                ts_end=start + timedelta(minutes=i + 1),
                open=Decimal("100") + Decimal(i),
                high=Decimal("101") + Decimal(i),
                low=Decimal("99") + Decimal(i),
                close=Decimal("100") + Decimal(i),
                volume=Decimal("100"),
                source="test",
            )
            for i in range(8)
        ]
    )
    return storage


def test_api_research_run_and_read_endpoints() -> None:
    app = create_app()
    app.state.storage = make_storage()
    client = TestClient(app)

    response = client.post(
        "/api/research/run",
        json={
            "strategy_id": "opening_range_breakout",
            "canonical_symbol": "MOEX:SiH6",
            "interval": "1m",
            "from": "2026-01-01",
            "to": "2026-01-02",
            "parameter_grid": {"opening_range_minutes": [2, 3]},
            "initial_cash": "100000",
        },
    )

    assert response.status_code == 200
    run_id = response.json()["research_run_id"]
    assert response.json()["completed_backtests"] == 2

    runs_response = client.get("/api/research/runs")
    get_response = client.get(f"/api/research/runs/{run_id}")
    results_response = client.get(f"/api/research/runs/{run_id}/results")
    report_response = client.get(f"/api/research/runs/{run_id}/report")
    compare_response = client.get(f"/api/research/runs/{run_id}/compare")

    assert runs_response.status_code == 200
    assert runs_response.json()[0]["id"] == run_id
    assert get_response.status_code == 200
    assert results_response.status_code == 200
    assert len(results_response.json()) == 2
    assert report_response.status_code == 200
    assert report_response.json()["research_run_id"] == run_id
    assert compare_response.status_code == 200
    assert compare_response.json()["best_row"] is not None


def test_api_research_unknown_run_returns_404() -> None:
    client = TestClient(create_app())

    response = client.get("/api/research/runs/unknown")

    assert response.status_code == 404
