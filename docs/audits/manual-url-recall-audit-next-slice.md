# Manual URL Recall Audit

## Scope
- Companies audited: BMO, Manulife
- Manual filter used: Canada only
- City/province/remote filters: not applied
- Pages checked manually: first 10 pages per source

## Manual Expected URL Counts
| Company | Expected URLs |
| --- | ---: |
| BMO | 0 |
| Manulife | 2 |

## Summary
| Status | Count |
| --- | ---: |
| saved_by_mvp | 0 |
| extracted_and_relevant | 0 |
| extracted_but_rejected_by_scoring | 0 |
| outside_scope | 2 |
| missed_by_collection | 0 |
| blocked_or_not_tested | 0 |
| unknown | 0 |

## Per-Company Status Counts
- BMO: none
- Manulife: outside_scope=2

## Per-Company Analysis
### BMO
- Manual career page: https://jobs.bmo.com/ca/en/search-results
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| - | - | - | - | - | - | - | - |
### Manulife
- Manual career page: https://manulife.wd3.myworkdayjobs.com/en-US/MFCJH_Jobs?Location_Country=a30a87ed25634629aa6c3958aa2b91ea
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://manulife.wd3.myworkdayjobs.com/en-US/MFCJH_Jobs/job/Toronto-Ontario/Lead-Platform-Reliability-Engineer_JR26051632-1?Location_Country=a30a87ed25634629aa6c3958aa2b91ea | - | outside_scope | Lead Platform Reliability Engineer | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |
| https://manulife.wd3.myworkdayjobs.com/en-US/MFCJH_Jobs/job/Toronto-Ontario/Senior-Cloud-Architect---AI---Modernization_JR26051153-1?Location_Country=a30a87ed25634629aa6c3958aa2b91ea | - | outside_scope | Senior Cloud Architect – AI & Modernization | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |

## Scoring And Tier Analysis
- `core_target_fit` keeps the original Cloud/DevOps/Admin/Support target intact.
- `adjacent_customer_facing_technical_fit` captures targeted solutions, customer-engineering, technical consulting, and similar adjacent roles.
- `outside_scope` is used when a manual URL was collected but still does not match the current core or adjacent target definitions.

## Recommended Fixes
- Keep clearly outside-scope roles separate so recall tuning does not broaden generic software or sales roles.

## Remaining Limitations
- Saved-job comparison only reflects what already exists in SQLite; scored-candidate exports are still required to distinguish rejection from collection misses.
- IBM and other non-Workday search pages may still depend on site-specific public filters that are not uniformly exposed through one generic search control.
