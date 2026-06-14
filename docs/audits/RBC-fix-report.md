# RBC Fix Report

## Current Trusted Source
- Official source URL: `https://jobs.rbc.com/ca/en/search-results?from=140&s=1`
- Canada scope method: public `Country=Canada` facet applied before pagination
- Trusted policy: Canada-only broad listing, with no subcategory, function, keyword, city, province, remote, or hybrid filters

## Fresh Trusted Run
- Status: completed
- Source scope status: `canada_scope_confirmed`
- Source scope method: `ui_filter`
- Source scope reason: RBC's public `Country=Canada` facet was applied before pagination.
- Final URL reached: `https://jobs.rbc.com/ca/en/search-results?from=90&s=1`
- Pages visited: `10`
- Pagination stop reason: `max_pages_reached`
- Jobs discovered: `100`
- Jobs scored: `100`
- Relevant jobs saved: `4`
- Explicit non-Canada rejected: `0`
- Suspicious saved rows in the clean trusted run: `0`

## Saved Jobs From The Clean Canada-Only Run
| Title | Location | Score | Tier | URL |
| --- | --- | ---: | --- | --- |
| Lead Business Systems Analyst | TORONTO, Ontario, Canada | 30 | adjacent_customer_facing_technical_fit | https://jobs.rbc.com/ca/en/job/R-0000169486/Lead-Business-Systems-Analyst |
| Senior Solution Architect-AI/ML | TORONTO, Ontario, Canada | 21 | adjacent_customer_facing_technical_fit | https://jobs.rbc.com/ca/en/job/R-0000167744/Senior-Solution-Architect-AI-ML |
| Senior Business Systems Analyst | TORONTO, Ontario, Canada | 15 | adjacent_customer_facing_technical_fit | https://jobs.rbc.com/ca/en/job/R-0000167721/Senior-Business-Systems-Analyst |
| Expert Banking Advisor | BROSSARD, Quebec, Canada | 8 | core_target_fit | https://jobs.rbc.com/ca/en/job/R-0000145401/Expert-Banking-Advisor |

## Old Manual URL Scope Decision
- The earlier RBC manual URLs were gathered using extra public subcategory filters.
- Those filters are outside the current trusted MVP collection policy.
- The four old URLs do not appear in the broad Canada-only scored-candidate export for the current page cap.
- Under the current policy, those rows should not be treated as `missed_by_collection`.

## Verification Decision
- Decision: `needs_manual_audit`

## Why RBC Was Not Promoted In This Task
- The trusted RBC run itself is healthy.
- Canada scope is confirmed before pagination.
- The remaining gap is not a proven collection bug under the current policy.
- RBC still needs a clean manual audit performed apples-to-apples against the broad Canada-only listing used by the MVP.

## Next Requirement To Promote RBC
- Complete the manual review pack in [docs/audits/RBC-clean-canada-only-audit-pack.md](/C:/projects/job-discovery-browser-copilot/docs/audits/RBC-clean-canada-only-audit-pack.md).
- If the user finds broad Canada-only RBC jobs inside the same page cap that the MVP should have captured but did not, then RBC should stay blocked for more collector work.
- If the user does not find such misses, RBC can be promoted safely in the next pass.
