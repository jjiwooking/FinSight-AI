from __future__ import annotations

import math
import re
from typing import Any


def norm_account(value: Any) -> str:
    text = str(value or "")
    return re.sub(r"[\s()·ㆍ,._-]+", "", text).lower()


def pct_change(prior: Any, current: Any) -> float | None:
    try:
        a = float(prior)
        b = float(current)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(a) and math.isfinite(b)):
        return None
    if a == 0:
        return 0.0 if b == 0 else None
    return (b - a) / abs(a) * 100.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def unit_label(multiplier: int | float) -> str:
    return {
        1: "원",
        1_000: "천원",
        1_000_000: "백만원",
        100_000_000: "억원",
    }.get(int(multiplier), "원")
