from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from trading_core.domain.errors import DataValidationError
from trading_core.market.sessions import (
    MarketSession,
    SessionClassification,
    SessionState,
    SessionType,
    TradingSessionTemplate,
)

_INTERVALS = {
    "1m": timedelta(minutes=1),
    "10m": timedelta(minutes=10),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}


class MarketCalendarService:
    def __init__(
        self,
        templates: list[TradingSessionTemplate],
        holiday_dates: set[date] | None = None,
        special_days: dict[date, list[TradingSessionTemplate]] | None = None,
    ) -> None:
        if not templates:
            raise DataValidationError("market calendar requires at least one template")
        self.templates = templates
        self.holiday_dates = holiday_dates or set()
        self.special_days = special_days or {}

    def generate_sessions(self, start: datetime, end: datetime) -> list[MarketSession]:
        _require_aware(start, "start")
        _require_aware(end, "end")
        if start >= end:
            raise DataValidationError("start must be before end")
        sessions: list[MarketSession] = []
        current = start.astimezone(UTC).date()
        last = end.astimezone(UTC).date()
        while current <= last:
            sessions.extend(
                session
                for session in self.sessions_for_date(current)
                if session.start < end.astimezone(UTC) and session.end > start.astimezone(UTC)
            )
            current += timedelta(days=1)
        return sorted(sessions, key=lambda session: session.start)

    def sessions_for_date(self, target_date: date) -> list[MarketSession]:
        if target_date in self.holiday_dates:
            return []
        templates = self.special_days.get(target_date, self.templates)
        sessions = [
            _session_from_template(template, target_date)
            for template in templates
            if target_date.weekday() in template.weekdays
        ]
        return sorted(sessions, key=lambda session: session.start)

    def classify_timestamp(self, ts: datetime) -> SessionClassification:
        _require_aware(ts, "ts")
        ts_utc = ts.astimezone(UTC)
        venue = self.templates[0].venue
        market = self.templates[0].market
        local_date = ts_utc.astimezone(ZoneInfo(self.templates[0].timezone)).date()
        if local_date in self.holiday_dates:
            return SessionClassification(
                ts=ts_utc,
                venue=venue,
                market=market,
                session_type=SessionType.CLOSED,
                session_state=SessionState.CLOSED,
                session_date=local_date,
                is_trading_time=False,
                reason="holiday",
            )
        for session in self.sessions_for_date(local_date):
            if session.start <= ts_utc < session.end:
                state = SessionState.OPEN if session.is_trading else SessionState.CLOSED
                if session.session_type == SessionType.CLEARING:
                    state = SessionState.CLEARING
                return SessionClassification(
                    ts=ts_utc,
                    venue=session.venue,
                    market=session.market,
                    session_type=session.session_type,
                    session_state=state,
                    session_id=session.id,
                    session_date=session.session_date,
                    is_trading_time=session.is_trading,
                    reason="inside trading session" if session.is_trading else "inside non-trading session",
                )
        session_type = SessionType.WEEKEND if local_date.weekday() >= 5 else SessionType.CLOSED
        return SessionClassification(
            ts=ts_utc,
            venue=venue,
            market=market,
            session_type=session_type,
            session_state=SessionState.CLOSED,
            session_date=local_date,
            is_trading_time=False,
            reason="outside configured sessions",
        )

    def expected_candle_timestamps(self, start: datetime, end: datetime, interval: str) -> list[datetime]:
        _require_aware(start, "start")
        _require_aware(end, "end")
        if start >= end:
            raise DataValidationError("start must be before end")
        step = _interval_delta(interval)
        timestamps: list[datetime] = []
        for session in self.generate_sessions(start, end):
            if not session.is_trading:
                continue
            current = max(start.astimezone(UTC), session.start)
            stop = min(end.astimezone(UTC), session.end)
            while current < stop:
                timestamps.append(current)
                current += step
        return sorted(dict.fromkeys(timestamps))

    def is_trading_time(self, ts: datetime) -> bool:
        return self.classify_timestamp(ts).is_trading_time

    def next_session_after(self, ts: datetime) -> MarketSession | None:
        _require_aware(ts, "ts")
        search_end = ts.astimezone(UTC) + timedelta(days=14)
        sessions = [
            session
            for session in self.generate_sessions(ts, search_end)
            if session.is_trading and session.start > ts.astimezone(UTC)
        ]
        return sessions[0] if sessions else None


def _session_from_template(template: TradingSessionTemplate, session_date: date) -> MarketSession:
    tz = ZoneInfo(template.timezone)
    local_start = datetime.combine(session_date, template.start_time_local, tzinfo=tz)
    local_end = datetime.combine(session_date, template.end_time_local, tzinfo=tz)
    start = local_start.astimezone(UTC)
    end = local_end.astimezone(UTC)
    return MarketSession(
        id=(
            f"{template.venue.value}:{template.market}:{session_date.isoformat()}:"
            f"{template.session_type.value}:{template.start_time_local.isoformat()}"
        ),
        venue=template.venue,
        market=template.market,
        session_type=template.session_type,
        session_date=session_date,
        timezone=template.timezone,
        start=start,
        end=end,
        is_trading=template.is_trading,
        metadata=dict(template.metadata),
    )


def _interval_delta(interval: str) -> timedelta:
    try:
        return _INTERVALS[interval]
    except KeyError as exc:
        raise DataValidationError(f"unsupported interval for session calendar: {interval}") from exc


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
