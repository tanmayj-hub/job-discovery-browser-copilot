# BMO Verified Run Status

## Outcome
- Run date: 2026-06-12
- Verification decision: `needs_review`
- Trusted source URL: `https://jobs.bmo.com/ca/en/search-results`
- Source scope status: `canada_scope_confirmed`
- Canada scope confirmed before pagination: `True`
- Source scope method: `page_evidence`
- Broad diagnostic collection used for verification: `False`

## Trusted Run Result
- `python -m src.main daily-run --company "BMO"`
- Companies checked: `1`
- Companies skipped: `0`
- Jobs discovered: `20`
- Jobs scored: `20`
- Jobs saved: `0`
- Pagination stop reason: `no_new_job_urls`
- Non-Canada jobs rejected by safety gate: `0`

## What Was Fixed
- The top-right `Canada / US` site selector is not the same as the job-search country filter.
- The collector now trusts the BMO results page based on visible result evidence, not just the locale path.
- The collector confirms Canada scope when the visible BMO search-result links are all `EXTERNALENCA` and no visible `EXTERNALENUS` links appear.
- The BMO extractor now prefers visible result rows and no longer pulls hidden US rows from the broader page DOM.
- A BMO-specific safety net now rejects `EXTERNALENUS` job URLs even if location text is blank.

## Current Review State
- BMO stays out of the verified-only slice for now.
- `config/verified_companies.yaml` remains `verified: false` with `status: needs_review`.
- Reason: source scope is now trusted, but the current BMO run saved `0` relevant jobs, so the next review point is scoring/fit rather than URL trust.

## Next Action
- Keep BMO available for single-company audits and scoring review.
- Revisit BMO promotion only after the saved-job quality is strong enough for the trusted verified-only slice.
