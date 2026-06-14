# RBC Manual URL Scope Review

## Purpose
- Separate the old RBC manual URLs from the clean broad Canada-only MVP policy.
- Prevent subcategory-filtered manual searches from being counted as collection misses against the current trusted collector.

## Current MVP Policy For RBC
- Official site only
- Public `Country=Canada` facet applied before pagination
- Broad Canada-only listing
- No category or subcategory filters
- No team, function, or keyword filters
- No city, province, remote, or hybrid filters
- Current page cap: `10`

## Old Manual Search Context
- Manual career page: `https://jobs.rbc.com/ca/en/search-results?from=140&s=1`
- Manual filter used:
  `Canada, sort by most recent, sub category= technology, project and program management, operations and business management`
- Manual pages checked: first `15`

## URL Classification
| Manual URL | Classification | Why |
| --- | --- | --- |
| https://jobs.rbc.com/ca/en/job/R-0000176580/Sr-IAM-Engineer-Vault-Specialist-CyberArk-Hashicorp-Global-Security | outside_current_listing_scope_subcategory_filter | This URL came from the earlier subcategory-filtered manual search and does not appear in the broad Canada-only scored-candidate export used by the trusted MVP run. |
| https://jobs.rbc.com/ca/en/job/R-0000174330/Staff-Cloud-Security-Engineer-Global-Security | outside_current_listing_scope_subcategory_filter | This URL came from the earlier subcategory-filtered manual search and does not appear in the broad Canada-only scored-candidate export used by the trusted MVP run. |
| https://jobs.rbc.com/ca/en/job/R-0000174266/DevOps-Platform-Solution-Engineer | outside_current_listing_scope_subcategory_filter | This URL came from the earlier subcategory-filtered manual search and does not appear in the broad Canada-only scored-candidate export used by the trusted MVP run. |
| https://jobs.rbc.com/ca/en/job/R-0000160538/Senior-DevOps-Engineer | outside_current_listing_scope_subcategory_filter | This URL came from the earlier subcategory-filtered manual search and does not appear in the broad Canada-only scored-candidate export used by the trusted MVP run. |

## Fair Recall Interpretation
- These 4 URLs should not count as `missed_by_collection` for the current broad Canada-only MVP policy.
- They were located through an intentionally narrower manual search than the production collector is allowed to use in this task.
- If any of these URLs later appear in a clean broad Canada-only manual audit within the same page cap, they can be reclassified then.

## Conclusion
- The old RBC manual URLs are not evidence of a current Canada-scope bug.
- RBC still needs a new clean manual audit that matches the production policy exactly before promotion.
