from __future__ import annotations

from pathlib import Path

import yaml

from importer.apply_career_urls import apply_career_url_updates, main


def _write_companies_yaml(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "companies": [
                    {
                        "name": "Example API",
                        "website_category": "greenhouse",
                        "ats_hint": "greenhouse",
                        "source_mode": "needs_url",
                    },
                    {
                        "name": "Example Browser",
                        "website_category": "company-careers",
                        "source_mode": "needs_url",
                    },
                    {
                        "name": "Example Human",
                        "website_category": "workday",
                        "ats_hint": "workday",
                        "source_mode": "needs_url",
                    },
                    {
                        "name": "Still Missing",
                        "website_category": "company-careers",
                        "source_mode": "needs_url",
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_starter_yaml(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "companies": [
                    {
                        "name": "Example API",
                        "careers_url": "https://jobs.exampleapi.com/board",
                        "confidence": "high",
                        "notes": "Verified starter URL",
                    },
                    {
                        "name": "Example Browser",
                        "careers_url": "https://careers.examplebrowser.com/jobs",
                        "confidence": "medium",
                        "notes": "Verified starter URL",
                    },
                    {
                        "name": "Example Human",
                        "careers_url": "https://examplehuman.workdayjobs.com/careers",
                        "confidence": "high",
                        "notes": "Verified starter URL",
                    },
                    {
                        "name": "Still Missing",
                        "careers_url": "",
                        "confidence": "low",
                        "notes": "No verified URL yet",
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_apply_career_url_updates_reclassifies_matching_companies(tmp_path: Path) -> None:
    companies_path = tmp_path / "companies.yaml"
    starter_path = tmp_path / "starter_career_urls.yaml"
    _write_companies_yaml(companies_path)
    _write_starter_yaml(starter_path)

    summary = apply_career_url_updates(
        starter_path=starter_path,
        companies_path=companies_path,
    )
    payload = yaml.safe_load(companies_path.read_text(encoding="utf-8"))
    companies = {company["name"]: company for company in payload["companies"]}

    assert summary == {
        "updated": 3,
        "still_missing": 1,
        "api_allowed": 1,
        "browser_allowed": 1,
        "human_in_loop": 1,
    }
    assert companies["Example API"]["source_mode"] == "api_allowed"
    assert companies["Example API"]["careers_url"] == "https://jobs.exampleapi.com/board"
    assert companies["Example Browser"]["source_mode"] == "browser_allowed"
    assert companies["Example Human"]["source_mode"] == "human_in_loop"
    assert "careers_url" not in companies["Still Missing"]


def test_apply_career_url_main_prints_summary(capsys, tmp_path: Path) -> None:
    companies_path = tmp_path / "companies.yaml"
    starter_path = tmp_path / "starter_career_urls.yaml"
    _write_companies_yaml(companies_path)
    _write_starter_yaml(starter_path)

    exit_code = main(
        [
            "--starter",
            str(starter_path),
            "--companies",
            str(companies_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "updated: 3" in captured.out
    assert "still missing: 1" in captured.out
    assert "api_allowed: 1" in captured.out
    assert "browser_allowed: 1" in captured.out
    assert "human_in_loop: 1" in captured.out
