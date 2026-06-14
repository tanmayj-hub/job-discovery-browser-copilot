# Scotiabank Fix Report

## Issue Found
- The original config pointed at the broad Scotiabank careers landing page, which did not expose job results or trusted Canada scope before pagination.
- After switching to the direct official results URL, the trusted run still skipped because the scope detector did not recognize `locationsearch=canada` as an explicit Canada filter.

## Fix Applied
- Updated [config/companies.yaml](C:/projects/job-discovery-browser-copilot/config/companies.yaml) to use:
  `https://jobs.scotiabank.com/search/?createNewAlert=false&q=&locationsearch=canada`
- Updated the trusted scope detector in [browser_collector.py](C:/projects/job-discovery-browser-copilot/src/collectors/browser_collector.py) so `locationsearch=canada` counts as an explicit Canada-scoped URL signal.

## Fresh Results
- Trusted run: `258` discovered, `258` scored, `6` relevant, `6` saved.
- Diagnostic run: `258` discovered, `6` relevant, `10` pages visited, stop reason `max_pages_reached`.
- Source scope status: `canada_scope_confirmed`
- Manual recall status for the current bank slice: `1 / 5` matched, `4 / 5` missed by collection.

## Verification Decision
- Decision: `needs_review`

## Remaining Blocker
- The source is now trusted and stable, but the current 10-page collection slice still misses most manually found target URLs from the audit pack.
- That is a recall gap, not a scope-gate gap.

## Exact Next Step
- Keep Scotiabank out of the verified-only slice for now.
- Investigate whether the missed URLs require deeper safe pagination, extraction tuning, or both.
