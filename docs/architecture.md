# Architecture

## Overview

Job Discovery Browser Co-Pilot is a local-first Python application that supports safe job discovery from company career pages. The system is designed around explicit source policies, deterministic scoring, and a human-in-the-loop dashboard.

## Main Components

### Importer

`src/importer/`

- reads the Excel watchlist input
- filters the targeted company set
- normalizes watchlist records into `config/companies.yaml`

### Classifier

`src/classifier/`

- classifies each company source into an operating mode
- applies policy rules for restricted portals and ATS hints
- routes blocked or restricted sources into manual workflows

### Browser Layer

`src/browser/`

- manages Playwright browser sessions
- detects barriers like login walls, CAPTCHA, cookie blockers, and location selectors
- extracts visible job-like content when safe to do so

### Collectors

`src/collectors/`

- orchestrates source visits and collection runs
- saves extracted results without auto-applying
- records source outcomes and intervention requirements

### Processing

`src/processing/`

- normalizes job objects into a consistent storage shape
- deduplicates repeated jobs
- scores jobs deterministically with keyword-based logic

### Storage

`src/storage/`

- defines the SQLite schema
- stores companies, sources, jobs, daily runs, and interventions
- supports dashboard queries and export workflows

### Reports

`src/reports/`

- runs the daily workflow
- writes Markdown summaries
- exports CSV job snapshots

### Dashboard

`src/dashboard/`

- surfaces watchlist readiness
- supports URL completion and source reclassification
- shows jobs, saved jobs, interventions, and exports

## Data Flow

1. Excel watchlist input is imported into `config/companies.yaml`.
2. The database is initialized and seeded from YAML.
3. Source classification assigns each company a safe operating mode.
4. Eligible sources are collected through browser-assisted workflows.
5. Raw jobs are normalized, deduplicated, scored, and stored.
6. The dashboard and daily report expose jobs, interventions, and exports for human review.

## Design Principles

- local-first storage and execution
- visible browser automation only
- conservative handling of restricted or unclear pages
- deterministic scoring before any future AI-based features
- explicit safety boundaries around browsing and application behavior
