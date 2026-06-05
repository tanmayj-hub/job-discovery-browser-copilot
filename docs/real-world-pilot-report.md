# Real-World Pilot Report

## Verdict

**Partial pass.**

The MVP completed two full real-world runs against the existing 34 configured companies in [config/companies.yaml](/C:/projects/job-discovery-browser-copilot/config/companies.yaml). The pilot proved that the workflow can run end to end on the live watchlist, save relevant jobs, generate exports, populate source readiness, and keep intervention dedupe stable for repeated unresolved issues.

It is not yet stable enough to call production-ready because:

- 2 live sources failed outright
- 3 live sources paused for manual intervention
- a few non-job or low-quality results still slipped through extraction/scoring
- 2 reporting/readiness bugs were found during the pilot and fixed afterward

## Environment

- Date tested: June 5, 2026
- Python: `3.12.10`
- OS: `Windows-11-10.0.26200-SP0`
- Branch: `task1-collect-first-score-later`
- Commands run:
  - `.\.venv\Scripts\python.exe -m pytest`
  - `.\.venv\Scripts\python.exe -m ruff check .`
  - `.\.venv\Scripts\python.exe -m src.main daily-run`
  - `.\.venv\Scripts\python.exe -m src.main daily-run`
  - `Invoke-WebRequest http://localhost:8501`

## Config Summary

### Main Watchlist

| Metric | Value |
| --- | ---: |
| Total companies/sources | 34 |
| URLs present | 34 |
| URLs missing | 0 |
| `browser_allowed` | 30 |
| `human_in_loop` | 4 |
| ATS `none` | 30 |
| ATS `workday` | 3 |
| ATS `ultipro` | 1 |
| `routing.api_fallback_to_browser` | disabled |
| `keyword_fallback.enabled` | disabled |

### Location Scope

- Canada
- Toronto
- Ontario
- Remote Canada
- Remote

### Pre-Run Database / Exports Baseline

| Metric | Value |
| --- | ---: |
| Existing DB file | `data/job_discovery.db` present |
| Jobs before run 1 | 13 |
| Total interventions before run 1 | 13 |
| Pending interventions before run 1 | 0 |
| Existing export files | `daily-report-2026-06-02.md`, `jobs-2026-06-02.csv` |

Note:

- The existing DB was from an older local run and did not yet have `sources.last_status` until the app migration path ran on startup. The normal app initialization handled that safely.

## Run Summary

### Run 1

CLI output:

```python
{'run_date': '2026-06-05', 'companies_checked': 34, 'companies_skipped': 0, 'jobs_discovered': 390, 'jobs_scored': 386, 'jobs_relevant': 42, 'jobs_saved': 42, 'location_scope_used': False, 'keyword_scope_used': False, 'report_path': 'C:\\projects\\job-discovery-browser-copilot\\data\\exports\\daily-report-2026-06-05.md', 'csv_path': 'C:\\projects\\job-discovery-browser-copilot\\data\\exports\\jobs-2026-06-05.csv'}
```

Observed storage/report outcomes:

| Metric | Value |
| --- | ---: |
| Companies checked | 34 |
| Companies skipped | 0 |
| Jobs discovered | 390 |
| Jobs scored | 386 |
| Jobs relevant | 42 |
| Jobs saved | 42 |
| Jobs inserted | 36 |
| Jobs updated | 6 |
| Jobs unchanged | 0 |
| Duplicates skipped | 4 |
| Jobs in DB after run 1 | 49 |
| Total interventions after run 1 | 19 |
| Pending interventions after run 1 | 6 |
| Source statuses | 28 completed / 4 paused / 2 error |

### Run 2

CLI output:

```python
{'run_date': '2026-06-05', 'companies_checked': 34, 'companies_skipped': 0, 'jobs_discovered': 390, 'jobs_scored': 386, 'jobs_relevant': 40, 'jobs_saved': 40, 'location_scope_used': False, 'keyword_scope_used': False, 'report_path': 'C:\\projects\\job-discovery-browser-copilot\\data\\exports\\daily-report-2026-06-05.md', 'csv_path': 'C:\\projects\\job-discovery-browser-copilot\\data\\exports\\jobs-2026-06-05.csv'}
```

Observed storage/report outcomes:

| Metric | Value |
| --- | ---: |
| Companies checked | 34 |
| Companies skipped | 0 |
| Jobs discovered | 390 |
| Jobs scored | 386 |
| Jobs relevant | 40 |
| Jobs saved | 40 |
| Jobs inserted | 0 |
| Jobs updated | 13 |
| Jobs unchanged | 27 |
| Duplicates skipped | 4 |
| Jobs in DB after run 2 | 49 |
| Total interventions after run 2 | 20 |
| Pending interventions after run 2 | 7 |
| Source statuses | 29 completed / 3 paused / 2 error |
| Duplicate identity count | 0 |

### Dedupe / Intervention Interpretation

- Job dedupe worked:
  - 13 jobs before run 1
  - 49 jobs after run 1
  - 49 jobs after run 2
  - duplicate identity count stayed at `0`
- Repeated unresolved interventions did **not** duplicate for the same logical issue after Task 8.1
- The pending intervention count increased from `6` to `7` on run 2 because **Tech Mahindra** surfaced a different blocker on run 2:
  - first pending reason: `login_required`
  - second pending reason: `extraction_failed`
- That behavior is expected under the current logical identity because the reason changed

### Real-World Outcome Summary

| Category | Count |
| --- | ---: |
| Sources that saved relevant jobs | 16 |
| Sources that completed with jobs but saved none | 13 |
| Sources paused for intervention | 3 |
| Sources failed | 2 |

## Source Readiness Table

| Company | URL | Source Mode | ATS Type | Collector | Status | Fallback Used | Intervention Required | Jobs Discovered | Jobs Relevant | Jobs Saved | Inserted | Updated | Unchanged | Last Error | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| ATB Financial | https://careers.atb.com/ | browser_allowed | - | browser_after_jsonld | completed | yes | no | 20 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| Accenture | https://www.accenture.com/ca-en/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 17 | 2 | 2 | 0 | 0 | 2 | - | Saved relevant jobs |
| BMO | https://jobs.bmo.com/global/en/home | browser_allowed | - | browser_after_jsonld | completed | yes | no | 12 | 2 | 2 | 0 | 0 | 2 | - | Saved relevant jobs |
| CGI | https://www.cgi.com/canada/en-ca/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 20 | 6 | 6 | 0 | 0 | 6 | - | Saved relevant jobs |
| CIBC | https://www.cibc.com/en/about-cibc/careers.html | human_in_loop | workday | browser | completed | no | no | 97 | 2 | 2 | 0 | 2 | 0 | - | Saved relevant jobs |
| Capgemini | https://careers.capgemini.com/?locale=en_US | browser_allowed | - | browser_after_jsonld | completed | yes | no | 1 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| Cognizant | https://careers.cognizant.com/ca-en/ | browser_allowed | - | browser_after_jsonld | completed | yes | no | 9 | 2 | 2 | 0 | 0 | 2 | - | Saved relevant jobs |
| DXC Technology | https://careers.dxc.com/global/en/home | browser_allowed | - | browser_after_jsonld | completed | yes | no | 0 | 0 | 0 | 0 | 0 | 0 | Static JSON-LD precheck failed: Static JSON-LD request failed: HTTP Error 404: Not Found | Completed with no visible jobs |
| Deloitte | https://www.deloitte.com/ca/en/careers.html | browser_allowed | - | browser_after_jsonld | completed | yes | no | 3 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| Desjardins | https://www.desjardins.com/en/careers.html | browser_allowed | - | browser_after_jsonld | completed | yes | no | 7 | 1 | 1 | 0 | 0 | 1 | - | Saved relevant jobs |
| EQ Bank (Equitable Bank) | https://www.eqbank.ca/about-us/about/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 1 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| EY | https://www.ey.com/en_ca/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 10 | 2 | 2 | 0 | 0 | 2 | - | Saved relevant jobs |
| Genpact | https://www.genpact.com/careers/job-search | browser_allowed | - | browser_after_jsonld | completed | yes | no | 40 | 9 | 9 | 0 | 9 | 0 | - | Saved relevant jobs |
| HCLTech | https://www.hcltech.com/careers | browser_allowed | - | browser_after_jsonld | paused | yes | yes | 0 | 0 | 0 | 0 | 0 | 0 | - | Pending manual intervention |
| IBM Consulting | https://www.ibm.com/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 20 | 4 | 4 | 0 | 0 | 4 | - | Saved relevant jobs |
| Infosys | https://careers.infosys.com/ | browser_allowed | - | browser_after_jsonld | completed | yes | no | 3 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| KPMG | https://kpmg.com/ca/en/careers.html | browser_allowed | - | browser_after_jsonld | completed | yes | no | 2 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| Kyndryl | https://www.kyndryl.com/us/en/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 7 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| Laurentian Bank | https://www.laurentianbank.ca/en/about-us/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 1 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| NTT DATA | https://ca.nttdata.com/en/careers | browser_allowed | - | browser_after_jsonld | paused | yes | yes | 0 | 0 | 0 | 0 | 0 | 0 | - | Pending manual intervention |
| National Bank of Canada | https://emplois.bnc.ca/en_CA/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 20 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| PwC | https://jobs-ca.pwc.com/ca/en/home | browser_allowed | - | browser_after_jsonld | completed | yes | no | 14 | 1 | 1 | 0 | 0 | 1 | - | Saved relevant jobs |
| RBC | https://jobs.rbc.com/en | browser_allowed | - | browser_after_jsonld | completed | yes | no | 12 | 1 | 1 | 0 | 0 | 1 | - | Saved relevant jobs |
| Scotiabank | https://www.scotiabank.com/careers/en/careers.html | browser_allowed | - | browser_after_jsonld | completed | yes | no | 16 | 1 | 1 | 0 | 0 | 1 | - | Saved relevant jobs |
| Slalom | https://www.slalom.com/us/en/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 6 | 1 | 1 | 0 | 0 | 1 | - | Saved relevant jobs |
| TD | https://careers.td.com/ | human_in_loop | workday | browser | completed | no | no | 20 | 1 | 1 | 0 | 0 | 1 | - | Saved relevant jobs |
| TMX Group | https://www.tmx.com/careers | human_in_loop | workday | browser | completed | no | no | 5 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| Tangerine | https://www.tangerine.ca/en/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 2 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |
| Tata Consultancy Services (TCS) | https://www.tcs.com/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 4 | 1 | 1 | 0 | 0 | 1 | - | Saved relevant jobs |
| Tech Mahindra | https://careers.techmahindra.com/ | browser_allowed | - | browser_after_jsonld | error | yes | no | 0 | 0 | 0 | 0 | 0 | 0 | Page.goto: Timeout 15000ms exceeded. Call log: - navigating to "https://careers.techmahindra.com/", waiting until "load" | Source failed during live pilot |
| Thoughtworks | https://www.thoughtworks.com/en-ca/careers | browser_allowed | - | browser_after_jsonld | completed | yes | no | 20 | 4 | 4 | 0 | 2 | 2 | - | Saved relevant jobs |
| Vancity | https://jobs.vancity.com/ | human_in_loop | ultipro | browser | error | no | no | 0 | 0 | 0 | 0 | 0 | 0 | Page.goto: net::ERR_NAME_NOT_RESOLVED at https://jobs.vancity.com/ Call log: - navigating to "https://jobs.vancity.com/", waiting until "load" | Source failed during live pilot |
| Wipro | https://careers.wipro.com/?locale=en_US | browser_allowed | - | browser_after_jsonld | paused | yes | yes | 0 | 0 | 0 | 0 | 0 | 0 | - | Pending manual intervention |
| Ateko | https://ateko.com/en/careers/ | browser_allowed | - | browser_after_jsonld | completed | yes | no | 1 | 0 | 0 | 0 | 0 | 0 | - | Collected jobs but none saved |

## Dashboard Verification

### What Worked

- The Streamlit dashboard endpoint responded successfully:
  - `Invoke-WebRequest http://localhost:8501` -> HTTP `200`
- Live dashboard data functions loaded without crashing:
  - overview metrics
  - jobs list
  - intervention queue
  - source readiness rows
  - source readiness filters
- Current live data checks:
  - `jobs_count=49`
  - `interventions_count=20`
  - `source_rows_count=34`
  - `prepared_rows_count=34`
  - `filtered_rows_count=26`
- Source readiness columns present:
  - `Company`
  - `Source URL`
  - `Source Mode`
  - `ATS Type`
  - `Collector`
  - `Status`
  - `Readiness`
  - `Fallback Used`
  - `Intervention Required`
  - `Jobs Discovered`
  - `Jobs Relevant`
  - `Jobs Saved`
  - `Jobs Inserted`
  - `Jobs Updated`
  - `Jobs Unchanged`
  - `Duplicates Skipped`
  - `Last Error`
  - `Last Success`
  - `Consecutive Failures`
- Exports were generated in [data/exports](/C:/projects/job-discovery-browser-copilot/data/exports)

### What Was Limited

- I verified the live endpoint and data plumbing, but not every visual interaction manually through a browser automation tool
- The raw Streamlit HTML shell did not include the app title string in the first HTTP response, so the endpoint check was best treated as availability verification, not full DOM verification

## Bugs Found

### 1. Successful `human_in_loop` sources were labeled `needs_human`

- Severity: medium
- Affected sources: TD, CIBC, TMX Group
- File/area: [src/reports/source_observability.py](/C:/projects/job-discovery-browser-copilot/src/reports/source_observability.py), [src/storage/db.py](/C:/projects/job-discovery-browser-copilot/src/storage/db.py)
- Reproduction:
  - Run a successful `human_in_loop` source that completes without intervention
- Expected:
  - readiness should reflect successful browser completion
- Actual:
  - readiness stayed `needs_human`
- Suggested fix:
  - only return `needs_human` for paused/intervention-required cases

### 2. Daily-run summary dropped `location_scope_used`

- Severity: medium
- Affected sources: at least some browser sources that used location queries during the pilot
- File/area: [src/collectors/base.py](/C:/projects/job-discovery-browser-copilot/src/collectors/base.py), [src/collectors/router.py](/C:/projects/job-discovery-browser-copilot/src/collectors/router.py)
- Reproduction:
  - run a browser source that uses location-scope search to reveal jobs
- Expected:
  - daily-run summary should report `location_scope_used=True`
- Actual:
  - per-source run notes showed location queries, but top-level run output still reported `False`
- Suggested fix:
  - preserve the boolean through `CollectorResult`

### 3. Non-job content can still survive extraction/scoring

- Severity: medium
- Affected examples:
  - Scotiabank `Helping drive equality for every future`
  - Desjardins `Why work at Desjardins?`
  - IBM Consulting `Hybrid (2671)`
  - Accenture relevant result with `no URL`
- File/area: browser extraction and post-extraction filtering
- Reproduction:
  - run the real pilot and inspect top matched jobs / saved jobs
- Expected:
  - only real job postings with usable titles/URLs should survive
- Actual:
  - some marketing/generic/navigation-like content still reached scoring
- Suggested fix:
  - tighten job-card filtering and require stronger job-like signals before save/report

### 4. Vancity source is not reachable with the configured URL

- Severity: medium
- Affected source: Vancity
- File/area: config/source data
- Reproduction:
  - run the pilot against `https://jobs.vancity.com/`
- Expected:
  - source should load or redirect to a valid public careers endpoint
- Actual:
  - `Page.goto: net::ERR_NAME_NOT_RESOLVED`
- Suggested fix:
  - validate and update the configured careers URL

## Bugs Fixed During Task 9

### 1. Fixed readiness labeling for successful human-in-loop sources

- Files changed:
  - [src/reports/source_observability.py](/C:/projects/job-discovery-browser-copilot/src/reports/source_observability.py)
  - [src/storage/db.py](/C:/projects/job-discovery-browser-copilot/src/storage/db.py)
  - [tests/test_source_observability.py](/C:/projects/job-discovery-browser-copilot/tests/test_source_observability.py)
- Result:
  - TD, CIBC, and TMX Group now read as `ready_browser` when completed successfully

### 2. Fixed routing pass-through for `location_scope_used`

- Files changed:
  - [src/collectors/base.py](/C:/projects/job-discovery-browser-copilot/src/collectors/base.py)
  - [src/collectors/router.py](/C:/projects/job-discovery-browser-copilot/src/collectors/router.py)
  - [tests/test_collector_router.py](/C:/projects/job-discovery-browser-copilot/tests/test_collector_router.py)
  - [tests/test_daily_run.py](/C:/projects/job-discovery-browser-copilot/tests/test_daily_run.py)
- Result:
  - daily-run can now preserve location-scope usage from browser collector results instead of silently dropping it

## Verification After Fixes

- `pytest` -> `145 passed`
- `ruff check .` -> `All checks passed!`

## Remaining Blockers

- Extraction quality still needs tightening before the pilot can be called stable
- One live configured source appears invalid or offline (`Vancity`)
- Two more live sources remain unstable in practice:
  - `Tech Mahindra`
  - `DXC Technology` still completed on run 2 with a carried precheck error note and zero discovered jobs, which deserves manual validation before relying on it

## Recommended Next Step

**Bug-fix pass before company onboarding.**

Recommended order:

1. Tighten browser extraction to reduce non-job false positives and URL-less saves.
2. Validate or replace failing careers URLs, starting with Vancity.
3. Re-run the 34-company pilot once those fixes land, then decide whether the watchlist is stable enough for company-onboarding expansion.

## Task 9.1 Bug-Fix Pass

### Scope

This pass addressed only the pilot hardening issues identified above:

- non-job content surviving extraction/scoring
- URL-less browser results being saved
- stale/invalid source URLs not taking effect from YAML
- Tech Mahindra timing out too aggressively
- stale pending interventions remaining open after a source later completed

### Code Changes Landed

- Added stronger actionable-job filtering in [src/browser/extraction.py](/C:/projects/job-discovery-browser-copilot/src/browser/extraction.py):
  - rejects off-domain marketing/article links
  - rejects generic careers landing titles such as `TD Careers`
  - rejects evergreen/culture titles such as `Why work at ...`, `Living Wage employers`, `Demanding more values.`
  - rejects non-HTTP pseudo-links such as `javascript:void(0)`
  - requires either a real job-like URL/external identity or a role-like title with job context
- Applied the same actionable-job guard before saving in:
  - [src/collectors/browser_collector.py](/C:/projects/job-discovery-browser-copilot/src/collectors/browser_collector.py)
  - [src/reports/daily_run.py](/C:/projects/job-discovery-browser-copilot/src/reports/daily_run.py)
- Added cleanup in [src/reports/daily_run.py](/C:/projects/job-discovery-browser-copilot/src/reports/daily_run.py) to mark previously saved non-actionable `new` rows as `rejected`
- Fixed YAML-vs-DB source precedence in [src/reports/daily_run.py](/C:/projects/job-discovery-browser-copilot/src/reports/daily_run.py) so a populated config URL overrides a stale SQLite URL
- Added pending-intervention auto-resolution for successful reruns in [src/storage/db.py](/C:/projects/job-discovery-browser-copilot/src/storage/db.py)
- Added a targeted navigation timeout bump for Tech Mahindra in [src/collectors/browser_collector.py](/C:/projects/job-discovery-browser-copilot/src/collectors/browser_collector.py)

### Source Config Corrections

- Vancity:
  - old: `https://jobs.vancity.com/`
  - new: `https://www.vancity.com/careers`
- DXC Technology:
  - old: `https://careers.dxc.com/global/en/home`
  - new: `https://careers.dxc.com/job-search-results/`

These corrections are in [config/companies.yaml](/C:/projects/job-discovery-browser-copilot/config/companies.yaml) and now survive daily-run classification because config values win over stale DB values when present.

### Regression Coverage Added

- [tests/test_browser_extraction.py](/C:/projects/job-discovery-browser-copilot/tests/test_browser_extraction.py)
  - rejects Scotiabank/Desjardins/IBM/Vancity-style marketing/facet noise
  - rejects URL-less browser rows
  - allows external-identity API/structured rows
- [tests/test_daily_run.py](/C:/projects/job-discovery-browser-copilot/tests/test_daily_run.py)
  - prefers non-empty YAML careers URLs over stale DB URLs
  - rejects previously saved non-actionable `new` rows during daily-run cleanup
- [tests/test_storage.py](/C:/projects/job-discovery-browser-copilot/tests/test_storage.py)
  - resolves pending interventions for a company after a successful rerun
- [tests/test_browser_collection.py](/C:/projects/job-discovery-browser-copilot/tests/test_browser_collection.py)
  - verifies the Tech Mahindra timeout extension

### Verification

- `pytest` -> `153 passed`
- `ruff check .` -> `All checks passed!`

### Final Live Rerun

Command:

```python
.\.venv\Scripts\python.exe -m src.main daily-run
```

Observed summary from the final rerun on June 5, 2026:

- companies checked: `34`
- companies skipped: `0`
- jobs discovered: `262`
- jobs scored: `258`
- jobs relevant: `33`
- jobs saved: `33`
- jobs inserted: `0`
- jobs updated: `11`
- jobs unchanged: `22`
- duplicates skipped: `4`
- location scope used: `True`
- keyword scope used: `False`
- source errors: `0`
- source statuses: `30 completed / 4 paused / 0 error`
- active pending interventions after rerun: `5`

### Outcome By Reported Issue

1. Non-job/marketing/navigation content:
   - fixed for the originally reported cases
   - confirmed rejected in local DB:
     - Scotiabank `Helping drive equality for every future`
     - Desjardins `Why work at Desjardins?`
     - IBM Consulting `Hybrid (2671)`
     - IBM marketing/support pages
     - Vancity `Demanding more values.`
     - TD `TD Careers`

2. URL-less saved browser result:
   - fixed
   - the Accenture no-URL row is now `rejected`

3. Vancity invalid source URL:
   - fixed
   - final rerun status: `completed`
   - final rerun result: `1 discovered / 0 saved`

4. DXC source validation:
   - improved
   - final rerun status: `completed`
   - final rerun result: `0 discovered / 0 saved`
   - stale pending extraction intervention was resolved

5. Tech Mahindra instability:
   - improved but not fully solved
   - final rerun status: `paused`, not a hard error
   - active blockers still remain (`login_required`, `extraction_failed`)

### Remaining Issues After Task 9.1

- Tech Mahindra still requires manual handling and is not yet stable
- NTT DATA, HCLTech, and Wipro still pause for manual intervention
- The intervention queue still shows resolved historical rows alongside pending ones; active pending items are now `5`
- Some saved jobs can still be outside Canada if the source exposes them on public boards and they pass the deterministic score

### Task 9.1 Verdict

**Substantially complete.**

The targeted bug-fix pass removed the specific false positives that triggered this work, stopped URL-less browser saves, made YAML source corrections take effect, recovered Vancity from a dead URL, normalized DXC to a non-error completed state, and downgraded Tech Mahindra from a hard failure to a paused/manual issue.

## Task 9.2 Operational Hardening

Task 9.2 addressed the remaining intervention-queue usability gap without changing collectors or routing policy.

Results:

- active pending blockers are now separated from resolved/manual history
- repeated same-source pending issues collapse into one active queue item with an `occurrence_count`
- source readiness now surfaces:
  - pending intervention count
  - resolved history count
  - latest pending reason
  - remediation label
  - suggested action

Current post-hardening local snapshot:

- active pending source blockers: `4`
- resolved/manual history rows: `15`
- Tech Mahindra now appears as one active pending source instead of two separate rows

See [docs/source-remediation-report.md](/C:/projects/job-discovery-browser-copilot/docs/source-remediation-report.md) for the current remediation summary.
