# RBC And Scotiabank Review Feedback Analysis

## Reviewed Dataset

- Reviewed jobs: 16
- Rows with notes: 14
- Useful: 7
- Maybe: 6
- Not useful: 2
- False positive: 1
- Already applied: 0
- Saved for later: 0

## Feedback Patterns

- Exact DevOps, Application Support Analyst, and Solution Engineer titles were
  consistently considered valuable but under-scored.
- Senior roles were still worth surfacing as `Maybe` or `Useful`; seniority is a ranking
  penalty and risk flag, not an automatic exclusion.
- The bilingual Application Support Analyst was personally unsuitable because of the
  language requirement. It remains technically relevant and does not create a global
  scoring exclusion.
- The finance networking event was a true false positive: `networking` referred to a
  recruiting event rather than IT networking.
- The Global Head IAM role was technically related but above the target seniority level;
  executive-title handling now makes that risk explicit and removes it from the active
  queue.

## Calibration Applied

- Added a DevOps Engineer title-family bonus that also applies to senior DevOps titles.
- Added exact-title core bonuses for Application Support Analyst and Application
  Support Engineer, avoiding a broad boost for senior or specialized variants.
- Added exact-title adjacent bonuses for Solution Engineer and Solutions Engineer.
- Added a hard reject for `networking event` titles.
- Added an executive-title penalty for `Global Head` and `Head of` titles.

## Before And After Reviewed Roles

| Company | Title | Decision | Old | New | Old tier | New tier | Result |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| RBC | Senior Technical Support Analyst | Maybe | 9 | 9 | Core | Core | Preserved; senior risk remains. |
| RBC | Senior Technical Systems Analyst - Application Support | Maybe | 9 | 9 | Core | Core | Preserved; senior risk remains. |
| RBC | Senior Application Support Analyst | Maybe | 1 | 1 | Core | Core | Preserved; intentionally not broadly boosted. |
| RBC | Senior Site Reliability Engineer | Useful | 42 | 42 | Core | Core | Preserved. |
| RBC | Senior Site Reliability Engineer (no longer current) | Useful | 42 | - | Core | - | Preserved in backup; absent from current listing. |
| RBC | DevOps Engineer | Useful | 57 | 75 | Core | Core | Raised into the requested 70-80 range. |
| Scotiabank | ScotiaMcLeod Branch Systems Administrator | Useful | 57 | 57 | Core | Core | Preserved. |
| RBC | Senior DevOps Engineer | Useful | 34 | 52 | Core | Core | Raised into the requested 50-60 range. |
| RBC | Application Support Analyst | Useful | 24 | 52 | Core | Core | Raised into the requested 50-60 range. |
| RBC | Enterprise Applications Support Engineer (EDI/MFT) | Maybe | 24 | 24 | Core | Core | Preserved; no broad specialized-support boost. |
| Scotiabank | Solution Engineer | Useful | 24 | 60 | Adjacent | Adjacent | Raised into the requested 60-70 range. |
| Scotiabank | Bilingual Application Support Analyst | Not useful | 12 | 12 | Core | Core | Technically relevant; language preference remains personal fit. |
| RBC | Senior Enterprise Applications Support Engineer | Maybe | 9 | 9 | Core | Core | Preserved. |
| RBC | Financial Planning Networking Event | False positive | 8 | 0 | Core | Not relevant | Removed by precise event-title rejection. |
| Scotiabank | Global Head of IAM | Not useful | 8 | 0 | Core | Not relevant | Removed by executive-title penalty. |
| RBC | Senior Network Analyst | Maybe | 1 | 1 | Core | Core | Preserved without broad network-analyst promotion. |

## Distribution After Calibration

- Useful: 5 core roles, 1 adjacent technical role, and 1 historical role no longer in
  the live listing.
- Maybe: all 6 remain core technical candidates with seniority or fit caveats.
- Not useful: one technical bilingual role remains relevant; the executive role is now
  excluded.
- False positive: the single finance networking-event false positive is excluded.

## Outcome

Useful roles remain selected unless they are no longer present in the current live
listing. The only exclusion rule added is the repeatable recruiting-event title
pattern; personal preferences such as bilingual requirements did not become global
scoring rules.
