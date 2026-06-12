# Manulife Verified Run

## Source
- Company: Manulife
- Source URL: https://careers.manulife.com/global/en/search-results
- Source mode: browser_allowed
- ATS type: -
- Stable Canada-filtered URL configured: no

## Fresh Production Run
- Run date: 2026-06-11
- Latest source timestamp: 2026-06-12 02:30:25
- Status: completed
- Jobs discovered: 100
- Jobs scored: 100
- Relevant jobs saved: 7
- Jobs inserted: 0
- Jobs updated: 0
- Jobs unchanged: 7
- Duplicates skipped: 0
- Suspicious saved rows: 0
- Pending interventions: none
- Error: none

## Canada Scope
- Canada-only scope confirmed by stable URL: no
- Canada-only scope confirmed by fresh production run: no
- `location_scope_used` in fresh `daily-run --company "Manulife"`: false
- Focused diagnostic note:
  the audit helper can type `Canada` into the public results search and keep the
  first 10 pages scoped during the focused diagnostic, but the default production
  run still does not confirm a stable Canada-only source URL or equivalent
  production-level scope signal.

## Pagination
- Pages visited in focused diagnostic: 10
- Pagination stop reason: max_pages_reached

## Verification Decision
- Meets fresh-run stability criteria: yes
- Meets Canada-only trust criterion: no
- Recommendation: keep as needs_review
- Reason:
  Manulife is productive enough to keep auditing, but it should not move into the
  trusted verified-only MVP slice until Canada-only scope is confirmed more
  explicitly in the production flow.
