# First Manual Accuracy Audit Guide

## Purpose

This is the first real manual validation pass for the MVP audit workflow.
The goal is to verify saved MVP jobs against official company career pages and
measure trustworthiness without changing collection or scoring logic.

## What Precision Means

Precision answers:

- Of the jobs the MVP saved, how many are correct and real?

Formula:

- `matched_count / mvp_saved_count`

High precision means the saved MVP rows are usually trustworthy.

## What Recall Means

Recall answers:

- Of the relevant jobs you manually found on the official source, how many did the MVP find?

Formula:

- `matched_count / manual_relevant_count`

High recall means the MVP is missing fewer relevant jobs.

## Files You Will Use

- MVP audit sample:
  - [accuracy-audit-sample.csv](/C:/projects/job-discovery-browser-copilot/data/exports/accuracy-audit-sample.csv)
- Manual recall template:
  - [manual-job-audit-template.csv](/C:/projects/job-discovery-browser-copilot/data/exports/manual-job-audit-template.csv)
- Link sheet:
  - [manual-audit-link-sheet.csv](/C:/projects/job-discovery-browser-copilot/data/exports/manual-audit-link-sheet.csv)
- After review, generate:
  - [accuracy-audit-report.md](/C:/projects/job-discovery-browser-copilot/docs/accuracy-audit-report.md)

## How To Open The MVP Audit Sample

Open [accuracy-audit-sample.csv](/C:/projects/job-discovery-browser-copilot/data/exports/accuracy-audit-sample.csv) in Excel or another spreadsheet tool.

Each row is one MVP-saved job candidate that should be manually checked.

Important MVP columns:

- `company_name`
- `mvp_title`
- `mvp_location`
- `mvp_url`
- `mvp_external_job_id`
- `mvp_score`
- `mvp_last_seen_at`

Important blank manual columns:

- `manual_title`
- `manual_location`
- `manual_url`
- `manual_found`
- `manual_relevant`
- `audit_status`
- `match_confidence`
- `reason`
- `manual_notes`

## How To Manually Verify Each MVP URL

For each row:

1. Open `mvp_url`.
2. Confirm the page is on the official company source or official ATS.
3. Confirm whether it is a real individual job posting.
4. Confirm title and location.
5. Decide whether the role is relevant to the audit scope.
6. Fill the manual columns.

If the URL is broken, redirected to a non-job page, or clearly not a real posting, do not guess.
Mark it carefully and add notes.

## How To Fill `manual_found`

Use:

- `true`
  - the MVP row corresponds to a real posting on the official source
- `false`
  - the MVP row does not correspond to a real posting, or you cannot confirm it on the official source
- blank
  - only if you have not reviewed the row yet

## How To Fill `manual_relevant`

Use:

- `true`
  - the role is relevant to the current target audit scope
- `false`
  - the role is real, but not relevant to the target scope
- blank
  - only if you have not reviewed the row yet

## How To Choose `audit_status`

Use:

- `matched`
  - real posting, relevant, and the MVP row clearly matches the manual result
- `false_positive`
  - MVP saved a row that is not a real relevant posting
- `unclear`
  - you cannot confidently tell whether it matches or whether the source is ambiguous
- `not_relevant`
  - real posting, but outside the target role scope

Do not use `missing_from_mvp` in the MVP sample file.
That status is produced later by the compare step from the separate manual template.

## How To Search Official Career Sites For Relevant Jobs

For each company:

1. Open the configured career URL from the link sheet or checklist.
2. Stay on the official company page or official ATS page only.
3. Look for relevant roles manually.
4. Add those manually found jobs to the manual template, even if they were not in the MVP sample.

Focus on real job-detail postings, not:

- category pages
- filter pages
- search landing pages
- careers marketing pages
- generic department listings

## How To Fill `manual-job-audit-template.csv`

Open [manual-job-audit-template.csv](/C:/projects/job-discovery-browser-copilot/data/exports/manual-job-audit-template.csv).

For each relevant job you manually discover on the official source, fill:

- `company_name`
- `manual_title`
- `manual_location`
- `manual_url`
- `manual_external_job_id` when visible
- `manual_source_url`
- `manual_relevant`
- `manual_notes`

This file is the recall ground truth.

## Validate The Files Before Compare

Run:

```powershell
python -m src.main audit validate-files `
  --mvp data/exports/accuracy-audit-sample.csv `
  --manual data/exports/manual-job-audit-template.csv
```

This checks:

- required columns
- valid `audit_status` values if filled
- valid manual boolean fields
- URL shape
- duplicate manual rows by company/title/url

## How To Run Audit Compare

Only run this after you have filled the manual audit files.

```powershell
python -m src.main audit compare `
  --mvp data/exports/accuracy-audit-sample.csv `
  --manual data/exports/manual-job-audit-template.csv `
  --output docs/accuracy-audit-report.md
```

Optional:

```powershell
python -m src.main audit compare `
  --mvp data/exports/accuracy-audit-sample.csv `
  --manual data/exports/manual-job-audit-template.csv `
  --output docs/accuracy-audit-report.md `
  --audited-by tanmay
```

## How To Interpret `docs/accuracy-audit-report.md`

Key sections:

- `Verdict`
  - high-level quality read for the audited slice
- `Overall Metrics`
  - overall precision and recall
- `Per-Company Metrics`
  - which companies are stronger or weaker
- `False Positives`
  - saved MVP rows that should not have been trusted
- `Missing Jobs`
  - relevant manual jobs the MVP did not capture
- `Unclear Jobs`
  - rows needing a second look
- `Recommended Fixes`
  - likely extraction issue, source URL issue, scoring issue, or manual/source limitation

## Recommended First Pass

Work company by company in this order:

1. TD
2. RBC
3. BMO
4. Deloitte
5. CGI
6. IBM Consulting
7. Sun Life
8. Canada Life
9. Wipro
10. NTT DATA

This keeps the first audit pass representative across banks, consulting, and harder manual/problem sources.
