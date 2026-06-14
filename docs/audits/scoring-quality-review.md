# Scoring Quality Review

## Run Context
- Date: `2026-06-14`
- Scope: `python -m src.main daily-run --verified-only`
- Verified companies checked: `11`
- Jobs discovered before scoring: `1898`
- Saved jobs before narrow Task 12.13 scoring fixes: `107`
- Saved jobs after narrow Task 12.13 scoring fixes: `93`
- Review export rows after fixes: `93`

## What Changed
The scoring pass for Task 12.13 did not rewrite the ranking model. It made a few narrow corrections:

- fixed substring false positives such as `iam` and `terraform` matching inside unrelated words
- hard-rejected obvious off-target titles such as `Executive Assistant`
- rejected retail and branch-style titles such as `Mortgage Specialist`, `Banking Advisor`, `Branch Advisor`, and similar titles unless strong technical context exists
- tightened adjacent customer-facing titles so generic `Delivery Consultant` style titles no longer qualify on title alone
- kept seniority as a confidence/risk flag instead of a blanket rejection

## Current Queue Summary
- Strong match: `23`
- Maybe match: `58`
- Likely false positive: `6`
- Needs user review: `6`

The strongest retained queue is concentrated in:
- CGI
- TD
- IBM Consulting
- Manulife
- NTT DATA

The latest scoring pass removed the obvious off-target saved rows that had been coming from:
- retail banking wording
- wealth management associate wording
- customer experience wording
- substring-only skill matches

## Strong Match
These look aligned with the current Cloud / DevOps / Platform / Systems / Technical-adjacent target.

| Company | Title | Location | Score | Relevance Tier | Why It Was Saved | Why It Might Still Be Wrong |
| --- | --- | --- | ---: | --- | --- | --- |
| TD | Lead Platform Engineer, TD Securities | - | 45 | core target | direct target title match | seniority / domain fit still needs human judgment |
| Manulife | Cloud & Platform Engineer | - | 45 | core target | direct platform title match | location not surfaced cleanly in export |
| CGI | Windows/Linux Systems Administrator – Cloud Focus (AWS/Azure) | Montreal, Canada | 69 | core target | target admin title plus AWS, Azure, Linux | very strong match; low risk |
| CGI | Linux Systems Administrator (Senior) | Montréal, Canada | 46 | core target | target admin title plus Linux | seniority lowers confidence |
| NTT DATA | Platform Engineer (AWS) - Remote | Remote | 53 | core target | target platform title plus AWS | remote scope still worth manual confirmation |
| Sun Life | Senior Security Platform Engineer | - | 30 | core target | target platform title | security/platform fit is good, but seniority matters |
| IBM Consulting | Sales Solutions Engineer - Hashicorp Professional Multiple Cities | - | 24 | adjacent technical | adjacent solutions engineer title survived because the title is explicitly technical | customer-facing sales engineering may or may not be useful depending on user preference |
| IBM Consulting | Consulting Microsoft Dynamics 365 CE Technical Solution Architect Professional Multiple Cities | - | 24 | adjacent technical | technical solution architect wording | solution-architect scope may still be more senior than desired |
| IBM Consulting | Infrastructure & Technology Maximo Technical Consultant/Architect Professional Multiple Cities | - | 24 | adjacent technical | explicit technical consultant/architect wording | consulting-heavy and likely senior |
| CGI | AWS Solution Architect | Toronto, Canada | 36 | adjacent technical | AWS skill plus solution architect fit | architect roles may be senior-heavy |

## Maybe Match
These are plausible enough to review, but they are weaker than the strongest queue and may be filtered down later with user feedback.

| Company | Title | Location | Score | Relevance Tier | Why It Was Saved | Why It Might Still Be Wrong |
| --- | --- | --- | ---: | --- | --- | --- |
| TD | Sr. IT Support Analyst - ION, MarketView, Trading | - | 12 | core target | support signals with clearly technical trading context | support-heavy rather than cloud/platform |
| TD | IT Support Analyst III | - | 12 | core target | support signals | could be too general without deeper infra context |
| TD | Cloud IAM Engineer II | - | 4 | core target | IAM skill match | score is thin because title is close but not in direct role list |
| TD | Sr. Business Systems Analyst - Salesforce, nCino | - | 18 | adjacent technical | business systems analyst with technical context | may be more business-application than platform |
| National Bank of Canada | Chief Technical Support Analyst End-User IT Support | Toronto, Ontario | 20 | core target | technical support wording | end-user support may be outside preferred target scope |
| National Bank of Canada | Chief Python Developer | Hybrid | 8 | core target | Python signal | generic developer roles are not always cloud/platform aligned |
| CGI | ServiceNow Administrator/Developer | Toronto, Canada | 16 | core target | admin/support signal with technical product context | may drift into app admin rather than infrastructure |
| IBM Consulting | Infrastructure & Technology Senior SAP Solution Architect (Utilities) Professional Multiple Cities | - | 9 | adjacent technical | solution architect wording | likely too senior and SAP-specific |
| Manulife | AI Product Analyst – Global Technology Operations | - | 8 | core target | operations signal in a technology context | could be product/ops rather than infra/platform |
| Canada Life | Solutions Architect (Digital) | Toronto | 16 | adjacent technical | adjacent architect fit plus location | may be too solution/experience oriented depending on the actual posting |

## Likely False Positive
These are still saved today, but they are the strongest candidates for a future narrow scoring cleanup.

| Company | Title | Location | Score | Relevance Tier | Why It Was Saved | Why It Might Be Wrong |
| --- | --- | --- | ---: | --- | --- | --- |
| IBM Consulting | Sales Customer Success Engineer - Automation - Application Development Professional Multiple Cities | - | 24 | adjacent technical | customer success engineer title is technically adjacent | may still be too sales-facing for the user's workflow |
| IBM Consulting | Consulting Advisory Delivery Consultant - Maximo Professional Multiple Cities | - | 24 | adjacent technical | legacy adjacent delivery-consultant path | generic delivery consulting is not a strong cloud/platform signal |
| IBM Consulting | Consulting Delivery Consultant - IBM Maximo, Tririga Professional Multiple Cities | - | 24 | adjacent technical | legacy adjacent delivery-consultant path | likely too consulting-specific and not hands-on enough |
| IBM Consulting | Consulting Lead Delivery Consultant - IBM Sterling / Consultant principal en livraison - IBM Sterling Professional Multiple Cities | - | 9 | adjacent technical | adjacent consultant wording survived plus location-like noise | principal/lead consulting is likely out of target scope |
| NTT DATA | Inbound Customer Service Representative (English) - On Site | Ottawa, Ontario, Canada | 20 | core target | troubleshooting text triggered support scoring | customer-service support is likely too broad and non-platform |
| Manulife | Admin Advantage Update Benefit Administrator (UBA), AdminAdvantage | - | 8 | core target | `administrator` / `admin` signal | product administration is probably not the intended systems-admin target |

## Needs User Review
These are not obvious false positives, but they depend strongly on the user's appetite for senior, architect, or application-heavy roles.

| Company | Title | Location | Score | Relevance Tier | Why It Was Saved | Why It Needs Review |
| --- | --- | --- | ---: | --- | --- | --- |
| National Bank of Canada | Senior Trading Support Analyst | Hybrid | 1 | core target | support signal survived with seniority penalty | thin score and trading-domain support may or may not be useful |
| CGI | Application Support Analyst (Senior) | Montréal, Canada | 1 | core target | support signals survived with seniority penalty | may be too application-operations focused |
| NTT DATA | Senior Azure Architect | Toronto, Ontario, Canada | 1 | core target | Azure signal survived a strong seniority penalty | clearly technical, but likely too senior |
| Manulife | Lead Solution Architect | - | 24 | adjacent technical | adjacent architect fit | probably senior, but still technically aligned |
| Manulife | Lead Solution Architect - GWAM Institutional and General Accounts Investments Technology | - | 24 | adjacent technical | adjacent architect fit with technology wording | likely senior and domain-specialized |
| CGI | Business Systems Analyst | Toronto, Canada | 26 | adjacent technical | technical-context BSA path | depends on whether the user wants systems/application analysis roles |

## Removed By The Narrow Fixes
The current queue no longer includes the obvious false positives that had been slipping through before the boundary and title checks:

- `Mortgage Specialist - Estrie & South Shore`
- `Spécialiste Hypothécaire - Estrie et Rive Sud de Montréal`
- `Customer Experience Associate - Candiac (Part-time, 18.75h/week)`
- `Wealth Management Associate Program - ScotiaMcLeod (Eastern Ontario) - January 2027`
- `Wealth Management Associate Program - ScotiaMcLeod (Western Canada) - January 2027`
- `Wealth Management Associate Program - ScotiaMcLeod (Atlantic Canada) - January 2027`

Those were driven by substring-only skill matches rather than real technical role fit.

## Recommended Next Scoring Work
The next scoring pass should stay narrow and evidence-based:

1. Decide whether `Customer Success Engineer` should remain in scope when the posting is visibly sales-led.
2. Decide whether `Delivery Consultant` should require stronger technical context everywhere, including titles coming from mixed IBM naming conventions.
3. Decide whether `Customer Service Representative` with technical troubleshooting should remain a maybe-match or be removed from the target scope.
4. Decide whether administrative product roles that only match `administrator` / `admin` should require infrastructure/platform terms before saving.

## Review Inputs
- Saved review CSV: [saved-jobs-review.csv](C:/projects/job-discovery-browser-copilot/data/exports/review/saved-jobs-review.csv)
- Saved jobs export: [jobs-2026-06-14.csv](C:/projects/job-discovery-browser-copilot/data/exports/jobs-2026-06-14.csv)
- Daily report: [daily-report-2026-06-14.md](C:/projects/job-discovery-browser-copilot/data/exports/daily-report-2026-06-14.md)
