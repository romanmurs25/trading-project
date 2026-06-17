from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import Side
from trading_core.market.continuous import ContinuousSeries, ContinuousSeriesComponent
from trading_core.market.roll import RollEvent
from trading_core.research.models import (
    BacktestEquityPoint,
    BacktestTradeRecord,
    ResearchBacktestResult,
    ResearchRun,
    ResearchStatus,
)

from apps.api.main import create_app


def aware(month: int = 1, day: int = 1) -> datetime:
    return datetime(2026, month, day, tzinfo=UTC)


def make_client() -> tuple[TestClient, InMemoryStorage]:
    app = create_app()
    storage = InMemoryStorage()
    storage.save_research_run(
        ResearchRun(
            id="research-1",
            strategy_id="opening_range_breakout",
            canonical_symbol="MOEX:SiH6",
            instrument_id="moex:SiH6",
            interval="1m",
            start=aware(),
            end=aware(day=2),
            parameter_grid={"opening_range_minutes": [5]},
            data_quality_gate={},
            status=ResearchStatus.COMPLETED,
        )
    )
    storage.save_research_backtest_result(
        ResearchBacktestResult(
            id="result-1",
            research_run_id="research-1",
            backtest_run_id="bt-1",
            strategy_id="opening_range_breakout",
            canonical_symbol="MOEX:SiH6",
            instrument_id="moex:SiH6",
            interval="1m",
            start=aware(),
            end=aware(day=2),
            params={"opening_range_minutes": 5},
            metrics={"profit_factor": "1.5"},
            quality_report={"warnings": []},
            status=ResearchStatus.COMPLETED,
        )
    )
    storage.save_backtest_equity_points(
        [
            BacktestEquityPoint(
                id="eq-1",
                backtest_run_id="bt-1",
                ts=aware(),
                equity=Decimal("100000"),
                drawdown=Decimal("0"),
            )
        ]
    )
    storage.save_backtest_trade_records(
        [
            BacktestTradeRecord(
                id="trade-1",
                backtest_run_id="bt-1",
                instrument_id="moex:SiH6",
                side=Side.BUY,
                entry_ts=aware(),
                exit_ts=aware(day=2),
                entry_price=Decimal("100"),
                exit_price=Decimal("110"),
                qty=Decimal("1"),
                gross_pnl=Decimal("10"),
                net_pnl=Decimal("9"),
                r_multiple=Decimal("1.2"),
                reason="paper closed trade",
            )
        ]
    )
    storage.save_continuous_series(
        ContinuousSeries(
            id="series-1",
            venue="MOEX",
            underlying_symbol="Si",
            canonical_symbol="MOEX:Si:CONT:1m",
            interval="1m",
            roll_rule={"roll_days_before_expiry": 5},
            adjustment_method="none",
            start=aware(),
            end=aware(day=2),
            created_at=aware(),
        )
    )
    storage.save_continuous_series_components(
        [
            ContinuousSeriesComponent(
                id="component-1",
                continuous_series_id="series-1",
                instrument_id="moex:SiH6",
                canonical_symbol="MOEX:SiH6",
                start=aware(),
                end=aware(day=2),
            )
        ]
    )
    storage.save_roll_events(
        [
            RollEvent(
                id="roll-1",
                venue="MOEX",
                underlying_symbol="Si",
                from_instrument_id="moex:SiH6",
                to_instrument_id="moex:SiM6",
                roll_date=date(2026, 3, 14),
                reason="roll 5 days before expiry",
            )
        ]
    )
    app.state.storage = storage
    return TestClient(app), storage


def test_api_research_equity_endpoint() -> None:
    client, _storage = make_client()

    response = client.get("/api/research/runs/research-1/equity")

    assert response.status_code == 200
    assert response.json()["research_run_id"] == "research-1"
    assert response.json()["points"][0]["backtest_run_id"] == "bt-1"
    assert response.json()["points"][0]["equity"] == "100000"


def test_api_research_trades_endpoint() -> None:
    client, _storage = make_client()

    response = client.get("/api/research/runs/research-1/trades")

    assert response.status_code == 200
    assert response.json()["research_run_id"] == "research-1"
    assert response.json()["trades"][0]["backtest_run_id"] == "bt-1"
    assert response.json()["trades"][0]["net_pnl"] == "9"


def test_api_continuous_series_list_endpoint() -> None:
    client, _storage = make_client()

    response = client.get("/api/continuous-series", params={"underlying_symbol": "Si", "interval": "1m"})

    assert response.status_code == 200
    assert response.json()[0]["canonical_symbol"] == "MOEX:Si:CONT:1m"


def test_api_continuous_series_components_endpoint() -> None:
    client, _storage = make_client()

    response = client.get("/api/continuous-series/series-1/components")

    assert response.status_code == 200
    assert response.json()["continuous_series_id"] == "series-1"
    assert response.json()["components"][0]["canonical_symbol"] == "MOEX:SiH6"


def test_api_roll_events_endpoint() -> None:
    client, _storage = make_client()

    response = client.get(
        "/api/roll-events",
        params={"underlying_symbol": "Si", "from": "2026-03-01", "to": "2026-04-01"},
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == "roll-1"
