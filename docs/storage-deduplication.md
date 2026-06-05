# Storage And Deduplication

## Purpose

Task 5 strengthens local job storage so repeated runs update the same job row instead of creating duplicates, especially for ATS and JSON-LD sources that expose stable external job IDs.

## Stored Metadata

The `jobs` table now supports these ATS-friendly metadata fields:

- `external_job_id`
- `ats_type`
- `board_slug`
- `raw_payload_json`
- `content_hash`
- `first_seen_at`
- `last_seen_at`
- `last_updated_at`

Legacy fields such as `first_seen`, `last_seen`, and `updated_at` remain for backward compatibility with existing local databases and dashboard views.

## Identity Priority

Job identity now follows this priority order:

- `company_name + ats_type + board_slug + external_job_id`
- `company_name + ats_type + external_job_id`
- normalized `job_url`
- `company_name + normalized_title + normalized_location + source_name`

This means Greenhouse, Lever, and Ashby jobs prefer ATS-provided stable IDs, static JSON-LD pages can also preserve stable identifiers when they expose them, and browser-collected jobs still work correctly without external IDs.

## Update Behavior

On first sighting:

- insert the row
- set `first_seen_at`
- set `last_seen_at`
- set `last_updated_at`
- compute and store `content_hash`

On a repeated unchanged sighting:

- keep the same row
- update `last_seen_at`
- preserve `first_seen_at`
- preserve `last_updated_at`

On changed content:

- update changed fields
- refresh `content_hash`
- update `last_seen_at`
- update `last_updated_at`
- preserve `first_seen_at`

## Content Hash

`content_hash` is based on stable job content only, including:

- title
- location
- description
- normalized job URL
- external job ID
- ATS type
- board slug

Volatile timestamps are intentionally excluded.

## Scope

This does not change the product safety model or the collect-first, score-later flow:

- collectors still return jobs broadly first
- scoring still happens after collection
- LinkedIn, Indeed, and Glassdoor remain manual-only
- no CAPTCHA bypass, login automation, or auto-apply behavior is added
