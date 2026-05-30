from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def percentile_normalize(values: dict[str, Decimal | None]) -> dict[str, Decimal]:
    valid = {k: v for k, v in values.items() if v is not None}
    if not valid:
        return {k: Decimal("0") for k in values}
    if len(valid) == 1:
        only_key = next(iter(valid))
        return {k: Decimal("0.5") if k == only_key else Decimal("0") for k in values}

    sorted_items = sorted(valid.items(), key=lambda item: (item[1], item[0]))
    n = len(sorted_items)
    result: dict[str, Decimal] = {k: Decimal("0") for k in values}

    index = 0
    while index < n:
        j = index
        while j + 1 < n and sorted_items[j + 1][1] == sorted_items[index][1]:
            j += 1
        if n == 1:
            percentile = Decimal("0.5")
        else:
            percentile = Decimal(str((index + j) / 2)) / Decimal(str(n - 1))
        percentile = percentile.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        for k, _ in sorted_items[index : j + 1]:
            result[k] = percentile
        index = j + 1

    return result


def redistribute_weights(weights: dict[str, Decimal], excluded: set[str]) -> dict[str, Decimal]:
    active = {k: v for k, v in weights.items() if k not in excluded}
    total = sum(active.values())
    if total <= 0:
        return active
    return {
        k: (v / total).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        for k, v in active.items()
    }
