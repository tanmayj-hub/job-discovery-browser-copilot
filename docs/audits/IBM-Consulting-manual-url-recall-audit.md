# Manual URL Recall Audit

## Scope
- Companies audited: IBM Consulting
- Manual filter used: Canada only
- City/province/remote filters: not applied
- Pages checked manually: first 10 pages per source

## Manual Expected URL Counts
| Company | Expected URLs |
| --- | ---: |
| IBM Consulting | 12 |

## Summary
| Status | Count |
| --- | ---: |
| saved_by_mvp | 7 |
| extracted_and_relevant | 0 |
| extracted_but_rejected_by_scoring | 2 |
| outside_scope | 3 |
| missed_by_collection | 0 |
| blocked_or_not_tested | 0 |
| unknown | 0 |

## Per-Company Status Counts
- IBM Consulting: saved_by_mvp=7, extracted_but_rejected_by_scoring=2, outside_scope=3

## Per-Company Analysis
### IBM Consulting
- Manual career page: https://www.ibm.com/careers/search?field_keyword_05[0]=Canada
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=113691&source=WEB_Search_NA | - | saved_by_mvp | Sales Customer Success Engineer - Automation - Application Development Professional Multiple Cities | 24 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Customer Success Engineer | - |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=92913&source=WEB_Search_NA | - | saved_by_mvp | Consulting Microsoft Dynamics 365 CE Technical Solution Architect Professional Multiple Cities | 24 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Solution Architect | - |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=99986&source=WEB_Search_NA | - | saved_by_mvp | Infrastructure & Technology Administrateur Infrastructure TI Professional BROMONT, CA | 8 | core_target_fit | support/ops signals: admin | - |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=115304&source=WEB_Search_NA | - | outside_scope | Sales Brand Sales Specialist- Infrastructure Professional Multiple Cities | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=109197&source=WEB_Search_NA | - | saved_by_mvp | Consulting Delivery Consultant - IBM Z DevOps Professional Markham, CA | 28 | adjacent_customer_facing_technical_fit | location signals: Markham; adjacent customer-facing technical fit: Delivery Consultant | - |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=87530&source=WEB_Search_NA | - | saved_by_mvp | Infrastructure & Technology Solution Architect Professional Toronto, CA | 28 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solution Architect | - |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=111494&source=WEB_Search_NA | - | extracted_but_rejected_by_scoring | Consulting Customer Experience Consulting Intern (Sept 2026 - 4 Months - Toronto) Internship Toronto, CA | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=115116&source=WEB_Search_NA | - | saved_by_mvp | Infrastructure & Technology Staff Site Reliability Engineer - Confluent Incident Management & Reliability Professional Multiple Cities | 38 | core_target_fit | title matches target role: Site Reliability Engineer; support/ops signals: incident | - |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=107046&source=WEB_Search_NA | - | outside_scope | Sales Technology Sales Specialist - Infrastructure Professional Multiple Cities | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=118746&source=WEB_Search_NA | - | saved_by_mvp | Sales Solutions Engineer - Hashicorp Professional Multiple Cities | 24 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Solutions Engineer | - |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=119355&source=WEB_Search_NA | - | outside_scope | Sales Technology Sales Specialist - Consulting/SI Partner Professional Multiple Cities | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=109784&source=WEB_Search_NA | - | extracted_but_rejected_by_scoring | Sales Brand Technical Sales Specialist – Power & Cloud Professional Toronto, CA | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |

## Scoring And Tier Analysis
- `core_target_fit` keeps the original Cloud/DevOps/Admin/Support target intact.
- `adjacent_customer_facing_technical_fit` captures targeted solutions, customer-engineering, technical consulting, and similar adjacent roles.
- `outside_scope` is used when a manual URL was collected but still does not match the current core or adjacent target definitions.

## Recommended Fixes
- Review rejected-but-extracted rows next to confirm whether scoring should promote them.
- Keep clearly outside-scope roles separate so recall tuning does not broaden generic software or sales roles.
- Preserve the current core-target scoring path for rows already saved cleanly by the MVP.

## Remaining Limitations
- Saved-job comparison only reflects what already exists in SQLite; scored-candidate exports are still required to distinguish rejection from collection misses.
- IBM and other non-Workday search pages may still depend on site-specific public filters that are not uniformly exposed through one generic search control.
