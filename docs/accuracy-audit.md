# Accuracy Audit

## Why This Exists

The MVP is intentionally conservative, but conservative collection still needs verification.
This audit workflow helps answer:

- Are saved MVP jobs real official postings?
- Are title, location, company, and URL values correct?
- Is the MVP missing relevant jobs visible on the official career page?
- What are precision and recall for an audited company set?

## Audit Workflow

### Simpler One-Company Workflow

Use this when you want to audit one company at a time with a single Markdown pack.

```powershell
python -m src.main audit company-pack `
  --company "TD" `
  --output docs/audits/TD-audit-pack.md `
  --limit 10 `
  --include-recent-days 14 `
  --status new
```

This command generates:

- a Markdown audit pack with the configured careers URL, source details, MVP jobs found,
  clickable job links, blank manual verification fields, a missed-jobs section, and a
  simple summary block
- `data/exports/audits/TD-mvp-sample.csv`
- `data/exports/audits/TD-manual-template.csv`

Recommended one-company flow:

1. Run `audit company-pack` for the company you want to review.
2. Open the generated Markdown file in `docs/audits/`.
3. Verify the MVP jobs against the official careers URL shown in the pack.
4. Fill the companion CSV files as you review.
5. Run `audit compare` after the manual fields are complete.

### Batch CSV Workflow

1. Export a reviewable MVP sample from SQLite.
2. Manually verify those saved rows on the official source.
3. Create a manual-job list for recall auditing.
4. Compare MVP rows against the manual list.
5. Review precision, recall, false positives, missing jobs, and unclear rows.

## Export MVP Audit Sample

```powershell
python -m src.main audit export-sample --output data/exports/accuracy-audit-sample.csv
```

Useful options:

```powershell
python -m src.main audit export-sample `
  --output data/exports/accuracy-audit-sample.csv `
  --companies "TD,RBC,BMO,Deloitte,CGI" `
  --limit-per-company 10 `
  --include-recent-days 14 `
  --status new
```

The exported CSV includes MVP job fields and blank manual-verification columns.

## Create Manual Recall Template

```powershell
python -m src.main audit create-manual-template --output data/exports/manual-job-audit-template.csv
```

Optional company-prefill:

```powershell
python -m src.main audit create-manual-template `
  --output data/exports/manual-job-audit-template.csv `
  --companies "TD,RBC,BMO,Deloitte,CGI"
```

## How To Manually Verify MVP Jobs

For each row in `accuracy-audit-sample.csv`:

- open the official job URL
- confirm the posting is real and still available if possible
- verify title, location, and company
- fill:
  - `manual_title`
  - `manual_location`
  - `manual_url`
  - `manual_found`
  - `manual_relevant`
  - `manual_notes`

Suggested conventions:

- `manual_found=true` when the MVP row is confirmed on the official source
- `manual_found=false` when the row is not a real posting or cannot be confirmed
- `manual_relevant=true` when it is a relevant audit target role
- `manual_relevant=false` when it is real but out of scope for the audited target

## How To Fill The Manual Template

Use `manual-job-audit-template.csv` for jobs discovered manually on the official career page,
including jobs the MVP may have missed.

Fill:

- `company_name`
- `manual_title`
- `manual_location`
- `manual_url`
- `manual_external_job_id` when visible
- `manual_source_url`
- `manual_relevant`
- `manual_notes`

This file is the recall ground truth for the audited source set.

## Compare MVP Vs Manual Results

```powershell
python -m src.main audit compare `
  --mvp data/exports/accuracy-audit-sample.csv `
  --manual data/exports/manual-job-audit-template.csv `
  --output docs/accuracy-audit-report.md
```

Validate files before compare:

```powershell
python -m src.main audit validate-files `
  --mvp data/exports/accuracy-audit-sample.csv `
  --manual data/exports/manual-job-audit-template.csv
```

Optional:

```powershell
python -m src.main audit compare `
  --mvp data/exports/accuracy-audit-sample.csv `
  --manual data/exports/manual-job-audit-template.csv `
  --output docs/accuracy-audit-report.md `
  --audited-by tanmay
```

The compare step uses deterministic matching only:

- `external_job_id`
- normalized URL
- normalized title + company + location fallback

## Metrics

Per company and overall, the audit report calculates:

- `mvp_saved_count`
- `manual_relevant_count`
- `matched_count`
- `false_positive_count`
- `missing_count`
- `unclear_count`
- `precision`
- `recall`

Definitions:

- `precision = matched_count / mvp_saved_count`
- `recall = matched_count / manual_relevant_count`

Divide-by-zero cases are handled as `0.0`.

## Interpreting Results

- High precision, high recall:
  - the MVP is both accurate and finding most relevant jobs in the audited slice
- High precision, low recall:
  - saved jobs are trustworthy, but the MVP is missing relevant postings
- Low precision, high recall:
  - discovery is broad enough, but saved results need better filtering
- Low precision, low recall:
  - both extraction quality and coverage need work

## Using Results For Future Fixes

Use audit outcomes to decide what kind of change is needed:

- extraction issue
  - false positives from category pages, filter rows, or partial cards
- source URL issue
  - wrong or unstable source entry URL
- scoring issue
  - real jobs saved even though they are not relevant to the target role set
- manual/source limitation
  - blocked layouts, login walls, or ambiguous manual-only cases

The audit workflow is meant to improve trustworthiness without changing the collect-first,
score-later architecture.
