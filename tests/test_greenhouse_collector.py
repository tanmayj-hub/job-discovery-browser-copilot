from __future__ import annotations

from urllib.error import HTTPError

import collectors.api.greenhouse as greenhouse_module
from collectors.api.greenhouse import collect_greenhouse_jobs, extract_greenhouse_board_token


def _company(**overrides: object) -> dict[str, object]:
    company = {
        "name": "Example Co",
        "company_name": "Example Co",
        "careers_url": "https://boards.greenhouse.io/example",
        "website_category": "greenhouse",
        "source_name": "greenhouse",
        "source_mode": "api_allowed",
    }
    company.update(overrides)
    return company


def test_extract_greenhouse_token_from_boards_url() -> None:
    assert extract_greenhouse_board_token("https://boards.greenhouse.io/stripe") == "stripe"


def test_extract_greenhouse_token_from_job_boards_url() -> None:
    assert extract_greenhouse_board_token("https://job-boards.greenhouse.io/airbnb") == "airbnb"


def test_extract_greenhouse_token_from_api_url() -> None:
    assert (
        extract_greenhouse_board_token(
            "https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true"
        )
        == "example"
    )


def test_collect_greenhouse_jobs_normalizes_payload(monkeypatch) -> None:
    def fake_fetch(url: str, *, timeout: int = 15):  # noqa: ARG001
        return {
            "jobs": [
                {
                    "id": 12345,
                    "title": "Cloud Engineer",
                    "absolute_url": "https://boards.greenhouse.io/example/jobs/12345",
                    "location": {"name": "Toronto, Canada"},
                    "content": "<p>AWS and Terraform support role</p>",
                    "first_published": "2026-06-01T12:00:00Z",
                }
            ]
        }

    monkeypatch.setattr(greenhouse_module, "_fetch_json", fake_fetch)

    result = collect_greenhouse_jobs(_company())

    assert result.status == "success"
    assert result.collector == "greenhouse_api"
    assert result.jobs_discovered == 1
    assert result.jobs[0]["title"] == "Cloud Engineer"
    assert result.jobs[0]["location"] == "Toronto, Canada"
    assert result.jobs[0]["job_url"] == "https://boards.greenhouse.io/example/jobs/12345"
    assert result.jobs[0]["apply_url"] == "https://boards.greenhouse.io/example/jobs/12345"
    assert result.jobs[0]["external_job_id"] == "12345"
    assert result.jobs[0]["ats_type"] == "greenhouse"
    assert result.jobs[0]["board_slug"] == "example"
    assert result.jobs[0]["source_mode"] == "api_allowed"
    assert "first_published" in result.jobs[0]["raw_payload_json"]


def test_collect_greenhouse_jobs_missing_token_returns_invalid_source_config() -> None:
    result = collect_greenhouse_jobs(_company(careers_url="https://careers.example.com"))

    assert result.status == "invalid_source_config"
    assert result.collector == "greenhouse_api"
    assert "Missing Greenhouse board token" in str(result.error)


def test_collect_greenhouse_jobs_http_error_returns_api_error(monkeypatch) -> None:
    def fake_fetch(url: str, *, timeout: int = 15):  # noqa: ARG001
        raise HTTPError(url, 503, "Service Unavailable", hdrs=None, fp=None)

    monkeypatch.setattr(greenhouse_module, "_fetch_json", fake_fetch)

    result = collect_greenhouse_jobs(_company())

    assert result.status == "api_error"
    assert result.collector == "greenhouse_api"
    assert "Greenhouse API request failed" in str(result.error)
