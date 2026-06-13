# NTT DATA Fix Report

## Issue Found
- NTT DATA was configured on a broad landing page and never reached a trusted Canada-scoped run.
- The public search-results surface required cookie handling plus a visible Country facet before pagination.

## Fix Applied
- Updated the configured source URL to the public search-results page:
  `https://careers.services.global.ntt/global/en/search-results`
- Added a safe NTT DATA country-facet step that applies `Country = Canada` before pagination.
- Kept the flow headed and public-only, with no login/CAPTCHA bypass and no stealth behavior.

## Fresh Run Metrics
- Run date: 2026-06-13
- Source scope: confirmed before pagination by public UI filter
- Pages visited: 4
- Jobs discovered: 78
- Jobs scored: 78
- Relevant jobs after scoring: 9
- Explicit non-Canada jobs rejected: 0

## Manual Recall Result
- `extracted_and_relevant`: 4
- `missed_by_collection`: 0

## Verification Decision
- Decision: promote to verified
- Reason: the source now completes a trusted Canada-scoped run and the audited NTT DATA URLs are all recovered by the current collector.

## Remaining Notes
- The page still depends on cookie handling and the public country facet, so future regressions should be checked against the diagnostic report first.
