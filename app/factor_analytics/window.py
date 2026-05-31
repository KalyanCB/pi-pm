from __future__ import annotations

from datetime import date

from app.factor_analytics.constants import (
    DATASET_SPLIT_ALL,
    DATASET_SPLIT_HOLDOUT,
    DATASET_SPLIT_TRAIN,
)


def split_dataset(as_of_date: date, holdout_start_date: date) -> str:
    return DATASET_SPLIT_HOLDOUT if as_of_date >= holdout_start_date else DATASET_SPLIT_TRAIN


def include_in_split(as_of_date: date, dataset_split: str, holdout_start_date: date) -> bool:
    if dataset_split == DATASET_SPLIT_ALL:
        return True
    return split_dataset(as_of_date, holdout_start_date) == dataset_split
