from __future__ import annotations

from classifier.ats_detector import (
    detect_ats_type,
    is_restricted_job_board,
    normalize_ats_hint,
    select_source_mode,
)


def test_detect_greenhouse_url() -> None:
    assert detect_ats_type("https://boards.greenhouse.io/example") == "greenhouse"


def test_detect_lever_url() -> None:
    assert detect_ats_type("https://jobs.lever.co/example") == "lever"


def test_detect_ashby_url() -> None:
    assert detect_ats_type("https://jobs.ashbyhq.com/example") == "ashby"


def test_detect_smartrecruiters_url() -> None:
    assert (
        detect_ats_type("https://jobs.smartrecruiters.com/Example/example")
        == "smartrecruiters"
    )


def test_detect_workday_url() -> None:
    assert detect_ats_type("https://example.myworkdayjobs.com/en-US/careers") == "workday"


def test_detect_successfactors_url() -> None:
    assert detect_ats_type("https://career5.successfactors.com/career") == "successfactors"


def test_detect_oracle_hcm_url() -> None:
    assert (
        detect_ats_type("https://fa-ext.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1")
        == "oracle_hcm"
    )


def test_detect_icims_url() -> None:
    assert detect_ats_type("https://jobs.example.icims.com/jobs/1234/job") == "icims"


def test_detect_phenom_url() -> None:
    assert detect_ats_type("https://jobs.example.phenompeople.com/us/en/job/123") == "phenom"


def test_restricted_board_detection_works_for_glassdoor() -> None:
    assert detect_ats_type("https://www.glassdoor.com/job-listing/example") == "restricted_board"
    assert is_restricted_job_board("https://www.glassdoor.com/job-listing/example") is True


def test_hint_detection_works_when_url_is_generic() -> None:
    assert detect_ats_type("https://careers.example.com", ats_hint="oraclecloud") == "oracle_hcm"
    assert normalize_ats_hint("oracle") == "oracle_hcm"


def test_select_source_mode_routes_api_friendly_and_complex_ats() -> None:
    assert (
        select_source_mode("https://boards.greenhouse.io/example", "greenhouse")
        == "api_allowed"
    )
    assert (
        select_source_mode("https://example.myworkdayjobs.com/jobs", "workday")
        == "human_in_loop"
    )
