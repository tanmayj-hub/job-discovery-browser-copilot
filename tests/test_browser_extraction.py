from __future__ import annotations

from pathlib import Path

from browser.extraction import (
    extract_jobs_from_html,
    extract_visible_job_cards,
    has_interactive_job_cards,
    navigate_to_job_search_page,
)

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
    assert jobs[0]["match_score"] > 0


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


def test_navigate_to_job_search_page_allows_public_external_job_boards() -> None:
    page = FakeExternalNavigationPage()

    resolved = navigate_to_job_search_page(page)

    assert resolved == "https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting"
    assert page.url == "https://cgi.njoyn.com/CORP/xweb/xweb.asp?page=joblisting"


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

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Application Support Consultant"
    assert jobs[0]["location"] == "St. John's, Canada"
    assert "JobDetails" in jobs[0]["job_url"]
