# RBC Collection Diagnostic

## Source
- Company: RBC
- Starting URL: https://jobs.rbc.com/ca/en/search-results
- Final URL reached: https://jobs.rbc.com/ca/en/search-results?from=20&s=1
- Source mode: browser_allowed
- ATS type: -
- Cookie banner action: #onetrust-accept-btn-handler
- Language prompt action: none

## Source Scope Validation
- Source URL used: https://jobs.rbc.com/ca/en/search-results
- Source scope status: canada_scope_confirmed
- Canada scope confirmed before pagination: True
- Source scope method: ui_filter
- Source scope reason: RBC's public Country=Canada facet was applied before pagination.
- Broad diagnostic collection: False

## Location Scope
- Location scope used: True
- Configured locations: Canada
- Location filter/search attempted: Canada (RBC country facet)
- Exact filter method: rbc_country_facet

## Pagination
- Page policy: capped
- Target page cap: 75
- Pagination detected: True
- Next/load-more detection result: detected
- Max pages per source: 3
- Pages visited: 3
- Jobs extracted per page: [10, 10, 10]
- Pagination stop reason: max_pages_reached
- Pagination complete: False
- Normal stop: False
- Engineering fix required: False

## Sort Policy
- Sort requested: most_recent
- Sort used: Most recent
- Sort status: confirmed
- Sort method: ui_control
- Sort reason: Applied the public newest-first results control before pagination.

## Counts
- Candidate jobs before scoring: 30
- Jobs after scoring: 30
- Relevant jobs after scoring: 2
- Explicit non-Canada jobs rejected by safety gate: 0
- Relevant jobs with unknown/blank location text: 0
- Unique IBM jobIds extracted: 0
- Unique Workday job IDs extracted: 0
- Scored candidates CSV: data\exports\audits\RBC-performance-probe.csv

## Visited Pages
- https://jobs.rbc.com/ca/en/search-results
- https://jobs.rbc.com/ca/en/search-results?from=10&s=1
- https://jobs.rbc.com/ca/en/search-results?from=20&s=1

## Verification Decision
- Decision: ready_for_verified_review
- Reason: Canada source scope was confirmed before pagination and no diagnostic-only fallback was required.

## Manual Expected Coverage
- Manual expected URLs provided: 31
- Matching manual expected URLs found: 0 / 31
- Manual expected URLs still missing: 31

| Manual URL | Manual Title | Raw HTML | Anchor href | Script/JSON | Extracted | Scored | Saved by MVP | Status | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| https://jobs.rbc.com/ca/en/job/R-0000174753/Senior-Cloud-Engineer | - | no | no | no | no | no | yes | saved_by_mvp | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000160071/Digital-Platform-Engineering-Technical-Product-Owner | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000160538/Senior-DevOps-Engineer | - | no | no | no | no | no | yes | saved_by_mvp | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000179431/Senior-Manager-DevOps-Engineering | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000179572/Senior-Site-Reliability-Engineer | - | no | no | no | no | no | yes | saved_by_mvp | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000177388/Application-Support-Engineer | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000176722/Senior-Site-Reliability-Engineer | - | no | no | no | no | no | yes | saved_by_mvp | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000176580/Sr-IAM-Engineer-Vault-Specialist-CyberArk-Hashicorp-Global-Security | - | no | no | no | no | no | yes | saved_by_mvp | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000179335/Senior-IAM-Systems-Support-Analyst-Global-security | - | no | no | no | no | no | yes | saved_by_mvp | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000179867/Staff-Data-platform-Engineer-GFT | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000180099/IAM-Director-Customer-Identity-Access-Management-Controls-Global-Security | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000178766/Senior-DevOps-Engineer | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000178411/Solution-Architect | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000171090/Lead-System-Administrator | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000178414/GFT-Lead-Solutions-Architect | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000179708/AI-Analyst | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000165735/Lead-System-Engineer-Global-Security | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000178089/DevOps-Engineer-Workday-Integrations | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000165577/DevOps-Data-Engineer | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000173122/Cloud-Security-Architect-Global-Security | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000168166/Senior-IAM-Systems-Engineer-Global-Security | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000178346/AI-Quality-Engineer | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000177144/Sr-Administrator | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000164593/Application-Administrator | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000175098/Lead-Solution-Architect | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000178580/Director-SRE-and-AI-Ops-GFT | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000168932/Principal-ML-Ops-Engineer-Azure | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000173020/Application-Support-Analyst-GFT-Halifax | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000177942/Sr-Technical-Systems-Analyst-Database-Activity-Monitoring-GCS | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000152065/Lead-Solution-Architect | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |
| https://jobs.rbc.com/ca/en/job/R-0000173104/Senior-Middleware-Technical-Support-Administrator | - | no | no | no | no | no | no | missed_by_collection | job not present in captured page HTML |

## Candidate Jobs Before Scoring
- Associate, Institutional Client Credit Management - Global Credit, Global Corporate Banking | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000170794/Associate-Institutional-Client-Credit-Management-Global-Credit-Global-Corporate-Banking
- Quantitative Risk Director | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000158350/Quantitative-Risk-Director
- Financial Planner, Investment and Retirement Planning | COBOURG, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000167599/Financial-Planner-Investment-and-Retirement-Planning
- Manager, AML Financial Crime Data Management | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000167903/Manager-AML-Financial-Crime-Data-Management
- (Senior) Relationship Manager, CFS (Agriculture) | RED DEER, Alberta, Canada | https://jobs.rbc.com/ca/en/job/R-0000181039/-Senior-Relationship-Manager-CFS-Agriculture
- Senior Software Developer | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180757/Senior-Software-Developer
- Senior Manager, Marketing Technology and Integrations | MISSISSAUGA, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180716/Senior-Manager-Marketing-Technology-and-Integrations
- Executive Assistant | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000177031/Executive-Assistant
- Financial Advisor Intern | MILTON, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180965/Financial-Advisor-Intern
- Office Manager - Toronto | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180182/Office-Manager-Toronto
- Senior Business Analyst | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000156306/Senior-Business-Analyst
- Financial Advisor | COURTENAY, British Columbia, Canada | https://jobs.rbc.com/ca/en/job/R-0000166799/Financial-Advisor
- Banking Advisor | CHATHAM-KENT, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000169952/Banking-Advisor
- Senior Business Analyst | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000171670/Senior-Business-Analyst
- Senior Manager, High Risk Client Management | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180192/Senior-Manager-High-Risk-Client-Management
- Investment Advisor | REGINA, Saskatchewan, Canada | https://jobs.rbc.com/ca/en/job/R-0000180997/Investment-Advisor
- Software Engineer 1 | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000175906/Software-Engineer-1
- Associate Director, ESG Risk Analytics | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000178085/Associate-Director-ESG-Risk-Analytics
- Financial Planner, Investment and Retirement Planner | SURREY, British Columbia, Canada | https://jobs.rbc.com/ca/en/job/R-0000178848/Financial-Planner-Investment-and-Retirement-Planner
- Director, Corporate Actuarial | MISSISSAUGA, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000175769/Director-Corporate-Actuarial
- Senior Project Manager | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180030/Senior-Project-Manager
- Financial Planner Investment and Retirement Planning | WINNIPEG, Manitoba, Canada | https://jobs.rbc.com/ca/en/job/R-0000180923/Financial-Planner-Investment-and-Retirement-Planning
- Senior Manager, Enterprise Delivery | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180356/Senior-Manager-Enterprise-Delivery
- Branch Manager Advisor | NORTHERN BRUCE PENINSULA, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180401/Branch-Manager-Advisor
- Senior Director, Planning, Strategy & Value – AI & Digital Transformation | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000171205/Senior-Director-Planning-Strategy-Value-AI-Digital-Transformation
- Associate | RED DEER, Alberta, Canada | https://jobs.rbc.com/ca/en/job/R-0000172226/Associate
- Director, Financial Crimes Model Risk Management | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180824/Director-Financial-Crimes-Model-Risk-Management
- Manager - Internal Audit, Global Corporate Treasury | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180842/Manager-Internal-Audit-Global-Corporate-Treasury
- Senior Enterprise Applications Support Engineer (EDI/MFT) | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000174981/Senior-Enterprise-Applications-Support-Engineer-EDI-MFT
- Enterprise Applications Support Engineer (EDI/MFT) | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000174982/Enterprise-Applications-Support-Engineer-EDI-MFT

## Scored Candidates
- Enterprise Applications Support Engineer (EDI/MFT) | score 24 | relevant=True | tier=core_target_fit | matched skills: support; location signals: Toronto, Ontario, Canada; support/ops signals: support | https://jobs.rbc.com/ca/en/job/R-0000174982/Enterprise-Applications-Support-Engineer-EDI-MFT
- Software Engineer 1 | score 12 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000175906/Software-Engineer-1
- Associate, Institutional Client Credit Management - Global Credit, Global Corporate Banking | score 12 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000170794/Associate-Institutional-Client-Credit-Management-Global-Credit-Global-Corporate-Banking
- Senior Enterprise Applications Support Engineer (EDI/MFT) | score 9 | relevant=True | tier=core_target_fit | matched skills: support; location signals: Toronto, Ontario, Canada; support/ops signals: support | https://jobs.rbc.com/ca/en/job/R-0000174981/Senior-Enterprise-Applications-Support-Engineer-EDI-MFT
- Financial Planner, Investment and Retirement Planning | score 8 | relevant=False | tier=not_relevant | location signals: Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000167599/Financial-Planner-Investment-and-Retirement-Planning
- Financial Advisor Intern | score 8 | relevant=False | tier=not_relevant | location signals: Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180965/Financial-Advisor-Intern
- Investment Advisor | score 4 | relevant=False | tier=not_relevant | location signals: Canada | https://jobs.rbc.com/ca/en/job/R-0000180997/Investment-Advisor
- Financial Planner, Investment and Retirement Planner | score 4 | relevant=False | tier=not_relevant | location signals: Canada | https://jobs.rbc.com/ca/en/job/R-0000178848/Financial-Planner-Investment-and-Retirement-Planner
- Financial Planner Investment and Retirement Planning | score 4 | relevant=False | tier=not_relevant | location signals: Canada | https://jobs.rbc.com/ca/en/job/R-0000180923/Financial-Planner-Investment-and-Retirement-Planning
- Financial Advisor | score 4 | relevant=False | tier=not_relevant | location signals: Canada | https://jobs.rbc.com/ca/en/job/R-0000166799/Financial-Advisor
- Associate | score 4 | relevant=False | tier=not_relevant | location signals: Canada | https://jobs.rbc.com/ca/en/job/R-0000172226/Associate
- Senior Software Developer | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180757/Senior-Software-Developer
- Senior Project Manager | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180030/Senior-Project-Manager
- Senior Manager, Marketing Technology and Integrations | score 0 | relevant=False | tier=not_relevant | location signals: Mississauga, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180716/Senior-Manager-Marketing-Technology-and-Integrations
- Senior Manager, High Risk Client Management | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180192/Senior-Manager-High-Risk-Client-Management
- Senior Manager, Enterprise Delivery | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180356/Senior-Manager-Enterprise-Delivery
- Senior Director, Planning, Strategy & Value – AI & Digital Transformation | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000171205/Senior-Director-Planning-Strategy-Value-AI-Digital-Transformation
- Senior Business Analyst | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000156306/Senior-Business-Analyst
- Senior Business Analyst | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000171670/Senior-Business-Analyst
- Quantitative Risk Director | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000158350/Quantitative-Risk-Director
- Office Manager - Toronto | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180182/Office-Manager-Toronto
- Manager, AML Financial Crime Data Management | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000167903/Manager-AML-Financial-Crime-Data-Management
- Manager - Internal Audit, Global Corporate Treasury | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180842/Manager-Internal-Audit-Global-Corporate-Treasury
- Executive Assistant | score 0 | relevant=False | tier=not_relevant | no core matches | https://jobs.rbc.com/ca/en/job/R-0000177031/Executive-Assistant
- Director, Financial Crimes Model Risk Management | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180824/Director-Financial-Crimes-Model-Risk-Management
- Director, Corporate Actuarial | score 0 | relevant=False | tier=not_relevant | location signals: Mississauga, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000175769/Director-Corporate-Actuarial
- Branch Manager Advisor | score 0 | relevant=False | tier=not_relevant | location signals: Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000180401/Branch-Manager-Advisor
- Banking Advisor | score 0 | relevant=False | tier=not_relevant | no core matches | https://jobs.rbc.com/ca/en/job/R-0000169952/Banking-Advisor
- Associate Director, ESG Risk Analytics | score 0 | relevant=False | tier=not_relevant | location signals: Toronto, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000178085/Associate-Director-ESG-Risk-Analytics
- (Senior) Relationship Manager, CFS (Agriculture) | score 0 | relevant=False | tier=not_relevant | location signals: Canada | https://jobs.rbc.com/ca/en/job/R-0000181039/-Senior-Relationship-Manager-CFS-Agriculture

## Relevant Jobs After Scoring
- Senior Enterprise Applications Support Engineer (EDI/MFT) | score 9 | tier=core_target_fit | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000174981/Senior-Enterprise-Applications-Support-Engineer-EDI-MFT
- Enterprise Applications Support Engineer (EDI/MFT) | score 24 | tier=core_target_fit | TORONTO, Ontario, Canada | https://jobs.rbc.com/ca/en/job/R-0000174982/Enterprise-Applications-Support-Engineer-EDI-MFT

## Rejected But Interesting Jobs
- Software Engineer 1 | score 12 | Rejected because the score came from weak or location-only signals and did not include a core role, skill, or support/ops reason. | https://jobs.rbc.com/ca/en/job/R-0000175906/Software-Engineer-1
- Senior Business Analyst | score 0 | Rejected because no positive scoring signals survived after penalties. | https://jobs.rbc.com/ca/en/job/R-0000156306/Senior-Business-Analyst
- Senior Business Analyst | score 0 | Rejected because no positive scoring signals survived after penalties. | https://jobs.rbc.com/ca/en/job/R-0000171670/Senior-Business-Analyst
