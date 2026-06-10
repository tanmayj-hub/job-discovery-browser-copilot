from __future__ import annotations

import csv
from pathlib import Path

import main as cli_main
from audit.accuracy_audit import (
    AUDIT_SAMPLE_FIELDS,
    MANUAL_TEMPLATE_FIELDS,
    _url_identity,
    build_company_audit_pack,
    build_manual_audit_link_sheet,
    calculate_metrics,
    compare_audit_files,
    compare_manual_expected_urls,
    create_manual_template,
    export_audit_sample,
    find_job_for_score_explanation,
    load_manual_expected_jobs,
    validate_audit_files,
    write_company_collection_diagnostic,
)
from storage.db import initialize_database, upsert_companies, upsert_job_record

AUDIT_FIXTURE_PATH = Path("tests/fixtures/audit/manual_expected_jobs_td_ibm_sunlife.yaml")


def _seed_company_and_job(tmp_path: Path) -> tuple[Path, object]:
    db_path = tmp_path / "job_discovery.db"
    connection = initialize_database(db_path)
    upsert_companies(
        connection,
        [
            {
                "name": "TD",
                "sector": "Banking & Capital Markets",
                "category": "Bank/Market",
                "careers_url": "https://careers.td.com/jobs",
                "website_category": "workday",
                "ats_hint": "workday",
                "canada_hubs_notes": "Toronto",
                "role_families": ["Cloud"],
                "keywords": ["cloud"],
                "priority": "High",
                "monitoring_hint": "Manual check",
                "status": "Watching",
                "source_mode": "human_in_loop",
            }
        ],
    )
    upsert_job_record(
        connection,
        {
            "company_name": "TD",
            "title": "Cloud Engineer",
            "location": "Toronto, Ontario, Canada",
            "job_url": "https://careers.td.com/jobs/cloud-engineer-123",
            "apply_url": "https://careers.td.com/jobs/cloud-engineer-123",
            "source_name": "workday",
            "source_mode": "human_in_loop",
            "description": "Cloud role.",
            "date_posted": "2026-06-06",
            "external_job_id": "td-123",
            "ats_type": "workday",
            "board_slug": "td",
            "match_score": 42,
            "match_reasons": ["title matches: cloud engineer"],
            "risk_flags": [],
            "status": "new",
            "last_seen_at": "2026-06-06T18:00:00Z",
        },
    )
    return db_path, connection


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _write_companies_config(path: Path) -> None:
    path.write_text(
        """
companies:
  - name: TD
    sector: Banking & Capital Markets
    category: Bank/Market
    careers_url: https://careers.td.com/jobs
    website_category: workday
    ats_hint: workday
    source_mode: human_in_loop
""",
        encoding="utf-8",
    )


def test_export_audit_sample_includes_mvp_fields_and_blank_manual_fields(tmp_path: Path) -> None:
    _, connection = _seed_company_and_job(tmp_path)
    output_path = tmp_path / "accuracy-audit-sample.csv"

    rows = export_audit_sample(
        connection,
        output_path=output_path,
        companies=["TD"],
        limit_per_company=10,
        include_recent_days=14,
        status="new",
    )

    exported = _read_csv(output_path)

    assert len(rows) == 1
    assert output_path.exists()
    assert exported[0]["company_name"] == "TD"
    assert exported[0]["mvp_title"] == "Cloud Engineer"
    assert exported[0]["mvp_external_job_id"] == "td-123"
    assert exported[0]["manual_title"] == ""
    assert exported[0]["manual_found"] == ""
    assert set(exported[0].keys()) == set(AUDIT_SAMPLE_FIELDS)


def test_create_manual_template_contains_required_fields(tmp_path: Path) -> None:
    output_path = tmp_path / "manual-job-audit-template.csv"

    rows = create_manual_template(
        output_path=output_path,
        companies=["TD", "RBC"],
    )

    exported = _read_csv(output_path)

    assert len(rows) == 2
    assert output_path.exists()
    assert exported[0]["company_name"] == "TD"
    assert exported[1]["company_name"] == "RBC"
    assert set(exported[0].keys()) == set(MANUAL_TEMPLATE_FIELDS)


def test_compare_matches_jobs_by_external_job_id(tmp_path: Path) -> None:
    mvp_path = tmp_path / "mvp.csv"
    manual_path = tmp_path / "manual.csv"
    report_path = tmp_path / "accuracy-audit-report.md"
    _write_csv(
        mvp_path,
        AUDIT_SAMPLE_FIELDS,
        [
            {
                "company_name": "TD",
                "mvp_title": "Cloud Engineer",
                "mvp_location": "Toronto",
                "mvp_url": "https://careers.td.com/jobs/cloud-engineer-123",
                "mvp_external_job_id": "td-123",
                "mvp_ats_type": "workday",
                "mvp_board_slug": "td",
                "mvp_score": "42",
                "mvp_last_seen_at": "2026-06-06T18:00:00Z",
                "manual_title": "",
                "manual_location": "",
                "manual_url": "",
                "manual_found": "",
                "manual_relevant": "",
                "audit_status": "",
                "match_confidence": "",
                "reason": "",
                "manual_notes": "",
            }
        ],
    )
    _write_csv(
        manual_path,
        MANUAL_TEMPLATE_FIELDS,
        [
            {
                "company_name": "TD",
                "manual_title": "Cloud Engineer",
                "manual_location": "Toronto",
                "manual_url": "https://careers.td.com/jobs/another-url",
                "manual_external_job_id": "td-123",
                "manual_source_url": "https://careers.td.com/jobs",
                "manual_relevant": "true",
                "manual_notes": "",
            }
        ],
    )

    result = compare_audit_files(
        mvp_path=mvp_path,
        manual_path=manual_path,
        output_path=report_path,
    )

    assert result.audit_records[0]["audit_status"] == "matched"
    assert result.audit_records[0]["match_confidence"] == "high"
    assert "external_job_id" in result.audit_records[0]["reason"]


def test_compare_matches_jobs_by_normalized_url(tmp_path: Path) -> None:
    mvp_path = tmp_path / "mvp.csv"
    manual_path = tmp_path / "manual.csv"
    report_path = tmp_path / "accuracy-audit-report.md"
    _write_csv(
        mvp_path,
        AUDIT_SAMPLE_FIELDS,
        [
            {
                "company_name": "CGI",
                "mvp_title": "Systems Administrator",
                "mvp_location": "Montreal",
                "mvp_url": "https://cgi.example.com/jobs/1?a=1&b=2",
                "mvp_external_job_id": "",
                "mvp_ats_type": "",
                "mvp_board_slug": "",
                "mvp_score": "25",
                "mvp_last_seen_at": "2026-06-06T18:00:00Z",
                "manual_title": "",
                "manual_location": "",
                "manual_url": "",
                "manual_found": "",
                "manual_relevant": "",
                "audit_status": "",
                "match_confidence": "",
                "reason": "",
                "manual_notes": "",
            }
        ],
    )
    _write_csv(
        manual_path,
        MANUAL_TEMPLATE_FIELDS,
        [
            {
                "company_name": "CGI",
                "manual_title": "Systems Administrator",
                "manual_location": "Montreal",
                "manual_url": "https://cgi.example.com/jobs/1?b=2&a=1",
                "manual_external_job_id": "",
                "manual_source_url": "https://cgi.example.com/jobs",
                "manual_relevant": "true",
                "manual_notes": "",
            }
        ],
    )

    result = compare_audit_files(
        mvp_path=mvp_path,
        manual_path=manual_path,
        output_path=report_path,
    )

    assert result.audit_records[0]["audit_status"] == "matched"
    assert result.audit_records[0]["match_confidence"] == "high"
    assert "normalized URL" in result.audit_records[0]["reason"]


def test_compare_matches_jobs_by_title_company_location_fallback(tmp_path: Path) -> None:
    mvp_path = tmp_path / "mvp.csv"
    manual_path = tmp_path / "manual.csv"
    report_path = tmp_path / "accuracy-audit-report.md"
    _write_csv(
        mvp_path,
        AUDIT_SAMPLE_FIELDS,
        [
            {
                "company_name": "BMO",
                "mvp_title": "Production Support Analyst",
                "mvp_location": "Toronto, Ontario, Canada",
                "mvp_url": "",
                "mvp_external_job_id": "",
                "mvp_ats_type": "",
                "mvp_board_slug": "",
                "mvp_score": "18",
                "mvp_last_seen_at": "2026-06-06T18:00:00Z",
                "manual_title": "",
                "manual_location": "",
                "manual_url": "",
                "manual_found": "",
                "manual_relevant": "",
                "audit_status": "",
                "match_confidence": "",
                "reason": "",
                "manual_notes": "",
            }
        ],
    )
    _write_csv(
        manual_path,
        MANUAL_TEMPLATE_FIELDS,
        [
            {
                "company_name": "BMO",
                "manual_title": "Production Support Analyst",
                "manual_location": "Toronto Ontario Canada",
                "manual_url": "",
                "manual_external_job_id": "",
                "manual_source_url": "https://bmo.example.com/jobs",
                "manual_relevant": "true",
                "manual_notes": "",
            }
        ],
    )

    result = compare_audit_files(
        mvp_path=mvp_path,
        manual_path=manual_path,
        output_path=report_path,
    )

    assert result.audit_records[0]["audit_status"] == "matched"
    assert result.audit_records[0]["match_confidence"] == "medium"


def test_compare_identifies_false_positives_and_missing_manual_jobs(tmp_path: Path) -> None:
    mvp_path = tmp_path / "mvp.csv"
    manual_path = tmp_path / "manual.csv"
    report_path = tmp_path / "accuracy-audit-report.md"
    _write_csv(
        mvp_path,
        AUDIT_SAMPLE_FIELDS,
        [
            {
                "company_name": "RBC",
                "mvp_title": "Search Results",
                "mvp_location": "Toronto",
                "mvp_url": "https://rbc.example.com/search",
                "mvp_external_job_id": "",
                "mvp_ats_type": "",
                "mvp_board_slug": "",
                "mvp_score": "12",
                "mvp_last_seen_at": "2026-06-06T18:00:00Z",
                "manual_title": "",
                "manual_location": "",
                "manual_url": "",
                "manual_found": "false",
                "manual_relevant": "",
                "audit_status": "",
                "match_confidence": "",
                "reason": "",
                "manual_notes": "Not a real posting.",
            }
        ],
    )
    _write_csv(
        manual_path,
        MANUAL_TEMPLATE_FIELDS,
        [
            {
                "company_name": "RBC",
                "manual_title": "Platform Engineer",
                "manual_location": "Toronto",
                "manual_url": "https://rbc.example.com/jobs/platform-engineer-1",
                "manual_external_job_id": "",
                "manual_source_url": "https://rbc.example.com/jobs",
                "manual_relevant": "true",
                "manual_notes": "",
            }
        ],
    )

    result = compare_audit_files(
        mvp_path=mvp_path,
        manual_path=manual_path,
        output_path=report_path,
    )

    statuses = {record["audit_status"] for record in result.audit_records}
    assert "false_positive" in statuses
    assert "missing_from_mvp" in statuses


def test_precision_and_recall_are_calculated_correctly(tmp_path: Path) -> None:
    mvp_path = tmp_path / "mvp.csv"
    manual_path = tmp_path / "manual.csv"
    report_path = tmp_path / "accuracy-audit-report.md"
    _write_csv(
        mvp_path,
        AUDIT_SAMPLE_FIELDS,
        [
            {
                "company_name": "IBM Consulting",
                "mvp_title": "Cloud Engineer",
                "mvp_location": "Toronto",
                "mvp_url": "https://ibm.example.com/jobs/1",
                "mvp_external_job_id": "",
                "mvp_ats_type": "",
                "mvp_board_slug": "",
                "mvp_score": "40",
                "mvp_last_seen_at": "2026-06-06T18:00:00Z",
                "manual_title": "",
                "manual_location": "",
                "manual_url": "",
                "manual_found": "",
                "manual_relevant": "",
                "audit_status": "",
                "match_confidence": "",
                "reason": "",
                "manual_notes": "",
            },
            {
                "company_name": "IBM Consulting",
                "mvp_title": "Filter Results",
                "mvp_location": "Toronto",
                "mvp_url": "https://ibm.example.com/search",
                "mvp_external_job_id": "",
                "mvp_ats_type": "",
                "mvp_board_slug": "",
                "mvp_score": "12",
                "mvp_last_seen_at": "2026-06-06T18:00:00Z",
                "manual_title": "",
                "manual_location": "",
                "manual_url": "",
                "manual_found": "false",
                "manual_relevant": "",
                "audit_status": "",
                "match_confidence": "",
                "reason": "",
                "manual_notes": "",
            },
        ],
    )
    _write_csv(
        manual_path,
        MANUAL_TEMPLATE_FIELDS,
        [
            {
                "company_name": "IBM Consulting",
                "manual_title": "Cloud Engineer",
                "manual_location": "Toronto",
                "manual_url": "https://ibm.example.com/jobs/1",
                "manual_external_job_id": "",
                "manual_source_url": "https://ibm.example.com/jobs",
                "manual_relevant": "true",
                "manual_notes": "",
            },
            {
                "company_name": "IBM Consulting",
                "manual_title": "Platform Engineer",
                "manual_location": "Toronto",
                "manual_url": "https://ibm.example.com/jobs/2",
                "manual_external_job_id": "",
                "manual_source_url": "https://ibm.example.com/jobs",
                "manual_relevant": "true",
                "manual_notes": "",
            },
        ],
    )

    result = compare_audit_files(
        mvp_path=mvp_path,
        manual_path=manual_path,
        output_path=report_path,
    )

    assert result.overall_metrics.matched_count == 1
    assert result.overall_metrics.mvp_saved_count == 2
    assert result.overall_metrics.manual_relevant_count == 2
    assert result.overall_metrics.precision == 0.5
    assert result.overall_metrics.recall == 0.5


def test_divide_by_zero_cases_are_handled_safely(tmp_path: Path) -> None:
    report_path = tmp_path / "accuracy-audit-report.md"
    _write_csv(tmp_path / "mvp.csv", AUDIT_SAMPLE_FIELDS, [])
    _write_csv(tmp_path / "manual.csv", MANUAL_TEMPLATE_FIELDS, [])

    result = compare_audit_files(
        mvp_path=tmp_path / "mvp.csv",
        manual_path=tmp_path / "manual.csv",
        output_path=report_path,
    )

    assert result.overall_metrics.precision == 0.0
    assert result.overall_metrics.recall == 0.0
    assert report_path.exists()


def test_report_generation_includes_per_company_metrics(tmp_path: Path) -> None:
    records = [
        {
            "company_name": "Sun Life",
            "mvp_title": "Cloud Engineer",
            "mvp_location": "Toronto",
            "mvp_url": "https://sunlife.example.com/jobs/1",
            "mvp_external_job_id": "",
            "mvp_ats_type": "",
            "mvp_board_slug": "",
            "mvp_score": "40",
            "mvp_saved_at": "2026-06-06T18:00:00Z",
            "manual_title": "Cloud Engineer",
            "manual_location": "Toronto",
            "manual_url": "https://sunlife.example.com/jobs/1",
            "manual_external_job_id": "",
            "manual_source_url": "https://sunlife.example.com/jobs",
            "manual_found": True,
            "manual_relevant": True,
            "manual_notes": "",
            "audit_status": "matched",
            "match_confidence": "high",
            "reason": "Matched by normalized URL.",
            "audited_by": "manual_audit",
            "audited_at": "2026-06-06T18:00:00Z",
        }
    ]

    metrics = calculate_metrics("Overall", records)
    per_company = [calculate_metrics("Sun Life", records)]
    output_path = tmp_path / "accuracy-audit-report.md"

    from audit.accuracy_audit import write_accuracy_report

    write_accuracy_report(
        output_path,
        audit_records=records,
        overall_metrics=metrics,
        per_company_metrics=per_company,
        companies_audited=["Sun Life"],
        mvp_path=tmp_path / "mvp.csv",
        manual_path=tmp_path / "manual.csv",
    )

    report_text = output_path.read_text(encoding="utf-8")

    assert "## Per-Company Metrics" in report_text
    assert "| Sun Life | 1 | 1 | 1 | 0 | 0 | 0 | 1.000 | 1.000 |" in report_text


def test_build_manual_audit_link_sheet_uses_config_and_export_counts(tmp_path: Path) -> None:
    config_path = tmp_path / "companies.yaml"
    config_path.write_text(
        """
companies:
  - name: TD
    careers_url: https://careers.td.com/
  - name: RBC
    careers_url: https://jobs.rbc.com/en
""",
        encoding="utf-8",
    )
    _, connection = _seed_company_and_job(tmp_path)
    audit_sample_path = tmp_path / "accuracy-audit-sample.csv"
    manual_template_path = tmp_path / "manual-job-audit-template.csv"
    export_audit_sample(
        connection,
        output_path=audit_sample_path,
        companies=["TD"],
        status="new",
    )
    create_manual_template(
        output_path=manual_template_path,
        companies=["TD", "RBC"],
    )

    output_path = tmp_path / "manual-audit-link-sheet.csv"
    rows = build_manual_audit_link_sheet(
        connection,
        output_path=output_path,
        companies_path=config_path,
        audit_sample_path=audit_sample_path,
        manual_template_path=manual_template_path,
        companies=["TD", "RBC"],
    )

    assert len(rows) == 2
    exported = _read_csv(output_path)
    assert exported[0]["configured_careers_url"] == "https://careers.td.com/"
    assert exported[0]["audit_sample_rows"] == "1"


def test_validate_files_reports_missing_required_column(tmp_path: Path) -> None:
    mvp_path = tmp_path / "mvp.csv"
    manual_path = tmp_path / "manual.csv"
    _write_csv(
        mvp_path,
        [field for field in AUDIT_SAMPLE_FIELDS if field != "mvp_url"],
        [
            {
                key: ""
                for key in AUDIT_SAMPLE_FIELDS
                if key != "mvp_url"
            }
        ],
    )
    _write_csv(manual_path, MANUAL_TEMPLATE_FIELDS, [])

    result = validate_audit_files(mvp_path=mvp_path, manual_path=manual_path)

    assert result.is_valid is False
    assert any("missing required columns" in error.lower() for error in result.errors)


def test_validate_files_reports_invalid_audit_status(tmp_path: Path) -> None:
    mvp_path = tmp_path / "mvp.csv"
    manual_path = tmp_path / "manual.csv"
    row = {field: "" for field in AUDIT_SAMPLE_FIELDS}
    row["company_name"] = "TD"
    row["audit_status"] = "wrong_value"
    _write_csv(mvp_path, AUDIT_SAMPLE_FIELDS, [row])
    _write_csv(manual_path, MANUAL_TEMPLATE_FIELDS, [])

    result = validate_audit_files(mvp_path=mvp_path, manual_path=manual_path)

    assert result.is_valid is False
    assert any("invalid audit_status" in error for error in result.errors)


def test_validate_files_reports_duplicate_manual_rows(tmp_path: Path) -> None:
    mvp_path = tmp_path / "mvp.csv"
    manual_path = tmp_path / "manual.csv"
    _write_csv(mvp_path, AUDIT_SAMPLE_FIELDS, [])
    _write_csv(
        manual_path,
        MANUAL_TEMPLATE_FIELDS,
        [
            {
                "company_name": "TD",
                "manual_title": "Cloud Engineer",
                "manual_location": "Toronto",
                "manual_url": "https://careers.td.com/jobs/1",
                "manual_external_job_id": "",
                "manual_source_url": "https://careers.td.com/",
                "manual_relevant": "true",
                "manual_notes": "",
            },
            {
                "company_name": "TD",
                "manual_title": "Cloud Engineer",
                "manual_location": "Toronto",
                "manual_url": "https://careers.td.com/jobs/1",
                "manual_external_job_id": "",
                "manual_source_url": "https://careers.td.com/",
                "manual_relevant": "true",
                "manual_notes": "",
            },
        ],
    )

    result = validate_audit_files(mvp_path=mvp_path, manual_path=manual_path)

    assert result.is_valid is False
    assert any("duplicates an earlier" in error for error in result.errors)


def test_validate_files_passes_for_valid_files(tmp_path: Path) -> None:
    mvp_path = tmp_path / "mvp.csv"
    manual_path = tmp_path / "manual.csv"
    mvp_row = {field: "" for field in AUDIT_SAMPLE_FIELDS}
    mvp_row["company_name"] = "TD"
    mvp_row["mvp_title"] = "Cloud Engineer"
    mvp_row["mvp_url"] = "https://careers.td.com/jobs/1"
    mvp_row["manual_found"] = "true"
    mvp_row["manual_relevant"] = "true"
    mvp_row["audit_status"] = "matched"
    mvp_row["match_confidence"] = "high"
    _write_csv(mvp_path, AUDIT_SAMPLE_FIELDS, [mvp_row])
    _write_csv(
        manual_path,
        MANUAL_TEMPLATE_FIELDS,
        [
            {
                "company_name": "TD",
                "manual_title": "Cloud Engineer",
                "manual_location": "Toronto",
                "manual_url": "https://careers.td.com/jobs/1",
                "manual_external_job_id": "",
                "manual_source_url": "https://careers.td.com/",
                "manual_relevant": "true",
                "manual_notes": "",
            }
        ],
    )

    result = validate_audit_files(mvp_path=mvp_path, manual_path=manual_path)

    assert result.is_valid is True
    assert result.errors == []


def test_build_company_audit_pack_creates_markdown_with_company_source_and_jobs(
    tmp_path: Path,
) -> None:
    _, connection = _seed_company_and_job(tmp_path)
    config_path = tmp_path / "companies.yaml"
    _write_companies_config(config_path)
    markdown_path = tmp_path / "docs" / "audits" / "TD-audit-pack.md"
    mvp_output_path = tmp_path / "data" / "exports" / "audits" / "TD-mvp-sample.csv"
    manual_output_path = (
        tmp_path / "data" / "exports" / "audits" / "TD-manual-template.csv"
    )

    result = build_company_audit_pack(
        connection,
        company_name="TD",
        companies_path=config_path,
        markdown_output_path=markdown_path,
        mvp_output_path=mvp_output_path,
        manual_output_path=manual_output_path,
        limit_per_company=10,
        include_recent_days=14,
        status="new",
    )

    content = markdown_path.read_text(encoding="utf-8")

    assert result.company_name == "TD"
    assert markdown_path.exists()
    assert mvp_output_path.exists()
    assert manual_output_path.exists()
    assert "Careers URL: https://careers.td.com/jobs" in content
    assert "Cloud Engineer" in content
    assert "[Open job](https://careers.td.com/jobs/cloud-engineer-123)" in content
    assert "## Jobs Found Manually That MVP Missed" in content


def test_company_pack_command_creates_markdown_file(tmp_path: Path, monkeypatch) -> None:
    db_path, _ = _seed_company_and_job(tmp_path)
    config_path = tmp_path / "companies.yaml"
    _write_companies_config(config_path)
    project_root = tmp_path / "project-root"
    project_root.mkdir(parents=True, exist_ok=True)
    output_path = project_root / "docs" / "audits" / "TD-audit-pack.md"

    monkeypatch.setattr(cli_main, "DATABASE_PATH", db_path)
    monkeypatch.setattr(cli_main, "COMPANIES_CONFIG_PATH", config_path)
    monkeypatch.setattr(cli_main, "PROJECT_ROOT", project_root)

    exit_code = cli_main.main(
        [
            "audit",
            "company-pack",
            "--company",
            "TD",
            "--output",
            str(output_path),
        ]
    )

    content = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert "# TD Manual Accuracy Audit" in content
    assert "## Manual Website Check" in content


def test_company_pack_command_reports_missing_company_clearly(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path, _ = _seed_company_and_job(tmp_path)
    config_path = tmp_path / "companies.yaml"
    _write_companies_config(config_path)
    project_root = tmp_path / "project-root"
    project_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(cli_main, "DATABASE_PATH", db_path)
    monkeypatch.setattr(cli_main, "COMPANIES_CONFIG_PATH", config_path)
    monkeypatch.setattr(cli_main, "PROJECT_ROOT", project_root)

    try:
        cli_main.main(
            [
                "audit",
                "company-pack",
                "--company",
                "Missing Company",
            ]
        )
    except ValueError as error:
        assert "Company not found in config/companies.yaml" in str(error)
    else:
        raise AssertionError("Expected a clear missing-company error.")


def test_write_company_collection_diagnostic_exports_relevant_and_rejected_candidates(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "docs" / "audits" / "TD-collection-diagnostic.md"
    scored_candidates_path = tmp_path / "data" / "exports" / "audits" / "TD-scored-candidates.csv"
    company = {
        "name": "TD",
        "careers_url": "https://careers.td.com/jobs",
        "source_mode": "human_in_loop",
        "ats_hint": "workday",
    }
    collection_result = {
        "starting_url": "https://careers.td.com/jobs",
        "final_url": "https://careers.td.com/jobs",
        "source_mode": "human_in_loop",
        "ats_type": "workday",
        "location_scope_used": True,
        "location_scope": ["Canada", "Toronto"],
        "location_queries": ["Canada (URL filter)"],
        "location_filter_method": "url_filter",
        "pagination_detected": True,
        "max_pages_per_source": 10,
        "pages_visited": ["https://careers.td.com/jobs"],
        "jobs_extracted_per_page": [2],
        "pagination_stop_reason": "completed",
        "cookie_dismissed": "#truste-consent-button",
        "language_prompt_action": ".geo-btn-secondary-cancel",
        "jobs_discovered": 2,
        "jobs_scored": 2,
        "jobs_relevant": 1,
        "candidate_jobs": [
            {
                "company_name": "TD",
                "title": "Lead Platform Engineer",
                "location": "Toronto, Ontario, Canada",
                "job_url": "https://careers.td.com/jobs/lead-platform-engineer",
            },
            {
                "company_name": "TD",
                "title": "Software Engineer II, Salesforce",
                "location": "Toronto, Ontario, Canada",
                "job_url": "https://careers.td.com/jobs/software-engineer-salesforce",
            },
        ],
        "scored_jobs": [
            {
                "company_name": "TD",
                "title": "Lead Platform Engineer",
                "location": "Toronto, Ontario, Canada",
                "job_url": "https://careers.td.com/jobs/lead-platform-engineer",
                "match_score": 53,
                "match_reasons": [
                    "title matches target role: Platform Engineer",
                    "location signals: Toronto, Ontario, Canada",
                ],
                "risk_flags": [],
                "source_mode": "human_in_loop",
            },
            {
                "company_name": "TD",
                "title": "Software Engineer II, Salesforce",
                "location": "Toronto, Ontario, Canada",
                "job_url": "https://careers.td.com/jobs/software-engineer-salesforce",
                "match_score": 8,
                "match_reasons": ["location signals: Toronto, Ontario, Canada"],
                "risk_flags": [],
                "source_mode": "human_in_loop",
            },
        ],
        "relevant_jobs": [
            {
                "company_name": "TD",
                "title": "Lead Platform Engineer",
                "location": "Toronto, Ontario, Canada",
                "job_url": "https://careers.td.com/jobs/lead-platform-engineer",
                "match_score": 53,
            }
        ],
    }

    write_company_collection_diagnostic(
        output_path=output_path,
        company=company,
        collection_result=collection_result,
        scored_candidates_output_path=scored_candidates_path,
        manual_expected_jobs=[
            {
                "job_url": "https://careers.td.com/jobs/lead-platform-engineer",
                "title": "Lead Platform Engineer",
            }
        ],
    )

    content = output_path.read_text(encoding="utf-8")
    exported_rows = _read_csv(scored_candidates_path)

    assert "## Scored Candidates" in content
    assert "## Rejected But Interesting Jobs" in content
    assert "- Cookie banner action: #truste-consent-button" in content
    assert "- Language prompt action: .geo-btn-secondary-cancel" in content
    assert "- Jobs extracted per page: [2]" in content
    assert "- Matching manual IBM jobIds found: none" in content
    assert "Software Engineer II, Salesforce" in content
    assert {row["is_relevant"] for row in exported_rows} == {"true", "false"}


def test_find_job_for_score_explanation_can_use_scored_candidates_export(tmp_path: Path) -> None:
    db_path, connection = _seed_company_and_job(tmp_path)
    assert db_path.exists()
    scored_candidates_path = tmp_path / "TD-scored-candidates.csv"
    _write_csv(
        scored_candidates_path,
        [
            "company",
            "title",
            "location",
            "url",
            "score",
            "is_relevant",
            "matched_terms",
            "reason",
            "match_reasons",
            "risk_flags",
            "description",
            "source_mode",
        ],
        [
            {
                "company": "TD",
                "title": "Software Engineer II, Salesforce",
                "location": "Toronto, Ontario, Canada",
                "url": "https://careers.td.com/jobs/software-engineer-salesforce",
                "score": "8",
                "is_relevant": "false",
                "matched_terms": "",
                "reason": "Rejected because the score came from weak or location-only signals.",
                "match_reasons": "location signals: Toronto, Ontario, Canada",
                "risk_flags": "",
                "description": "",
                "source_mode": "human_in_loop",
            }
        ],
    )

    job, source = find_job_for_score_explanation(
        connection,
        company_name="TD",
        title="Software Engineer II, Salesforce",
        scored_candidates_path=scored_candidates_path,
        include_rejected=True,
    )

    assert source == "scored_candidates_export"
    assert job["title"] == "Software Engineer II, Salesforce"


def test_explain_score_command_creates_markdown_file(tmp_path: Path, monkeypatch) -> None:
    db_path, _ = _seed_company_and_job(tmp_path)
    config_path = tmp_path / "companies.yaml"
    _write_companies_config(config_path)
    project_root = tmp_path / "project-root"
    project_root.mkdir(parents=True, exist_ok=True)
    output_path = project_root / "docs" / "audits" / "TD-score-explanation.md"

    monkeypatch.setattr(cli_main, "DATABASE_PATH", db_path)
    monkeypatch.setattr(cli_main, "COMPANIES_CONFIG_PATH", config_path)
    monkeypatch.setattr(cli_main, "PROJECT_ROOT", project_root)

    exit_code = cli_main.main(
        [
            "audit",
            "explain-score",
            "--company",
            "TD",
            "--title",
            "Cloud Engineer",
            "--output",
            str(output_path),
        ]
    )

    content = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert output_path.exists()
    assert "# Cloud Engineer Score Explanation" in content
    assert "## Score Result" in content
    assert "Careers URL" not in content


def test_load_manual_expected_jobs_reads_structured_fixture() -> None:
    companies = load_manual_expected_jobs(AUDIT_FIXTURE_PATH)

    assert [item["company_name"] for item in companies] == [
        "TD",
        "IBM Consulting",
        "Sun Life",
    ]
    assert len(companies[0]["expected_jobs"]) == 4


def test_ibm_url_identity_extracts_job_id() -> None:
    identity = _url_identity(
        "https://careers.ibm.com/en_US/careers/JobDetail?jobId=92913&source=WEB_Search_NA"
    )

    assert identity["ibm_job_id"] == "92913"


def test_compare_manual_expected_urls_matches_workday_id_despite_query_difference(
    tmp_path: Path,
) -> None:
    _, connection = _seed_company_and_job(tmp_path)
    upsert_job_record(
        connection,
        {
            "company_name": "TD",
            "title": "Lead Platform Engineer, TD Securities",
            "location": "Toronto, Ontario, Canada",
            "job_url": (
                "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/"
                "Lead-Platform-Engineer--TD-Securities_R_1491997"
            ),
            "apply_url": "",
            "source_name": "workday",
            "source_mode": "human_in_loop",
            "description": "Platform engineering role.",
            "date_posted": "2026-06-06",
            "match_score": 45,
            "match_reasons": ["title matches target role: Platform Engineer"],
            "risk_flags": [],
            "status": "new",
        },
    )
    fixture = [
        {
            "company_name": "TD",
            "manual_career_page": "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers",
            "manual_filter_used": "Canada",
            "pages_checked": "first 10",
            "expected_jobs": [
                {
                    "job_url": (
                        "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/"
                        "Toronto-Ontario/Lead-Platform-Engineer--TD-Securities_R_1491997"
                        "?locationCountry=a30a87ed25634629aa6c3958aa2b91ea"
                    ),
                    "title": "Lead Platform Engineer, TD Securities",
                    "notes": "",
                }
            ],
        }
    ]

    result = compare_manual_expected_urls(
        connection,
        companies=fixture,
        scored_candidates_dir=tmp_path,
    )

    assert result["records"][0]["status"] == "saved_by_mvp"
    assert result["records"][0]["matched_title"] == "Lead Platform Engineer, TD Securities"


def test_compare_manual_expected_urls_matches_sunlife_jr_id_despite_query_difference(
    tmp_path: Path,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    export_dir = tmp_path
    _write_csv(
        export_dir / "Sun-Life-scored-candidates.csv",
        [
            "company",
            "title",
            "location",
            "url",
            "score",
            "is_relevant",
            "relevance_tier",
            "matched_terms",
            "reason",
            "match_reasons",
            "risk_flags",
            "rejection_reason",
            "description",
            "source_mode",
        ],
        [
            {
                "company": "Sun Life",
                "title": "M365 Productivity & Collaboration Engineer",
                "location": "Waterloo, Ontario, Canada",
                "url": (
                    "https://sunlife.wd3.myworkdayjobs.com/en-US/Experienced-Jobs/job/"
                    "Waterloo-Ontario/M365-Productivity---Collaboration-Engineer_JR00124191"
                ),
                "score": "0",
                "is_relevant": "false",
                "relevance_tier": "not_relevant",
                "matched_terms": "",
                "reason": "Rejected because the job did not match the current target role profile.",
                "match_reasons": "",
                "risk_flags": "",
                "rejection_reason": (
                    "Rejected because the job did not match the current target role profile."
                ),
                "description": "",
                "source_mode": "human_in_loop",
            }
        ],
    )
    fixture = [
        {
            "company_name": "Sun Life",
            "manual_career_page": "https://sunlife.wd3.myworkdayjobs.com/Experienced-Jobs",
            "manual_filter_used": "Canada",
            "pages_checked": "first 10",
            "expected_jobs": [
                {
                    "job_url": (
                        "https://sunlife.wd3.myworkdayjobs.com/en-US/Experienced-Jobs/job/"
                        "Waterloo-Ontario/M365-Productivity---Collaboration-Engineer_JR00124191"
                        "?Location_Country=a30a87ed25634629aa6c3958aa2b91ea"
                    ),
                    "title": "M365 Productivity & Collaboration Engineer",
                    "notes": "",
                }
            ],
        }
    ]

    result = compare_manual_expected_urls(
        connection,
        companies=fixture,
        scored_candidates_dir=export_dir,
    )

    assert result["records"][0]["matched_title"] == "M365 Productivity & Collaboration Engineer"
    assert result["records"][0]["status"] == "outside_scope"


def test_compare_manual_expected_urls_matches_ibm_job_id(
    tmp_path: Path,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    _write_csv(
        tmp_path / "IBM-Consulting-scored-candidates.csv",
        [
            "company",
            "title",
            "location",
            "url",
            "score",
            "is_relevant",
            "relevance_tier",
            "matched_terms",
            "reason",
            "match_reasons",
            "risk_flags",
            "rejection_reason",
            "description",
            "source_mode",
        ],
        [
            {
                "company": "IBM Consulting",
                "title": "Technical Consultant",
                "location": "Toronto, Ontario, Canada",
                "url": (
                    "https://careers.ibm.com/en_US/careers/JobDetail?jobId=92913"
                ),
                "score": "24",
                "is_relevant": "true",
                "relevance_tier": "adjacent_customer_facing_technical_fit",
                "matched_terms": "Technical Consultant",
                "reason": (
                    "Saved as an adjacent customer-facing technical fit because the "
                    "role matched the secondary relevance bucket."
                ),
                "match_reasons": "adjacent customer-facing technical fit: Technical Consultant",
                "risk_flags": "",
                "rejection_reason": "",
                "description": "Technical consultant role.",
                "source_mode": "browser_allowed",
            }
        ],
    )
    fixture = [
        {
            "company_name": "IBM Consulting",
            "manual_career_page": "https://www.ibm.com/careers/search",
            "manual_filter_used": "Canada",
            "pages_checked": "first 10",
            "expected_jobs": [
                {
                    "job_url": (
                        "https://careers.ibm.com/en_US/careers/JobDetail?jobId=92913&source=WEB_Search_NA"
                    ),
                    "title": "",
                    "notes": "",
                }
            ],
        }
    ]

    result = compare_manual_expected_urls(
        connection,
        companies=fixture,
        scored_candidates_dir=tmp_path,
    )

    assert result["records"][0]["matched_title"] == "Technical Consultant"
    assert result["records"][0]["status"] == "extracted_and_relevant"


def test_compare_manual_expected_urls_distinguishes_saved_rejected_and_missed(
    tmp_path: Path,
) -> None:
    connection = initialize_database(tmp_path / "job_discovery.db")
    upsert_companies(
        connection,
        [
            {
                "name": "TD",
                "sector": "Banking & Capital Markets",
                "category": "Bank/Market",
                "careers_url": "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers",
                "source_mode": "human_in_loop",
            }
        ],
    )
    upsert_job_record(
        connection,
        {
            "company_name": "TD",
            "title": "Lead Platform Engineer, TD Securities",
            "location": "Toronto, Ontario, Canada",
            "job_url": (
                "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/"
                "Lead-Platform-Engineer--TD-Securities_R_1491997"
            ),
            "apply_url": "",
            "source_name": "workday",
            "source_mode": "human_in_loop",
            "description": "Platform engineering role.",
            "date_posted": "2026-06-06",
            "match_score": 45,
            "match_reasons": ["title matches target role: Platform Engineer"],
            "risk_flags": [],
            "status": "new",
        },
    )
    _write_csv(
        tmp_path / "TD-scored-candidates.csv",
        [
            "company",
            "title",
            "location",
            "url",
            "score",
            "is_relevant",
            "relevance_tier",
            "matched_terms",
            "reason",
            "match_reasons",
            "risk_flags",
            "rejection_reason",
            "description",
            "source_mode",
        ],
        [
            {
                "company": "TD",
                "title": "Software Engineer II, Salesforce",
                "location": "Toronto, Ontario, Canada",
                "url": (
                    "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/"
                    "Software-Engineer-II--Salesforce_R_1486443"
                ),
                "score": "3",
                "is_relevant": "false",
                "relevance_tier": "not_relevant",
                "matched_terms": "Toronto",
                "reason": "Rejected because the score came from weak or location-only signals.",
                "match_reasons": "location signals: Toronto",
                "risk_flags": "",
                "rejection_reason": (
                    "Rejected because the score came from weak or location-only signals."
                ),
                "description": "",
                "source_mode": "human_in_loop",
            }
        ],
    )
    fixture = [
        {
            "company_name": "TD",
            "manual_career_page": "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers",
            "manual_filter_used": "Canada",
            "pages_checked": "first 10",
            "expected_jobs": [
                {
                    "job_url": (
                        "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/"
                        "Lead-Platform-Engineer--TD-Securities_R_1491997"
                    ),
                    "title": "Lead Platform Engineer, TD Securities",
                    "notes": "",
                },
                {
                    "job_url": (
                        "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/"
                        "Software-Engineer-II--Salesforce_R_1486443"
                    ),
                    "title": "Software Engineer II, Salesforce",
                    "notes": "",
                },
                {
                    "job_url": (
                        "https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers/job/Toronto-Ontario/"
                        "IT-Build-Analyst-II---Onsite-AV-Support_R_1493452"
                    ),
                    "title": "IT Build Analyst II - Onsite AV Support",
                    "notes": "",
                },
            ],
        }
    ]

    result = compare_manual_expected_urls(
        connection,
        companies=fixture,
        scored_candidates_dir=tmp_path,
    )

    statuses = [record["status"] for record in result["records"]]

    assert statuses == [
        "saved_by_mvp",
        "extracted_but_rejected_by_scoring",
        "missed_by_collection",
    ]
