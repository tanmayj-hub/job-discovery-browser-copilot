# Browser Workflow

## Goal

Use Playwright in a visible browser window to review safe company career sources and capture relevant job listings without crossing compliance boundaries.

## Standard Flow

1. Load companies from the local watchlist.
2. Classify each source and skip anything not eligible.
3. Open the careers URL in headed mode.
4. Navigate to a public job search or results page when the page exposes one.
5. First extract visible or listed jobs without using role or skill keywords.
6. If the page requires search or filtering to reveal jobs, use location-scope terms only.
7. Do not use Cloud, DevOps, AWS, Terraform, Kubernetes, Linux, SRE, or similar role and skill terms as pre-extraction search terms.
8. Normalize and dedupe discovered jobs.
9. Score jobs locally after collection.
10. Save or export relevant jobs and report discovery, scoring, relevance, and saved counts.
11. Record interventions instead of forcing progress on blocked pages.

## Discovery Scope

Role, skill, and title keywords are not used before extraction by default.

Location terms are allowed before extraction when a company board requires search or filtering to reveal public job listings.

Default location terms come from [discovery.yaml](C:/projects/job-discovery-browser-copilot/config/discovery.yaml):

- Canada
- Toronto
- Ontario
- Remote Canada
- Remote

Keyword fallback is disabled by default.

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
