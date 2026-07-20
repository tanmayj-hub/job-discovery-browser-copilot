from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

import pytest

from review.current_review_slice import (
    CURRENT_SLICE_COLUMNS,
    backup_review_file,
    load_current_review_slice,
    update_current_review_decision,
    write_current_review_slice,
)


def _write_job_export(
    path: Path,
    *,
    company_name: str,
    title: str,
    location: str = "Toronto, Ontario, Canada",
    status: str = "new",
    job_url: str | None = None,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "company_name",
                "title",
                "location",
                "job_url",
                "description",
                "date_posted",
                "match_score",
                "match_reasons",
                "risk_flags",
                "status",
                "created_at",
                "last_updated_at",
                "first_seen_at",
                "last_seen_at",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id": "job-1",
                "company_name": company_name,
                "title": title,
                "location": location,
                "job_url": job_url or f"https://jobs.example.com/{company_name.lower()}/1",
                "description": "Cloud and Terraform engineering role.",
                "date_posted": "2026-07-20T00:00:00.000+0000",
                "match_score": "55",
                "match_reasons": "['title matches target role: Cloud Engineer']",
                "risk_flags": "['negative signal: Senior']",
                "status": status,
                "created_at": "2026-07-20 20:00:00",
                "last_updated_at": "2026-07-20T20:00:00Z",
                "first_seen_at": "2026-07-20T20:00:00Z",
                "last_seen_at": "2026-07-20T20:00:00Z",
            }
        )


def _write_slice(tmp_path: Path, *, generated_at: datetime) -> tuple[dict[str, object], Path]:
    job_export = tmp_path / f"rbc-{generated_at.minute}.csv"
    _write_job_export(job_export, company_name="RBC", title="Cloud Engineer")
    manifest_path = tmp_path / "current-review-slice.json"
    manifest = write_current_review_slice(
        job_export_paths=[job_export],
        run_records=[
            {
                "company_name": "RBC",
                "last_success_at": "2026-07-20T20:00:00Z",
            }
        ],
        output_dir=tmp_path / "review",
        manifest_path=manifest_path,
        generated_at=generated_at,
    )
    return manifest, manifest_path


def test_current_review_slice_has_product_fields_and_stable_key(tmp_path: Path) -> None:
    manifest, manifest_path = _write_slice(
        tmp_path,
        generated_at=datetime(2026, 7, 20, 20, 1, tzinfo=UTC),
    )
    _, rows = load_current_review_slice(manifest_path)

    assert manifest["review_rows"] == 1
    assert set(CURRENT_SLICE_COLUMNS).issubset(rows[0])
    assert rows[0]["job_key"] == rows[0]["job_url"]
    assert rows[0]["posting_date"] == "20 Jul 2026"
    assert rows[0]["risk_flags"] == "negative signal: Senior"
    assert rows[0]["match_reasons"] == "title matches target role: Cloud Engineer"
    assert rows[0]["change_type"] == "New"


def test_current_review_slice_excludes_rejected_jobs_and_other_companies(tmp_path: Path) -> None:
    rbc_export = tmp_path / "rbc.csv"
    rejected_export = tmp_path / "rejected.csv"
    _write_job_export(rbc_export, company_name="RBC", title="Cloud Engineer")
    _write_job_export(
        rejected_export,
        company_name="Other Co",
        title="Other Cloud Engineer",
    )
    manifest_path = tmp_path / "current-review-slice.json"
    write_current_review_slice(
        job_export_paths=[rbc_export, rejected_export],
        run_records=[{"company_name": "RBC"}],
        output_dir=tmp_path / "review",
        manifest_path=manifest_path,
        generated_at=datetime(2026, 7, 20, 20, 2, tzinfo=UTC),
    )
    _, rows = load_current_review_slice(manifest_path)

    assert [row["company"] for row in rows] == ["RBC"]


def test_current_review_slice_cleans_contaminated_and_missing_locations(tmp_path: Path) -> None:
    job_export = tmp_path / "scotia.csv"
    _write_job_export(
        job_export,
        company_name="Scotiabank",
        title="Systems Administrator",
        location="Systems Administrator Systems Administrator Toronto, ON,",
    )
    manifest_path = tmp_path / "current-review-slice.json"
    write_current_review_slice(
        job_export_paths=[job_export],
        run_records=[],
        output_dir=tmp_path / "review",
        manifest_path=manifest_path,
        generated_at=datetime(2026, 7, 20, 20, 3, tzinfo=UTC),
    )
    _, rows = load_current_review_slice(manifest_path)

    assert rows[0]["location"] == "Toronto, ON, Canada"


def test_current_review_slice_keeps_long_titles_and_labels_missing_locations(
    tmp_path: Path,
) -> None:
    job_export = tmp_path / "long-title.csv"
    long_title = "Senior Cloud Platform Reliability Engineer for Enterprise Technology Services"
    _write_job_export(
        job_export,
        company_name="RBC",
        title=long_title,
        location="",
    )
    manifest_path = tmp_path / "current-review-slice.json"
    write_current_review_slice(
        job_export_paths=[job_export],
        run_records=[{"company_name": "RBC"}],
        output_dir=tmp_path / "review",
        manifest_path=manifest_path,
        generated_at=datetime(2026, 7, 20, 20, 3, tzinfo=UTC),
    )
    _, rows = load_current_review_slice(manifest_path)

    assert rows[0]["title"] == long_title
    assert rows[0]["location"] == "Location not listed"


def test_decisions_persist_by_stable_job_key_and_carry_forward(tmp_path: Path) -> None:
    _, manifest_path = _write_slice(
        tmp_path,
        generated_at=datetime(2026, 7, 20, 20, 4, tzinfo=UTC),
    )
    _, initial_rows = load_current_review_slice(manifest_path)
    job_key = initial_rows[0]["job_key"]

    assert update_current_review_decision(
        manifest_path=manifest_path,
        job_key=job_key,
        decision="useful",
        notes="Apply this week.",
    )
    _, updated_rows = load_current_review_slice(manifest_path)
    assert updated_rows[0]["user_decision"] == "useful"

    job_export = tmp_path / "refresh.csv"
    _write_job_export(job_export, company_name="RBC", title="Cloud Engineer")
    write_current_review_slice(
        job_export_paths=[job_export],
        run_records=[],
        output_dir=tmp_path / "review",
        manifest_path=manifest_path,
        generated_at=datetime(2026, 7, 20, 20, 5, tzinfo=UTC),
    )
    _, refreshed_rows = load_current_review_slice(manifest_path)

    assert refreshed_rows[0]["user_decision"] == "useful"
    assert refreshed_rows[0]["user_notes"] == "Apply this week."
    assert refreshed_rows[0]["review_state"] == "Previously reviewed"


def test_review_backup_preserves_user_decisions_before_regeneration(tmp_path: Path) -> None:
    _, manifest_path = _write_slice(
        tmp_path,
        generated_at=datetime(2026, 7, 20, 20, 4, tzinfo=UTC),
    )
    _, rows = load_current_review_slice(manifest_path)
    assert update_current_review_decision(
        manifest_path=manifest_path,
        job_key=rows[0]["job_key"],
        decision="maybe",
        notes="Check location before applying.",
    )
    manifest, _ = load_current_review_slice(manifest_path)
    backup_path = tmp_path / "backups" / "reviewed.csv"

    backup_review_file(Path(str(manifest["working_path"])), backup_path)
    write_current_review_slice(
        job_export_paths=[tmp_path / "rbc-4.csv"],
        run_records=[],
        output_dir=tmp_path / "review",
        manifest_path=manifest_path,
        generated_at=datetime(2026, 7, 20, 20, 5, tzinfo=UTC),
    )

    backup_rows = list(csv.DictReader(backup_path.open(encoding="utf-8", newline="")))
    assert backup_rows[0]["user_decision"] == "maybe"
    assert backup_rows[0]["user_notes"] == "Check location before applying."


def test_regeneration_can_use_verified_backup_as_the_decision_source(tmp_path: Path) -> None:
    _, manifest_path = _write_slice(
        tmp_path,
        generated_at=datetime(2026, 7, 20, 20, 4, tzinfo=UTC),
    )
    _, rows = load_current_review_slice(manifest_path)
    assert update_current_review_decision(
        manifest_path=manifest_path,
        job_key=rows[0]["job_key"],
        decision="useful",
        notes="Preserve this review.",
    )
    manifest, _ = load_current_review_slice(manifest_path)
    backup_path = tmp_path / "backups" / "reviewed.csv"
    backup_review_file(Path(str(manifest["working_path"])), backup_path)

    write_current_review_slice(
        job_export_paths=[tmp_path / "rbc-4.csv"],
        run_records=[],
        output_dir=tmp_path / "review",
        manifest_path=manifest_path,
        generated_at=datetime(2026, 7, 20, 20, 5, tzinfo=UTC),
        previous_working_path=backup_path,
    )
    _, regenerated_rows = load_current_review_slice(manifest_path)

    assert regenerated_rows[0]["user_decision"] == "useful"
    assert regenerated_rows[0]["user_notes"] == "Preserve this review."


def test_empty_working_file_is_not_overwritten_during_dashboard_save(tmp_path: Path) -> None:
    _, manifest_path = _write_slice(
        tmp_path,
        generated_at=datetime(2026, 7, 20, 20, 6, tzinfo=UTC),
    )
    manifest, rows = load_current_review_slice(manifest_path)
    working_path = Path(str(manifest["working_path"]))
    _write_csv = working_path.write_text(
        ",".join(CURRENT_SLICE_COLUMNS) + "\n",
        encoding="utf-8",
    )
    assert _write_csv > 0
    before = working_path.read_bytes()

    with pytest.raises(OSError, match="unexpectedly empty"):
        update_current_review_decision(
            manifest_path=manifest_path,
            job_key=rows[0]["job_key"],
            decision="useful",
            notes="Do not overwrite.",
        )

    assert working_path.read_bytes() == before


def test_decision_values_are_validated(tmp_path: Path) -> None:
    _, manifest_path = _write_slice(
        tmp_path,
        generated_at=datetime(2026, 7, 20, 20, 6, tzinfo=UTC),
    )
    _, rows = load_current_review_slice(manifest_path)

    with pytest.raises(ValueError, match="Unsupported user decision"):
        update_current_review_decision(
            manifest_path=manifest_path,
            job_key=rows[0]["job_key"],
            decision="invalid",
            notes="",
        )
