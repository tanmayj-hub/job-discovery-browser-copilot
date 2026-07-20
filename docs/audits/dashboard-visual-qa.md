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

## Scotiabank Reconciliation QA

- The focused workspace now uses the fresh 88-row Scotiabank review slice, with 85 roles
  requiring a user decision and three carried-forward decisions.
- The compact desktop shell keeps the main page fixed. The opportunity list is the only
  vertically scrollable region; selecting a card keeps the selected-job panel stationary.
- The review action opens a native Streamlit modal so decision and note controls remain
  usable without turning the right detail panel into a second long scroll area.
- The visible labels now say `source-verified`, which describes collection reliability
  without implying that deterministic scoring has made a final personal-fit decision.
- A live 1280 by 720 browser check confirmed the Scotiabank queue, selected-detail update,
  official-posting action, review dialog controls, no runtime error, and a zero main-scroll
  position after selecting a different job card.

### Remaining Limitation

Streamlit uses a fixed desktop shell for the focused review queue. The compact filter control
is collapsed by default to preserve the selected detail and review action on shorter desktop
viewports; open it when changing company, score, fit, location, or sort filters.
