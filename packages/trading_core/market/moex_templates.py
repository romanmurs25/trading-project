from datetime import time

from trading_core.domain.enums import Venue
from trading_core.market.sessions import SessionType, TradingSessionTemplate

MOEX_FUTURES_TIMEZONE = "Europe/Moscow"
MOEX_FORTS_MARKET = "forts"
MOEX_WEEKDAYS = [0, 1, 2, 3, 4]

# Configurable MVP defaults. They are intentionally centralized and documented as
# research templates, not official production exchange calendar truth.
MOEX_MORNING_START = time(7, 0)
MOEX_MORNING_END = time(10, 0)
MOEX_MAIN_START = time(10, 0)
MOEX_DAY_CLEARING_START = time(14, 0)
MOEX_DAY_CLEARING_END = time(14, 5)
MOEX_MAIN_AFTER_CLEARING_START = time(14, 5)
MOEX_MAIN_END = time(18, 45)
MOEX_EVENING_CLEARING_START = time(18, 45)
MOEX_EVENING_CLEARING_END = time(19, 0)
MOEX_EVENING_START = time(19, 0)
MOEX_EVENING_END = time(23, 50)


def default_moex_futures_session_templates() -> list[TradingSessionTemplate]:
    return [
        _template(SessionType.MORNING, MOEX_MORNING_START, MOEX_MORNING_END, True),
        _template(SessionType.MAIN, MOEX_MAIN_START, MOEX_DAY_CLEARING_START, True),
        _template(SessionType.CLEARING, MOEX_DAY_CLEARING_START, MOEX_DAY_CLEARING_END, False),
        _template(SessionType.MAIN, MOEX_MAIN_AFTER_CLEARING_START, MOEX_MAIN_END, True),
        _template(SessionType.CLEARING, MOEX_EVENING_CLEARING_START, MOEX_EVENING_CLEARING_END, False),
        _template(SessionType.EVENING, MOEX_EVENING_START, MOEX_EVENING_END, True),
    ]


def _template(
    session_type: SessionType,
    start_time_local: time,
    end_time_local: time,
    is_trading: bool,
) -> TradingSessionTemplate:
    return TradingSessionTemplate(
        venue=Venue.MOEX,
        market=MOEX_FORTS_MARKET,
        session_type=session_type,
        timezone=MOEX_FUTURES_TIMEZONE,
        weekdays=MOEX_WEEKDAYS,
        start_time_local=start_time_local,
        end_time_local=end_time_local,
        is_trading=is_trading,
        metadata={"source": "configurable_mvp_default"},
    )
