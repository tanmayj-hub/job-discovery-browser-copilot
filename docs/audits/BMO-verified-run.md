# BMO Verified Run

## Source
- Company: BMO
- Source URL: https://jobs.bmo.com/global/en/home
- Source mode: browser_allowed
- ATS type: -
- Stable Canada-filtered URL configured: no

## Fresh Production Run
- Run date: 2026-06-11
- Latest source timestamp: 2026-06-12 02:30:22
- Status: completed
- Jobs discovered: 102
- Jobs scored: 102
- Relevant jobs saved: 10
- Jobs inserted: 0
- Jobs updated: 0
- Jobs unchanged: 10
- Duplicates skipped: 0
- Suspicious saved rows: 0
- Pending interventions: none
- Error: none

## Canada Scope
- Canada-only scope confirmed by stable URL: no
- Canada-only scope confirmed by fresh production run: no
- `location_scope_used` in fresh `daily-run --company "BMO"`: false
- Focused diagnostic note:
  the public results flow is productive and paginates well, but the production
  run still does not confirm an explicit Canada-only scope signal.

## Pagination
- Pages visited in focused diagnostic: 10
- Pagination stop reason: max_pages_reached

## Verification Decision
- Meets fresh-run stability criteria: yes
- Meets Canada-only trust criterion: no
- Recommendation: keep as needs_review
- Reason:
  BMO completed a strong fresh run and saved relevant jobs, but it still lacks a
  stable Canada-filtered source URL or equivalent production evidence that the
  automated run stayed Canada-only.
