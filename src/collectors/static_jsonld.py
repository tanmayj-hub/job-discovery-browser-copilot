"""Static HTTP collector for public JSON-LD JobPosting pages."""

from __future__ import annotations

import hashlib
import json
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from collectors.base import CollectorResult, NormalizedJob

STATIC_JSONLD_TIMEOUT_SECONDS = 15
STATIC_JSONLD_USER_AGENT = "JobDiscoveryBrowserCoPilot/0.1"


def _fetch_html(url: str, *, timeout: int = STATIC_JSONLD_TIMEOUT_SECONDS) -> str:
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": STATIC_JSONLD_USER_AGENT,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _format_fetch_error(exc: Exception) -> str:
    if isinstance(exc, URLError) and isinstance(exc.reason, ssl.SSLError):
        return f"Static JSON-LD SSL verification failed: {exc.reason}"
    return f"Static JSON-LD request failed: {exc}"


def _iter_json_ld_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        graph = payload.get("@graph")
        if isinstance(graph, list):
            return [item for item in graph if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _is_job_posting(item: dict[str, Any]) -> bool:
    raw_type = item.get("@type")
    if isinstance(raw_type, str):
        return raw_type.lower() == "jobposting"
    if isinstance(raw_type, list):
        return any(str(value).lower() == "jobposting" for value in raw_type)
    return False


def _strip_html(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return BeautifulSoup(text, "html.parser").get_text("\n", strip=True) or None


def _normalize_location_address(address: dict[str, Any]) -> str | None:
    parts = []
    for field in ("streetAddress", "addressLocality", "addressRegion", "addressCountry"):
        value = str(address.get(field) or "").strip()
        if value:
            parts.append(value)
    joined = ", ".join(dict.fromkeys(parts))
    return joined or None


def _normalize_job_location(item: dict[str, Any]) -> str | None:
    raw_locations = item.get("jobLocation")
    location_type = str(item.get("jobLocationType") or "").strip().lower()
    normalized_parts: list[str] = []

    if isinstance(raw_locations, str):
        if raw_locations.strip():
            normalized_parts.append(raw_locations.strip())
    elif isinstance(raw_locations, dict):
        address = raw_locations.get("address")
        if isinstance(address, dict):
            address_text = _normalize_location_address(address)
            if address_text:
                normalized_parts.append(address_text)
        else:
            name = str(raw_locations.get("name") or "").strip()
            if name:
                normalized_parts.append(name)
    elif isinstance(raw_locations, list):
        for location in raw_locations:
            if isinstance(location, str) and location.strip():
                normalized_parts.append(location.strip())
            elif isinstance(location, dict):
                address = location.get("address")
                if isinstance(address, dict):
                    address_text = _normalize_location_address(address)
                    if address_text:
                        normalized_parts.append(address_text)
                else:
                    name = str(location.get("name") or "").strip()
                    if name:
                        normalized_parts.append(name)

    if "remote" in location_type or "telecommute" in location_type:
        normalized_parts.append("Remote")

    joined = " | ".join(dict.fromkeys(part for part in normalized_parts if part))
    return joined or None


def _stable_external_job_id(item: dict[str, Any], *, job_url: str, title: str) -> str:
    identifier = item.get("identifier")
    if isinstance(identifier, dict):
        for field in ("value", "@value", "name"):
            value = identifier.get(field)
            if value is not None and str(value).strip():
                return str(value).strip()
    elif identifier is not None and str(identifier).strip():
        return str(identifier).strip()
    if job_url:
        return job_url
    stable_input = f"{job_url}|{title}"
    return hashlib.sha256(stable_input.encode("utf-8")).hexdigest()


def _normalize_jsonld_job(
    item: dict[str, Any],
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    page_url: str,
) -> NormalizedJob:
    page_hostname = urlparse(page_url).netloc.lower()
    explicit_url = str(item.get("url") or "").strip()
    job_url = explicit_url or page_url
    title = str(item.get("title") or "").strip()
    return NormalizedJob(
        company_name=company_name,
        title=title,
        location=_normalize_job_location(item),
        job_url=job_url,
        apply_url=job_url,
        source_name=source_name,
        source_mode=source_mode,
        description=_strip_html(item.get("description")),
        date_posted=str(item.get("datePosted") or "").strip() or None,
        external_job_id=_stable_external_job_id(item, job_url=job_url, title=title),
        ats_type="jsonld",
        board_slug=page_hostname or None,
        raw_payload_json=json.dumps(item, ensure_ascii=True, sort_keys=True),
    )


def collect_static_jsonld_jobs(company: dict[str, Any]) -> CollectorResult:
    """Collect public JobPosting records from static JSON-LD on a page."""

    company_name = str(company.get("name") or company.get("company_name") or "")
    source_name = str(company.get("source_name") or company.get("website_category") or "jsonld")
    source_mode = str(company.get("source_mode") or "browser_allowed")
    page_url = str(company.get("careers_url") or "").strip()
    if not page_url:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="invalid_source_config",
            collector="static_jsonld",
            ats_type="jsonld",
            source_mode=source_mode,
            error="Missing careers_url for static JSON-LD collection.",
        )

    try:
        html = _fetch_html(page_url)
    except (HTTPError, URLError, TimeoutError) as exc:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="api_error",
            collector="static_jsonld",
            ats_type="jsonld",
            source_mode=source_mode,
            error=_format_fetch_error(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="api_error",
            collector="static_jsonld",
            ats_type="jsonld",
            source_mode=source_mode,
            error=f"Unexpected static JSON-LD error: {exc}",
        )

    soup = BeautifulSoup(html, "html.parser")
    jobs: list[dict[str, Any]] = []
    parse_errors: list[str] = []

    for script in soup.select("script[type='application/ld+json']"):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            parse_errors.append(str(exc))
            continue
        try:
            for item in _iter_json_ld_items(payload):
                if not _is_job_posting(item):
                    continue
                job = _normalize_jsonld_job(
                    item,
                    company_name=company_name,
                    source_name=source_name,
                    source_mode=source_mode,
                    page_url=page_url,
                ).to_dict()
                if job["title"]:
                    jobs.append(job)
        except Exception as exc:  # noqa: BLE001
            return CollectorResult(
                company_name=company_name,
                source_name=source_name,
                status="parse_error",
                collector="static_jsonld",
                ats_type="jsonld",
                source_mode=source_mode,
                error=f"Failed to normalize JSON-LD JobPosting: {exc}",
            )

    if jobs:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="success",
            collector="static_jsonld",
            ats_type="jsonld",
            source_mode=source_mode,
            jobs_discovered=len(jobs),
            jobs=jobs,
        )
    if parse_errors:
        return CollectorResult(
            company_name=company_name,
            source_name=source_name,
            status="parse_error",
            collector="static_jsonld",
            ats_type="jsonld",
            source_mode=source_mode,
            error=f"Malformed JSON-LD encountered: {parse_errors[0]}",
        )
    return CollectorResult(
        company_name=company_name,
        source_name=source_name,
        status="no_jobs_found",
        collector="static_jsonld",
        ats_type="jsonld",
        source_mode=source_mode,
        jobs_discovered=0,
        jobs=[],
    )
