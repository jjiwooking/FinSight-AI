from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Iterable

import pandas as pd

ACCOUNT_CATALOG = [
    "복리후생비",
    "접대비",
    "여비교통비",
    "지급수수료",
    "전산비",
    "소프트웨어사용료",
    "운반비",
    "광고선전비",
    "보험료",
    "지급임차료",
    "소모품비",
    "교육훈련비",
    "통신비",
    "미분류",
]

RULES = [
    (re.compile(r"카카오.?택시|택시|taxi|ktx|srt|철도|고속버스", re.I), "여비교통비", 86, "교통 키워드"),
    (re.compile(r"aws|azure|gcp|cloud|클라우드", re.I), "전산비", 78, "클라우드 키워드"),
    (re.compile(r"adobe|microsoft|notion|slack|zoom|software|소프트웨어", re.I), "소프트웨어사용료", 82, "SaaS 키워드"),
    (re.compile(r"스타벅스|카페|coffee|커피|식당|식대", re.I), "복리후생비", 72, "식음료 키워드"),
    (re.compile(r"골프|접대|거래처.?식사", re.I), "접대비", 76, "접대 키워드"),
    (re.compile(r"네이버.?광고|구글.?광고|meta.?ads|facebook.?ads|광고", re.I), "광고선전비", 85, "광고 키워드"),
    (re.compile(r"택배|우체국|퀵서비스|배송", re.I), "운반비", 74, "배송 키워드"),
    (re.compile(r"세무|회계법인|법무|변호사|노무", re.I), "지급수수료", 82, "전문용역 키워드"),
    (re.compile(r"보험", re.I), "보험료", 80, "보험 키워드"),
    (re.compile(r"임대|rent|월세", re.I), "지급임차료", 84, "임차 키워드"),
    (re.compile(r"통신|인터넷|전화|kt |skt|lg유플러스", re.I), "통신비", 78, "통신 키워드"),
    (re.compile(r"교육|세미나|강의|인강", re.I), "교육훈련비", 76, "교육 키워드"),
]


def norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def transaction_fingerprint(record: dict[str, Any]) -> str:
    return f"{str(record.get('date','')).strip()}|{norm_text(record.get('desc'))}|{float(record.get('amount') or 0):.6f}"


def _approved_memory(records: Iterable[dict[str, Any]], exclude_id: int | None = None) -> dict[str, tuple[str, int]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if exclude_id is not None and int(record.get("id", -1)) == int(exclude_id):
            continue
        if record.get("status") != "승인":
            continue
        account = str(record.get("final_account") or "")
        if not account or account == "미분류":
            continue
        key = norm_text(record.get("desc"))
        if key:
            grouped[key].append(account)
    memory: dict[str, tuple[str, int]] = {}
    for key, accounts in grouped.items():
        account, count = Counter(accounts).most_common(1)[0]
        memory[key] = (account, count)
    return memory


def recommend_transaction(desc: str, records: Iterable[dict[str, Any]] = (), exclude_id: int | None = None) -> dict[str, Any]:
    text = norm_text(desc)
    memory = _approved_memory(records, exclude_id=exclude_id)
    if text in memory:
        account, count = memory[text]
        return {"account": account, "score": 95, "source": f"과거 승인 {count}건"}
    for pattern, account, score, label in RULES:
        if pattern.search(text):
            return {"account": account, "score": score, "source": label}
    return {"account": "미분류", "score": 0, "source": "추천 근거 부족"}


def mark_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()
    out = df.copy()
    records = out.to_dict("records")
    fps = [transaction_fingerprint(r) for r in records]
    counts = Counter(fps)
    out["duplicate"] = [counts[fp] > 1 for fp in fps]
    return out


def refresh_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()
    out = df.copy()
    records = out.to_dict("records")
    for idx, row in out.iterrows():
        if row.get("status") == "승인" and bool(row.get("user_modified")):
            continue
        rec = recommend_transaction(str(row.get("desc", "")), records, exclude_id=int(row.get("id")))
        out.at[idx, "ai_account"] = rec["account"]
        out.at[idx, "recommendation_score"] = rec["score"]
        out.at[idx, "recommendation_source"] = rec["source"]
        if not bool(row.get("user_modified")) and not str(row.get("original_account") or "").strip():
            out.at[idx, "final_account"] = rec["account"]
    return mark_duplicates(out)
