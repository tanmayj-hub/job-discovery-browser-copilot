# Using The MVP

## Run One Verified Company
Run IBM Consulting only:

```bash
python -m src.main daily-run --company "IBM Consulting"
```

Run Sun Life only:

```bash
python -m src.main daily-run --company "Sun Life"
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
- IBM Consulting: verified, usable
- Sun Life: verified, usable

## What "Verified Company" Means
A company is usable enough for the current MVP workflow when the latest evidence shows:

- a fresh `daily-run --company` completed without error
- Canada-only scope is confirmed by run behavior or by a stable Canada-filtered official URL
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
