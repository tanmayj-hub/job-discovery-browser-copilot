# CGI Fix Report

## Issue Found
- CGI was starting from the broad `cgi.com` landing page instead of the direct Canada Njoyn board.
- Manual recall matching was weak for Njoyn because URL comparison collapsed on the generic `xweb.asp` path.
- Extraction also kept generic `View Job Details` shell links, which inflated counts.
- Trusted pagination was still stopping after page 1 because CGI's board exposes `NEXT` through `javascript:gotopage(...)`.
- Even after pagination started working, the collector capped per-source candidates at `max_pages * 20`, which truncated later CGI pages before manual recall could be completed.

## Fix Applied
- Updated the configured source URL to CGI's direct Canada board:
  `https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting&CLID=21001&CountryID=CA&lang=1`
- Added Njoyn job identity matching by `Jobid` / `BRID` for manual recall.
- Filtered generic `View Job Details` rows from extraction.
- Tightened the Canada safety gate so `Any CGI location` rows without a Canada marker are rejected.
- Allowed safe JavaScript `gotopage(...)` pagination when the control is clearly the public `NEXT` action.
- Raised the per-source candidate cap so dense public boards like CGI are not truncated after the first 200 unique rows.

## Fresh Run Metrics
- Run date: 2026-06-13
- Source scope: confirmed before pagination by URL filter
- Pages visited: 9
- Jobs discovered: 416
- Jobs scored: 416
- Relevant jobs after scoring: 53
- Explicit non-Canada jobs rejected: 1

## Manual Recall Result
- `saved_by_mvp`: 15
- `extracted_but_rejected_by_scoring`: 3
- `missed_by_collection`: 0

## Verification Decision
- Decision: promote to `usable`
- Reason: Canada scope is confirmed before pagination, the safety gate prevents non-Canada saves, and the current next-slice manual audit no longer shows active collection misses.

## Remaining Blockers
- Some manually expected CGI rows are still rejected by scoring, which is now the correct next-stage tuning problem rather than a collection problem.
- A historical stale CGI job row may still exist in SQLite from an earlier run; the fresh trusted diagnostic is the source of truth for current verification.
