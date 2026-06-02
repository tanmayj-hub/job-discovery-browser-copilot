"""Visible-page extraction helpers for browser-assisted job collection."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import Locator, Page

from processing.score import score_job

SEARCH_INPUT_SELECTORS = (
    "input[type='search']",
    "input[placeholder*='Search' i]",
    "input[placeholder*='keyword' i]",
    "input[aria-label*='search' i]",
    "input[name*='search' i]",
    "input[name*='keyword' i]",
    "[role='searchbox']",
)
JOB_ROLE_HINTS = (
    "engineer",
    "devops",
    "cloud",
    "platform",
    "administrator",
    "admin",
    "analyst",
    "support",
    "reliability",
    "systems",
    "ops",
)
JOB_CONTAINER_SELECTORS = (
    "article",
    "section",
    "div",
    "li",
)
TITLE_SELECTORS = ("h1", "h2", "h3", "h4", "a", "strong", "[data-job-title]")
PAGINATION_LABELS = (
    "next",
    "next page",
    "load more",
    "show more",
    "more jobs",
)
NOISE_TEXT_HINTS = (
    "home",
    "about",
    "contact",
    "privacy",
    "terms",
    "cookie",
    "accessibility",
    "investor",
    "benefits",
    "sign in",
    "log in",
    "careers",
)
NOISE_URL_HINTS = (
    "/privacy",
    "/terms",
    "/contact",
    "/about",
    "/benefits",
    "/signin",
    "/login",
)
RESTRICTED_DOMAINS = ("linkedin.com", "indeed.com")


def find_search_input(page: Page) -> Locator | None:
    """Return the first visible search input if present."""

    for selector in SEARCH_INPUT_SELECTORS:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            return locator.first
    return None


def search_with_keywords(page: Page, keywords: list[str]) -> str | None:
    """Fill a detected search input with configured keywords."""

    search_input = find_search_input(page)
    if search_input is None or not keywords:
        return None

    query = " ".join(keywords[:3]).strip()
    if not query:
        return None

    search_input.click()
    search_input.fill(query)
    search_input.press("Enter")
    page.wait_for_timeout(1_500)
    return query


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _strip_html(value: object) -> str:
    return BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True)


def _is_restricted_url(url: str) -> bool:
    hostname = urlparse(url).netloc.lower()
    return any(domain in hostname for domain in RESTRICTED_DOMAINS)


def _is_noise_candidate(title: str, href: str, context: str) -> bool:
    normalized_title = title.lower()
    normalized_href = href.lower()
    normalized_context = context.lower()
    if any(hint == normalized_title for hint in NOISE_TEXT_HINTS):
        return True
    if any(hint in normalized_href for hint in NOISE_URL_HINTS):
        return True
    if "footer" in normalized_context or "navigation" in normalized_context:
        return True
    if title.lower().startswith("back to") or title.lower().startswith("learn more"):
        return True
    return False


def _best_title_from_container(container: BeautifulSoup) -> str:
    for selector in TITLE_SELECTORS:
        element = container.select_one(selector)
        if element is not None:
            title = _clean_text(element.get_text(" ", strip=True))
            if title:
                return title
    return ""


def _best_link_from_container(container: BeautifulSoup, base_url: str) -> str | None:
    link = container.select_one("a[href]")
    if link is None:
        return None
    href = str(link.get("href") or "").strip()
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return None
    return urljoin(base_url, href)


def _build_job_record(
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    title: str,
    base_url: str,
    href: str | None = None,
    location: str | None = None,
    description: str | None = None,
    date_posted: str | None = None,
    apply_url: str | None = None,
) -> dict[str, Any] | None:
    cleaned_title = _clean_text(title)
    cleaned_description = _clean_text(description)
    resolved_href = urljoin(base_url, href) if href else base_url
    if not cleaned_title or _is_restricted_url(resolved_href):
        return None
    if _is_noise_candidate(cleaned_title, resolved_href, cleaned_description):
        return None

    job = {
        "company_name": company_name,
        "title": cleaned_title,
        "location": _clean_text(location) or extract_location(cleaned_description) or None,
        "job_url": resolved_href,
        "apply_url": urljoin(base_url, apply_url) if apply_url else None,
        "source_name": source_name,
        "source_mode": source_mode,
        "description": cleaned_description or None,
        "date_posted": date_posted,
        "status": "new",
    }
    score_result = score_job(job)
    job["match_score"] = score_result.match_score
    job["match_reasons"] = score_result.match_reasons
    job["risk_flags"] = score_result.risk_flags
    if not _is_relevant_job(job):
        return None
    return job


def _is_relevant_job(job: dict[str, Any]) -> bool:
    if int(job.get("match_score", 0)) <= 0:
        return False
    reasons = [str(reason).lower() for reason in job.get("match_reasons", [])]
    return any(
        reason.startswith("title matches")
        or reason.startswith("description mentions")
        or reason.startswith("matched skills")
        or reason.startswith("location signals")
        for reason in reasons
    )


def _dedupe_jobs(jobs: Iterable[dict[str, Any]], *, max_cards: int) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_fallbacks: set[tuple[str, str]] = set()
    for job in jobs:
        job_url = str(job.get("job_url") or "").strip()
        title = str(job.get("title") or "").strip()
        location = str(job.get("location") or "").strip()
        if job_url:
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)
        else:
            fallback_key = (title, location)
            if fallback_key in seen_fallbacks:
                continue
            seen_fallbacks.add(fallback_key)
        deduped.append(job)
        if len(deduped) >= max_cards:
            break
    return deduped


def _extract_from_job_links(
    soup: BeautifulSoup,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    base_url: str,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for link in soup.select("a[href]"):
        if link.find_parent(["nav", "footer", "header", "aside"]):
            continue
        href = str(link.get("href") or "").strip()
        title = _clean_text(link.get_text(" ", strip=True))
        context = _clean_text(link.find_parent(["article", "li", "tr", "section", "div"]) or "")
        if not title or not any(hint in title.lower() for hint in JOB_ROLE_HINTS):
            continue
        job = _build_job_record(
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            title=title,
            base_url=base_url,
            href=href,
            description=context,
        )
        if job is not None:
            jobs.append(job)
    return jobs


def _extract_from_list_items(
    soup: BeautifulSoup,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    base_url: str,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for item in soup.select("li"):
        if item.find_parent(["nav", "footer", "header", "aside"]):
            continue
        title = _best_title_from_container(item)
        href = _best_link_from_container(item, base_url)
        text = _clean_text(item.get_text(" ", strip=True))
        if not title or not any(hint in text.lower() for hint in JOB_ROLE_HINTS):
            continue
        job = _build_job_record(
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            title=title,
            base_url=base_url,
            href=href,
            description=text,
        )
        if job is not None:
            jobs.append(job)
    return jobs


def _extract_from_cards(
    soup: BeautifulSoup,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    base_url: str,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for selector in JOB_CONTAINER_SELECTORS:
        for container in soup.select(selector):
            if container.find_parent(["nav", "footer", "header", "aside"]):
                continue
            title = _best_title_from_container(container)
            href = _best_link_from_container(container, base_url)
            text = _clean_text(container.get_text(" ", strip=True))
            if not title or not any(hint in text.lower() for hint in JOB_ROLE_HINTS):
                continue
            job = _build_job_record(
                company_name=company_name,
                source_name=source_name,
                source_mode=source_mode,
                title=title,
                base_url=base_url,
                href=href,
                description=text,
            )
            if job is not None:
                jobs.append(job)
    return jobs


def _extract_from_tables(
    soup: BeautifulSoup,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    base_url: str,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for row in soup.select("table tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        title = _clean_text(cells[0].get_text(" ", strip=True))
        href = None
        first_link = row.select_one("a[href]")
        if first_link is not None:
            href = str(first_link.get("href") or "").strip()
        location = _clean_text(cells[1].get_text(" ", strip=True))
        description = _clean_text(row.get_text(" ", strip=True))
        if not title or not any(hint in description.lower() for hint in JOB_ROLE_HINTS):
            continue
        job = _build_job_record(
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            title=title,
            base_url=base_url,
            href=href,
            location=location,
            description=description,
        )
        if job is not None:
            jobs.append(job)
    return jobs


def _extract_json_ld_jobs(
    soup: BeautifulSoup,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    base_url: str,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for script in soup.select("script[type='application/ld+json']"):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in _iter_json_ld_items(payload):
            if str(item.get("@type") or "").lower() != "jobposting":
                continue
            title = _clean_text(item.get("title"))
            description = _strip_html(item.get("description"))
            job_url = str(item.get("url") or item.get("directApply") or "").strip() or None
            date_posted = _clean_text(item.get("datePosted")) or None
            location = _extract_json_ld_location(item)
            job = _build_job_record(
                company_name=company_name,
                source_name=source_name,
                source_mode=source_mode,
                title=title,
                base_url=base_url,
                href=job_url,
                apply_url=job_url,
                location=location,
                description=description,
                date_posted=date_posted,
            )
            if job is not None:
                jobs.append(job)
    return jobs


def _iter_json_ld_items(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("@graph"), list):
            return [item for item in payload["@graph"] if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _extract_json_ld_location(item: dict[str, Any]) -> str | None:
    locations = item.get("jobLocation") or item.get("applicantLocationRequirements")
    if isinstance(locations, dict):
        locations = [locations]
    if not isinstance(locations, list):
        return None

    parts: list[str] = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        address = location.get("address")
        if isinstance(address, dict):
            for field in ("addressLocality", "addressRegion", "addressCountry"):
                value = _clean_text(address.get(field))
                if value:
                    parts.append(value)
        else:
            value = _clean_text(location.get("name") or location)
            if value:
                parts.append(value)
    return ", ".join(dict.fromkeys(parts)) or None


def extract_jobs_from_html(
    html: str,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    base_url: str,
    max_cards: int = 20,
) -> list[dict[str, Any]]:
    """Extract relevant job records from one HTML document."""

    soup = BeautifulSoup(html, "html.parser")
    candidates: list[dict[str, Any]] = []
    candidates.extend(
        _extract_json_ld_jobs(
            soup,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            base_url=base_url,
        )
    )
    candidates.extend(
        _extract_from_job_links(
            soup,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            base_url=base_url,
        )
    )
    candidates.extend(
        _extract_from_list_items(
            soup,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            base_url=base_url,
        )
    )
    candidates.extend(
        _extract_from_cards(
            soup,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            base_url=base_url,
        )
    )
    candidates.extend(
        _extract_from_tables(
            soup,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            base_url=base_url,
        )
    )
    return _dedupe_jobs(candidates, max_cards=max_cards)


def _find_safe_pagination_target(page: Page) -> Locator | None:
    locator = page.locator("button, a, [role='button']")
    candidate_count = min(locator.count(), 50)
    current_host = urlparse(page.url).netloc.lower()

    for index in range(candidate_count):
        candidate = locator.nth(index)
        if not candidate.is_visible():
            continue
        try:
            enabled = candidate.is_enabled()
        except Exception:  # noqa: BLE001
            enabled = True
        if not enabled:
            continue

        text = _clean_text(candidate.inner_text()).lower()
        if text not in PAGINATION_LABELS:
            continue
        if any(blocked in text for blocked in ("sign in", "log in", "linkedin", "indeed")):
            continue
        href = str(candidate.get_attribute("href") or "").strip()
        if href:
            resolved = urljoin(page.url, href)
            resolved_host = urlparse(resolved).netloc.lower()
            if resolved_host and resolved_host != current_host:
                continue
            if _is_restricted_url(resolved):
                continue
        return candidate
    return None


def _collect_paginated_snapshots(page: Page, *, max_pages: int) -> list[tuple[str, str]]:
    snapshots: list[tuple[str, str]] = [(page.url, page.content())]
    for _ in range(max_pages - 1):
        target = _find_safe_pagination_target(page)
        if target is None:
            break
        before = page.content()
        target.click()
        page.wait_for_timeout(1_000)
        after = page.content()
        if after == before:
            break
        snapshots.append((page.url, after))
    return snapshots


def extract_visible_job_cards(
    page: Page,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    max_cards: int = 20,
    max_pages: int = 2,
) -> list[dict[str, Any]]:
    """Extract relevant jobs from one page and up to one safe pagination step."""

    if _is_restricted_url(page.url):
        return []

    candidates: list[dict[str, Any]] = []
    for url, html in _collect_paginated_snapshots(page, max_pages=max_pages):
        candidates.extend(
            extract_jobs_from_html(
                html,
                company_name=company_name,
                source_name=source_name,
                source_mode=source_mode,
                base_url=url,
                max_cards=max_cards,
            )
        )
    return _dedupe_jobs(candidates, max_cards=max_cards)


def extract_location(description: str) -> str | None:
    """Best-effort location extraction from surrounding card text."""

    text = description.strip()
    if not text:
        return None

    soup = BeautifulSoup(f"<div>{text}</div>", "html.parser")
    flattened = soup.get_text(" ", strip=True)
    location_hints = (
        "toronto",
        "markham",
        "mississauga",
        "ontario",
        "canada",
        "remote",
        "hybrid",
        "montreal",
        "vancouver",
        "calgary",
    )
    for line in flattened.split("  "):
        candidate = line.strip()
        if any(hint in candidate.lower() for hint in location_hints):
            return candidate[:160]
    if any(hint in flattened.lower() for hint in location_hints):
        return flattened[:160]
    return None
