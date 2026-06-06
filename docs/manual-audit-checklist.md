# Manual Audit Checklist

Use this checklist while filling:

- [accuracy-audit-sample.csv](/C:/projects/job-discovery-browser-copilot/data/exports/accuracy-audit-sample.csv)
- [manual-job-audit-template.csv](/C:/projects/job-discovery-browser-copilot/data/exports/manual-job-audit-template.csv)

For every company:

- manually verify MVP rows in `accuracy-audit-sample.csv`
- manually record relevant jobs found on the official source in `manual-job-audit-template.csv`
- do not add fake results

## TD

- Configured career URL:
  - `https://careers.td.com/`
- Manually check:
  - job detail pages are real
  - title and location are correct
  - relevant jobs visible on the official source are captured
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## RBC

- Configured career URL:
  - `https://jobs.rbc.com/en`
- Manually check:
  - real job posting vs category/search pages
  - title/location accuracy
  - relevant missing jobs on official results pages
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## BMO

- Configured career URL:
  - `https://jobs.bmo.com/global/en/home`
- Manually check:
  - official job-detail pages
  - whether broad role titles are still relevant
  - whether non-Canadian rows should be marked not relevant
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## Deloitte

- Configured career URL:
  - `https://www.deloitte.com/ca/en/careers.html`
- Manually check:
  - official Canada careers navigation
  - real posting pages vs marketing pages
  - relevant missing jobs
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## CGI

- Configured career URL:
  - `https://www.cgi.com/canada/en-ca/careers`
- Manually check:
  - official CGI Canada jobs pages
  - title/location correctness
  - whether MVP missed relevant postings
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## IBM Consulting

- Configured career URL:
  - `https://www.ibm.com/careers`
- Manually check:
  - official IBM job-detail pages
  - Canadian relevance of saved roles
  - whether out-of-country roles should be marked not relevant
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## Sun Life

- Configured career URL:
  - `https://sunlife.wd3.myworkdayjobs.com/Experienced-Jobs`
- Manually check:
  - workday result rows vs official job details
  - whether saved roles are in the intended geography/scope
  - relevant missing jobs
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## Canada Life

- Configured career URL:
  - `https://jobs.canadalife.com/go/All-Jobs/9170201?locale=en_US`
- Manually check:
  - official job listings and detail pages
  - title/location correctness
  - whether relevant roles were missed
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## Wipro

- Configured career URL:
  - `https://careers.wipro.com/?locale=en_US`
- Manually check:
  - public jobs visibility
  - whether blocked/cookie issues limit recall
  - relevant jobs visible manually on the official source
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## NTT DATA

- Configured career URL:
  - `https://ca.nttdata.com/en/careers`
- Manually check:
  - public job visibility
  - whether login/manual limitations affect recall
  - relevant jobs visible manually on the official source
- Record MVP validation in:
  - `data/exports/accuracy-audit-sample.csv`
- Record manually found relevant jobs in:
  - `data/exports/manual-job-audit-template.csv`
- Notes:
  - ________________________________________

## After The Checklist

1. Validate the files:

```powershell
python -m src.main audit validate-files --mvp data/exports/accuracy-audit-sample.csv --manual data/exports/manual-job-audit-template.csv
```

2. Only after manual fields are filled, run compare:

```powershell
python -m src.main audit compare --mvp data/exports/accuracy-audit-sample.csv --manual data/exports/manual-job-audit-template.csv --output docs/accuracy-audit-report.md
```
