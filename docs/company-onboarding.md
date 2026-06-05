# Company Onboarding

## Current MVP Input Requirement

The core MVP expects company/source records in [config/companies.yaml](/C:/projects/job-discovery-browser-copilot/config/companies.yaml).

In practice that usually means:

- company name
- career page URL or job board URL
- enough metadata to classify the source safely

That works well for technical users, but it is still too manual for users who only have a list of company names.

## What The Onboarding Helper Does

Task 10 adds a review-first helper that turns company names into candidate source records.

It does **not** rewrite the MVP engine.

It helps by:

- accepting a plain text, CSV, or XLSX list of company names
- checking existing known sources in the repo
- producing reviewable candidate URLs and classifications
- marking missing or restricted candidates clearly
- keeping the result in an export file instead of changing main config automatically

## Modes

The onboarding helper now has three safe modes:

1. Internal-only onboarding
2. Opt-in live discovery onboarding
3. Existing source refresh / weekly source-health check

## What It Does Not Do

- no guaranteed company-name-only web discovery
- no internet-search dependency in tests
- no blind overwrite of [config/companies.yaml](/C:/projects/job-discovery-browser-copilot/config/companies.yaml)
- no LinkedIn, Indeed, or Glassdoor automation
- no CAPTCHA/login bypass
- no new collectors
- no hosted scheduler

## Candidate Sources

Candidate generation currently uses these sources in order:

1. Existing [config/companies.yaml](/C:/projects/job-discovery-browser-copilot/config/companies.yaml)
2. Existing [config/starter_career_urls.yaml](/C:/projects/job-discovery-browser-copilot/config/starter_career_urls.yaml)
3. Existing reference import workbook data already present in `data/input/`
4. A low-confidence `needs_url` candidate if no known URL exists

The helper does **not** fabricate URLs.

## Internal-Only Generate Candidates

Main CLI style:

```powershell
python -m src.main onboard generate --input data/input/company-names.txt --output data/exports/source-onboarding-candidates.yaml
```

Direct helper module:

```powershell
python -m src.onboarding.source_onboarding generate --input data/input/company-names.txt --output data/exports/source-onboarding-candidates.yaml
```

Supported input formats:

- `.txt`
- `.csv`
- `.xlsx`

Without `--live-discovery`, the helper stops after internal repo lookups:

1. [config/companies.yaml](/C:/projects/job-discovery-browser-copilot/config/companies.yaml)
2. [config/starter_career_urls.yaml](/C:/projects/job-discovery-browser-copilot/config/starter_career_urls.yaml)
3. reference workbook data in `data/input/`
4. fallback `needs_url`

## Live Discovery Mode

Live discovery is opt-in:

```powershell
python -m src.main onboard generate --input data/input/company-input.csv --output data/exports/source-onboarding-candidates.yaml --live-discovery
```

Use this when the input includes a known official website or a known careers URL.

### Input Examples

TXT company names only:

```text
RBC
Accenture
```

TXT with optional website/careers fields:

```text
Example Co | https://www.example.com
Example ATS Co | https://www.exampleats.com | https://www.exampleats.com/careers
```

CSV:

```csv
company_name,website_url,careers_url
Example Co,https://www.example.com,
Example ATS Co,https://www.exampleats.com,https://www.exampleats.com/careers
```

XLSX:

- required company column: `Company`, `company_name`, `company`, or `name`
- optional website column: `website_url`, `official_website`, `company_website`, or `website`
- optional careers column: `careers_url`, `career_url`, or `job_board_url`

### Company-Name-Only Behavior

If you provide only a company name:

- internal lookup still runs first
- if the repo already knows the company, you still get internal candidates
- if the repo does **not** know the company and no website URL is provided, the helper does **not** invent a domain
- it returns a low-confidence review candidate instead

Company-name-only open-web search is future work unless a search provider is added later.

### Company Name Plus Website Behavior

If `website_url` is present:

- the helper fetches only the provided site
- it looks for same-domain careers/jobs links
- it may also detect linked ATS boards such as Greenhouse, Lever, Ashby, Workday, and similar systems
- it does not use a search engine

### How Careers And Job-Board Links Are Found

The helper:

- fetches the provided homepage or known source URL with safe timeouts
- parses links with BeautifulSoup
- prefers same-domain links that look like careers/jobs pages
- follows only a small number of pages, default `8`
- limits depth to a shallow careers discovery flow
- allows known ATS/job-board domains only when they are linked from the official/public page
- marks LinkedIn, Indeed, and Glassdoor as restricted/manual-only

Signals include:

- `careers`
- `career`
- `jobs`
- `job`
- `join-us`
- `work-with-us`
- `opportunities`
- `employment`
- `open-roles`

### Safety Notes

- no Playwright/browser automation in this task
- no login
- no CAPTCHA bypass
- no stealth crawling
- robots.txt is checked where practical
- if robots.txt cannot be read, the helper stays on a minimal safe fetch path instead of broad crawling

## Review Candidates

The generated candidate file is reviewable output, usually:

- [data/exports/source-onboarding-candidates.yaml](/C:/projects/job-discovery-browser-copilot/data/exports/source-onboarding-candidates.yaml)

Each candidate includes:

- `company_name`
- `candidate_official_website`
- `candidate_careers_url`
- `candidate_job_board_url`
- `detected_ats_type`
- `suggested_source_mode`
- `confidence`
- `needs_review`
- `reason`
- `evidence`
- `approved`

Candidates may also carry extra metadata when the repo already knows it, such as sector/category and existing watchlist hints.

Refresh candidates can also include:

- `current_careers_url`
- `current_source_mode`
- `current_ats_type`
- `current_status_or_last_error`
- `suggested_action`

## Confidence Meanings

- `high`
  - direct existing configured source
  - direct known ATS board such as Greenhouse, Lever, or Ashby
- `medium`
  - official-looking careers URL from starter/reference data
  - plausible repo-known source that should still be checked by a human
  - same-domain careers/jobs page found from an official website
- `low`
  - missing URL
  - ambiguous candidate
  - restricted third-party board
  - discovery failure or homepage-only result

## ATS And Source Validation

For each candidate URL the helper:

- runs the ATS detector
- runs the existing source classifier
- marks restricted third-party boards as `manual_only`
- identifies API-ready ATS boards such as Greenhouse, Lever, and Ashby
- identifies `human_in_loop` sources such as Workday
- identifies generic public pages as `browser_allowed`
- identifies missing URLs as `needs_url`

## Restricted Boards

LinkedIn, Indeed, and Glassdoor are treated as restricted/manual-only.

That means:

- they can appear in review output for visibility
- they are not treated as automatable sources
- they are not auto-applied into the main automated watchlist flow

## Source Refresh Mode

Use this to generate reviewable replacement candidates for existing configured sources:

```powershell
python -m src.main onboard refresh-sources --output data/exports/source-refresh-candidates.yaml
```

Useful flags:

```powershell
python -m src.main onboard refresh-sources --only-problem-sources --min-days-between-checks 7 --max-pages-per-company 8
```

Optional company filter:

```powershell
python -m src.main onboard refresh-sources --company "Tech Mahindra" --force
```

The refresh flow uses:

- the current configured careers URL
- the source domain/root when available
- current source readiness and intervention history from the local SQLite DB

It does **not** auto-update the main config.

### Stale URL Recovery Flow

Configured source
-> source looks stale/problematic
-> live refresh discovery checks the current URL/root
-> replacement careers or ATS candidates are generated
-> candidate file is written for review
-> user sets `approved: true`
-> apply only happens with explicit `--update-existing`

## Weekly Source-Health Check

Run the lightweight weekly failsafe manually:

```powershell
python -m src.main onboard weekly-source-check --output data/exports/weekly-source-refresh-candidates.yaml
```

Recommended usage:

```powershell
python -m src.main onboard refresh-sources --only-problem-sources --min-days-between-checks 7 --output data/exports/weekly-source-refresh-candidates.yaml
```

The helper tracks lightweight local state in:

- [data/exports/source-health-state.json](/C:/projects/job-discovery-browser-copilot/data/exports/source-health-state.json)

Tracked fields include:

- `company_name`
- `source_url`
- `last_health_check_at`
- `last_health_status`
- `last_candidate_count`
- `last_error`

### Scheduling Examples

Windows Task Scheduler:

- schedule `python -m src.main onboard weekly-source-check --output data/exports/weekly-source-refresh-candidates.yaml`

cron:

- schedule the same command weekly on the local machine

GitHub Actions:

- possible future option for documentation-only/local-safe workflows
- not added in this task

## Apply Approved Candidates

If you explicitly approve candidates, you can apply them with:

```powershell
python -m src.main onboard apply --input data/exports/source-onboarding-candidates.yaml
```

Optional update mode for existing companies:

```powershell
python -m src.main onboard apply --input data/exports/source-onboarding-candidates.yaml --update-existing
```

Safety rules:

- only `approved: true` candidates are applied
- existing companies are skipped by default
- replacement candidates require `--update-existing`
- a backup of [config/companies.yaml](/C:/projects/job-discovery-browser-copilot/config/companies.yaml) is created before changes
- restricted/manual-only candidates are skipped
- candidates without a valid URL are skipped
- candidates still need human review before approval

## Limitations

- Automatic company-name-only web discovery is still future work.
- Human review is still required before approval.
- Some new candidates may not carry enough metadata to become a full watchlist record automatically.
- If sector/category metadata is missing, the helper can still generate a candidate but may skip applying it to the main config.
- Some stale ATS-hosted sources may still need a manually supplied official website before a good replacement can be discovered.
