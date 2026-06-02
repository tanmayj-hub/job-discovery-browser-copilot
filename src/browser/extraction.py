"""Visible-page extraction helpers for browser-assisted job collection."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

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


def extract_visible_job_cards(
    page: Page,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    max_cards: int = 20,
) -> list[dict[str, Any]]:
    """Extract visible job-like links from the current page."""

    base_url = page.url
    cards = page.evaluate(
        """
        ({ maxCards, roleHints }) => {
          const isVisible = (element) => {
            const style = window.getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return (
              style &&
              style.visibility !== "hidden" &&
              style.display !== "none" &&
              rect.width > 0 &&
              rect.height > 0
            );
          };

          const anchors = Array.from(document.querySelectorAll("a[href]"));
          const results = [];
          const seen = new Set();

          for (const anchor of anchors) {
            if (!isVisible(anchor)) continue;
            const title = (anchor.innerText || anchor.textContent || "").trim();
            if (!title || title.length < 4 || title.length > 120) continue;
            const normalized = title.toLowerCase();
            if (!roleHints.some((hint) => normalized.includes(hint))) continue;

            const container =
              anchor.closest("article, li, tr, section, div") || anchor.parentElement || anchor;
            const description = (container.innerText || "").trim().replace(/\\s+/g, " ");
            const href = anchor.href || "";
            const key = `${title}::${href}`;
            if (seen.has(key)) continue;
            seen.add(key);

            results.push({
              title,
              href,
              text: description.slice(0, 700),
            });
            if (results.length >= maxCards) break;
          }

          return results;
        }
        """,
        {"maxCards": max_cards, "roleHints": list(JOB_ROLE_HINTS)},
    )

    extracted_jobs: list[dict[str, Any]] = []
    for card in cards:
        description = str(card.get("text", "")).strip()
        title = str(card.get("title", "")).strip()
        if not title:
            continue

        normalized_job = {
            "company_name": company_name,
            "title": title,
            "location": extract_location(description),
            "job_url": urljoin(base_url, str(card.get("href", "")).strip()) or base_url,
            "apply_url": None,
            "source_name": source_name,
            "source_mode": source_mode,
            "description": description,
            "date_posted": None,
            "status": "new",
        }
        score_result = score_job(normalized_job)
        normalized_job["match_score"] = score_result.match_score
        normalized_job["match_reasons"] = score_result.match_reasons
        normalized_job["risk_flags"] = score_result.risk_flags
        extracted_jobs.append(normalized_job)

    return extracted_jobs


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
