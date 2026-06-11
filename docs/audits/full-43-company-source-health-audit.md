# Full 43-Company Source Health Audit

## Executive Summary
- Run date: 2026-06-10
- Configured companies reviewed: 43
- Companies checked in the run: 43
- Completed sources: 35
- Paused sources: 6
- Error sources: 2
- Manual-only sources: 0
- Needs-URL sources: 0
- Jobs discovered: 860
- Jobs scored: 860
- Relevant jobs saved: 51
- Pending interventions: 9
- Suspicious saved rows: 0

## Run Configuration
- Active collection scope: Canada
- Canada-only scope confirmed: yes
- City/province/remote filters used globally: no
- Max pages per source: 10
- Keyword fallback used before extraction: False
- Relevance tiers confirmed: `core_target_fit`, `adjacent_customer_facing_technical_fit`

## Overall Metrics
| Metric | Value |
| --- | ---: |
| Configured companies | 43 |
| Companies checked | 43 |
| Completed | 35 |
| Paused | 6 |
| Errors | 2 |
| Manual-only | 0 |
| Needs-URL | 0 |
| Jobs discovered | 860 |
| Jobs scored | 860 |
| Relevant saved | 51 |
| Jobs inserted | 44 |
| Jobs updated | 5 |
| Jobs unchanged | 2 |
| Duplicates skipped | 0 |

## Company-By-Company Source Table
| Company | Source URL | Mode | ATS | Status | Pages | Candidates | Scored | Relevant Saved | Inserted | Updated | Unchanged | Pagination Stop | Intervention | Suspicious | Recommended Action |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| CIBC | https://www.cibc.com/en/about-cibc/careers.html | human_in_loop | workday | error | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | extraction_failed | 0 | Review the page manually to confirm whether selectors need updating or the source should stay manual-only. |
| Desjardins | https://www.desjardins.com/en/careers.html | browser_allowed | - | paused | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | cookie_blocked | 0 | Open the source, clear or accept the blocking cookie banner, then rerun the source. |
| NTT DATA | https://ca.nttdata.com/en/careers | browser_allowed | - | paused | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | login_required | 0 | Open the public careers URL manually and confirm whether sign-in is mandatory. If login is required for job listings, keep the source manual-only. |
| Cognizant | https://careers.cognizant.com/ca-en/ | browser_allowed | - | paused | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | unclear_layout | 0 | Open the source manually and identify the public careers results page before another run. |
| HCLTech | https://www.hcltech.com/careers | browser_allowed | - | error | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | extraction_failed | 0 | Review the page manually to confirm whether selectors need updating or the source should stay manual-only. |
| Wipro | https://careers.wipro.com/?locale=en_US | browser_allowed | - | paused | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | cookie_blocked | 0 | Open the source, clear or accept the blocking cookie banner, then rerun the source. |
| Tech Mahindra | https://careers.techmahindra.com/ | browser_allowed | - | paused | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | login_required | 0 | Open the public careers URL manually and confirm whether sign-in is mandatory. If login is required for job listings, keep the source manual-only. |
| Wawanesa Insurance | https://jobs.wawanesa.com/search?utm_source=corporate_website&utm_medium=search_jobs_button&utm_campaign=traffic_source | browser_allowed | - | paused | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | unclear_layout | 0 | Open the source manually and identify the public careers results page before another run. |
| TD | https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=a30a87ed25634629aa6c3958aa2b91ea | human_in_loop | workday | completed | 2 | 0 | 0 | 0 | 0 | 0 | 0 | no_new_job_urls | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Tangerine | https://www.tangerine.ca/en/careers | browser_allowed | - | completed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| EQ Bank (Equitable Bank) | https://www.eqbank.ca/about-us/about/careers | browser_allowed | - | completed | 2 | 0 | 0 | 0 | 0 | 0 | 0 | no_new_job_urls | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Laurentian Bank | https://www.laurentianbank.ca/en/about-us/careers | browser_allowed | - | completed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Accenture | https://www.accenture.com/ca-en/careers | browser_allowed | - | completed | 2 | 0 | 0 | 0 | 0 | 0 | 0 | no_new_job_urls | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| KPMG | https://kpmg.com/ca/en/careers.html | browser_allowed | - | completed | 2 | 0 | 0 | 0 | 0 | 0 | 0 | no_new_job_urls | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Capgemini | https://careers.capgemini.com/?locale=en_US | browser_allowed | - | completed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Tata Consultancy Services (TCS) | https://www.tcs.com/careers | browser_allowed | - | completed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Infosys | https://careers.infosys.com/ | browser_allowed | - | completed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| DXC Technology | https://careers.dxc.com/job-search-results/ | browser_allowed | - | completed | 2 | 0 | 0 | 0 | 0 | 0 | 0 | no_new_job_urls | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Genpact | https://www.genpact.com/careers/job-search | browser_allowed | - | completed | 2 | 0 | 0 | 0 | 0 | 0 | 0 | no_new_job_urls | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Aviva Canada | https://aviva.wd1.myworkdayjobs.com/External?Location_Country=a30a87ed25634629aa6c3958aa2b91ea | human_in_loop | workday | completed | 2 | 0 | 0 | 0 | 0 | 0 | 0 | no_new_job_urls | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| iA Financial Group | https://ia.ca/jobs/jobs-available | browser_allowed | - | completed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Manulife | https://careers.manulife.com/global/en/search-results | browser_allowed | - | completed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| Ateko | https://ateko.com/en/careers/ | browser_allowed | - | completed | 1 | 0 | 0 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs. |
| BMO | https://jobs.bmo.com/global/en/home | browser_allowed | - | completed | 10 | 102 | 102 | 10 | 8 | 0 | 2 | max_pages_reached | - | 0 | Consider a manual audit or a per-company page-cap override if relevant jobs may exist beyond the current safe pagination limit. |
| National Bank of Canada | https://emplois.bnc.ca/en_CA/careers | browser_allowed | - | completed | 10 | 200 | 200 | 2 | 2 | 0 | 0 | max_pages_reached | - | 0 | Consider a manual audit or a per-company page-cap override if relevant jobs may exist beyond the current safe pagination limit. |
| Intact Financial | https://careers.intactfc.com/jobs | browser_allowed | - | completed | 10 | 101 | 101 | 2 | 2 | 0 | 0 | max_pages_reached | - | 0 | Consider a manual audit or a per-company page-cap override if relevant jobs may exist beyond the current safe pagination limit. |
| RBC | https://jobs.rbc.com/en | browser_allowed | - | completed | 1 | 9 | 9 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| Scotiabank | https://www.scotiabank.com/careers/en/careers.html | browser_allowed | - | completed | 1 | 1 | 1 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| ATB Financial | https://careers.atb.com/ | browser_allowed | - | completed | 2 | 13 | 13 | 1 | 0 | 1 | 0 | no_new_job_urls | - | 0 | Monitor normally. |
| Vancity | https://www.vancity.com/careers | human_in_loop | ultipro | completed | 1 | 1 | 1 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| TMX Group | https://www.tmx.com/careers | human_in_loop | workday | completed | 1 | 4 | 4 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| Deloitte | https://www.deloitte.com/ca/en/careers.html | browser_allowed | - | completed | 1 | 1 | 1 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| PwC | https://jobs-ca.pwc.com/ca/en/home | browser_allowed | - | completed | 4 | 31 | 31 | 3 | 3 | 0 | 0 | no_new_job_urls | - | 0 | Monitor normally. |
| EY | https://www.ey.com/en_ca/careers | browser_allowed | - | completed | 2 | 1 | 1 | 0 | 0 | 0 | 0 | no_new_job_urls | - | 0 | Monitor normally. |
| IBM Consulting | https://www.ibm.com/careers/search | browser_allowed | - | completed | 4 | 103 | 103 | 17 | 16 | 1 | 0 | next_disabled_or_missing | - | 0 | Monitor normally. |
| CGI | https://www.cgi.com/canada/en-ca/careers | browser_allowed | - | completed | 1 | 1 | 1 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| Slalom | https://www.slalom.com/us/en/careers | browser_allowed | - | completed | 2 | 2 | 2 | 0 | 0 | 0 | 0 | no_new_job_urls | - | 0 | Monitor normally. |
| Thoughtworks | https://www.thoughtworks.com/en-ca/careers | browser_allowed | - | completed | 1 | 81 | 81 | 9 | 6 | 3 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| Kyndryl | https://www.kyndryl.com/us/en/careers | browser_allowed | - | completed | 1 | 5 | 5 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| Canada Life | https://jobs.canadalife.com/go/All-Jobs/9170201?locale=en_US | browser_allowed | - | completed | 1 | 35 | 35 | 1 | 1 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| Definity Financial (Economical) | https://hdks.fa.ca2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/Careers-Definity/jobs?lastSelectedFacet=AttributeChar4&mode=location&selectedFlexFieldsFacets=%22AttributeChar4%7CEnglish+and+French%3BEnglish%22 | human_in_loop | oracle_hcm | completed | 1 | 1 | 1 | 0 | 0 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |
| Sun Life | https://sunlife.wd3.myworkdayjobs.com/Experienced-Jobs?Location_Country=a30a87ed25634629aa6c3958aa2b91ea | human_in_loop | workday | completed | 6 | 117 | 117 | 3 | 3 | 0 | 0 | next_disabled_or_missing | - | 0 | Monitor normally. |
| The Co-operators | https://recruiting.ultipro.com/COO5000COOP/JobBoard/163383cc-cbae-4201-956e-c5e437bbfeb3?q=&o=postedDateDesc&w=&wc=&we=&wpst= | human_in_loop | ultipro | completed | 1 | 51 | 51 | 3 | 3 | 0 | 0 | pagination_not_detected | - | 0 | Monitor normally. |

## Top 10 Companies Needing Attention
- CIBC | status=error | mode=human_in_loop | candidates=0 | saved=0 | issue=paused_or_error | Review the page manually to confirm whether selectors need updating or the source should stay manual-only.
- Desjardins | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the source, clear or accept the blocking cookie banner, then rerun the source.
- NTT DATA | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the public careers URL manually and confirm whether sign-in is mandatory. If login is required for job listings, keep the source manual-only.
- Cognizant | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the source manually and identify the public careers results page before another run.
- HCLTech | status=error | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Review the page manually to confirm whether selectors need updating or the source should stay manual-only.
- Wipro | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the source, clear or accept the blocking cookie banner, then rerun the source.
- Tech Mahindra | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the public careers URL manually and confirm whether sign-in is mandatory. If login is required for job listings, keep the source manual-only.
- Wawanesa Insurance | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the source manually and identify the public careers results page before another run.
- TD | status=completed | mode=human_in_loop | candidates=0 | saved=0 | issue=zero_discovery | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Tangerine | status=completed | mode=browser_allowed | candidates=0 | saved=0 | issue=zero_discovery | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.

## Zero-Discovery Companies
- TD | status=completed | mode=human_in_loop | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Tangerine | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- EQ Bank (Equitable Bank) | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Laurentian Bank | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Accenture | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- KPMG | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Capgemini | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Tata Consultancy Services (TCS) | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Infosys | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- DXC Technology | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Genpact | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Aviva Canada | status=completed | mode=human_in_loop | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- iA Financial Group | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Manulife | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.
- Ateko | status=completed | mode=browser_allowed | candidates=0 | saved=0 | Review the public careers flow and Canada scoping because the run completed with zero discovered jobs.

## High-Discovery / Zero-Relevant Companies
- None

## Paused Or Error Companies
- CIBC | status=error | mode=human_in_loop | candidates=0 | saved=0 | issue=paused_or_error | Review the page manually to confirm whether selectors need updating or the source should stay manual-only.
- Desjardins | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the source, clear or accept the blocking cookie banner, then rerun the source.
- NTT DATA | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the public careers URL manually and confirm whether sign-in is mandatory. If login is required for job listings, keep the source manual-only.
- Cognizant | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the source manually and identify the public careers results page before another run.
- HCLTech | status=error | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Review the page manually to confirm whether selectors need updating or the source should stay manual-only.
- Wipro | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the source, clear or accept the blocking cookie banner, then rerun the source.
- Tech Mahindra | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the public careers URL manually and confirm whether sign-in is mandatory. If login is required for job listings, keep the source manual-only.
- Wawanesa Insurance | status=paused | mode=browser_allowed | candidates=0 | saved=0 | issue=paused_or_error | Open the source manually and identify the public careers results page before another run.

## Pagination-Cap Companies
- BMO | status=completed | mode=browser_allowed | candidates=102 | saved=10 | Consider a manual audit or a per-company page-cap override if relevant jobs may exist beyond the current safe pagination limit.
- National Bank of Canada | status=completed | mode=browser_allowed | candidates=200 | saved=2 | Consider a manual audit or a per-company page-cap override if relevant jobs may exist beyond the current safe pagination limit.
- Intact Financial | status=completed | mode=browser_allowed | candidates=101 | saved=2 | Consider a manual audit or a per-company page-cap override if relevant jobs may exist beyond the current safe pagination limit.

## Source URL Remediation Candidates
- None

## Recommended Next Manual Audit Slice
- TD | priority=High | status=completed | candidates=0 | saved=0 | reason=zero_discovery
- Aviva Canada | priority=High | status=completed | candidates=0 | saved=0 | reason=zero_discovery
- BMO | priority=High | status=completed | candidates=102 | saved=10 | reason=pagination_cap
- National Bank of Canada | priority=High | status=completed | candidates=200 | saved=2 | reason=pagination_cap
- Intact Financial | priority=High | status=completed | candidates=101 | saved=2 | reason=pagination_cap

## Notes
- The first 3-company manual URL audit reports remain unchanged and are still the authoritative manual-recall audit artifacts.
- This report focuses on source health, run behavior, and next debugging priorities across the configured 43-company watchlist.
