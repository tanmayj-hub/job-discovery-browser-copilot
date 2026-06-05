# Smoke Test Report

## Summary Verdict

**Pass after one low-risk blocker fix.**

The MVP completed controlled end-to-end smoke testing across all major Task 8 paths on **June 5, 2026** using a safe fixture config at [tests/fixtures/smoke/companies.yaml](/C:/projects/job-discovery-browser-copilot/tests/fixtures/smoke/companies.yaml). The only blocker found during the first pass was ATS-backed job deduplication collapsing distinct jobs that shared the same `company_name + title + location + source_name`. That was fixed in [src/storage/db.py](/C:/projects/job-discovery-browser-copilot/src/storage/db.py), covered by a regression test in [tests/test_storage.py](/C:/projects/job-discovery-browser-copilot/tests/test_storage.py), and the smoke run was repeated successfully.

## Environment

- Date tested: June 5, 2026
- Timestamp captured: `2026-06-05T14:53:35+00:00`
- Python: `3.12.10`
- Platform: `Windows-11-10.0.26200-SP0`
- Commands run:
  - `.\.venv\Scripts\python.exe -m pytest`
  - `.\.venv\Scripts\python.exe -m ruff check .`
  - smoke daily-run via `reports.daily_run.run_daily_workflow` against [tests/fixtures/smoke/companies.yaml](/C:/projects/job-discovery-browser-copilot/tests/fixtures/smoke/companies.yaml)

## Config Summary

### Main Config

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

### Controlled Smoke Config

| Metric | Value |
| --- | ---: |
| Total sources | 9 |
| URLs present | 8 |
| URLs missing | 1 |
| `api_allowed` | 4 |
| `browser_allowed` | 2 |
| `human_in_loop` | 1 |
| `manual_only` | 1 |
| `needs_url` | 1 |

Smoke ATS counts:

- `greenhouse`: 1
- `lever`: 1
- `ashby`: 1
- `smartrecruiters`: 1
- `workday`: 1
- `restricted_board`: 1
- `none`: 3

## Test Matrix

| Path | Company/source | URL | Expected behavior | Actual behavior | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Greenhouse API | Stripe Smoke | `https://boards.greenhouse.io/stripe` | API collection, no browser | `greenhouse_api`, `success`, 483 discovered, 246 relevant | Pass | `external_job_id`, `ats_type`, and `board_slug` persisted |
| Lever API | Veeva Smoke | `https://jobs.lever.co/veeva` | API collection, no browser | `lever_api`, `success`, 1025 discovered, 647 relevant | Pass | `external_job_id`, `ats_type`, and `board_slug` persisted |
| Ashby API | Notion Smoke | `https://jobs.ashbyhq.com/notion` | API collection, no browser | `ashby_api`, `success`, 144 discovered, 66 relevant | Pass | `external_job_id`, `ats_type`, and `board_slug` persisted |
| Static JSON-LD | Static JSONLD Smoke | `http://127.0.0.1:8765/jsonld_table_page1.html` | JSON-LD collected before browser | `static_jsonld`, `success`, 1 discovered, 1 relevant | Pass | No browser fallback used |
| Browser fallback | Browser Fallback Smoke | `http://127.0.0.1:8765/anchors_cards.html` | JSON-LD precheck then browser fallback | `browser_after_jsonld`, `completed`, 2 discovered, 2 relevant | Pass | `fallback_used=True` |
| Human in loop | Human In Loop Smoke | `http://127.0.0.1:8765/human_in_loop_location_gate.html` | Pause and record intervention | `browser`, `paused`, intervention recorded | Pass | Safe stop on location gate |
| Manual only | Manual Only Smoke | `https://www.linkedin.com/jobs/view/example` | Classify and skip without automation | `manual_only`, no jobs collected | Pass | Not treated as crawler failure |
| Needs URL | Needs URL Smoke | blank | Classify as `needs_url`, no automation | `needs_url`, no jobs collected | Pass | Visible in source readiness |
| API not implemented | SmartRecruiters Smoke | `https://jobs.smartrecruiters.com/Example/example` | Detect ATS and report not implemented | `api_not_implemented`, no browser fallback | Pass | Correctly not treated as success |

## Run Metrics

### First Run

| Metric | Value |
| --- | ---: |
| Jobs discovered | 1655 |
| Jobs scored | 1655 |
| Jobs relevant | 962 |
| Jobs saved | 962 |
| Jobs inserted | 962 |
| Jobs updated | 0 |
| Jobs unchanged | 0 |
| Duplicates skipped | 0 |
| Interventions required | 1 |
| Errors | 0 |
| Rows in DB after run | 962 |

### Second Run

| Metric | Value |
| --- | ---: |
| Jobs discovered | 1655 |
| Jobs scored | 1655 |
| Jobs relevant | 962 |
| Jobs saved | 962 |
| Jobs inserted | 0 |
| Jobs updated | 0 |
| Jobs unchanged | 962 |
| Duplicates skipped | 0 |
| Interventions required | 2 |
| Errors | 0 |
| Rows in DB after run | 962 |

Generated artifacts were successfully written during smoke testing:

- Markdown report: `%TEMP%\job-discovery-browser-copilot-task8-smoke\exports\daily-report-2026-06-05.md`
- CSV export: `%TEMP%\job-discovery-browser-copilot-task8-smoke\exports\jobs-2026-06-05.csv`

## Collector Results

### Greenhouse

- Routed to API collector
- No browser used
- 483 jobs discovered
- 246 jobs scored as relevant and saved
- ATS identity metadata persisted correctly

### Lever

- Routed to API collector
- No browser used
- 1025 jobs discovered
- 647 jobs scored as relevant and saved
- ATS identity metadata persisted correctly

### Ashby

- Routed to API collector
- No browser used
- 144 jobs discovered
- 66 jobs scored as relevant and saved
- ATS identity metadata persisted correctly

### Static JSON-LD

- JSON-LD collector ran before browser
- 1 `JobPosting` item was collected directly
- Browser fallback was not needed

### Browser Fallback

- Static JSON-LD precheck returned no jobs
- Browser collector completed successfully
- 2 jobs were extracted and saved
- `fallback_used` surfaced correctly in source readiness data

### Human In Loop

- Browser path paused on a location-selection gate
- Intervention was recorded instead of forcing progress
- No CAPTCHA, login bypass, or stealth behavior was attempted

### Manual Only

- Restricted board classified as `manual_only`
- No automation attempted
- Correctly surfaced as a safe skip instead of an error

### Needs URL

- Missing URL classified as `needs_url`
- No automation attempted
- Correctly surfaced in source readiness data

### API Not Implemented

- SmartRecruiters detected correctly
- Returned `api_collector_not_implemented`
- No browser fallback used because `routing.api_fallback_to_browser` is disabled

## Scoring Verification

- Collection happened before scoring across all tested routes
- `keyword_scope_used` remained `False`
- `location_scope_used` remained `False` for this smoke set
- Role/skill keywords were not used before extraction
- Discovered/scored/relevant/saved counts were internally consistent:
  - 1655 discovered
  - 1655 scored
  - 962 relevant
  - 962 saved
- Low-score jobs did not break the run; they were simply excluded from the saved relevant set

## Dedupe Results

Storage and dedupe behavior were verified by running the same smoke set twice.

| Check | Result |
| --- | --- |
| Total rows after first run | 962 |
| Total rows after second run | 962 |
| Unique identity rows after second run | 962 |
| Duplicate identity rows after second run | 0 |
| `first_seen_at` changed across rerun | 0 rows |
| `last_seen_at` changed across rerun | 962 rows |
| `last_updated_at` changed for unchanged rows | 0 rows |
| `content_hash` changed for unchanged rows | 0 rows |

Result:

- `external_job_id`-based identities for Greenhouse, Lever, and Ashby were stable
- duplicate row creation was eliminated after the storage fix
- unchanged jobs correctly advanced `last_seen_at` while preserving `first_seen_at` and `content_hash`

## Dashboard And Reporting Verification

I did not rely on a live manual Streamlit walkthrough for Task 8. Instead, I verified the dashboard data pipeline directly against the smoke database:

- [src/storage/db.py](/C:/projects/job-discovery-browser-copilot/src/storage/db.py) `get_source_status_rows()`
- [src/dashboard/source_status.py](/C:/projects/job-discovery-browser-copilot/src/dashboard/source_status.py) `prepare_source_status_rows()`
- [src/dashboard/source_status.py](/C:/projects/job-discovery-browser-copilot/src/dashboard/source_status.py) `filter_source_status_items()`

Verified fields:

- Source Readiness table rows present: 9
- Prepared dashboard rows present: 9
- Filters executed without crashing
- Columns present:
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

The generated daily Markdown report also rendered the expected routing summary, top matched jobs, source outcomes, skipped sources, interventions, and zero-error status.

## Bugs Found

### 1. ATS-backed jobs could collapse under weak fallback identity

- Severity: blocker
- Area: [src/storage/db.py](/C:/projects/job-discovery-browser-copilot/src/storage/db.py)
- Reproduction:
  - Save two ATS jobs from the same company with the same title, location, and source name.
  - Give them different `external_job_id` values and different ATS job URLs.
- Expected:
  - Two distinct rows should remain because ATS identity is stronger than the fallback text identity.
- Actual before fix:
  - The second job updated the first row because lookup still tried `company_title_location_source`.
- Fix applied:
  - `_build_identity_candidates()` now only adds the weak fallback identity for URL-based or fallback-based jobs, not for ATS jobs that already have stronger identities.
- Verification:
  - Added regression coverage in [tests/test_storage.py](/C:/projects/job-discovery-browser-copilot/tests/test_storage.py)
  - Re-ran smoke workflow twice with 962 stable rows and 0 duplicate identities

### 2. Re-running the same paused source creates another pending intervention row

- Severity: low
- Area: intervention recording path during repeated paused browser runs
- Reproduction:
  - Run the same human-in-loop source twice without resolving the first intervention.
- Expected:
  - Either deduplicate the open intervention or update the existing one.
- Actual:
  - The second smoke run produced a second pending intervention for the same source.
- Suggested fix:
  - Before inserting a new intervention, check for an unresolved intervention with the same `company_name`, `reason`, and `source_url`

## Fixes Made During Task 8

- Updated ATS-backed job lookup in [src/storage/db.py](/C:/projects/job-discovery-browser-copilot/src/storage/db.py)
- Added regression coverage for same-title/different-`external_job_id` API jobs in [tests/test_storage.py](/C:/projects/job-discovery-browser-copilot/tests/test_storage.py)
- Added a safe human-in-loop fixture at [tests/fixtures/browser/human_in_loop_location_gate.html](/C:/projects/job-discovery-browser-copilot/tests/fixtures/browser/human_in_loop_location_gate.html)
- Added a controlled smoke config at [tests/fixtures/smoke/companies.yaml](/C:/projects/job-discovery-browser-copilot/tests/fixtures/smoke/companies.yaml)

## Verification Results

- `pytest`: `141 passed`
- `ruff`: `All checks passed!`

## Recommended Next Steps

1. Fix low-risk intervention deduplication before adding more collection breadth.
2. Keep the ATS identity regression test in place as protection for future collector work.
3. Start new feature work only from this smoke-tested baseline.
