from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from trading_core.domain.enums import Venue
from trading_core.domain.models import Candle, Instrument

from apps.api.main import create_app


class FakeMoexAdapter:
    calls = 0

    async def get_historical_candles(
        self,
        instrument: Instrument,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Candle]:
        type(self).calls += 1
        candle_start = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
        return [
            Candle(
                instrument_id=instrument.id,
                venue=Venue.MOEX,
                interval=interval,
                ts_start=candle_start,
                ts_end=candle_start + timedelta(minutes=1),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
                volume=Decimal("10"),
                value=Decimal("1000"),
                source="fake-moex",
            )
        ]


def test_api_moex_backfill_defaults_to_dry_run_without_network() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/market-data/backfill/moex",
        json={
            "symbol": "SiH6",
            "instrument_id": "moex-si",
            "interval": "1m",
            "from": "2026-01-01",
            "to": "2026-01-02",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "skipped",
        "candles_loaded": 0,
        "candles_saved": 0,
        "dry_run": True,
        "warnings": ["external network is disabled by default; pass allow_network=true explicitly"],
    }


def test_api_moex_backfill_uses_mocked_adapter_when_allowed() -> None:
    FakeMoexAdapter.calls = 0
    app = create_app()
    app.state.moex_market_data_adapter = FakeMoexAdapter()
    client = TestClient(app)

    response = client.post(
        "/api/market-data/backfill/moex",
        json={
            "symbol": "SiH6",
            "instrument_id": "moex-si",
            "interval": "1m",
            "from": "2026-01-01",
            "to": "2026-01-02",
            "allow_network": True,
            "dry_run": True,
        },
    )

    assert response.status_code == 200
    assert FakeMoexAdapter.calls == 1
    assert response.json() == {
        "status": "dry_run",
        "candles_loaded": 1,
        "candles_saved": 0,
        "dry_run": True,
        "warnings": [],
    }
