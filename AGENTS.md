# AGENTS.md

## Project Purpose

Job Discovery Browser Co-Pilot is a local Python project for human-in-the-loop job discovery across Canadian banks and IT consulting companies.

The tool helps users review company career pages, capture relevant job leads, store them locally, and export findings. It must keep the human in control and must not auto-apply to jobs.

## Repo Structure

```text
config/          Project configuration files
data/input/      Source input files, including company spreadsheets
data/exports/    Generated CSV, JSON, or report exports
src/importer/    Input loading and normalization
src/classifier/  Company and role classification
src/collectors/  Safe career-page collection helpers
src/browser/     Browser-assisted discovery and manual workflows
src/processing/  Parsing, deduplication, and enrichment
src/storage/     SQLite schema and persistence
src/reports/     Export and reporting tools
src/dashboard/   Streamlit dashboard entry points
tests/           Unit and integration tests
docs/            Project notes and design docs
```

## Run The Dashboard

```powershell
streamlit run src/dashboard/app.py
```

## Run Tests

```powershell
pytest
```

## Lint Command

```powershell
ruff check .
```

## Coding Conventions

- Use Python type hints for public functions and data models.
- Prefer Pydantic models for structured inputs, normalized records, and validation boundaries.
- Keep browser automation explicit, visible, and reviewable.
- Use SQLite for local persistence and keep schema changes documented.
- Keep modules small and organized by responsibility.
- Write tests for parsing, normalization, classification, storage behavior, and safety boundaries.
- Avoid broad refactors while implementing focused features.

## Safety Rules

- No auto-apply.
- No CAPTCHA bypass.
- No proxy rotation.
- No stealth scraping.
- No LinkedIn or Indeed automation.
- Use manual-only mode for restricted sites.
- Respect robots.txt, terms of service, and access restrictions.
- Prefer official company career pages and user-reviewed browser-assisted discovery.
