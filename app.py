from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from core.anomaly import analyze_financials, result_fingerprint
from core.io import (
    build_financial_rows,
    build_transactions,
    detect_financial_mapping,
    detect_transaction_mapping,
    detect_unit_multiplier,
    infer_statement,
    parse_document,
    read_tabular_file,
)
from core.project import load_project, serialize_project
from core.transactions import ACCOUNT_CATALOG, refresh_recommendations
from core.validation import validate_financials

BASE_DIR = Path(__file__).resolve().parent

FINANCIAL_COLUMNS = [
    "id",
    "account",
    "statement",
    "prior",
    "current",
    "included",
    "series",
    "source_file",
    "source_sheet",
    "source_row",
    "source_page",
    "prior_cell",
    "current_cell",
    "period_cells",
    "unit",
    "multiplier",
    "method",
    "mapping_confirmed",
    "value_confirmed",
    "user_adjusted",
]

TRANSACTION_COLUMNS = [
    "id",
    "date",
    "desc",
    "amount",
    "original_account",
    "ai_account",
    "recommendation_score",
    "recommendation_source",
    "final_account",
    "status",
    "user_modified",
    "duplicate",
    "source_file",
    "source_row",
]

PAGES = ["업무 요약", "데이터", "이상징후 분석", "전표 분류"]

st.set_page_config(page_title="FinSight AI", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """
    <style>
      .stApp { background: #0b1220; color: #e8eef9; }
      .block-container { max-width: 1500px; padding-top: 1.0rem; padding-bottom: 3rem; }
      [data-testid="stMetric"] { background:#0f1828; border:1px solid #202e44; padding:12px; border-radius:10px; }
      div[data-testid="stDataEditor"], div[data-testid="stDataFrame"] { border:1px solid #202e44; border-radius:10px; overflow:hidden; }
      .fs-muted { color:#8392a8; font-size:.9rem; }
      .fs-card { background:#0f1828; border:1px solid #202e44; border-radius:10px; padding:14px; margin:0 0 10px 0; min-height:82px; }
      .fs-high { border-left:4px solid #ef5665; }
      .fs-mid { border-left:4px solid #d49a20; }
      .fs-low { border-left:4px solid #65768e; }
      .fs-brand { font-size:1.55rem; font-weight:800; }
      .fs-sub { color:#8190aa; margin-top:-.35rem; margin-bottom:.7rem; }
      .fs-empty { background:#0f1828; border:1px dashed #2b3a52; border-radius:12px; padding:24px; color:#aeb9cb; }
      .fs-section-note { color:#8493aa; margin-top:-.4rem; margin-bottom:.8rem; }
      code { color:#f6c35b !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


def empty_financial_df() -> pd.DataFrame:
    return pd.DataFrame(columns=FINANCIAL_COLUMNS)


def empty_transaction_df() -> pd.DataFrame:
    return pd.DataFrame(columns=TRANSACTION_COLUMNS)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def log_action(action: str, detail: str = "") -> None:
    st.session_state.audit_log.append(
        {"at": datetime.now().isoformat(timespec="seconds"), "action": action, "detail": detail}
    )
    st.session_state.audit_log = st.session_state.audit_log[-500:]


def init_state() -> None:
    defaults: dict[str, Any] = {
        "source_rows": empty_financial_df(),
        "working_rows": empty_financial_df(),
        "analysis_rows": empty_financial_df(),
        "file_name": "",
        "prior_label": "전기",
        "current_label": "당기",
        "reviewed": set(),
        "review_notes": {},
        "reviewed_at": {},
        "audit_log": [],
        "transactions": empty_transaction_df(),
        "txn_file_name": "",
        "pending_financial": None,
        "pending_financial_hash": None,
        "pending_transaction": None,
        "pending_txn_hash": None,
        "doc_preview": "",
        "nav_page": "데이터",
        "selected_anomaly_id": None,
        "focus_financial_id": None,
        "data_undo_stack": [],
        "data_editor_version": 0,
        "txn_editor_version": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_blank_project() -> None:
    st.session_state.source_rows = empty_financial_df()
    st.session_state.working_rows = empty_financial_df()
    st.session_state.analysis_rows = empty_financial_df()
    st.session_state.file_name = ""
    st.session_state.prior_label = "전기"
    st.session_state.current_label = "당기"
    st.session_state.reviewed = set()
    st.session_state.review_notes = {}
    st.session_state.reviewed_at = {}
    st.session_state.transactions = empty_transaction_df()
    st.session_state.txn_file_name = ""
    st.session_state.pending_financial = None
    st.session_state.pending_financial_hash = None
    st.session_state.pending_transaction = None
    st.session_state.pending_txn_hash = None
    st.session_state.doc_preview = ""
    st.session_state.selected_anomaly_id = None
    st.session_state.focus_financial_id = None
    st.session_state.data_undo_stack = []
    st.session_state.data_editor_version += 1
    st.session_state.txn_editor_version += 1
    st.session_state.nav_page = "데이터"
    log_action("PROJECT_NEW", "빈 프로젝트")


def go_to(page: str, anomaly_id: int | None = None, financial_id: int | None = None) -> None:
    st.session_state.nav_page = page
    if anomaly_id is not None:
        st.session_state.selected_anomaly_id = int(anomaly_id)
    if financial_id is not None:
        st.session_state.focus_financial_id = int(financial_id)


def dataframe_signature(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "empty"
    keep = [c for c in ["id", "account", "statement", "prior", "current", "included", "series"] if c in df.columns]
    payload = df[keep].sort_values("id").to_json(orient="records", force_ascii=False, default_handler=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def analysis_is_stale() -> bool:
    return dataframe_signature(st.session_state.working_rows) != dataframe_signature(st.session_state.analysis_rows)


def current_anomalies() -> pd.DataFrame:
    return analyze_financials(st.session_state.analysis_rows)


def unconfirmed_doc_count(df: pd.DataFrame) -> int:
    if df is None or df.empty or not {"method", "value_confirmed"}.issubset(df.columns):
        return 0
    mask = df["method"].isin(["pdf", "docx"]) & ~df["value_confirmed"].fillna(False).astype(bool)
    return int(mask.sum())


def values_equal(a: Any, b: Any) -> bool:
    if isinstance(a, dict) or isinstance(b, dict):
        return json.dumps(a if isinstance(a, dict) else {}, sort_keys=True, ensure_ascii=False, default=str) == json.dumps(
            b if isinstance(b, dict) else {}, sort_keys=True, ensure_ascii=False, default=str
        )
    try:
        if pd.isna(a) and pd.isna(b):
            return True
    except (TypeError, ValueError):
        pass
    return a == b


def changed_financial_ids() -> set[int]:
    working = st.session_state.working_rows
    source = st.session_state.source_rows
    if working.empty:
        return set()
    source_map = {safe_int(r["id"]): r for _, r in source.iterrows()} if not source.empty else {}
    changed: set[int] = set()
    for _, row in working.iterrows():
        rid = safe_int(row.get("id"))
        original = source_map.get(rid)
        if original is None:
            changed.add(rid)
            continue
        for col in ["account", "statement", "prior", "current", "included"]:
            if not values_equal(row.get(col), original.get(col)):
                changed.add(rid)
                break
    return changed


def draft_change_count() -> int:
    changed = changed_financial_ids()
    working_ids = {safe_int(x) for x in st.session_state.working_rows.get("id", pd.Series(dtype=int)).dropna().tolist()}
    source_ids = {safe_int(x) for x in st.session_state.source_rows.get("id", pd.Series(dtype=int)).dropna().tolist()}
    deleted = source_ids - working_ids
    return len(changed) + len(deleted)


def push_data_undo() -> None:
    stack = st.session_state.data_undo_stack
    stack.append(st.session_state.working_rows.copy(deep=True))
    st.session_state.data_undo_stack = stack[-20:]


def undo_data() -> None:
    if not st.session_state.data_undo_stack:
        return
    st.session_state.working_rows = st.session_state.data_undo_stack.pop()
    st.session_state.data_editor_version += 1
    log_action("DATA_UNDO", "직전 편집 복원")


def apply_analysis() -> None:
    if st.session_state.working_rows.empty:
        st.info("먼저 재무 데이터를 불러와 주세요.")
        return
    issues_now = validate_financials(
        st.session_state.working_rows, st.session_state.prior_label, st.session_state.current_label
    )
    if any(x["type"] == "error" for x in issues_now):
        st.error("검증 오류를 먼저 수정해 주세요.")
        return
    old_anom = current_anomalies()
    old_fingerprints = (
        {int(r["id"]): result_fingerprint(r) for _, r in old_anom.iterrows()} if not old_anom.empty else {}
    )
    old_reviewed = set(st.session_state.reviewed)
    st.session_state.analysis_rows = st.session_state.working_rows.copy(deep=True)
    new_anom = current_anomalies()
    new_fingerprints = (
        {int(r["id"]): result_fingerprint(r) for _, r in new_anom.iterrows()} if not new_anom.empty else {}
    )
    preserved = {rid for rid in old_reviewed if old_fingerprints.get(rid) == new_fingerprints.get(rid)}
    removed_review_count = len(old_reviewed - preserved)
    st.session_state.reviewed = preserved
    st.session_state.reviewed_at = {
        k: v for k, v in st.session_state.reviewed_at.items() if safe_int(k, -1) in preserved
    }
    log_action("ANALYSIS_APPLY", f"{len(st.session_state.analysis_rows)}개 계정")
    if removed_review_count:
        st.success(f"분석을 갱신했습니다. 변경된 결과 {removed_review_count}건의 검토 완료 상태를 해제했습니다.")
    else:
        st.success("분석을 갱신했습니다. 변경되지 않은 검토 완료 상태는 유지했습니다.")


def project_state() -> dict[str, Any]:
    return {
        "source_rows": st.session_state.source_rows,
        "working_rows": st.session_state.working_rows,
        "analysis_rows": st.session_state.analysis_rows,
        "prior_label": st.session_state.prior_label,
        "current_label": st.session_state.current_label,
        "file_name": st.session_state.file_name,
        "transactions": st.session_state.transactions,
        "txn_file_name": st.session_state.txn_file_name,
        "reviewed": st.session_state.reviewed,
        "review_notes": st.session_state.review_notes,
        "reviewed_at": st.session_state.reviewed_at,
        "audit_log": st.session_state.audit_log,
    }


def confirm_source_values(ids: list[int]) -> None:
    id_set = {int(x) for x in ids}
    for key in ["source_rows", "working_rows", "analysis_rows"]:
        df = st.session_state[key].copy()
        if not df.empty and {"id", "value_confirmed"}.issubset(df.columns):
            df.loc[df["id"].astype(int).isin(id_set), "value_confirmed"] = True
            st.session_state[key] = df
    log_action("SOURCE_CONFIRMED", f"{len(id_set)}건")


def make_manual_financial_record(rid: int) -> dict[str, Any]:
    return {
        "id": rid,
        "account": "",
        "statement": "기타",
        "prior": None,
        "current": None,
        "included": True,
        "series": {},
        "source_file": st.session_state.file_name or "수기 입력",
        "source_sheet": "",
        "source_row": None,
        "source_page": None,
        "prior_cell": "",
        "current_cell": "",
        "period_cells": {},
        "unit": "원",
        "multiplier": 1,
        "method": "manual",
        "mapping_confirmed": True,
        "value_confirmed": True,
        "user_adjusted": True,
    }


def save_financial_editor(filtered_before: pd.DataFrame, edited: pd.DataFrame) -> None:
    base = st.session_state.working_rows.copy(deep=True)
    push_data_undo()
    visible_ids = {
        safe_int(x) for x in filtered_before.get("id", pd.Series(dtype=int)).dropna().tolist()
    }
    base_map = {safe_int(r["id"]): r.to_dict() for _, r in base.iterrows() if pd.notna(r.get("id"))}
    hidden = [r.to_dict() for _, r in base.iterrows() if safe_int(r.get("id")) not in visible_ids]
    next_id = max([safe_int(x) for x in base.get("id", pd.Series(dtype=int)).dropna().tolist()] + [0]) + 1
    rebuilt_visible: list[dict[str, Any]] = []

    for _, e in edited.iterrows():
        rid = safe_int(e.get("id"), 0)
        if not rid:
            rid = next_id
            next_id += 1
        record = base_map.get(rid, make_manual_financial_record(rid)).copy()
        before = record.copy()
        record["id"] = rid
        for col in ["account", "statement", "prior", "current", "included"]:
            record[col] = e.get(col)
        record["user_adjusted"] = record.get("user_adjusted", False) or any(
            not values_equal(before.get(col), record.get(col))
            for col in ["account", "statement", "prior", "current", "included"]
        )
        if isinstance(record.get("series"), dict):
            if st.session_state.prior_label in record["series"]:
                record["series"][st.session_state.prior_label] = record["prior"]
            if st.session_state.current_label in record["series"]:
                record["series"][st.session_state.current_label] = record["current"]
        rebuilt_visible.append(record)

    combined = hidden + rebuilt_visible
    if combined:
        out = pd.DataFrame(combined)
        for col in FINANCIAL_COLUMNS:
            if col not in out.columns:
                out[col] = None
        out = out[FINANCIAL_COLUMNS].sort_values("id").reset_index(drop=True)
    else:
        out = empty_financial_df()
    st.session_state.working_rows = out
    st.session_state.data_editor_version += 1
    log_action("DATA_EDIT", f"{len(rebuilt_visible)}개 표시행 저장")


def save_transaction_editor(filtered_before: pd.DataFrame, edited: pd.DataFrame) -> None:
    base = st.session_state.transactions.copy(deep=True)
    visible_ids = {safe_int(x) for x in filtered_before.get("id", pd.Series(dtype=int)).dropna().tolist()}
    base_map = {safe_int(r["id"]): r.to_dict() for _, r in base.iterrows()}
    hidden = [r.to_dict() for _, r in base.iterrows() if safe_int(r.get("id")) not in visible_ids]
    updated: list[dict[str, Any]] = []
    for _, e in edited.iterrows():
        rid = safe_int(e.get("id"))
        if rid not in base_map:
            continue
        rec = base_map[rid].copy()
        for col in ["date", "desc", "amount", "final_account", "status"]:
            rec[col] = e.get(col)
        rec["user_modified"] = str(rec.get("final_account") or "") != str(rec.get("ai_account") or "")
        updated.append(rec)
    out = pd.DataFrame(hidden + updated) if hidden or updated else empty_transaction_df()
    st.session_state.transactions = refresh_recommendations(out)
    st.session_state.txn_editor_version += 1
    log_action("TXN_REVIEW_SAVE", f"{len(updated)}개 표시행")


init_state()

has_financial = not st.session_state.working_rows.empty
issues = (
    validate_financials(st.session_state.working_rows, st.session_state.prior_label, st.session_state.current_label)
    if has_financial
    else []
)
has_error = any(x["type"] == "error" for x in issues)
stale = analysis_is_stale() if has_financial else False
unconfirmed_count = unconfirmed_doc_count(st.session_state.analysis_rows)

st.markdown('<div class="fs-brand">FinSight AI V2.6.1</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="fs-sub">Python Engine · 재무제표 이상징후 탐지 + 전표 분류 워크스페이스</div>',
    unsafe_allow_html=True,
)

status_cols = st.columns([1.5, 1.2, 1.4, 1.2, 1.3])
status_cols[0].caption(f"파일 · {st.session_state.file_name or '불러오기 전'}")
status_cols[1].caption(
    f"기간 · {st.session_state.prior_label} ↔ {st.session_state.current_label}" if has_financial else "기간 · —"
)
if not has_financial:
    validation_label = "파일 대기"
elif has_error:
    validation_label = "수정 필요"
elif unconfirmed_count:
    validation_label = f"원본 대조 필요 {unconfirmed_count}건"
else:
    validation_label = "기본 검증 통과"
status_cols[2].caption(f"검증 · {validation_label}")
if not has_financial:
    analysis_label = "대기"
elif stale:
    analysis_label = "재분석 필요"
elif unconfirmed_count:
    analysis_label = "임시 결과"
else:
    analysis_label = "최신"
status_cols[3].caption(f"분석 · {analysis_label}")
status_cols[4].caption("엔진 · Python / pandas")

if stale:
    c1, c2 = st.columns([5, 1])
    c1.warning("수정한 데이터가 아직 분석 결과에 반영되지 않았습니다. 현재 이상징후 결과는 수정 전 기준입니다.")
    if c2.button("지금 반영", type="primary", use_container_width=True):
        apply_analysis()
        st.rerun()
elif unconfirmed_count:
    st.warning(f"문서에서 추출한 값 {unconfirmed_count}건이 원본 대조 전입니다. 현재 분석은 임시 결과로 표시됩니다.")

with st.sidebar:
    st.subheader("프로젝트")
    project_upload = st.file_uploader("프로젝트 JSON 불러오기", type=["json"], key="project_upload")
    if project_upload is not None and st.button("프로젝트 적용", use_container_width=True):
        try:
            loaded = load_project(project_upload.getvalue().decode("utf-8"))
            for key, value in loaded.items():
                st.session_state[key] = value
            st.session_state.pending_financial = None
            st.session_state.pending_transaction = None
            st.session_state.focus_financial_id = None
            st.session_state.selected_anomaly_id = None
            st.session_state.data_undo_stack = []
            st.session_state.data_editor_version += 1
            st.session_state.txn_editor_version += 1
            st.session_state.nav_page = "업무 요약" if not st.session_state.working_rows.empty else "데이터"
            log_action("PROJECT_OPEN", st.session_state.file_name)
            st.success("프로젝트를 불러왔습니다.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    st.download_button(
        "프로젝트 백업",
        data=serialize_project(project_state()).encode("utf-8"),
        file_name=f"FinSight_Project_{datetime.now():%Y-%m-%d}.json",
        mime="application/json",
        use_container_width=True,
    )
    if st.button("새 빈 프로젝트", use_container_width=True):
        reset_blank_project()
        st.rerun()
    st.caption("실제 회사 재무데이터와 프로젝트 백업은 public GitHub 저장소에 커밋하지 마세요.")

if st.session_state.nav_page not in PAGES:
    st.session_state.nav_page = "데이터" if not has_financial else "업무 요약"
st.radio("화면", PAGES, horizontal=True, key="nav_page", label_visibility="collapsed")
page = st.session_state.nav_page

# ----------------------------- 업무 요약 -----------------------------
if page == "업무 요약":
    if not has_financial:
        st.markdown(
            '<div class="fs-empty"><b>아직 불러온 재무 데이터가 없습니다.</b><br>데이터 화면에서 Excel, CSV, PDF 또는 Word 파일을 불러오면 분석을 시작합니다.</div>',
            unsafe_allow_html=True,
        )
        st.button("재무 데이터 불러오기", type="primary", on_click=go_to, args=("데이터",))
    else:
        anomalies = current_anomalies()
        current_ids = {safe_int(x) for x in anomalies.get("id", pd.Series(dtype=int)).tolist()}
        reviewed_count = len(current_ids & set(st.session_state.reviewed))
        active_count = int(st.session_state.analysis_rows.get("included", pd.Series(dtype=bool)).fillna(True).astype(bool).sum())
        high_count = int((anomalies.get("level", pd.Series(dtype=str)) == "높음").sum()) if not anomalies.empty else 0
        pending_count = len(current_ids - set(st.session_state.reviewed))
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("분석 계정", active_count)
        m2.metric("확인 필요", len(anomalies))
        m3.metric("우선순위 높음", high_count)
        m4.metric("미검토", pending_count)

        if not anomalies.empty:
            dist = anomalies["level"].value_counts()
            d1, d2, d3 = st.columns(3)
            d1.metric("높음", int(dist.get("높음", 0)))
            d2.metric("중간", int(dist.get("중간", 0)))
            d3.metric("낮음", int(dist.get("낮음", 0)))

        st.subheader("지금 확인할 항목")
        st.markdown('<div class="fs-section-note">미검토 항목과 높은 우선순위를 먼저 보여줍니다.</div>', unsafe_allow_html=True)
        if anomalies.empty:
            st.info("현재 탐지 규칙에서 명확한 검토 신호가 발견되지 않았습니다.")
        else:
            queue = anomalies.copy()
            queue["reviewed_sort"] = queue["id"].map(lambda x: safe_int(x) in st.session_state.reviewed)
            queue = queue.sort_values(["reviewed_sort", "priority", "account"], ascending=[True, False, True])
            for _, row in queue.head(8).iterrows():
                rid = int(row["id"])
                reviewed = rid in st.session_state.reviewed
                css = "fs-high" if row["level"] == "높음" else "fs-mid" if row["level"] == "중간" else "fs-low"
                change = "비교 불가" if pd.isna(row.get("change_pct")) else f"{float(row['change_pct']):+.1f}%"
                reasons = " · ".join((row.get("reasons") or [])[:2])
                c1, c2, c3 = st.columns([7.5, 1.25, 1.45])
                with c1:
                    st.markdown(
                        f'<div class="fs-card {css}"><b>{row["account"]}</b> · 우선순위 {row["priority"]}/100 · {change}'
                        f'<div class="fs-muted">{reasons}{" · 검토 완료" if reviewed else ""}</div></div>',
                        unsafe_allow_html=True,
                    )
                c2.button(
                    "상세 검토",
                    key=f"summary_detail_{rid}",
                    use_container_width=True,
                    on_click=go_to,
                    args=("이상징후 분석", rid, None),
                )
                c3.button(
                    "데이터 확인",
                    key=f"summary_data_{rid}",
                    use_container_width=True,
                    on_click=go_to,
                    args=("데이터", None, rid),
                )
            if reviewed_count:
                st.caption(f"현재 이상징후 중 검토 완료 {reviewed_count}건")

# ----------------------------- 데이터 -----------------------------
elif page == "데이터":
    st.subheader("재무 데이터 가져오기")
    uploaded = st.file_uploader("Excel · CSV · PDF · Word", type=["xlsx", "xls", "csv", "pdf", "docx"], key="financial_upload")
    if uploaded is not None:
        upload_hash = hashlib.sha256(uploaded.getvalue()).hexdigest()
        if st.session_state.get("pending_financial_hash") != upload_hash:
            try:
                ext = Path(uploaded.name).suffix.lower()
                if ext in {".xlsx", ".xls", ".csv"}:
                    sheets = read_tabular_file(uploaded.name, uploaded.getvalue())
                    mappings = {name: detect_financial_mapping(df) for name, df in sheets.items()}
                    preview_text = "\n".join(
                        " | ".join(map(str, df.head(8).fillna("").values.flatten().tolist())) for df in sheets.values()
                    )
                    st.session_state.pending_financial = {
                        "kind": "table",
                        "filename": uploaded.name,
                        "sheets": sheets,
                        "mappings": mappings,
                        "unit": detect_unit_multiplier(preview_text),
                    }
                else:
                    st.session_state.pending_financial = {
                        "kind": "document",
                        "filename": uploaded.name,
                        "data": uploaded.getvalue(),
                    }
                st.session_state.pending_financial_hash = upload_hash
            except Exception as exc:
                st.error(f"파일을 읽지 못했습니다: {exc}")

    pending = st.session_state.pending_financial
    if pending:
        st.markdown("#### 업로드 확인")
        if pending["kind"] == "table":
            first_map = next(iter(pending["mappings"].values()))
            pcol, ccol, ucol = st.columns(3)
            prior_label = pcol.text_input("전기 표시명", value=first_map["prior_label"], key="fin_prior_label")
            current_label = ccol.text_input("당기 표시명", value=first_map["current_label"], key="fin_current_label")
            unit_options = {"원": 1, "천원": 1_000, "백만원": 1_000_000, "억원": 100_000_000}
            default_unit = next((k for k, v in unit_options.items() if v == pending["unit"]), "원")
            unit_name = ucol.selectbox(
                "금액 단위", list(unit_options), index=list(unit_options).index(default_unit), key="fin_unit"
            )
            selections = []
            for idx, (sheet_name, df) in enumerate(pending["sheets"].items()):
                mapping = pending["mappings"][sheet_name]
                headers = mapping["headers"]
                with st.expander(f"{sheet_name} · 매핑 확인", expanded=idx == 0):
                    st.dataframe(
                        df.iloc[mapping["header_index"] : mapping["header_index"] + 6].fillna(""),
                        use_container_width=True,
                        hide_index=True,
                    )
                    cols = st.columns(5)
                    include = cols[0].checkbox("포함", value=True, key=f"include_{idx}")
                    statement_options = ["손익계산서", "재무상태표", "현금흐름표", "기타"]
                    inferred = infer_statement(sheet_name)
                    statement = cols[1].selectbox(
                        "재무제표",
                        statement_options,
                        index=statement_options.index(inferred),
                        key=f"stmt_{idx}",
                    )
                    account_col = cols[2].selectbox(
                        "계정과목",
                        range(len(headers)),
                        index=mapping["account_col"],
                        format_func=lambda i, h=headers: h[i] or f"열 {i+1}",
                        key=f"acct_{idx}",
                    )
                    prior_col = cols[3].selectbox(
                        "전기",
                        range(len(headers)),
                        index=mapping["prior_col"],
                        format_func=lambda i, h=headers: h[i] or f"열 {i+1}",
                        key=f"prior_{idx}",
                    )
                    current_col = cols[4].selectbox(
                        "당기",
                        range(len(headers)),
                        index=mapping["current_col"],
                        format_func=lambda i, h=headers: h[i] or f"열 {i+1}",
                        key=f"current_{idx}",
                    )
                    selections.append((sheet_name, df, mapping, include, statement, account_col, prior_col, current_col))
            if st.button("확인하고 데이터 불러오기", type="primary"):
                try:
                    if prior_label.strip() == current_label.strip():
                        raise ValueError("전기와 당기 표시명이 같습니다.")
                    built = []
                    next_id = 1
                    for sheet_name, df, mapping, include, statement, account_col, prior_col, current_col in selections:
                        if not include:
                            continue
                        part = build_financial_rows(
                            df,
                            filename=pending["filename"],
                            sheet_name=sheet_name,
                            statement=statement,
                            account_col=account_col,
                            prior_col=prior_col,
                            current_col=current_col,
                            header_index=mapping["header_index"],
                            multiplier=unit_options[unit_name],
                            method="csv" if pending["filename"].lower().endswith(".csv") else "excel",
                            period_cols=mapping["period_cols"],
                            id_start=next_id,
                        )
                        built.append(part)
                        next_id += len(part)
                    rows = pd.concat(built, ignore_index=True) if built else empty_financial_df()
                    if rows.empty:
                        raise ValueError("선택한 매핑에서 유효한 계정을 찾지 못했습니다.")
                    st.session_state.source_rows = rows.copy(deep=True)
                    st.session_state.working_rows = rows.copy(deep=True)
                    st.session_state.analysis_rows = rows.copy(deep=True)
                    st.session_state.file_name = pending["filename"]
                    st.session_state.prior_label = prior_label.strip() or "전기"
                    st.session_state.current_label = current_label.strip() or "당기"
                    st.session_state.reviewed = set()
                    st.session_state.review_notes = {}
                    st.session_state.reviewed_at = {}
                    st.session_state.pending_financial = None
                    st.session_state.doc_preview = ""
                    st.session_state.focus_financial_id = None
                    st.session_state.selected_anomaly_id = None
                    st.session_state.data_undo_stack = []
                    st.session_state.data_editor_version += 1
                    log_action("FINANCIAL_IMPORT", f"{pending['filename']} · {len(rows)}개 계정")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            c1, c2 = st.columns(2)
            statement = c1.selectbox("재무제표", ["손익계산서", "재무상태표", "현금흐름표", "기타"], index=3, key="doc_statement")
            unit_name = c2.selectbox("금액 단위", ["원", "천원", "백만원", "억원"], key="doc_unit")
            st.caption("PDF/DOCX 추출값은 자동으로 확정하지 않습니다. 불러온 뒤 원본 대조 상태를 별도로 표시합니다.")
            if st.button("문서 추출", type="primary"):
                try:
                    multiplier = {"원": 1, "천원": 1_000, "백만원": 1_000_000, "억원": 100_000_000}[unit_name]
                    rows, preview = parse_document(
                        pending["filename"], pending["data"], statement=statement, multiplier=multiplier
                    )
                    if rows.empty:
                        raise ValueError("문서에서 전기·당기 두 금액을 가진 행을 찾지 못했습니다.")
                    st.session_state.source_rows = rows.copy(deep=True)
                    st.session_state.working_rows = rows.copy(deep=True)
                    st.session_state.analysis_rows = rows.copy(deep=True)
                    st.session_state.file_name = pending["filename"]
                    st.session_state.prior_label = "전기"
                    st.session_state.current_label = "당기"
                    st.session_state.reviewed = set()
                    st.session_state.review_notes = {}
                    st.session_state.reviewed_at = {}
                    st.session_state.doc_preview = preview
                    st.session_state.pending_financial = None
                    st.session_state.focus_financial_id = None
                    st.session_state.selected_anomaly_id = None
                    st.session_state.data_undo_stack = []
                    st.session_state.data_editor_version += 1
                    log_action("DOCUMENT_IMPORT", f"{pending['filename']} · {len(rows)}개 추출")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    if st.session_state.working_rows.empty:
        if not pending:
            st.markdown(
                '<div class="fs-empty"><b>빈 프로젝트입니다.</b><br>위에서 재무 파일을 불러오면 데이터 편집, 검증, 이상징후 분석이 활성화됩니다.</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown("#### 데이터 편집기")
        changed_ids = changed_financial_ids()
        f1, f2, f3, f4 = st.columns([2.1, 1.4, 1.25, 1.15])
        search_text = f1.text_input("계정 검색", placeholder="계정과목 검색", key="fin_search")
        statement_filter = f2.selectbox(
            "재무제표",
            ["전체", "손익계산서", "재무상태표", "현금흐름표", "기타"],
            key="fin_statement_filter",
        )
        included_filter = f3.selectbox("분석 상태", ["전체", "분석 포함", "분석 제외"], key="fin_included_filter")
        changed_only = f4.checkbox("변경된 행만", value=False, key="fin_changed_only")

        filtered = st.session_state.working_rows.copy()
        if search_text.strip():
            filtered = filtered[
                filtered["account"].fillna("").astype(str).str.contains(search_text.strip(), case=False, na=False)
            ]
        if statement_filter != "전체":
            filtered = filtered[filtered["statement"] == statement_filter]
        if included_filter == "분석 포함":
            filtered = filtered[filtered["included"].fillna(True).astype(bool)]
        elif included_filter == "분석 제외":
            filtered = filtered[~filtered["included"].fillna(True).astype(bool)]
        if changed_only:
            filtered = filtered[filtered["id"].astype(int).isin(changed_ids)]

        focus_id = st.session_state.get("focus_financial_id")
        if focus_id is not None:
            focus_id = safe_int(focus_id, -1)
            if focus_id in set(st.session_state.working_rows["id"].astype(int).tolist()):
                focus_row = st.session_state.working_rows[st.session_state.working_rows["id"].astype(int) == focus_id].iloc[0]
                st.info(f"이상징후에서 선택한 '{focus_row['account']}' 계정만 표시 중입니다.")
                filtered = st.session_state.working_rows[
                    st.session_state.working_rows["id"].astype(int) == focus_id
                ].copy()
                if st.button("전체 데이터 보기"):
                    st.session_state.focus_financial_id = None
                    st.rerun()
            else:
                st.session_state.focus_financial_id = None

        st.caption(
            f"표시 {len(filtered)}개 / 전체 {len(st.session_state.working_rows)}개 · 초안 변경 {draft_change_count()}건"
        )
        editable_cols = ["id", "account", "statement", "prior", "current", "included"]
        editor_df = filtered[editable_cols].copy()
        visible_key = hashlib.sha1(
            ",".join(map(str, editor_df.get("id", pd.Series(dtype=int)).fillna(0).astype(int).tolist())).encode("utf-8")
        ).hexdigest()[:10]
        edited = st.data_editor(
            editor_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            disabled=["id"],
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "account": st.column_config.TextColumn("계정과목", required=True),
                "statement": st.column_config.SelectboxColumn(
                    "재무제표", options=["손익계산서", "재무상태표", "현금흐름표", "기타"], required=True
                ),
                "prior": st.column_config.NumberColumn(st.session_state.prior_label, format="%.0f"),
                "current": st.column_config.NumberColumn(st.session_state.current_label, format="%.0f"),
                "included": st.column_config.CheckboxColumn("분석 포함"),
            },
            key=f"financial_editor_{st.session_state.data_editor_version}_{visible_key}",
        )

        a1, a2, a3, a4, a5 = st.columns([1.2, 1.0, 1.0, 1.1, 1.3])
        if a1.button("편집값 저장", type="primary", use_container_width=True):
            save_financial_editor(filtered, edited)
            st.success("초안에 저장했습니다. 분석에 반영하면 결과가 갱신됩니다.")
            st.rerun()
        if a2.button("실행 취소", use_container_width=True, disabled=not bool(st.session_state.data_undo_stack)):
            undo_data()
            st.rerun()
        if a3.button("원본 복원", use_container_width=True):
            push_data_undo()
            st.session_state.working_rows = st.session_state.source_rows.copy(deep=True)
            st.session_state.data_editor_version += 1
            log_action("SOURCE_RESTORE", st.session_state.file_name)
            st.rerun()
        if a4.button("분석에 반영", type="primary", use_container_width=True):
            apply_analysis()
            st.rerun()
        working_export = st.session_state.working_rows.copy()
        for col in ["series", "period_cells"]:
            if col in working_export.columns:
                working_export[col] = working_export[col].map(
                    lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else ""
                )
        a5.download_button(
            "수정 데이터 CSV",
            working_export.to_csv(index=False).encode("utf-8-sig"),
            "FinSight_수정데이터.csv",
            "text/csv",
            use_container_width=True,
        )

        current_issues = validate_financials(
            st.session_state.working_rows, st.session_state.prior_label, st.session_state.current_label
        )
        error_count = sum(x["type"] == "error" for x in current_issues)
        warn_count = sum(x["type"] == "warn" for x in current_issues)
        ok_count = sum(x["type"] == "ok" for x in current_issues)
        info_count = sum(x["type"] == "info" for x in current_issues)
        st.markdown("#### 데이터 검증")
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("오류", error_count)
        v2.metric("경고", warn_count)
        v3.metric("정상", ok_count)
        v4.metric("참고", info_count)
        with st.expander(
            f"검증 상세 · 오류 {error_count} / 경고 {warn_count}", expanded=bool(error_count or warn_count)
        ):
            for issue in current_issues:
                if issue["type"] == "error":
                    st.error(issue["msg"])
                elif issue["type"] == "warn":
                    st.warning(issue["msg"])
                elif issue["type"] == "ok":
                    st.success(issue["msg"])
                else:
                    st.info(issue["msg"])

        doc_unconfirmed_working = unconfirmed_doc_count(st.session_state.working_rows)
        if doc_unconfirmed_working:
            if st.button(f"문서 추출값 {doc_unconfirmed_working}건 전체 원본 대조 완료"):
                ids = st.session_state.working_rows.loc[
                    st.session_state.working_rows["method"].isin(["pdf", "docx"])
                    & ~st.session_state.working_rows["value_confirmed"].fillna(False).astype(bool),
                    "id",
                ].astype(int).tolist()
                confirm_source_values(ids)
                st.rerun()

        with st.expander("원본 위치 확인", expanded=st.session_state.focus_financial_id is not None):
            row_ids = st.session_state.working_rows["id"].astype(int).tolist()
            default_id = safe_int(st.session_state.get("focus_financial_id"), row_ids[0]) if row_ids else 0
            default_index = row_ids.index(default_id) if default_id in row_ids else 0
            selected_id = st.selectbox(
                "계정 선택",
                row_ids,
                index=default_index,
                format_func=lambda rid: str(
                    st.session_state.working_rows.loc[
                        st.session_state.working_rows["id"].astype(int) == rid, "account"
                    ].iloc[0]
                ),
                key="source_trace_id",
            )
            row = st.session_state.working_rows.loc[
                st.session_state.working_rows["id"].astype(int) == selected_id
            ].iloc[0]
            s1, s2 = st.columns(2)
            s1.caption(f"파일: {row.get('source_file') or '-'}")
            s1.caption(f"시트/페이지: {row.get('source_sheet') or row.get('source_page') or '-'}")
            s1.caption(f"행: {row.get('source_row') or '-'}")
            s2.caption(f"전기 위치: {row.get('prior_cell') or '-'}")
            s2.caption(f"당기 위치: {row.get('current_cell') or '-'}")
            s2.caption(
                f"추출 방식: {row.get('method') or '-'} · 원본 대조 {'완료' if bool(row.get('value_confirmed')) else '필요'}"
            )
            if row.get("method") in {"pdf", "docx"} and not bool(row.get("value_confirmed")):
                if st.button("이 값 원본 대조 완료", use_container_width=False):
                    confirm_source_values([int(selected_id)])
                    st.rerun()
            if st.session_state.doc_preview:
                with st.expander("문서 추출 미리보기"):
                    st.text(st.session_state.doc_preview[:12000])

# ----------------------------- 이상징후 -----------------------------
elif page == "이상징후 분석":
    if st.session_state.analysis_rows.empty:
        st.markdown(
            '<div class="fs-empty"><b>분석할 데이터가 없습니다.</b><br>데이터 화면에서 재무 파일을 먼저 불러와 주세요.</div>',
            unsafe_allow_html=True,
        )
        st.button("재무 데이터 불러오기", type="primary", on_click=go_to, args=("데이터",))
    else:
        anomalies = current_anomalies()
        active_count = int(st.session_state.analysis_rows.get("included", pd.Series(dtype=bool)).fillna(True).astype(bool).sum())
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("분석 계정", active_count)
        m2.metric("확인 필요", len(anomalies))
        m3.metric(
            "우선순위 높음",
            int((anomalies.get("level", pd.Series(dtype=str)) == "높음").sum()) if not anomalies.empty else 0,
        )
        max_change = anomalies["change_pct"].abs().max() if not anomalies.empty and "change_pct" in anomalies.columns else None
        m4.metric("최대 변동폭", "—" if max_change is None or pd.isna(max_change) else f"{max_change:.1f}%")

        if stale:
            st.warning("현재 결과는 수정 전 데이터를 기준으로 합니다. 검토 완료 처리는 재분석 후 가능합니다.")
        if unconfirmed_count:
            st.warning(f"원본 대조 미완료 문서 추출값 {unconfirmed_count}건이 포함되어 있어 분석은 임시 결과입니다.")

        if anomalies.empty:
            st.info("현재 탐지 규칙에서 명확한 검토 신호가 발견되지 않았습니다.")
        else:
            q1, q2, q3 = st.columns([2.0, 1.2, 1.2])
            anomaly_search = q1.text_input("계정 검색", placeholder="계정과목 검색", key="anomaly_search")
            level_filter = q2.selectbox("우선순위 수준", ["전체", "높음", "중간", "낮음"], key="anomaly_level_filter")
            review_filter = q3.selectbox("검토 상태", ["미검토", "전체", "검토 완료"], key="anomaly_review_filter")

            filtered_anom = anomalies.copy()
            filtered_anom["검토 상태"] = filtered_anom["id"].map(
                lambda x: "검토 완료" if safe_int(x) in st.session_state.reviewed else "미검토"
            )
            if anomaly_search.strip():
                filtered_anom = filtered_anom[
                    filtered_anom["account"].fillna("").astype(str).str.contains(anomaly_search.strip(), case=False, na=False)
                ]
            if level_filter != "전체":
                filtered_anom = filtered_anom[filtered_anom["level"] == level_filter]
            if review_filter != "전체":
                filtered_anom = filtered_anom[filtered_anom["검토 상태"] == review_filter]
            filtered_anom["_reviewed"] = filtered_anom["id"].map(lambda x: safe_int(x) in st.session_state.reviewed)
            filtered_anom = filtered_anom.sort_values(["_reviewed", "priority", "account"], ascending=[True, False, True])

            if filtered_anom.empty:
                st.info("현재 필터에 해당하는 이상징후가 없습니다.")
            else:
                display = filtered_anom[
                    ["account", "statement", "change_pct", "priority", "level", "evidence_level", "검토 상태"]
                ].copy()
                display["change_pct"] = display["change_pct"].map(
                    lambda x: None if pd.isna(x) else round(float(x), 1)
                )
                display = display.rename(
                    columns={
                        "account": "계정과목",
                        "statement": "재무제표",
                        "change_pct": "증감률(%)",
                        "priority": "검토 우선순위",
                        "level": "수준",
                        "evidence_level": "근거 수준",
                    }
                )
                st.dataframe(display, use_container_width=True, hide_index=True)

            options = filtered_anom["id"].astype(int).tolist() if not filtered_anom.empty else []
            requested = st.session_state.get("selected_anomaly_id")
            if requested is not None and safe_int(requested, -1) in set(anomalies["id"].astype(int).tolist()):
                requested = safe_int(requested)
                if requested not in options:
                    options = [requested] + options
            if not options:
                options = anomalies["id"].astype(int).tolist()
            if st.session_state.get("selected_anomaly_id") not in options:
                st.session_state.selected_anomaly_id = options[0]

            selected = st.selectbox(
                "상세 검토",
                options,
                key="selected_anomaly_id",
                format_func=lambda rid: str(anomalies.loc[anomalies["id"].astype(int) == rid, "account"].iloc[0]),
            )
            row = anomalies.loc[anomalies["id"].astype(int) == int(selected)].iloc[0]
            st.markdown(f"### {row['account']} · 우선순위 {row['priority']}/100")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("변동 규모", f"{int(row['magnitude'])}/20")
            c2.metric(
                "재무적 중요성", "데이터 부족" if pd.isna(row["materiality"]) else f"{int(row['materiality'])}/25"
            )
            c3.metric("연관계정 신호", f"{int(row['relation'])}/30")
            c4.metric(
                "패턴 이탈",
                "데이터 부족" if not bool(row["pattern_available"]) else f"{int(row['pattern_score'])}/20",
            )
            st.write("**확인 이유**")
            for reason in row.get("reasons") or []:
                st.write(f"- {reason}")
            st.caption(f"근거 수준: {row['evidence_level']} · {row['evidence_reason']}")
            st.caption(
                f"출처: {row.get('source_file') or '-'} · {row.get('source_sheet') or row.get('source_page') or '-'} · "
                f"{row.get('prior_cell') or '-'} / {row.get('current_cell') or '-'}"
            )
            series = row.get("series") if isinstance(row.get("series"), dict) else {}
            if len(series) >= 3:
                trend_df = pd.DataFrame({"기간": list(series.keys()), "금액": list(series.values())}).set_index("기간")
                st.line_chart(trend_df)
                st.caption(str(row.get("pattern_reason") or ""))

            st.button(
                "데이터에서 확인 / 수정",
                use_container_width=False,
                on_click=go_to,
                args=("데이터", None, int(selected)),
            )

            review_key = str(int(selected))
            note = st.text_area(
                "검토 메모",
                value=st.session_state.review_notes.get(review_key, ""),
                key=f"note_{selected}",
                disabled=stale,
            )
            reviewed = st.checkbox(
                "검토 완료",
                value=int(selected) in st.session_state.reviewed,
                key=f"review_{selected}",
                disabled=stale,
            )
            if st.button("검토 상태 저장", type="primary", disabled=stale):
                st.session_state.review_notes[review_key] = note
                if reviewed:
                    st.session_state.reviewed.add(int(selected))
                    st.session_state.reviewed_at[review_key] = datetime.now().isoformat(timespec="seconds")
                else:
                    st.session_state.reviewed.discard(int(selected))
                    st.session_state.reviewed_at.pop(review_key, None)
                log_action("ANOMALY_REVIEW", f"{row['account']} · {'완료' if reviewed else '미완료'}")
                st.success("검토 상태를 저장했습니다.")
                st.rerun()

            report = anomalies.copy()
            report["검토완료"] = report["id"].map(lambda x: safe_int(x) in st.session_state.reviewed)
            report["검토메모"] = report["id"].map(lambda x: st.session_state.review_notes.get(str(safe_int(x)), ""))
            report["검토시간"] = report["id"].map(lambda x: st.session_state.reviewed_at.get(str(safe_int(x)), ""))
            report["reasons"] = report["reasons"].map(lambda x: " | ".join(x) if isinstance(x, list) else x)
            report["series"] = report["series"].map(
                lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else ""
            )
            st.download_button(
                "검토 결과 CSV",
                report.to_csv(index=False).encode("utf-8-sig"),
                "FinSight_검토결과.csv",
                "text/csv",
            )

# ----------------------------- 전표 분류 -----------------------------
elif page == "전표 분류":
    st.caption("전표 추천은 최종 회계처리를 확정하지 않습니다. 현재 엔진은 과거 승인 기억 → 명시적 키워드 → 미분류 순서로 동작합니다.")
    txn_upload = st.file_uploader("전표 Excel / CSV", type=["xlsx", "xls", "csv"], key="txn_upload")
    if txn_upload is not None:
        txn_hash = hashlib.sha256(txn_upload.getvalue()).hexdigest()
        if st.session_state.get("pending_txn_hash") != txn_hash:
            try:
                sheets = read_tabular_file(txn_upload.name, txn_upload.getvalue())
                st.session_state.pending_transaction = {
                    "filename": txn_upload.name,
                    "sheets": sheets,
                    "mappings": {name: detect_transaction_mapping(df) for name, df in sheets.items()},
                }
                st.session_state.pending_txn_hash = txn_hash
            except Exception as exc:
                st.error(f"전표 파일을 읽지 못했습니다: {exc}")
    pending_txn = st.session_state.pending_transaction
    if pending_txn:
        sheet_names = list(pending_txn["sheets"])
        sheet_name = st.selectbox("전표 시트", sheet_names, key="txn_sheet")
        df = pending_txn["sheets"][sheet_name]
        mapping = pending_txn["mappings"][sheet_name]
        headers = mapping["headers"]
        st.dataframe(
            df.iloc[mapping["header_index"] : mapping["header_index"] + 7].fillna(""),
            use_container_width=True,
            hide_index=True,
        )
        cols = st.columns(5)
        date_col = cols[0].selectbox(
            "일자", range(len(headers)), index=mapping["date_col"], format_func=lambda i: headers[i] or f"열 {i+1}", key="txn_date_col"
        )
        desc_col = cols[1].selectbox(
            "적요/거래처", range(len(headers)), index=mapping["desc_col"], format_func=lambda i: headers[i] or f"열 {i+1}", key="txn_desc_col"
        )
        amount_col = cols[2].selectbox(
            "금액", range(len(headers)), index=mapping["amount_col"], format_func=lambda i: headers[i] or f"열 {i+1}", key="txn_amount_col"
        )
        account_options = [-1] + list(range(len(headers)))
        default_account_index = account_options.index(mapping["account_col"]) if mapping["account_col"] in account_options else 0
        account_col = cols[3].selectbox(
            "기존 계정",
            account_options,
            index=default_account_index,
            format_func=lambda i: "없음" if i == -1 else headers[i] or f"열 {i+1}",
            key="txn_account_col",
        )
        mode = cols[4].selectbox(
            "가져오기", ["현재 전표 대신 불러오기", "현재 전표에 이어붙이기"], key="txn_mode"
        )
        if st.button("확인하고 전표 불러오기", type="primary"):
            try:
                existing = st.session_state.transactions if mode.endswith("이어붙이기") else empty_transaction_df()
                start_id = int(existing["id"].max()) + 1 if not existing.empty else 1
                built = build_transactions(
                    df,
                    filename=pending_txn["filename"],
                    date_col=date_col,
                    desc_col=desc_col,
                    amount_col=amount_col,
                    account_col=account_col,
                    header_index=mapping["header_index"],
                    existing=existing,
                    id_start=start_id,
                )
                if built.empty:
                    raise ValueError("선택한 열에서 유효한 전표를 찾지 못했습니다.")
                if mode.endswith("이어붙이기") and not existing.empty:
                    st.session_state.transactions = pd.concat([existing, built], ignore_index=True)
                else:
                    st.session_state.transactions = built
                st.session_state.transactions = refresh_recommendations(st.session_state.transactions)
                st.session_state.txn_file_name = pending_txn["filename"]
                st.session_state.pending_transaction = None
                st.session_state.txn_editor_version += 1
                log_action("TXN_IMPORT", f"{pending_txn['filename']} · {len(built)}건")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    txns = refresh_recommendations(st.session_state.transactions)
    st.session_state.transactions = txns
    if txns.empty:
        if not pending_txn:
            st.markdown(
                '<div class="fs-empty"><b>불러온 전표가 없습니다.</b><br>위에서 Excel 또는 CSV 전표 파일을 불러오면 분류 검토가 시작됩니다.</div>',
                unsafe_allow_html=True,
            )
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("승인 대기", int((txns["status"] == "대기").sum()))
        m2.metric("승인 완료", int((txns["status"] == "승인").sum()))
        m3.metric("반려", int((txns["status"] == "반려").sum()))
        m4.metric("중복 의심", int(txns["duplicate"].fillna(False).astype(bool).sum()))

        t1, t2, t3, t4 = st.columns([2.1, 1.2, 1.25, 1.4])
        txn_search = t1.text_input("전표 검색", placeholder="적요 · 계정과목 검색", key="txn_search")
        txn_status = t2.selectbox("상태", ["전체", "대기", "승인", "반려"], key="txn_status_filter")
        txn_duplicate = t3.selectbox("중복", ["전체", "중복 의심만", "중복 제외"], key="txn_dup_filter")
        txn_unclassified = t4.checkbox("미분류만", value=False, key="txn_unclassified_filter")

        filtered_txns = txns.copy()
        if txn_search.strip():
            query = txn_search.strip()
            mask = pd.Series(False, index=filtered_txns.index)
            for col in ["desc", "original_account", "ai_account", "final_account"]:
                mask = mask | filtered_txns[col].fillna("").astype(str).str.contains(query, case=False, na=False)
            filtered_txns = filtered_txns[mask]
        if txn_status != "전체":
            filtered_txns = filtered_txns[filtered_txns["status"] == txn_status]
        if txn_duplicate == "중복 의심만":
            filtered_txns = filtered_txns[filtered_txns["duplicate"].fillna(False).astype(bool)]
        elif txn_duplicate == "중복 제외":
            filtered_txns = filtered_txns[~filtered_txns["duplicate"].fillna(False).astype(bool)]
        if txn_unclassified:
            filtered_txns = filtered_txns[filtered_txns["final_account"].fillna("미분류") == "미분류"]

        st.caption(f"표시 {len(filtered_txns)}건 / 전체 {len(txns)}건")
        if filtered_txns.empty:
            st.info("현재 필터에 해당하는 전표가 없습니다.")
        else:
            editor_cols = [
                "id",
                "date",
                "desc",
                "amount",
                "original_account",
                "ai_account",
                "recommendation_score",
                "recommendation_source",
                "final_account",
                "status",
                "duplicate",
                "source_row",
            ]
            account_choices = sorted(
                set(ACCOUNT_CATALOG)
                | {str(x) for x in txns["final_account"].dropna().tolist() if str(x).strip()}
                | {str(x) for x in txns["original_account"].dropna().tolist() if str(x).strip()}
            )
            txn_key = hashlib.sha1(
                ",".join(map(str, filtered_txns["id"].astype(int).tolist())).encode("utf-8")
            ).hexdigest()[:10]
            edited_txns = st.data_editor(
                filtered_txns[editor_cols],
                use_container_width=True,
                hide_index=True,
                disabled=["id", "original_account", "ai_account", "recommendation_score", "recommendation_source", "duplicate", "source_row"],
                column_config={
                    "id": "ID",
                    "date": "일자",
                    "desc": "적요",
                    "amount": st.column_config.NumberColumn("금액", format="%.0f"),
                    "original_account": "원본 계정",
                    "ai_account": "추천 계정",
                    "recommendation_score": st.column_config.ProgressColumn("추천 점수", min_value=0, max_value=100),
                    "recommendation_source": "추천 근거",
                    "final_account": st.column_config.SelectboxColumn("최종 계정", options=account_choices),
                    "status": st.column_config.SelectboxColumn("상태", options=["대기", "승인", "반려"]),
                    "duplicate": "중복 의심",
                    "source_row": "원본 행",
                },
                key=f"txn_editor_{st.session_state.txn_editor_version}_{txn_key}",
            )
            if st.button("표시된 전표 저장", type="primary"):
                save_transaction_editor(filtered_txns, edited_txns)
                st.success("전표 검토 결과를 저장했습니다.")
                st.rerun()

        st.download_button(
            "분류 결과 CSV",
            txns.to_csv(index=False).encode("utf-8-sig"),
            "FinSight_전표분류결과.csv",
            "text/csv",
        )
