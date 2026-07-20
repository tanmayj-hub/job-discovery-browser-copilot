from __future__ import annotations

from pathlib import Path

from audit.scotiabank_trace import (
    canonical_job_id,
    load_scotiabank_expected_urls,
    trace_expected_jobs,
)


def test_scotiabank_fixture_urls_have_canonical_job_ids() -> None:
    urls = load_scotiabank_expected_urls(
        Path("data/exports/audits/manual-expected-jobs-next-slice.yaml")
    )

    assert len(urls) == 65
    assert all(canonical_job_id(url) for url in urls)


def test_trace_distinguishes_visible_rejected_and_direct_page_only_jobs() -> None:
    expected = [
        "https://jobs.scotiabank.com/job/Toronto-Cloud-Engineer-ON/123456789/",
        "https://jobs.scotiabank.com/job/Toronto-Quality-Engineer-ON/123456788/",
        "https://jobs.scotiabank.com/job/Toronto-DevOps-Engineer-ON/123456787/",
    ]
    rows = trace_expected_jobs(
        expected,
        [
            {
                "url": expected[0],
                "title": "Cloud Engineer",
                "is_relevant": "true",
                "score": "49",
                "relevance_tier": "core_target_fit",
            },
            {
                "url": expected[1],
                "title": "Quality Engineer",
                "is_relevant": "false",
                "score": "4",
                "relevance_tier": "not_relevant",
                "rejection_reason": "Weak title context.",
            },
        ],
        [{"job_url": expected[0], "status": "new"}],
        [{"job_url": expected[0], "review_state": "New"}],
        direct_statuses={"123456787": "active"},
    )

    assert [row["final_outcome"] for row in rows] == [
        "collected_and_visible",
        "collected_but_scoring_rejected",
        "active_but_not_in_current_listing",
    ]
