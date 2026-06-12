# Manual URL Recall Audit

## Scope
- Companies audited: Sun Life
- Manual filter used: Canada only
- City/province/remote filters: not applied
- Pages checked manually: first 10 pages per source

## Manual Expected URL Counts
| Company | Expected URLs |
| --- | ---: |
| Sun Life | 2 |

## Summary
| Status | Count |
| --- | ---: |
| saved_by_mvp | 1 |
| extracted_and_relevant | 0 |
| extracted_but_rejected_by_scoring | 0 |
| outside_scope | 1 |
| missed_by_collection | 0 |
| blocked_or_not_tested | 0 |
| unknown | 0 |

## Per-Company Status Counts
- Sun Life: saved_by_mvp=1, outside_scope=1

## Per-Company Analysis
### Sun Life
- Manual career page: https://sunlife.wd3.myworkdayjobs.com/Experienced-Jobs?Location_Country=a30a87ed25634629aa6c3958aa2b91ea
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://sunlife.wd3.myworkdayjobs.com/en-US/Experienced-Jobs/job/Waterloo-Ontario/M365-Productivity---Collaboration-Engineer_JR00124191?Location_Country=a30a87ed25634629aa6c3958aa2b91ea | - | outside_scope | M365 Productivity & Collaboration Engineer | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |
| https://sunlife.wd3.myworkdayjobs.com/en-US/Experienced-Jobs/job/Waterloo-Ontario/Container-Service-Delivery-Co-Ordinator--OpenShift---Kubernetes--_JR00123895-1?Location_Country=a30a87ed25634629aa6c3958aa2b91ea | - | saved_by_mvp | Container Service Delivery Co-Ordinator (OpenShift / Kubernetes) | 4 | core_target_fit | matched skills: Kubernetes | - |

## Scoring And Tier Analysis
- `core_target_fit` keeps the original Cloud/DevOps/Admin/Support target intact.
- `adjacent_customer_facing_technical_fit` captures targeted solutions, customer-engineering, technical consulting, and similar adjacent roles.
- `outside_scope` is used when a manual URL was collected but still does not match the current core or adjacent target definitions.

## Recommended Fixes
- Keep clearly outside-scope roles separate so recall tuning does not broaden generic software or sales roles.
- Preserve the current core-target scoring path for rows already saved cleanly by the MVP.

## Remaining Limitations
- Saved-job comparison only reflects what already exists in SQLite; scored-candidate exports are still required to distinguish rejection from collection misses.
- IBM and other non-Workday search pages may still depend on site-specific public filters that are not uniformly exposed through one generic search control.
