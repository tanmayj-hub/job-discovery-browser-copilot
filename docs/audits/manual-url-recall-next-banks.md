# Manual URL Recall Audit

## Scope
- Companies audited: RBC, TD, Scotiabank
- Manual filter used: Canada only
- City/province/remote filters: not applied
- Pages checked manually: first 10 pages per source

## Manual Expected URL Counts
| Company | Expected URLs |
| --- | ---: |
| RBC | 4 |
| TD | 3 |
| Scotiabank | 5 |

## Summary
| Status | Count |
| --- | ---: |
| saved_by_mvp | 3 |
| extracted_and_relevant | 1 |
| extracted_but_rejected_by_scoring | 0 |
| outside_scope | 0 |
| inactive_or_expired | 0 |
| active_but_not_in_current_listing | 0 |
| outside_current_listing_scope | 0 |
| manual_intervention_required | 0 |
| missed_by_collection | 8 |
| blocked_or_not_tested | 0 |
| unknown | 0 |

## Per-Company Status Counts
- RBC: missed_by_collection=4
- TD: saved_by_mvp=3
- Scotiabank: extracted_and_relevant=1, missed_by_collection=4

## Per-Company Analysis
### RBC
- Manual career page: https://jobs.rbc.com/ca/en/search-results?from=140&s=1
- Filter used: Canada, sort by most recent, sub category= technology, project and program management, operations and business management.
- Pages checked: first 15

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://jobs.rbc.com/ca/en/job/R-0000176580/Sr-IAM-Engineer-Vault-Specialist-CyberArk-Hashicorp-Global-Security | - | missed_by_collection | - | - | not_relevant | - | - |
| https://jobs.rbc.com/ca/en/job/R-0000174330/Staff-Cloud-Security-Engineer-Global-Security | - | missed_by_collection | - | - | not_relevant | - | - |
| https://jobs.rbc.com/ca/en/job/R-0000174266/DevOps-Platform-Solution-Engineer | - | missed_by_collection | - | - | not_relevant | - | - |
| https://jobs.rbc.com/ca/en/job/R-0000160538/Senior-DevOps-Engineer | - | missed_by_collection | - | - | not_relevant | - | - |
### TD
- Manual career page: https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers?locationCountry=a30a87ed25634629aa6c3958aa2b91ea
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Lead-Platform-Engineer--TD-Securities_R_1491997?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | - | saved_by_mvp | Lead Platform Engineer, TD Securities | 45 | core_target_fit | title matches target role: Platform Engineer | - |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/IT-Support-Analyst-III_R_1485356?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | - | saved_by_mvp | IT Support Analyst III | 12 | core_target_fit | matched skills: support; support/ops signals: support | - |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Cloud-IAM-Engineer-II_R_1484934-1?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | - | saved_by_mvp | Cloud IAM Engineer II | 4 | core_target_fit | matched skills: IAM | - |
### Scotiabank
- Manual career page: https://jobs.scotiabank.com/search/?createNewAlert=false&q=&locationsearch=canada
- Filter used: Canada
- Pages checked: first 15

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://jobs.scotiabank.com/job/Toronto-Developer%2C-Platform-Engineering-ON/600736517/ | - | extracted_and_relevant | Developer, Platform Engineering | 49 | core_target_fit | title matches target role: Platform Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Private-Cloud-Engineer-ON-M1L4S2/602836217/ | - | missed_by_collection | - | - | not_relevant | - | - |
| https://jobs.scotiabank.com/job/Toronto-Staff-Software-Engineer-%28Cloud-CICD-Platforms%29-ON-M5H-1H1/602658317/ | - | missed_by_collection | - | - | not_relevant | - | - |
| https://jobs.scotiabank.com/job/Toronto-Software-Engineer%2C-%28Cloud-CICD-Platforms%29-ON-M5H-1H1/602664117/ | - | missed_by_collection | - | - | not_relevant | - | - |
| https://jobs.scotiabank.com/job/Toronto-Senior-DevOps-Engineer-ON-M5H4A6/601192017/ | - | missed_by_collection | - | - | not_relevant | - | - |

## Scoring And Tier Analysis
- `core_target_fit` keeps the original Cloud/DevOps/Admin/Support target intact.
- `adjacent_customer_facing_technical_fit` captures targeted solutions, customer-engineering, technical consulting, and similar adjacent roles.
- `outside_scope` is used when a manual URL was collected but still does not match the current core or adjacent target definitions.

## Recommended Fixes
- Prioritize collection gaps first where the manual URL never appeared in scored candidates.
- Preserve the current core-target scoring path for rows already saved cleanly by the MVP.

## Remaining Limitations
- Saved-job comparison only reflects what already exists in SQLite; scored-candidate exports are still required to distinguish rejection from collection misses.
- IBM and other non-Workday search pages may still depend on site-specific public filters that are not uniformly exposed through one generic search control.
