from datetime import UTC, date, datetime

from trading_core.market.calendar import MarketCalendarService
from trading_core.market.moex_templates import default_moex_futures_session_templates
from trading_core.market.sessions import SessionState, SessionType


def test_default_moex_templates_return_weekday_sessions() -> None:
    templates = default_moex_futures_session_templates()
    calendar = MarketCalendarService(templates)

    sessions = calendar.sessions_for_date(date(2026, 1, 5))

    assert {session.session_type for session in sessions} >= {
        SessionType.MORNING,
        SessionType.MAIN,
        SessionType.EVENING,
        SessionType.CLEARING,
    }
    assert all(session.timezone == "Europe/Moscow" for session in sessions)
    assert all(session.start.tzinfo == UTC for session in sessions)


def test_default_moex_templates_do_not_generate_weekend_sessions() -> None:
    calendar = MarketCalendarService(default_moex_futures_session_templates())

    assert calendar.sessions_for_date(date(2026, 1, 10)) == []


def test_moex_clearing_interval_classified_as_clearing() -> None:
    calendar = MarketCalendarService(default_moex_futures_session_templates())

    classification = calendar.classify_timestamp(datetime(2026, 1, 5, 11, 2, tzinfo=UTC))

    assert classification.session_type == SessionType.CLEARING
    assert classification.session_state == SessionState.CLEARING
    assert classification.is_trading_time is False
