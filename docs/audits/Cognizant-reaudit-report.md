# Cognizant Re-Audit Report

## Official Canada Source
- Source: `https://careers.cognizant.com/ca-en/jobs/?keyword=&location=Canada&radius=100&lat=&lng=&cname=Canada&ccode=CA&pagesize=10#results`
- Canada parameters: `location=Canada`, `cname=Canada`, and `ccode=CA` are present before collection.
- Sort policy: `source_default_all_pages`; no public newest-first control could be inspected.

## Result
The official request returned HTTP `403` and displayed Cloudflare's security-verification page before the careers application loaded. No job cards, API/XHR requests, embedded job JSON, pagination, or public data endpoint were available to inspect.

## Decision
- Status: `blocked_by_cloudflare`
- Verification: not eligible
- Verified-only runs: excluded
- Normal daily retries: excluded
- Future action: perform a manual/source-health recheck only when the official public board is accessible without an anti-bot challenge.

No CAPTCHA, Cloudflare, proxy, stealth, or login bypass was attempted or added.
