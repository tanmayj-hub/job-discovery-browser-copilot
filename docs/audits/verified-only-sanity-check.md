# Verified-Only Sanity Check

## Run
- Date: 2026-06-14
- Command: `python -m src.main daily-run --verified-only`
- Dashboard import smoke: `python -c "import src.dashboard.app; print('dashboard_import_ok')"`

## Current Verified Usable List
- Aviva Canada
- BMO
- Canada Life
- CGI
- IBM Consulting
- Manulife
- National Bank of Canada
- NTT DATA
- Sun Life
- TD
- Scotiabank

## Metrics
- Companies checked: 11
- Companies skipped: 0
- Jobs discovered: 1899
- Jobs scored: 1899
- Jobs relevant: 108
- Jobs saved: 108
- Explicit non-Canada jobs rejected by safety gate: 40
- Suspicious saved rows: 0
- Errors: 0

## Source Warnings
- None in the latest verified-only smoke.
- CGI's earlier extraction warning was rechecked separately and was not reproducible.

## Dashboard Sanity
- The dashboard module imports successfully from the repo virtualenv.
- The current dashboard code supports:
  - verified-company filtering
  - provisional verified records like BMO
  - saved jobs and job URLs
  - source status rows with scope/readiness
  - relevance-tier display
- Result: the dashboard is usable for daily review of the current verified slice.

## Next Bank Status
- RBC: scope fix is complete, but the current manual URL set used extra subcategory filters and is not yet an apples-to-apples verification pack for the trusted broad Canada-only policy. Status stays `needs_manual_audit` until the clean pack in [RBC-clean-canada-only-audit-pack.md](/C:/projects/job-discovery-browser-copilot/docs/audits/RBC-clean-canada-only-audit-pack.md) is reviewed.
- Scotiabank: deeper safe pagination removed the active collection misses. Status is now `usable`.

## Conclusion
- The verified-only dashboard/data path is currently usable for daily review.
- Scotiabank now joins the trusted verified slice.
- RBC remains available for single-company runs but stays outside verified-only until its manual audit pack matches the trusted collection policy more closely.
