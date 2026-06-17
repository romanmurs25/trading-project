from datetime import UTC, date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from storage.sqlalchemy_models import Base, ContinuousSeriesRow
from storage.sqlalchemy_repositories import SQLAlchemyStorage
from trading_core.domain.enums import Venue
from trading_core.market.continuous import ContinuousSeries, ContinuousSeriesComponent
from trading_core.market.roll import RollEvent
from trading_core.market.sessions import MarketSession, SessionType


def make_storage() -> SQLAlchemyStorage:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return SQLAlchemyStorage(sessionmaker(bind=engine))


def session() -> MarketSession:
    return MarketSession(
        id="session-1",
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


def test_sqlalchemy_save_and_load_market_sessions() -> None:
    storage = make_storage()

    storage.save_market_sessions([session()])

    assert storage.load_market_sessions(venue=Venue.MOEX, market="forts") == [session()]


def test_sqlalchemy_save_and_get_continuous_series_and_components() -> None:
    storage = make_storage()
    continuous_series = series()
    continuous_component = component()

    storage.save_continuous_series(continuous_series)
    storage.save_continuous_series_components([continuous_component])

    assert storage.get_continuous_series("series-1") == continuous_series
    assert storage.get_continuous_series_by_canonical_symbol("MOEX:Si:CONT:1m") == continuous_series
    assert storage.load_continuous_series_components("series-1") == [continuous_component]


def test_sqlalchemy_save_continuous_series_upserts_by_canonical_symbol() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    storage = SQLAlchemyStorage(sessionmaker(bind=engine))
    first = series()
    second = first.model_copy(
        update={
            "id": "series-2",
            "start": datetime(2026, 2, 1, tzinfo=UTC),
            "metadata": {"updated": True},
        }
    )

    storage.save_continuous_series(first)
    storage.save_continuous_series(second)

    with sessionmaker(bind=engine)() as session:
        rows = session.scalars(select(ContinuousSeriesRow)).all()
    saved = storage.get_continuous_series_by_canonical_symbol("MOEX:Si:CONT:1m")

    assert len(rows) == 1
    assert saved == second


def test_sqlalchemy_save_and_load_roll_events() -> None:
    storage = make_storage()

    storage.save_roll_events([roll_event()])

    assert storage.load_roll_events(underlying_symbol="Si") == [roll_event()]
    assert storage.load_roll_events(start_date=date(2026, 3, 1), end_date=date(2026, 4, 1)) == [roll_event()]
