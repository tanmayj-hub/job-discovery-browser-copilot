# RBC Fix Report

## Issue Found
- The official RBC results board was real, but the trusted MVP run could not confirm Canada scope before pagination.
- The public page needed a safe pre-pagination `Country=Canada` interaction instead of locale-only URL evidence.

## Fix Applied
- Kept the direct official source URL:
  `https://jobs.rbc.com/ca/en/search-results?from=140&s=1`
- Added a safe public RBC `Country=Canada` facet flow in the browser collector.
- Added trusted visible-page evidence so the run records Canada scope as confirmed before pagination.

## Fresh Results
- Trusted run: `100` discovered, `100` scored, `4` relevant, `4` saved.
- Diagnostic run: `100` discovered, `4` relevant, `10` pages visited, stop reason `max_pages_reached`.
- Extra 15-page diagnostic check: `150` discovered, `5` relevant, and the 4 manually expected RBC URLs still did not appear in the broad Canada-only listing.
- Source scope status: `canada_scope_confirmed`
- Explicit non-Canada saved jobs: `0`
- Suspicious saved rows in the latest verified-only smoke: `0`

## Manual Recall Interpretation
- The current manual expected RBC URLs were gathered with extra manual subcategory filters:
  `technology`, `project and program management`, and `operations and business management`.
- Those extra filters are not part of the trusted MVP collect-first policy.
- Because the same 4 URLs still do not appear even after a 15-page Canada-only diagnostic run, the remaining mismatch is best treated as `outside_current_listing_scope` for the current trusted MVP slice, not as a broken Canada filter.

## Verification Decision
- Decision: `needs_review`

## Why It Was Not Promoted In This Task
- The source-scope blocker is fixed.
- The remaining audit mismatch is now a workflow-comparison problem, not a Canada-filter problem.
- Before promotion, RBC still needs a cleaner apples-to-apples manual audit pack that matches the trusted broad Canada-only MVP policy.

## Recommended Next Step
- Keep RBC available for single-company runs.
- When we revisit RBC, build a manual audit pack that uses the same broad Canada-only source scope as the trusted collector, then re-evaluate promotion.
