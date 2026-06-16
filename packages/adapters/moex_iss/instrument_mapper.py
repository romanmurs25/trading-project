from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from trading_core.domain.enums import AssetClass, Venue
from trading_core.domain.errors import DataValidationError
from trading_core.domain.models import ContractSpec, Instrument

FUTURES_ENGINE = "futures"
FUTURES_MARKET = "forts"
DEFAULT_CURRENCY = "RUB"
DEFAULT_DECIMAL = Decimal("1")


def parse_iss_table(payload: dict[str, Any], table_name: str) -> list[dict[str, Any]]:
    table = payload.get(table_name)
    if not isinstance(table, dict):
        raise DataValidationError(f"MOEX ISS payload missing {table_name} table")
    columns_raw = table.get("columns")
    data_raw = table.get("data")
    if not isinstance(columns_raw, list) or not all(isinstance(column, str) for column in columns_raw):
        raise DataValidationError(f"MOEX ISS {table_name}.columns must be a list of strings")
    if not isinstance(data_raw, list):
        raise DataValidationError(f"MOEX ISS {table_name}.data must be a list")

    rows: list[dict[str, Any]] = []
    for row in data_raw:
        if not isinstance(row, list):
            raise DataValidationError(f"MOEX ISS {table_name} row must be a list")
        if len(row) != len(columns_raw):
            raise DataValidationError(f"MOEX ISS {table_name} row length must match columns")
        rows.append(dict(zip(columns_raw, row, strict=True)))
    return rows


def map_futures_instruments(payload: dict[str, Any]) -> list[Instrument]:
    return [_instrument_from_row(row) for row in parse_iss_table(payload, "securities")]


def map_futures_contract_specs(payload: dict[str, Any]) -> list[ContractSpec]:
    return [_contract_spec_from_row(row) for row in parse_iss_table(payload, "securities")]


def _instrument_from_row(row: dict[str, Any]) -> Instrument:
    native_symbol = _required_string(row, ("SECID", "secid"), "SECID")
    spec_incomplete = _is_spec_incomplete(row)
    return Instrument(
        id=_instrument_id(native_symbol),
        venue=Venue.MOEX,
        asset_class=AssetClass.FUTURES,
        native_symbol=native_symbol,
        canonical_symbol=_canonical_symbol(native_symbol),
        name=_optional_string(row, ("SECNAME", "SHORTNAME", "NAME", "secname")) or native_symbol,
        lot_size=_decimal_or_default(row, ("LOTSIZE", "LOTVOLUME", "lotsize")),
        tick_size=_decimal_or_default(row, ("MINSTEP", "STEP", "minstep")),
        tick_value=_decimal_or_default(row, ("STEPPRICE", "TICKVALUE", "stepprice")),
        currency=_optional_string(row, ("FACEUNIT", "CURRENCYID", "currencyid")) or DEFAULT_CURRENCY,
        expiry_date=_optional_date(row, ("MATDATE", "EXPIRATIONDATE", "matdate")),
        is_active=_is_active(row),
        metadata=_metadata(row, spec_incomplete=spec_incomplete),
    )


def _contract_spec_from_row(row: dict[str, Any]) -> ContractSpec:
    native_symbol = _required_string(row, ("SECID", "secid"), "SECID")
    spec_incomplete = _is_spec_incomplete(row)
    return ContractSpec(
        instrument_id=_instrument_id(native_symbol),
        lot_size=_decimal_or_default(row, ("LOTSIZE", "LOTVOLUME", "lotsize")),
        tick_size=_decimal_or_default(row, ("MINSTEP", "STEP", "minstep")),
        tick_value=_decimal_or_default(row, ("STEPPRICE", "TICKVALUE", "stepprice")),
        currency=_optional_string(row, ("FACEUNIT", "CURRENCYID", "currencyid")) or DEFAULT_CURRENCY,
        expiry_date=_optional_date(row, ("MATDATE", "EXPIRATIONDATE", "matdate")),
        first_trade_date=_optional_date(row, ("FIRSTTRADEDATE", "FIRSTTRADE", "firsttradedate")),
        last_trade_date=_optional_date(row, ("LASTTRADEDATE", "LASTTRADE", "lasttradedate")),
        underlying_symbol=_optional_string(row, ("ASSETCODE", "UNDERLYINGASSET", "underlyingasset")),
        metadata=_metadata(row, spec_incomplete=spec_incomplete),
    )


def _metadata(row: dict[str, Any], *, spec_incomplete: bool) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "moex_engine": FUTURES_ENGINE,
        "moex_market": FUTURES_MARKET,
        "source": "moex-iss",
        "spec_incomplete": spec_incomplete,
    }
    board = _optional_string(row, ("BOARDID", "boardid"))
    if board is not None:
        metadata["moex_board"] = board
    return metadata


def _is_spec_incomplete(row: dict[str, Any]) -> bool:
    required_groups: tuple[tuple[str, ...], ...] = (
        ("LOTSIZE", "LOTVOLUME", "lotsize"),
        ("MINSTEP", "STEP", "minstep"),
        ("STEPPRICE", "TICKVALUE", "stepprice"),
        ("FACEUNIT", "CURRENCYID", "currencyid"),
    )
    return any(_first_present(row, names) in (None, "") for names in required_groups)


def _is_active(row: dict[str, Any]) -> bool:
    status = (_optional_string(row, ("STATUS", "STATUSNAME", "status")) or "A").lower()
    return status not in {"d", "n", "inactive", "disabled", "delisted"}


def _instrument_id(native_symbol: str) -> str:
    return f"moex:{native_symbol}"


def _canonical_symbol(native_symbol: str) -> str:
    return f"MOEX:{native_symbol}"


def _required_string(row: dict[str, Any], names: Sequence[str], field_name: str) -> str:
    value = _optional_string(row, names)
    if value is None:
        raise DataValidationError(f"MOEX ISS field {field_name} is required")
    return value


def _optional_string(row: dict[str, Any], names: Sequence[str]) -> str | None:
    value = _first_present(row, names)
    if value in (None, ""):
        return None
    if isinstance(value, float):
        raise DataValidationError("MOEX ISS string field must not be float")
    return str(value)


def _decimal_or_default(row: dict[str, Any], names: Sequence[str]) -> Decimal:
    value = _first_present(row, names)
    if value in (None, ""):
        return DEFAULT_DECIMAL
    if isinstance(value, float):
        raise DataValidationError("MOEX ISS Decimal field must not be float")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DataValidationError("MOEX ISS Decimal field is invalid") from exc


def _optional_date(row: dict[str, Any], names: Sequence[str]) -> date | None:
    value = _first_present(row, names)
    if value in (None, ""):
        return None
    if isinstance(value, float):
        raise DataValidationError("MOEX ISS date field must not be float")
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise DataValidationError("MOEX ISS date field is invalid") from exc


def _first_present(row: dict[str, Any], names: Sequence[str]) -> Any | None:
    for name in names:
        if name in row:
            return row[name]
    return None
