"""Visible-page extraction helpers for browser-assisted job collection."""

from __future__ import annotations

import json
import re
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
COOKIE_ACCEPT_TEXT_HINTS = (
    "accept",
    "accept all",
    "accept all cookies",
    "accept cookies",
    "accept all cookie",
    "allow",
    "allow all",
    "allow all cookies",
    "agree",
    "i agree",
    "got it",
    "ok",
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
    "jobs",
    "manage",
    "view all jobs",
    "search jobs",
    "job cart",
    "all filters",
    "clear all",
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
JOB_URL_HINTS = (
    "job",
    "jobs",
    "jobdetail",
    "job-detail",
    "requisition",
    "reqid",
    "position",
    "posting",
    "vacancy",
    "opening",
)
JOB_SEARCH_ENTRY_HINTS = (
    "job search",
    "search jobs",
    "search open roles",
    "search opportunities",
    "find a job",
    "find jobs",
    "open roles",
    "view jobs",
    "browse opportunities",
)
EMPTY_RESULTS_HINTS = (
    "0 jobs",
    "0 job",
    "we didn't find any relevant jobs",
    "no jobs found",
    "no matching jobs",
    "try modifying search/filters",
)


def _is_search_results_style_page(page: Page) -> bool:
    """Return True when the page is an actual job results surface where keyword search helps."""

    url_text = page.url.lower()
    return any(marker in url_text for marker in ("jobsearch", "search-results", "jobs/search"))


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
    if (
        search_input is None
        or not keywords
        or (has_interactive_job_cards(page) and not _is_search_results_style_page(page))
    ):
        return None

    query = " ".join(keywords[:3]).strip()
    if not query:
        return None

    starting_url = page.url
    try:
        search_input.fill(query)
    except Exception:  # noqa: BLE001
        search_input.click()
        search_input.fill(query)
    search_input.press("Enter")
    page.wait_for_timeout(1_500)
    current_text = _clean_text(page.locator("body").inner_text(timeout=3_000))
    if _looks_like_empty_results_page(current_text):
        try:
            if page.url != starting_url:
                page.go_back(wait_until="load")
            else:
                page.goto(starting_url, wait_until="load")
        except Exception:  # noqa: BLE001
            page.goto(starting_url, wait_until="load")
        page.wait_for_timeout(1_000)
        return None
    return query


def has_interactive_job_cards(page: Page) -> bool:
    """Return True when the page already exposes live job-card controls."""

    try:
        count = page.evaluate(
            """
            () => Array.from(
              document.querySelectorAll(
                [
                  '[aria-label^="View job:"]',
                  'button[aria-label]',
                  'a[aria-label]',
                  '[role="button"][aria-label]',
                ].join(',')
              )
            ).filter((node) => {
              const label = (
                `${node.getAttribute('aria-label') || ''} ${node.innerText || ''}`
              ).toLowerCase();
              return label.includes('view job:') || label.includes('expand job details');
            }).length
            """,
        )
    except Exception:  # noqa: BLE001
        return False
    return bool(count)


def navigate_to_job_search_page(page: Page) -> str | None:
    """Move from a careers landing page to an on-site job-search/results page when visible."""

    current_host = urlparse(page.url).netloc.lower()
    try:
        candidates = page.evaluate(
            """
            () => Array.from(
              document.querySelectorAll('a[href], button, [role="button"]')
            ).map((el) => ({
              text: (el.innerText || '').trim(),
              aria: (el.getAttribute('aria-label') || '').trim(),
              href: (el.getAttribute('href') || '').trim(),
            }))
            """,
        )
    except Exception:  # noqa: BLE001
        page.wait_for_timeout(1_000)
        candidates = page.evaluate(
            """
            () => Array.from(
              document.querySelectorAll('a[href], button, [role="button"]')
            ).map((el) => ({
              text: (el.innerText || '').trim(),
              aria: (el.getAttribute('aria-label') || '').trim(),
              href: (el.getAttribute('href') || '').trim(),
            }))
            """,
        )
    normalized: list[dict[str, str]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        text = _clean_text(candidate.get("text"))
        aria = _clean_text(candidate.get("aria"))
        href = str(candidate.get("href") or "").strip()
        combined = f"{text} {aria}".lower()
        if not any(hint in combined for hint in JOB_SEARCH_ENTRY_HINTS):
            continue
        normalized.append(
            {
                "text": text,
                "aria": aria,
                "href": href,
            }
        )

    for candidate in normalized:
        href = candidate["href"]
        if not href:
            continue
        resolved = urljoin(page.url, href)
        resolved_host = urlparse(resolved).netloc.lower()
        if (
            resolved_host
            and resolved_host != current_host
            and not _is_public_job_search_url(resolved)
        ):
            continue
        if _is_restricted_url(resolved) or resolved == page.url:
            continue
        page.goto(resolved, wait_until="load")
        page.wait_for_timeout(1_500)
        return resolved

    locator = page.locator("button, a, [role='button']")
    candidate_count = min(locator.count(), 80)
    before_url = page.url
    before_text = _clean_text(page.locator("body").inner_text(timeout=3_000))[:1200]
    for candidate in normalized:
        target_text = candidate["text"].lower()
        target_aria = candidate["aria"].lower()
        if candidate["href"]:
            continue
        for index in range(candidate_count):
            element = locator.nth(index)
            if not element.is_visible():
                continue
            text = _clean_text(element.inner_text()).lower()
            aria = _clean_text(element.get_attribute("aria-label")).lower()
            if (target_text and text == target_text) or (target_aria and aria == target_aria):
                element.click()
                page.wait_for_timeout(2_000)
                after_url = page.url
                after_text = _clean_text(page.locator("body").inner_text(timeout=3_000))[:1200]
                if after_url != before_url or after_text != before_text:
                    return after_url
                break
    return None


def _is_public_job_search_url(url: str) -> bool:
    """Return True for public company-hosted ATS/search boards."""

    parsed = urlparse(url)
    normalized = f"{parsed.netloc} {parsed.path} {parsed.query}".lower()
    if _is_restricted_url(url):
        return False
    return any(
        hint in normalized
        for hint in (
            "workdayjobs.com",
            "njoyn.com",
            "joblisting",
            "jobsearch",
            "search-results",
            "jobs/search",
        )
    )


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _normalize_job_title_text(title: str) -> str:
    """Strip repetitive UI prefixes and trailing metadata from extracted titles."""

    cleaned = _clean_text(title)
    lowered = cleaned.lower()
    if lowered.startswith("job title "):
        cleaned = cleaned[10:].strip()
        cleaned = re.split(
            r"\s+(?:location|category|posted)\s+",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
    if lowered.startswith("apply now "):
        cleaned = cleaned[10:].strip()
    return _clean_text(cleaned)


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
    if title.lower().startswith("view all") or title.lower().startswith("show all"):
        return True
    if title.lower().startswith("apply now"):
        return True
    if title.lower().startswith("browse opportunities"):
        return True
    if title.lower().startswith("you belong here"):
        return True
    if title.lower().startswith("showing search results"):
        return True
    if any(term in normalized_title for term in ("adjoint", "administratif", "commis")):
        return True
    if "/apply" in normalized_href:
        return True
    if (
        "search-results?" in normalized_href
        and "read full job description" not in normalized_context
    ):
        return True
    return False


def _looks_like_empty_results_page(text: str) -> bool:
    normalized = text.lower()
    return any(hint in normalized for hint in EMPTY_RESULTS_HINTS)


def _has_non_location_match_reasons(job: dict[str, Any]) -> bool:
    reasons = [str(reason).lower() for reason in job.get("match_reasons", [])]
    return any(
        reason.startswith("title matches")
        or reason.startswith("description mentions")
        or reason.startswith("matched skills")
        or reason.startswith("support/ops signals")
        for reason in reasons
    )


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


def _has_job_posting_signal(
    *,
    title: str,
    href: str,
    description: str,
    location: str | None,
) -> bool:
    normalized_title = title.lower()
    normalized_href = href.lower()
    normalized_description = description.lower()
    has_role_hint = any(hint in normalized_title for hint in JOB_ROLE_HINTS)
    has_job_url_hint = any(hint in normalized_href for hint in JOB_URL_HINTS)
    has_posting_text = any(
        marker in normalized_description
        for marker in ("posted", "apply", "job id", "job req", "requisition", "req id")
    )
    has_location = bool(_clean_text(location))
    return (has_role_hint and (has_job_url_hint or has_posting_text or has_location)) or (
        has_posting_text and has_location
    )


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
    structured_source: bool = False,
    allow_base_url_fallback: bool = True,
) -> dict[str, Any] | None:
    cleaned_title = _normalize_job_title_text(title)
    cleaned_description = _clean_text(description)
    resolved_href = (
        urljoin(base_url, href)
        if href
        else (base_url if allow_base_url_fallback else None)
    )
    cleaned_location = _clean_text(location) or extract_location(cleaned_description) or None
    resolved_href_text = resolved_href or ""
    if not cleaned_title or (resolved_href and _is_restricted_url(resolved_href)):
        return None
    if _is_noise_candidate(cleaned_title, resolved_href_text, cleaned_description):
        return None
    if not structured_source and not _has_job_posting_signal(
        title=cleaned_title,
        href=resolved_href_text,
        description=cleaned_description,
        location=cleaned_location,
    ):
        return None

    job = {
        "company_name": company_name,
        "title": cleaned_title,
        "location": cleaned_location,
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
    if not _has_non_location_match_reasons(job):
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
            allow_base_url_fallback=False,
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
            if _is_page_shell_container(container, text):
                continue
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


def _is_page_shell_container(container: BeautifulSoup, text: str) -> bool:
    """Avoid treating an entire search page shell as one job card."""

    if len(text) < 2_500:
        return False
    return len(container.find_all("a", href=True, limit=12)) >= 10


def _extract_from_accenture_job_cards(
    soup: BeautifulSoup,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    base_url: str,
) -> list[dict[str, Any]]:
    """Extract Accenture-style job rows from the structured jobsearch cards."""

    jobs: list[dict[str, Any]] = []
    for container in soup.select("div.rad-filters-vertical__job-card"):
        title_element = container.select_one("h3.rad-filters-vertical__job-card-title")
        link = container.select_one("a[href*='jobdetails']")
        if title_element is None or link is None:
            continue
        title = _clean_text(title_element.get_text(" ", strip=True))
        href = str(link.get("href") or "").strip()
        text = _clean_text(container.get_text(" ", strip=True))
        job = _build_job_record(
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            title=title,
            base_url=base_url,
            href=href,
            description=text,
            allow_base_url_fallback=False,
        )
        if job is not None:
            jobs.append(job)
    return jobs


def _extract_from_bmo_job_cards(
    soup: BeautifulSoup,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    base_url: str,
) -> list[dict[str, Any]]:
    """Extract BMO/Phenom-style structured job rows with cleaner fields."""

    jobs: list[dict[str, Any]] = []
    selectors = (
        "a[data-ph-at-id='job-link']",
        "a[data-ph-at-id='suggested-data-link']",
    )
    for selector in selectors:
        for link in soup.select(selector):
            href = str(link.get("href") or "").strip()
            title = _clean_text(
                link.get("data-ph-at-job-title-text")
                or link.get("aria-label")
                or link.get_text(" ", strip=True)
            )
            location = _clean_text(
                link.get("data-ph-at-job-location-text")
                or link.get("data-ph-at-job-location-area-text")
            ) or None
            date_posted = _clean_text(link.get("data-ph-at-job-post-date-text")) or None
            teaser = link.find_parent(["li", "div", "article"])
            description = (
                _clean_text(teaser.get_text(" ", strip=True))
                if teaser is not None
                else title
            )
            job = _build_job_record(
                company_name=company_name,
                source_name=source_name,
                source_mode=source_mode,
                title=title,
                base_url=base_url,
                href=href,
                location=location,
                description=description,
                date_posted=date_posted,
                allow_base_url_fallback=False,
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
            allow_base_url_fallback=False,
        )
        if job is not None:
            jobs.append(job)
    return jobs


def _extract_from_njoyn_tables(
    soup: BeautifulSoup,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    base_url: str,
) -> list[dict[str, Any]]:
    """Extract Njoyn/CGI-style search-result rows from structured tables."""

    jobs: list[dict[str, Any]] = []
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        id_cell, title_cell, category_cell, city_cell, country_cell = cells[:5]
        link = id_cell.select_one("a[href]")
        if link is None:
            continue
        position_id = _clean_text(id_cell.get_text(" ", strip=True))
        title = _clean_text(title_cell.get_text(" ", strip=True))
        category = _clean_text(category_cell.get_text(" ", strip=True))
        city = _clean_text(city_cell.get_text(" ", strip=True))
        country = _clean_text(country_cell.get_text(" ", strip=True))
        location = ", ".join(part for part in (city, country) if part)
        href = str(link.get("href") or "").strip()
        description = _clean_text(
            f"{position_id} {title} Category {category} City {city} Country {country}"
        )
        job = _build_job_record(
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            title=title,
            base_url=base_url,
            href=href,
            location=location,
            description=description,
            allow_base_url_fallback=False,
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
                structured_source=True,
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


def _extract_from_interactive_cards(
    page: Page,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
) -> list[dict[str, Any]]:
    """Extract job-like cards from live interactive elements on dynamic boards."""

    try:
        items = page.evaluate(
            """
            () => {
              const visible = (element) => {
                if (!(element instanceof HTMLElement)) return false;
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none'
                  && style.visibility !== 'hidden'
                  && rect.width > 0
                  && rect.height > 0;
              };

              const nodes = Array.from(
                document.querySelectorAll(
                  [
                    '[aria-label^="View job:"]',
                    'button[aria-label]',
                    'a[aria-label]',
                    '[role="button"][aria-label]',
                  ].join(',')
                )
              );

              return nodes
                .filter((node) => visible(node))
                .map((node) => ({
                  aria: (node.getAttribute('aria-label') || '').trim(),
                  href: (node.getAttribute('href') || '').trim(),
                  text: (node.innerText || '').trim(),
                  context: (
                    node.closest('article, li, section, div')?.innerText
                    || node.parentElement?.innerText
                    || ''
                  ).trim(),
                }))
                .filter((item) => {
                  const combined = `${item.aria} ${item.text}`.toLowerCase();
                  return combined.includes('view job:')
                    || combined.includes('expand job details');
                });
            }
            """,
        )
    except Exception:  # noqa: BLE001
        return []

    jobs: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_text = _clean_text(item.get("text"))
        raw_aria = _clean_text(item.get("aria"))
        raw_context = _clean_text(item.get("context"))
        href = str(item.get("href") or "").strip() or None
        title = raw_aria.removeprefix("View job:").strip() or raw_aria
        if "Expand job details".lower() in raw_text.lower() and raw_aria:
            title = raw_aria
            raw_text = raw_context or raw_text.replace("Expand job details", "").strip()
        job = _build_job_record(
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            title=title,
            base_url=page.url,
            href=href,
            description=raw_context or raw_text or raw_aria,
            allow_base_url_fallback=False,
        )
        if job is not None:
            jobs.append(job)
    return jobs


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
    page_text = _clean_text(soup.get_text(" ", strip=True))
    if _looks_like_empty_results_page(page_text):
        return []
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
        _extract_from_bmo_job_cards(
            soup,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            base_url=base_url,
        )
    )
    candidates.extend(
        _extract_from_accenture_job_cards(
            soup,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            base_url=base_url,
        )
    )
    candidates.extend(
        _extract_from_njoyn_tables(
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


def dismiss_cookie_banner(page: Page) -> str | None:
    """Dismiss a visible cookie banner when the page exposes a safe accept action."""

    direct_selectors = (
        "#onetrust-accept-btn-handler",
        "button#onetrust-accept-btn-handler",
        "#accept-recommended-btn-handler",
        "#truste-consent-button",
        "button.agree-button.eu-cookie-compliance-default-button",
    )
    for attempt in range(6):
        for selector in direct_selectors:
            locator = page.locator(selector)
            if locator.count() > 0 and locator.first.is_visible():
                locator.first.click()
                page.wait_for_timeout(1_000)
                return selector
        if attempt < 5:
            page.wait_for_timeout(500)

    top_page_text = _clean_text(page.locator("body").inner_text(timeout=3_000)[:1200]).lower()
    if "cookie" in top_page_text or "consent" in top_page_text:
        locator = page.locator("button, a, [role='button']")
        candidate_count = min(locator.count(), 40)
        for index in range(candidate_count):
            candidate = locator.nth(index)
            if not candidate.is_visible():
                continue
            label = _clean_text(candidate.inner_text()).lower()
            if label in COOKIE_ACCEPT_TEXT_HINTS:
                candidate.click()
                page.wait_for_timeout(1_000)
                return label

    result = page.evaluate(
        """
        (labels) => {
          const visible = (element) => {
            if (!(element instanceof HTMLElement)) return false;
            const style = window.getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return style.display !== "none"
              && style.visibility !== "hidden"
              && rect.width > 0
              && rect.height > 0;
          };

          const hasCookieContext = (element) => {
            const text = (
              element.innerText
              || element.getAttribute("aria-label")
              || element.getAttribute("id")
              || element.className
              || ""
            ).toLowerCase();
            return text.includes("cookie") || text.includes("consent") || text.includes("privacy");
          };

          const matchesAction = (element) => {
            const text = (
              element.innerText
              || element.getAttribute("aria-label")
              || element.getAttribute("value")
              || ""
            ).trim().toLowerCase();
            return labels.some((label) => text === label || text.startsWith(label + " "));
          };

          const containers = Array.from(
            document.querySelectorAll(
              [
                "#onetrust-banner-sdk",
                "[id*='cookie']",
                "[class*='cookie']",
                "[aria-label*='cookie' i]",
                "[role='dialog']",
                "aside",
                "section",
                "div",
              ].join(",")
            )
          );

          for (const container of containers) {
            if (!visible(container) || !hasCookieContext(container)) continue;
            const actions = Array.from(
              container.querySelectorAll("button, [role='button'], a, input[type='button']")
            );
            for (const action of actions) {
              if (!visible(action) || !matchesAction(action)) continue;
              action.click();
              return (
                action.innerText
                || action.getAttribute("aria-label")
                || action.getAttribute("value")
                || "cookie_action"
              );
            }
          }
          return null;
        }
        """,
        list(COOKIE_ACCEPT_TEXT_HINTS),
    )
    if result:
        page.wait_for_timeout(1_000)
        return str(result)
    return None


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
    candidates.extend(
        _extract_from_interactive_cards(
            page,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
        )
    )
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
    match = re.search(
        r"\b(?:Toronto|Markham|Mississauga|Montreal|Vancouver|Calgary|REMOTE/TELETRAVAIL)[^,.]{0,80},\s*(?:ON|QC|BC|AB)[^,.]{0,40},\s*Canada\b",
        flattened,
        flags=re.IGNORECASE,
    )
    if match:
        return _clean_text(match.group(0))
    for line in flattened.split("  "):
        candidate = line.strip()
        if any(hint in candidate.lower() for hint in location_hints):
            return candidate[:160]
    if any(hint in flattened.lower() for hint in location_hints):
        return flattened[:160]
    return None
