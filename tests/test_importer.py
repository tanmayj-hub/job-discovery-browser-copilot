from __future__ import annotations

from pathlib import Path

import yaml
from openpyxl import Workbook

from importer.excel_importer import (
    SOURCE_MODE_API_ALLOWED,
    SOURCE_MODE_BROWSER_ALLOWED,
    SOURCE_MODE_HUMAN_IN_LOOP,
    SOURCE_MODE_NEEDS_URL,
    build_companies_payload,
    load_company_configs,
    update_company_record_in_yaml,
    write_companies_yaml,
)


def test_load_company_configs_filters_bank_market_and_it_consulting() -> None:
    workbook_path = Path("data/input/rishi/companies.xlsx")

    configs = load_company_configs(workbook_path)
    names = [config.name for config in configs]

    assert "RBC" in names
    assert "Accenture" in names
    assert "Ateko" in names
    assert all(
        config.category == "Bank/Market" or config.sector == "IT Consulting & Systems Integrators"
        for config in configs
    )


def test_url_and_ats_hint_normalization(tmp_path: Path) -> None:
    workbook_path = tmp_path / "companies.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Companies"
    sheet.append(
        [
            "Company",
            "Careers page URL (fill in)",
            "website category",
            "Sector",
            "Category",
            "Canada hubs / notes",
            "Role families",
            "Suggested search keywords",
            "Early-career pipeline",
            "Priority",
            "Monitoring hint",
            "Status",
            "Last checked",
            "Notes",
        ]
    )
    sheet.append(
        [
            "Example Bank",
            "Search results | Jobs at Example Bank",
            "Workday",
            "Banking & Capital Markets",
            "Bank/Market",
            "Toronto",
            "Cloud / DevOps",
            "cloud, devops",
            "Yes",
            "High",
            "Manual review",
            "Watching",
            "",
            "",
        ]
    )
    sheet.append(
        [
            "Example Consulting",
            "https://careers.example.com",
            "Greenhouse",
            "IT Consulting & Systems Integrators",
            "Consulting/SI",
            "Canada-wide",
            "Cloud / Platform",
            "platform, terraform",
            "Yes",
            "Medium",
            "Manual review",
            "Watching",
            "",
            "",
        ]
    )
    sheet.append(
        [
            "Example Public Careers",
            "https://jobs.examplepublic.com/careers",
            "jobs",
            "IT Consulting & Systems Integrators",
            "Consulting/SI",
            "Canada-wide",
            "Cloud / Platform",
            "platform, terraform",
            "Yes",
            "Medium",
            "Manual review",
            "Watching",
            "",
            "",
        ]
    )
    sheet.append(
        [
            "Example Workday",
            "https://exampleworkday.com/careers",
            "Workday",
            "IT Consulting & Systems Integrators",
            "Consulting/SI",
            "Canada-wide",
            "Cloud / Platform",
            "platform, terraform",
            "Yes",
            "Medium",
            "Manual review",
            "Watching",
            "",
            "",
        ]
    )
    workbook.save(workbook_path)

    configs = load_company_configs(workbook_path)

    assert [config.name for config in configs] == [
        "Example Bank",
        "Example Consulting",
        "Example Public Careers",
        "Example Workday",
    ]
    assert configs[0].careers_url is None
    assert configs[0].source_mode == SOURCE_MODE_NEEDS_URL
    assert configs[0].ats_hint == "workday"
    assert configs[0].role_families == ["Cloud", "DevOps"]
    assert configs[0].keywords == ["cloud", "devops"]

    assert configs[1].careers_url == "https://careers.example.com"
    assert configs[1].source_mode == SOURCE_MODE_API_ALLOWED
    assert configs[1].ats_hint == "greenhouse"

    assert configs[2].careers_url == "https://jobs.examplepublic.com/careers"
    assert configs[2].source_mode == SOURCE_MODE_BROWSER_ALLOWED
    assert configs[2].ats_hint is None

    assert configs[3].careers_url == "https://exampleworkday.com/careers"
    assert configs[3].source_mode == SOURCE_MODE_HUMAN_IN_LOOP
    assert configs[3].ats_hint == "workday"


def test_write_companies_yaml(tmp_path: Path) -> None:
    output_path = tmp_path / "companies.yaml"
    configs = load_company_configs(Path("data/input/rishi/companies.xlsx"))

    write_companies_yaml(configs[:1], output_path)

    payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert list(payload) == ["companies"]
    assert payload["companies"][0]["name"] == "RBC"
    assert "ats_hint" not in payload["companies"][0]
    assert payload["companies"][0]["source_mode"] == SOURCE_MODE_NEEDS_URL


def test_build_companies_payload_is_yaml_friendly() -> None:
    configs = load_company_configs(Path("data/input/rishi/companies.xlsx"))[:1]
    payload = build_companies_payload(configs)

    assert list(payload) == ["companies"]
    assert isinstance(payload["companies"], list)


def test_update_company_record_in_yaml_updates_one_company(tmp_path: Path) -> None:
    output_path = tmp_path / "companies.yaml"
    output_path.write_text(
        yaml.safe_dump(
            {
                "companies": [
                    {
                        "name": "Example Bank",
                        "source_mode": "needs_url",
                    },
                    {
                        "name": "Example Consulting",
                        "careers_url": "https://careers.example.com",
                        "source_mode": "api_allowed",
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    updated = update_company_record_in_yaml(
        output_path,
        company_name="Example Bank",
        updates={
            "careers_url": "https://bank.example.com/careers",
            "source_mode": "browser_allowed",
        },
    )

    payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert updated["careers_url"] == "https://bank.example.com/careers"
    assert updated["source_mode"] == "browser_allowed"
    assert payload["companies"][0]["careers_url"] == "https://bank.example.com/careers"
    assert payload["companies"][0]["source_mode"] == "browser_allowed"
    assert payload["companies"][1]["source_mode"] == "api_allowed"


def test_update_company_record_in_yaml_raises_for_unknown_company(tmp_path: Path) -> None:
    output_path = tmp_path / "companies.yaml"
    output_path.write_text(
        yaml.safe_dump({"companies": [{"name": "Example Bank", "source_mode": "needs_url"}]}),
        encoding="utf-8",
    )

    try:
        update_company_record_in_yaml(
            output_path,
            company_name="Missing Company",
            updates={"source_mode": "browser_allowed"},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected update of an unknown company to raise ValueError")
