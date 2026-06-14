# Scotiabank Fix Report

## Issue Found
- The trusted Canada-scoped Scotiabank source was already fixed at the URL level, but the current global 10-page cap left 4 manually expected URLs unmatched.
- Direct page checks showed those URLs lived deeper in the official Canada listing, so the remaining problem was page depth, not source scope.

## Fix Applied
- Kept the official trusted source URL:
  `https://jobs.scotiabank.com/search/?createNewAlert=false&q=&locationsearch=canada`
- Added a narrow per-company pagination override in `config/discovery.yaml`:
  `Scotiabank: 15`

## Fresh Results
- Trusted run: `383` discovered, `383` scored, `6` relevant, `6` saved.
- Diagnostic run: `383` discovered, `6` relevant, `15` pages visited, stop reason `max_pages_reached`.
- Source scope status: `canada_scope_confirmed`
- Explicit non-Canada saved jobs in the latest verified-only smoke: `0`
- Suspicious saved rows in the latest verified-only smoke: `0`

## Manual Recall Result
- Current bank-slice audit summary:
  - `4 / 5` `extracted_and_relevant`
  - `1 / 5` `extracted_but_rejected_by_scoring`
  - `0` active collection misses
- The remaining non-saved expected URL is:
  `Staff Software Engineer (Cloud CICD Platforms)`
- That row is now a scoring decision, not a collection failure.

## Verification Decision
- Decision: `usable`

## Promotion Result
- Scotiabank is now promoted into the verified-only slice.
- Reason: the trusted Canada-scoped source is stable, deeper safe pagination closes the manual collection gap, and the remaining manual discrepancy is scoring-only.
