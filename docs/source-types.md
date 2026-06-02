# Source Types

## Purpose

Source modes control what the system is allowed to do with a company careers source.

## Modes

### `api_allowed`

Use this for public ATS platforms that are usually structured and safer to automate in controlled ways.

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
- Oracle Cloud
- UltiPro

### `manual_only`

Use this for restricted portals or sources where automation should not continue.

Typical cases:

- LinkedIn
- Indeed
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
