from __future__ import annotations

from pathlib import Path

from processing.score import score_job

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
