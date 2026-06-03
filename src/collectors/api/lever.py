"""Lever public postings API collector."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from collectors.base import CollectorResult, NormalizedJob

LEVER_API_TIMEOUT_SECONDS = 15
LEVER_API_USER_AGENT = "JobDiscoveryBrowserCoPilot/0.1"
LEVER_HOSTS = {
    "jobs.lever.co",
    "api.lever.co",
}


def extract_lever_site(url: str | None) -> str | None:
    """Extract a Lever site slug from supported public Lever URLs."""

    if not url:
        return None
    parsed = urlparse(str(url).strip())
    hostname = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if hostname not in LEVER_HOSTS:
        return None
    if hostname == "jobs.lever.co":
        return path_parts[0] if path_parts else None
    if hostname == "api.lever.co" and len(path_parts) >= 3:
        if path_parts[0] == "v0" and path_parts[1] == "postings":
            return path_parts[2]
    return None


def _build_lever_endpoint(site: str) -> str:
    return f"https://api.lever.co/v0/postings/{site}?mode=json"


def _fetch_json(url: str, *, timeout: int = LEVER_API_TIMEOUT_SECONDS) -> Any:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": LEVER_API_USER_AGENT,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _html_to_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text("\n", strip=True)


def _normalize_lever_timestamp(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 1_000_000_000_000:
            timestamp /= 1000.0
        return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()
    return str(value)


def _collect_additional_text(posting: dict[str, Any]) -> str | None:
    parts: list[str] = []

    description_plain = str(posting.get("descriptionPlain") or "").strip()
    if description_plain:
        parts.append(description_plain)
    else:
        description_html = _html_to_text(posting.get("description"))
        if description_html:
            parts.append(description_html)

    lists = posting.get("lists")
    if isinstance(lists, list):
        for item in lists:
            if not isinstance(item, dict):
                continue
            heading = str(item.get("text") or "").strip()
            content_items = item.get("content")
            normalized_items: list[str] = []
            if isinstance(content_items, list):
                for entry in content_items:
                    normalized_text = _html_to_text(entry)
                    if normalized_text:
                        normalized_items.append(normalized_text)
            elif content_items:
                normalized_text = _html_to_text(content_items)
                if normalized_text:
                    normalized_items = [normalized_text]
            if heading:
                parts.append(heading)
            parts.extend(normalized_items)

    additional = posting.get("additional")
    if isinstance(additional, list):
        for item in additional:
            text = _html_to_text(item)
            if text:
                parts.append(text)
    elif additional:
        text = _html_to_text(additional)
        if text:
            parts.append(text)

    cleaned_parts = [part for part in parts if part]
    return "\n\n".join(cleaned_parts) if cleaned_parts else None


def _normalize_lever_job(
    posting: dict[str, Any],
    *,
    company_name: str,
    source_name: str,
    board_slug: str,
) -> NormalizedJob:
    categories = posting.get("categories")
    if isinstance(categories, dict):
        location = str(categories.get("location") or "").strip() or None
    else:
        location = None

    hosted_url = str(posting.get("hostedUrl") or "").strip() or None
    apply_url = str(posting.get("applyUrl") or "").strip() or hosted_url

    return NormalizedJob(
        company_name=company_name,
        title=str(posting.get("text") or "").strip(),
        location=location,
        job_url=hosted_url,
        apply_url=apply_url,
        source_name=source_name,
        source_mode="api_allowed",
        description=_collect_additional_text(posting),
        date_posted=_normalize_lever_timestamp(posting.get("createdAt")),
        external_job_id=str(posting.get("id")) if posting.get("id") is not None else None,
        ats_type="lever",
        board_slug=board_slug,
        raw_payload_json=json.dumps(posting, ensure_ascii=True, sort_keys=True),
    )


def collect_lever_jobs(company: dict[str, Any]) -> CollectorResult:
    """Collect all public postings from a Lever API board."""

    company_name = str(company.get("name") or company.get("company_name") or "")
    source_name = str(company.get("source_name") or company.get("website_category") or "lever")
    site = extract_lever_site(company.get("careers_url"))
    if not site:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="invalid_source_config",
            collector="lever_api",
            ats_type="lever",
            source_mode="api_allowed",
            error="Missing Lever site slug in careers_url.",
        )

    endpoint = _build_lever_endpoint(site)
    try:
        payload = _fetch_json(endpoint)
    except (HTTPError, URLError, TimeoutError) as exc:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="api_error",
            collector="lever_api",
            ats_type="lever",
            source_mode="api_allowed",
            error=f"Lever API request failed: {exc}",
        )
    except ValueError as exc:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="lever_api",
            ats_type="lever",
            source_mode="api_allowed",
            error=f"Lever API response could not be parsed: {exc}",
        )
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="api_error",
            collector="lever_api",
            ats_type="lever",
            source_mode="api_allowed",
            error=f"Unexpected Lever API error: {exc}",
        )

    if not isinstance(payload, list):
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="lever_api",
            ats_type="lever",
            source_mode="api_allowed",
            error="Lever API response did not contain a postings list.",
        )

    try:
        jobs = [
            _normalize_lever_job(
                raw_posting,
                company_name=company_name,
                source_name=source_name,
                board_slug=site,
            ).to_dict()
            for raw_posting in payload
            if isinstance(raw_posting, dict) and str(raw_posting.get("text") or "").strip()
        ]
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="lever_api",
            ats_type="lever",
            source_mode="api_allowed",
            error=f"Failed to normalize Lever postings: {exc}",
        )

    return CollectorResult(
        company_name=company_name,
        source_name=source_name,
        status="success" if jobs else "no_jobs_found",
        collector="lever_api",
        ats_type="lever",
        source_mode="api_allowed",
        jobs_discovered=len(jobs),
        jobs=jobs,
    )
