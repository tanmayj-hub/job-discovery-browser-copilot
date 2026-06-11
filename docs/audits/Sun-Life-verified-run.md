# Sun Life Verified Run

## Fresh Run
- Run date: 2026-06-10
- Latest source timestamp: 2026-06-11 03:37:37 UTC
- Configured source URL: https://sunlife.wd3.myworkdayjobs.com/Experienced-Jobs?Location_Country=a30a87ed25634629aa6c3958aa2b91ea
- Source mode: human_in_loop
- ATS type: workday
- Collector used: browser
- Final URL reached: https://sunlife.wd3.myworkdayjobs.com/Experienced-Jobs?Location_Country=a30a87ed25634629aa6c3958aa2b91ea
- Pages visited in focused diagnostic: 7
- Pagination stop reason: next_disabled_or_missing

## Latest Production Daily-Run Result
- Status: completed
- Jobs discovered: 122
- Jobs scored: 122
- Relevant jobs saved: 3
- Jobs inserted: 0
- Jobs updated: 0
- Jobs unchanged: 3
- Duplicates skipped: 0
- Suspicious saved rows: 0
- Pending intervention: none
- Error: none
- Canada-only scope confirmed in fresh run: yes

## Manual Audit Context
- Official careers page only: yes
- Canada-only manual audit: yes
- First-10-page manual audit summary: no remaining collection misses in the current audited slice
- Manual URL recall summary status: usable for the current MVP target scope
- Known scope note: some extracted roles remain outside the current scoring scope, which is acceptable for verified MVP use

## Verification Decision
- Verified: yes
- Status: usable
- Reason:
  fresh `daily-run --company "Sun Life"` completed cleanly, used a stable Canada-filtered official Workday URL, discovered jobs, saved relevant jobs, showed no suspicious saved rows, had no unresolved blocking intervention, and the latest manual URL audit did not show active collection misses.
