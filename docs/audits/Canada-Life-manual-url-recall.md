# Manual URL Recall Audit

## Scope
- Companies audited: Canada Life
- Manual filter used: Canada only
- City/province/remote filters: not applied
- Pages checked manually: first 10 pages per source

## Manual Expected URL Counts
| Company | Expected URLs |
| --- | ---: |
| Canada Life | 4 |

## Summary
| Status | Count |
| --- | ---: |
| saved_by_mvp | 1 |
| extracted_and_relevant | 0 |
| extracted_but_rejected_by_scoring | 1 |
| outside_scope | 0 |
| missed_by_collection | 2 |
| blocked_or_not_tested | 0 |
| unknown | 0 |

## Per-Company Status Counts
- Canada Life: saved_by_mvp=1, extracted_but_rejected_by_scoring=1, missed_by_collection=2

## Per-Company Analysis
### Canada Life
- Manual career page: https://jobs.canadalife.com/search/?createNewAlert=false&q=&locationsearch=&optionsFacetsDD_location=&optionsFacetsDD_country=CA&optionsFacetsDD_department=
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://jobs.canadalife.com/job/London-Solutions-Architect-ON/1404013933/ | - | saved_by_mvp | London, ON, CA +2 more… | 12 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Solutions Architect | - |
| https://jobs.canadalife.com/job/Toronto-Senior-Network-Engineering-Specialist-Lead-%28Cloud-and-On-premise%29-ON/1381006633/ | - | extracted_but_rejected_by_scoring | Toronto, ON, CA +2 more… | - | not_relevant | matched skills: networking; location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.canadalife.com/job/London-Senior-Devops-Engineering-Specialist-ON/1400494133/ | - | missed_by_collection | - | - | not_relevant | - | - |
| https://jobs.canadalife.com/job/Toronto-Senior-Network-Engineering-Specialist-%28Cloud-and-On-premise%29-ON/1381005333/ | - | missed_by_collection | - | - | not_relevant | - | - |

## Scoring And Tier Analysis
- `core_target_fit` keeps the original Cloud/DevOps/Admin/Support target intact.
- `adjacent_customer_facing_technical_fit` captures targeted solutions, customer-engineering, technical consulting, and similar adjacent roles.
- `outside_scope` is used when a manual URL was collected but still does not match the current core or adjacent target definitions.

## Recommended Fixes
- Prioritize collection gaps first where the manual URL never appeared in scored candidates.
- Review rejected-but-extracted rows next to confirm whether scoring should promote them.
- Preserve the current core-target scoring path for rows already saved cleanly by the MVP.

## Remaining Limitations
- Saved-job comparison only reflects what already exists in SQLite; scored-candidate exports are still required to distinguish rejection from collection misses.
- IBM and other non-Workday search pages may still depend on site-specific public filters that are not uniformly exposed through one generic search control.
