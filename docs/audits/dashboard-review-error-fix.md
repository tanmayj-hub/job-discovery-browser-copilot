# Dashboard Review Error Fix

## Reported Error

The bottom-of-page error was:

```text
streamlit.errors.StreamlitDuplicateElementId: There are multiple checkbox
elements with the same auto-generated ID.
```

## Reproduction

The fresh RBC + Scotiabank review workspace was exercised by selecting multiple jobs,
editing review controls, changing filters, saving, and refreshing. The error appeared
after Streamlit rerendered the dashboard, with the traceback pointing to the
keyless `Verified companies only` checkbox in `render_jobs_tab()`.

## Root Cause

Every Streamlit tab renders during a page run. `render_jobs_tab()` was rendered in the
primary `All Verified Jobs` tab and a second time through the default Workspace
selection, so both copies created the same keyless checkbox. A second source of
fragile state was the explicit `st.rerun()` issued by each `View details` button,
which made selection depend on a full-page rerun and long URL-derived widget keys.

## Fix

- Remove the duplicate Workspace rendering path for `render_jobs_tab()`.
- Assign explicit stable keys to the remaining verified-job filters.
- Use a canonical URL-derived SHA-256 key for review widgets and forms.
- Use Streamlit's button callback to update the selected canonical job key before the
  normal rerun, rather than issuing a second explicit rerun for selection.
- Reset the selected key to the first valid filtered row when filters remove it.
- Write editable review CSVs atomically and refuse to overwrite an expected non-empty
  review slice when its working file cannot be loaded.

## Regression Coverage

Focused tests cover the single `render_jobs_tab()` call, stable widget keys, filtering
down to a valid replacement row, review-decision validation, decision persistence by
canonical job URL, and protection against an empty working-file overwrite.
