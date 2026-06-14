# Autonomous Company Audit Template

Use this prompt when you want Codex to take a batch of companies, audit them with minimal back-and-forth, and only return when the company is fixed, promoted, or genuinely blocked.

---

You are working in my existing repo: `job-discovery-browser-copilot`.

Goal:
Audit the following companies end to end and keep going autonomously until each company is either:

- fixed and re-run successfully
- promoted into the verified usable slice
- or blocked by a real user-only issue such as CAPTCHA, login, missing official Canada URL, or missing manual expected URLs

Companies to audit:

`[PASTE COMPANY LIST HERE]`

Rules:

- Do not add new companies outside the list above.
- Do not use LinkedIn, Indeed, Glassdoor, Google, or broad search APIs as collection sources.
- Do not bypass login or CAPTCHA.
- Do not auto-apply.
- Do not switch to non-official sites.
- Do not use broad global scraping as the verified source.
- Keep the collect-first, score-later workflow intact.
- Make narrow scoring fixes only when evidence shows collection succeeded but relevant roles were rejected incorrectly.

For each company, do this:

1. Inspect local config, docs, verified-company YAML, manual expected job YAML, and prior audit artifacts for that company.
2. Run the trusted source workflow using the official configured source.
3. Confirm Canada scope before pagination whenever possible.
4. If the configured URL is not Canada-scoped enough, fix it using a safe official Canada URL or a public pre-pagination Canada filter.
5. Run the company daily workflow or diagnostic workflow as needed.
6. If the source fails, diagnose the source-specific issue and fix it autonomously where safe.
7. If collection misses manually supplied official job URLs, fix extraction, pagination, canonicalization, or source-specific navigation where safe.
8. If the jobs are collected but not saved, generate score explanations and make only narrow justified scoring fixes.
9. Re-run after each fix until the source behavior is stable.
10. Promote the company only when the latest evidence supports promotion.

Use these commands when useful:

```bash
python -m src.main daily-run --company "Company Name"
python -m src.main audit diagnose-company-collection --company "Company Name" --use-audit-scope
python -m src.main audit company-pack --company "Company Name"
python -m src.main audit compare-manual-urls --input data/exports/audits/manual-expected-jobs-next-slice.yaml
python -m src.main audit explain-score --company "Company Name" --title "Exact Title" --include-rejected
```

Promotion rules:

- Promote only if the company uses an official public source
- Canada scope is confirmed before pagination or through a stable official Canada URL
- no active blocking intervention remains
- the latest run is stable
- collection recall is acceptable against manual expected URLs when such URLs exist
- suspicious saved rows are not a sign of a broken source

When to stop and ask me:

- login is required
- CAPTCHA appears
- there is no safe official Canada source or filter and you cannot derive one confidently
- the company needs manual expected URLs and none exist
- the public source is unclear enough that a user decision is truly required

Expected final response format:

1. Companies fixed and promoted
2. Companies fixed but not promoted
3. Companies blocked and why
4. Exact files changed
5. Exact commands run
6. Latest run results per company
7. Any scoring changes made and why

Do not stop after analysis. Keep going until the companies are resolved or genuinely blocked.
