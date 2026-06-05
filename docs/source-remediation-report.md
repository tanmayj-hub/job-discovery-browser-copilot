# Source Remediation Report

## Purpose

This report summarizes the current source blockers that still need human follow-up after the Task 9.2 intervention hardening pass.

It focuses on operational cleanup only:

- separate active pending blockers from resolved history
- group repeated same-source pending events into one active item
- show a stable remediation label and suggested action for each source

## Snapshot

- Date: June 5, 2026
- Active pending source blockers: `4`
- Resolved/manual history rows: `15`

## Active Pending Sources

| Company | Source URL | Latest Reason | Occurrences | Remediation | Suggested Action |
| --- | --- | --- | ---: | --- | --- |
| Tech Mahindra | `https://careers.techmahindra.com/` | `login_required` | 2 | `login_required` | Open the public careers URL manually and confirm whether sign-in is mandatory. If login is required for job listings, keep the source manual-only. |
| Wipro | `https://careers.wipro.com/search?searchResultView=LIST` | `cookie_blocked` | 1 | `cookie_banner` | Open the source, clear or accept the blocking cookie banner, then rerun the source. |
| HCLTech | `https://careers.hcltech.com/` | `cookie_blocked` | 1 | `cookie_banner` | Open the source, clear or accept the blocking cookie banner, then rerun the source. |
| NTT DATA | `https://ca.nttdata.com/en/careers` | `login_required` | 1 | `login_required` | Open the public careers URL manually and confirm whether sign-in is mandatory. If login is required for job listings, keep the source manual-only. |

## Notes

- Tech Mahindra previously produced both `login_required` and `extraction_failed` pending rows for the same source. The queue now collapses those repeated same-source events into one active pending row with `occurrence_count = 2`.
- Wipro and HCLTech remain safe to inspect manually, but they should not auto-continue until the blocking cookie flow is cleared by the user.
- NTT DATA still needs a manual check to confirm whether the public listings remain reachable without account access.

## Resolved History Highlights

Recent resolved/manual history currently includes:

- DXC Technology `extraction_failed` -> `resolved`
- Vancity `extraction_failed` -> `resolved`
- BMO `cookie_blocked` -> `resolved`
- Accenture `location_selection_required` -> `resolved`
- ATB Financial `unclear_layout` -> `resolved`

Resolved history stays visible for audit, but it is no longer mixed into the active queue.

## Operational Outcome

Task 9.2 improves actionability in two ways:

1. The dashboard and reports can now show the real active blocker count instead of mixing pending and historical rows.
2. Source readiness now includes remediation guidance so the next human action is obvious without digging through raw intervention notes.

## Follow-Up Workflow

Task 10.1 adds a review-first refresh path for these cases:

```powershell
python -m src.main onboard refresh-sources --only-problem-sources --min-days-between-checks 7 --output data/exports/source-refresh-candidates.yaml
```

That workflow does not update the main watchlist automatically. It generates replacement candidates for manual review and approval first.
