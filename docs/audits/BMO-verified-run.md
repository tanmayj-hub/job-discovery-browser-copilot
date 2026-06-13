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
- Jobs discovered: `100`
- Jobs scored: `100`
- Jobs saved: `0`
- Pagination stop reason: `max_pages_reached`
- Non-Canada jobs rejected by safety gate: `0`
- Suspicious saved rows: `0`

## What Was Fixed
- The top-right `Canada / US` site selector is not the same as the job-search country filter.
- The collector no longer clicks `FIND JOBS` when the BMO results list is already visible.
- The collector now trusts the BMO results page based on visible result evidence, not just the locale path.
- The collector confirms Canada scope when the visible BMO search-result links are all `EXTERNALENCA` and no visible `EXTERNALENUS` links appear.
- The BMO extractor now prefers visible result rows and no longer pulls hidden US rows from the broader page DOM.
- BMO pagination progress now uses the visible result rows themselves, so it can safely continue across paginated result pages.
- The source-scope check now waits for visible BMO Canada results before deciding whether the page is confirmable.
- A BMO-specific safety net now rejects `EXTERNALENUS` job URLs even if location text is blank.

## Current Review State
- BMO stays out of the verified-only slice for now.
- `config/verified_companies.yaml` remains `verified: false` with `status: needs_review`.
- Reason: source scope is now trusted, and the fresh trusted run saved `0` relevant jobs. That aligns with the user's manual review of the first 10 Canada-filtered pages finding no relevant roles, so BMO remains under review rather than being promoted prematurely.

## Next Action
- Keep BMO available for single-company audits and later scoring review.
- Revisit BMO promotion only if future fresh Canada-scoped runs save genuinely relevant jobs with no suspicious rows.
