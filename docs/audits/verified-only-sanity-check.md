# Verified-Only Sanity Check

## Run
- Date: 2026-06-14
- Command: `python -m src.main daily-run --verified-only`
- Dashboard import smoke: `python -c "import src.dashboard.app; print('dashboard_import_ok')"`

## Current Verified Usable List
- Aviva Canada
- BMO
- Canada Life
- CGI
- IBM Consulting
- Manulife
- National Bank of Canada
- NTT DATA
- Sun Life
- TD

## Metrics
- Companies checked: 10
- Companies skipped: 0
- Jobs discovered: 1040
- Jobs scored: 1040
- Jobs relevant: 48
- Jobs saved: 48
- Explicit non-Canada jobs rejected by safety gate: 18
- Suspicious saved rows: 0
- Errors: 1

## Source Warnings
- CGI returned a fresh extraction error during the verified-only smoke run:
  `Page.content: Unable to retrieve content because the page is navigating and changing the content.`
- The verified-only report still completed and saved the rest of the slice successfully.
- Active pending interventions shown in the report are currently outside the verified-only daily review path.

## Dashboard Sanity
- The dashboard module imports successfully from the repo virtualenv.
- The current dashboard code supports:
  - verified-company filtering
  - provisional verified records like BMO
  - saved jobs and job URLs
  - source status rows with scope/readiness
  - relevance-tier display
- Result: the dashboard is usable for daily review of the current verified slice.

## Next Bank Slice Fault Table
| Company | Configured source URL | Manual audit URL if present | Source scope status | Trusted run result | Diagnostic result | Manual recall availability | Likely failure mode | Fix plan |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RBC | `https://jobs.rbc.com/ca/en/search-results?from=140&s=1` | same | unconfirmed | skipped before pagination | 100 discovered, 3 relevant, 10 pages | yes, 4 URLs | public results page still mixes countries unless the Country facet is properly applied and confirmed | keep `needs_review`; add safe public Country=Canada facet handling later |
| TD | `https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=a30a87ed25634629aa6c3958aa2b91ea` | `https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers?locationCountry=a30a87ed25634629aa6c3958aa2b91ea` | confirmed | 182 discovered, 9 saved, 10 pages | 182 discovered, 9 relevant, 10 pages | yes, 3 URLs | no active source-scope blocker in the current slice | promote to verified usable |
| Scotiabank | `https://jobs.scotiabank.com/search/?createNewAlert=false&q=&locationsearch=canada` | same | confirmed after fix | 258 discovered, 6 saved, 10 pages | 258 discovered, 6 relevant, 10 pages | yes, 5 URLs | current 10-page slice still misses 4 manually found roles | keep `needs_review`; investigate page-depth or extraction gaps later |

## Conclusion
- The verified-only dashboard/data path is currently usable for daily review.
- TD is ready to join the trusted verified slice.
- RBC and Scotiabank both need more source-specific verification work before promotion.
- CGI should stay in the verified slice for now, but its fresh extraction error should be revisited in the next maintenance pass.
