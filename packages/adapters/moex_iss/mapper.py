from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from trading_core.domain.enums import Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import Candle, Instrument

REQUIRED_COLUMNS = {"begin", "end", "open", "high", "low", "close", "volume"}


def map_candles_payload(
    payload: dict[str, Any],
    instrument: Instrument,
    interval: str,
    exchange_timezone: str = "Europe/Moscow",
) -> list[Candle]:
    table = payload.get("candles")
    if not isinstance(table, dict):
        raise DataValidationError("MOEX ISS payload missing candles table")
    columns_raw = table.get("columns")
    data_raw = table.get("data")
    if not isinstance(columns_raw, list) or not all(isinstance(column, str) for column in columns_raw):
        raise DataValidationError("MOEX ISS candles.columns must be a list of strings")
    if not isinstance(data_raw, list):
        raise DataValidationError("MOEX ISS candles.data must be a list")
    missing = REQUIRED_COLUMNS.difference(columns_raw)
    if missing:
        raise DataValidationError(f"MOEX ISS candles payload missing columns: {', '.join(sorted(missing))}")

    candles: list[Candle] = []
    for row in data_raw:
        if not isinstance(row, list):
            raise DataValidationError("MOEX ISS candle row must be a list")
        candles.append(_map_row(columns_raw, row, instrument, interval, exchange_timezone))
    return candles


def _map_row(
    columns: list[str],
    row: list[Any],
    instrument: Instrument,
    interval: str,
    exchange_timezone: str,
) -> Candle:
    values = _row_values(columns, row)
    return Candle(
        instrument_id=instrument.id,
        venue=Venue.MOEX,
        interval=interval,
        ts_start=_parse_datetime(values["begin"], exchange_timezone),
        ts_end=_parse_datetime(values["end"], exchange_timezone),
        open=_to_decimal(values["open"], "open"),
        high=_to_decimal(values["high"], "high"),
        low=_to_decimal(values["low"], "low"),
        close=_to_decimal(values["close"], "close"),
        volume=_to_decimal(values["volume"], "volume"),
        value=_optional_decimal(values.get("value"), "value"),
        trades_count=_optional_int(values.get("trades"), "trades"),
        source="moex-iss",
    )


def _row_values(columns: list[str], row: list[Any]) -> dict[str, Any]:
    if len(row) < len(columns):
        raise DataValidationError("MOEX ISS candle row shorter than columns")
    return dict(zip(columns, row, strict=False))


def _to_decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, float):
        raise DataValidationError(f"MOEX ISS field {field_name} must not be float")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DataValidationError(f"MOEX ISS field {field_name} is not a valid Decimal") from exc


def _optional_decimal(value: Any, field_name: str) -> Decimal | None:
    if value in (None, ""):
        return None
    return _to_decimal(value, field_name)


def _optional_int(value: Any, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise DataValidationError(f"MOEX ISS field {field_name} is not a valid int") from exc


def _parse_datetime(value: Any, exchange_timezone: str) -> datetime:
    if not isinstance(value, str):
        raise DataValidationError("MOEX ISS datetime value must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError as exc:
        raise DataValidationError("MOEX ISS datetime value is invalid") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(exchange_timezone))
    return parsed.astimezone(UTC)
