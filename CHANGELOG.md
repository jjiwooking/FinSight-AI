# Changelog

## V2.5 Streamlit Package

### Deployment packaging
- Added `app.py` as the Streamlit Community Cloud entrypoint.
- Embedded the existing V2.5 HTML workspace with `streamlit.components.v1.html` to preserve current UI and behavior.
- Added `requirements.txt` with Streamlit dependency only.
- Added `.streamlit/config.toml` for a dark, headless deployment shell.
- Added `.gitignore` and GitHub/Streamlit deployment documentation.
- Moved test CSVs into `sample_data/`.
- Kept `index.html` at repository root so the same build can also be served as a plain static page.

## V2.5 Core

- Added actual Excel/CSV transaction-file import with mapping for date, description/vendor, amount, and optional existing account.
- Added transaction replace/append modes, source-row tracking, duplicate suspicion detection, search/status filters, and classified-transaction CSV export.
- Replaced hardcoded-only transaction recommendation behavior with a transparent local recommender: prior approved exact-description memory first, then explicit keyword rules, otherwise unclassified.
- Preserves original account values from imported transaction files separately from recommendations and final user selections.
- Added multi-period financial series capture when Excel/CSV includes 3+ year columns. Latest two years remain prior/current while earlier years are retained for trend analysis.
- Added robust trend-deviation signal using historical change median and MAD-based scaling. Pattern score is only available when at least 3 usable periods exist.
- Integrated real pattern signal into review-priority calculation instead of displaying a permanent data-insufficient placeholder.
- Added per-account sparkline and top multi-period trend-deviation summary.
- Editing prior/current values also updates matching period values so stale-analysis detection remains consistent.
- Project schema advanced to v3 and remains backward-compatible with v1/v2 projects.

### Product principle
- Convenience/readability first: transaction upload avoids manual row-by-row entry; trend analysis appears only when enough evidence exists.
- No fake AI probability: recommendation scores remain explicitly relative review scores, and local rule/memory source is shown.
