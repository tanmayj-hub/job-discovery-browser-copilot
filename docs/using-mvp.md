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

## Run Verified Companies Only

```bash
python -m src.main daily-run --verified-only
```

This reads [verified_companies.yaml](C:/projects/job-discovery-browser-copilot/config/verified_companies.yaml) and runs only companies marked:

- `verified: true`
- `status: usable`

## List Verified Companies

```bash
python -m src.main daily-run --list-verified
```

This prints the current verified-company records without running collection.

## Open The Dashboard

```bash
streamlit run src/dashboard/app.py
```

## Current Verified Company Status
- Aviva Canada: verified, usable
- BMO: needs_review
- IBM Consulting: verified, usable
- Manulife: verified, usable
- Sun Life: verified, usable

Only companies marked `verified: true` and `status: usable` are included in
`--verified-only` runs. Companies marked `needs_review` remain available for
single-company audits, but they are intentionally excluded from the trusted MVP
slice until both source scope and result quality are proven strongly enough.

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

## What "Verified Company" Means
A company is usable enough for the current MVP workflow when the latest evidence shows:

- a fresh `daily-run --company` completed without error
- Canada-only scope is confirmed before pagination by run behavior or by a stable Canada-filtered official URL
- the run discovered jobs
- the run saved relevant jobs, unless a zero-saved result is explicitly explained and accepted
- suspicious saved rows are `0`
- no unresolved blocking intervention exists for that source
- the latest manual URL audit does not show active collection misses when such an audit exists

Verified does not mean perfect.
It means safe enough to include in the user's daily MVP workflow.

## Relevance Tiers
- `core_target_fit`: direct Cloud / DevOps / Platform / Admin / Support target fit
- `adjacent_customer_facing_technical_fit`: adjacent customer-facing technical roles that are still useful to review
- outside scope / rejected: collected but not saved because the current scoring rules do not treat the role as relevant

## Dashboard Notes
- The Jobs Found view defaults to verified companies only.
- The Daily Summary view includes verified-company counts, latest new/updated counts, and a verified source-health table.
- Use Source Readiness for a fuller source-health view when you want more than the compact verified summary.

## Add The Next Verified Company
Use this sequence when we want to promote another company into the verified-only
slice:

1. Run `python -m src.main daily-run --company "Company Name"` on the official public source.
2. Confirm Canada-only scope using a stable public URL or production-level scope evidence.
3. Check the latest source row for discovered jobs, saved relevant jobs, and no blocking interventions.
4. Run a manual URL audit when needed.
5. Update [verified_companies.yaml](C:/projects/job-discovery-browser-copilot/config/verified_companies.yaml) only after the fresh evidence is clean.
