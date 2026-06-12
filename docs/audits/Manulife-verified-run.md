# Manulife Verified Run Status

## Outcome
- Run date: 2026-06-12
- Verification decision: `usable`
- Trusted source URL: `https://manulife.wd3.myworkdayjobs.com/en-US/MFCJH_Jobs?Location_Country=a30a87ed25634629aa6c3958aa2b91ea`
- Source scope status: `canada_scope_confirmed`
- Canada scope confirmed before pagination: `True`
- Source scope method: `url_filter`
- Broad diagnostic collection used for verification: `False`

## Trusted Run Result
- `python -m src.main daily-run --company "Manulife"`
- Companies checked: `1`
- Companies skipped: `0`
- Jobs discovered: `144`
- Jobs scored: `144`
- Jobs saved: `9`
- Pagination stop reason: `next_disabled_or_missing`
- Non-Canada jobs rejected by safety gate: `0`
- Relevant jobs with blank location text: `9`

## Manual Next-Slice Audit
- Manual career page reviewed: `https://manulife.wd3.myworkdayjobs.com/en-US/MFCJH_Jobs?Location_Country=a30a87ed25634629aa6c3958aa2b91ea`
- Manual filter used: `Canada`
- Pages checked manually: first `10`
- Manual URL recall summary:
  - `saved_by_mvp`: `1`
  - `extracted_but_rejected_by_scoring`: `1`
  - `outside_scope`: `2`
  - `missed_by_collection`: `0`
- Manual URLs were either saved or correctly surfaced as collected-but-not-relevant. No collection miss remained in this slice.

## Decision
- Manulife is promoted into the verified-only slice.
- `config/verified_companies.yaml` is updated to `verified: true` and `status: usable`.
- Remaining follow-up: improve location text extraction for Workday rows so saved Manulife jobs no longer rely on source-level Canada scope alone for location readability.
