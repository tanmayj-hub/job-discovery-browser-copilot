from __future__ import annotations

from pathlib import Path

import yaml

from dashboard.starter_urls import build_starter_career_url_map, load_starter_career_url_entries


def test_load_starter_career_url_entries_reads_companies_list(tmp_path: Path) -> None:
    starter_path = tmp_path / "starter_career_urls.yaml"
    starter_path.write_text(
        yaml.safe_dump(
            {
                "companies": [
                    {
                        "name": "Example One",
                        "careers_url": "https://example.com/careers",
                        "confidence": "high",
                        "notes": "Verified",
                    },
                    {
                        "name": "Example Two",
                        "careers_url": "",
                        "confidence": "low",
                        "notes": "Still unknown",
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    entries = load_starter_career_url_entries(starter_path)

    assert len(entries) == 2
    assert entries[0]["name"] == "Example One"
    assert entries[1]["confidence"] == "low"


def test_build_starter_career_url_map_keys_entries_by_company_name(tmp_path: Path) -> None:
    starter_path = tmp_path / "starter_career_urls.yaml"
    starter_path.write_text(
        yaml.safe_dump(
            {
                "companies": [
                    {
                        "name": "Example One",
                        "careers_url": "https://example.com/careers",
                        "confidence": "high",
                        "notes": "Verified",
                    },
                    {
                        "name": "Example Two",
                        "careers_url": "",
                        "confidence": "low",
                        "notes": "Still unknown",
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    starter_map = build_starter_career_url_map(starter_path)

    assert sorted(starter_map) == ["Example One", "Example Two"]
    assert starter_map["Example One"]["careers_url"] == "https://example.com/careers"
    assert starter_map["Example Two"]["notes"] == "Still unknown"
