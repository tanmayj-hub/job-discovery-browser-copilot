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
- 2 not present in the fresh Canada/newest-first pages 1-75:
  - `R-0000178346` AI Quality Engineer
  - `R-0000178580` Director, SRE and AI Ops, GFT

The direct public job URLs could not be independently checked with a non-browser HTTP client because RBC closed those connections. Their current active/expired state is therefore unknown rather than assumed. This is a manual-recall gap, not evidence of a scope or pagination failure.

## Decision
RBC remains `manual_recall_incomplete` and is excluded from verified-only runs. It can be promoted only after a user confirms the two URLs are inactive/outside the current listing or a fresh official browser check establishes their status. The collection implementation itself is stable and the audit-only 75-page result is complete.
