from __future__ import annotations

import math
import re
from typing import Any

MONEY_UNITS: dict[str, int] = {
    "원": 1,
    "천원": 1_000,
    "백만원": 1_000_000,
    "억원": 100_000_000,
}


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


def money_unit_multiplier(unit: str) -> int:
    return MONEY_UNITS.get(str(unit or "원"), 1)


def format_money(value: Any, *, unit: str = "원", include_unit: bool = False) -> str:
    """Format KRW amounts with thousands separators without changing stored precision.

    All FinSight engine calculations remain in KRW. The unit argument only controls
    presentation. Examples: 1000000 -> '1,000,000' in won, or '1' in million won.
    """
    if value is None:
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(n):
        return "—"

    multiplier = money_unit_multiplier(unit)
    scaled = n / multiplier
    abs_scaled = abs(scaled)

    if multiplier == 1:
        text = f"{scaled:,.0f}"
    elif multiplier == 1_000:
        text = f"{scaled:,.1f}".rstrip("0").rstrip(".")
    else:
        text = f"{scaled:,.2f}".rstrip("0").rstrip(".")

    return f"{text} {unit}" if include_unit else text
