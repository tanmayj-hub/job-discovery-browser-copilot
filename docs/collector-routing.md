# Collector Routing

## Purpose

The collector router decides which collection path is allowed for each company source based on `source_mode` and detected `ats_type`.

Task 3 added the routing skeleton. Task 4 adds real public API collectors for Greenhouse and Lever only.

## Current Routing

- `manual_only` -> never automated, returned as `manual_only`
- restricted boards such as LinkedIn, Indeed, and Glassdoor -> never automated, returned as `manual_only`
- `needs_url` -> skipped as `needs_url`
- `browser_allowed` -> routed to the existing browser collector
- `human_in_loop` -> routed to the existing browser collector and intervention-safe browser flow
- `api_allowed + greenhouse` -> routed to the Greenhouse public jobs API collector
- `api_allowed + lever` -> routed to the Lever public postings API collector
- `api_allowed + ashby` -> returned as `api_collector_not_implemented` unless explicit browser fallback is enabled
- `api_allowed + smartrecruiters` -> returned as `api_collector_not_implemented` unless explicit browser fallback is enabled
- other `api_allowed` sources -> returned as `api_collector_not_implemented` unless explicit browser fallback is enabled

## API Sources

Greenhouse and Lever now use public ATS endpoints only:

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`
- Lever: `https://api.lever.co/v0/postings/{site}?mode=json`

These collectors:

- collect broadly from the public job feed
- do not send Cloud/DevOps/Admin role keywords into the ATS API
- normalize jobs into the shared collector model
- leave scoring, dedupe, and saving to the downstream daily-run flow
- pass `external_job_id`, `ats_type`, and `board_slug` into storage for stronger dedupe

Ashby and SmartRecruiters are still classified as `api_allowed`, but their collectors are not implemented yet.

When fallback is disabled, unimplemented API-friendly ATS types such as Ashby and SmartRecruiters return:

- `status: api_collector_not_implemented`
- `collector: api_not_implemented`

If a Greenhouse or Lever API call fails, the router returns the API error directly unless explicit fallback is enabled.

When fallback is enabled explicitly, the router may use the browser collector and reports:

- `collector: browser_fallback`
- `fallback_used: true`

This fallback is explicit, never silent.

## Config

Routing fallback is controlled in [discovery.yaml](C:/projects/job-discovery-browser-copilot/config/discovery.yaml):

```yaml
routing:
  api_fallback_to_browser: false
```

The default is conservative and transparent.
