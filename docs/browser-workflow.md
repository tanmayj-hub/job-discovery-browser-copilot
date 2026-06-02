# Browser Workflow

## Goal

Use Playwright in a visible browser window to review safe company career sources and capture relevant job listings without crossing compliance boundaries.

## Standard Flow

1. Load companies from the local watchlist.
2. Classify each source and skip anything not eligible.
3. Open the careers URL in headed mode.
4. Look for a search field when the page supports search.
5. Search with the configured keywords when appropriate.
6. Extract visible job-like cards and links.
7. Normalize, score, and save jobs to SQLite.
8. Record interventions instead of forcing progress on blocked pages.

## Pause Conditions

Create an intervention and stop automatic progress when the page shows:

- login requirements
- CAPTCHA
- blocking cookie consent
- a required location selector
- an unclear layout
- extraction failure

## Expected User Actions

The user may:

- open the blocked source manually
- clear a cookie banner
- inspect a public page visually
- mark a source manual-only
- skip a source
- add notes to the intervention queue

## Non-Goals

The browser workflow does not:

- solve CAPTCHA
- sign into accounts automatically
- impersonate a user
- rotate proxies
- automate restricted job boards
