"""Visible-page extraction helpers for browser-assisted job collection."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import Locator, Page

SEARCH_INPUT_SELECTORS = (
    "input[type='search']",
    "input[placeholder*='Search' i]",
    "input[placeholder*='keyword' i]",
    "input[aria-label*='search' i]",
    "input[name*='search' i]",
    "input[name*='keyword' i]",
    "[role='searchbox']",
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
IBM_LANGUAGE_DISMISS_SELECTORS = (
    ".geo-btn-secondary-cancel",
    "button:has-text('Annuler')",
    ".geo-modal-close-icon",
)
IBM_CANADA_FILTER_SELECTORS = (
    "input[aria-label='Canada']",
    "label:has-text('Canada')",
    "text=Canada (102)",
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
NON_NAVIGABLE_URL_SCHEMES = ("javascript", "mailto", "tel", "data", "vbscript")
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
ALLOWED_EXTERNAL_JOB_HOST_HINTS = (
    "workdayjobs.com",
    "myworkdayjobs.com",
    "greenhouse.io",
    "jobs.lever.co",
    "ashbyhq.com",
    "smartrecruiters.com",
    "njoyn.com",
    "ultipro.com",
    "ukg.com",
    "successfactors.com",
    "oraclecloud.com",
    "icims.com",
    "phenompeople.com",
)
JOB_TITLE_HINTS = (
    "engineer",
    "developer",
    "analyst",
    "administrator",
    "admin",
    "consultant",
    "specialist",
    "architect",
    "coordinator",
    "technician",
    "representative",
    "associate",
    "manager",
    "lead",
    "support",
    "operations",
    "operator",
    "platform",
    "infrastructure",
    "cloud",
    "devops",
    "reliability",
    "systems",
)
MARKETING_TITLE_PREFIXES = (
    "why work at",
    "working at",
    "life at",
    "helping ",
    "our culture",
    "benefits",
    "meet ",
    "students and graduates",
    "students and grads",
    "join our talent community",
)
MARKETING_TITLE_EXACT_HINTS = (
    "living wage employers",
    "always-open job posting",
)
GENERIC_NON_JOB_TITLES = (
    "filter results",
    "search results",
    "job search",
    "careers home",
    "view job details",
    "view all jobs",
    "all jobs",
    "departments",
    "locations",
    "job category",
    "category",
    "business area",
    "employment type",
    "remote",
    "hybrid",
    "on-site",
    "onsite",
    "manage consent preferences",
)
GENERIC_NON_JOB_TITLE_PREFIXES = (
    "filter results",
    "search results",
    "job search",
    "careers home",
)
INDEX_PAGE_PATH_SUFFIXES = (
    "/careers",
    "/jobs",
    "/search",
    "/job-search",
    "/job-search-results",
    "/life-at",
    "/benefits",
    "/culture",
    "/teams",
    "/locations",
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
FORBIDDEN_PRE_EXTRACTION_TERMS = (
    "cloud",
    "devops",
    "aws",
    "azure",
    "terraform",
    "kubernetes",
    "docker",
    "linux",
    "sre",
    "platform",
    "infrastructure",
    "support",
    "administrator",
    "engineer",
    "analyst",
)


@dataclass(slots=True)
class ExtractionDiagnostics:
    """Structured metadata about one paginated extraction pass."""

    pages_visited: list[str]
    jobs_extracted_per_page: list[int]
    pagination_detected: bool
    pagination_stop_reason: str
    max_pages: int
    total_candidates_before_dedupe: int
    total_candidates_after_dedupe: int
    page_html_snapshots: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _is_search_results_style_page(page: Page) -> bool:
    """Return True when the page is a results surface where location-scoped search can help."""

    url_text = page.url.lower()
    return any(
        marker in url_text
        for marker in ("jobsearch", "search-results", "jobs/search", "careers/search")
    )


def find_search_input(page: Page) -> Locator | None:
    """Return the first visible search input if present."""

    for selector in SEARCH_INPUT_SELECTORS:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            return locator.first
    return None


def _contains_forbidden_pre_extraction_term(query: str) -> bool:
    normalized = query.lower()
    return any(
        re.search(rf"\b{re.escape(term)}\b", normalized)
        for term in FORBIDDEN_PRE_EXTRACTION_TERMS
    )


def search_with_location_term(
    page: Page,
    location_term: str,
    *,
    allow_visible_results: bool = False,
) -> str | None:
    """Fill a detected search input with one location-only discovery term."""

    search_input = find_search_input(page)
    query = _clean_text(location_term)
    if (
        search_input is None
        or not query
        or _contains_forbidden_pre_extraction_term(query)
        or (
            not allow_visible_results
            and has_interactive_job_cards(page)
            and not _is_search_results_style_page(page)
        )
    ):
        return None

    starting_url = page.url
    try:
        search_input.fill(query)
    except Exception:  # noqa: BLE001
        search_input.click()
        search_input.fill(query)
    search_input.press("Enter")
    page.wait_for_timeout(1_500)
    current_text = _safe_locator_inner_text(page.locator("body"), timeout=3_000)
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


def is_ibm_careers_search_url(url: str) -> bool:
    """Return True when the URL is IBM's public careers search surface."""

    parsed = urlparse(str(url or "").strip().lower())
    return parsed.netloc.endswith("ibm.com") and parsed.path.rstrip("/") == "/careers/search"


def is_bmo_careers_search_url(url: str) -> bool:
    """Return True when the URL is BMO's public Canada search-results page."""

    parsed = urlparse(str(url or "").strip().lower())
    return parsed.netloc == "jobs.bmo.com" and "/search-results" in parsed.path


def is_ntt_careers_search_url(url: str) -> bool:
    """Return True when the URL is NTT DATA's public search-results page."""

    parsed = urlparse(str(url or "").strip().lower())
    return parsed.netloc == "careers.services.global.ntt" and "/search-results" in parsed.path


def is_rbc_careers_search_url(url: str) -> bool:
    """Return True when the URL is RBC's public Canada search-results page."""

    parsed = urlparse(str(url or "").strip().lower())
    return parsed.netloc == "jobs.rbc.com" and "/search-results" in parsed.path


def detect_rbc_canada_page_evidence(page: Page) -> dict[str, Any] | None:
    """Return trusted Canada-scope evidence from RBC's visible results page when available."""

    if not is_rbc_careers_search_url(page.url):
        return None

    try:
        evidence = page.evaluate(
            """
            () => {
              const visible = (element) => {
                if (!element || typeof element.getBoundingClientRect !== 'function') return false;
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none'
                  && style.visibility !== 'hidden'
                  && rect.width > 0
                  && rect.height > 0;
              };

              const activeCanadaChip = Array.from(
                document.querySelectorAll('button, a, span, div')
              ).some((node) => {
                if (!visible(node)) return false;
                const text = (node.textContent || '').trim();
                const parentText = (node.parentElement?.textContent || '').trim();
                return text === 'Canada' && parentText.includes('Clear all');
              });

              const countryFacet = document.querySelector(
                'input[data-ph-at-facetkey="facet-country"][data-ph-at-text="Canada"]'
              );
              const countryFacetChecked = Boolean(
                countryFacet
                && (
                  countryFacet.checked
                  || String(
                    countryFacet.getAttribute('aria-checked') || ''
                  ).toLowerCase() === 'true'
                )
              );

              const visibleLinks = Array.from(
                document.querySelectorAll('a[data-ph-at-id="job-link"]')
              ).filter((node) => visible(node));

              return {
                activeCanadaChip,
                countryFacetPresent: Boolean(countryFacet),
                countryFacetChecked,
                visibleJobLinkCount: visibleLinks.length,
                sampleHrefs: visibleLinks.slice(0, 10).map((node) => node.href || ''),
              };
            }
            """,
        )
    except Exception:  # noqa: BLE001
        return None

    if not isinstance(evidence, dict):
        return None

    visible_count = int(evidence.get("visibleJobLinkCount", 0) or 0)
    if visible_count <= 0:
        return None
    if not (
        evidence.get("activeCanadaChip")
        or evidence.get("countryFacetChecked")
    ):
        return None

    return {
        "confirmed": True,
        "method": "page_evidence",
        "reason": (
            "RBC's visible results page showed an active Canada filter before pagination."
        ),
        "visible_job_link_count": visible_count,
        "active_canada_chip": bool(evidence.get("activeCanadaChip")),
        "country_facet_present": bool(evidence.get("countryFacetPresent")),
        "country_facet_checked": bool(evidence.get("countryFacetChecked")),
        "sample_hrefs": list(evidence.get("sampleHrefs") or []),
    }


def detect_bmo_canada_page_evidence(page: Page) -> dict[str, Any] | None:
    """Return trusted Canada-scope evidence from BMO's visible results page when available."""

    if not is_bmo_careers_search_url(page.url):
        return None

    try:
        evidence = page.evaluate(
            """
            () => {
              const visible = (element) => {
                if (!element || typeof element.getBoundingClientRect !== 'function') return false;
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none'
                  && style.visibility !== 'hidden'
                  && rect.width > 0
                  && rect.height > 0;
              };

              const activeCanadaChip = Array.from(
                document.querySelectorAll('button, a, span, div')
              ).some((node) => {
                if (!visible(node)) return false;
                const text = (node.textContent || '').trim();
                const parentText = (node.parentElement?.textContent || '').trim();
                return text === 'Canada' && parentText.includes('Clear all');
              });

              const countryFacet = document.querySelector(
                'input[data-ph-at-facetkey="facet-country"][data-ph-at-text="Canada"]'
              );
              const countryFacetChecked = Boolean(
                countryFacet
                && (
                  countryFacet.checked
                  || String(
                    countryFacet.getAttribute('aria-checked') || ''
                  ).toLowerCase() === 'true'
                )
              );

              const visibleLinks = Array.from(
                document.querySelectorAll('a[data-ph-at-id="job-link"]')
              ).filter((node) => visible(node));
              const sampleHrefs = visibleLinks.slice(0, 10).map((node) => node.href || '');
              const allVisibleEnca = sampleHrefs.length > 0
                && sampleHrefs.every((href) => href.includes('EXTERNALENCA'));
              const anyVisibleEnus = sampleHrefs.some((href) => href.includes('EXTERNALENUS'));

              return {
                activeCanadaChip,
                countryFacetChecked,
                visibleJobLinkCount: visibleLinks.length,
                allVisibleEnca,
                anyVisibleEnus,
                sampleHrefs,
              };
            }
            """,
        )
    except Exception:  # noqa: BLE001
        return None

    if not isinstance(evidence, dict):
        return None

    visible_count = int(evidence.get("visibleJobLinkCount", 0) or 0)
    if visible_count <= 0:
        return None
    if not evidence.get("allVisibleEnca") or evidence.get("anyVisibleEnus"):
        return None

    return {
        "confirmed": True,
        "method": "page_evidence",
        "reason": (
            "BMO's visible results page exposes only Canada (`EXTERNALENCA`) job result "
            "links and no visible US (`EXTERNALENUS`) result links."
        ),
        "visible_job_link_count": visible_count,
        "active_canada_chip": bool(evidence.get("activeCanadaChip")),
        "country_facet_checked": bool(evidence.get("countryFacetChecked")),
        "sample_hrefs": list(evidence.get("sampleHrefs") or []),
    }


def _count_visible_bmo_job_links(page: Page) -> int:
    """Return the count of visible BMO result links on the current page."""

    if not is_bmo_careers_search_url(page.url):
        return 0

    try:
        count = page.evaluate(
            """
            () => {
              const visible = (element) => {
                if (!element || typeof element.getBoundingClientRect !== 'function') return false;
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none'
                  && style.visibility !== 'hidden'
                  && rect.width > 0
                  && rect.height > 0;
              };

              return Array.from(
                document.querySelectorAll('a[data-ph-at-id="job-link"]')
              ).filter((node) => visible(node)).length;
            }
            """,
        )
    except Exception:  # noqa: BLE001
        return 0

    try:
        return int(count or 0)
    except (TypeError, ValueError):
        return 0


def _wait_for_visible_bmo_job_links(
    page: Page,
    *,
    min_links: int = 1,
    max_polls: int = 10,
    poll_delay_ms: int = 500,
) -> int:
    """Allow BMO's client-side results grid time to render visible job links."""

    if not is_bmo_careers_search_url(page.url):
        return 0

    last_count = 0
    for _ in range(max_polls):
        last_count = _count_visible_bmo_job_links(page)
        if last_count >= min_links:
            return last_count
        page.wait_for_timeout(poll_delay_ms)
    return last_count


def dismiss_ibm_language_prompt(page: Page) -> str | None:
    """Dismiss IBM's French geo/language prompt without switching locales."""

    if not is_ibm_careers_search_url(page.url):
        return None
    for selector in IBM_LANGUAGE_DISMISS_SELECTORS:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            locator.first.click()
            page.wait_for_timeout(1_000)
            return selector
    return None


def apply_ibm_canada_filter(
    page: Page,
    location_scope: Iterable[str],
) -> str | None:
    """Apply IBM's public Canada location facet when the current page supports it."""

    if not is_ibm_careers_search_url(page.url):
        return None
    normalized_scope = {
        str(item).strip().lower() for item in location_scope if str(item).strip()
    }
    if "canada" not in normalized_scope:
        return None

    before_url = page.url
    try:
        location_button = page.locator("button:has-text('Location')").first
        if location_button.is_visible():
            location_button.click()
            page.wait_for_timeout(500)
    except Exception:  # noqa: BLE001
        return None

    for selector in IBM_CANADA_FILTER_SELECTORS:
        locator = page.locator(selector)
        if locator.count() == 0 or not locator.first.is_visible():
            continue
        try:
            candidate = locator.first
            if hasattr(candidate, "is_checked") and candidate.is_checked():
                return "Canada (IBM location facet)"
            if hasattr(candidate, "check"):
                candidate.check(force=True)
            else:
                candidate.click(force=True)
            for _ in range(8):
                page.wait_for_timeout(500)
                current_url = page.url
                if (
                    current_url != before_url
                    or "field_keyword_05[0]=canada" in current_url.lower()
                    or "field_keyword_05%5b0%5d=canada" in current_url.lower()
                ):
                    return "Canada (IBM location facet)"
        except Exception:  # noqa: BLE001
            continue
    return None


def _count_visible_ntt_job_links(page: Page) -> int:
    """Return the count of visible NTT DATA result links on the current page."""

    if not is_ntt_careers_search_url(page.url):
        return 0

    try:
        count = page.evaluate(
            """
            () => {
              const visible = (element) => {
                if (!element || typeof element.getBoundingClientRect !== 'function') return false;
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none'
                  && style.visibility !== 'hidden'
                  && rect.width > 0
                  && rect.height > 0;
              };

              return Array.from(
                document.querySelectorAll('a.au-target[href*="/job/"]')
              ).filter((node) => visible(node)).length;
            }
            """,
        )
    except Exception:  # noqa: BLE001
        return 0

    try:
        return int(count or 0)
    except (TypeError, ValueError):
        return 0


def _count_visible_rbc_job_links(page: Page) -> int:
    """Return the count of visible RBC result links on the current page."""

    if not is_rbc_careers_search_url(page.url):
        return 0

    try:
        count = page.evaluate(
            """
            () => {
              const visible = (element) => {
                if (!element || typeof element.getBoundingClientRect !== 'function') return false;
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none'
                  && style.visibility !== 'hidden'
                  && rect.width > 0
                  && rect.height > 0;
              };

              return Array.from(
                document.querySelectorAll('a[data-ph-at-id="job-link"]')
              ).filter((node) => visible(node)).length;
            }
            """,
        )
    except Exception:  # noqa: BLE001
        return 0

    try:
        return int(count or 0)
    except (TypeError, ValueError):
        return 0


def apply_ntt_canada_filter(
    page: Page,
    location_scope: Iterable[str],
) -> str | None:
    """Apply NTT DATA's public Canada country facet when the page exposes it."""

    if not is_ntt_careers_search_url(page.url):
        return None
    normalized_scope = {
        str(item).strip().lower() for item in location_scope if str(item).strip()
    }
    if "canada" not in normalized_scope:
        return None

    try:
        country_button = page.locator("button:has-text('Country')").first
        if country_button.is_visible():
            country_button.click()
            page.wait_for_timeout(500)
    except Exception:  # noqa: BLE001
        return None

    selectors = (
        "input[name^='country_phs_'][aria-label*='Canada' i]",
        "input[type='checkbox'][aria-label*='Canada' i]",
    )
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() == 0 or not locator.first.is_visible():
            continue
        checkbox = locator.first
        try:
            if hasattr(checkbox, "is_checked") and checkbox.is_checked():
                return "Canada (NTT country facet)"
            if hasattr(checkbox, "check"):
                checkbox.check(force=True)
            else:
                checkbox.click(force=True)
            for _ in range(10):
                page.wait_for_timeout(500)
                is_checked = hasattr(checkbox, "is_checked") and checkbox.is_checked()
                if is_checked and _count_visible_ntt_job_links(page) > 0:
                    return "Canada (NTT country facet)"
            if hasattr(checkbox, "is_checked") and checkbox.is_checked():
                return "Canada (NTT country facet)"
        except Exception:  # noqa: BLE001
            continue
    return None


def apply_rbc_canada_filter(
    page: Page,
    location_scope: Iterable[str],
) -> str | None:
    """Apply RBC's public Country=Canada facet when the page exposes it."""

    if not is_rbc_careers_search_url(page.url):
        return None
    normalized_scope = {
        str(item).strip().lower() for item in location_scope if str(item).strip()
    }
    if "canada" not in normalized_scope:
        return None

    try:
        country_button = page.locator("button:has-text('Country')").first
        if country_button.is_visible():
            country_button.click()
            page.wait_for_timeout(500)
    except Exception:  # noqa: BLE001
        return None

    selectors = (
        "label:has(input[data-ph-at-facetkey='facet-country'][data-ph-at-text='Canada'])",
        "input[data-ph-at-facetkey='facet-country'][data-ph-at-text='Canada']",
        "label:has-text('Canada')",
    )
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() == 0 or not locator.first.is_visible():
            continue
        candidate = locator.first
        try:
            if hasattr(candidate, "is_checked") and candidate.is_checked():
                return "Canada (RBC country facet)"
            if hasattr(candidate, "check"):
                candidate.check(force=True)
            else:
                try:
                    candidate.click(force=True)
                except TypeError:
                    candidate.click()
            for _ in range(10):
                page.wait_for_timeout(500)
                evidence = detect_rbc_canada_page_evidence(page)
                if evidence or _count_visible_rbc_job_links(page) > 0:
                    return "Canada (RBC country facet)"
        except Exception:  # noqa: BLE001
            continue
    return None


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
    if isinstance(count, bool):
        return count
    if isinstance(count, int):
        return count > 0
    if isinstance(count, list):
        for item in count:
            if not isinstance(item, Mapping):
                continue
            combined = _clean_text(
                f"{item.get('aria', '')} {item.get('text', '')} {item.get('label', '')}"
            ).lower()
            if "view job:" in combined or "expand job details" in combined:
                return True
        return False
    return False


def _page_already_shows_job_results(page: Page) -> bool:
    """Return True when the current page already exposes visible job results."""

    if has_interactive_job_cards(page):
        return True
    if detect_bmo_canada_page_evidence(page):
        return True
    if not _is_search_results_style_page(page):
        return False

    body_text = _safe_locator_inner_text(page.locator("body"), timeout=3_000).lower()
    if re.search(r"\b\d+\s*-\s*\d+\s+of\s+\d+\s+results\b", body_text):
        return True
    if re.search(r"\b\d+\s+jobs?\b", body_text) and "sort by" in body_text:
        return True
    return False


def navigate_to_job_search_page(page: Page) -> str | None:
    """Move from a careers landing page to an on-site job-search/results page when visible."""

    if _page_already_shows_job_results(page):
        return None

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
        resolved = _normalize_actionable_url(page.url, href)
        if not resolved:
            continue
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
    before_text = _safe_locator_inner_text(page.locator("body"), timeout=3_000)[:1200]
    for candidate in normalized:
        target_text = candidate["text"].lower()
        target_aria = candidate["aria"].lower()
        if candidate["href"]:
            continue
        for index in range(candidate_count):
            element = locator.nth(index)
            if not element.is_visible():
                continue
            text = _safe_locator_inner_text(element).lower()
            aria = _safe_locator_attribute(element, "aria-label").lower()
            if (target_text and text == target_text) or (target_aria and aria == target_aria):
                element.click()
                page.wait_for_timeout(2_000)
                after_url = page.url
                after_text = _safe_locator_inner_text(page.locator("body"), timeout=3_000)[:1200]
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


def _safe_locator_inner_text(locator: Locator, *, timeout: int | None = None) -> str:
    try:
        if timeout is None:
            return _clean_text(locator.inner_text())
        return _clean_text(locator.inner_text(timeout=timeout))
    except Exception:  # noqa: BLE001
        return ""


def _safe_locator_attribute(locator: Locator, name: str) -> str:
    try:
        return _clean_text(locator.get_attribute(name))
    except Exception:  # noqa: BLE001
        return ""


def _normalize_actionable_url(base_url: str, candidate_url: str | None) -> str | None:
    raw = str(candidate_url or "").strip()
    if not raw or raw.startswith("#"):
        return None

    parsed = urlparse(raw)
    scheme = parsed.scheme.lower()
    if scheme in NON_NAVIGABLE_URL_SCHEMES:
        return None
    if scheme and scheme not in {"http", "https"}:
        return None

    resolved = urljoin(base_url, raw)
    resolved_parsed = urlparse(resolved)
    if resolved_parsed.scheme.lower() not in {"http", "https"}:
        return None
    return resolved


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
    if "/apply" in normalized_href:
        return True
    if (
        "search-results?" in normalized_href
        and "read full job description" not in normalized_context
    ):
        return True
    return False


def _registrable_domain(hostname: str) -> str:
    parts = [part for part in hostname.lower().split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return hostname.lower()


def _is_usable_job_url(job_url: str) -> bool:
    return _normalize_actionable_url("https://example.invalid", job_url) is not None


def _is_allowed_external_job_link(job_url: str, base_url: str | None) -> bool:
    job_host = urlparse(job_url).netloc.lower()
    if not job_host:
        return True
    if _is_restricted_url(job_url):
        return False
    if not base_url:
        return True
    base_host = urlparse(base_url).netloc.lower()
    if not base_host:
        return True
    if job_host == base_host:
        return True
    if _registrable_domain(job_host) == _registrable_domain(base_host):
        return True
    normalized = f"{job_host}{urlparse(job_url).path}".lower()
    return any(hint in normalized for hint in ALLOWED_EXTERNAL_JOB_HOST_HINTS)


def _looks_like_marketing_title(title: str) -> bool:
    normalized = title.lower()
    return (
        normalized.startswith(MARKETING_TITLE_PREFIXES)
        or normalized in MARKETING_TITLE_EXACT_HINTS
        or normalized.endswith(" careers")
        or normalized.endswith("?")
    )


def _looks_like_generic_non_job_title(title: str) -> bool:
    normalized = title.lower()
    if normalized in GENERIC_NON_JOB_TITLES:
        return True
    if normalized.startswith(GENERIC_NON_JOB_TITLE_PREFIXES):
        return True
    return bool(re.search(r"\b\d+\s+available jobs?\b", normalized))


def _looks_like_facet_count_title(title: str) -> bool:
    normalized = title.lower()
    return re.fullmatch(r"[a-z0-9/&,\- ]+\(\d+\)", normalized) is not None


def _looks_like_index_or_category_url(job_url: str) -> bool:
    path = urlparse(job_url).path.lower().rstrip("/")
    if not path:
        return False
    if any(path == suffix or path.endswith(suffix) for suffix in INDEX_PAGE_PATH_SUFFIXES):
        return True
    return re.search(r"/c/[^/]+-jobs$", path) is not None


def _has_job_title_hint(title: str) -> bool:
    normalized = title.lower()
    return any(
        re.search(rf"\b{re.escape(hint)}\b", normalized)
        for hint in JOB_TITLE_HINTS
    )


def _looks_like_empty_results_page(text: str) -> bool:
    normalized = text.lower()
    return any(hint in normalized for hint in EMPTY_RESULTS_HINTS)


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
    return _normalize_actionable_url(base_url, href)


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
    has_job_url_hint = any(hint in normalized_href for hint in JOB_URL_HINTS)
    has_posting_text = any(
        marker in normalized_description
        for marker in ("posted", "apply", "job id", "job req", "requisition", "req id")
    )
    has_location = bool(_clean_text(location))
    has_meaningful_title = len(normalized_title) >= 4
    return has_meaningful_title and (
        has_job_url_hint
        or has_posting_text
        or (has_location and _has_job_title_hint(title))
    )


def is_probable_job_listing(
    job: Mapping[str, Any],
    *,
    base_url: str | None = None,
) -> bool:
    """Return True when a discovered record looks actionable enough to keep."""

    title = _normalize_job_title_text(job.get("title"))
    description = _clean_text(job.get("description"))
    location = _clean_text(job.get("location")) or None
    job_url = str(job.get("job_url") or "").strip()
    apply_url = str(job.get("apply_url") or "").strip()
    external_job_id = _clean_text(job.get("external_job_id"))
    ats_type = _clean_text(job.get("ats_type"))
    board_slug = _clean_text(job.get("board_slug"))
    has_external_identity = bool(external_job_id and (ats_type or board_slug))

    if not title:
        return False
    if (
        _looks_like_marketing_title(title)
        or _looks_like_generic_non_job_title(title)
        or _looks_like_facet_count_title(title)
    ):
        return False
    if job_url and not _is_usable_job_url(job_url):
        return False
    if job_url and not _is_allowed_external_job_link(job_url, base_url):
        return False
    if _is_noise_candidate(title, job_url, description):
        return False
    if job_url and not has_external_identity and _looks_like_index_or_category_url(job_url):
        return False

    has_job_signal = _has_job_posting_signal(
        title=title,
        href=" ".join(part for part in (job_url, apply_url) if part),
        description=description,
        location=location,
    )
    has_job_title = _has_job_title_hint(title)
    has_context_signal = bool(location) or any(
        marker in description.lower()
        for marker in ("posted", "full-time", "part-time", "contract", "requisition", "job")
    )
    has_jobish_url = any(
        hint in " ".join(part for part in (job_url, apply_url) if part).lower()
        for hint in JOB_URL_HINTS
    )

    if not job_url and not has_external_identity:
        return False
    if has_external_identity or has_jobish_url:
        return True
    return has_job_title and (has_job_signal or has_context_signal)


def get_job_quality_signals(
    job: Mapping[str, Any],
    *,
    base_url: str | None = None,
) -> list[str]:
    """Return debug-friendly quality flags for suspicious rows."""

    title = _normalize_job_title_text(job.get("title"))
    job_url = str(job.get("job_url") or "").strip()
    external_job_id = _clean_text(job.get("external_job_id"))
    ats_type = _clean_text(job.get("ats_type"))
    board_slug = _clean_text(job.get("board_slug"))
    source_mode = _clean_text(job.get("source_mode"))
    has_external_identity = bool(external_job_id and (ats_type or board_slug))
    signals: list[str] = []

    if not title:
        signals.append("missing_title")
    if _looks_like_generic_non_job_title(title):
        signals.append("generic_title")
    if _looks_like_facet_count_title(title):
        signals.append("facet_count_title")
    if _looks_like_marketing_title(title):
        signals.append("marketing_title")
    if not job_url and not has_external_identity:
        signals.append("missing_url")
    if job_url and not _is_usable_job_url(job_url):
        signals.append("non_actionable_url")
    if job_url and not has_external_identity and _looks_like_index_or_category_url(job_url):
        signals.append("index_or_category_url")
    if (
        source_mode in {"browser_allowed", "human_in_loop"}
        and not has_external_identity
        and signals
    ):
        signals.append("browser_without_external_id")
    return signals


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
    raw_href = str(href or "").strip()
    if raw_href:
        resolved_href = _normalize_actionable_url(base_url, raw_href)
        if resolved_href is None:
            return None
    else:
        resolved_href = base_url if allow_base_url_fallback else None
    cleaned_location = _clean_text(location) or extract_location(cleaned_description) or None
    if not cleaned_title or (resolved_href and _is_restricted_url(resolved_href)):
        return None
    if not is_probable_job_listing(
        {
            "title": cleaned_title,
            "location": cleaned_location,
            "job_url": resolved_href,
            "apply_url": apply_url,
            "description": cleaned_description,
            "external_job_id": None,
            "ats_type": "structured" if structured_source else None,
            "board_slug": urlparse(base_url).netloc.lower() if structured_source else None,
        },
        base_url=base_url,
    ):
        return None

    job = {
        "company_name": company_name,
        "title": cleaned_title,
        "location": cleaned_location,
        "job_url": resolved_href,
        "apply_url": _normalize_actionable_url(base_url, apply_url) if apply_url else None,
        "source_name": source_name,
        "source_mode": source_mode,
        "description": cleaned_description or None,
        "date_posted": date_posted,
        "status": "new",
    }
    return job


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
        if not title:
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
        if not title:
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
            has_explicit_link = container.select_one("a[href]") is not None
            text = _clean_text(container.get_text(" ", strip=True))
            if _is_page_shell_container(container, text):
                continue
            if not title:
                continue
            job = _build_job_record(
                company_name=company_name,
                source_name=source_name,
                source_mode=source_mode,
                title=title,
                base_url=base_url,
                href=href,
                description=text,
                allow_base_url_fallback=not has_explicit_link,
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


def _extract_visible_bmo_job_cards(
    page: Page,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
) -> list[dict[str, Any]]:
    """Extract only visible BMO/Phenom result cards from the live page DOM."""

    if not is_bmo_careers_search_url(page.url):
        return []

    try:
        items = page.evaluate(
            """
            () => {
              const visible = (element) => {
                if (!element || typeof element.getBoundingClientRect !== 'function') return false;
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none'
                  && style.visibility !== 'hidden'
                  && rect.width > 0
                  && rect.height > 0;
              };

              return Array.from(
                document.querySelectorAll('a[data-ph-at-id="job-link"]')
              )
                .filter((node) => visible(node))
                .map((node) => {
                  const title = (
                    node.getAttribute('data-ph-at-job-title-text')
                    || node.textContent
                    || ''
                  ).trim();
                  const href = (node.getAttribute('href') || '').trim();
                  const card = node.closest('li, article, section, div');
                  const description = ((card?.innerText) || '').replace(/\\s+/g, ' ').trim();
                  return { title, href, description };
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
        job = _build_job_record(
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            title=_clean_text(item.get("title")),
            base_url=page.url,
            href=str(item.get("href") or "").strip(),
            description=_clean_text(item.get("description")),
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
        if not title:
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
    include_bmo_structured: bool = True,
) -> list[dict[str, Any]]:
    """Extract plausible job records from one HTML document."""

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
    if include_bmo_structured:
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
                try:
                    locator.first.click()
                    page.wait_for_timeout(1_000)
                    return selector
                except Exception:  # noqa: BLE001
                    continue
        if attempt < 5:
            page.wait_for_timeout(500)

    top_page_text = _safe_locator_inner_text(page.locator("body"), timeout=3_000)[:1200].lower()
    if "cookie" in top_page_text or "consent" in top_page_text:
        locator = page.locator("button, a, [role='button']")
        candidate_count = min(locator.count(), 40)
        for index in range(candidate_count):
            candidate = locator.nth(index)
            if not candidate.is_visible():
                continue
            label = _safe_locator_inner_text(candidate).lower()
            if label in COOKIE_ACCEPT_TEXT_HINTS:
                try:
                    candidate.click()
                    page.wait_for_timeout(1_000)
                    return label
                except Exception:  # noqa: BLE001
                    continue

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
    current_host = urlparse(page.url).netloc.lower()
    priority_selectors = (
        "[aria-label='Next']",
        "button[aria-label*='Next' i]",
        "a[aria-label*='Next' i]",
        "a[aria-label*='Go to Next Page' i]",
        "a:has-text('NEXT')",
        "a:has-text('Next')",
        "button:has-text('NEXT')",
        "button:has-text('Next')",
        "li.active + li a[title^='Page ']",
        "li.active + li a[href*='startrow=']",
    )
    for selector in priority_selectors:
        locator = page.locator(selector)
        if locator.count() == 0 or not locator.first.is_visible():
            continue
        candidate = locator.first
        try:
            enabled = candidate.is_enabled()
        except Exception:  # noqa: BLE001
            enabled = True
        if not enabled:
            continue
        href = _safe_locator_attribute(candidate, "href")
        onclick = _safe_locator_attribute(candidate, "onclick")
        if _is_safe_same_page_pagination_action(href, onclick):
            return candidate
        if href:
            resolved = _normalize_actionable_url(page.url, href)
            if resolved:
                resolved_host = urlparse(resolved).netloc.lower()
                if resolved_host and resolved_host != current_host:
                    continue
                if _is_restricted_url(resolved):
                    continue
        return candidate

    locator = page.locator("button, a, [role='button']")
    candidate_count = min(locator.count(), 150)

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

        text = _safe_locator_inner_text(candidate).lower()
        aria = _safe_locator_attribute(candidate, "aria-label").lower()
        title = _safe_locator_attribute(candidate, "title").lower()
        combined = " ".join(part for part in (text, aria, title) if part)
        if not any(
            re.search(rf"\b{re.escape(label)}\b", combined)
            for label in PAGINATION_LABELS
        ):
            continue
        if any(
            blocked in combined for blocked in ("sign in", "log in", "linkedin", "indeed")
        ):
            continue
        href = _safe_locator_attribute(candidate, "href")
        onclick = _safe_locator_attribute(candidate, "onclick")
        if _is_safe_same_page_pagination_action(href, onclick):
            return candidate
        if href:
            resolved = _normalize_actionable_url(page.url, href)
            if not resolved:
                continue
            resolved_host = urlparse(resolved).netloc.lower()
            if resolved_host and resolved_host != current_host:
                continue
            if _is_restricted_url(resolved):
                continue
        return candidate
    return None


def _is_safe_same_page_pagination_action(href: str, onclick: str) -> bool:
    normalized_href = str(href or "").strip().lower()
    normalized_onclick = str(onclick or "").strip().lower()
    return any(
        action.startswith("javascript:gotopage(") or action.startswith("gotopage(")
        for action in (normalized_href, normalized_onclick)
    )


def _job_identity_key(job: Mapping[str, Any]) -> tuple[str, str]:
    job_url = str(job.get("job_url") or "").strip()
    if job_url:
        return ("url", job_url)
    title = str(job.get("title") or "").strip()
    location = str(job.get("location") or "").strip()
    return ("fallback", f"{title}|{location}")


def _wait_for_page_settle(
    page: Page,
    *,
    before_url: str,
    before_html: str,
    max_polls: int = 8,
    poll_delay_ms: int = 500,
) -> tuple[str, str]:
    latest_url = page.url
    latest_html = page.content()
    stable_polls = 0

    for _ in range(max_polls):
        page.wait_for_timeout(poll_delay_ms)
        current_url = page.url
        current_html = page.content()
        if current_url == latest_url and current_html == latest_html:
            stable_polls += 1
            if stable_polls >= 2 and (
                current_url != before_url or current_html != before_html
            ):
                return current_url, current_html
            continue
        latest_url = current_url
        latest_html = current_html
        stable_polls = 0

    return latest_url, latest_html


def extract_visible_job_cards_with_diagnostics(
    page: Page,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    max_cards: int = 20,
    max_pages: int = 2,
    capture_page_html: bool = False,
) -> tuple[list[dict[str, Any]], ExtractionDiagnostics]:
    """Extract plausible jobs and return pagination diagnostics for the pass."""

    if _is_restricted_url(page.url):
        diagnostics = ExtractionDiagnostics(
            pages_visited=[],
            jobs_extracted_per_page=[],
            pagination_detected=False,
            pagination_stop_reason="restricted_url",
            max_pages=max_pages,
            total_candidates_before_dedupe=0,
            total_candidates_after_dedupe=0,
            page_html_snapshots=[],
        )
        return [], diagnostics

    candidates: list[dict[str, Any]] = []
    pages_visited: list[str] = []
    jobs_extracted_per_page: list[int] = []
    page_html_snapshots: list[dict[str, str]] = []
    seen_job_identities: set[tuple[str, str]] = set()
    pagination_detected = False
    pagination_stop_reason = "single_page_only"

    _wait_for_visible_bmo_job_links(page)
    interactive_jobs = _extract_from_interactive_cards(
        page,
        company_name=company_name,
        source_name=source_name,
        source_mode=source_mode,
    )
    candidates.extend(interactive_jobs)
    seen_job_identities.update(_job_identity_key(job) for job in interactive_jobs)

    visible_bmo_jobs = _extract_visible_bmo_job_cards(
        page,
        company_name=company_name,
        source_name=source_name,
        source_mode=source_mode,
    )
    candidates.extend(visible_bmo_jobs)
    seen_job_identities.update(_job_identity_key(job) for job in visible_bmo_jobs)

    current_url = page.url
    current_html = page.content()
    current_jobs = (
        []
        if visible_bmo_jobs
        else extract_jobs_from_html(
            current_html,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
            base_url=current_url,
            max_cards=max_cards,
        )
    )
    current_page_candidates = visible_bmo_jobs or current_jobs
    pages_visited.append(current_url)
    jobs_extracted_per_page.append(len(current_page_candidates))
    if capture_page_html:
        page_html_snapshots.append({"url": current_url, "html": current_html})
    candidates.extend(current_jobs)
    seen_job_identities.update(_job_identity_key(job) for job in current_jobs)

    for _ in range(max(0, max_pages - 1)):
        target = _find_safe_pagination_target(page)
        if target is None:
            pagination_stop_reason = (
                "next_disabled_or_missing" if pagination_detected else "pagination_not_detected"
            )
            break
        pagination_detected = True
        before_url = page.url
        before_html = page.content()
        target.click()
        after_url, after_html = _wait_for_page_settle(
            page,
            before_url=before_url,
            before_html=before_html,
        )
        _wait_for_visible_bmo_job_links(page)
        after_url = page.url
        after_html = page.content()
        if after_url == before_url and after_html == before_html:
            pagination_stop_reason = "no_page_change"
            break

        page_visible_bmo_jobs = _extract_visible_bmo_job_cards(
            page,
            company_name=company_name,
            source_name=source_name,
            source_mode=source_mode,
        )
        page_jobs = (
            []
            if page_visible_bmo_jobs
            else extract_jobs_from_html(
                after_html,
                company_name=company_name,
                source_name=source_name,
                source_mode=source_mode,
                base_url=after_url,
                max_cards=max_cards,
            )
        )
        page_candidates = page_visible_bmo_jobs or page_jobs
        pages_visited.append(after_url)
        jobs_extracted_per_page.append(len(page_candidates))
        if capture_page_html:
            page_html_snapshots.append({"url": after_url, "html": after_html})

        new_jobs = [
            job for job in page_candidates if _job_identity_key(job) not in seen_job_identities
        ]
        candidates.extend(page_candidates)
        if not new_jobs:
            pagination_stop_reason = "no_new_job_urls"
            break
        seen_job_identities.update(_job_identity_key(job) for job in new_jobs)
    else:
        pagination_stop_reason = "max_pages_reached"

    deduped = _dedupe_jobs(candidates, max_cards=max_cards)
    diagnostics = ExtractionDiagnostics(
        pages_visited=pages_visited,
        jobs_extracted_per_page=jobs_extracted_per_page,
        pagination_detected=pagination_detected,
        pagination_stop_reason=pagination_stop_reason,
        max_pages=max_pages,
        total_candidates_before_dedupe=len(candidates),
        total_candidates_after_dedupe=len(deduped),
        page_html_snapshots=page_html_snapshots,
    )
    return deduped, diagnostics


def extract_visible_job_cards(
    page: Page,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    max_cards: int = 20,
    max_pages: int = 2,
) -> list[dict[str, Any]]:
    """Extract plausible jobs from the current page and safe pagination flow."""

    jobs, _ = extract_visible_job_cards_with_diagnostics(
        page,
        company_name=company_name,
        source_name=source_name,
        source_mode=source_mode,
        max_cards=max_cards,
        max_pages=max_pages,
    )
    return jobs


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
