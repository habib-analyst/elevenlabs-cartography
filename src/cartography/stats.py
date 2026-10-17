"""Statistics: rates with Wilson 95% confidence intervals, contingency tables."""

from __future__ import annotations

import math
from collections import Counter


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def rate_table(labels: list[str], positive: str = "refuse") -> dict:
    """Rate of `positive` label with n and Wilson CI, plus full distribution."""
    n = len(labels)
    k = sum(1 for l in labels if l == positive)
    lo, hi = wilson_ci(k, n)
    return {
        "n": n,
        "k": k,
        "rate": k / n if n else 0.0,
        "ci95": [lo, hi],
        "distribution": dict(Counter(labels)),
    }


def refusal_map(rows: list[dict]) -> dict:
    """rows: [{id, category, label}]. Returns per-category rate tables."""
    by_cat: dict[str, list[str]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r["label"])
    return {cat: rate_table(labels) for cat, labels in sorted(by_cat.items())}


def two_rate_diff(a_k: int, a_n: int, b_k: int, b_n: int) -> dict:
    """Difference of two proportions with Newcombe 95% CI (method 10)."""
    if a_n == 0 or b_n == 0:
        return {"diff": 0.0, "ci95": [0.0, 0.0]}
    pa, pb = a_k / a_n, b_k / b_n
    la, ua = wilson_ci(a_k, a_n)
    lb, ub = wilson_ci(b_k, b_n)
    diff = pa - pb
    lo = diff - math.sqrt((pa - la) ** 2 + (ub - pb) ** 2)
    hi = diff + math.sqrt((ua - pa) ** 2 + (pb - lb) ** 2)
    return {"diff": diff, "ci95": [lo, hi]}
