from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd

from .trend import pattern_signal
from .utils import clamp, norm_account, pct_change


def _active(df: pd.DataFrame) -> pd.DataFrame:
    if "included" in df.columns:
        return df[df["included"].fillna(True).astype(bool)].copy()
    return df.copy()


def _find_account(df: pd.DataFrame, aliases: list[str], statement: str | None = None) -> pd.Series | None:
    keys = {norm_account(a) for a in aliases}
    for _, row in df.iterrows():
        if statement and row.get("statement") != statement:
            continue
        if norm_account(row.get("account")) in keys:
            return row
    return None


def _benchmark(row: pd.Series, rows: pd.DataFrame) -> dict[str, Any] | None:
    statement = row.get("statement")
    if statement == "손익계산서":
        target = _find_account(rows, ["매출액", "매출", "영업수익"], "손익계산서")
        label = "매출액"
    elif statement == "재무상태표":
        target = _find_account(rows, ["자산총계", "총자산", "자산 합계"], "재무상태표")
        label = "자산총계"
    elif statement == "현금흐름표":
        target = _find_account(rows, ["기말현금및현금성자산", "기말현금"])
        label = "기말 현금및현금성자산"
    else:
        return None
    if target is None:
        return None
    try:
        if int(target.get("id", -1)) == int(row.get("id", -2)):
            return None
    except (TypeError, ValueError):
        pass
    try:
        value = abs(float(target["current"]))
    except (TypeError, ValueError):
        return None
    return {"value": value, "label": label} if value > 0 else None


def _priority_parts(row: pd.Series, rows: pd.DataFrame) -> dict[str, Any]:
    prior, current = row.get("prior"), row.get("current")
    try:
        p, c = float(prior), float(current)
    except (TypeError, ValueError):
        return {
            "magnitude": 0,
            "materiality": None,
            "materiality_ratio": None,
            "benchmark": None,
            "relation": 0,
            "relation_text": [],
            "pattern": {"available": False, "score": None, "reason": "금액 데이터 부족"},
            "priority": 0,
        }
    if not (math.isfinite(p) and math.isfinite(c)):
        return {
            "magnitude": 0,
            "materiality": None,
            "materiality_ratio": None,
            "benchmark": None,
            "relation": 0,
            "relation_text": [],
            "pattern": {"available": False, "score": None, "reason": "금액 데이터 부족"},
            "priority": 0,
        }

    change = pct_change(p, c)
    abs_change = abs(c - p)
    if change is None:
        magnitude = 8 if abs_change > 0 else 0
    else:
        a = abs(change)
        if a >= 200:
            magnitude = 20
        elif a >= 100:
            magnitude = 16
        elif a >= 50:
            magnitude = 12
        elif a >= 25:
            magnitude = 7
        else:
            magnitude = round(a / 25 * 5)

    benchmark = _benchmark(row, rows)
    materiality = None
    materiality_ratio = None
    if benchmark:
        ratio = abs_change / max(float(benchmark["value"]), 1.0)
        materiality_ratio = ratio
        if ratio >= 0.10:
            materiality = 25
        elif ratio >= 0.05:
            materiality = 20
        elif ratio >= 0.02:
            materiality = 14
        elif ratio >= 0.01:
            materiality = 9
        else:
            materiality = round(clamp(ratio / 0.01 * 6, 0, 6))

    relation = 0
    relation_text: list[str] = []
    rev = _find_account(rows, ["매출액", "매출", "영업수익"], "손익계산서")
    rev_change = pct_change(rev.get("prior"), rev.get("current")) if rev is not None else None
    account = norm_account(row.get("account"))
    if account == norm_account("영업활동현금흐름") and rev_change is not None and rev_change > 0 and change is not None and change < 0:
        relation = 30
        relation_text.append("매출액 증가와 영업활동현금흐름 감소 방향 불일치")
    if account == norm_account("매출채권") and rev_change is not None and change is not None and change - rev_change > 20:
        relation = max(relation, 24)
        relation_text.append("매출채권 증가율이 매출액 증가율을 20%p 초과")
    if account == norm_account("재고자산") and rev_change is not None and change is not None and change - rev_change > 20:
        relation = max(relation, 18)
        relation_text.append("재고자산 증가율이 매출액 증가율을 20%p 초과")
    if row.get("statement") == "손익계산서" and rev is not None and int(row.get("id", -1)) != int(rev.get("id", -2)):
        try:
            rp, rc = float(rev["prior"]), float(rev["current"])
            if rp != 0 and rc != 0:
                prior_ratio = abs(p) / abs(rp)
                current_ratio = abs(c) / abs(rc)
                if prior_ratio > 0 and current_ratio / prior_ratio >= 2:
                    relation = max(relation, 15)
                    relation_text.append("매출액 대비 계정 비중이 전기 대비 2배 이상")
        except (TypeError, ValueError):
            pass

    series = row.get("series") if isinstance(row.get("series"), dict) else {}
    pattern = pattern_signal(series)
    weighted = [
        {"score": magnitude, "max": 20, "weight": 25},
        {"score": relation, "max": 30, "weight": 30},
    ]
    if materiality is not None:
        weighted.append({"score": materiality, "max": 25, "weight": 25})
    if pattern.get("available"):
        weighted.append({"score": pattern["score"], "max": 20, "weight": 20})
    weight_sum = sum(x["weight"] for x in weighted)
    priority = round(sum((x["score"] / x["max"]) * x["weight"] for x in weighted) / max(weight_sum, 1) * 100)
    return {
        "magnitude": magnitude,
        "materiality": materiality,
        "materiality_ratio": materiality_ratio,
        "benchmark": benchmark,
        "relation": relation,
        "relation_text": relation_text,
        "pattern": pattern,
        "priority": int(clamp(priority, 0, 100)),
    }


def _level(score: int) -> str:
    if score >= 70:
        return "높음"
    if score >= 45:
        return "중간"
    return "낮음"


def _evidence(row: pd.Series) -> tuple[str, str]:
    pts = 0
    reasons: list[str] = []
    method = row.get("method")
    if method in {"excel", "csv"}:
        pts += 2
        reasons.append("표 구조 기반 추출")
    if bool(row.get("mapping_confirmed")):
        pts += 1
        reasons.append("매핑 확인")
    if bool(row.get("value_confirmed")):
        pts += 1
        reasons.append("원본 대조")
    if isinstance(row.get("series"), dict) and len(row["series"]) >= 3:
        pts += 1
        reasons.append("다기간 데이터")
    if pts >= 4:
        return "높음", " · ".join(reasons)
    if pts >= 2:
        return "보통", " · ".join(reasons) or "핵심 값 확인"
    return "낮음", " · ".join(reasons) or "추출/근거 확인 필요"


def analyze_financials(df: pd.DataFrame) -> pd.DataFrame:
    """Return only rows that have at least one explicit review signal.

    Materiality still changes priority, but materiality by itself does not create an
    anomaly. This prevents totals/benchmark rows from being presented as anomalies
    merely because their absolute amounts are large.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    rows = _active(df)
    results: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        parts = _priority_parts(row, rows)
        change = pct_change(row.get("prior"), row.get("current"))
        evidence_level, evidence_reason = _evidence(row)
        pattern = parts["pattern"]
        reasons: list[str] = []

        if change is not None and abs(change) >= 25:
            reasons.append(f"전기 대비 {change:+.1f}% 변동")
        elif change is None:
            try:
                if float(row.get("prior") or 0) == 0 and float(row.get("current") or 0) != 0:
                    reasons.append("전기 금액이 0이어서 증감률 비교가 제한됨")
            except (TypeError, ValueError):
                pass

        reasons.extend(parts["relation_text"])
        if pattern.get("available") and int(pattern.get("score") or 0) >= 8:
            reasons.append(str(pattern.get("reason")))

        # A row is not an anomaly unless an explicit, explainable signal exists.
        if not reasons:
            continue

        results.append(
            {
                "id": int(row.get("id")),
                "account": row.get("account"),
                "statement": row.get("statement"),
                "prior": row.get("prior"),
                "current": row.get("current"),
                "change_pct": change,
                "priority": parts["priority"],
                "level": _level(parts["priority"]),
                "magnitude": parts["magnitude"],
                "materiality": parts["materiality"],
                "materiality_ratio": parts["materiality_ratio"],
                "materiality_benchmark": parts["benchmark"]["label"] if parts["benchmark"] else "데이터 부족",
                "relation": parts["relation"],
                "pattern_score": pattern.get("score"),
                "pattern_available": bool(pattern.get("available")),
                "pattern_reason": pattern.get("reason"),
                "evidence_level": evidence_level,
                "evidence_reason": evidence_reason,
                "reasons": reasons,
                "source_file": row.get("source_file"),
                "source_sheet": row.get("source_sheet"),
                "source_row": row.get("source_row"),
                "source_page": row.get("source_page"),
                "prior_cell": row.get("prior_cell"),
                "current_cell": row.get("current_cell"),
                "series": row.get("series") if isinstance(row.get("series"), dict) else {},
            }
        )
    if not results:
        return pd.DataFrame(columns=["id", "account", "priority", "level"])
    out = pd.DataFrame(results)
    return out.sort_values(["priority", "account"], ascending=[False, True]).reset_index(drop=True)


def result_fingerprint(row: pd.Series | dict[str, Any]) -> str:
    get = row.get
    payload = [get("account"), get("statement"), get("prior"), get("current"), get("priority"), get("relation"), sorted(get("reasons") or [])]
    return json.dumps(payload, ensure_ascii=False, default=str)
