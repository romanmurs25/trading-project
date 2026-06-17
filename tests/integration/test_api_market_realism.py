from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.models import Candle, ContractSpec, Instrument

from apps.api.main import create_app


def instrument(symbol: str, expiry: date) -> Instrument:
    return Instrument(
        id=f"moex:{symbol}",
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=symbol,
        canonical_symbol=f"MOEX:{symbol}",
        name=symbol,
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry,
    )


def spec(symbol: str, expiry: date) -> ContractSpec:
    return ContractSpec(
        instrument_id=f"moex:{symbol}",
        lot_size=Decimal("1"),
        tick_size=Decimal("1"),
        tick_value=Decimal("1"),
        currency="RUB",
        expiry_date=expiry,
        last_trade_date=expiry,
        underlying_symbol="Si",
    )


def candle(symbol: str, ts_start: datetime, close: str) -> Candle:
    return Candle(
        instrument_id=f"moex:{symbol}",
        venue=Venue.MOEX,
        interval="1m",
        ts_start=ts_start,
        ts_end=ts_start + timedelta(minutes=1),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal("100"),
        source="test",
    )


def make_client() -> tuple[TestClient, InMemoryStorage]:
    app = create_app()
    storage = InMemoryStorage()
    storage.save_instruments([instrument("SiH6", date(2026, 3, 19)), instrument("SiM6", date(2026, 6, 18))])
    storage.save_contract_spec(spec("SiH6", date(2026, 3, 19)))
    storage.save_contract_spec(spec("SiM6", date(2026, 6, 18)))
    storage.save_candles(
        [
            candle("SiH6", datetime(2026, 3, 13, 7, 0, tzinfo=UTC), "100"),
            candle("SiM6", datetime(2026, 3, 16, 7, 0, tzinfo=UTC), "200"),
        ]
    )
    app.state.storage = storage
    return TestClient(app), storage


def test_api_generate_sessions_endpoint_works() -> None:
    client, storage = make_client()

    response = client.post(
        "/api/market/sessions/generate",
        json={"from": "2026-01-05", "to": "2026-01-06", "write": True},
    )

    assert response.status_code == 200
    assert response.json()["sessions_count"] > 0
    assert storage.market_sessions


def test_api_session_aware_quality_endpoint_works() -> None:
    client, _storage = make_client()

    response = client.get(
        "/api/data/quality/session-aware",
        params={
            "canonical_symbol": "MOEX:SiH6",
            "interval": "1m",
            "from": "2026-03-13",
            "to": "2026-03-14",
        },
    )

    assert response.status_code == 200
    assert response.json()["quality_mode"] == "session_aware"
    assert response.json()["report"]["candles_count"] == 1


def test_api_futures_select_front_endpoint_works() -> None:
    client, _storage = make_client()

    response = client.get(
        "/api/futures/select-front",
        params={"underlying": "Si", "as_of": "2026-03-16"},
    )

    assert response.status_code == 200
    assert response.json()["selected_canonical_symbol"] == "MOEX:SiM6"


def test_api_build_continuous_endpoint_works() -> None:
    client, storage = make_client()

    response = client.post(
        "/api/data/continuous/build",
        json={
            "underlying": "Si",
            "interval": "1m",
            "from": "2026-03-13",
            "to": "2026-03-17",
            "write": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["candles_count"] == 2
    assert storage.get_continuous_series_by_canonical_symbol("MOEX:Si:CONT") is not None
