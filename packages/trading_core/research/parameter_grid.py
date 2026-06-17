from decimal import Decimal, InvalidOperation
from itertools import product
from typing import Any

from trading_core.domain.errors import DataValidationError

ParameterValue = str | int | Decimal


def parse_parameter_grid(
    raw: dict[str, list[ParameterValue]],
    max_combinations: int = 500,
) -> list[dict[str, object]]:
    if max_combinations <= 0:
        raise DataValidationError("max_combinations must be positive")
    if not raw:
        return [{}]

    keys = list(raw.keys())
    normalized_values: list[list[object]] = []
    combinations_count = 1
    for key in keys:
        values = raw[key]
        if not values:
            raise DataValidationError(f"parameter grid value list is empty: {key}")
        normalized = [_normalize_value(value) for value in values]
        combinations_count *= len(normalized)
        if combinations_count > max_combinations:
            raise DataValidationError(f"parameter grid exceeds max combinations: {max_combinations}")
        normalized_values.append(normalized)

    return [dict(zip(keys, values, strict=True)) for values in product(*normalized_values)]


def _normalize_value(value: Any) -> object:
    if isinstance(value, float):
        raise DataValidationError("float is forbidden in parameter grid")
    if isinstance(value, Decimal | int | bool):
        return value
    if isinstance(value, str):
        return _normalize_string(value)
    raise DataValidationError(f"unsupported parameter grid value: {type(value).__name__}")


def _normalize_string(value: str) -> str | Decimal:
    if not value:
        raise DataValidationError("empty string is not supported in parameter grid")
    if _looks_decimal(value):
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise DataValidationError("invalid decimal string in parameter grid") from exc
    return value


def _looks_decimal(value: str) -> bool:
    if value.startswith(("+", "-")):
        value = value[1:]
    if not value:
        return False
    parts = value.split(".")
    return len(parts) <= 2 and all(part.isdigit() for part in parts if part) and any(parts)
