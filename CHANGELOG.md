# Changelog

## V2.6.1 — Blank Start + Workflow UI Recovery

### Startup
- Removed automatic sample financial data and sample transactions from the running app.
- A new session now starts as a blank project on the Data screen.
- Replaced the old sample-reset action with `새 빈 프로젝트`.

### Workflow / readability
- Restored financial account search, statement filter, included/excluded filter, and changed-only view.
- Restored one-click navigation from summary → anomaly detail and anomaly → source data edit.
- Added one-level workflow support through a 20-step financial edit undo stack plus source restore.
- Reordered review queues so unreviewed, higher-priority items appear first.
- Replaced internal English anomaly-table field names with Korean user-facing labels.
- Reworked validation into readable error/warning/normal/info summaries with expandable details.
- Restored transaction search, status, duplicate, and unclassified filters.

### Safety / state handling
- PDF/DOCX values are shown as `원본 대조 필요`, and analysis is labeled `임시 결과` until confirmation.
- Added individual and bulk source-confirmation actions for extracted document values.
- Fixed PDF/DOCX import so old review notes and reviewed timestamps cannot remain on a newly imported document.
- Review completion is disabled while edited financial data is stale.
- Filtered editor saves now merge only visible rows instead of dropping hidden rows.

### Anomaly display
- An anomaly must now have an explicit review reason (large change, relationship signal, or meaningful historical-pattern deviation).
- Materiality still affects priority, but materiality alone no longer creates an anomaly.
- This prevents total/benchmark rows from appearing as anomalies merely because they are large.

### Packaging
- Removed runtime cache folders from the release package.
- Added regression tests for explicit anomaly reasons and blank startup.

## V2.6 — Python Engine

### Core migration
- Moved financial parsing, validation, anomaly scoring, trend analysis, transaction recommendation, duplicate detection, and project serialization into Python modules.
- Replaced the V2.5 iframe/browser engine with native Streamlit state + pandas processing.
- Archived the old V2.5 HTML implementation under `legacy/index_v2_5.html`; it is no longer the production execution path.

### Data handling
- Added Python Excel/CSV parsing with explicit mapping confirmation.
- Preserved Excel/CSV source row and cell references.
- Added Python PDF/DOCX extraction with `value_confirmed=False` by default.
- Added editable working data separated from source and analysis data.

### Analysis
- Ported deterministic priority scoring: magnitude, statement-specific materiality benchmark, relation rules, and multi-period pattern signal.
- Ported median/MAD-based multi-period trend deviation.
- Preserved review states only when the resulting anomaly fingerprint remains unchanged after re-analysis.

### Transactions
- Ported approved-history memory and keyword rules to Python.
- Preserved self-leak prevention by excluding the current transaction from its own approved-memory lookup.
- Added Python duplicate detection and editable review status.

### Reliability
- Added pytest coverage for accounting-number parsing, period mapping direction, trend spike detection, balance-sheet equation validation, anomaly output, transaction self-leak prevention, and duplicate detection.
