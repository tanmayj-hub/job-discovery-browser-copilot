from __future__ import annotations

from pathlib import Path

from classifier.policy_engine import evaluate_source_policy, handle_browsing_barrier
from classifier.source_classifier import classify_source
from storage.db import get_interventions, initialize_database, upsert_companies

POLICIES_PATH = Path("config/policies.yaml")


def test_missing_url_sets_needs_url() -> None:
    result = classify_source(
        {
            "name": "Example Co",
            "source_name": "Example Careers",
            "careers_url": "",
            "ats_hint": None,
        },
        policies_path=POLICIES_PATH,
    )

    assert result.source_mode == "needs_url"
    assert result.ats_type is None
    assert "missing or invalid careers URL" in result.reasons


def test_workday_url_sets_human_in_loop() -> None:
    result = classify_source(
        {
            "name": "Example Co",
            "source_name": "Example Careers",
            "careers_url": "https://example.myworkdayjobs.com/en-US/careers",
            "ats_hint": None,
        },
        policies_path=POLICIES_PATH,
    )

    assert result.source_mode == "human_in_loop"
    assert result.ats_type == "workday"
    assert any("complex ATS" in reason for reason in result.reasons)


def test_linkedin_portal_sets_manual_only() -> None:
    decision = evaluate_source_policy(
        {
            "name": "Example Co",
            "source_name": "LinkedIn",
            "careers_url": "https://www.linkedin.com/jobs/view/example",
            "ats_hint": None,
        },
        policies_path=POLICIES_PATH,
    )

    assert decision.source_mode == "manual_only"
    assert decision.pause is True


def test_indeed_portal_sets_manual_only() -> None:
    result = classify_source(
        {
            "name": "Example Co",
            "source_name": "Indeed",
            "careers_url": "https://www.indeed.com/viewjob?jk=123",
            "ats_hint": None,
        },
        policies_path=POLICIES_PATH,
    )

    assert result.source_mode == "manual_only"
    assert result.ats_type == "restricted_board"


def test_glassdoor_portal_sets_manual_only() -> None:
    result = classify_source(
        {
            "name": "Example Co",
            "source_name": "Glassdoor",
            "careers_url": "https://www.glassdoor.com/job-listing/example",
            "ats_hint": None,
        },
        policies_path=POLICIES_PATH,
    )

    assert result.source_mode == "manual_only"
    assert result.ats_type == "restricted_board"


def test_public_browser_source_sets_browser_allowed() -> None:
    result = classify_source(
        {
            "name": "Example Co",
            "source_name": "Company Careers",
            "careers_url": "https://careers.example.com",
            "ats_hint": "",
        },
        policies_path=POLICIES_PATH,
    )

    assert result.source_mode == "browser_allowed"
    assert result.ats_type is None
    assert any("public careers URL" in reason for reason in result.reasons)


def test_greenhouse_source_sets_api_allowed() -> None:
    result = classify_source(
        {
            "name": "Example Co",
            "source_name": "Careers",
            "careers_url": "https://boards.greenhouse.io/example",
            "ats_hint": None,
        },
        policies_path=POLICIES_PATH,
    )

    assert result.source_mode == "api_allowed"
    assert result.ats_type == "greenhouse"
    assert any("API-friendly" in reason for reason in result.reasons)


def test_lever_ashby_and_smartrecruiters_sources_are_api_allowed() -> None:
    urls = {
        "lever": "https://jobs.lever.co/example",
        "ashby": "https://jobs.ashbyhq.com/example",
        "smartrecruiters": "https://jobs.smartrecruiters.com/Example/example",
    }

    for ats_type, url in urls.items():
        result = classify_source(
            {
                "name": "Example Co",
                "source_name": "Careers",
                "careers_url": url,
                "ats_hint": None,
            },
            policies_path=POLICIES_PATH,
        )
        assert result.source_mode == "api_allowed"
        assert result.ats_type == ats_type


def test_successfactors_oracle_icims_and_phenom_do_not_become_api_allowed() -> None:
    urls = {
        "successfactors": "https://career5.successfactors.com/career",
        "oracle_hcm": "https://fa-ext.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1",
        "icims": "https://jobs.example.icims.com/jobs/1234/job",
        "phenom": "https://jobs.example.phenompeople.com/us/en/job/123",
    }

    for ats_type, url in urls.items():
        result = classify_source(
            {
                "name": "Example Co",
                "source_name": "Careers",
                "careers_url": url,
                "ats_hint": None,
            },
            policies_path=POLICIES_PATH,
        )
        assert result.source_mode == "human_in_loop"
        assert result.ats_type == ats_type


def test_hint_detection_still_works_with_generic_url() -> None:
    result = classify_source(
        {
            "name": "Example Co",
            "source_name": "Careers",
            "website_category": "Oracle HCM",
            "careers_url": "https://careers.example.com",
            "ats_hint": "oraclecloud",
        },
        policies_path=POLICIES_PATH,
    )

    assert result.source_mode == "human_in_loop"
    assert result.ats_type == "oracle_hcm"


def test_captcha_or_login_creates_intervention_and_pauses(tmp_path: Path) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(
        connection,
        [
            {
                "name": "Example Co",
                "sector": "IT Consulting & Systems Integrators",
                "category": "Consulting/SI",
                "careers_url": "https://careers.example.com",
                "website_category": "careers",
                "ats_hint": "",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "browser_allowed",
            }
        ],
    )

    decision = handle_browsing_barrier(
        connection,
        company_name="Example Co",
        detected_signals=["captcha"],
        policies_path=POLICIES_PATH,
    )

    interventions = get_interventions(connection)

    assert decision.pause is True
    assert decision.source_mode == "manual_only"
    assert decision.intervention_id is not None
    assert len(interventions) == 1
    assert interventions[0]["intervention_type"] == "barrier_detected"
