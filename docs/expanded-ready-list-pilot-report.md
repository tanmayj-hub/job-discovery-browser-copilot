# Expanded Ready-List Pilot Report

## Verdict

Partial pass.

The 10 ready-list candidates were reviewed conservatively, 9 were approved, and 9 were safely
applied to the watchlist through the existing approved-candidate flow. The expanded pilot then ran
against 43 configured companies and completed twice. Dedupe held on the second run, but three new
company sources surfaced runtime issues that still need hardening.

## Candidates Reviewed

- Aviva Canada
- Canada Life
- Definity Financial (Economical)
- iA Financial Group
- Intact Financial
- Manulife
- RSA Canada (Intact)
- Sun Life
- The Co-operators
- Wawanesa Insurance

## Candidates Approved

- Aviva Canada
  - Official Workday host
  - Public jobs page
  - `human_in_loop` classification is appropriate
- Canada Life
  - Official `jobs.canadalife.com` jobs page
  - Public jobs listing page
  - `browser_allowed` classification is reasonable
- Definity Financial (Economical)
  - Official Oracle HCM candidate experience page
  - Company branding matched
  - `human_in_loop` classification is appropriate
- iA Financial Group
  - Official `ia.ca` jobs page
  - Public jobs/careers page
- Intact Financial
  - Official `careers.intactfc.com` jobs page
  - Public jobs page
- Manulife
  - Official `careers.manulife.com` search page
  - Public careers/jobs results page
- Sun Life
  - Official Workday jobs page
  - `human_in_loop` classification is appropriate
- The Co-operators
  - Official UltiPro board
  - Public jobs board
  - `human_in_loop` classification is appropriate
- Wawanesa Insurance
  - Official `jobs.wawanesa.com` jobs page pattern
  - Public jobs entry URL

## Candidates Skipped

- RSA Canada (Intact)
  - Left unapproved intentionally
  - `ats.rippling.com/rsa-security` may be valid, but the branding and alias relationship were
    weaker than the other nine candidates
  - Kept out of the expanded pilot until verified more strongly

## Config Changes

- Config count before apply: `34`
- Config count after apply: `43`
- Companies added:
  - Aviva Canada
  - Canada Life
  - Definity Financial (Economical)
  - iA Financial Group
  - Intact Financial
  - Manulife
  - Sun Life
  - The Co-operators
  - Wawanesa Insurance
- Companies skipped:
  - RSA Canada (Intact), because it remained `approved: false`
- Existing companies overwritten: `none`
- Backup created:
  - `config/companies.yaml.bak.20260605T205938Z`

## Expanded Pilot Run 1 Summary

Notes:

- The first `daily-run` completed successfully but slightly exceeded the original local command
  timeout window in Codex, so the final report landed shortly after the first command timeout.
- The run itself did complete and produced a full report.

Run 1 summary:

- Companies checked: `43`
- Jobs discovered: `410`
- Jobs scored: `406`
- Jobs relevant: `40`
- Jobs saved: `40`
- Jobs inserted: `10`
- Jobs updated: `19`
- Jobs unchanged: `11`
- Duplicates skipped before scoring: `4`
- Completed sources: `36`
- Paused sources: `5`
- Error sources: `2`
- Active pending interventions: `7`
- Errors reported: `3`

Newly added company outcomes in run 1:

- Aviva Canada: completed, no saved jobs
- Canada Life: completed, `8` relevant jobs, `3` inserted and `5` updated
- Definity Financial (Economical): completed, no saved jobs
- iA Financial Group: completed, no saved jobs
- Intact Financial: error
- Manulife: error
- Sun Life: completed, `5` relevant jobs, `3` inserted and `2` updated
- The Co-operators: completed, no saved jobs
- Wawanesa Insurance: paused with intervention

Database count:

- Job count before run 1: `72`
- Job count after run 1: `82`

## Expanded Pilot Run 2 Dedupe Summary

Run 2 summary:

- Companies checked: `43`
- Jobs discovered: `330`
- Jobs scored: `326`
- Jobs relevant: `35`
- Jobs saved: `35`
- Jobs inserted: `0`
- Jobs updated: `18`
- Jobs unchanged: `17`
- Duplicates skipped before scoring: `4`
- Completed sources: `36`
- Paused sources: `5`
- Error sources: `2`
- Active pending interventions: `7`
- Errors reported: `3`

Dedupe result:

- Job count after run 2: `82`
- New inserts on run 2: `0`
- Existing rows were updated or left unchanged
- No duplicate growth was observed across the two runs

Observed new-company persistence after run 2:

- Canada Life: `3` jobs in SQLite
- Sun Life: `3` jobs in SQLite
- Aviva Canada: `0`
- Definity Financial (Economical): `0`
- iA Financial Group: `0`
- Intact Financial: `0`
- Manulife: `0`
- The Co-operators: `0`
- Wawanesa Insurance: `0`

## New Source Readiness Outcomes

Completed successfully:

- Aviva Canada
- Canada Life
- Definity Financial (Economical)
- iA Financial Group
- Sun Life
- The Co-operators

Completed with no persisted jobs:

- Aviva Canada
- Definity Financial (Economical)
- iA Financial Group
- The Co-operators

Completed with persisted jobs:

- Canada Life
- Sun Life

Error:

- Intact Financial
- Manulife

Paused / needs human review:

- Wawanesa Insurance

## New Pending Interventions

Newly introduced by the expanded ready-list set:

- Wawanesa Insurance
  - `unclear_layout`
  - pending occurrence count after run 2: `2`
- Manulife
  - `extraction_failed`
  - pending occurrence count after run 2: `2`
- Intact Financial
  - `extraction_failed`
  - pending occurrence count after run 2: `2`

Pre-existing pending interventions still present:

- HCLTech: `cookie_blocked`
- NTT DATA: `login_required`
- Tech Mahindra: `login_required`
- Tech Mahindra: `extraction_failed`
- Wipro: `cookie_blocked`

## Bugs Found

- Intact Financial
  - browser fallback raised `Locator.inner_text: Error: Node is not an HTMLElement`
- Manulife
  - browser fallback attempted to navigate to `javascript:void(0)` and failed with
    `net::ERR_ABORTED`
- Wawanesa Insurance
  - static JSON-LD precheck failed due local SSL certificate verification on the jobs host

## Bugs Fixed

- No code fixes were applied in Task 10.4
- The task stayed focused on candidate review, safe apply, and expanded pilot validation

## Remaining Issues

- Browser fallback should avoid following non-navigable `javascript:void(0)` links
- Browser extraction should be more defensive before calling `inner_text()` on generic locators
- Static JSON-LD precheck should fail more gracefully when a public jobs host has certificate
  issues, instead of escalating to a source error/paused path too early
- The full expanded daily-run takes longer than the earlier 34-company pilot and needs a longer
  execution window in Codex than the initial 10-minute timeout

## Recommended Next Task

Harden the browser/static precheck path for the three new source issues found here:

1. Skip `javascript:` links during fallback navigation.
2. Make generic element text extraction safer for non-HTMLElement nodes.
3. Make static JSON-LD precheck degrade cleanly on SSL verification failures for public jobs
   hosts, so the collector can continue into the visible browser path when appropriate.

## Task 10.5 Hardening Rerun

Focused fixes applied:

- `src/browser/extraction.py`
  - added safe locator text/attribute helpers so non-HTMLElement nodes no longer abort source
    inspection
  - reject pseudo-links such as `javascript:void(0)`, `mailto:`, `tel:`, `data:`, and fragment
    links before browser navigation or job persistence
  - stop falling back to the page URL when a container exposes an explicit but non-actionable link
- `src/collectors/static_jsonld.py`
  - classify SSL certificate verification failures explicitly while still returning a recoverable
    precheck error for router fallback
- tests added for:
  - non-HTMLElement locator safety
  - pseudo-link rejection during navigation and extraction
  - SSL precheck fallback behavior

Verification:

- `.\.venv\Scripts\python.exe -m pytest` -> `204 passed`
- `.\.venv\Scripts\python.exe -m ruff check .` -> `All checks passed!`

Expanded rerun 1:

- Jobs discovered: `334`
- Jobs scored: `334`
- Jobs relevant: `34`
- Jobs saved: `34`
- Jobs inserted: `5`
- Jobs updated: `17`
- Jobs unchanged: `12`
- Interventions needed: `5`
- Errors: `1`
- Job count: `82 -> 87`

Expanded rerun 2:

- Jobs discovered: `354`
- Jobs scored: `354`
- Jobs relevant: `36`
- Jobs saved: `36`
- Jobs inserted: `3`
- Jobs updated: `17`
- Jobs unchanged: `16`
- Interventions needed: `5`
- Errors: `1`
- Job count: `87 -> 90`

Exact hardening outcomes:

- Intact Financial
  - no longer fails with `Locator.inner_text: Error: Node is not an HTMLElement`
  - source completed in both reruns
  - prior `extraction_failed` intervention is now `resolved`
  - latest source row: `completed`, `12` discovered, `1` unchanged, `last_error = none`
- Manulife
  - no longer attempts navigation to `javascript:void(0)`
  - source completed in both reruns
  - prior `extraction_failed` intervention is now `resolved`
  - latest source row: `completed`, `14` discovered, `1` unchanged, `last_error = none`
- Wawanesa Insurance
  - static JSON-LD SSL failure is now reported as a recoverable precheck error
  - browser fallback still runs and the source pauses on `unclear_layout` instead of crashing
  - latest source row: `paused`, `0` discovered, `last_error` records the SSL precheck failure

Remaining pending interventions after Task 10.5 rerun:

- Wawanesa Insurance: `unclear_layout`
- HCLTech: `cookie_blocked`
- NTT DATA: `login_required`
- Tech Mahindra: `login_required`
- Tech Mahindra: `extraction_failed`
- Wipro: `cookie_blocked`

Dedupe note:

- The rerun did not recreate the previous Intact or Manulife failure rows.
- Database growth on rerun 2 came from newly discovered distinct live job URLs rather than repeat
  insertion of the same Intact/Manulife records.

## Task 10.6 Result Quality Hardening

Focused quality fixes applied:

- strengthened post-extraction non-job rejection in `src/browser/extraction.py`
- rejected generic filter/category/navigation labels including:
  - `Filter Results`
  - `Search Results`
  - `View All Jobs`
  - `Careers Home`
  - `Manage Consent Preferences`
  - count/facet rows such as `Hybrid (2671)` and `Technology (42)`
  - category titles ending in patterns like `149 available jobs`
- tightened browser/static URL quality checks for generic index/category pages such as:
  - `/careers`
  - `/jobs`
  - `/search`
  - `/job-search`
  - `/job-search-results`
  - locale-prefixed equivalents such as `/en_ca/careers/job-search`
  - category-listing paths such as `/c/...-jobs`
- added suspicious-saved-row reporting in the daily Markdown report

Actionable-job filtering locations:

- browser/static extraction:
  - `src/browser/extraction.py`
  - `_normalize_actionable_url()`
  - `_best_link_from_container()`
  - `is_probable_job_listing()`
- daily-run persistence gate:
  - `src/reports/daily_run.py`
  - `is_actionable_job()`
  - `reject_non_actionable_new_jobs()`

New tests added:

- `Filter Results` rejected
- `Search Results` rejected
- `View All Jobs` rejected
- `Careers Home` rejected
- `Technology (42)` rejected
- generic `/careers` page with title `Careers` rejected
- generic `/job-search-results` page with title `Filter Results` rejected
- category-page title `Business & Customer Operations 149 available jobs` rejected
- `Infrastructure Analyst` with a real job URL allowed
- `Production Support Analyst` with a real job URL allowed
- `Cloud Engineer` with a real job URL allowed
- API job with `external_job_id` is not blocked by browser-only index-page URL heuristics
- daily report now includes `## Suspicious Saved Rows`

Verification:

- `.\.venv\Scripts\python.exe -m pytest` -> `205 passed`
- `.\.venv\Scripts\python.exe -m ruff check .` -> `All checks passed!`

Expanded rerun after quality hardening, run 1:

- Companies checked: `43`
- Jobs discovered: `312`
- Jobs scored: `312`
- Jobs relevant: `33`
- Jobs saved: `33`
- Jobs inserted: `2`
- Jobs updated: `17`
- Jobs unchanged: `14`
- Duplicates skipped before scoring: `0`
- Completed sources: `37`
- Paused sources: `5`
- Error sources: `1`
- DB count: `90 -> 92`
- Suspicious saved rows in report: `none`

Expanded rerun after quality hardening, run 2:

- Companies checked: `43`
- Jobs discovered: `332`
- Jobs scored: `332`
- Jobs relevant: `32`
- Jobs saved: `32`
- Jobs inserted: `0`
- Jobs updated: `17`
- Jobs unchanged: `15`
- Duplicates skipped before scoring: `0`
- Completed sources: `38`
- Paused sources: `5`
- Error sources: `0`
- DB count: `92 -> 92`
- Suspicious saved rows in report: `none`

False-positive rows verified and cleaned:

- `EY | Manage Consent Preferences | https://www.ey.com/en_ca/careers/job-search`
  - now marked `rejected`
- `Intact Financial | Filter Results | https://careers.intactfc.com/jobs`
  - now marked `rejected`
- `Manulife | Business & Customer Operations 149 available jobs | https://careers.manulife.com/global/en/c/business-customer-operations-jobs`
  - now marked `rejected`

Inserted-row analysis:

- The 3 rows inserted during Task 10.5 rerun 2 were legitimate distinct live job-detail URLs:
  - `BMO | Mortgage Specialist`
  - `IBM Consulting | Enterprise Operations Recruitment Coordinator (RPO) Professional`
  - `IBM Consulting | Software Engineering Application Developer-AWS Cloud FullStack Professional`
- The 2 rows inserted during Task 10.6 rerun 1 were also legitimate distinct IBM job-detail URLs:
  - `IBM Consulting | Enterprise Operations Process Associate Order Management - Health Care (Voice) Professional`
  - `IBM Consulting | Enterprise Operations Quote to Cash Professional-English Support Professional`
- None of the inserted rows were pseudo-links, index pages, category pages, or duplicate identities.
- The second Task 10.6 rerun inserted `0`, which confirms dedupe remained stable after the quality hardening.

Remaining paused/error sources after Task 10.6 rerun:

- Wawanesa Insurance: `paused`, `unclear_layout`
- HCLTech: `paused`, `cookie_blocked`
- NTT DATA: `paused`, `login_required`
- Tech Mahindra: `paused`, `login_required`
- Wipro: `paused`, `cookie_blocked`

Transient source note:

- National Bank of Canada timed out once during Task 10.6 rerun 1 and created a temporary
  `extraction_failed` intervention.
- The second rerun completed successfully for the source and the intervention moved into resolved
  history.

Recommendation for the next task:

1. Keep the collection/filtering logic as-is for Task 10.6.
2. Focus next on source-specific live-board quality for high-noise boards only if more false
   positives appear in future pilots.
3. Continue treating Wawanesa, HCLTech, NTT DATA, Tech Mahindra, and Wipro as manual/human-review
   operational follow-up rather than collector-architecture work.
