from datetime import date, datetime, time
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from trading_core.domain.enums import Venue
from trading_core.domain.models import DomainModel, new_id


class SessionType(StrEnum):
    MORNING = "MORNING"
    MAIN = "MAIN"
    EVENING = "EVENING"
    WEEKEND = "WEEKEND"
    CLEARING = "CLEARING"
    CLOSED = "CLOSED"


class SessionState(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CLEARING = "CLEARING"
    PREOPEN = "PREOPEN"
    UNKNOWN = "UNKNOWN"


class TradingSessionTemplate(DomainModel):
    venue: Venue
    market: str
    session_type: SessionType
    timezone: str
    weekdays: list[int]
    start_time_local: time
    end_time_local: time
    is_trading: bool
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, weekdays: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in weekdays):
            raise ValueError("weekdays must use Python weekday numbers 0..6")
        return weekdays


class MarketSession(DomainModel):
    id: str = Field(default_factory=new_id)
    venue: Venue
    market: str
    session_type: SessionType
    session_date: date
    timezone: str
    start: datetime
    end: datetime
    is_trading: bool
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("end")
    @classmethod
    def validate_end_after_start(cls, end: datetime, info: Any) -> datetime:
        start = info.data.get("start")
        if isinstance(start, datetime) and end <= start:
            raise ValueError("session end must be after start")
        return end


class MarketCalendarDay(DomainModel):
    venue: Venue
    market: str
    date: date
    is_trading_day: bool
    sessions: list[MarketSession]
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionClassification(DomainModel):
    ts: datetime
    venue: Venue
    market: str
    session_type: SessionType
    session_state: SessionState
    session_id: str | None = None
    session_date: date | None = None
    is_trading_time: bool
    reason: str
