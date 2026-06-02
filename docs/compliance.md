# Compliance

## Intent

This project is built for job discovery support, not job application automation.

## Safety Rules

- No auto-apply
- No CAPTCHA bypass
- No proxy rotation
- No stealth scraping
- No bot evasion
- No LinkedIn or Indeed automation
- Restricted sites stay in manual-only mode

## Human-In-The-Loop Expectations

The user should be able to see what the browser is doing and intervene when needed. The system should pause rather than improvise when it encounters:

- a login wall
- a CAPTCHA
- a blocking cookie banner
- a location selector that changes page content
- an unclear layout that risks extracting the wrong data

## Allowed Collection Scope

The intended collection scope is:

- public company careers pages
- safe ATS-backed public listings
- supervised browser workflows for supported sources

The intended collection scope is not:

- private portals
- restricted aggregator sites
- hidden endpoints discovered through evasion or reverse engineering

## Data Handling

- data is stored locally in SQLite
- exports are written locally under `data/exports/`
- no cloud deployment is included in this repository yet

## Operating Principle

When a source is ambiguous, blocked, or restricted, the correct behavior is to pause and defer to manual review.
