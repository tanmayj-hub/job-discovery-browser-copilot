# TD Manual Accuracy Audit

## Configured Source

* Company: TD
* Original landing page used during manual audit: https://careers.td.com/
* Current collection URL after Task 11.2 fix:
  https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=a30a87ed25634629aa6c3958aa2b91ea
* Actual job search page reached manually: https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs
* Source mode: human_in_loop
* ATS type if available: workday

## Manual Navigation Notes

Manual check process:

1. Opened the configured TD careers page: https://careers.td.com/
2. The page opened the TD Careers landing page.
3. Clicked the **Discover jobs at TD** button.
4. This redirected to the Workday job search page:

   * https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs
5. Applied **Canada** as the manual location/country filter.
6. Checked only the first 5 pages manually.
7. Found more relevant jobs than the MVP captured, so TD likely needs better pagination/location-filter handling.

## MVP Jobs Found

* MVP sample CSV: `C:\projects\job-discovery-browser-copilot\data\exports\audits\TD-mvp-sample.csv`

| # | MVP title                             | MVP location | MVP URL                                                                                                                                | Manual result | Relevant | Notes                                                                                     |
| - | ------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------- | ------------- | -------- | ----------------------------------------------------------------------------------------- |
| 1 | Lead Platform Engineer, TD Securities | -            | [Open job](https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Lead-Platform-Engineer--TD-Securities_R_1491997) | correct       | yes      | Verified manually on TD Workday. This is a real TD job posting. MVP found this correctly. |

## Jobs Found Manually That MVP Missed

* Manual template CSV: `C:\projects\job-discovery-browser-copilot\data\exports\audits\TD-manual-template.csv`

| title                                           | location         | URL                                                                                                                                                                                                                                                                                                                                                                    | why relevant                                                             | notes                                                                                   |
| ----------------------------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| IT Support Analyst, ION / MarketView Trading    | Toronto, Ontario | https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/IT-Support-Analyst--ION---MarketView--Trading_R_1489302?locationCountry=a30a87ed25634629aa6c3958aa2b91ea&remoteType=3f9079914dc21000b526dbcf4bd80001&remoteType=3f9079914dc21000b526dbcf4bd80000&remoteType=3f9079914dc21000b526db345d5c0000&remoteType=3f9079914dc21000b526dc6965b90000    | IT/support role relevant to cloud/support/admin target                   | Found manually after applying Canada filter. MVP did not capture this in the TD sample. |
| Software Engineer II, Salesforce                | Toronto, Ontario | https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Software-Engineer-II--Salesforce_R_1486443?locationCountry=a30a87ed25634629aa6c3958aa2b91ea&remoteType=3f9079914dc21000b526dbcf4bd80001&remoteType=3f9079914dc21000b526dbcf4bd80000&remoteType=3f9079914dc21000b526db345d5c0000&remoteType=3f9079914dc21000b526dc6965b90000                 | Software engineering role; possibly relevant depending on scoring target | Found manually after applying Canada filter. MVP did not capture this in the TD sample. |
| Sr IT Support Analyst, ION / MarketView Trading | Toronto, Ontario | https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Sr-IT-Support-Analyst---ION--MarketView--Trading_R_1489301?locationCountry=a30a87ed25634629aa6c3958aa2b91ea&remoteType=3f9079914dc21000b526dbcf4bd80001&remoteType=3f9079914dc21000b526dbcf4bd80000&remoteType=3f9079914dc21000b526db345d5c0000&remoteType=3f9079914dc21000b526dc6965b90000 | Senior IT support role relevant to support/admin/cloud-adjacent target   | Found manually after applying Canada filter. MVP did not capture this in the TD sample. |
| Lead Platform Engineer, TD Securities           | Toronto, Ontario | https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/Lead-Platform-Engineer--TD-Securities_R_1491997?locationCountry=a30a87ed25634629aa6c3958aa2b91ea&remoteType=3f9079914dc21000b526dbcf4bd80001&remoteType=3f9079914dc21000b526dbcf4bd80000&remoteType=3f9079914dc21000b526db345d5c0000&remoteType=3f9079914dc21000b526dc6965b90000            | Platform engineering role; directly relevant                             | MVP found this job. Manual check confirms it is correct.                                |

## Manual Accuracy Findings

### Precision

The MVP result for TD was correct.

* MVP jobs checked: 1
* Correct: 1
* Wrong: 0
* Unclear: 0

Initial precision finding:

```text
TD precision appears good for the sampled MVP result.
```

### Recall

Manual review found more relevant TD jobs than the MVP captured.

* MVP relevant jobs found: 1
* Manual relevant jobs found in first 5 pages: at least 4
* Missed jobs found manually: at least 3
* Manual review did not cover all pages, so there may be more missed jobs.

Initial recall finding:

```text
TD recall appears low. MVP likely needs better TD/Workday pagination and Canada-filter handling.
```

## Main Issue Noticed

The configured TD careers URL starts at:

```text
https://careers.td.com/
```

But the actual searchable jobs page is:

```text
https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs
```

Manual process required:

```text
TD careers landing page
  -> Discover jobs at TD
  -> Workday jobs page
  -> Canada filter
  -> multiple pages of results
```

The MVP only captured one TD job, while manual review found multiple relevant jobs in the first 5 pages.

Likely issue:

```text
MVP is not fully paginating through TD Workday results and/or is not applying the Canada filter consistently.
```

## Questions For Code Investigation

1. Does the current browser collector click through all pages on Workday job boards?
2. Does it stop after the first page?
3. Does it detect and click Workday pagination buttons?
4. Does it apply Canada/location scope correctly?
5. Does it collect all visible jobs before scoring?
6. Does it have a page limit or timeout that stops early?
7. Should TD use the direct Workday jobs URL instead of the TD landing page URL?

## Task 11.2 Engineering Findings

### What The Previous MVP Was Doing

Before the targeted TD fix, the collector had three recall weaknesses for this source:

1. TD config started from the careers landing page instead of the searchable Workday jobs URL.
2. The browser extraction path only paginated up to 2 pages.
3. Visible extraction was also capped to the first 20 deduped cards total.

Practical effect:

```text
TD could collect too little even when Workday pagination existed,
and the Canada scope was not reliably pre-applied.
```

### What Changed In Task 11.2

The targeted TD/Workday fix now:

1. Uses the official direct TD Workday jobs URL.
2. Applies the verified Canada scope in the URL query.
3. Increases safe pagination to 10 pages per source.
4. Allows extraction beyond the first 20 total cards during paginated collection.
5. Records pagination diagnostics and per-page extraction counts.

### TD Diagnostic Rerun

Diagnostic report:

* `docs/audits/TD-collection-diagnostic.md`

Rerun summary:

* Starting URL: direct TD Workday Canada-filtered URL
* Pagination detected: yes
* Pages visited: 10
* Jobs extracted per page:
  * 20
  * 20
  * 19
  * 20
  * 16
  * 18
  * 20
  * 20
  * 16
  * 19
* Candidate jobs before scoring: 188
* Relevant jobs after scoring: 8
* Pagination stop reason: `max_pages_reached`

### Before / After

Before Task 11.2:

* Manual audit sample had only 1 MVP TD job.
* That 1 job was correct.
* Recall looked low.

After Task 11.2 rerun:

* TD collection surfaced 188 candidate jobs from the Canada-filtered Workday board.
* 8 jobs scored as relevant during the targeted rerun.
* Active saved TD rows now include multiple relevant support/platform/operations roles instead of only one sampled role.

### Manual Jobs Captured After Rerun

Captured by collection and saved as relevant:

* Lead Platform Engineer, TD Securities
* IT Support Analyst, ION / MarketView Trading
* Sr IT Support Analyst, ION / MarketView Trading

Captured by collection but not saved as relevant by current scoring:

* Software Engineer II, Salesforce

Reason:

```text
The rerun extracted the Salesforce job from the Workday board, but the current deterministic
score rules did not rank it as a relevant save in this targeted pass.
```

### Updated Conclusion

```text
TD was not first-page only in principle, but the previous implementation was too shallow:
landing-page entry was weak, pagination was capped too low, and extraction was truncated too early.
After switching TD to the direct official Workday Canada URL and expanding safe pagination,
recall improved materially.
```

## Summary

* MVP found 1 TD job.
* Manual audit confirmed the MVP job is correct.
* Manual audit found at least 3 additional relevant TD jobs in the first 5 pages.
* Task 11.2 rerun found 188 candidate jobs across 10 pages and 8 relevant candidates after scoring.
* The rerun captured the two manual IT Support jobs and the Lead Platform Engineer role.
* The Salesforce role was extracted but not saved as relevant under the current scoring rules.
* TD recall improved materially, but it is still bounded by the 10-page cap and current post-collection scoring rules.
