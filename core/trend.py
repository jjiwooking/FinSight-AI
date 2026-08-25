from __future__ import annotations

import math
import re
import statistics
from typing import Any

from .utils import pct_change


def _period_sort_key(period: str) -> tuple[int, str]:
    match = re.search(r"20\d{2}", str(period))
    return (int(match.group(0)) if match else 9999, str(period))


def period_entries(series: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(series, dict):
        return []
    out: list[dict[str, Any]] = []
    for period, value in series.items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            out.append({"period": str(period), "value": number})
    return sorted(out, key=lambda x: _period_sort_key(x["period"]))


def pattern_signal(series: dict[str, Any] | None) -> dict[str, Any]:
    entries = period_entries(series)
    if len(entries) < 3:
        return {"available": False, "score": None, "entries": entries, "reason": "3개 이상 기간 필요"}
    changes: list[dict[str, Any]] = []
    for left, right in zip(entries, entries[1:]):
        change = pct_change(left["value"], right["value"])
        if change is not None and math.isfinite(change):
            changes.append({"from": left["period"], "to": right["period"], "change": change})
    if len(changes) < 2:
        return {"available": False, "score": None, "entries": entries, "reason": "비교 가능한 증감률 부족"}

    latest = changes[-1]["change"]
    history = [x["change"] for x in changes[:-1]]
    baseline = statistics.median(history)
    deviations = [abs(x - baseline) for x in history]
    mad = statistics.median(deviations) if deviations else 0.0
    scale = max(8.0, 1.4826 * mad)
    robust_z = abs(latest - baseline) / scale
    if robust_z >= 4:
        score = 20
    elif robust_z >= 3:
        score = 17
    elif robust_z >= 2:
        score = 13
    elif robust_z >= 1.25:
        score = 8
    elif robust_z >= 0.75:
        score = 4
    else:
        score = 0
    return {
        "available": True,
        "score": score,
        "entries": entries,
        "latest": latest,
        "baseline": baseline,
        "robust_z": robust_z,
        "reason": f"최근 {latest:+.1f}% · 과거 변화 중앙값 {baseline:+.1f}%",
    }
