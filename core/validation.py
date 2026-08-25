from __future__ import annotations

import math
from typing import Any

import pandas as pd

from .utils import norm_account


def _active(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "included" not in df.columns:
        return df.copy()
    return df[df["included"].fillna(True).astype(bool)].copy()


def _find_account(df: pd.DataFrame, aliases: list[str], statement: str | None = None) -> pd.Series | None:
    keys = {norm_account(a) for a in aliases}
    for _, row in df.iterrows():
        if statement and str(row.get("statement", "")) != statement:
            continue
        if norm_account(row.get("account")) in keys:
            return row
    return None


def validate_financials(df: pd.DataFrame, prior_label: str = "전기", current_label: str = "당기") -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if df is None or df.empty:
        return [{"type": "error", "code": "EMPTY", "msg": "데이터 행이 없습니다."}]
    active = _active(df)
    if active.empty:
        return [{"type": "error", "code": "NO_INCLUDED", "msg": "분석에 포함된 계정이 없습니다."}]

    bad = 0
    for _, row in active.iterrows():
        if not str(row.get("account", "")).strip():
            bad += 1
            continue
        for key in ("prior", "current"):
            value = row.get(key)
            if value is None or pd.isna(value):
                bad += 1
                break
            try:
                if not math.isfinite(float(value)):
                    bad += 1
                    break
            except (TypeError, ValueError):
                bad += 1
                break
    if bad:
        issues.append({"type": "error", "code": "FORMAT", "msg": f"빈 금액·숫자 형식 또는 계정명 오류 {bad}건"})

    keys = active.apply(lambda r: f"{r.get('statement','')}|{norm_account(r.get('account'))}", axis=1)
    dup_count = int(keys.duplicated(keep=False).sum())
    if dup_count:
        issues.append({"type": "warn", "code": "DUP", "msg": f"동일 재무제표 내 중복 계정 {dup_count}행"})

    import re

    py = re.search(r"20\d{2}", str(prior_label))
    cy = re.search(r"20\d{2}", str(current_label))
    if py and cy and int(py.group()) >= int(cy.group()):
        issues.append({"type": "error", "code": "PERIOD_ORDER", "msg": f"기간 순서 확인 필요: 전기 {prior_label} / 당기 {current_label}"})
    if str(prior_label).strip() == str(current_label).strip():
        issues.append({"type": "error", "code": "PERIOD_SAME", "msg": "전기와 당기 표시명이 같습니다."})

    if "multiplier" in active.columns:
        multipliers = {int(x) for x in active["multiplier"].dropna().tolist()}
        if len(multipliers) > 1:
            issues.append({"type": "warn", "code": "UNIT_MIX", "msg": "서로 다른 원본 금액 단위가 섞여 있습니다. 내부 계산은 원 단위로 통일됩니다."})

    other_count = int((active.get("statement", pd.Series(dtype=str)) == "기타").sum())
    if other_count / max(len(active), 1) > 0.2:
        issues.append({"type": "warn", "code": "STATEMENT_MAP", "msg": f"재무제표 유형 미확정 {other_count}건 — 분석 기준이 제한될 수 있습니다."})

    zero_pairs = int(((pd.to_numeric(active["prior"], errors="coerce") == 0) & (pd.to_numeric(active["current"], errors="coerce") == 0)).sum())
    if zero_pairs / max(len(active), 1) > 0.35:
        issues.append({"type": "warn", "code": "ZERO_HEAVY", "msg": "전기·당기 모두 0인 분석 포함 행이 많습니다."})

    if {"method", "value_confirmed"}.issubset(active.columns):
        unconfirmed = active[active["method"].isin(["pdf", "docx"]) & ~active["value_confirmed"].fillna(False).astype(bool)]
        if len(unconfirmed):
            issues.append({"type": "warn", "code": "DOC_UNCONFIRMED", "msg": f"문서 추출값 원본 대조 미완료 {len(unconfirmed)}건"})

    multi_period = 0
    if "series" in active.columns:
        multi_period = sum(isinstance(v, dict) and len([x for x in v.values() if x is not None]) >= 3 for v in active["series"])
        if multi_period:
            issues.append({"type": "info", "code": "MULTI_PERIOD", "msg": f"다기간 추세 분석 가능 {multi_period}개 계정"})

    assets = _find_account(active, ["자산총계", "자산 합계", "총자산"], "재무상태표")
    liab = _find_account(active, ["부채총계", "부채 합계", "총부채"], "재무상태표")
    equity = _find_account(active, ["자본총계", "자본 합계", "총자본"], "재무상태표")
    if assets is not None and liab is not None and equity is not None:
        ap, ac = float(assets["prior"]), float(assets["current"])
        lp, lc = float(liab["prior"]), float(liab["current"])
        ep, ec = float(equity["prior"]), float(equity["current"])
        diff_prior = abs(ap - (lp + ep))
        diff_current = abs(ac - (lc + ec))
        tolerance = max(1000.0, abs(ac) * 0.001)
        if diff_prior > tolerance or diff_current > tolerance:
            issues.append({"type": "error", "code": "BS_EQ", "msg": f"재무상태표 등식 불일치 — 당기 차이 {diff_current:,.0f}원"})
        else:
            issues.append({"type": "ok", "code": "BS_EQ_OK", "msg": "재무상태표 자산 = 부채 + 자본 확인"})
    else:
        issues.append({"type": "info", "code": "BS_EQ_SKIP", "msg": "재무상태표 합계 계정이 부족해 등식 검증을 건너뜁니다."})

    begin_cash = _find_account(active, ["기초현금및현금성자산", "기초 현금및현금성자산", "기초현금"])
    cash_change = _find_account(active, ["현금및현금성자산의증가감소", "현금의증가감소", "현금증감"])
    end_cash = _find_account(active, ["기말현금및현금성자산", "기말 현금및현금성자산", "기말현금"])
    if begin_cash is not None and cash_change is not None and end_cash is not None:
        diff = abs((float(begin_cash["current"]) + float(cash_change["current"])) - float(end_cash["current"]))
        tolerance = max(1000.0, abs(float(end_cash["current"])) * 0.001)
        if diff > tolerance:
            issues.append({"type": "error", "code": "CF_EQ", "msg": f"현금흐름 연결 불일치 — 당기 차이 {diff:,.0f}원"})
        else:
            issues.append({"type": "ok", "code": "CF_EQ_OK", "msg": "기초현금 + 현금증감 = 기말현금 확인"})

    source_missing = 0
    if "method" in active.columns:
        for _, row in active.iterrows():
            if row.get("method") == "manual":
                continue
            if not str(row.get("source_sheet") or "").strip() and pd.isna(row.get("source_page")):
                source_missing += 1
    if source_missing:
        issues.append({"type": "warn", "code": "LINEAGE", "msg": f"원본 위치 추적 정보 부족 {source_missing}건"})

    excluded = len(df) - len(active)
    if excluded:
        issues.append({"type": "info", "code": "EXCLUDED", "msg": f"분석 제외 {excluded}건 · 원본 데이터에는 유지"})

    if not any(x["type"] == "error" for x in issues):
        issues.insert(0, {"type": "ok", "code": "BASIC", "msg": f"기본 형식 검사 통과 · 분석 포함 {len(active)}개"})
    return issues
