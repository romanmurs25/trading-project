from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from trading_core.domain.enums import Venue
from trading_core.market.calendar import MarketCalendarService
from trading_core.market.sessions import MarketSession, SessionState, SessionType, TradingSessionTemplate


def make_calendar() -> MarketCalendarService:
    tz = "Europe/Moscow"
    templates = [
        TradingSessionTemplate(
            venue=Venue.MOEX,
            market="forts",
            session_type=SessionType.MAIN,
            timezone=tz,
            weekdays=[0, 1, 2, 3, 4],
            start_time_local=time(10, 0),
            end_time_local=time(14, 0),
            is_trading=True,
        ),
        TradingSessionTemplate(
            venue=Venue.MOEX,
            market="forts",
            session_type=SessionType.CLEARING,
            timezone=tz,
            weekdays=[0, 1, 2, 3, 4],
            start_time_local=time(14, 0),
            end_time_local=time(14, 5),
            is_trading=False,
        ),
        TradingSessionTemplate(
            venue=Venue.MOEX,
            market="forts",
            session_type=SessionType.EVENING,
            timezone=tz,
            weekdays=[0, 1, 2, 3, 4],
            start_time_local=time(19, 0),
            end_time_local=time(23, 50),
            is_trading=True,
        ),
    ]
    return MarketCalendarService(templates)


def local_dt(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("Europe/Moscow"))


def test_template_generates_utc_sessions() -> None:
    calendar = make_calendar()

    sessions = calendar.sessions_for_date(date(2026, 1, 5))

    assert sessions[0].start == datetime(2026, 1, 5, 7, 0, tzinfo=UTC)
    assert sessions[0].end == datetime(2026, 1, 5, 11, 0, tzinfo=UTC)
    assert sessions[0].session_type == SessionType.MAIN


def test_market_session_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        MarketSession(
            venue=Venue.MOEX,
            market="forts",
            session_type=SessionType.MAIN,
            session_date=date(2026, 1, 5),
            timezone="Europe/Moscow",
            start=datetime(2026, 1, 5, 7, 0),
            end=datetime(2026, 1, 5, 11, 0, tzinfo=UTC),
            is_trading=True,
        )


def test_classifies_main_evening_clearing_and_closed() -> None:
    calendar = make_calendar()

    main = calendar.classify_timestamp(local_dt(2026, 1, 5, 10, 30))
    clearing = calendar.classify_timestamp(local_dt(2026, 1, 5, 14, 2))
    evening = calendar.classify_timestamp(local_dt(2026, 1, 5, 19, 30))
    closed = calendar.classify_timestamp(local_dt(2026, 1, 5, 18, 0))

    assert main.session_type == SessionType.MAIN
    assert main.session_state == SessionState.OPEN
    assert evening.session_type == SessionType.EVENING
    assert evening.is_trading_time is True
    assert clearing.session_type == SessionType.CLEARING
    assert clearing.session_state == SessionState.CLEARING
    assert closed.session_state == SessionState.CLOSED
    assert closed.is_trading_time is False


def test_weekend_and_holiday_are_closed() -> None:
    calendar = MarketCalendarService(make_calendar().templates, holiday_dates={date(2026, 1, 6)})

    weekend = calendar.classify_timestamp(local_dt(2026, 1, 10, 12, 0))
    holiday = calendar.classify_timestamp(local_dt(2026, 1, 6, 12, 0))

    assert weekend.session_type == SessionType.WEEKEND
    assert weekend.session_state == SessionState.CLOSED
    assert holiday.session_type == SessionType.CLOSED
    assert holiday.reason == "holiday"


def test_expected_timestamps_exclude_clearing_and_closed_periods() -> None:
    calendar = make_calendar()

    timestamps = calendar.expected_candle_timestamps(
        local_dt(2026, 1, 5, 13, 58),
        local_dt(2026, 1, 5, 14, 7),
        "1m",
    )

    assert local_dt(2026, 1, 5, 13, 59).astimezone(UTC) in timestamps
    assert local_dt(2026, 1, 5, 14, 1).astimezone(UTC) not in timestamps


def test_next_session_after_returns_following_trading_session() -> None:
    calendar = make_calendar()

    session = calendar.next_session_after(local_dt(2026, 1, 5, 14, 1))

    assert session is not None
    assert session.session_type == SessionType.EVENING
