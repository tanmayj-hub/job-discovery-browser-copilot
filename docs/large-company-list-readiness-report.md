# Large Company List Readiness Report

## Verdict

The 150-company spreadsheet has been audited for MVP input readiness.
Configured companies are separated from additional reviewable source candidates,
and missing/manual-only rows are clearly marked without changing config.

## Input Files Inspected

- `C:\projects\job-discovery-browser-copilot\data\input\Rishi canada companies list (1).xlsx`
- `C:\projects\job-discovery-browser-copilot\data\input\rishi\companies.xlsx`

## Total Companies In Spreadsheet

- 150

## Already Configured Count

- 34

## Usable URL Count

- 44

## Missing URL Count

- 106

## Spreadsheet Hyperlink Count

- 23

## Starter URL Match Count

- 34

## Source Mode Distribution

- `needs_url`: 106
- `browser_allowed`: 36
- `human_in_loop`: 8

## ATS Type Distribution

- `none`: 142
- `workday`: 5
- `ultipro`: 2
- `oracle_hcm`: 1

## High-Priority Companies Ready Now

- Accenture
- ATB Financial
- Aviva Canada
- BMO
- Canada Life
- Capgemini
- CGI
- CIBC
- Cognizant
- Definity Financial (Economical)
- Deloitte
- Desjardins
- DXC Technology
- EQ Bank (Equitable Bank)
- EY
- Genpact
- HCLTech
- iA Financial Group
- IBM Consulting
- Infosys
- ... and 23 more

## High-Priority Companies Needing URL/Manual Review

- Amazon / AWS
- Apple
- Atlassian
- Benevity
- BlackBerry
- Block / Square
- Borrowell
- Ceridian/Dayforce
- Cisco
- Clio
- Constellation Software
- Coveo
- D2L (Desire2Learn)
- Descartes Systems Group
- Fairfax Financial
- FreshBooks
- Google
- Great-West Lifeco
- Hootsuite
- Interac
- ... and 24 more

## Companies Safe To Test In Next Batch

- Aviva Canada
- Canada Life
- Definity Financial (Economical)
- iA Financial Group
- Intact Financial
- Manulife
- RSA Canada (Intact)
- Sun Life
- The Co-operators
- Wawanesa Insurance

## Companies Not Ready For Testing

- AIMCo
- Air Canada
- Air Transat
- Alberta Health Services
- Alectra Utilities
- AltaGas
- Amazon / AWS
- Apple
- Atlassian
- BC Hydro
- BCI (British Columbia Investment Management)
- Bell
- Benevity
- BlackBerry
- Block / Square
- Borrowell
- Canada Post
- Canada Revenue Agency (CRA)
- Canadian Tire
- CDPQ
- ... and 86 more

## Recommended Batch Plan

- Batch 1: current configured 34 (`34` rows matched config in this audit)
- Batch 2: additional companies with confirmed URLs (`10` candidates ready for review/apply)
- Batch 3: companies needing website URL/live discovery/manual review (`106` rows)

## Risks And Limitations

- Spreadsheet display text without a hyperlink is treated as unverified and not auto-used as a URL.
- Restricted boards such as LinkedIn, Indeed, and Glassdoor remain manual-only.
- No candidates were auto-applied to `config/companies.yaml`.
- This is a readiness audit only, not a full 150-company discovery run.
- Some alias or duplicate matches may still require human review.

## Candidate Generation Summary

- Reviewable candidates generated: 10
- High-confidence candidates: 0
- Manual-only candidates: 0
