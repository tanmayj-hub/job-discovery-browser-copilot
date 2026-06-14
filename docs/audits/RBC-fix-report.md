# RBC Fix Report

## Issue Found
- The original config pointed at a broad RBC careers entry page that did not expose trusted Canada scope before pagination.
- Updating to the direct official search-results page improved diagnostic collection, but the public page still mixes Canada and non-Canada jobs unless the Country facet is properly applied and confirmed.

## Fix Applied
- Updated [config/companies.yaml](C:/projects/job-discovery-browser-copilot/config/companies.yaml) to use:
  `https://jobs.rbc.com/ca/en/search-results?from=140&s=1`

## Fresh Results
- Trusted run: `0` discovered, skipped before pagination because Canada scope remained unconfirmed.
- Diagnostic run: `100` discovered, `3` relevant, `10` pages visited, stop reason `max_pages_reached`.
- Source scope status: `canada_scope_unconfirmed`
- Manual recall status: `0 / 4` matched in the current bank-slice audit.

## Verification Decision
- Decision: `needs_review`

## Remaining Blocker
- The official results board exposes a public Country facet with `Canada`, but the current trusted path does not yet apply and confirm that facet safely before pagination.
- Because mixed-country rows still appear in diagnostic output, RBC cannot be promoted from locale-only evidence.

## Exact Next Step
- Add a safe public RBC Country=Canada facet interaction and confirmation path, then rerun the trusted company flow and manual URL recall audit.
