"""Playwright browser session helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


@dataclass(slots=True)
class BrowserSessionConfig:
    """Runtime settings for browser-assisted collection."""

    headless: bool = False
    slow_mo_ms: int = 0
    timeout_ms: int = 15_000


@dataclass(slots=True)
class BrowserSession:
    """Container for the active Playwright objects."""

    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page


@contextmanager
def open_browser_session(
    config: BrowserSessionConfig | None = None,
) -> Iterator[BrowserSession]:
    """Open a Playwright Chromium session in headed mode by default."""

    session_config = config or BrowserSessionConfig()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=session_config.headless,
            slow_mo=session_config.slow_mo_ms,
        )
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(session_config.timeout_ms)
        try:
            yield BrowserSession(
                playwright=playwright,
                browser=browser,
                context=context,
                page=page,
            )
        finally:
            context.close()
            browser.close()
