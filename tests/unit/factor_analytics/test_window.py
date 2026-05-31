from datetime import date

from app.factor_analytics.constants import (
    DATASET_SPLIT_ALL,
    DATASET_SPLIT_HOLDOUT,
    DATASET_SPLIT_TRAIN,
    DEFAULT_HOLDOUT_START_DATE,
)
from app.factor_analytics.window import include_in_split, split_dataset


def test_split_dataset_train_before_holdout_boundary():
    assert split_dataset(date(2024, 12, 31), DEFAULT_HOLDOUT_START_DATE) == DATASET_SPLIT_TRAIN


def test_split_dataset_holdout_on_or_after_boundary():
    assert split_dataset(date(2025, 1, 1), DEFAULT_HOLDOUT_START_DATE) == DATASET_SPLIT_HOLDOUT
    assert split_dataset(date(2025, 6, 1), DEFAULT_HOLDOUT_START_DATE) == DATASET_SPLIT_HOLDOUT


def test_include_in_split_all():
    holdout = date(2025, 1, 1)
    assert include_in_split(date(2024, 1, 1), DATASET_SPLIT_ALL, holdout)
    assert include_in_split(date(2025, 2, 1), DATASET_SPLIT_ALL, holdout)


def test_include_in_split_train_and_holdout():
    holdout = date(2025, 1, 1)
    assert include_in_split(date(2024, 6, 1), DATASET_SPLIT_TRAIN, holdout)
    assert not include_in_split(date(2025, 2, 1), DATASET_SPLIT_TRAIN, holdout)
    assert include_in_split(date(2025, 2, 1), DATASET_SPLIT_HOLDOUT, holdout)
    assert not include_in_split(date(2024, 6, 1), DATASET_SPLIT_HOLDOUT, holdout)
