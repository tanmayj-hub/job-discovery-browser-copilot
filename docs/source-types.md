# Source Types

## Purpose

The app tracks two related but different ideas:

- `ats_type`: what kind of career board or ATS the source appears to use
- `source_mode`: what the app is allowed to do with that source right now

Task 2 added deterministic ATS detection, later routing work adds real public API collectors for Greenhouse, Lever, and Ashby, plus a static JSON-LD precheck for browser-safe public pages.

## ATS Types

`ats_type` is a lightweight detector result inferred from the careers URL, `ats_hint`, or `website_category`.

Currently recognized ATS and source types include:

- `greenhouse`
- `lever`
- `ashby`
- `smartrecruiters`
- `workday`
- `successfactors`
- `oracle_hcm`
- `icims`
- `phenom`
- `restricted_board`

When the source does not match a known ATS, `ats_type` remains empty and the app falls back to public-browser handling rules.

## Modes

### `api_allowed`

Use this for ATS types that are API-friendly in principle. Greenhouse, Lever, and Ashby now have real public API collectors. SmartRecruiters is still detection-only in this mode by default.

Typical hints:

- Greenhouse
- Lever
- Ashby
- SmartRecruiters

### `browser_allowed`

Use this when the company has a public careers page and there is no known restriction or blocked ATS behavior.

Typical cases:

- public company careers site
- jobs index pages
- custom search pages without login or CAPTCHA

### `human_in_loop`

Use this when the source can be explored, but it should be done with an explicitly visible and supervised browser workflow.

Typical hints:

- Workday
- SuccessFactors
- Oracle HCM
- ICIMS
- Phenom
- UltiPro

### `manual_only`

Use this for restricted portals or sources where automation should not continue.

Typical cases:

- LinkedIn
- Indeed
- Glassdoor
- sites that require login
- sources that repeatedly present CAPTCHA or unclear barriers

### `needs_url`

Use this when the watchlist entry does not yet have a valid public careers URL.

Typical cases:

- blank careers URL
- search result text instead of a real URL
- incomplete watchlist data

### `avoid`

Use this when the source should be intentionally skipped.

Typical cases:

- out-of-scope sources
- unsafe sources
- companies intentionally removed from active monitoring

## Intervention Triggers

Collection should pause and create an intervention when the browser encounters:

- `login_required`
- `captcha_detected`
- `cookie_blocked`
- `location_selection_required`
- `unclear_layout`
- `extraction_failed`

## Current Classification Rules

- Greenhouse, Lever, Ashby, and SmartRecruiters classify as `api_allowed`
- Workday, SuccessFactors, Oracle HCM, ICIMS, and Phenom classify as `human_in_loop`
- LinkedIn, Indeed, and Glassdoor classify as `manual_only`
- Missing or invalid careers URLs classify as `needs_url`
- Unknown public career pages classify as `browser_allowed`

Greenhouse, Lever, and Ashby public job feeds are now collected broadly first and scored locally later. Browser-safe public pages can also be collected from static JSON-LD `JobPosting` blocks before a headed browser session is opened. Stored jobs preserve `external_job_id`, `ats_type`, and `board_slug` when available so local dedupe prefers stable ATS identity before falling back to URL or title/location matching. SmartRecruiters still remains unimplemented in the router by default, which keeps the routing small and local-first without expanding into unsupported collectors.
