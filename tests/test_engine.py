from __future__ import annotations

import pandas as pd

from core.anomaly import analyze_financials
from core.io import detect_financial_mapping, parse_number
from core.sample import financial_sample
from core.transactions import mark_duplicates, recommend_transaction
from core.trend import pattern_signal
from core.validation import validate_financials


def test_parse_number_accounting_formats():
    assert parse_number("1,234") == 1234
    assert parse_number("(1,234)") == -1234
    assert parse_number("-") == 0
    assert parse_number("") is None


def test_mapping_orders_years_chronologically():
    df = pd.DataFrame([
        ["계정과목", "2025", "2024"],
        ["매출액", "100", "90"],
    ])
    mapping = detect_financial_mapping(df)
    assert mapping["prior_label"] == "2024"
    assert mapping["current_label"] == "2025"
    assert mapping["prior_col"] == 2
    assert mapping["current_col"] == 1


def test_pattern_signal_detects_spike():
    signal = pattern_signal({"2022": 10, "2023": 11, "2024": 12, "2025": 45})
    assert signal["available"] is True
    assert signal["score"] >= 13


def test_balance_sheet_equation_passes_sample():
    issues = validate_financials(financial_sample(), "2024", "2025")
    assert not any(i["code"] == "BS_EQ" for i in issues)
    assert any(i["code"] == "BS_EQ_OK" for i in issues)


def test_anomaly_engine_returns_priority():
    result = analyze_financials(financial_sample())
    assert not result.empty
    target = result[result["account"] == "접대비"].iloc[0]
    assert target["priority"] > 0
    assert target["pattern_available"]


def test_transaction_memory_excludes_self_leak():
    records = [
        {"id": 1, "desc": "ABC 서비스", "status": "승인", "final_account": "지급수수료"},
    ]
    rec = recommend_transaction("ABC 서비스", records, exclude_id=1)
    assert rec["account"] == "미분류"
    rec2 = recommend_transaction("ABC 서비스", records, exclude_id=99)
    assert rec2["account"] == "지급수수료"


def test_duplicate_detection():
    df = pd.DataFrame([
        {"id": 1, "date": "2026-01-01", "desc": "AWS", "amount": 100},
        {"id": 2, "date": "2026-01-01", "desc": "AWS", "amount": 100},
    ])
    out = mark_duplicates(df)
    assert out["duplicate"].tolist() == [True, True]


def test_anomaly_output_requires_explicit_reason():
    result = analyze_financials(financial_sample())
    assert not result.empty
    assert result["reasons"].map(bool).all()
    assert "자산총계" not in set(result["account"])
    assert "부채총계" not in set(result["account"])
    assert "자본총계" not in set(result["account"])


def test_streamlit_app_does_not_autoload_sample_data():
    from pathlib import Path

    app_text = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "financial_sample(" not in app_text
    assert "transaction_sample(" not in app_text
    assert '"source_rows": empty_financial_df()' in app_text
    assert '"transactions": empty_transaction_df()' in app_text
