# RBC Clean Canada-Only Audit Pack

## Source Used By MVP
- Company: RBC
- Official source URL: `https://jobs.rbc.com/ca/en/search-results?from=140&s=1`
- Source mode: `browser_allowed`
- Canada scope method: public `Country=Canada` facet applied before pagination
- Current trusted page cap: `10`

## Current Clean Run Snapshot
- Jobs discovered: `100`
- Jobs scored: `100`
- Jobs saved: `4`
- Explicit non-Canada rejected: `0`
- Pagination stop reason: `max_pages_reached`

## Saved Jobs From The Current RBC Run
| # | Title | Location | Score | Relevance Tier | URL |
| ---: | --- | --- | ---: | --- | --- |
| 1 | Lead Business Systems Analyst | TORONTO, Ontario, Canada | 30 | adjacent_customer_facing_technical_fit | https://jobs.rbc.com/ca/en/job/R-0000169486/Lead-Business-Systems-Analyst |
| 2 | Senior Solution Architect-AI/ML | TORONTO, Ontario, Canada | 21 | adjacent_customer_facing_technical_fit | https://jobs.rbc.com/ca/en/job/R-0000167744/Senior-Solution-Architect-AI-ML |
| 3 | Senior Business Systems Analyst | TORONTO, Ontario, Canada | 15 | adjacent_customer_facing_technical_fit | https://jobs.rbc.com/ca/en/job/R-0000167721/Senior-Business-Systems-Analyst |
| 4 | Expert Banking Advisor | BROSSARD, Quebec, Canada | 8 | core_target_fit | https://jobs.rbc.com/ca/en/job/R-0000145401/Expert-Banking-Advisor |

## Apples-To-Apples Manual Audit Instructions
1. Open the official RBC career page:
   `https://jobs.rbc.com/ca/en/search-results?from=140&s=1`
2. Apply `Country=Canada` only.
3. Do not apply category, subcategory, function, keyword, city, province, remote, or hybrid filters.
4. Check the same page cap as the MVP:
   first `10` pages only.
5. Compare what you see against the 4 saved jobs above.
6. If you find additional jobs inside those same first 10 broad Canada-only pages that the MVP should have captured, record them below.
7. If a job is only visible after adding extra subcategory or role filters, do not count it against the current MVP policy.

## Blank Section For New Clean Manual RBC URLs
| Title | Location | URL | Why MVP should have found it in broad Canada-only first 10 pages | Notes |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |

## Decision After Manual Review
- If no clean broad Canada-only misses are found, RBC is ready for promotion in the next pass.
- If clean misses are found inside the same first 10 broad Canada-only pages, RBC should stay out of verified-only until those misses are fixed.
