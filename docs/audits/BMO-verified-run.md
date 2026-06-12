# BMO Verified Run Status

## Outcome
- Run date: 2026-06-12
- Verification decision: `needs_review`
- Trusted source URL: `https://jobs.bmo.com/ca/en/search-results`
- Source scope status: `canada_scope_unconfirmed`
- Canada scope confirmed before pagination: `False`
- Source scope method: `manual_audit_url`
- Broad diagnostic collection used for verification: `False`

## Trusted Run Result
- `python -m src.main daily-run --company "BMO"`
- Companies checked: `1`
- Companies skipped: `1`
- Jobs discovered: `0`
- Jobs scored: `0`
- Jobs saved: `0`
- Pagination stop reason: `scope_not_confirmed_before_pagination`
- Non-Canada jobs rejected by safety gate: `0`

## Separate Diagnostic Review
- `python -m src.main audit diagnose-company-collection --company "BMO"`
- Diagnostic source scope status: `canada_scope_unconfirmed`
- Broad diagnostic collection: `True`
- Pages visited: `10`
- Candidate jobs discovered: `104`
- Relevant jobs after scoring: `0`
- Observed behavior: the `/ca/en/search-results` page still exposed mixed `ENCA` and `ENUS` job URLs, so the locale path alone is not strong enough to trust as a Canada-only listing.

## Manual Audit Alignment
- Manual career page reviewed: `https://jobs.bmo.com/ca/en/search-results`
- Manual filter used: `Canada`
- Pages checked manually: first `10`
- Manual note: no relevant jobs were found in the first 10 Canada-scoped pages.

## Decision
- BMO stays out of the verified-only slice.
- `config/verified_companies.yaml` remains `verified: false` and `status: needs_review`.
- Next action: keep using the source-scope diagnostic path until BMO exposes a stable Canada-only URL or a public pre-pagination Canada filter that the MVP can confirm deterministically.
