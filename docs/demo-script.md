# Demo Script

## Goal

Show the repository as a safe, local-first job discovery assistant for Canadian banking and IT consulting targets.

## Demo Setup

Before the demo:

- create the virtual environment
- install dependencies
- confirm `config/companies.yaml` exists
- confirm the SQLite database can initialize
- launch the dashboard with `streamlit run src/dashboard/app.py`

## Suggested Walkthrough

### 1. Introduce the problem

Explain that career-page monitoring is fragmented and repetitive, especially when trying to track public roles across many companies without relying on restricted job portals.

### 2. Show the watchlist

Open the dashboard and point to:

- total companies
- ready-to-search count
- missing URL count
- intervention count

### 3. Show source safety controls

Explain the source modes:

- `browser_allowed`
- `human_in_loop`
- `manual_only`
- `needs_url`

Call out that LinkedIn and Indeed are not automated.

### 4. Show job review

Open the `Jobs Found` section and highlight:

- score filters
- status filters
- match reasons
- risk flags
- saved versus rejected review actions

### 5. Show intervention handling

Open the `Intervention Queue` and explain that blocked sources pause instead of bypassing barriers.

### 6. Show exports

Open the `Exports` section and show the daily Markdown report and CSV output.

## Closing Message

This project is designed to support disciplined job discovery, not unsafe automation. The strongest value is the combination of watchlist tracking, conservative browser assistance, and human review.
