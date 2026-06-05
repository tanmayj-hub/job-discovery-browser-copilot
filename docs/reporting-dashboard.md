# Reporting And Dashboard

## Purpose

Task 7 improves visibility only. It does not add new collectors or change routing, scoring, browser behavior, or dedupe rules.

The goal is to make it clear what happened for each company source during local runs.

## Source Readiness View

The Streamlit dashboard now includes a `Source Readiness` section.

For each source it can show:

- company
- source URL
- source mode
- ATS type
- collector used
- status
- readiness label
- pending intervention count
- resolved intervention history count
- latest pending reason
- remediation label
- suggested action
- fallback used
- intervention required
- jobs discovered
- jobs relevant
- jobs saved
- jobs inserted
- jobs updated
- jobs unchanged
- duplicates skipped
- last error
- last success time
- consecutive failures

The table also supports simple filters for:

- source mode
- ATS type
- collector
- status
- fallback used
- intervention required

## Daily Report

The daily Markdown report now separates the run into clearer sections:

- `Collection`
- `Evaluation`
- `Storage And Dedupe`
- `Routing Summary`
- `Source Outcomes`
- `Active Pending Interventions`
- `Resolved Intervention History`

This makes it easier to distinguish:

- `jobs discovered`: collected before scoring
- `jobs scored`: locally evaluated after dedupe
- `jobs relevant`: passed deterministic relevance checks
- `jobs saved`: persisted after relevance filtering

And also:

- `jobs inserted`: brand-new rows written to SQLite
- `jobs updated`: existing rows whose content changed
- `jobs unchanged`: existing rows seen again without content change
- `duplicates skipped`: duplicates removed before scoring/persistence

Interventions are now split into:

- active pending items that still block progress
- resolved/manual-only/skipped history that remains available for audit

## Status Interpretation

- `success`, `completed`, `no_jobs_found`: source check completed without an execution error
- `manual_only`: intentionally skipped because the source is restricted
- `needs_url`: intentionally skipped because the source is missing a valid URL
- `api_collector_not_implemented`: the source is API-friendly in principle, but no safe public collector is implemented yet
- `paused`: human intervention is required before continuing
- `error`, `api_error`, `parse_error`: the source check failed

## Fallback Interpretation

- `fallback_used = true` means the source did not stay on its primary path
- For browser-allowed public pages, this typically means static JSON-LD did not finish the job and the flow continued into the browser collector
- For API-enabled sources, this means browser fallback was explicitly enabled and used

Fallback visibility is reporting-only in this task. It does not change the underlying routing policy.

## Scope Reminder

This task does not add:

- SmartRecruiters collection
- Workday, SuccessFactors, Oracle HCM, ICIMS, or Phenom collectors
- new browser automation behavior
- keyword-first collection
- cloud infrastructure or queueing systems
