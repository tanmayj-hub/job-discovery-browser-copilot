# First 3-Company Manual URL Audit Summary

## Audit Scope
- Companies: TD, IBM Consulting, Sun Life
- Filter used: Canada only
- Pages checked: first 10 pages per company
- Sources reviewed: official company career pages only

## Manual Expected Counts
| Company | Expected URLs |
| --- | ---: |
| TD | 4 |
| IBM Consulting | 12 |
| Sun Life | 3 |

## Final Status Counts
| Status | Count |
| --- | ---: |
| saved_by_mvp | 2 |
| extracted_and_relevant | 10 |
| extracted_but_rejected_by_scoring | 3 |
| outside_scope | 3 |
| inactive_or_expired | 1 |
| blocked_or_not_tested | 0 |
| unknown | 0 |

## Per-Company Results
- TD: saved_by_mvp=2, extracted_and_relevant=1, inactive_or_expired=1
- Lead Platform Engineer, TD Securities: saved_by_mvp
- Sr IT Support Analyst, ION / MarketView Trading: saved_by_mvp
- IT Build Analyst II - Onsite AV Support: extracted_and_relevant
- Software Engineer II, Salesforce: inactive_or_expired
- IBM Consulting: extracted_and_relevant=8, extracted_but_rejected_by_scoring=3, outside_scope=1
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=92913&source=WEB_Search_NA: extracted_and_relevant
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=113691&source=WEB_Search_NA: extracted_and_relevant
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=99986&source=WEB_Search_NA: extracted_and_relevant
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=116909&source=WEB_Search_NA: extracted_and_relevant
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=109197&source=WEB_Search_NA: extracted_and_relevant
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=111494&source=WEB_Search_NA: extracted_but_rejected_by_scoring
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=111872&source=WEB_Search_NA: extracted_but_rejected_by_scoring
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=87530&source=WEB_Search_NA: extracted_and_relevant
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=115116&source=WEB_Search_NA: extracted_and_relevant
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=118746&source=WEB_Search_NA: extracted_and_relevant
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=119355&source=WEB_Search_NA: outside_scope
- https://careers.ibm.com/en_US/careers/JobDetail?jobId=109784&source=WEB_Search_NA: extracted_but_rejected_by_scoring
- Sun Life: extracted_and_relevant=1, outside_scope=2
- M365 Productivity & Collaboration Engineer: outside_scope
- Container Service Delivery Co-Ordinator (OpenShift / Kubernetes): extracted_and_relevant
- Future Opportunities: outside_scope

## Remaining Collection Misses
- None in the current first-10-page audited slice.

## Direct URL Follow-Up
- TD: Software Engineer II, Salesforce -> inactive_or_expired
  Direct official Workday URL now returns `The page you are looking for doesn't exist.`
  The role was also absent from the current Canada listing in both the first 10 pages and a diagnostic-only 20-page rerun.

## Remaining Scoring Or Scope Debates
- IBM Consulting: Consulting Customer Experience Consulting Intern (Sept 2026 - 4 Months - Toronto) Internship Toronto, CA -> extracted_but_rejected_by_scoring (Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason.)
- IBM Consulting: Consulting Salesforce Consulting & GTM Intern (Sept 2026 - 4 Months - Toronto) Internship Toronto, CA -> extracted_but_rejected_by_scoring (Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason.)
- IBM Consulting: Sales Technology Sales Specialist - Consulting/SI Partner Professional Multiple Cities -> outside_scope (Rejected because no positive scoring signals survived after penalties.)
- IBM Consulting: Sales Brand Technical Sales Specialist – Power & Cloud Professional Toronto, CA -> extracted_but_rejected_by_scoring (Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason.)
- Sun Life: M365 Productivity & Collaboration Engineer -> outside_scope (Rejected because no positive scoring signals survived after penalties.)
- Sun Life: Future Opportunities -> outside_scope (Rejected because no positive scoring signals survived after penalties.)

## Recommendation
- No current extractor fix is justified from this first 3-company manual URL audit.
- Scoring changes are not yet recommended broadly; review rejected-but-extracted rows case by case.
- TD `Software Engineer II, Salesforce` should be monitored only if it reappears in a future collected slice; title-only historical evidence is not enough to promote it.
- Move to the next company audit or the next scoring-focused review with the current collection path unchanged.
