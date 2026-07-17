# RBC Audit Performance Profile

## Probe
- Date: 2026-07-17
- Command: `python -m src.main audit diagnose-company-collection --company "RBC" --page-start 1 --page-end 3 --use-audit-scope`
- Source: `https://jobs.rbc.com/ca/en/search-results`
- Scope: public Country=Canada facet confirmed before pagination.
- Sort: Most recent confirmed before pagination.
- Pages: 1-3, 30 candidates.

## Previous Limitation
The previous 75-page attempt progressed past the SPA navigation race but exceeded the 15-minute command window. The normal path repeatedly called `page.content()` and parsed the large replacement DOM on every page and settle poll.

## Optimized Measurements
| Metric | Page 1 | Page 2 | Page 3 |
| --- | ---: | ---: | ---: |
| Live-card extraction | 16.42 ms | 175.54 ms | 14.71 ms |
| Result fingerprint | 6.56 ms | 33.92 ms | 15.99 ms |
| Post-click settle | n/a | 3647.79 ms | 2615.34 ms |
| Full-page serializations | 0 | 0 | 0 |

- Initial navigation: 1082.16 ms
- Initial post-navigation settle: 9752.72 ms
- Scoring/normalization for 30 candidates: 83.90 ms
- Full-page serializations: `0`

## Result
RBC now extracts the visible public `data-ph-at-id="job-link"` cards and uses ordered visible job URLs for transition fingerprints. Full-document serialization remains only a bounded fallback when the focused card surface is empty or unsupported; it is not part of the successful RBC page path.
