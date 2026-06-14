# CGI Stability Check

## Reason For Check
- The previous verified-only smoke reported a fresh CGI warning:
  `Page.content: Unable to retrieve content because the page is navigating and changing the content.`

## Sequential Re-Run
- Trusted run:
  `python -m src.main daily-run --company "CGI"`
  - `413` discovered
  - `413` scored
  - `54` relevant
  - `54` saved
- Diagnostic run:
  `python -m src.main audit diagnose-company-collection --company "CGI" --output docs/audits/CGI-collection-diagnostic.md --export-scored-candidates data/exports/audits/CGI-scored-candidates.csv`
  - `413` discovered
  - `53` relevant
  - `9` pages visited
  - stop reason `next_disabled_or_missing`

## Diagnosis
- The warning was not reproducible on the sequential re-run.
- Canada scope remained confirmed through the direct `CountryID=CA` source URL.
- Pagination completed cleanly through the visible Njoyn page sequence.
- Valid jobs were still saved in the trusted run.

## Likely Cause
- Most likely a transient timing race while the smoke run tried to read page HTML during navigation.
- Current evidence does not point to a persistent source-scope, pagination, or extraction blocker.

## Decision
- CGI remains `verified: true` and `status: usable`.
- No source-specific code change was required in this task because the issue did not reproduce.
