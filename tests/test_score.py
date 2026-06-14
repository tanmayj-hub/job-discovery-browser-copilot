from __future__ import annotations

from pathlib import Path

from processing.score import explain_job_score, score_job

KEYWORDS_PATH = Path("config/keywords.yaml")
SCORING_PATH = Path("config/scoring.yaml")


def test_score_job_high_match_for_target_cloud_devops_role() -> None:
    job = {
        "title": "Cloud Support Engineer",
        "location": "Toronto, Ontario, Canada",
        "description": (
            "Support AWS and Kubernetes production environments, write Bash and Python "
            "automation, manage IAM, troubleshooting, monitoring, and CloudWatch alerts."
        ),
        "requirements": (
            "Linux, Docker, Terraform, CI/CD, GitHub Actions, networking, and support mindset."
        ),
    }

    result = score_job(job, keywords_path=KEYWORDS_PATH, scoring_path=SCORING_PATH)

    assert result.match_score >= 75
    assert any("title matches target role" in reason for reason in result.match_reasons)
    assert any("matched skills" in reason for reason in result.match_reasons)
    assert result.risk_flags == []


def test_score_job_applies_negative_penalties() -> None:
    job = {
        "title": "Senior Platform Architect",
        "location": "Remote - US only",
        "description": (
            "Principal-level architect role. Requires 10+ years, requires US citizenship, "
            "own cloud strategy and platform design."
        ),
    }

    result = score_job(job, keywords_path=KEYWORDS_PATH, scoring_path=SCORING_PATH)

    assert result.match_score < 40
    assert any("Senior" in flag for flag in result.risk_flags)
    assert any("US only" in flag for flag in result.risk_flags)
    assert any("Requires 10+ years" in flag for flag in result.risk_flags)


def test_score_job_can_match_role_from_description_when_title_is_generic() -> None:
    job = {
        "title": "Technology Analyst",
        "location": "Hybrid - Mississauga, Ontario",
        "description": (
            "This team is hiring a Junior DevOps Engineer to support CI/CD pipelines, Jenkins, "
            "GitHub Actions, Linux administration, and troubleshooting."
        ),
    }

    result = score_job(job, keywords_path=KEYWORDS_PATH, scoring_path=SCORING_PATH)

    assert result.match_score >= 40
    assert any("description mentions target role" in reason for reason in result.match_reasons)
    assert any("location signals" in reason for reason in result.match_reasons)


def test_score_job_returns_low_score_when_signals_are_weak() -> None:
    job = {
        "title": "Business Analyst",
        "location": "Montreal",
        "description": "Document stakeholder requirements and coordinate reporting.",
    }

    result = score_job(job, keywords_path=KEYWORDS_PATH, scoring_path=SCORING_PATH)

    assert result.match_score == 0
    assert result.match_reasons == []
    assert result.risk_flags == []


def test_explain_job_score_includes_threshold_score_and_relevance() -> None:
    job = {
        "company_name": "TD",
        "title": "Cloud Support Engineer",
        "location": "Toronto, Ontario, Canada",
        "description": "Support AWS and Linux environments with monitoring and troubleshooting.",
    }

    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["final_score"] > 0
    assert explanation["threshold"]
    assert explanation["is_relevant"] is True
    assert "Cloud Support Engineer" in explanation["title_matches"]
    assert "AWS" in explanation["positive_keyword_matches"]


def test_explain_job_score_handles_no_matches_cleanly() -> None:
    job = {
        "title": "Business Analyst",
        "location": "Montreal",
        "description": "Document stakeholder requirements and coordinate reporting.",
    }

    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["final_score"] == 0
    assert explanation["is_relevant"] is False
    assert explanation["positive_keyword_matches"] == []
    assert explanation["match_reasons"] == []


def test_explain_job_score_matches_score_job_output() -> None:
    job = {
        "title": "Technology Analyst",
        "location": "Hybrid - Mississauga, Ontario",
        "description": (
            "This team is hiring a Junior DevOps Engineer to support Jenkins, "
            "GitHub Actions, Linux administration, and troubleshooting."
        ),
    }

    scored = score_job(job, keywords_path=KEYWORDS_PATH, scoring_path=SCORING_PATH)
    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["final_score"] == scored.match_score
    assert explanation["match_reasons"] == scored.match_reasons
    assert explanation["risk_flags"] == scored.risk_flags


def test_score_job_ignores_html_link_markup_noise_in_description() -> None:
    job = {
        "title": "Software Engineer II- Salesforce",
        "location": "",
        "description": (
            '<div><a href="/en-US/TD_Bank_Careers/job/Toronto-Ontario/'
            'Software-Engineer-II--Salesforce_R_1486443">Software Engineer II- Salesforce</a></div>'
        ),
    }

    result = score_job(job, keywords_path=KEYWORDS_PATH, scoring_path=SCORING_PATH)
    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert result.match_score == 0
    assert result.match_reasons == []
    assert explanation["location_scope_signals"] == []


def test_solutions_engineer_is_scored_as_adjacent_customer_facing_technical_fit() -> None:
    job = {
        "title": "Solutions Engineer",
        "location": "Toronto, Ontario, Canada",
        "description": "Support enterprise platform demos and customer technical discovery.",
    }

    result = score_job(job, keywords_path=KEYWORDS_PATH, scoring_path=SCORING_PATH)
    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert result.match_score > 0
    assert explanation["is_relevant"] is True
    assert explanation["relevance_tier"] == "adjacent_customer_facing_technical_fit"
    assert any(
        "adjacent customer-facing technical fit" in reason
        for reason in explanation["match_reasons"]
    )


def test_customer_success_engineer_is_scored_as_adjacent_fit() -> None:
    job = {
        "title": "Customer Success Engineer",
        "location": "Canada",
        "description": "Guide customers through technical onboarding and platform adoption.",
    }

    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is True
    assert explanation["relevance_tier"] == "adjacent_customer_facing_technical_fit"


def test_technical_consultant_with_technical_context_is_adjacent_fit() -> None:
    job = {
        "title": "Technical Consultant",
        "location": "Toronto, Ontario, Canada",
        "description": (
            "Work with customers on enterprise platform implementation, cloud integration, "
            "and solution design."
        ),
    }

    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is True
    assert explanation["relevance_tier"] == "adjacent_customer_facing_technical_fit"


def test_customer_service_representative_is_not_promoted_to_relevant() -> None:
    job = {
        "title": "Customer Service Representative",
        "location": "Toronto, Ontario, Canada",
        "description": "Support customer billing questions and handle account inquiries.",
    }

    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert explanation["relevance_tier"] == "not_relevant"


def test_sales_associate_is_not_promoted_to_relevant() -> None:
    job = {
        "title": "Sales Associate",
        "location": "Toronto, Ontario, Canada",
        "description": "Retail sales role focused on store performance and transactions.",
    }

    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert explanation["relevance_tier"] == "not_relevant"


def test_generic_business_analyst_without_technical_context_is_not_relevant() -> None:
    job = {
        "title": "Business Analyst",
        "location": "Toronto, Ontario, Canada",
        "description": "Coordinate reporting, timelines, and stakeholder meetings.",
    }

    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert explanation["relevance_tier"] == "not_relevant"


def test_business_systems_analyst_with_platform_context_can_be_adjacent_fit() -> None:
    job = {
        "title": "Business Systems Analyst",
        "location": "Toronto, Ontario, Canada",
        "description": (
            "Support enterprise platform implementation, systems integration, and product "
            "delivery across cloud tooling."
        ),
    }

    explanation = explain_job_score(
        job,
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is True
    assert explanation["relevance_tier"] == "adjacent_customer_facing_technical_fit"


def test_expert_banking_advisor_is_rejected() -> None:
    explanation = explain_job_score(
        {
            "title": "Expert Banking Advisor",
            "location": "Toronto, Ontario, Canada",
            "description": "Advise retail clients on branch products and daily banking needs.",
        },
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert any("hard reject title" in flag for flag in explanation["risk_flags"])


def test_mortgage_specialist_is_rejected_without_technical_context() -> None:
    explanation = explain_job_score(
        {
            "title": "Mortgage Specialist",
            "location": "Toronto, Ontario, Canada",
            "description": "Grow a mortgage portfolio and advise clients on lending products.",
        },
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert explanation["final_score"] == 0


def test_executive_assistant_is_hard_rejected() -> None:
    explanation = explain_job_score(
        {
            "title": "Executive Assistant",
            "location": "Toronto, Ontario, Canada",
            "description": "Support leadership calendars, travel, and meeting coordination.",
        },
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert any(
        "hard reject title: executive assistant" == flag
        for flag in explanation["risk_flags"]
    )


def test_client_delivery_associate_without_technical_context_is_rejected() -> None:
    explanation = explain_job_score(
        {
            "title": "Client Delivery Associate",
            "location": "Toronto, Ontario, Canada",
            "description": "Coordinate client meetings, reporting, and account follow-up.",
        },
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert explanation["final_score"] == 0


def test_customer_success_engineer_with_technical_context_remains_relevant() -> None:
    explanation = explain_job_score(
        {
            "title": "Customer Success Engineer",
            "location": "Toronto, Ontario, Canada",
            "description": (
                "Guide customer onboarding for cloud platform adoption, API integration, "
                "and Kubernetes production readiness."
            ),
        },
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is True
    assert explanation["relevance_tier"] == "adjacent_customer_facing_technical_fit"


def test_delivery_consultant_without_technical_context_is_rejected() -> None:
    explanation = explain_job_score(
        {
            "title": "Delivery Consultant",
            "location": "Toronto, Ontario, Canada",
            "description": "Coordinate client meetings, timelines, and status reporting.",
        },
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert explanation["relevance_tier"] == "not_relevant"


def test_sales_associate_with_aws_substring_noise_is_not_relevant() -> None:
    explanation = explain_job_score(
        {
            "title": "Sales Associate",
            "location": "Toronto, Ontario, Canada",
            "description": "Grow store traffic and support weekend retail campaigns.",
        },
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert explanation["positive_keyword_matches"] == []


def test_customer_experience_associate_does_not_gain_false_iam_match() -> None:
    explanation = explain_job_score(
        {
            "title": "Customer Experience Associate - Part-time",
            "location": "Toronto, Ontario, Canada",
            "description": "Help clients with branch transactions and day-to-day questions.",
        },
        keywords_path=KEYWORDS_PATH,
        scoring_path=SCORING_PATH,
    )

    assert explanation["is_relevant"] is False
    assert "IAM" not in explanation["positive_keyword_matches"]
