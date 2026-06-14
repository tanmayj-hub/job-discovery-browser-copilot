# Next Bank Fault Table

| Company | Configured URL | Manual URLs available | Scope status | Trusted run | Diagnostic run | Manual recall | Likely failure | Fix plan |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| RBC | `https://jobs.rbc.com/ca/en/search-results?from=140&s=1` | 4 | confirmed after public `Country=Canada` facet | `100` discovered, `4` saved | `100` discovered, `4` relevant, `10` pages | old manual URLs came from extra subcategory filters and are now classified separately from broad-policy misses | not a Canada-scope failure anymore; current mismatch is between the broad trusted listing and a narrower manual filtered search | keep `needs_manual_audit`; use the clean broad-policy audit pack before promotion |
| Scotiabank | `https://jobs.scotiabank.com/search/?createNewAlert=false&q=&locationsearch=canada` | 5 | confirmed by Canada-filtered URL | `383` discovered, `6` saved | `383` discovered, `6` relevant, `15` pages | `4 / 5` extracted_and_relevant, `1 / 5` extracted_but_rejected_by_scoring | page-depth cap was too low for the manual expected URLs | fixed with a per-company 15-page cap; promoted to verified usable |
