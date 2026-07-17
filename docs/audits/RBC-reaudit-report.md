# RBC Re-Audit Report

## Fresh Audit Evidence
- Official source: `https://jobs.rbc.com/ca/en/search-results`
- Canada scope: confirmed through RBC's public Country=Canada facet before pagination.
- Sort: Most Recent confirmed before pagination.
- Production policy: unchanged at 20 pages.
- Audit policy: pages 1-75 in deterministic chunks of 25.
- Coverage: 75 contiguous pages, no missing pages, no duplicate page fingerprints.
- Candidates: 750 before and after canonical URL deduplication.
- Relevant after current scoring: 46.
- Location safety gate: 0 explicit non-Canada relevant rows.

## Manual URL Recall
The fresh merged audit matched 29 of 31 manually supplied RBC URLs:
- 6 saved by the MVP.
- 15 extracted and relevant in the audit result.
- 8 extracted but rejected by the existing scoring rules.
- 2 active jobs were not present in the fresh Canada/newest-first pages 1-75:
  - `R-0000178346` AI Quality Engineer: `active_but_not_in_current_listing`. The user confirmed it is active and potentially adjacent to the target scope through CI/CD and cloud skills. It was not evidence of a page-1-75 extraction miss because it was absent from that audited listing.
  - `R-0000178580` Director, SRE and AI Ops, GFT: `active_but_not_in_current_listing`. The user confirmed it is active, but Director-level and outside the target seniority scope. It remains a useful scoring-rejection example if it returns to the broad listing.

## Decision
RBC is promoted to `usable` for verified-only runs. Canada scope and Most Recent were confirmed before pagination; all audit pages 1-75 were covered without duplicate fingerprints; the safety gate found zero explicit non-Canada relevant rows; and no active in-scope collection miss remains. Production remains capped at 20 pages. The 75-page traversal was audit-only.
