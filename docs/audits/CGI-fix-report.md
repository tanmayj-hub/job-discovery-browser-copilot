# CGI Fix Report

## Issue Found
- CGI was starting from the broad `cgi.com` landing page instead of the direct Canada Njoyn board.
- Manual recall matching was weak for Njoyn because URL comparison collapsed on the generic `xweb.asp` path.
- Extraction also kept generic `View Job Details` shell links, which inflated counts.

## Fix Applied
- Updated the configured source URL to CGI's direct Canada board:
  `https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting&CLID=21001&CountryID=CA&lang=1`
- Added Njoyn job identity matching by `Jobid` / `BRID` for manual recall.
- Filtered generic `View Job Details` rows from extraction.
- Tightened the Canada safety gate so `Any CGI location` rows without a Canada marker are rejected.

## Fresh Run Metrics
- Run date: 2026-06-13
- Source scope: confirmed before pagination by URL filter
- Pages visited: 1
- Jobs discovered: 51
- Jobs scored: 51
- Relevant jobs after scoring: 7
- Explicit non-Canada jobs rejected: 1

## Manual Recall Result
- `saved_by_mvp`: 5
- `extracted_but_rejected_by_scoring`: 1
- `missed_by_collection`: 12

## Verification Decision
- Decision: keep as `needs_review`
- Reason: the source is materially better and now produces trusted Canada-scoped results, but the current next-slice audit still has too many unresolved manual URL misses to promote CGI into the verified-only slice.

## Remaining Blockers
- Several manually expected CGI URLs from the earlier audit are not reproduced by the current listing export.
- Direct URL re-checks hit Radware bot-protection pages outside the normal trusted headed collection flow, so those misses cannot be safely auto-classified further in this task.
- A historical stale CGI job row may still exist in SQLite from an earlier run; the fresh trusted diagnostic is the source of truth for current verification.
