# Job Discovery Browser Co-Pilot

Human-in-the-loop job discovery for Canadian banks and IT consulting companies.

## Project Overview

Job Discovery Browser Co-Pilot helps organize career-page monitoring without drifting into unsafe automation. It combines a local Streamlit dashboard, SQLite storage, deterministic scoring, and browser-assisted collection so you can review relevant roles, track blocked sources, and export results for manual follow-up.

## Problem Solved

Job searching across dozens of company career pages is repetitive, fragmented, and easy to lose track of. This project creates one local workflow for:

- maintaining a company watchlist
- tracking which sources are ready, blocked, or missing URLs
- collecting public job postings from allowed sources
- scoring Cloud, DevOps, Platform, Admin, and Support roles
- queueing human interventions when a site needs manual review
- exporting a daily summary and CSV for follow-up

The app also distinguishes between detected source type and allowed operating mode. It can identify ATS families such as Greenhouse, Lever, Ashby, SmartRecruiters, Workday, SuccessFactors, Oracle HCM, ICIMS, and Phenom, then map them into the current local safety modes without adding collectors prematurely.

The current routing layer also makes source handling explicit: browser-safe sources first try a static JSON-LD precheck before the visible browser collector, manual-only sources are never automated, Greenhouse, Lever, and Ashby use public ATS APIs, and SmartRecruiters remains intentionally unimplemented unless an explicit browser fallback is enabled.

SQLite storage now also preserves stable ATS metadata for API-collected and static JSON-LD jobs. Greenhouse, Lever, and Ashby jobs carry `external_job_id`, `ats_type`, `board_slug`, `content_hash`, and first/last-seen timestamps so repeated runs can update the same row instead of creating duplicates.

The dashboard now also surfaces source-level readiness and collector visibility. Each company source can show the latest route used, status, fallback behavior, intervention requirement, discovered/scored/relevant/saved counts, storage outcomes, last error, and remediation guidance so manual follow-up stays clear.

## Safety And Compliance Note

This project is intentionally limited to safe, visible, human-in-the-loop discovery.

- No auto-apply workflows
- No CAPTCHA bypass
- No proxy rotation
- No stealth scraping or bot evasion
- No LinkedIn or Indeed automation
- Restricted or ambiguous sources should be handled in manual-only mode

## Discovery Policy

The MVP uses a collect-first, score-later strategy for company career pages.

- Use company career pages as the source of truth.
- Discover visible job listings broadly before relevance scoring.
- For Greenhouse, Lever, and Ashby, collect broadly from the public ATS API before relevance scoring.
- Use location scope only when a career board needs a search/filter to reveal jobs.
- Avoid role, title, or skill keyword searches on company boards by default.
- For browser-safe public pages, try static JSON-LD `JobPosting` extraction before opening the interactive browser flow.
- Score collected jobs locally for Cloud, DevOps, Admin, Platform, and Support relevance.
- Keep LinkedIn and Indeed manual-only.
- Pause for CAPTCHA, login, or unclear manual-intervention cases.
- Use stable ATS job IDs for dedupe when a source provides them, while keeping browser jobs on URL and title/location fallbacks.

Default pre-collection location scope is configured in `config/discovery.yaml`:

- Canada
- Toronto
- Ontario
- Remote Canada
- Remote

Role and skill terms such as Cloud, DevOps, AWS, Azure, Terraform, Kubernetes, Linux, SRE, Platform, Support, Admin, Engineer, and Analyst are used after collection by the deterministic scoring layer. Keyword fallback is disabled by default. JobSeek was reviewed only as a read-only architecture reference for the collect-first principle; its files and larger architecture are not copied into this MVP.

## Repository Layout

```text
config/                   YAML configuration for companies, discovery scope, keywords, scoring, and policies
data/input/               Local input files such as company spreadsheets
data/exports/             Generated CSV and Markdown exports
docs/                     Project documentation
docs/screenshots/         Dashboard screenshot placeholder folder
src/browser/              Playwright session, interventions, and extraction helpers
src/classifier/           Source classification and policy rules
src/collectors/           Collection workflows
src/dashboard/            Streamlit app
src/importer/             Excel importer for watchlist generation
src/processing/           Scoring and processing logic
src/reports/              Daily run reporting workflow
src/storage/              SQLite schema and database helpers
tests/                    Pytest coverage
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

## Commands

Run the dashboard:

```powershell
streamlit run src/dashboard/app.py
```

Run browser collection for a few safe sources:

```powershell
python -m src.main collect --mode browser --limit 3
```

Run the daily workflow:

```powershell
python -m src.main daily-run
```

Apply verified starter career URLs into the main company config:

```powershell
python -m src.importer.apply_career_urls
```

Run tests:

```powershell
pytest
```

Run lint:

```powershell
ruff check .
```

## Dashboard Screenshots Placeholder

Store dashboard screenshots in `docs/screenshots/`.

Suggested filenames:

- `dashboard-daily-summary.png`
- `dashboard-source-readiness.png`
- `dashboard-jobs-found.png`
- `dashboard-intervention-queue.png`

## Limitations

- It currently focuses on local workflows and local SQLite storage only.
- Browser collection is intentionally conservative and may pause often on unclear layouts.
- Some ATS-backed sites still require manual URL entry or human review before collection is safe.
- SmartRecruiters is still intentionally detection-only until there is a clearly safe public collector path.
- Storage metadata is intentionally local-first and lightweight; it improves dedupe and update behavior but is not a full audit-history system.
- Scoring is deterministic keyword scoring only and does not yet use semantic matching.
- The current watchlist is strongest for Canadian banks and IT consulting targets, not broad job search.

## Roadmap

- expand safe public-source coverage beyond Greenhouse, Lever, Ashby, and static JSON-LD
- improve normalization for job descriptions and posting dates
- expand dashboard review tools for saved and rejected jobs
- add richer intervention analytics and retry history
- improve company onboarding from spreadsheets and manual watchlists

## Documentation

- [Architecture](docs/architecture.md)
- [Source Types](docs/source-types.md)
- [Compliance](docs/compliance.md)
- [Browser Workflow](docs/browser-workflow.md)
- [Collector Routing](docs/collector-routing.md)
- [Reporting And Dashboard](docs/reporting-dashboard.md)
- [Storage And Deduplication](docs/storage-deduplication.md)
- [Demo Script](docs/demo-script.md)
