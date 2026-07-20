# Using The MVP

## Run One Company
Run IBM Consulting only:

```bash
python -m src.main daily-run --company "IBM Consulting"
```

Run Sun Life only:

```bash
python -m src.main daily-run --company "Sun Life"
```

Run Aviva Canada only:

```bash
python -m src.main daily-run --company "Aviva Canada"
```

## Run Source-Verified Companies Only

```bash
python -m src.main daily-run --verified-only
```

This reads [verified_companies.yaml](C:/projects/job-discovery-browser-copilot/config/verified_companies.yaml) and runs only companies marked:

- `verified: true`
- `status: usable`

## List Source-Verified Companies

```bash
python -m src.main daily-run --list-verified
```

This prints the current source-verified company records without running collection.

## Open The Dashboard

```bash
streamlit run src/dashboard/app.py
```

## Current Verified Company Status
- Aviva Canada: verified, usable
- BMO: verified, usable (provisional; deeper relevance-quality review deferred)
- Canada Life: verified, usable
- CGI: verified, usable
- IBM Consulting: verified, usable
- Manulife: verified, usable
- National Bank of Canada: verified, usable
- NTT DATA: verified, usable
- RBC: verified, usable
- Scotiabank: verified, usable
- Sun Life: verified, usable
- TD: verified, usable

Only companies marked `verified: true` and `status: usable` are included in
`--verified-only` runs. Companies marked `needs_review` remain available for
single-company audits, but they are intentionally excluded from the trusted MVP
slice until both source scope and result quality are proven strongly enough.
Sources marked `blocked_by_cloudflare` are excluded from verified-only and
normal daily retries. Recheck them manually only when their official public
board is accessible without an anti-bot challenge.

BMO is now included in the verified-only slice as a provisional usable source
after the Canada-scope and pagination fixes. This is a deliberate workflow
decision so the daily MVP can keep monitoring BMO while we defer deeper
relevance-quality review to a later task.

Canada Life and NTT DATA are now part of the verified-only slice because both
sources completed fresh Canada-scoped runs on 2026-06-13 and cleared their
current manual next-slice checks without active collection misses.

CGI now uses the direct Canada Njoyn board with trusted JavaScript pagination,
and National Bank of Canada now uses public Canada page evidence from its
`en_CA` search-results board before pagination. Both sources are now part of
the verified-only slice because the latest next-slice audit shows extraction
coverage rather than active collection misses.

TD is now part of the verified-only slice because the direct Canada-filtered
Workday URL completed a fresh trusted run on 2026-06-14 and the current bank
manual URL audit matched all `3 / 3` expected URLs as `saved_by_mvp`.

Scotiabank is part of the source-verified slice because the official
Canada-filtered board completed a fresh all-pages run on 2026-07-20: 52 pages,
1,299 candidates, 88 relevant roles, and a genuine `no_more_pages` ending.
The current 65-row manual fixture found no pagination or extraction miss among
roles in the current listing. One active direct-page role was absent from that
listing; 12 collected roles remain rejected by the deliberate local scoring
rules. Its selection status is `calibrated_review_required`, so the review
workspace remains the final human quality check.

RBC is part of the verified-only slice after its Canada/newest-first audit
covered pages 1-75 without gaps or duplicate pages. Manual recall closed at
29/31 extracted; the two active URLs were absent from the audited current
listing, with one being an adjacent AI Quality role and the other a
Director-level SRE role outside target seniority. Production remains
Canada-scoped and capped at 20 pages; 75 pages were audit-only.

Cognizant remains outside the verified-only slice with status
`blocked_by_cloudflare`. The official Canada URL returned HTTP 403 and a
Cloudflare security-verification screen before its job board loaded. The MVP
does not bypass that protection, so Cognizant is not retried in normal daily
runs.

## Trusted Run Rule
Trusted MVP runs do not start from a broad/global careers listing and then rely
on post-filtering to recover Canada-only results.

Before pagination begins, the source must expose Canada scope through one of:

- a stable official Canada-filtered source URL
- a public pre-pagination Canada UI filter that the collector can confirm

If Canada scope cannot be confirmed before pagination:

- the trusted run skips the source
- the source remains `needs_review` or `needs_user_canada_url`
- any broader collection is treated as diagnostic-only evidence, not verification evidence

## What "Source-Verified Company" Means
A company is usable enough for the current MVP workflow when the latest evidence shows:

- a fresh `daily-run --company` completed without error
- Canada-only scope is confirmed before pagination by run behavior or by a stable Canada-filtered official URL
- the run discovered jobs
- the run saved relevant jobs, unless a zero-saved result is explicitly explained and accepted
- suspicious saved rows are `0`
- no unresolved blocking intervention exists for that source
- the latest manual URL audit does not show active collection misses when such an audit exists

Source-verified does not mean every role is a perfect personal fit.
It means the public source is safe enough to include in the user's daily MVP
workflow. Relevance selection remains subject to the local scoring rules and
human review.

Some verified companies may also carry a provisional confidence note in
[verified_companies.yaml](C:/projects/job-discovery-browser-copilot/config/verified_companies.yaml)
when the source is stable enough for daily use but still scheduled for later
quality review.

## Relevance Tiers
- `core_target_fit`: direct Cloud / DevOps / Platform / Admin / Support target fit
- `adjacent_customer_facing_technical_fit`: adjacent customer-facing technical roles that are still useful to review
- outside scope / rejected: collected but not saved because the current scoring rules do not treat the role as relevant

## Dashboard Notes
- The Jobs Found view defaults to source-verified companies only.
- The Daily Summary view includes verified-company counts, latest new/updated counts, and a verified source-health table.
- Use Source Readiness for a fuller source-health view when you want more than the compact verified summary.
- Use Saved Job Review to export the current trusted saved-job queue for manual triage.
- The review export now reflects the latest verified-only snapshot, not just newly changed rows.
- The review export excludes rejected jobs and non-verified companies such as `Cognizant`.

## Current Review Queue
The active review queue is regenerated by each verified-only run. Its metrics have
distinct meanings:

- `jobs_relevant_current_run` is the number of current-run candidates that passed
  scoring and Canada safety checks.
- `jobs_new`, `jobs_updated`, and `jobs_unchanged` are the persistence outcomes
  for those current-run relevant candidates.
- `active_saved_jobs` is the broader non-rejected verified-company queue after
  the run, including unchanged rows from earlier runs.
- `review_export_rows` is the number of active saved jobs written to the review CSV.

These counts can differ substantially. A small current-run relevant count does
not mean older active saved jobs have disappeared from the review queue.

## Export The Review Queue

```bash
python -m src.main review export-saved-jobs
```

This writes:

```text
data/exports/review/saved-jobs-review.csv
```

The dashboard's Saved Job Review section surfaces the same queue, with clickable job links,
match reasons, risk flags, and provisional source flags.

## Add The Next Verified Company
Use this sequence when we want to promote another company into the verified-only
slice:

1. Run `python -m src.main daily-run --company "Company Name"` on the official public source.
2. Confirm Canada-only scope using a stable public URL or production-level scope evidence.
3. Check the latest source row for discovered jobs, saved relevant jobs, and no blocking interventions.
4. Run a manual URL audit when needed.
5. Update [verified_companies.yaml](C:/projects/job-discovery-browser-copilot/config/verified_companies.yaml) only after the fresh evidence is clean.
# Collection Standards

Trusted runs confirm Canada scope before they paginate. They request newest-first sorting where the official board provides it, then report the actual sort outcome, pages scanned, and stop reason. The normal page cap is 20; Scotiabank and Cognizant are documented all-pages exceptions, while RBC uses 75 pages only for verification audits.
