# Job Review Workflow

## Run The Verified MVP

```bash
python -m src.main daily-run --verified-only
```

This refreshes the current trusted Canada-scoped job set from the verified usable companies
and writes a stable verified review snapshot.

Current post-fix baseline from the latest trusted run on `2026-06-14`:
- companies checked: `11`
- jobs discovered: `1898`
- jobs saved after scoring: `93`
- review export rows: `93`

## Open The Dashboard

```bash
streamlit run src/dashboard/app.py
```

In the dashboard:
- open `Saved Job Review`
- click `Refresh review CSV`
- download or open the generated review file

Default review export path:

```text
data/exports/review/saved-jobs-review.csv
```

Verified snapshot path used by the review export:

```text
data/exports/review/latest-verified-saved-jobs.csv
```

## Review Each Saved Job

For each row, fill:
- `user_decision`
- `user_notes`

Allowed `user_decision` values:
- `useful`
- `maybe`
- `not_useful`
- `false_positive`
- `already_applied`
- `saved_for_later`

## What Counts As A False Positive
- generic banking or sales role
- senior-only role that is not aligned with your target scope
- non-technical business or admin role
- role outside Cloud / DevOps / Solutions / Technical Customer Success scope

The review export now intentionally:
- includes unchanged saved jobs from the latest trusted verified-only run
- excludes non-verified companies such as `RBC`
- excludes rejected jobs
- includes provisional verified companies such as `BMO` when they have saved jobs

## Suspicious Examples To Check Carefully
- `Expert Banking Advisor`
- generic `Mortgage Specialist` roles
- `Private Banking Officer`
- `Executive Assistant`
- generic `Delivery Consultant` roles without technical context
- generic `Customer Service Representative` roles that only mention troubleshooting
- administrative roles that match only `administrator` / `admin`

These are good candidates to mark as `false_positive` or `not_useful` if they are not actually relevant to your target workflow.

## How To Use The Dashboard During Review
1. Run the verified-only MVP.
2. Open `Saved Job Review` in the dashboard.
3. Preview the latest verified saved jobs there.
4. Open individual job URLs from the dashboard when you want to inspect the posting.
5. Fill the CSV locally with your decisions and notes.

The dashboard now shows:
- review row count
- companies included in the current review export
- provisional company flags
- clickable job URLs
- match reasons and risk flags for each review row

## Why This Review Matters
This workflow now sits on top of the narrowed scoring pass from Task 12.13.

The review CSV is the lightweight feedback layer we will use later to:
- identify recurring false positives
- understand which adjacent roles are actually useful
- tune scoring with real review data instead of guesses
