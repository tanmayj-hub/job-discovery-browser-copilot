from __future__ import annotations

from reports.daily_run import deduplicate_jobs


def test_deduplicate_jobs_removes_duplicate_job_urls() -> None:
    jobs = [
        {
            "company_name": "Example Co",
            "title": "Cloud Engineer",
            "location": "Toronto",
            "job_url": "https://careers.example.com/jobs/1",
        },
        {
            "company_name": "Example Co",
            "title": "Cloud Engineer",
            "location": "Toronto",
            "job_url": "https://careers.example.com/jobs/1",
        },
        {
            "company_name": "Example Co",
            "title": "Platform Engineer",
            "location": "Remote",
            "job_url": "https://careers.example.com/jobs/2",
        },
    ]

    deduped = deduplicate_jobs(jobs)

    assert len(deduped) == 2
    assert [job["job_url"] for job in deduped] == [
        "https://careers.example.com/jobs/1",
        "https://careers.example.com/jobs/2",
    ]


def test_deduplicate_jobs_falls_back_to_company_title_and_location() -> None:
    jobs = [
        {
            "company_name": "Example Co",
            "title": "Cloud Support Engineer",
            "location": "Toronto",
            "job_url": None,
        },
        {
            "company_name": "Example Co",
            "title": "Cloud Support Engineer",
            "location": "Toronto",
            "job_url": None,
        },
        {
            "company_name": "Example Co",
            "title": "Cloud Support Engineer",
            "location": "Mississauga",
            "job_url": None,
        },
    ]

    deduped = deduplicate_jobs(jobs)

    assert len(deduped) == 2
    assert deduped[0]["location"] == "Toronto"
    assert deduped[1]["location"] == "Mississauga"


def test_deduplicate_jobs_uses_external_ats_identity_when_available() -> None:
    jobs = [
        {
            "company_name": "Example Co",
            "title": "Cloud Engineer",
            "location": "Toronto",
            "job_url": None,
            "external_job_id": "123",
            "ats_type": "greenhouse",
            "board_slug": "example",
        },
        {
            "company_name": "Example Co",
            "title": "Cloud Engineer II",
            "location": "Remote",
            "job_url": None,
            "external_job_id": "123",
            "ats_type": "greenhouse",
            "board_slug": "example",
        },
        {
            "company_name": "Example Co",
            "title": "Cloud Engineer",
            "location": "Toronto",
            "job_url": None,
            "external_job_id": "456",
            "ats_type": "greenhouse",
            "board_slug": "example",
        },
    ]

    deduped = deduplicate_jobs(jobs)

    assert len(deduped) == 2
    assert deduped[0]["external_job_id"] == "123"
    assert deduped[1]["external_job_id"] == "456"
