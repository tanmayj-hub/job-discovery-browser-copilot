# TD Fix Report

## Current Source Status
- TD uses the direct official Canada-filtered Workday jobs URL:
  `https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=a30a87ed25634629aa6c3958aa2b91ea`

## Fresh Results
- Trusted run: `182` discovered, `182` scored, `9` relevant, `9` saved.
- Diagnostic run: `182` discovered, `9` relevant, `10` pages visited, stop reason `max_pages_reached`.
- Source scope status: `canada_scope_confirmed`
- Manual recall status for the current bank slice: `3 / 3` saved by MVP.

## Verification Decision
- Decision: `verified usable`

## Why TD Was Promoted
- Canada scope is confirmed before pagination by the Workday URL filter.
- The trusted run completed cleanly with discovered and saved jobs.
- The current manual bank-slice audit is clean.
- No unresolved source blocker prevented daily use in the current slice.

## Remaining Note
- TD still stops at the current safe `10`-page cap.
- The unusual page ordering / recency behavior is still worth documenting later, but it is not blocking current verified use.
