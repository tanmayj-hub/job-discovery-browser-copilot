# Manual URL Recall Audit

## Scope
- Companies audited: TD, IBM Consulting, Sun Life
- Manual filter used: Canada only
- City/province/remote filters: not applied
- Pages checked manually: first 10 pages per source

## Manual Expected URL Counts
| Company | Expected URLs |
| --- | ---: |
| TD | 4 |
| IBM Consulting | 12 |
| Sun Life | 3 |

## Summary
| Status | Count |
| --- | ---: |
| blocked_or_not_tested | 0 |
| extracted_and_relevant | 9 |
| extracted_but_rejected_by_scoring | 3 |
| missed_by_collection | 2 |
| outside_scope | 3 |
| saved_by_mvp | 2 |
| unknown | 0 |

## Per-Company Status Counts
- TD: extracted_and_relevant=1, missed_by_collection=1, saved_by_mvp=2
- IBM Consulting: extracted_and_relevant=7, extracted_but_rejected_by_scoring=3, missed_by_collection=1, outside_scope=1
- Sun Life: extracted_and_relevant=1, outside_scope=2

## Per-Company Analysis
### TD
- Manual career page: https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Lead-Platform-Engineer--TD-Securities_R_1491997?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | Lead Platform Engineer, TD Securities | saved_by_mvp | Lead Platform Engineer, TD Securities | 53 | core_target_fit | title matches target role: Platform Engineer | - |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Sr-IT-Support-Analyst---ION--MarketView--Trading_R_1489301?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | Sr IT Support Analyst, ION / MarketView Trading | saved_by_mvp | Sr. IT Support Analyst - ION, MarketView, Trading | 20 | core_target_fit | matched skills: support; support/ops signals: support | - |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/IT-Build-Analyst-II---Onsite-AV-Support_R_1493452?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | IT Build Analyst II - Onsite AV Support | extracted_and_relevant | IT Build Analyst II - Onsite AV Support | 12 | core_target_fit | matched skills: support; support/ops signals: support | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Software-Engineer-II--Salesforce_R_1486443?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | Software Engineer II, Salesforce | missed_by_collection | - | - | not_relevant | - | - |
### IBM Consulting
- Manual career page: https://www.ibm.com/careers/search
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=92913&source=WEB_Search_NA | - | extracted_and_relevant | Consulting Microsoft Dynamics 365 CE Technical Solution Architect Professional Multiple Cities | 24 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Solution Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=113691&source=WEB_Search_NA | - | extracted_and_relevant | Sales Customer Success Engineer - Automation - Application Development Professional Multiple Cities | 24 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Customer Success Engineer | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=99986&source=WEB_Search_NA | - | extracted_and_relevant | Infrastructure & Technology Administrateur Infrastructure TI Professional BROMONT, CA | 8 | core_target_fit | support/ops signals: admin | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=116909&source=WEB_Search_NA | - | extracted_and_relevant | Sales Customer Success Engineer Professional Montreal, CA | 24 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Customer Success Engineer | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=109197&source=WEB_Search_NA | - | extracted_and_relevant | Consulting Delivery Consultant - IBM Z DevOps Professional Markham, CA | 28 | adjacent_customer_facing_technical_fit | location signals: Markham; adjacent customer-facing technical fit: Delivery Consultant | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=111494&source=WEB_Search_NA | - | extracted_but_rejected_by_scoring | Consulting Customer Experience Consulting Intern (Sept 2026 - 4 Months - Toronto) Internship Toronto, CA | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=111872&source=WEB_Search_NA | - | extracted_but_rejected_by_scoring | Consulting Salesforce Consulting & GTM Intern (Sept 2026 - 4 Months - Toronto) Internship Toronto, CA | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=87530&source=WEB_Search_NA | - | extracted_and_relevant | Infrastructure & Technology Solution Architect Professional Toronto, CA | 28 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solution Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=115116&source=WEB_Search_NA | - | missed_by_collection | - | - | not_relevant | - | - |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=118746&source=WEB_Search_NA | - | extracted_and_relevant | Sales Solutions Engineer - Hashicorp Professional Multiple Cities | 24 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Solutions Engineer | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=119355&source=WEB_Search_NA | - | outside_scope | Sales Technology Sales Specialist - Consulting/SI Partner Professional Multiple Cities | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |
| https://careers.ibm.com/en_US/careers/JobDetail?jobId=109784&source=WEB_Search_NA | - | extracted_but_rejected_by_scoring | Sales Brand Technical Sales Specialist – Power & Cloud Professional Toronto, CA | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
### Sun Life
- Manual career page: https://sunlife.wd3.myworkdayjobs.com/Experienced-Jobs?Location_Country=a30a87ed25634629aa6c3958aa2b91ea
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://sunlife.wd3.myworkdayjobs.com/en-US/Experienced-Jobs/job/Waterloo-Ontario/M365-Productivity---Collaboration-Engineer_JR00124191?Location_Country=a30a87ed25634629aa6c3958aa2b91ea | M365 Productivity & Collaboration Engineer | outside_scope | M365 Productivity & Collaboration Engineer | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |
| https://sunlife.wd3.myworkdayjobs.com/en-US/Experienced-Jobs/job/Waterloo-Ontario/Container-Service-Delivery-Co-Ordinator--OpenShift---Kubernetes--_JR00123895-1?Location_Country=a30a87ed25634629aa6c3958aa2b91ea | Container Service Delivery Co-Ordinator (OpenShift / Kubernetes) | extracted_and_relevant | Container Service Delivery Co-Ordinator (OpenShift / Kubernetes) | 4 | core_target_fit | matched skills: Kubernetes | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://sunlife.wd3.myworkdayjobs.com/en-US/Experienced-Jobs/job/Toronto-Ontario/Future-Opportunities_JR00106798?Location_Country=a30a87ed25634629aa6c3958aa2b91ea | Future Opportunities | outside_scope | Future Opportunities | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |

## Scoring And Tier Analysis
- `core_target_fit` keeps the original Cloud/DevOps/Admin/Support target intact.
- `adjacent_customer_facing_technical_fit` captures targeted solutions, customer-engineering, technical consulting, and similar adjacent roles.
- `outside_scope` is used when a manual URL was collected but still does not match the current core or adjacent target definitions.

## Recommended Fixes
- Prioritize collection gaps first where the manual URL never appeared in scored candidates.
- Review rejected-but-extracted rows next to confirm whether scoring should promote them.
- Keep clearly outside-scope roles separate so recall tuning does not broaden generic software or sales roles.
- Preserve the current core-target scoring path for rows already saved cleanly by the MVP.

## Remaining Limitations
- Saved-job comparison only reflects what already exists in SQLite; scored-candidate exports are still required to distinguish rejection from collection misses.
- IBM and other non-Workday search pages may still depend on site-specific public filters that are not uniformly exposed through one generic search control.
