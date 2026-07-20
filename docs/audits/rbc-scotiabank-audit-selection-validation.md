# Manual URL Recall Audit

## Scope
- Companies audited: RBC, Scotiabank
- Manual filter used: Canada only
- City/province/remote filters: not applied
- Pages checked manually: first 10 pages per source

## Manual Expected URL Counts
| Company | Expected URLs |
| --- | ---: |
| RBC | 31 |
| Scotiabank | 65 |

## Summary
| Status | Count |
| --- | ---: |
| saved_by_mvp | 8 |
| extracted_and_relevant | 48 |
| extracted_but_rejected_by_scoring | 37 |
| outside_scope | 1 |
| inactive_or_expired | 0 |
| active_but_not_in_current_listing | 0 |
| outside_current_listing_scope | 0 |
| manual_intervention_required | 0 |
| missed_by_collection | 2 |
| blocked_or_not_tested | 0 |
| unknown | 0 |

## Per-Company Status Counts
- RBC: saved_by_mvp=6, extracted_and_relevant=15, extracted_but_rejected_by_scoring=8, missed_by_collection=2
- Scotiabank: saved_by_mvp=2, extracted_and_relevant=33, extracted_but_rejected_by_scoring=29, outside_scope=1

## Per-Company Analysis
### RBC
- Manual career page: https://jobs.rbc.com/ca/en/search-results
- Filter used: Canada, sort by most recent
- Pages checked: first 75

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://jobs.rbc.com/ca/en/job/R-0000174753/Senior-Cloud-Engineer | - | saved_by_mvp | Senior Cloud Engineer | 42 | core_target_fit | title matches target role: Cloud Engineer; location signals: Toronto, Ontario, Canada | - |
| https://jobs.rbc.com/ca/en/job/R-0000160071/Digital-Platform-Engineering-Technical-Product-Owner | - | extracted_but_rejected_by_scoring | Digital Platform & Engineering Technical Product Owner | 12 | not_relevant | location signals: Toronto, Ontario, Canada | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.rbc.com/ca/en/job/R-0000160538/Senior-DevOps-Engineer | - | saved_by_mvp | Senior DevOps Engineer | 34 | core_target_fit | title matches target role: DevOps Engineer; title family match: DevOps Engineer; location signals: Canada | - |
| https://jobs.rbc.com/ca/en/job/R-0000179431/Senior-Manager-DevOps-Engineering | - | extracted_but_rejected_by_scoring | Senior Manager - DevOps Engineering | - | not_relevant | location signals: Toronto, Ontario, Canada | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.rbc.com/ca/en/job/R-0000179572/Senior-Site-Reliability-Engineer | - | saved_by_mvp | Senior Site Reliability Engineer | 42 | core_target_fit | title matches target role: Site Reliability Engineer; location signals: Toronto, Ontario, Canada | - |
| https://jobs.rbc.com/ca/en/job/R-0000177388/Application-Support-Engineer | - | extracted_and_relevant | Application Support Engineer | 24 | core_target_fit | matched skills: support; location signals: Toronto, Ontario, Canada; support/ops signals: support | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000176722/Senior-Site-Reliability-Engineer | - | saved_by_mvp | Senior Site Reliability Engineer | 42 | core_target_fit | title matches target role: Site Reliability Engineer; location signals: Mississauga, Ontario, Canada | - |
| https://jobs.rbc.com/ca/en/job/R-0000176580/Sr-IAM-Engineer-Vault-Specialist-CyberArk-Hashicorp-Global-Security | - | saved_by_mvp | Sr IAM Engineer - Vault Specialist (CyberArk, Hashicorp) (Global Security) | 16 | core_target_fit | matched skills: IAM; location signals: Toronto, Ontario, Canada | - |
| https://jobs.rbc.com/ca/en/job/R-0000179335/Senior-IAM-Systems-Support-Analyst-Global-security | - | saved_by_mvp | Senior IAM Systems Support Analyst (Global security) | 13 | core_target_fit | matched skills: IAM, support; location signals: Toronto, Ontario, Canada; support/ops signals: support | - |
| https://jobs.rbc.com/ca/en/job/R-0000179867/Staff-Data-platform-Engineer-GFT | - | extracted_and_relevant | Staff Data platform Engineer, GFT | 42 | core_target_fit | title matches target role: Platform Engineer; location signals: Toronto, Ontario, Canada | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000180099/IAM-Director-Customer-Identity-Access-Management-Controls-Global-Security | - | extracted_but_rejected_by_scoring | IAM Director - Customer Identity Access Management Controls (Global Security) | - | not_relevant | matched skills: IAM; location signals: Canada | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.rbc.com/ca/en/job/R-0000178766/Senior-DevOps-Engineer | - | extracted_and_relevant | Senior DevOps Engineer | 42 | core_target_fit | title matches target role: DevOps Engineer; location signals: Toronto, Ontario, Canada | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000178411/Solution-Architect | - | extracted_and_relevant | Solution Architect | 36 | adjacent_customer_facing_technical_fit | location signals: Toronto, Ontario, Canada; adjacent customer-facing technical fit: Solution Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.rbc.com/ca/en/job/R-0000171090/Lead-System-Administrator | - | extracted_and_relevant | Lead System Administrator | 20 | core_target_fit | location signals: Toronto, Ontario, Canada; support/ops signals: administrator | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000178414/GFT-Lead-Solutions-Architect | - | extracted_and_relevant | GFT - Lead Solutions Architect | 28 | adjacent_customer_facing_technical_fit | location signals: Canada; adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.rbc.com/ca/en/job/R-0000179708/AI-Analyst | - | extracted_but_rejected_by_scoring | AI Analyst | 12 | not_relevant | location signals: Toronto, Ontario, Canada | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.rbc.com/ca/en/job/R-0000165735/Lead-System-Engineer-Global-Security | - | extracted_but_rejected_by_scoring | Lead System Engineer (Global Security) | 12 | not_relevant | location signals: Toronto, Ontario, Canada | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.rbc.com/ca/en/job/R-0000178089/DevOps-Engineer-Workday-Integrations | - | extracted_and_relevant | DevOps Engineer - Workday Integrations | 57 | core_target_fit | title matches target role: DevOps Engineer; location signals: Toronto, Ontario, Canada | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000165577/DevOps-Data-Engineer | - | extracted_but_rejected_by_scoring | DevOps Data Engineer | 12 | not_relevant | location signals: Toronto, Ontario, Canada | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.rbc.com/ca/en/job/R-0000173122/Cloud-Security-Architect-Global-Security | - | extracted_but_rejected_by_scoring | Cloud Security Architect (Global Security) | 12 | not_relevant | location signals: Toronto, Ontario, Canada | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.rbc.com/ca/en/job/R-0000168166/Senior-IAM-Systems-Engineer-Global-Security | - | extracted_and_relevant | Senior IAM Systems Engineer (Global Security) | 1 | core_target_fit | matched skills: IAM; location signals: Toronto, Ontario, Canada | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000178346/AI-Quality-Engineer | - | missed_by_collection | - | - | not_relevant | - | - |
| https://jobs.rbc.com/ca/en/job/R-0000177144/Sr-Administrator | - | extracted_but_rejected_by_scoring | Sr. Administrator. | 12 | not_relevant | location signals: Toronto, Ontario, Canada | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.rbc.com/ca/en/job/R-0000164593/Application-Administrator | - | extracted_and_relevant | Application Administrator | 20 | core_target_fit | location signals: Toronto, Ontario, Canada; support/ops signals: administrator | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000175098/Lead-Solution-Architect | - | extracted_and_relevant | Lead Solution Architect | 36 | adjacent_customer_facing_technical_fit | location signals: Toronto, Ontario, Canada; adjacent customer-facing technical fit: Solution Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.rbc.com/ca/en/job/R-0000178580/Director-SRE-and-AI-Ops-GFT | - | missed_by_collection | - | - | not_relevant | - | - |
| https://jobs.rbc.com/ca/en/job/R-0000168932/Principal-ML-Ops-Engineer-Azure | - | extracted_and_relevant | Principal ML Ops Engineer, Azure | 1 | core_target_fit | matched skills: Azure; location signals: Toronto, Ontario, Canada | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000173020/Application-Support-Analyst-GFT-Halifax | - | extracted_and_relevant | Application Support Analyst, GFT - Halifax | 16 | core_target_fit | matched skills: support; location signals: Canada; support/ops signals: support | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000177942/Sr-Technical-Systems-Analyst-Database-Activity-Monitoring-GCS | - | extracted_and_relevant | Sr. Technical Systems Analyst – Database Activity Monitoring (GCS) | 16 | core_target_fit | matched skills: monitoring; location signals: Toronto, Ontario, Canada | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.rbc.com/ca/en/job/R-0000152065/Lead-Solution-Architect | - | extracted_and_relevant | Lead Solution Architect | 36 | adjacent_customer_facing_technical_fit | location signals: Mississauga, Ontario, Canada; adjacent customer-facing technical fit: Solution Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.rbc.com/ca/en/job/R-0000173104/Senior-Middleware-Technical-Support-Administrator | - | extracted_and_relevant | Senior Middleware Technical Support Administrator | 9 | core_target_fit | matched skills: support; location signals: Toronto, Ontario, Canada; support/ops signals: support, administrator | Saved as relevant because the job had a positive score and at least one core non-location signal. |
### Scotiabank
- Manual career page: https://jobs.scotiabank.com/search/?createNewAlert=false&q=&locationsearch=canada
- Filter used: Canada
- Pages checked: 53

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://jobs.scotiabank.com/job/Toronto-Data-Platform-Operations-Engineer-ON/602447917/ | - | extracted_and_relevant | Data Platform Operations Engineer | 12 | core_target_fit | location signals: Toronto; support/ops signals: operations | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Developer%2C-Platform-Engineering-ON/600736517/ | - | extracted_but_rejected_by_scoring | Developer, Platform Engineering | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Developer%2C-Platform-Engineering-ON/600736617/ | - | extracted_but_rejected_by_scoring | Senior Developer, Platform Engineering | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Infrastructure-Support-Analyst-ON-M1L4S2/602278317/ | - | extracted_and_relevant | Infrastructure Support Analyst | 16 | core_target_fit | matched skills: support; location signals: Toronto; support/ops signals: support | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Developer%2C-Cloud-Engineering-ON-M5H-1H1/603196017/ | - | extracted_but_rejected_by_scoring | Developer, Cloud Engineering | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Solutions-Architect-ON-M5H-1H1/602310417/ | - | extracted_and_relevant | Solutions Architect | 28 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.scotiabank.com/job/Toronto-Site-Reliability-Engineer-%28SRE%29-ON-M5V2T3/598813017/ | - | extracted_and_relevant | Site Reliability Engineer (SRE) | 49 | core_target_fit | title matches target role: Site Reliability Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Solutions-Architect-ON-M5H-1H1/602405917/ | - | extracted_and_relevant | Senior Solutions Architect | 13 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Database-Administrator-ON-M5V2T3/603306417/ | - | extracted_but_rejected_by_scoring | Senior Database Administrator | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Database-Administrator-ON-M5V2T3/603305917/ | - | extracted_but_rejected_by_scoring | Senior Database Administrator | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Quality-Engineer-ON-M5A3X5/602440717/ | - | extracted_but_rejected_by_scoring | Quality Engineer | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Cloud-Security-Engineer-ON-M5H-1H1/603386017/ | - | extracted_but_rejected_by_scoring | Senior Cloud Security Engineer | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Incident-Coordinator-ON-M1K5L1/601573717/ | - | extracted_but_rejected_by_scoring | Incident Coordinator | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Quality-Engineer-Associate-ON-M5A3X5/601637817/ | - | extracted_but_rejected_by_scoring | Quality Engineer Associate | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-DevOps-Engineer-ON-M5H-1H1/600857917/ | - | extracted_and_relevant | DevOps Engineer | 49 | core_target_fit | title matches target role: DevOps Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Platform-Engineer-PeopleSoft-ON-M5H-1H1/599205217/ | - | extracted_and_relevant | Platform Engineer - PeopleSoft | 49 | core_target_fit | title matches target role: Platform Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior-DevOps-Engineer-ON-M5H4A6/601192017/ | - | extracted_and_relevant | Senior DevOps Engineer | 34 | core_target_fit | title matches target role: DevOps Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Cloud-Engineer%2C-Infrastructure-as-Code-ON-M5H-1H1/601991717/ | - | extracted_and_relevant | Senior Cloud Engineer, Infrastructure as Code | 38 | core_target_fit | title matches target role: Cloud Engineer; matched skills: Terraform; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Cloud-Engineer%2C-Infrastructure-as-Code-ON-M5H-1H1/601992517/ | - | extracted_and_relevant | Senior Cloud Engineer, Infrastructure as Code | 38 | core_target_fit | title matches target role: Cloud Engineer; matched skills: Terraform; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Solutions-Architect-ON-M5H4A6/603340517/ | - | extracted_and_relevant | Senior Solutions Architect | 13 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.scotiabank.com/job/Toronto-Cloud-Engineer-ON-M5H-1H1/603165917/ | - | extracted_and_relevant | Cloud Engineer | 49 | core_target_fit | title matches target role: Cloud Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-ServiceNow-Administrator-Specialist-ON-M5H-1H1/602949717/ | - | extracted_but_rejected_by_scoring | ServiceNow Administrator Specialist | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Developer%2C-Cloud-Engineering-Contract-Full-Time-for-12-Months-ON-M5H-1H1/603792117/ | - | extracted_but_rejected_by_scoring | Developer, Cloud Engineering - Contract Full Time for 12 Months | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Staff-Cloud-Platform-Engineer-ON-M5H-1H1/603864217/ | - | extracted_and_relevant | Staff Cloud Platform Engineer | 34 | core_target_fit | title matches target role: Platform Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Cloud-Platform-Engineer-ON-M5H-1H1/604298717/ | - | extracted_and_relevant | Senior Cloud Platform Engineer | 34 | core_target_fit | title matches target role: Platform Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Network-Security-Administrator-ON-M2H0A1/601842617/ | - | extracted_and_relevant | Senior Network Security Administrator | 1 | core_target_fit | matched skills: networking; location signals: Toronto; support/ops signals: administrator | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Cloud-Security-Engineer-ON-M5H-1H1/604157417/ | - | extracted_but_rejected_by_scoring | Cloud Security Engineer | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Sr-Associate-Platform-Engineer-ON-M5H-1H1/604106817/ | - | extracted_and_relevant | Sr Associate Platform Engineer | 49 | core_target_fit | title matches target role: Platform Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Solutions-Architect-Wealth-Management-ON-M5H1B6/603544117/ | - | extracted_and_relevant | Solutions Architect - Wealth Management | 28 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.scotiabank.com/job/Toronto-Cloud-Engineer-ON-M5H1B6/603676317/ | - | extracted_and_relevant | Cloud Engineer | 49 | core_target_fit | title matches target role: Cloud Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Technical-Solution-Advisor-ON-M5V2T3/596536317/ | - | extracted_but_rejected_by_scoring | Technical Solution Advisor | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Cloud-Platform-Engineer-ON-M5H-1H1/603986717/ | - | extracted_and_relevant | Cloud Platform Engineer | 49 | core_target_fit | title matches target role: Platform Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-IAM-Architect%2CEnterprise-Security-Identity-Access-Management-ON-M1K5L1/602477617/ | - | extracted_and_relevant | IAM Architect,Enterprise Security - Identity Access Management | 8 | core_target_fit | matched skills: IAM; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Platform-Engineer-ON-M5H4A6/599985017/ | - | extracted_and_relevant | Senior Platform Engineer | 34 | core_target_fit | title matches target role: Platform Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Manager%2C-Cloud-Security-Engineering-ON-M5H-1H1/604346717/ | - | extracted_but_rejected_by_scoring | Senior Manager, Cloud Security Engineering | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Scarborough-Solution-Engineer-ON-M1L4S2/604176817/ | - | saved_by_mvp | Solution Engineer | 60 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Solution Engineer (high-signal title); adjacent customer-facing technical fit: Solution Engineer | - |
| https://jobs.scotiabank.com/job/Toronto-Solutions-Architect-ON-M1L4S2/604279217/ | - | extracted_and_relevant | Solutions Architect | 28 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Platform-Engineer-ON-M5H4A6/599558117/ | - | extracted_and_relevant | Senior Platform Engineer | 34 | core_target_fit | title matches target role: Platform Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Senior%2C-Cloud-Engineering-ON-M5H-1H1/602560417/ | - | extracted_but_rejected_by_scoring | Senior, Cloud Engineering | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Integration-Engineer-ON-M5H1H1/604418917/ | - | extracted_but_rejected_by_scoring | Integration Engineer | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-IAM-Architect-ON-M1K5L1/602252917/ | - | extracted_and_relevant | IAM Architect | 8 | core_target_fit | matched skills: IAM; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-System-Reliability-Engineer-ON-M5A3X5/603613217/ | - | extracted_but_rejected_by_scoring | System Reliability Engineer | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Software-Engineer%2C-%28Cloud-CICD-Platforms%29-ON-M5H-1H1/602664117/ | - | extracted_and_relevant | Software Engineer, (Cloud CICD Platforms) | 8 | core_target_fit | matched skills: CI/CD; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Director%2C-Cloud-Governance-&-Controls-Engineering-ON-M5H4A6/602677717/ | - | extracted_but_rejected_by_scoring | Director, Cloud Governance & Controls Engineering | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Staff-Software-Engineer-%28Cloud-CICD-Platforms%29-ON-M5H-1H1/602658317/ | - | extracted_but_rejected_by_scoring | Staff Software Engineer (Cloud CICD Platforms) | - | not_relevant | matched skills: CI/CD; location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Director-&-Head%2C-Cloud-Modernization-&-Migrations-ON-M5H4A6/602677017/ | - | extracted_but_rejected_by_scoring | Director & Head, Cloud Modernization & Migrations | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Quality-Engineer-ON-M5V2T3/601762517/ | - | extracted_but_rejected_by_scoring | Quality Engineer | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Cloud-Security-Architect-Cloud-&-Platform-Engineering-ON-M5H-1H1/602655317/ | - | extracted_but_rejected_by_scoring | Cloud Security Architect-Cloud & Platform Engineering | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Scarborough-Manager%2C-DevOps-and-Release-Management-ON-M1L4S2/603130417/ | - | outside_scope | Manager, DevOps and Release Management | - | not_relevant | - | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Director-of-Infrastructure-Solution-Architecture-ON-M5H3Y2/603814017/ | - | extracted_but_rejected_by_scoring | Director of Infrastructure Solution Architecture | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Private-Cloud-Engineer-ON-M1L4S2/602836217/ | - | extracted_and_relevant | Private Cloud Engineer | 49 | core_target_fit | title matches target role: Cloud Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-IAM-Product-Manager-ON-M1K5L1/603983717/ | - | extracted_but_rejected_by_scoring | IAM Product Manager | - | not_relevant | matched skills: IAM; location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Staff%2C-Cloud-Engineering-ON-M5H-1H1/601200717/ | - | extracted_but_rejected_by_scoring | Staff, Cloud Engineering | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Solutions-Architect-%28Capital-Markets-Technology%29-ON-M5H-1H1/601291517/ | - | extracted_and_relevant | Senior Solutions Architect (Capital Markets Technology) | 13 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Platform-Engineering-ON-M5H-1H1/601011617/ | - | extracted_but_rejected_by_scoring | Senior Platform Engineering | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Cloud-Security-Engineer-ON-M5H-1H1/600933117/ | - | extracted_but_rejected_by_scoring | Cloud Security Engineer | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Senior-Solution-Architect-ON-M5A3X5/600955617/ | - | extracted_and_relevant | Senior Solution Architect | 13 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solution Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.scotiabank.com/job/Toronto-Solutions-Architect-ON-M5H-1H1/600957817/ | - | extracted_and_relevant | Solutions Architect | 28 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.scotiabank.com/job/Toronto-Business-Quality-Analyst-%2812-month-contract-role%29-ON-M1K5L1/600316917/ | - | extracted_but_rejected_by_scoring | Business Quality Analyst (12 month contract role) | 4 | not_relevant | location signals: Toronto | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://jobs.scotiabank.com/job/Toronto-Solutions-Architect-Personalization-ON-M5A3X5/602129017/ | - | extracted_and_relevant | Solutions Architect - Personalization | 28 | adjacent_customer_facing_technical_fit | location signals: Toronto; adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.scotiabank.com/job/Toronto-Infrastructure-Support-Analyst-ON-M1K5L1/603698517/ | - | extracted_and_relevant | Infrastructure Support Analyst | 16 | core_target_fit | matched skills: support; location signals: Toronto; support/ops signals: support | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Toronto-Infrastructure-Support-Analyst-ON-M1L4S2/603664617/ | - | extracted_and_relevant | Infrastructure Support Analyst | 16 | core_target_fit | matched skills: support; location signals: Toronto; support/ops signals: support | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/Tangerine/job/Toronto-Senior-Oracle-Database-Administrator-ON-M2H0A1/602756817/ | - | extracted_but_rejected_by_scoring | Senior Oracle Database Administrator | - | not_relevant | location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.scotiabank.com/job/Toronto-Private-Cloud-Engineer-ON-M1L4S2/602836217/ | - | extracted_and_relevant | Private Cloud Engineer | 49 | core_target_fit | title matches target role: Cloud Engineer; location signals: Toronto | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://jobs.scotiabank.com/job/Scarborough-Solution-Engineer-ON-M1L4S2/604176817/ | - | saved_by_mvp | Solution Engineer | 60 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Solution Engineer (high-signal title); adjacent customer-facing technical fit: Solution Engineer | - |

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

## RBC And Scotiabank Closeout

### Historical Collection Recall

- Expected URLs: 96
- Collected or saved in stored audit evidence: 94
- Historical collection recall: 97.9 percent
- Historical relevant-selection recall: 56 of 96 selected as relevant in stored audit
  evidence; 37 additional collected roles were deliberately rejected by deterministic
  scoring because they were senior, managerial, generic, or outside the target profile.

### Current-Live Interpretation

The two RBC rows labelled `missed_by_collection` are not active reproducible misses in
the current production run:

- `AI Quality Engineer` was reviewed during the RBC 75-page closeout and recorded as
  an active adjacent role outside the audited current listing.
- `Director SRE and AI Ops` was reviewed during the same closeout and recorded as an
  executive-level role outside the target seniority scope and outside the audited
  current listing.

Both classifications are supported by [RBC re-audit evidence](RBC-reaudit-report.md)
and the manual URL closeout. No additional 75-page rerun was warranted. The current
post-calibration live run has no active in-scope manual collection miss for either RBC
or Scotiabank.

### Selection Outcome

- `Solution Engineer` now scores 60 and remains an adjacent technical fit.
- The finance networking event is now correctly rejected as a false positive.
- The executive Global Head IAM role is now correctly rejected after an executive-title
  penalty, while ordinary senior technical roles remain eligible with a risk flag.
