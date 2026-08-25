"""FinSight AI Python engine."""

from .anomaly import analyze_financials
from .io import (
    build_financial_rows,
    build_transactions,
    detect_financial_mapping,
    detect_transaction_mapping,
    infer_statement,
    parse_document,
    parse_number,
    read_tabular_file,
)
from .transactions import refresh_recommendations
from .validation import validate_financials

__all__ = [
    "analyze_financials",
    "build_financial_rows",
    "build_transactions",
    "detect_financial_mapping",
    "detect_transaction_mapping",
    "infer_statement",
    "parse_document",
    "parse_number",
    "read_tabular_file",
    "refresh_recommendations",
    "validate_financials",
]
