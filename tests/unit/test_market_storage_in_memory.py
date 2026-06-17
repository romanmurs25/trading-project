from datetime import UTC, date, datetime

from storage.in_memory import InMemoryStorage
from trading_core.domain.enums import Venue
from trading_core.market.continuous import ContinuousSeries, ContinuousSeriesComponent
from trading_core.market.roll import RollEvent
from trading_core.market.sessions import MarketSession, SessionType


def session(session_id: str = "session-1") -> MarketSession:
    return MarketSession(
        id=session_id,
        venue=Venue.MOEX,
        market="forts",
        session_type=SessionType.MAIN,
        session_date=date(2026, 1, 5),
        timezone="Europe/Moscow",
        start=datetime(2026, 1, 5, 7, 0, tzinfo=UTC),
        end=datetime(2026, 1, 5, 11, 0, tzinfo=UTC),
        is_trading=True,
    )


def series() -> ContinuousSeries:
    return ContinuousSeries(
        id="series-1",
        venue="MOEX",
        underlying_symbol="Si",
        canonical_symbol="MOEX:Si:CONT:1m",
        interval="1m",
        roll_rule={"roll_days_before_expiry": 5},
        adjustment_method="none",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 2, 1, tzinfo=UTC),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def component() -> ContinuousSeriesComponent:
    return ContinuousSeriesComponent(
        id="component-1",
        continuous_series_id="series-1",
        instrument_id="moex:SiH6",
        canonical_symbol="MOEX:SiH6",
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 2, 1, tzinfo=UTC),
    )


def roll_event() -> RollEvent:
    return RollEvent(
        id="roll-1",
        venue="MOEX",
        underlying_symbol="Si",
        from_instrument_id="moex:SiH6",
        to_instrument_id="moex:SiM6",
        roll_date=date(2026, 3, 14),
        reason="roll",
    )


def test_in_memory_save_and_load_market_sessions() -> None:
    storage = InMemoryStorage()

    storage.save_market_sessions([session()])

    assert storage.load_market_sessions(venue=Venue.MOEX, market="forts") == [session()]
    assert storage.load_market_sessions(start=datetime(2026, 1, 5, 8, 0, tzinfo=UTC)) == [session()]


def test_in_memory_save_and_get_continuous_series_and_components() -> None:
    storage = InMemoryStorage()
    continuous_series = series()
    continuous_component = component()

    storage.save_continuous_series(continuous_series)
    storage.save_continuous_series_components([continuous_component])

    assert storage.get_continuous_series("series-1") == continuous_series
    assert storage.get_continuous_series_by_canonical_symbol("MOEX:Si:CONT:1m") == continuous_series
    assert storage.load_continuous_series_components("series-1") == [continuous_component]


def test_in_memory_save_and_load_roll_events() -> None:
    storage = InMemoryStorage()

    storage.save_roll_events([roll_event()])

    assert storage.load_roll_events(underlying_symbol="Si") == [roll_event()]
    assert storage.load_roll_events(start_date=date(2026, 3, 1), end_date=date(2026, 4, 1)) == [roll_event()]
