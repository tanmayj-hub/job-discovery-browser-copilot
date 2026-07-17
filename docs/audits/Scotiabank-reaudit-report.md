# Scotiabank Re-Audit Report

- Official source: `https://jobs.scotiabank.com/search/?createNewAlert=false&q=&locationsearch=canada`
- Canada confirmation: URL `locationsearch=canada` before pagination.
- Sort: requested `source_default_all_pages`; used source order; status `unavailable_by_source`; method `none`.
- Page policy: `all_available` with a 500-page defensive ceiling.
- Pages scanned: 53.
- Discovered / scored / saved: 1,316 / 1,316 / 3 relevant candidates in the diagnostic (the diagnostic does not save jobs).
- Stop reason: `no_more_pages` after the source reported its final page.
- Complete: yes.
- Fixes applied: cookie-footer false-positive prevention, Next.js job-link pagination guard, and final-page detection.
- Decision: remains verified for Canada-scoped collection. Manual URL scoring/relevance review remains separate from collection recall.
