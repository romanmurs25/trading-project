from datetime import UTC, datetime

import pytest
from trading_core.domain.errors import DataValidationError
from trading_core.research.walk_forward import create_walk_forward_splits


def test_walk_forward_splits_generated() -> None:
    splits = create_walk_forward_splits(
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 4, 1, tzinfo=UTC),
        train_days=30,
        test_days=10,
        step_days=20,
    )

    assert len(splits) == 3
    assert splits[0].train_start == datetime(2026, 1, 1, tzinfo=UTC)
    assert splits[0].train_end == datetime(2026, 1, 31, tzinfo=UTC)
    assert splits[0].test_end == datetime(2026, 2, 10, tzinfo=UTC)


def test_walk_forward_rejects_invalid_ranges() -> None:
    with pytest.raises(DataValidationError):
        create_walk_forward_splits(
            datetime(2026, 1, 2, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
            train_days=30,
            test_days=10,
            step_days=10,
        )


def test_walk_forward_rejects_non_positive_days() -> None:
    with pytest.raises(DataValidationError):
        create_walk_forward_splits(
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 2, 1, tzinfo=UTC),
            train_days=0,
            test_days=10,
            step_days=10,
        )


def test_walk_forward_rejects_naive_datetime() -> None:
    with pytest.raises(DataValidationError):
        create_walk_forward_splits(
            datetime(2026, 1, 1),
            datetime(2026, 2, 1, tzinfo=UTC),
            train_days=10,
            test_days=5,
            step_days=5,
        )
