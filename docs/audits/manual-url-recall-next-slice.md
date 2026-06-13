# Manual URL Recall Audit

## Scope
- Companies audited: CGI, Canada Life, NTT Data, National Bank of Canada
- Manual filter used: Canada only
- City/province/remote filters: not applied
- Pages checked manually: first 10 pages per source

## Manual Expected URL Counts
| Company | Expected URLs |
| --- | ---: |
| CGI | 18 |
| Canada Life | 4 |
| NTT Data | 4 |
| National Bank of Canada | 2 |

## Summary
| Status | Count |
| --- | ---: |
| saved_by_mvp | 7 |
| extracted_and_relevant | 5 |
| extracted_but_rejected_by_scoring | 3 |
| outside_scope | 0 |
| inactive_or_expired | 0 |
| active_but_not_in_current_listing | 0 |
| outside_current_listing_scope | 0 |
| manual_intervention_required | 0 |
| missed_by_collection | 13 |
| blocked_or_not_tested | 0 |
| unknown | 0 |

## Per-Company Status Counts
- CGI: saved_by_mvp=5, extracted_but_rejected_by_scoring=1, missed_by_collection=12
- Canada Life: saved_by_mvp=1, extracted_and_relevant=1, extracted_but_rejected_by_scoring=2
- NTT Data: extracted_and_relevant=4
- National Bank of Canada: saved_by_mvp=1, missed_by_collection=1

## Per-Company Analysis
### CGI
- Manual career page: https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=joblisting
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0626-0210&BRID=1305099&lang=1 | - | extracted_but_rejected_by_scoring | Analyste / Conseiller DevSecOps – Spécialiste Snyk | 4 | not_relevant | location signals: Canada | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0626-1106&BRID=1308343&lang=1 | - | saved_by_mvp | Azure DevOps / Cloud Infrastructure Engineer (Azure) | 4 | core_target_fit | matched skills: Azure | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0426-1288&BRID=1291363&lang=1 | - | saved_by_mvp | Control-M System Administrator | 16 | core_target_fit | location signals: Toronto, Canada; support/ops signals: administrator, admin | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0426-2021&BRID=1293937&lang=1 | - | saved_by_mvp | Cloud/DevOps Administrator | 16 | core_target_fit | location signals: Toronto, Canada; support/ops signals: administrator, admin | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0626-0759&BRID=1307869&lang=1 | - | saved_by_mvp | Architecte de solution Infrastructure Cloud AWS | 8 | core_target_fit | matched skills: AWS; location signals: Canada | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0526-0817&BRID=1298993&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0526-2544&BRID=1304144&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0426-0390&BRID=1289578&lang=1 | - | saved_by_mvp | GCP Cloud Architect/ Platform Consultant | 12 | core_target_fit | matched skills: GCP; location signals: Toronto, Canada | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0326-3015&BRID=1289709&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0426-0094&BRID=1286628&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0526-0438&BRID=1297401&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0526-2108&BRID=1302790&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0226-1981&BRID=1277686&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0526-1715&BRID=1302324&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0426-2636&BRID=1296165&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0326-1111&BRID=1282176&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J0226-1829&BRID=1276643&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
| https://cgi.njoyn.com/corp/xweb/xweb.asp?NTKN=c&clid=21001&Page=JobDetails&Jobid=J1125-2226&BRID=1252104&lang=1 | - | missed_by_collection | - | - | not_relevant | - | - |
### Canada Life
- Manual career page: https://jobs.canadalife.com/search/?createNewAlert=false&q=&locationsearch=&optionsFacetsDD_location=&optionsFacetsDD_country=CA&optionsFacetsDD_department=
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://jobs.canadalife.com/job/London-Solutions-Architect-ON/1404013933/ | - | extracted_and_relevant | London, ON, CA +2 more… | 12 | adjacent_customer_facing_technical_fit | adjacent customer-facing technical fit: Solutions Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://jobs.canadalife.com/job/Toronto-Senior-Network-Engineering-Specialist-Lead-%28Cloud-and-On-premise%29-ON/1381006633/ | - | extracted_but_rejected_by_scoring | Toronto, ON, CA +2 more… | - | not_relevant | matched skills: networking; location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
| https://jobs.canadalife.com/job/London-Senior-Devops-Engineering-Specialist-ON/1400494133/ | - | saved_by_mvp | London, ON, CA +2 more… | 5 | core_target_fit | description mentions target role: DevOps Engineer | - |
| https://jobs.canadalife.com/job/Toronto-Senior-Network-Engineering-Specialist-%28Cloud-and-On-premise%29-ON/1381005333/ | - | extracted_but_rejected_by_scoring | Toronto, ON, CA +2 more… | - | not_relevant | matched skills: networking; location signals: Toronto | Rejected because no positive scoring signals survived after penalties. |
### NTT Data
- Manual career page: https://careers.services.global.ntt/global/en/search-results
- Filter used: Canada
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://careers.services.global.ntt/global/en/job/R-139490/Senior-Azure-Architect | - | extracted_and_relevant | Senior Azure Architect | 1 | core_target_fit | matched skills: Azure; location signals: Toronto, Ontario, Canada | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://careers.services.global.ntt/global/en/job/369004/Platform-Engineer-AWS-Remote | - | extracted_and_relevant | Platform Engineer (AWS) - Remote | 61 | core_target_fit | title matches target role: Platform Engineer; matched skills: AWS; location signals: Toronto, Canada, Remote | Saved as relevant because the job had a positive score and at least one core non-location signal. |
| https://careers.services.global.ntt/global/en/job/375279/Oracle-ERP-Cloud-Solution-Architect-Remote | - | extracted_and_relevant | Oracle ERP Cloud Solution Architect - Remote | 36 | adjacent_customer_facing_technical_fit | location signals: Toronto, Canada, Remote; adjacent customer-facing technical fit: Solution Architect | Saved as an adjacent customer-facing technical fit because the role matched the secondary relevance bucket. |
| https://careers.services.global.ntt/global/en/job/354894/Azure-APIM-Self-Hosted-Gateway-Administrator-HYBRID | - | extracted_and_relevant | Azure APIM & Self-Hosted Gateway Administrator - HYBRID | 24 | core_target_fit | matched skills: Azure; location signals: Toronto, Canada, Hybrid; support/ops signals: administrator, admin | Saved as relevant because the job had a positive score and at least one core non-location signal. |
### National Bank of Canada
- Manual career page: https://emplois.bnc.ca/en_CA/careers/searchjobs
- Filter used: note: couldnt apply country filter, i think the list had roles outside of canada as well. i would like to know if the mvp was able to add coutnry filter or not.
- Pages checked: first 10

| Manual URL | Manual Title | Status | Matched Title | Score | Tier | Reasons | Rejection/Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| https://emplois.bnc.ca/en_CA/careers/JobDetail/P6I75-ARCHITECTE-SENIOR-DE-SOLUTIONS/32846 | - | saved_by_mvp | Senior Solutions Architect | 13 | adjacent_customer_facing_technical_fit | location signals: Hybrid; adjacent customer-facing technical fit: Solutions Architect | - |
| https://emplois.bnc.ca/en_CA/careers/JobDetail/P5I27-INT-GRATEUR-SENIOR-DEVOPS/32032 | - | missed_by_collection | - | - | not_relevant | - | - |

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
