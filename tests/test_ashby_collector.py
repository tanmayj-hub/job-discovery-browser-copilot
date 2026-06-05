from __future__ import annotations

from urllib.error import HTTPError

import collectors.api.ashby as ashby_module
from collectors.api.ashby import collect_ashby_jobs, extract_ashby_job_board_name


def _company(**overrides: object) -> dict[str, object]:
    company = {
        "name": "Example Co",
        "company_name": "Example Co",
        "careers_url": "https://jobs.ashbyhq.com/example",
        "website_category": "ashby",
        "source_name": "ashby",
        "source_mode": "api_allowed",
    }
    company.update(overrides)
    return company


def test_extract_ashby_job_board_name_from_jobs_url() -> None:
    assert extract_ashby_job_board_name("https://jobs.ashbyhq.com/example") == "example"


def test_extract_ashby_job_board_name_from_nested_jobs_url() -> None:
    assert (
        extract_ashby_job_board_name("https://jobs.ashbyhq.com/example/job/software-engineer")
        == "example"
    )


def test_extract_ashby_job_board_name_from_api_url() -> None:
    assert (
        extract_ashby_job_board_name(
            "https://api.ashbyhq.com/posting-api/job-board/example?includeCompensation=true"
        )
        == "example"
    )


def test_collect_ashby_jobs_normalizes_payload(monkeypatch) -> None:
    def fake_fetch(url: str, *, timeout: int = 15):  # noqa: ARG001
        return {
            "jobs": [
                {
                    "id": "job-123",
                    "title": "Platform Engineer",
                    "jobUrl": "https://jobs.ashbyhq.com/example/job-123",
                    "applyUrl": "https://jobs.ashbyhq.com/example/job-123/apply",
                    "location": {"city": "Toronto", "region": "Ontario", "country": "Canada"},
                    "secondaryLocations": ["Remote Canada"],
                    "descriptionHtml": "<p>Build AWS platforms.</p>",
                    "publishedAt": "2026-06-01T12:00:00Z",
                }
            ]
        }

    monkeypatch.setattr(ashby_module, "_fetch_json", fake_fetch)

    result = collect_ashby_jobs(_company())

    assert result.status == "success"
    assert result.collector == "ashby_api"
    assert result.jobs_discovered == 1
    assert result.jobs[0]["title"] == "Platform Engineer"
    assert result.jobs[0]["location"] == "Toronto, Ontario, Canada | Remote Canada"
    assert result.jobs[0]["job_url"] == "https://jobs.ashbyhq.com/example/job-123"
    assert result.jobs[0]["apply_url"] == "https://jobs.ashbyhq.com/example/job-123/apply"
    assert result.jobs[0]["external_job_id"] == "job-123"
    assert result.jobs[0]["ats_type"] == "ashby"
    assert result.jobs[0]["board_slug"] == "example"
    assert result.jobs[0]["source_mode"] == "api_allowed"
    assert "publishedAt" in result.jobs[0]["raw_payload_json"]


def test_collect_ashby_jobs_missing_board_name_returns_invalid_source_config() -> None:
    result = collect_ashby_jobs(_company(careers_url="https://careers.example.com"))

    assert result.status == "invalid_source_config"
    assert result.collector == "ashby_api"
    assert "Missing Ashby job board name" in str(result.error)


def test_collect_ashby_jobs_http_error_returns_api_error(monkeypatch) -> None:
    def fake_fetch(url: str, *, timeout: int = 15):  # noqa: ARG001
        raise HTTPError(url, 503, "Service Unavailable", hdrs=None, fp=None)

    monkeypatch.setattr(ashby_module, "_fetch_json", fake_fetch)

    result = collect_ashby_jobs(_company())

    assert result.status == "api_error"
    assert result.collector == "ashby_api"
    assert "Ashby API request failed" in str(result.error)
