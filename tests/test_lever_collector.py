from __future__ import annotations

from urllib.error import HTTPError

import collectors.api.lever as lever_module
from collectors.api.lever import collect_lever_jobs, extract_lever_site


def _company(**overrides: object) -> dict[str, object]:
    company = {
        "name": "Example Co",
        "company_name": "Example Co",
        "careers_url": "https://jobs.lever.co/example",
        "website_category": "lever",
        "source_name": "lever",
        "source_mode": "api_allowed",
    }
    company.update(overrides)
    return company


def test_extract_lever_site_from_jobs_url() -> None:
    assert extract_lever_site("https://jobs.lever.co/netflix") == "netflix"


def test_extract_lever_site_from_nested_job_url() -> None:
    assert extract_lever_site("https://jobs.lever.co/example/12345-job-slug") == "example"


def test_extract_lever_site_from_api_url() -> None:
    assert extract_lever_site("https://api.lever.co/v0/postings/example?mode=json") == "example"


def test_collect_lever_jobs_normalizes_payload(monkeypatch) -> None:
    def fake_fetch(url: str, *, timeout: int = 15):  # noqa: ARG001
        return [
            {
                "id": "abc123",
                "text": "Junior DevOps Engineer",
                "hostedUrl": "https://jobs.lever.co/example/abc123",
                "applyUrl": "https://jobs.lever.co/example/apply/abc123",
                "categories": {"location": "Remote Canada"},
                "description": "<p>Build CI/CD pipelines</p>",
                "lists": [
                    {
                        "text": "Requirements",
                        "content": ["<li>Linux</li>", "<li>Python</li>"],
                    }
                ],
                "additional": ["<p>Support rotation</p>"],
                "createdAt": 1_717_203_600_000,
            }
        ]

    monkeypatch.setattr(lever_module, "_fetch_json", fake_fetch)

    result = collect_lever_jobs(_company())

    assert result.status == "success"
    assert result.collector == "lever_api"
    assert result.jobs_discovered == 1
    assert result.jobs[0]["title"] == "Junior DevOps Engineer"
    assert result.jobs[0]["location"] == "Remote Canada"
    assert result.jobs[0]["job_url"] == "https://jobs.lever.co/example/abc123"
    assert result.jobs[0]["apply_url"] == "https://jobs.lever.co/example/apply/abc123"
    assert result.jobs[0]["external_job_id"] == "abc123"
    assert result.jobs[0]["ats_type"] == "lever"
    assert result.jobs[0]["board_slug"] == "example"
    assert "Requirements" in str(result.jobs[0]["description"])
    assert result.jobs[0]["date_posted"] == "2024-06-01T01:00:00+00:00"


def test_collect_lever_jobs_missing_site_returns_invalid_source_config() -> None:
    result = collect_lever_jobs(_company(careers_url="https://careers.example.com"))

    assert result.status == "invalid_source_config"
    assert result.collector == "lever_api"
    assert "Missing Lever site slug" in str(result.error)


def test_collect_lever_jobs_http_error_returns_api_error(monkeypatch) -> None:
    def fake_fetch(url: str, *, timeout: int = 15):  # noqa: ARG001
        raise HTTPError(url, 503, "Service Unavailable", hdrs=None, fp=None)

    monkeypatch.setattr(lever_module, "_fetch_json", fake_fetch)

    result = collect_lever_jobs(_company())

    assert result.status == "api_error"
    assert result.collector == "lever_api"
    assert "Lever API request failed" in str(result.error)
