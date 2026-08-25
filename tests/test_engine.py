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


def test_money_format_uses_thousands_separator_and_display_units():
    from core.utils import format_money

    assert format_money(1_000_000) == "1,000,000"
    assert format_money(123_456_789, unit="백만원") == "123.46"
    assert format_money(123_456_789, unit="억원") == "1.23"


def _load_sample_financial(filename: str):
    from pathlib import Path
    from core.io import build_financial_rows, infer_statement, read_tabular_file

    base = Path(__file__).resolve().parents[1]
    data = (base / "sample_data" / filename).read_bytes()
    sheets = read_tabular_file(filename, data)
    parts = []
    first_mapping = None
    next_id = 1
    for sheet_name, raw in sheets.items():
        mapping = detect_financial_mapping(raw)
        first_mapping = first_mapping or mapping
        part = build_financial_rows(
            raw,
            filename=filename,
            sheet_name=sheet_name,
            statement=infer_statement(sheet_name),
            account_col=mapping["account_col"],
            prior_col=mapping["prior_col"],
            current_col=mapping["current_col"],
            header_index=mapping["header_index"],
            multiplier=1,
            method="excel",
            period_cols=mapping["period_cols"],
            id_start=next_id,
        )
        parts.append(part)
        next_id += len(part)
    return pd.concat(parts, ignore_index=True), first_mapping


def test_clean_validation_sample_passes_and_has_zero_anomalies():
    rows, mapping = _load_sample_financial("sample_financial_valid_4year.xlsx")
    issues = validate_financials(rows, mapping["prior_label"], mapping["current_label"])
    assert not any(i["type"] == "error" for i in issues)
    assert any(i["code"] == "BS_EQ_OK" for i in issues)
    assert any(i["code"] == "CF_EQ_OK" for i in issues)
    assert analyze_financials(rows).empty


def test_error_validation_sample_triggers_expected_controls():
    rows, mapping = _load_sample_financial("sample_financial_validation_errors.xlsx")
    issues = validate_financials(rows, mapping["prior_label"], mapping["current_label"])
    codes = {i["code"] for i in issues}
    assert {"FORMAT", "DUP", "BS_EQ", "CF_EQ"}.issubset(codes)


def test_source_unit_conversion_is_exact_in_krw():
    from core.io import build_financial_rows, detect_unit_multiplier

    raw = pd.DataFrame([
        ["단위: 백만원", "", ""],
        ["계정과목", "2024", "2025"],
        ["매출액", "1,234.5", "1,500.25"],
    ])
    mapping = detect_financial_mapping(raw)
    multiplier = detect_unit_multiplier("단위: 백만원")
    rows = build_financial_rows(
        raw,
        filename="unit_test.xlsx",
        sheet_name="손익계산서",
        statement="손익계산서",
        account_col=mapping["account_col"],
        prior_col=mapping["prior_col"],
        current_col=mapping["current_col"],
        header_index=mapping["header_index"],
        multiplier=multiplier,
        method="excel",
        period_cols=mapping["period_cols"],
    )
    assert multiplier == 1_000_000
    assert rows.iloc[0]["prior"] == 1_234_500_000
    assert rows.iloc[0]["current"] == 1_500_250_000


def test_transaction_validation_sample_detects_duplicate_rows():
    from pathlib import Path
    from core.io import build_transactions, detect_transaction_mapping, read_tabular_file
    from core.transactions import mark_duplicates

    base = Path(__file__).resolve().parents[1]
    filename = "sample_transactions_validation.xlsx"
    sheets = read_tabular_file(filename, (base / "sample_data" / filename).read_bytes())
    raw = sheets["전표"]
    mapping = detect_transaction_mapping(raw)
    txns = build_transactions(
        raw,
        filename=filename,
        date_col=mapping["date_col"],
        desc_col=mapping["desc_col"],
        amount_col=mapping["amount_col"],
        account_col=mapping["account_col"],
        header_index=mapping["header_index"],
    )
    txns = mark_duplicates(txns)
    assert len(txns) == 8
    assert int(txns["duplicate"].sum()) == 2
    assert -125_000 in set(txns["amount"].tolist())
