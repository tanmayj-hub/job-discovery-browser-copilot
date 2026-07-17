# Cognizant Source Architecture

- Official entry URL: `https://careers.cognizant.com/ca-en/jobs/?keyword=&location=Canada&radius=100&lat=&lng=&cname=Canada&ccode=CA&pagesize=10#results`
- Canada filter: URL includes `location=Canada`, `cname=Canada`, and `ccode=CA` before any collection attempt.
- Sort policy: `source_default_all_pages`; no usable public newest-first control was available to inspect.
- Rendering/data source: not observable. The official request returned HTTP 403 and rendered Cloudflare's security-verification interstitial rather than a job board.
- Embedded JSON, XHR/fetch, GraphQL, iframe, pagination, and load-more: not available because the security verification blocked public listing access before application initialization.
- Chosen collector method: none. The source remains browser-assisted/manual review only until its official public board is accessible without an anti-bot challenge.
- Rejected alternatives: no external aggregators, proxy rotation, stealth automation, or CAPTCHA/anti-bot bypass is permitted by this project.

## Verification Decision

This is a genuine public-source blocker in the current environment. Cognizant remains unverified and cannot be promoted without a fresh Canada-scoped, all-results official listing snapshot and manual URL recall.
