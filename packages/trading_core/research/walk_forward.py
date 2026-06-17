from datetime import datetime, timedelta

from trading_core.domain.errors import DataValidationError
from trading_core.research.models import WalkForwardSplit


def create_walk_forward_splits(
    start: datetime,
    end: datetime,
    train_days: int,
    test_days: int,
    step_days: int,
) -> list[WalkForwardSplit]:
    _validate_window(start, end)
    if train_days <= 0 or test_days <= 0 or step_days <= 0:
        raise DataValidationError("walk-forward day counts must be positive")

    train_delta = timedelta(days=train_days)
    test_delta = timedelta(days=test_days)
    step_delta = timedelta(days=step_days)
    cursor = start
    splits: list[WalkForwardSplit] = []
    while cursor + train_delta + test_delta <= end:
        train_end = cursor + train_delta
        test_end = train_end + test_delta
        splits.append(
            WalkForwardSplit(
                train_start=cursor,
                train_end=train_end,
                test_start=train_end,
                test_end=test_end,
            )
        )
        cursor += step_delta
    return splits


def _validate_window(start: datetime, end: datetime) -> None:
    if start.tzinfo is None or end.tzinfo is None:
        raise DataValidationError("walk-forward datetimes must be timezone-aware")
    if start >= end:
        raise DataValidationError("walk-forward start must be before end")
