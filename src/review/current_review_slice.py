"""Persist and load a narrow, current-run job-review slice.

The slice is intentionally separate from long-lived SQLite history. It creates an
immutable export plus a separately editable working copy, so users can review fresh
live results without losing earlier runs or their decisions.
"""

from __future__ import annotations

import ast
import csv
import json
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from processing.score import score_job
from review.saved_job_review import USER_DECISION_VALUES

DEFAULT_CURRENT_SLICE_MANIFEST_PATH = Path("data/exports/review/current-review-slice.json")
CURRENT_SLICE_COLUMNS = [
    "job_key",
    "company",
    "title",
    "location",
    "posting_date",
    "relevance_tier",
    "score",
    "risk_flags",
    "job_url",
    "match_reasons",
    "first_seen",
    "last_seen",
    "change_type",
    "previous_score",
    "previous_relevance_tier",
    "review_state",
    "user_decision",
    "user_notes",
]
_CANADIAN_PROVINCE_CODES = {
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NS",
    "NT",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Atomically replace a review CSV so dashboard reruns cannot leave a partial file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    try:
        with temporary_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CURRENT_SLICE_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def backup_review_file(source_path: Path, backup_path: Path) -> Path:
    """Create a verified immutable copy before replacing a working review slice."""

    if not source_path.exists():
        raise FileNotFoundError(f"Review working file does not exist: {source_path}")
    if backup_path.exists():
        raise FileExistsError(f"Review backup already exists: {backup_path}")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, backup_path)
    if source_path.read_bytes() != backup_path.read_bytes():
        raise OSError("Review backup did not match its source file.")
    return backup_path


def _parse_timestamp(value: object) -> datetime | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    normalized = text.replace(" ", "T").replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _format_posting_date(value: object) -> str:
    timestamp = _parse_timestamp(value)
    return timestamp.strftime("%d %b %Y") if timestamp else "Posting date not listed"


def _clean_location(value: object, *, title: str) -> str:
    """Correct clearly contaminated board locations without altering source history."""

    location = " ".join(str(value or "").split())
    normalized_title = " ".join(title.split()).lower()
    if not location:
        return "Location not listed"

    # Some public boards repeat the title before an otherwise valid city/province value.
    # Remove that known contamination only in the disposable review presentation layer.
    location_without_title = re.sub(re.escape(title), "", location, flags=re.IGNORECASE)
    location_without_title = " ".join(location_without_title.split())
    city_matches = re.findall(
        r"([A-Za-z][A-Za-z .'-]{1,60}),\s*([A-Z]{2})\b",
        location_without_title,
    )
    if city_matches:
        city, province = city_matches[-1]
        if province in _CANADIAN_PROVINCE_CODES:
            return f"{city.strip()}, {province}, Canada"

    normalized_location = location.lower()
    if normalized_location == normalized_title or normalized_location.count(normalized_title) >= 2:
        return "Location not listed"
    if len(location) > 120 or normalized_title in normalized_location:
        return "Location not listed"
    return location


def _format_list_text(value: object) -> str:
    """Make serialized list fields readable in a human review file."""

    if isinstance(value, (list, tuple, set)):
        return " | ".join(str(item).strip() for item in value if str(item).strip())
    text = " ".join(str(value or "").split())
    if not text or text == "[]":
        return ""
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return text
    if isinstance(parsed, list):
        return " | ".join(str(item).strip() for item in parsed if str(item).strip())
    return str(parsed).strip()


def _run_record_map(run_records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("company_name") or "").strip(): record
        for record in run_records
        if str(record.get("company_name") or "").strip()
    }


def _change_type(job: dict[str, str], run_record: dict[str, Any]) -> str:
    run_time = _parse_timestamp(run_record.get("last_success_at"))
    if run_time is None:
        return "Current run"
    created_at = _parse_timestamp(job.get("created_at"))
    updated_at = _parse_timestamp(job.get("last_updated_at") or job.get("updated_at"))
    tolerance = timedelta(seconds=2)
    if created_at is not None and abs(created_at - run_time) <= tolerance:
        return "New"
    if updated_at is not None and abs(updated_at - run_time) <= tolerance:
        return "Updated"
    return "Existing"


def _is_eligible_for_review(job: dict[str, str]) -> bool:
    status = str(job.get("status") or "new").strip().lower()
    relevance_tier = str(job.get("relevance_tier") or "").strip().lower()
    return (
        status != "rejected"
        and relevance_tier not in {"not_relevant", "not relevant"}
        and bool(str(job.get("job_url") or "").strip())
        and bool(str(job.get("title") or "").strip())
    )


def _review_row(job: dict[str, str], *, run_record: dict[str, Any]) -> dict[str, str]:
    title = str(job.get("title") or "").strip()
    score_result = score_job(
        {
            "title": title,
            "company_name": job.get("company_name") or "",
            "location": job.get("location") or "",
            "description": job.get("description") or "",
        }
    )
    job_url = str(job.get("job_url") or "").strip()
    return {
        "job_key": job_url,
        "company": str(job.get("company_name") or "").strip(),
        "title": title,
        "location": _clean_location(job.get("location"), title=title),
        "posting_date": _format_posting_date(job.get("date_posted")),
        "relevance_tier": score_result.relevance_tier,
        "score": str(int(job.get("match_score", 0) or 0)),
        "risk_flags": _format_list_text(job.get("risk_flags")),
        "job_url": job_url,
        "match_reasons": _format_list_text(job.get("match_reasons")),
        "first_seen": str(job.get("first_seen_at") or job.get("first_seen") or "").strip(),
        "last_seen": str(job.get("last_seen_at") or job.get("last_seen") or "").strip(),
        "change_type": _change_type(job, run_record),
        "previous_score": "",
        "previous_relevance_tier": "",
        "review_state": "Review needed",
        "user_decision": "",
        "user_notes": "",
    }


def _existing_review_rows(manifest_path: Path) -> dict[str, dict[str, str]]:
    """Load prior editable review rows keyed by canonical job URL."""

    if not manifest_path.exists():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        working_path = Path(str(manifest.get("working_path") or ""))
        rows = _read_csv(working_path) if working_path.exists() else []
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return _review_rows_by_key(rows)


def _review_rows_by_key(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Index editable rows by their canonical job URL."""

    return {
        str(row.get("job_key") or row.get("job_url") or "").strip(): row
        for row in rows
        if str(row.get("job_key") or row.get("job_url") or "").strip()
    }


def _review_state(
    row: dict[str, str],
    previous_row: dict[str, str] | None,
    *,
    calibrated: bool,
) -> str:
    """Classify what a returning reviewer needs to look at next."""

    if previous_row:
        previous_score = str(previous_row.get("score") or "")
        previous_tier = str(previous_row.get("relevance_tier") or "")
        if previous_tier and previous_tier != row["relevance_tier"]:
            return "Tier changed"
        if previous_score and previous_score != row["score"]:
            return "Score changed"
        if (
            str(previous_row.get("user_decision") or "").strip()
            or str(previous_row.get("user_notes") or "").strip()
        ):
            return "Previously reviewed"
    if row["change_type"] == "New":
        return "New"
    return "Newly selected after calibration" if calibrated else "Review needed"


def write_current_review_slice(
    *,
    job_export_paths: list[Path],
    run_records: list[dict[str, Any]],
    output_dir: Path,
    manifest_path: Path = DEFAULT_CURRENT_SLICE_MANIFEST_PATH,
    generated_at: datetime | None = None,
    calibrated: bool = False,
    previous_working_path: Path | None = None,
    review_prefix: str | None = None,
    review_label: str | None = None,
) -> dict[str, Any]:
    """Build a dated review export and an editable copy without erasing decisions."""

    timestamp_value = generated_at or datetime.now(UTC)
    timestamp = timestamp_value.strftime("%Y-%m-%d-%H%M%SZ")
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = review_prefix or (
        "rbc-scotiabank-calibrated-live-review" if calibrated else "rbc-scotiabank-live-review"
    )
    review_path = output_dir / f"{prefix}-{timestamp}.csv"
    working_path = output_dir / f"{prefix}-working-{timestamp}.csv"
    if review_path.exists() or working_path.exists():
        raise FileExistsError("A review slice already exists for this exact timestamp.")

    if previous_working_path is not None:
        if not previous_working_path.exists():
            raise FileNotFoundError(
                f"Previous review working file does not exist: {previous_working_path}"
            )
        existing_review_rows = _review_rows_by_key(_read_csv(previous_working_path))
    else:
        existing_review_rows = _existing_review_rows(manifest_path)
    run_records_by_company = _run_record_map(run_records)
    allowed_companies = set(run_records_by_company)
    jobs: list[dict[str, str]] = []
    for job_export_path in job_export_paths:
        jobs.extend(_read_csv(job_export_path))
    rows = [
        _review_row(
            job,
            run_record=run_records_by_company.get(str(job.get("company_name") or ""), {}),
        )
        for job in jobs
        if _is_eligible_for_review(job)
        and (
            not allowed_companies or str(job.get("company_name") or "").strip() in allowed_companies
        )
    ]
    for row in rows:
        previous_row = existing_review_rows.get(row["job_key"])
        if previous_row:
            row["user_decision"] = str(previous_row.get("user_decision") or "")
            row["user_notes"] = str(previous_row.get("user_notes") or "")
            row["previous_score"] = str(previous_row.get("score") or "")
            row["previous_relevance_tier"] = str(previous_row.get("relevance_tier") or "")
        row["review_state"] = _review_state(row, previous_row, calibrated=calibrated)
    rows.sort(
        key=lambda row: (
            {
                "Review needed": 0,
                "New": 1,
                "Score changed": 2,
                "Tier changed": 3,
                "Newly selected after calibration": 4,
                "Previously reviewed": 5,
            }.get(row["review_state"], 6),
            -int(row["score"]),
            row["posting_date"],
            row["title"].lower(),
        )
    )
    _write_csv(review_path, rows)
    _write_csv(working_path, rows)

    manifest = {
        "label": review_label
        or (
            "Calibrated live review: RBC + Scotiabank"
            if calibrated
            else "Fresh live review: RBC + Scotiabank"
        ),
        "generated_at": timestamp_value.isoformat(),
        "companies": sorted({row["company"] for row in rows}),
        "review_rows": len(rows),
        "review_path": str(review_path.resolve()),
        "working_path": str(working_path.resolve()),
        "calibrated": calibrated,
        "review_state_counts": {
            state: sum(1 for row in rows if row["review_state"] == state)
            for state in sorted({row["review_state"] for row in rows})
        },
        "run_records": run_records,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_current_review_slice(
    manifest_path: Path = DEFAULT_CURRENT_SLICE_MANIFEST_PATH,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Load the manifest and its editable working copy, if one has been prepared."""

    if not manifest_path.exists():
        return {}, []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    working_path = Path(str(manifest.get("working_path") or ""))
    if not working_path.exists():
        return manifest, []
    return manifest, _read_csv(working_path)


def update_current_review_decision(
    *,
    manifest_path: Path,
    job_key: str,
    decision: str,
    notes: str,
) -> bool:
    """Persist one decision by stable job key without touching the immutable export."""

    if decision and decision not in USER_DECISION_VALUES:
        raise ValueError(f"Unsupported user decision: {decision}")
    manifest, rows = load_current_review_slice(manifest_path)
    working_path = Path(str(manifest.get("working_path") or ""))
    expected_row_count = int(manifest.get("review_rows") or 0)
    if expected_row_count and not rows:
        raise OSError(
            "Review working file is unexpectedly empty; no decision was saved or overwritten."
        )
    for row in rows:
        if str(row.get("job_key") or row.get("job_url") or "") == job_key:
            row["user_decision"] = decision
            row["user_notes"] = notes.strip()
            _write_csv(working_path, rows)
            return True
    return False
