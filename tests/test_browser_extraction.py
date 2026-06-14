from __future__ import annotations

from pathlib import Path

from browser.extraction import (
    apply_ibm_canada_filter,
    apply_ntt_canada_filter,
    detect_bmo_canada_page_evidence,
    dismiss_cookie_banner,
    dismiss_ibm_language_prompt,
    extract_jobs_from_html,
    extract_visible_job_cards,
    extract_visible_job_cards_with_diagnostics,
    has_interactive_job_cards,
    is_ibm_careers_search_url,
    is_probable_job_listing,
    navigate_to_job_search_page,
    search_with_location_term,
)
from processing.score import score_job

FIXTURES_DIR = Path("tests/fixtures/browser")


def _ibm_job_article(job_id: str) -> str:
    return (
        '<article><a href="https://careers.ibm.com/en_US/careers/JobDetail'
        f'?jobId={job_id}">Job {job_id}</a></article>'
    )


class FakeLocatorItem:
    def __init__(
        self,
        page,
        label: str,
        href: str | None = None,
        *,
        enabled: bool = True,
        onclick: str | None = None,
    ) -> None:
        self.page = page
        self.label = label
        self.href = href
        self.enabled = enabled
        self.onclick = onclick

    def is_visible(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return self.enabled

    def inner_text(self) -> str:
        return self.label

    def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self.href
        if name == "onclick":
            return self.onclick
        return None

    def click(self) -> None:
        self.page.advance()


class FakeBrokenTextLocatorItem(FakeLocatorItem):
    def inner_text(self) -> str:
        raise RuntimeError("Node is not an HTMLElement")


class FakeLocatorCollection:
    def __init__(self, items: list[FakeLocatorItem]) -> None:
        self.items = items

    @property
    def first(self) -> FakeLocatorItem:
        return self.items[0]

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


class FakeBodyLocator:
    def __init__(self, text: str) -> None:
        self.text = text

    def inner_text(self, timeout: int | None = None) -> str:  # noqa: ARG002
        return self.text


class FakeInteractivePage:
    def __init__(self) -> None:
        self._url = "https://careers.example.com/jobs"
        self._html = "<main><p>Jobs</p></main>"
        self.interactive_items = [
            {
                "aria": "View job: Support Analyst",
                "href": "/careers/job/123",
                "text": "Support Analyst\nCALGARY, Alberta, Canada\nTechnology\nPosted 12 days ago",
                "context": "Support Analyst CALGARY, Alberta, Canada Technology Posted 12 days ago",
            }
        ]

    @property
    def url(self) -> str:
        return self._url

    def content(self) -> str:
        return self._html

    def locator(self, selector: str):
        if selector == "button, a, [role='button']":
            return FakeLocatorCollection([])
        if selector == "body":
            return FakeBodyLocator("Jobs")
        return FakeLocatorCollection([])

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def evaluate(self, _script: str):
        return self.interactive_items


class FakeNavigationPage:
    def __init__(self) -> None:
        self._url = "https://www.example.com/careers"
        self.visited: list[str] = []
        self.candidates = [
            {
                "text": "Search open roles",
                "aria": "Search open roles",
                "href": "/careers/jobsearch",
            }
        ]

    @property
    def url(self) -> str:
        return self._url

    def evaluate(self, _script: str):
        return self.candidates

    def goto(self, url: str, wait_until: str = "load") -> None:  # noqa: ARG002
        self._url = url
        self.visited.append(url)

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None


class FakeButtonNavigationPage(FakeNavigationPage):
    def __init__(self) -> None:
        super().__init__()
        self.candidates = [
            {
                "text": "FIND JOBS",
                "aria": "Find Jobs",
                "href": "",
            }
        ]
        self._body_text = "Search for Job title, keyword, skill"

    def locator(self, selector: str):
        if selector == "body":
            return FakeBodyLocator(self._body_text)
        if selector == "button, a, [role='button']":
            return FakeLocatorCollection([FakeLocatorItem(self, "FIND JOBS")])
        return FakeLocatorCollection([])

    def advance(self) -> None:
        self._url = "https://www.example.com/careers/search-results"
        self._body_text = "1170 Jobs Sort by Most relevant Software Developer"


class FakeExternalNavigationPage(FakeNavigationPage):
    def __init__(self) -> None:
        super().__init__()
        self.candidates = [
            {
                "text": "Search opportunities",
                "aria": "Search opportunities",
                "href": "https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting",
            }
        ]


class FakeJavascriptNavigationPage(FakeNavigationPage):
    def __init__(self) -> None:
        super().__init__()
        self.candidates = [
            {
                "text": "Search careers",
                "aria": "Search careers",
                "href": "javascript:void(0)",
            },
            {
                "text": "Search opportunities",
                "aria": "Search opportunities",
                "href": "/careers/jobsearch",
            },
        ]


class FakeBrokenButtonNavigationPage(FakeButtonNavigationPage):
    def locator(self, selector: str):
        if selector == "body":
            return FakeBodyLocator(self._body_text)
        if selector == "button, a, [role='button']":
            return FakeLocatorCollection(
                [
                    FakeBrokenTextLocatorItem(self, "Broken"),
                    FakeLocatorItem(self, "FIND JOBS"),
                ]
            )
        return FakeLocatorCollection([])


class FakeResultsAlreadyVisibleNavigationPage(FakeButtonNavigationPage):
    def __init__(self) -> None:
        super().__init__()
        self._url = "https://jobs.bmo.com/ca/en/search-results"
        self._body_text = "1-10 of 667 results Sort by Relevance Software Developer"
        self.visited: list[str] = []

    def goto(self, url: str, wait_until: str = "load") -> None:  # noqa: ARG002
        self._url = url
        self.visited.append(url)


class FakeSearchInput(FakeLocatorItem):
    def __init__(self, page) -> None:
        super().__init__(page, "")

    def fill(self, value: str) -> None:
        self.page.search_terms.append(value)

    def press(self, key: str) -> None:
        self.page.pressed_keys.append(key)


class FakeSearchPage:
    def __init__(self) -> None:
        self._url = "https://careers.example.com/search-results"
        self.search_terms: list[str] = []
        self.pressed_keys: list[str] = []
        self.search_input = FakeSearchInput(self)

    @property
    def url(self) -> str:
        return self._url

    def locator(self, selector: str):
        if selector == "body":
            return FakeBodyLocator("25 jobs found in Canada")
        if selector == "input[type='search']":
            return FakeLocatorCollection([self.search_input])
        return FakeLocatorCollection([])

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def evaluate(self, _script: str):
        return 0


class FakeBmoVisiblePage:
    def __init__(self) -> None:
        self._url = "https://jobs.bmo.com/ca/en/search-results"
        self._html = """
        <main>
          <a
            data-ph-at-id="job-link"
            data-ph-at-job-title-text="Software Developer"
            href="https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000290EXTERNALENCA/Software-Developer"
          >Software Developer</a>
          <a
            data-ph-at-id="job-link"
            data-ph-at-job-title-text="Senior Premier Relationship Manager"
            href="https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260010172EXTERNALENUS/Senior-Premier-Relationship-Manager"
          >Senior Premier Relationship Manager</a>
        </main>
        """
        self.visible_bmo_rows = [
            {
                "title": "Software Developer",
                "href": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000290EXTERNALENCA/Software-Developer",
                "description": "Software Developer Toronto, ON M8X 1C4, Canada Category Technology",
            }
        ]
        self.bmo_evidence = {
            "activeCanadaChip": True,
            "countryFacetChecked": False,
            "visibleJobLinkCount": 10,
            "allVisibleEnca": True,
            "anyVisibleEnus": False,
            "sampleHrefs": [
                "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000290EXTERNALENCA/Software-Developer"
            ],
        }

    @property
    def url(self) -> str:
        return self._url

    def content(self) -> str:
        return self._html

    def locator(self, selector: str):
        if selector == "button, a, [role='button']":
            return FakeLocatorCollection([])
        if selector == "body":
            return FakeBodyLocator("BMO jobs")
        return FakeLocatorCollection([])

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def evaluate(self, script: str):
        if 'view job:' in script.lower():
            return []
        if 'activeCanadaChip' in script:
            return self.bmo_evidence
        if 'data-ph-at-id="job-link"' in script:
            return self.visible_bmo_rows
        return []


class FakeCheckboxLocatorItem(FakeLocatorItem):
    def __init__(self, page, label: str) -> None:
        super().__init__(page, label)
        self.checked = False

    def is_checked(self) -> bool:
        return self.checked

    def check(self, force: bool = False) -> None:  # noqa: ARG002
        self.checked = True
        self.page._url = "https://www.ibm.com/careers/search?field_keyword_05[0]=Canada"


class FakeIbmModalPage:
    def __init__(self) -> None:
        self._url = "https://www.ibm.com/careers/search"
        self.cookie = FakeLocatorItem(self, "Accept all")
        self.language = FakeLocatorItem(self, "Annuler")
        self.location = FakeLocatorItem(self, "Location")
        self.canada = FakeCheckboxLocatorItem(self, "Canada")

    @property
    def url(self) -> str:
        return self._url

    def locator(self, selector: str):
        mapping = {
            "#truste-consent-button": [self.cookie],
            ".geo-btn-secondary-cancel": [self.language],
            "button:has-text('Annuler')": [self.language],
            ".geo-modal-close-icon": [],
            "button:has-text('Location')": [self.location],
            "input[aria-label='Canada']": [self.canada],
            "label:has-text('Canada')": [],
            "text=Canada (102)": [],
        }
        return FakeLocatorCollection(mapping.get(selector, []))

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def advance(self) -> None:
        return None


class FakeNttCheckboxLocatorItem(FakeCheckboxLocatorItem):
    def check(self, force: bool = False) -> None:  # noqa: ARG002
        self.checked = True
        self.page.filtered = True


class FakeNttFilterPage:
    def __init__(self) -> None:
        self._url = "https://careers.services.global.ntt/global/en/search-results"
        self.country_button = FakeLocatorItem(self, "Country")
        self.canada = FakeNttCheckboxLocatorItem(self, "Canada")
        self.filtered = False

    @property
    def url(self) -> str:
        return self._url

    def locator(self, selector: str):
        mapping = {
            "button:has-text('Country')": [self.country_button],
            "input[name^='country_phs_'][aria-label*='Canada' i]": [self.canada],
            "input[type='checkbox'][aria-label*='Canada' i]": [self.canada],
        }
        return FakeLocatorCollection(mapping.get(selector, []))

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def advance(self) -> None:
        return None

    def evaluate(self, script: str):
        if 'a.au-target[href*="/job/"]' in script:
            return 3 if self.filtered else 0
        return []


class FakeDenseIbmPaginationPage:
    def __init__(self, urls: list[str], html_pages: list[str]) -> None:
        self.urls = urls
        self.html_pages = html_pages
        self.index = 0
        self.controls = [FakeLocatorItem(self, f"Filter {index}") for index in range(80)]
        self.next_item = FakeMultiPageLocatorItem(self, "next", enabled=True)
        self.controls.append(self.next_item)

    @property
    def url(self) -> str:
        return self.urls[self.index]

    def content(self) -> str:
        return self.html_pages[self.index]

    def locator(self, selector: str):
        if selector == "[aria-label='Next']":
            if self.index < len(self.html_pages) - 1:
                return FakeLocatorCollection([self.next_item])
            return FakeLocatorCollection([])
        if selector == "button, a, [role='button']":
            if self.index < len(self.html_pages) - 1:
                return FakeLocatorCollection(self.controls)
            return FakeLocatorCollection(self.controls[:-1])
        if selector == "body":
            return FakeBodyLocator("IBM careers results")
        return FakeLocatorCollection([])

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def advance(self) -> None:
        if self.index < len(self.html_pages) - 1:
            self.index += 1


class FakeMultiPageLocatorItem(FakeLocatorItem):
    def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self.href
        if name == "aria-label":
            return self.label
        return None


class FakeMultiPageWorkday:
    def __init__(self, urls: list[str], html_pages: list[str]) -> None:
        self.urls = urls
        self.html_pages = html_pages
        self.index = 0

    @property
    def url(self) -> str:
        return self.urls[self.index]

    def content(self) -> str:
        return self.html_pages[self.index]

    def locator(self, selector: str):
        if selector == "button, a, [role='button']":
            if self.index < len(self.html_pages) - 1:
                return FakeLocatorCollection(
                    [FakeMultiPageLocatorItem(self, "next", enabled=True)]
                )
            return FakeLocatorCollection(
                [FakeMultiPageLocatorItem(self, "next", enabled=False)]
            )
        if selector == "body":
            return FakeBodyLocator("TD Workday jobs")
        return FakeLocatorCollection([])

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def advance(self) -> None:
        if self.index < len(self.html_pages) - 1:
            self.index += 1


class FakeNoNewJobsPage(FakeMultiPageWorkday):
    def advance(self) -> None:
        if self.index < len(self.html_pages) - 1:
            self.index += 1


class FakeMultiPageBmoVisible:
    def __init__(self, urls: list[str], rows_by_page: list[list[dict[str, str]]]) -> None:
        self.urls = urls
        self.rows_by_page = rows_by_page
        self.index = 0

    @property
    def url(self) -> str:
        return self.urls[self.index]

    def content(self) -> str:
        return "<main>BMO visible jobs</main>"

    def locator(self, selector: str):
        if selector == "button, a, [role='button']":
            if self.index < len(self.rows_by_page) - 1:
                return FakeLocatorCollection(
                    [FakeMultiPageLocatorItem(self, "next", enabled=True)]
                )
            return FakeLocatorCollection(
                [FakeMultiPageLocatorItem(self, "next", enabled=False)]
            )
        if selector == "body":
            return FakeBodyLocator("1-10 of 667 results Sort by Relevance")
        return FakeLocatorCollection([])

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def advance(self) -> None:
        if self.index < len(self.rows_by_page) - 1:
            self.index += 1

    def evaluate(self, script: str):
        if "activeCanadaChip" in script:
            return {
                "activeCanadaChip": True,
                "countryFacetChecked": False,
                "visibleJobLinkCount": len(self.rows_by_page[self.index]),
                "allVisibleEnca": True,
                "anyVisibleEnus": False,
                "sampleHrefs": [row["href"] for row in self.rows_by_page[self.index][:3]],
            }
        if 'data-ph-at-id="job-link"' in script:
            return self.rows_by_page[self.index]
        if "view job:" in script.lower():
            return []
        return []


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
    assert all("match_score" not in job for job in jobs)
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
    assert all("match_score" not in job for job in jobs)


def test_extract_visible_job_cards_uses_interactive_job_cards() -> None:
    page = FakeInteractivePage()

    jobs = extract_visible_job_cards(
        page,
        company_name="Example Co",
        source_name="company-careers",
        source_mode="browser_allowed",
    )

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Support Analyst"
    assert jobs[0]["job_url"] == "https://careers.example.com/careers/job/123"
    assert "match_score" not in jobs[0]


def test_detect_bmo_canada_page_evidence_confirms_active_canada_results() -> None:
    page = FakeBmoVisiblePage()

    evidence = detect_bmo_canada_page_evidence(page)

    assert evidence is not None
    assert evidence["confirmed"] is True
    assert evidence["method"] == "page_evidence"


def test_extract_visible_job_cards_prefers_visible_bmo_rows_over_hidden_us_dom_links() -> None:
    page = FakeBmoVisiblePage()

    jobs = extract_visible_job_cards(
        page,
        company_name="BMO",
        source_name="company-careers",
        source_mode="browser_allowed",
        max_pages=1,
    )

    assert [job["job_url"] for job in jobs] == [
        "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000290EXTERNALENCA/Software-Developer"
    ]


def test_extract_visible_job_cards_paginates_until_disabled_or_max_pages() -> None:
    page1 = """
    <main>
      <article>
        <a href="/en-US/TD_Bank_Careers/job/Toronto/Lead-Platform-Engineer_R_1491997">
          Lead Platform Engineer, TD Securities
        </a>
        <p>Toronto, Ontario</p>
      </article>
      <article>
        <a href="/en-US/TD_Bank_Careers/job/Toronto/IT-Support-Analyst_R_1489302">
          IT Support Analyst, ION / MarketView Trading
        </a>
        <p>Toronto, Ontario</p>
      </article>
    </main>
    """
    page2 = """
    <main>
      <article>
        <a href="/en-US/TD_Bank_Careers/job/Toronto/Software-Engineer-II_R_1486443">
          Software Engineer II, Salesforce
        </a>
        <p>Toronto, Ontario</p>
      </article>
      <article>
        <a href="/en-US/TD_Bank_Careers/job/Toronto/Sr-IT-Support-Analyst_R_1489301">
          Sr IT Support Analyst, ION / MarketView Trading
        </a>
        <p>Toronto, Ontario</p>
      </article>
    </main>
    """
    page3 = """
    <main>
      <article>
        <a href="/en-US/TD_Bank_Careers/job/Toronto/Java-Engineer_R_1489761">
          Java Engineer, TD Securities
        </a>
        <p>Toronto, Ontario</p>
      </article>
    </main>
    """
    page = FakeMultiPageWorkday(
        urls=[
            "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=ca",
            "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?page=2&locationCountry=ca",
            "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?page=3&locationCountry=ca",
        ],
        html_pages=[page1, page2, page3],
    )

    jobs, diagnostics = extract_visible_job_cards_with_diagnostics(
        page,
        company_name="TD",
        source_name="workday",
        source_mode="human_in_loop",
        max_cards=60,
        max_pages=3,
    )

    titles = {job["title"] for job in jobs}

    assert "Lead Platform Engineer, TD Securities" in titles
    assert "IT Support Analyst, ION / MarketView Trading" in titles
    assert "Software Engineer II, Salesforce" in titles
    assert "Sr IT Support Analyst, ION / MarketView Trading" in titles
    assert diagnostics.pagination_detected is True
    assert diagnostics.pages_visited == [
        "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=ca",
        "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?page=2&locationCountry=ca",
        "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?page=3&locationCountry=ca",
    ]
    assert diagnostics.pagination_stop_reason == "max_pages_reached"


def test_extract_visible_job_cards_stops_when_no_new_job_urls_appear() -> None:
    repeated_page = """
    <main>
      <article>
        <a href="/en-US/TD_Bank_Careers/job/Toronto/Lead-Platform-Engineer_R_1491997">
          Lead Platform Engineer, TD Securities
        </a>
        <p>Toronto, Ontario</p>
      </article>
    </main>
    """
    page = FakeMultiPageWorkday(
        urls=[
            "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=ca",
            "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?page=2&locationCountry=ca",
            "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?page=3&locationCountry=ca",
        ],
        html_pages=[repeated_page, repeated_page, repeated_page],
    )

    jobs, diagnostics = extract_visible_job_cards_with_diagnostics(
        page,
        company_name="TD",
        source_name="workday",
        source_mode="human_in_loop",
        max_cards=60,
        max_pages=10,
    )

    assert len(jobs) == 1
    assert diagnostics.pagination_detected is True
    assert diagnostics.pagination_stop_reason == "no_new_job_urls"
    assert diagnostics.pages_visited == [
        "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?locationCountry=ca",
        "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?page=2&locationCountry=ca",
    ]


def test_extract_visible_job_cards_does_not_loop_forever_on_static_next_page() -> None:
    page1 = """
    <main>
      <article>
        <a href="/jobs/1">Lead Platform Engineer, TD Securities</a>
        <p>Toronto, Ontario</p>
      </article>
    </main>
    """
    page = FakeMultiPageWorkday(
        urls=[
            "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs",
            "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/jobs?page=2",
        ],
        html_pages=[page1, page1],
    )

    _, diagnostics = extract_visible_job_cards_with_diagnostics(
        page,
        company_name="TD",
        source_name="workday",
        source_mode="human_in_loop",
        max_cards=40,
        max_pages=10,
    )

    assert diagnostics.pagination_stop_reason == "no_new_job_urls"
    assert len(diagnostics.pages_visited) == 2


def test_extract_visible_job_cards_handles_ibm_dense_pagination_until_max_pages() -> None:
    page1 = f"<main>{_ibm_job_article('92913')}{_ibm_job_article('113691')}</main>"
    page2 = f"<main>{_ibm_job_article('115116')}{_ibm_job_article('118746')}</main>"
    page3 = f"<main>{_ibm_job_article('109784')}{_ibm_job_article('119355')}</main>"
    page = FakeDenseIbmPaginationPage(
        urls=[
            "https://www.ibm.com/careers/search?field_keyword_05[0]=Canada",
            "https://www.ibm.com/careers/search?field_keyword_05[0]=Canada&p=2",
            "https://www.ibm.com/careers/search?field_keyword_05[0]=Canada&p=3",
        ],
        html_pages=[page1, page2, page3],
    )

    jobs, diagnostics = extract_visible_job_cards_with_diagnostics(
        page,
        company_name="IBM Consulting",
        source_name="IBM Consulting",
        source_mode="browser_allowed",
        max_cards=60,
        max_pages=3,
    )

    assert len(jobs) == 6
    assert diagnostics.pagination_detected is True
    assert diagnostics.pagination_stop_reason == "max_pages_reached"
    assert diagnostics.jobs_extracted_per_page == [2, 2, 2]


def test_extract_visible_job_cards_handles_ibm_dense_pagination_no_new_job_ids() -> None:
    repeated_page = f"<main>{_ibm_job_article('92913')}</main>"
    page = FakeDenseIbmPaginationPage(
        urls=[
            "https://www.ibm.com/careers/search?field_keyword_05[0]=Canada",
            "https://www.ibm.com/careers/search?field_keyword_05[0]=Canada&p=2",
        ],
        html_pages=[repeated_page, repeated_page],
    )

    jobs, diagnostics = extract_visible_job_cards_with_diagnostics(
        page,
        company_name="IBM Consulting",
        source_name="IBM Consulting",
        source_mode="browser_allowed",
        max_cards=60,
        max_pages=10,
    )

    assert len(jobs) == 1
    assert diagnostics.pagination_detected is True
    assert diagnostics.pagination_stop_reason == "no_new_job_urls"


class FakeCanadaLifePaginationPage:
    def __init__(self, urls: list[str], html_pages: list[str]) -> None:
        self.urls = urls
        self.html_pages = html_pages
        self.index = 0
        self.next_item = FakeMultiPageLocatorItem(self, "Page 2", "/search?startrow=25")

    @property
    def url(self) -> str:
        return self.urls[self.index]

    def content(self) -> str:
        return self.html_pages[self.index]

    def locator(self, selector: str):
        if selector == "li.active + li a[title^='Page ']":
            if self.index < len(self.html_pages) - 1:
                return FakeLocatorCollection([self.next_item])
            return FakeLocatorCollection([])
        if selector == "button, a, [role='button']":
            return FakeLocatorCollection([])
        if selector == "body":
            return FakeBodyLocator("Canada Life jobs")
        return FakeLocatorCollection([])

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def advance(self) -> None:
        if self.index < len(self.html_pages) - 1:
            self.index += 1


class FakeNjoynJavascriptPaginationPage:
    def __init__(self, urls: list[str], html_pages: list[str]) -> None:
        self.urls = urls
        self.html_pages = html_pages
        self.index = 0

    @property
    def url(self) -> str:
        return self.urls[self.index]

    def content(self) -> str:
        return self.html_pages[self.index]

    def locator(self, selector: str):
        if selector == "button, a, [role='button']":
            if self.index < len(self.html_pages) - 1:
                return FakeLocatorCollection(
                    [FakeLocatorItem(self, "NEXT", "javascript:gotopage(2)")]
                )
            return FakeLocatorCollection([])
        if selector == "body":
            return FakeBodyLocator("CGI jobs")
        return FakeLocatorCollection([])

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def advance(self) -> None:
        if self.index < len(self.html_pages) - 1:
            self.index += 1


def test_extract_visible_job_cards_handles_canada_life_numeric_pagination() -> None:
    page1 = """
    <main>
      <article>
        <a href="/job/London-Solutions-Architect-ON/1404013933/">Solutions Architect</a>
      </article>
    </main>
    """
    page2 = """
    <main>
      <article>
        <a href="/job/London-Senior-Devops-Engineering-Specialist-ON/1400494133/">
          Senior Devops Engineering Specialist
        </a>
      </article>
    </main>
    """
    page = FakeCanadaLifePaginationPage(
        urls=[
            "https://jobs.canadalife.com/search/?optionsFacetsDD_country=CA",
            "https://jobs.canadalife.com/search/?optionsFacetsDD_country=CA&startrow=25",
        ],
        html_pages=[page1, page2],
    )

    jobs, diagnostics = extract_visible_job_cards_with_diagnostics(
        page,
        company_name="Canada Life",
        source_name="Canada Life",
        source_mode="browser_allowed",
        max_cards=20,
        max_pages=2,
    )

    titles = {job["title"] for job in jobs}

    assert titles == {"Solutions Architect", "Senior Devops Engineering Specialist"}
    assert diagnostics.pagination_detected is True
    assert diagnostics.jobs_extracted_per_page == [1, 1]


def test_extract_visible_job_cards_handles_njoyn_javascript_next_pagination() -> None:
    page1 = """
    <main>
      <table>
        <tr>
          <th>Position ID</th><th>Title</th><th>Category</th><th>City</th><th>Country</th>
        </tr>
        <tr>
          <td><a href="xweb.asp?Page=JobDetails&Jobid=J0426-1288&BRID=1291363">J0426-1288</a></td>
          <td>Control-M System Administrator</td>
          <td>ERP/CRM/Tools</td>
          <td>Toronto</td>
          <td>Canada</td>
        </tr>
      </table>
    </main>
    """
    page2 = """
    <main>
      <table>
        <tr>
          <th>Position ID</th><th>Title</th><th>Category</th><th>City</th><th>Country</th>
        </tr>
        <tr>
          <td><a href="xweb.asp?Page=JobDetails&Jobid=J0626-0759&BRID=1307869">J0626-0759</a></td>
          <td>AWS Cloud Engineer</td>
          <td>Infrastructure/Cloud</td>
          <td>Montreal</td>
          <td>Canada</td>
        </tr>
      </table>
    </main>
    """
    page = FakeNjoynJavascriptPaginationPage(
        urls=[
            "https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting&CLID=21001&CountryID=CA&lang=1",
            "https://cgi.njoyn.com/CORP/xweb/xweb.asp?NTKN=c&clid=21001&Page=joblisting",
        ],
        html_pages=[page1, page2],
    )

    jobs, diagnostics = extract_visible_job_cards_with_diagnostics(
        page,
        company_name="CGI",
        source_name="CGI",
        source_mode="browser_allowed",
        max_cards=20,
        max_pages=2,
    )

    titles = {job["title"] for job in jobs}

    assert titles == {"Control-M System Administrator", "AWS Cloud Engineer"}
    assert diagnostics.pagination_detected is True
    assert diagnostics.jobs_extracted_per_page == [1, 1]
    assert diagnostics.pagination_stop_reason == "max_pages_reached"


def test_extract_visible_job_cards_uses_visible_bmo_rows_across_pages() -> None:
    page = FakeMultiPageBmoVisible(
        urls=[
            "https://jobs.bmo.com/ca/en/search-results",
            "https://jobs.bmo.com/ca/en/search-results?from=10&s=1",
            "https://jobs.bmo.com/ca/en/search-results?from=20&s=1",
        ],
        rows_by_page=[
            [
                {
                    "title": "Software Developer",
                    "href": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000290EXTERNALENCA/Software-Developer",
                    "description": (
                        "Software Developer Toronto, ON M8X 1C4, Canada "
                        "Category Technology"
                    ),
                },
                {
                    "title": "Cloud Engineer",
                    "href": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000291EXTERNALENCA/Cloud-Engineer",
                    "description": "Cloud Engineer Toronto, ON, Canada Category Technology",
                },
            ],
            [
                {
                    "title": "DevOps Engineer",
                    "href": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000292EXTERNALENCA/DevOps-Engineer",
                    "description": "DevOps Engineer Mississauga, ON, Canada Category Technology",
                },
                {
                    "title": "Systems Administrator",
                    "href": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000293EXTERNALENCA/Systems-Administrator",
                    "description": "Systems Administrator Toronto, ON, Canada Category Technology",
                },
            ],
            [
                {
                    "title": "Cloud Operations Analyst",
                    "href": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000294EXTERNALENCA/Cloud-Operations-Analyst",
                    "description": (
                        "Cloud Operations Analyst Toronto, ON, Canada Category "
                        "Technology"
                    ),
                },
                {
                    "title": "Linux Administrator",
                    "href": "https://jobs.bmo.com/ca/en/job/BOMOGLOBALR260000295EXTERNALENCA/Linux-Administrator",
                    "description": "Linux Administrator Toronto, ON, Canada Category Technology",
                },
            ],
        ],
    )

    jobs, diagnostics = extract_visible_job_cards_with_diagnostics(
        page,
        company_name="BMO",
        source_name="BMO",
        source_mode="browser_allowed",
        max_cards=60,
        max_pages=3,
    )

    assert len(jobs) == 6
    assert diagnostics.pagination_detected is True
    assert diagnostics.pagination_stop_reason == "max_pages_reached"
    assert diagnostics.jobs_extracted_per_page == [2, 2, 2]


def test_extract_jobs_from_html_captures_live_like_ibm_card_and_dedupes_duplicate_job_ids() -> None:
    html = """
    <main>
      <a href="https://www.ibm.com/privacy">Privacy</a>
      <div class="bx--card-group__cards__col" role="region"
           aria-label="Staff Site Reliability Engineer - Confluent Incident
           Management &amp; Reliability">
        <a href="https://careers.ibm.com/en_US/careers/JobDetail?jobId=115116&amp;source=WEB_Search_NA"
           class="bx--card-group__card">
          <div class="bx--card__content">
            <div class="bx--card__eyebrow">Infrastructure &amp; Technology</div>
            <div class="bx--card__heading">
              Staff Site Reliability Engineer - Confluent Incident Management &amp; Reliability
            </div>
            <div class="ibm--card__copy__inner">Professional<br>Multiple Cities</div>
          </div>
        </a>
      </div>
      <div class="bx--card-group__cards__col" role="region"
           aria-label="Staff Site Reliability Engineer - Confluent Incident
           Management &amp; Reliability">
        <a href="https://careers.ibm.com/en_US/careers/JobDetail?jobId=115116&amp;source=WEB_Search_NA"
           class="bx--card-group__card">
          <div class="bx--card__content">
            <div class="bx--card__eyebrow">Infrastructure &amp; Technology</div>
            <div class="bx--card__heading">
              Staff Site Reliability Engineer - Confluent Incident Management &amp; Reliability
            </div>
            <div class="ibm--card__copy__inner">Professional<br>Multiple Cities</div>
          </div>
        </a>
      </div>
      <div class="bx--card-group__cards__col" role="region" aria-label="Careers Home">
        <a href="https://www.ibm.com/careers/search" class="bx--card-group__card">
          <div class="bx--card__content">
            <div class="bx--card__heading">Careers Home</div>
          </div>
        </a>
      </div>
    </main>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="IBM Consulting",
        source_name="IBM Consulting",
        source_mode="browser_allowed",
        base_url="https://www.ibm.com/careers/search?field_keyword_05[0]=Canada&p=2",
        max_cards=50,
    )

    assert len(jobs) == 1
    assert jobs[0]["job_url"] == (
        "https://careers.ibm.com/en_US/careers/JobDetail?jobId=115116&source=WEB_Search_NA"
    )
    assert "Staff Site Reliability Engineer" in jobs[0]["title"]


def test_search_with_location_term_does_not_use_role_or_skill_terms() -> None:
    page = FakeSearchPage()

    assert search_with_location_term(page, "cloud devops platform") is None
    assert page.search_terms == []


def test_search_with_location_term_uses_single_location_scope_term() -> None:
    page = FakeSearchPage()

    query = search_with_location_term(page, "Toronto")

    assert query == "Toronto"
    assert page.search_terms == ["Toronto"]
    assert page.pressed_keys == ["Enter"]


def test_ibm_helpers_dismiss_cookie_and_language_modal_and_apply_canada_filter() -> None:
    page = FakeIbmModalPage()

    cookie_action = dismiss_cookie_banner(page)
    language_action = dismiss_ibm_language_prompt(page)
    filter_action = apply_ibm_canada_filter(page, ("Canada",))

    assert is_ibm_careers_search_url("https://www.ibm.com/careers/search") is True
    assert cookie_action == "#truste-consent-button"
    assert language_action in {
        ".geo-btn-secondary-cancel",
        "button:has-text('Annuler')",
    }
    assert filter_action == "Canada (IBM location facet)"
    assert "field_keyword_05[0]=Canada" in page.url


def test_ibm_helpers_return_none_safely_when_page_is_not_ibm() -> None:
    page = FakeSearchPage()

    assert dismiss_ibm_language_prompt(page) is None
    assert apply_ibm_canada_filter(page, ("Canada",)) is None


def test_ntt_helper_applies_canada_country_facet() -> None:
    page = FakeNttFilterPage()

    filter_action = apply_ntt_canada_filter(page, ("Canada",))

    assert filter_action == "Canada (NTT country facet)"
    assert page.canada.is_checked() is True


def test_has_interactive_job_cards_detects_live_view_job_elements() -> None:
    page = FakeInteractivePage()

    assert has_interactive_job_cards(page) is True


def test_navigate_to_job_search_page_uses_on_site_search_link() -> None:
    page = FakeNavigationPage()

    resolved = navigate_to_job_search_page(page)

    assert resolved == "https://www.example.com/careers/jobsearch"
    assert page.url == "https://www.example.com/careers/jobsearch"
    assert page.visited == ["https://www.example.com/careers/jobsearch"]


def test_navigate_to_job_search_page_can_click_button_navigation() -> None:
    page = FakeButtonNavigationPage()

    resolved = navigate_to_job_search_page(page)

    assert resolved == "https://www.example.com/careers/search-results"
    assert page.url == "https://www.example.com/careers/search-results"


def test_navigate_to_job_search_page_skips_find_jobs_when_results_already_visible() -> None:
    page = FakeResultsAlreadyVisibleNavigationPage()

    resolved = navigate_to_job_search_page(page)

    assert resolved is None
    assert page.url == "https://jobs.bmo.com/ca/en/search-results"
    assert page.visited == []


def test_navigate_to_job_search_page_allows_public_external_job_boards() -> None:
    page = FakeExternalNavigationPage()

    resolved = navigate_to_job_search_page(page)

    assert resolved == "https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting"
    assert page.url == "https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting"


def test_navigate_to_job_search_page_skips_javascript_links() -> None:
    page = FakeJavascriptNavigationPage()

    resolved = navigate_to_job_search_page(page)

    assert resolved == "https://www.example.com/careers/jobsearch"
    assert page.visited == ["https://www.example.com/careers/jobsearch"]


def test_navigate_to_job_search_page_skips_non_html_button_nodes() -> None:
    page = FakeBrokenButtonNavigationPage()

    resolved = navigate_to_job_search_page(page)

    assert resolved == "https://www.example.com/careers/search-results"
    assert page.url == "https://www.example.com/careers/search-results"


def test_extract_jobs_from_html_skips_empty_state_job_board_shell() -> None:
    html = """
    <main>
      <h1>Jobs</h1>
      <button>Manage</button>
      <button>View all jobs</button>
      <p>0 jobs</p>
      <p>We didn't find any relevant jobs</p>
      <p>Try modifying search/filters</p>
      <p>Cloud DevOps Platform Toronto, Ontario, Canada Remote</p>
    </main>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="Example Co",
        source_name="company-careers",
        source_mode="browser_allowed",
        base_url="https://careers.example.com",
    )

    assert jobs == []


def test_extract_jobs_from_html_skips_view_job_details_shell_links() -> None:
    html = """
    <main>
      <article>
        <a href="https://cgi.njoyn.com/CORP/xweb/XWeb.asp?NTKN=c&Page=JobDetails&Jobid=J0626-0210">
          View Job Details
        </a>
      </article>
    </main>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="CGI",
        source_name="CGI",
        source_mode="browser_allowed",
        base_url="https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting",
    )

    assert jobs == []


def test_extract_jobs_from_html_skips_career_marketing_links() -> None:
    html = """
    <main>
      <section>
        <a href="/careers/explore-careers/area-of-interest/software-engineering-careers">
          Software engineering
        </a>
        <p>Create software that will power change and empower people.</p>
      </section>
      <section>
        <a href="/careers/explore-careers/area-of-interest/customer-care-careers">
          Customer care
        </a>
        <p>Use your passion for problem-solving to support important clients.</p>
      </section>
    </main>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="Example Co",
        source_name="company-careers",
        source_mode="browser_allowed",
        base_url="https://careers.example.com",
    )

    assert jobs == []


def test_extract_jobs_from_html_normalizes_bmo_style_titles_and_drops_apply_rows() -> None:
    html = """
    <main>
      <li>
        <a
          data-ph-at-id="suggested-data-link"
          data-ph-at-job-title-text="Senior Cloud Platform Engineer"
          data-ph-at-job-location-text="Toronto, ON M8X 1C4, Canada"
          href="https://jobs.example.com/job/123"
        >
          Job title Senior Cloud Platform Engineer location Toronto, ON, Canada category Technology
        </a>
      </li>
      <div>
        <a href="https://jobs.example.com/job/123/apply">
          Apply Now Senior Cloud Platform Engineer
        </a>
      </div>
      <div>
        <a href="https://jobs.example.com/search-results?keywords=cloud">
          Showing Search results for "cloud"
        </a>
      </div>
    </main>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="Example Co",
        source_name="company-careers",
        source_mode="browser_allowed",
        base_url="https://jobs.example.com/search-results",
    )

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Cloud Platform Engineer"
    assert jobs[0]["location"] == "Toronto, ON M8X 1C4, Canada"
    assert jobs[0]["job_url"] == "https://jobs.example.com/job/123"


def test_extract_jobs_from_html_drops_browse_opportunities_ctas() -> None:
    html = """
    <main>
      <a href="https://example.wd3.myworkdayjobs.com/search?Country=ca">
        Browse opportunities
        <span>related to supporting communities</span>
      </a>
    </main>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="Example Bank",
        source_name="workday",
        source_mode="human_in_loop",
        base_url="https://example.com/careers",
    )

    assert jobs == []


def test_extract_jobs_from_html_rejects_javascript_pseudo_links() -> None:
    html = """
    <main>
      <article>
        <a href="javascript:void(0)">Cloud Engineer</a>
        <p>Toronto, Ontario, Canada</p>
      </article>
    </main>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="Example Bank",
        source_name="company-careers",
        source_mode="browser_allowed",
        base_url="https://example.com/careers",
    )

    assert jobs == []


def test_extract_jobs_from_html_supports_accenture_jobsearch_cards() -> None:
    html = """
    <div class="rad-filters-vertical__job-card">
      <div class="rad-filters-vertical__job-card-header">
        <h3 class="rad-filters-vertical__job-card-title">
          Cloud Support Engineer
        </h3>
      </div>
      <div class="rad-filters-vertical__job-card-content">
        <span class="rad-filters-vertical__job-card-details-location">Toronto, Ontario</span>
        <a href="/ca-en/careers/jobdetails?id=R00331889_en&title=Cloud-Support-Engineer">
          Read full job description
        </a>
      </div>
    </div>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="Accenture",
        source_name="Accenture",
        source_mode="browser_allowed",
        base_url="https://www.accenture.com/ca-en/careers/jobsearch",
    )

    assert any(job["title"] == "Cloud Support Engineer" for job in jobs)
    assert any(
        job["job_url"]
        == "https://www.accenture.com/ca-en/careers/jobdetails?id=R00331889_en&title=Cloud-Support-Engineer"
        for job in jobs
    )


def test_extract_jobs_from_html_supports_njoyn_tables_without_page_shell_noise() -> None:
    html = """
    <main>
      <table>
        <tr>
          <th>Position ID</th><th>Title</th><th>Category</th><th>City</th><th>Country</th>
        </tr>
        <tr>
          <td><a href="xweb.asp?Page=JobDetails&Jobid=J0526-0865">J0526-0865</a></td>
          <td>Application Support Consultant</td>
          <td>Service Desk / End User Services</td>
          <td>St. John's</td>
          <td>Canada</td>
        </tr>
        <tr>
          <td><a href="xweb.asp?Page=JobDetails&Jobid=J0626-0071">J0626-0071</a></td>
          <td>Business Analyst</td>
          <td>Business Analysis</td>
          <td>Vancouver</td>
          <td>Canada</td>
        </tr>
        <tr>
          <td><a href="xweb.asp?Page=JobDetails&Jobid=J0626-0173">J0626-0173</a></td>
          <td>Adjoint(e) administratif(ve)</td>
          <td>Administration</td>
          <td>Quebec</td>
          <td>Canada</td>
        </tr>
      </table>
    </main>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="CGI",
        source_name="CGI",
        source_mode="browser_allowed",
        base_url="https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting",
    )

    titles = {job["title"] for job in jobs}

    assert "Application Support Consultant" in titles
    assert "Business Analyst" in titles
    assert "Adjoint(e) administratif(ve)" in titles
    assert all("JobDetails" in job["job_url"] for job in jobs)


def test_extraction_keeps_infrastructure_and_production_support_before_scoring() -> None:
    html = """
    <main>
      <article>
        <a href="/job/infra-123">Infrastructure Analyst</a>
        <p>Posted yesterday Toronto, Ontario, Canada</p>
      </article>
      <article>
        <a href="/job/prod-456">Production Support Analyst</a>
        <p>Posted yesterday Remote Canada</p>
      </article>
    </main>
    """

    jobs = extract_jobs_from_html(
        html,
        company_name="Example Co",
        source_name="company-careers",
        source_mode="browser_allowed",
        base_url="https://careers.example.com",
    )
    scored_jobs = [score_job(job) for job in jobs]
    titles = {job["title"] for job in jobs}

    assert "Infrastructure Analyst" in titles
    assert "Production Support Analyst" in titles
    assert all(score.match_score > 0 for score in scored_jobs)


def test_is_probable_job_listing_rejects_marketing_and_facet_noise() -> None:
    assert is_probable_job_listing(
        {
            "title": "Helping drive equality for every future",
            "job_url": "https://www.womenofinfluence.ca/2026/04/27/katy-waugh",
            "description": (
                "We know that inclusion fuels innovation and drives better outcomes for everyone."
            ),
        },
        base_url="https://www.scotiabank.com/careers/en/careers.html",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Why work at Desjardins?",
            "job_url": "https://www.desjardins.com/en/careers/working-at-desjardins.html",
            "description": "Benefits that help you succeed and support your growth.",
        },
        base_url="https://www.desjardins.com/en/careers.html",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Hybrid (2671)",
            "job_url": "https://www.ibm.com/careers/search",
            "description": "Hybrid and Remote jobs Hybrid (2671) Remote only (20).",
        },
        base_url="https://www.ibm.com/careers/search",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Living Wage employers",
            "job_url": "https://www.vancity.com/careers/living-wage",
            "description": "We are one of Canada's largest private-sector Living Wage employers.",
        },
        base_url="https://www.vancity.com/careers",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "always-open job posting",
            "job_url": (
                "https://recruiting.ultipro.com/VAN5000VCSCU/JobBoard/"
                "a46cbdaa-ca2c-49b6-8d2b-e0ceaafa0e25/OpportunityDetail"
                "?opportunityId=8fde6fbc-383c-41e5-b89b-aded260bc527"
            ),
            "description": "Expanding opportunities for Indigenous, Black and Transgender people.",
        },
        base_url="https://www.vancity.com/careers",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Demanding more values.",
            "job_url": "https://www.vancity.com/careers/living-wage",
            "description": (
                "Putting people and planet first. We are one of Canada's largest "
                "private-sector Living Wage employers."
            ),
            "location": "Canada",
        },
        base_url="https://www.vancity.com/careers",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "TD Careers",
            "job_url": "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers",
            "description": "Explore opportunities across TD.",
        },
        base_url="https://careers.td.com/",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Technology (42)",
            "job_url": "https://careers.example.com/job-search",
            "description": "Browse technology openings.",
        },
        base_url="https://careers.example.com/job-search",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Filter Results",
            "job_url": "https://careers.intactfc.com/jobs",
            "description": "Filter Results Job Category Locations Remote Hybrid",
        },
        base_url="https://careers.intactfc.com/jobs",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Search Results",
            "job_url": "https://www.ey.com/en_ca/careers/job-search",
            "description": "Search Results for career opportunities.",
        },
        base_url="https://www.ey.com/en_ca/careers/job-search",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "View All Jobs",
            "job_url": "https://careers.example.com/jobs",
            "description": "View all jobs by department and location.",
        },
        base_url="https://careers.example.com/jobs",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Careers Home",
            "job_url": "https://careers.example.com/careers",
            "description": "Careers Home and job search links.",
        },
        base_url="https://careers.example.com/careers",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Careers",
            "job_url": "https://careers.example.com/careers",
            "description": "Learn about our teams, benefits, and locations.",
        },
        base_url="https://careers.example.com/careers",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Filter Results",
            "job_url": "https://careers.example.com/job-search-results",
            "description": "Filter Results by category, location, and employment type.",
        },
        base_url="https://careers.example.com/job-search-results",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Business & Customer Operations 149 available jobs",
            "job_url": "https://careers.manulife.com/global/en/c/business-customer-operations-jobs",
            "description": "Browse business and customer operations jobs.",
        },
        base_url="https://careers.manulife.com/global/en/search-results",
    ) is False


def test_is_probable_job_listing_requires_actionable_identity() -> None:
    assert is_probable_job_listing(
        {
            "title": (
                "Infrastructure & Capital Projects - "
                "Construction Technical Support Coordinator, COM"
            ),
            "description": "Toronto Full-time Expand job details",
            "job_url": None,
        },
        base_url="https://www.accenture.com/ca-en/careers/jobsearch",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Cloud Engineer",
            "job_url": None,
            "external_job_id": "job-123",
            "ats_type": "greenhouse",
            "board_slug": "example",
            "description": "Remote Canada",
        },
        base_url="https://boards.greenhouse.io/example",
    ) is True
    assert is_probable_job_listing(
        {
            "title": "Cloud Engineer",
            "job_url": "https://boards.greenhouse.io/example/careers",
            "external_job_id": "job-123",
            "ats_type": "greenhouse",
            "board_slug": "example",
            "description": "Remote Canada",
        },
        base_url="https://boards.greenhouse.io/example",
    ) is True


def test_is_probable_job_listing_rejects_marketing_support_pages_and_js_links() -> None:
    assert is_probable_job_listing(
        {
            "title": (
                "IBM Cloud platform Access subject matter experts and content "
                "to address questions and issues about IBM Cloud"
            ),
            "job_url": "https://www.ibm.com/products/cloud/support?lnk=flathl",
            "description": "Access subject matter experts and content.",
        },
        base_url="https://www.ibm.com/careers/search",
    ) is False
    assert is_probable_job_listing(
        {
            "title": "Enterprise Operations (415)",
            "job_url": "javascript:void(0)",
            "description": "Enterprise Operations jobs and categories.",
        },
        base_url="https://www.ibm.com/careers/search",
    ) is False


def test_is_probable_job_listing_keeps_real_broad_job_titles_with_real_urls() -> None:
    assert is_probable_job_listing(
        {
            "title": "Infrastructure Analyst",
            "job_url": "https://careers.example.com/jobs/infrastructure-analyst-123",
            "description": "Toronto, Ontario, Canada. Posted today.",
        },
        base_url="https://careers.example.com/jobs",
    ) is True
    assert is_probable_job_listing(
        {
            "title": "Production Support Analyst",
            "job_url": "https://careers.example.com/jobs/production-support-456",
            "description": "Remote Canada. Full-time support role.",
        },
        base_url="https://careers.example.com/jobs",
    ) is True
    assert is_probable_job_listing(
        {
            "title": "Cloud Engineer",
            "job_url": "https://careers.example.com/jobs/cloud-engineer-789",
            "description": "Toronto, Ontario. AWS platform role.",
        },
        base_url="https://careers.example.com/jobs",
    ) is True
