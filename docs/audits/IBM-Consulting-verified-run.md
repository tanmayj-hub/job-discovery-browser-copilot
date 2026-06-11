# IBM Consulting Verified Run

## Fresh Run
- Run date: 2026-06-10
- Latest source timestamp: 2026-06-11 03:37:46 UTC
- Configured source URL: https://www.ibm.com/careers/search
- Source mode: browser_allowed
- ATS type: -
- Collector used: browser_after_jsonld
- Final Canada-scoped URL: https://www.ibm.com/careers/search?field_keyword_05[0]=Canada
- Pages visited in focused diagnostic: 4
- Pagination stop reason: next_disabled_or_missing

## Latest Production Daily-Run Result
- Status: completed
- Jobs discovered: 103
- Jobs scored: 103
- Relevant jobs saved: 18
- Jobs inserted: 0
- Jobs updated: 2
- Jobs unchanged: 16
- Duplicates skipped: 0
- Suspicious saved rows: 0
- Pending intervention: none
- Error: none
- Canada-only scope confirmed in fresh run: yes

## Manual Audit Context
- Official careers page only: yes
- Canada-only manual audit: yes
- First-10-page manual audit summary: no remaining collection misses in the current audited slice
- Manual URL recall summary status: strong enough for MVP use

## Verification Decision
- Verified: yes
- Status: usable
- Reason:
  fresh `daily-run --company "IBM Consulting"` completed cleanly, discovered jobs, saved relevant jobs, showed no suspicious saved rows, had no unresolved blocking intervention, and the latest manual URL audit did not show active collection misses.
