from decimal import Decimal

import pytest
from trading_core.domain.errors import DataValidationError
from trading_core.research.parameter_grid import parse_parameter_grid


def test_parameter_grid_cartesian_product_and_decimal_strings() -> None:
    combinations = parse_parameter_grid(
        {
            "opening_range_minutes": [5, 15],
            "take_profit_r_multiple": ["1.5", "2"],
            "max_trades_per_session": [1],
        }
    )

    assert combinations == [
        {
            "opening_range_minutes": 5,
            "take_profit_r_multiple": Decimal("1.5"),
            "max_trades_per_session": 1,
        },
        {
            "opening_range_minutes": 5,
            "take_profit_r_multiple": Decimal("2"),
            "max_trades_per_session": 1,
        },
        {
            "opening_range_minutes": 15,
            "take_profit_r_multiple": Decimal("1.5"),
            "max_trades_per_session": 1,
        },
        {
            "opening_range_minutes": 15,
            "take_profit_r_multiple": Decimal("2"),
            "max_trades_per_session": 1,
        },
    ]


def test_parameter_grid_rejects_empty_values() -> None:
    with pytest.raises(DataValidationError):
        parse_parameter_grid({"opening_range_minutes": []})


def test_parameter_grid_rejects_too_many_combinations() -> None:
    with pytest.raises(DataValidationError):
        parse_parameter_grid({"a": list(range(30)), "b": list(range(30))}, max_combinations=500)


def test_parameter_grid_rejects_float_values() -> None:
    with pytest.raises(DataValidationError):
        parse_parameter_grid({"take_profit_r_multiple": [1.5]})


def test_parameter_grid_accepts_empty_grid_as_one_default_combination() -> None:
    assert parse_parameter_grid({}) == [{}]
