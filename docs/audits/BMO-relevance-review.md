# BMO Relevance Review

## Summary
- Review date: 2026-06-12
- Fresh trusted run: `python -m src.main daily-run --company "BMO"`
- Trusted source URL: `https://jobs.bmo.com/ca/en/search-results`
- Source scope status: `canada_scope_confirmed`
- Scope method: `page_evidence`
- Location scope used: `True`
- Pages reviewed by MVP: `10`
- Jobs discovered: `100`
- Jobs scored: `100`
- Jobs relevant: `0`
- Jobs saved: `0`
- Suspicious saved rows: `0`

## Manual Audit Comparison
- User manual note: first 10 Canada-filtered pages reviewed, no relevant jobs found.
- MVP result after the BMO collection fix: no jobs were saved as relevant.
- Alignment: strong. The current trusted run does not contradict the user's manual audit.

## Saved / Relevant Jobs

| Title | Location | URL | Relevance Tier | Score | Match Reasons | Why It Was Saved | Canada Location Evidence | Reviewer Decision |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| None | - | - | - | 0 | - | No BMO jobs met the current relevance threshold in the fresh trusted run. | All paginated result links used visible `EXTERNALENCA` rows only. | keep |

## Score Explanation Status
- There were no saved BMO jobs in the fresh trusted run, so there were no per-job saved-role score explanations to generate.
- All reviewed BMO rows stayed below the relevance threshold.
- The highest observed BMO scores in the export were location-only `4` point internship rows, which were still rejected as `not_relevant`.

## Noisy Roles Checked

| Title | Outcome | Why It Stayed Rejected |
| --- | --- | --- |
| Mortgage Specialist | rejected | No Cloud / DevOps / Platform / Admin / Support / technical context signals. |
| Private Banking Officer, Sales, Private Banking | rejected | Sales / banking wording without technical delivery context. |
| Executive Assistant, Investment Banking, BMO Capital Markets | rejected | Administrative role with no target technical signals. |
| Client Service Associate, BMO Nesbitt Burns | rejected | Generic service wording without customer-facing technical evidence. |
| Customer Service Representative | rejected | Generic customer-service wording without technical product or platform signals. |

## Technical-Adjacent Rows Not Saved
- `Application Security Automation Engineer`
- `AI Data Engineer`
- `Software Developer`
- `Software Developer - (Java / Websphere / Payment Systems)`
- `Mainframe Application Developer`
- `IBM MDM Developer`
- `Senior Analyst, Data Foundations and Infrastructure`

These rows were discovered successfully but still scored below relevance. That is a scoring-tuning question for a later task, not a collection or Canada-scope failure.

## Review Decision
- Collection trust: `fixed`
- Relevance trust: `not yet promoted`
- Verified-company decision: keep BMO at `verified: false` and `status: needs_review`
- Reason: the trusted run is Canada-scoped and stable, but there are currently no saved relevant jobs to justify promotion into the verified-only slice.
