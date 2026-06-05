from __future__ import annotations

import collectors.static_jsonld as jsonld_module
from collectors.static_jsonld import collect_static_jsonld_jobs


def _company(**overrides: object) -> dict[str, object]:
    company = {
        "name": "Example Co",
        "company_name": "Example Co",
        "careers_url": "https://careers.example.com/jobs",
        "website_category": "company-careers",
        "source_name": "company-careers",
        "source_mode": "browser_allowed",
    }
    company.update(overrides)
    return company


def test_collect_static_jsonld_jobs_normalizes_job_posting(monkeypatch) -> None:
    html = """
    <html>
      <body>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Cloud Support Engineer",
            "description": "<p>AWS and Linux support.</p>",
            "datePosted": "2026-06-02",
            "url": "https://careers.example.com/jobs/cloud-support-engineer",
            "identifier": {"value": "job-987"},
            "jobLocationType": "TELECOMMUTE",
            "jobLocation": {
              "@type": "Place",
              "address": {
                "addressLocality": "Toronto",
                "addressRegion": "Ontario",
                "addressCountry": "Canada"
              }
            }
          }
        </script>
      </body>
    </html>
    """

    monkeypatch.setattr(jsonld_module, "_fetch_html", lambda url, timeout=15: html)  # noqa: ARG005

    result = collect_static_jsonld_jobs(_company())

    assert result.status == "success"
    assert result.collector == "static_jsonld"
    assert result.jobs_discovered == 1
    assert result.jobs[0]["title"] == "Cloud Support Engineer"
    assert result.jobs[0]["location"] == "Toronto, Ontario, Canada | Remote"
    assert result.jobs[0]["job_url"] == "https://careers.example.com/jobs/cloud-support-engineer"
    assert result.jobs[0]["apply_url"] == "https://careers.example.com/jobs/cloud-support-engineer"
    assert result.jobs[0]["external_job_id"] == "job-987"
    assert result.jobs[0]["ats_type"] == "jsonld"
    assert result.jobs[0]["board_slug"] == "careers.example.com"
    assert result.jobs[0]["source_mode"] == "browser_allowed"


def test_collect_static_jsonld_jobs_supports_graph_payload(monkeypatch) -> None:
    html = """
    <html>
      <body>
        <script type="application/ld+json">
          {
            "@graph": [
              {"@type": "Organization", "name": "Example Co"},
              {
                "@type": "JobPosting",
                "title": "Infrastructure Analyst",
                "description": "<p>Monitoring and support.</p>",
                "url": "https://careers.example.com/jobs/infrastructure-analyst"
              }
            ]
          }
        </script>
      </body>
    </html>
    """

    monkeypatch.setattr(jsonld_module, "_fetch_html", lambda url, timeout=15: html)  # noqa: ARG005

    result = collect_static_jsonld_jobs(_company())

    assert result.status == "success"
    assert result.jobs_discovered == 1
    assert result.jobs[0]["title"] == "Infrastructure Analyst"


def test_collect_static_jsonld_jobs_returns_parse_error_for_only_malformed_payload(
    monkeypatch,
) -> None:
    html = """
    <html>
      <body>
        <script type="application/ld+json">{not valid json}</script>
      </body>
    </html>
    """

    monkeypatch.setattr(jsonld_module, "_fetch_html", lambda url, timeout=15: html)  # noqa: ARG005

    result = collect_static_jsonld_jobs(_company())

    assert result.status == "parse_error"
    assert result.collector == "static_jsonld"
    assert "Malformed JSON-LD encountered" in str(result.error)


def test_collect_static_jsonld_jobs_returns_no_jobs_when_no_jobposting_found(
    monkeypatch,
) -> None:
    html = """
    <html>
      <body>
        <script type="application/ld+json">
          {"@type": "Organization", "name": "Example Co"}
        </script>
      </body>
    </html>
    """

    monkeypatch.setattr(jsonld_module, "_fetch_html", lambda url, timeout=15: html)  # noqa: ARG005

    result = collect_static_jsonld_jobs(_company())

    assert result.status == "no_jobs_found"
    assert result.collector == "static_jsonld"
