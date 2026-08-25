from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd


SERIES_COLUMNS = {"series", "period_cells"}


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None:
        return []
    out = []
    for record in df.to_dict("records"):
        cleaned = {}
        for key, value in record.items():
            if pd.isna(value) if not isinstance(value, (dict, list)) else False:
                cleaned[key] = None
            elif hasattr(value, "item"):
                cleaned[key] = value.item()
            else:
                cleaned[key] = value
        out.append(cleaned)
    return out


def serialize_project(state: dict[str, Any]) -> str:
    payload = {
        "version": 4,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": _records(state.get("source_rows", pd.DataFrame())),
        "working_rows": _records(state.get("working_rows", pd.DataFrame())),
        "analysis_rows": _records(state.get("analysis_rows", pd.DataFrame())),
        "prior_label": state.get("prior_label", "전기"),
        "current_label": state.get("current_label", "당기"),
        "file_name": state.get("file_name", ""),
        "transactions": _records(state.get("transactions", pd.DataFrame())),
        "txn_file_name": state.get("txn_file_name", ""),
        "reviewed": list(state.get("reviewed", [])),
        "review_notes": state.get("review_notes", {}),
        "reviewed_at": state.get("reviewed_at", {}),
        "audit_log": state.get("audit_log", [])[-500:],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def load_project(text: str) -> dict[str, Any]:
    data = json.loads(text)
    if int(data.get("version", 0)) not in {4}:
        raise ValueError("지원하지 않는 프로젝트 형식입니다.")
    return {
        "source_rows": pd.DataFrame(data.get("source_rows", [])),
        "working_rows": pd.DataFrame(data.get("working_rows", [])),
        "analysis_rows": pd.DataFrame(data.get("analysis_rows", [])),
        "prior_label": str(data.get("prior_label", "전기")),
        "current_label": str(data.get("current_label", "당기")),
        "file_name": str(data.get("file_name", "복원 프로젝트")),
        "transactions": pd.DataFrame(data.get("transactions", [])),
        "txn_file_name": str(data.get("txn_file_name", "프로젝트 전표")),
        "reviewed": {int(x) for x in data.get("reviewed", [])},
        "review_notes": {str(k): str(v) for k, v in data.get("review_notes", {}).items()},
        "reviewed_at": {str(k): str(v) for k, v in data.get("reviewed_at", {}).items()},
        "audit_log": list(data.get("audit_log", []))[-500:],
    }
