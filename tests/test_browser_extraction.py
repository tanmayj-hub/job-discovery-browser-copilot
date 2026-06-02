from __future__ import annotations

from pathlib import Path

from browser.extraction import extract_jobs_from_html, extract_visible_job_cards

FIXTURES_DIR = Path("tests/fixtures/browser")


class FakeLocatorItem:
    def __init__(self, page, label: str, href: str | None = None, *, enabled: bool = True) -> None:
        self.page = page
        self.label = label
        self.href = href
        self.enabled = enabled

    def is_visible(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return self.enabled

    def inner_text(self) -> str:
        return self.label

    def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self.href
        return None

    def click(self) -> None:
        self.page.advance()


class FakeLocatorCollection:
    def __init__(self, items: list[FakeLocatorItem]) -> None:
        self.items = items

    def count(self) -> int:
        return len(self.items)

    def nth(self, index: int) -> FakeLocatorItem:
        return self.items[index]


class FakePage:
    def __init__(self, urls: list[str], html_pages: list[str]) -> None:
        self.urls = urls
        self.html_pages = html_pages
        self.index = 0

    @property
    def url(self) -> str:
        return self.urls[self.index]

    def content(self) -> str:
        return self.html_pages[self.index]

    def locator(self, selector: str) -> FakeLocatorCollection:
        if selector != "button, a, [role='button']":
            return FakeLocatorCollection([])
        if self.index == 0:
            return FakeLocatorCollection(
                [FakeLocatorItem(self, "Next", "/careers?page=2", enabled=True)]
            )
        return FakeLocatorCollection(
            [FakeLocatorItem(self, "Next", None, enabled=False)]
        )

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def advance(self) -> None:
        if self.index < len(self.html_pages) - 1:
            self.index += 1


def test_extract_jobs_from_html_uses_anchor_and_card_strategies() -> None:
    html = (FIXTURES_DIR / "anchors_cards.html").read_text(encoding="utf-8")

    jobs = extract_jobs_from_html(
        html,
        company_name="Example Co",
        source_name="company-careers",
        source_mode="browser_allowed",
        base_url="https://careers.example.com",
    )

    titles = {job["title"] for job in jobs}

    assert "Cloud Engineer" in titles
    assert "Platform DevOps Engineer" in titles
    assert all(job["match_score"] > 0 for job in jobs)
    assert all("privacy" not in job["job_url"].lower() for job in jobs)


def test_extract_visible_job_cards_uses_jsonld_table_and_safe_pagination() -> None:
    page1 = (FIXTURES_DIR / "jsonld_table_page1.html").read_text(encoding="utf-8")
    page2 = (FIXTURES_DIR / "jsonld_table_page2.html").read_text(encoding="utf-8")
    page = FakePage(
        urls=[
            "https://careers.example.com/careers",
            "https://careers.example.com/careers?page=2",
        ],
        html_pages=[page1, page2],
    )

    jobs = extract_visible_job_cards(
        page,
        company_name="Example Co",
        source_name="company-careers",
        source_mode="browser_allowed",
        max_pages=2,
    )

    titles = {job["title"] for job in jobs}

    assert "Cloud Support Engineer" in titles
    assert "Linux Administrator" in titles
    assert "Site Reliability Engineer" in titles
    assert len(jobs) == 3
    assert all(job["match_score"] > 0 for job in jobs)
