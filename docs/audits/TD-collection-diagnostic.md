# TD Collection Diagnostic

## Source
- Company: TD
- Starting URL: https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=a30a87ed25634629aa6c3958aa2b91ea
- Final URL reached: https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=a30a87ed25634629aa6c3958aa2b91ea
- Source mode: human_in_loop
- ATS type: workday
- Cookie banner action: accept cookies
- Language prompt action: none

## Location Scope
- Location scope used: True
- Configured locations: Canada
- Location filter/search attempted: Canada (URL filter)
- Exact filter method: url_filter

## Pagination
- Pagination detected: True
- Next/load-more detection result: detected
- Max pages per source: 10
- Pages visited: 2
- Jobs extracted per page: [0, 0]
- Pagination stop reason: no_new_job_urls

## Counts
- Candidate jobs before scoring: 0
- Jobs after scoring: 0
- Relevant jobs after scoring: 0
- Unique IBM jobIds extracted: 0
- Unique Workday job IDs extracted: 0
- Scored candidates CSV: data\exports\audits\TD-scored-candidates.csv

## Visited Pages
- https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=a30a87ed25634629aa6c3958aa2b91ea
- https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=a30a87ed25634629aa6c3958aa2b91ea

## Manual Expected Coverage
- Manual expected URLs provided: 4
- Matching manual expected URLs found: 0 / 4
- Manual expected URLs still missing: 4
- Matching manual Workday job IDs found: none
- Manual Workday job IDs still missing: R_1486443, R_1489301, R_1491997, R_1493452

| Manual URL | Manual Title | Raw HTML | Anchor href | Script/JSON | Extracted | Scored | Saved by MVP | Status | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Lead-Platform-Engineer--TD-Securities_R_1491997?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | Lead Platform Engineer, TD Securities | yes | yes | no | no | no | yes | saved_by_mvp | job anchor present in DOM but extraction did not emit a candidate |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Sr-IT-Support-Analyst---ION--MarketView--Trading_R_1489301?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | Sr IT Support Analyst, ION / MarketView Trading | yes | yes | no | no | no | yes | saved_by_mvp | job anchor present in DOM but extraction did not emit a candidate |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/IT-Build-Analyst-II---Onsite-AV-Support_R_1493452?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | IT Build Analyst II - Onsite AV Support | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Software-Engineer-II--Salesforce_R_1486443?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | Software Engineer II, Salesforce | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |

## Candidate Jobs Before Scoring
- None

## Scored Candidates
- None

## Relevant Jobs After Scoring
- None

## Rejected But Interesting Jobs
- None

## Task 12.1 Full-Run Mismatch Review
- Current TD config URL and current full `daily-run` URL are the same Canada-filtered Workday URL shown above.
- Current one-company diagnostic path and current filtered `daily-run --company "TD"` path both ended at zero discovered jobs.
- Current TD outcome is therefore a real live zero-discovery issue, not a routing mismatch between the diagnostic and the daily workflow.
- The earlier apparent mismatch came from comparing this current TD state against an older historical TD diagnostic that no longer matches the latest reruns.
- A separate report-generation issue was also confirmed during Task 12.1:
  the earlier full 43-company audit had been produced from a nonstandard headless helper instead of the default `daily-run` path.
- Rechecking the same default daily-run path with company filters showed:
  `Aviva Canada` now discovers 83 candidates and saves 1 relevant job, and `Manulife` now discovers 100 candidates and saves 8 relevant jobs.
- That means the old full-audit zeroes for `Aviva Canada` and `Manulife` were report artifacts, while `TD` remains the source that still needs direct Workday extraction investigation.
