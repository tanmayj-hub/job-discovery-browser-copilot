"""Ashby public job postings API collector."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from collectors.base import CollectorResult, NormalizedJob

ASHBY_API_TIMEOUT_SECONDS = 15
ASHBY_API_USER_AGENT = "JobDiscoveryBrowserCoPilot/0.1"
ASHBY_HOSTS = {
    "jobs.ashbyhq.com",
    "api.ashbyhq.com",
}


def extract_ashby_job_board_name(url: str | None) -> str | None:
    """Extract an Ashby job board name from supported public URLs."""

    if not url:
        return None
    parsed = urlparse(str(url).strip())
    hostname = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if hostname not in ASHBY_HOSTS:
        return None
    if hostname == "jobs.ashbyhq.com":
        return path_parts[0] if path_parts else None
    if hostname == "api.ashbyhq.com" and len(path_parts) >= 3:
        if path_parts[0] == "posting-api" and path_parts[1] == "job-board":
            return path_parts[2]
    return None


def _build_ashby_endpoint(job_board_name: str) -> str:
    return (
        "https://api.ashbyhq.com/posting-api/job-board/"
        f"{job_board_name}?includeCompensation=true"
    )


def _fetch_json(url: str, *, timeout: int = ASHBY_API_TIMEOUT_SECONDS) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": ASHBY_API_USER_AGENT,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _strip_html(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return BeautifulSoup(text, "html.parser").get_text("\n", strip=True) or None


def _normalize_location(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        parts = []
        for field in ("name", "city", "region", "country"):
            candidate = str(value.get(field) or "").strip()
            if candidate:
                parts.append(candidate)
        joined = ", ".join(dict.fromkeys(parts))
        return joined or None
    if isinstance(value, list):
        parts = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        joined = " | ".join(dict.fromkeys(parts))
        return joined or None
    return None


def _stable_external_job_id(job: dict[str, Any]) -> str | None:
    for field in ("id", "jobPostingId", "jobId"):
        value = job.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    job_url = str(job.get("jobUrl") or "").strip()
    if job_url:
        return job_url
    title = str(job.get("title") or "").strip()
    if not title:
        return None
    stable_input = f"{job_url}|{title}"
    return hashlib.sha256(stable_input.encode("utf-8")).hexdigest()


def _extract_jobs_payload(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, dict):
        for field in ("jobs", "jobPostings", "openings"):
            value = payload.get(field)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return None


def _normalize_ashby_job(
    job: dict[str, Any],
    *,
    company_name: str,
    source_name: str,
    board_slug: str,
) -> NormalizedJob:
    description = str(job.get("descriptionPlain") or "").strip() or _strip_html(
        job.get("descriptionHtml")
    )
    job_url = str(job.get("jobUrl") or "").strip() or None
    apply_url = str(job.get("applyUrl") or "").strip() or job_url
    location_parts: list[str] = []
    primary_location = _normalize_location(job.get("location"))
    if primary_location:
        location_parts.append(primary_location)
    secondary = job.get("secondaryLocations")
    if isinstance(secondary, list):
        for item in secondary:
            normalized = _normalize_location(item)
            if normalized:
                location_parts.append(normalized)
    location = " | ".join(dict.fromkeys(location_parts)) or None

    return NormalizedJob(
        company_name=company_name,
        title=str(job.get("title") or "").strip(),
        location=location,
        job_url=job_url,
        apply_url=apply_url,
        source_name=source_name,
        source_mode="api_allowed",
        description=description,
        date_posted=str(job.get("publishedAt") or "").strip() or None,
        external_job_id=_stable_external_job_id(job),
        ats_type="ashby",
        board_slug=board_slug,
        raw_payload_json=json.dumps(job, ensure_ascii=True, sort_keys=True),
    )


def collect_ashby_jobs(company: dict[str, Any]) -> CollectorResult:
    """Collect all public jobs from an Ashby job board."""

    company_name = str(company.get("name") or company.get("company_name") or "")
    source_name = str(company.get("source_name") or company.get("website_category") or "ashby")
    board_name = extract_ashby_job_board_name(company.get("careers_url"))
    if not board_name:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="invalid_source_config",
            collector="ashby_api",
            ats_type="ashby",
            source_mode="api_allowed",
            error="Missing Ashby job board name in careers_url.",
        )

    endpoint = _build_ashby_endpoint(board_name)
    try:
        payload = _fetch_json(endpoint)
    except (HTTPError, URLError, TimeoutError) as exc:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="api_error",
            collector="ashby_api",
            ats_type="ashby",
            source_mode="api_allowed",
            error=f"Ashby API request failed: {exc}",
        )
    except ValueError as exc:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="ashby_api",
            ats_type="ashby",
            source_mode="api_allowed",
            error=f"Ashby API response could not be parsed: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="api_error",
            collector="ashby_api",
            ats_type="ashby",
            source_mode="api_allowed",
            error=f"Unexpected Ashby API error: {exc}",
        )

    jobs_payload = _extract_jobs_payload(payload)
    if jobs_payload is None:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="ashby_api",
            ats_type="ashby",
            source_mode="api_allowed",
            error="Ashby API response did not contain a jobs list.",
        )

    try:
        jobs = [
            _normalize_ashby_job(
                raw_job,
                company_name=company_name,
                source_name=source_name,
                board_slug=board_name,
            ).to_dict()
            for raw_job in jobs_payload
            if str(raw_job.get("title") or "").strip()
        ]
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="ashby_api",
            ats_type="ashby",
            source_mode="api_allowed",
            error=f"Failed to normalize Ashby jobs: {exc}",
        )

    return CollectorResult(
        company_name=company_name,
        source_name=source_name,
        status="success" if jobs else "no_jobs_found",
        collector="ashby_api",
        ats_type="ashby",
        source_mode="api_allowed",
        jobs_discovered=len(jobs),
        jobs=jobs,
    )
