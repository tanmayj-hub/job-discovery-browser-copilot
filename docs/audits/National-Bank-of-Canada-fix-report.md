# National Bank of Canada Fix Report

## Issue Found
- National Bank was running only in diagnostic mode because the collector could not prove Canada scope before pagination.
- The collector was also failing to follow the board's public offset-based pagination, so the manually expected Senior DevOps Integrator role never appeared in the scored-candidate export.

## Fix Applied
- Confirmed Canada scope from National Bank's public `en_CA` search-results page evidence before pagination.
- Added support for the board's public `Go to Next Page` pagination links so the collector can walk result offsets safely.
- Reused the higher per-source candidate cap so dense public pages are not truncated mid-audit.

## Fresh Run Metrics
- Run date: 2026-06-13
- Source scope: confirmed before pagination by public page evidence
- Pages visited: 10
- Jobs discovered: 212
- Jobs scored: 212
- Relevant jobs after scoring: 5
- Explicit non-Canada jobs rejected: 0

## Manual Recall Result
- `saved_by_mvp`: 1
- `extracted_but_rejected_by_scoring`: 1
- `missed_by_collection`: 0

## Verification Decision
- Decision: promote to `usable`
- Reason: Canada scope is confirmed before pagination, trusted pagination reaches the first 10 public result pages, and the current next-slice manual audit shows no active collection misses.

## Remaining Blockers
- The manually expected Senior DevOps Integrator role is now extracted but still rejected by scoring, so any follow-up work should stay in the scoring/tuning lane rather than the collection lane.
