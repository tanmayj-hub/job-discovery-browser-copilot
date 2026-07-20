# Dashboard Visual QA

Date: 2026-07-20

## Scope

The default dashboard workspace was checked against the fresh live review slice for
RBC and Scotiabank only. The final calibrated slice contains 13 eligible, relevant job
rows and keeps
historical verified-company jobs behind the `All Verified Jobs` tab.

## Screenshots

- `data/exports/dashboard-qa/pass-2-desktop-1440x900.png`: desktop header, navigation,
  and focused review filters.
- `data/exports/dashboard-qa/pass-2-job-review-flow.png`: first job-card and detail
  panel inspection.
- `data/exports/dashboard-qa/pass-5-final-job-review.png`: final card, action, and
  detail-panel contrast check.

## Pass 1 Findings

- The initial job-detail capture exposed default dark action buttons whose labels did
  not have enough contrast.
- Serialized match reasons displayed Python-style list syntax, which read like source
  data instead of an explanation for a job seeker.
- Some public source rows repeated a title inside the location field. The review layer
  now reduces those values to the confirmed city, province, and Canada label when it is
  safe to do so; missing locations show `Location not listed`.

## Changes Made

- Made `Jobs` the default tab and placed the current RBC + Scotiabank live scope in the
  header with refresh and collection-health labels.
- Replaced the table-first review workflow with job cards and a selected-job detail
  panel. The full historical verified queue remains available as a secondary view.
- Added compact filters for company, fit, score, review status, location, keyword, and
  sort order.
- Converted relevance tiers, review decisions, and run freshness values to readable
  labels.
- Added persistent, URL-keyed review decisions and notes in a separate working CSV.
- Normalized serialized list fields and known location contamination only in the review
  presentation export; SQLite history and raw source data are not changed.
- Applied explicit action-button contrast styles for readable `View details`, `Open
  posting`, `Open official job posting`, and save controls.

## Validation

- Desktop QA used a 1440 by 900 viewport.
- A narrow-viewport override was requested for a 390 by 844 check. The in-app capture
  backend returned its fixed 1440 by 899 image size, so this remains a capture-tool
  limitation rather than evidence of a mobile layout change.
- Opened an official RBC posting and an official Scotiabank posting from fresh-slice
  URLs. Both resolved to their expected employer job-detail pages.
- Saved a temporary in-dashboard decision and note, refreshed the dashboard, confirmed
  the URL-keyed values in the working CSV, then removed the QA-only decision so the
  user starts with a clean review file.

## Remaining Limitations

- Streamlit's standard controls constrain fine-grained responsive behavior. A manual
  browser check on a physical narrow screen is still useful before presenting this as a
  mobile-first product.
- The review queue intentionally explains deterministic scoring signals; it does not
  attempt to rewrite or expand the scoring policy.

## Calibration Follow-up QA

### Original Interaction Problem

Selecting a lower job card triggered an explicit rerun of the whole Streamlit page.
The user remained at the lower page position while the selected detail content could
be above the viewport.

### Fixes Verified

- The left opportunity list is now a height-constrained, independently scrollable
  Streamlit container.
- The selected-job detail and review form use a matching constrained container in the
  adjacent column, so they remain visible while the user scrolls the list.
- `View details` uses a callback to set the canonical URL key before the normal rerun.
  The selected card is highlighted and the right panel updates in place.
- The review filter now defaults to `Review needed`; the calibrated queue shows the
  score-changed DevOps Engineer, Solution Engineer, and Application Support Analyst
  without cluttering the first view with unchanged reviewed jobs.
- A `StreamlitDuplicateElementId` error was reproduced after save and refresh, traced
  to rendering All Verified Jobs twice, and removed by eliminating the duplicate
  Workspace render path.

### Final Evidence

- `data/exports/dashboard-qa/calibrated-dashboard-top.png`
- `data/exports/dashboard-qa/calibrated-review-flow.png`
- `data/exports/dashboard-qa/calibrated-dashboard-post-error-fix.png`

The calibrated review-flow capture shows the left job cards, highlighted Solution
Engineer, right-side detail panel, preserved user note, readable score of 60, and
official posting action in one desktop view.

The final live check reloaded the restored 13-row slice, selected `Review needed`, and
confirmed that exactly the three score-changed rows were shown. Selecting Solution
Engineer updated the adjacent detail panel immediately. No Streamlit error appeared.

### Viewport Note

Desktop behavior was checked at the in-app browser's 1440 by 900 capture. The capture
backend did not reliably apply a 1366 by 768 viewport override, so a physical-browser
responsive pass remains the only non-blocking visual limitation.
