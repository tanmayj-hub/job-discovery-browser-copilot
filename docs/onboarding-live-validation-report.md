# Onboarding Live Validation Report

## Verdict

Task 10.1 live onboarding and source-refresh workflows are working locally with realistic inputs, and the main usability issue found during validation was fixed.

The workflows now generate reviewable candidate files without the earlier flood of locale-switcher and job-detail links. They are ready for a dashboard review UI next, with a few known limitations still left for later polish.

## Commands Run

```bash
python -m src.main onboard generate --input data/input/onboarding-validation-companies.csv --output data/exports/source-onboarding-candidates.yaml --live-discovery
python -m src.main onboard refresh-sources --only-problem-sources --force --output data/exports/source-refresh-candidates.yaml
python -m src.main onboard weekly-source-check --force --output data/exports/weekly-source-refresh-candidates.yaml
python -m src.main onboard weekly-source-check --output data/exports/weekly-source-refresh-candidates.yaml
python -m pytest
python -m ruff check .
```

## Input Companies Used

- Shopify, `https://www.shopify.com`
- Stripe, `https://stripe.com`
- Datadog, `https://www.datadoghq.com`
- Canonical, `https://canonical.com`
- FreshBooks, `https://www.freshbooks.com`
- PagerDuty, `https://www.pagerduty.com`

## Candidate Generation Summary

Command result:

- `generated: 35`
- `high_confidence: 0`
- `needs_review: 35`

Observed candidate coverage:

- Canonical: 23 same-domain browser candidates
- Stripe: 7 candidates, including public jobs pages and one restricted LinkedIn result
- Datadog: 2 candidates, both low-value for onboarding
- Shopify: 1 missing candidate record
- FreshBooks: 1 missing candidate record
- PagerDuty: 1 missing candidate record

Observed source modes:

- `browser_allowed`: 26
- `needs_url`: 6
- `manual_only`: 3

Observed ATS detection:

- No public ATS-hosted jobs board was discovered from these six homepages
- Restricted LinkedIn links were correctly marked `manual_only`

## Refresh-Source Summary

Command result:

- `generated: 18`
- `needs_review: 17`

Problem sources checked from the local database/state:

- HCLTech
- NTT DATA
- Tech Mahindra
- Wipro

Observed outcomes:

- NTT DATA produced one strong replacement candidate:
  - `https://career17.sapsf.com/career?company=NTTBCCANP`
  - detected ATS: `successfactors`
  - suggested source mode: `human_in_loop`
  - confidence: `high`
- HCLTech produced multiple same-domain careers candidates and one restricted LinkedIn candidate
- Tech Mahindra produced a restricted LinkedIn/manual-only candidate
- Wipro produced a restricted LinkedIn/manual-only candidate

Active problem sources were represented in the output, and restricted/manual-only handling stayed intact.

## Weekly Check Summary

Forced run result:

- `generated: 18`
- output written to `data/exports/weekly-source-refresh-candidates.yaml`

Immediate follow-up run without `--force`:

- `generated: 0`

State file behavior:

- `data/exports/source-health-state.json` was updated with fresh `last_health_check_at` timestamps on June 5, 2026
- Entries were recorded for HCLTech, NTT DATA, Tech Mahindra, and Wipro

Output file behavior:

- the forced weekly run wrote candidate output
- the non-forced follow-up run wrote an empty candidate file because no sources were due yet

Skip behavior:

- min-days-between-checks behavior worked as expected
- no additional sources were refreshed on the immediate second run

## Candidate Quality Findings

What looked good:

- obvious ATS links still classify correctly
- restricted portals still remain review-only and are not auto-applied
- same-domain careers discovery is now much less noisy than the first validation pass
- numeric job-detail links are no longer treated as onboarding candidates
- locale-switcher variants are no longer treated as distinct onboarding candidates

What still needs later polish:

- some global companies still generate multiple same-domain careers subpages that are technically valid but repetitive for human review
- HCLTech still surfaced several region-specific careers pages
- Canonical still surfaced several department-level careers pages
- homepage-only discovery did not find a useful public careers candidate for Shopify, FreshBooks, or PagerDuty from this limited crawl
- Datadog surfaced a restricted LinkedIn result instead of a useful public careers source

## Bugs Found

Validation found one material usability bug:

- live discovery treated many same-domain career-adjacent links as review candidates
- this created very noisy candidate files, especially for Stripe and Canonical
- examples included locale-switcher variants and numeric job-detail pages

## Bugs Fixed

Implemented during this validation pass:

- separated discovery keyword text checks from URL structure checks
- added stronger same-domain careers-index detection
- filtered equivalent locale-switcher variants
- filtered numeric job-detail links under careers paths
- added focused tests for both cases

Impact after fix:

- onboarding live-discovery output dropped from 328 candidates to 35 for the same six-company input
- refresh output dropped from 71 candidates to 18 for the same local problem-source set

## Remaining Limitations

- same-domain discovery still returns multiple reviewable section pages for some large career sites
- weekly non-forced runs currently overwrite the weekly output file with an empty candidate list when nothing is due
- live discovery remains intentionally shallow and homepage-seeded only
- no external search provider is used in this task
- review and approval still happen from files, not a dashboard queue yet

## Recommendation

Yes, the next logical step is a dashboard review UI for onboarding candidates and source-refresh candidates.

The current backend is stable enough for that step:

- live discovery is working
- refresh and weekly source checks are working
- restricted/manual-only behavior is preserved
- candidate quality is reviewable after the noise fix

The next UI should focus on:

- sorting and collapsing similar candidates per company
- approving or rejecting candidates
- showing evidence and current-vs-candidate URL comparison
- preserving auditability for source changes
