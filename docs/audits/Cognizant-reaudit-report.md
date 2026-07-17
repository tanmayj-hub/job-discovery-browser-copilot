# Cognizant Re-Audit Report

- Official source: `https://careers.cognizant.com/ca-en/jobs/?keyword=&location=Canada&radius=100&lat=&lng=&cname=Canada&ccode=CA&pagesize=10#results`
- Canada confirmation: explicit `location=Canada`, `cname=Canada`, and `ccode=CA` URL parameters before pagination.
- Sort policy: `source_default_all_pages`; public newest-first control documented as unavailable.
- Page policy: `all_available` with a 500-page defensive ceiling.
- Audit outcome: incomplete. The live board did not expose a stable extractable listing in this environment, so no page traversal or fresh candidate snapshot was produced.
- Decision: remains unverified / needs review. Do not promote it until a live all-pages Canada-scoped extraction completes and is compared with the manual expected URLs.
