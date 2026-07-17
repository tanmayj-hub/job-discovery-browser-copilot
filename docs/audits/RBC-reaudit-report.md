# RBC Re-Audit Report

- Official source: `https://jobs.rbc.com/ca/en/search-results`
- Production policy: Canada scope, newest-first requested, 20-page cap. The fresh production run completed with 201 discovered candidates and 10 relevant saved jobs.
- Audit policy: Canada scope, newest-first, 75-page verification-only cap.
- Audit outcome: incomplete. The public Country=Canada facet triggers a client-side navigation race during the long diagnostic pass, so no fresh 75-page candidate snapshot was produced.
- Stop reason: `source_error` (`Page.content` observed while the board was replacing its results surface).
- Decision: remains `needs_manual_audit`; it is not promoted from the 20-page production result.
- Required follow-up: stabilize the RBC board transition/readiness signal, then regenerate the 75-page audit export and compare it to the current manual fixture.
