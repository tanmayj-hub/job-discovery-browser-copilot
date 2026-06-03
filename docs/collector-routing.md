# Collector Routing

## Purpose

The collector router decides which collection path is allowed for each company source based on `source_mode` and detected `ats_type`.

Task 3 adds the routing skeleton only. It does not add real API collectors yet.

## Current Routing

- `manual_only` -> never automated, returned as `manual_only`
- restricted boards such as LinkedIn, Indeed, and Glassdoor -> never automated, returned as `manual_only`
- `needs_url` -> skipped as `needs_url`
- `browser_allowed` -> routed to the existing browser collector
- `human_in_loop` -> routed to the existing browser collector and intervention-safe browser flow
- `api_allowed` -> returned as `api_collector_not_implemented` unless explicit browser fallback is enabled

## API-Friendly Sources

For now, `api_allowed` means the source looks eligible for API collection later. It does not mean a real API collector exists today.

When fallback is disabled, API-friendly ATS types such as Greenhouse, Lever, Ashby, and SmartRecruiters return:

- `status: api_collector_not_implemented`
- `collector: api_not_implemented`

When fallback is enabled explicitly, the router uses the browser collector and reports:

- `collector: browser_fallback`
- `fallback_used: true`

## Config

Routing fallback is controlled in [discovery.yaml](C:/projects/job-discovery-browser-copilot/config/discovery.yaml):

```yaml
routing:
  api_fallback_to_browser: false
```

The default is conservative and transparent.
