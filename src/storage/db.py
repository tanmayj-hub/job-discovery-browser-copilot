"""SQLite storage helpers for the job discovery app."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from reports.source_observability import (
    build_source_remediation,
    compute_source_readiness,
    is_error_status,
    is_success_status,
    summarize_source_metrics,
)

JOB_STATUS_VALUES = {
    "new",
    "saved",
    "rejected",
    "reviewed",
    "needs_manual_review",
}
INTERVENTION_STATUS_VALUES = {
    "pending",
    "resolved",
    "manual_only",
    "skipped",
}
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


@dataclass(slots=True)
class JobUpsertResult:
    """Structured upsert outcome for one job row."""

    job_id: int
    action: str
    content_changed: bool


def _ensure_list_json(value: object) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return json.dumps(list(value))
    raise TypeError(f"Unsupported list-like value: {value!r}")


def _serialize_timestamp(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_job_url(url: str | None) -> str | None:
    """Normalize job URLs for stable identity matching."""

    text = str(url or "").strip()
    if not text:
        return None
    parsed = urlsplit(text)
    if not parsed.scheme or not parsed.netloc:
        return text
    path = parsed.path.rstrip("/") or "/"
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    normalized_query = urlencode(sorted(query_items))
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            normalized_query,
            "",
        )
    )


def normalize_job_text(value: str | None) -> str:
    """Normalize job text fields for resilient dedupe matching."""

    return " ".join(str(value or "").strip().lower().split())


def build_job_identity(job: Mapping[str, Any]) -> tuple[str, ...]:
    """Build the strongest available stable identity for a normalized job."""

    company_name = normalize_job_text(job.get("company_name"))
    ats_type = normalize_job_text(job.get("ats_type"))
    board_slug = normalize_job_text(job.get("board_slug"))
    external_job_id = normalize_job_text(job.get("external_job_id"))
    job_url = normalize_job_url(job.get("job_url"))
    title = normalize_job_text(job.get("title"))
    location = normalize_job_text(job.get("location"))
    source_name = normalize_job_text(job.get("source_name"))

    if company_name and ats_type and board_slug and external_job_id:
        return ("company_ats_board_external", company_name, ats_type, board_slug, external_job_id)
    if company_name and ats_type and external_job_id:
        return ("company_ats_external", company_name, ats_type, external_job_id)
    if job_url:
        return ("job_url", job_url)
    return ("company_title_location_source", company_name, title, location, source_name)


def compute_content_hash(job: Mapping[str, Any]) -> str:
    """Hash stable job content for change detection across repeated runs."""

    payload = {
        "title": normalize_job_text(job.get("title")),
        "location": normalize_job_text(job.get("location")),
        "description": normalize_job_text(job.get("description")),
        "job_url": normalize_job_url(job.get("job_url")),
        "external_job_id": normalize_job_text(job.get("external_job_id")),
        "ats_type": normalize_job_text(job.get("ats_type")),
        "board_slug": normalize_job_text(job.get("board_slug")),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    for field in ("role_families", "keywords", "match_reasons", "risk_flags"):
        if field in data and isinstance(data[field], str):
            data[field] = json.loads(data[field])
    if "first_seen_at" in data and not data.get("first_seen_at"):
        data["first_seen_at"] = data.get("first_seen")
    if "last_seen_at" in data and not data.get("last_seen_at"):
        data["last_seen_at"] = data.get("last_seen")
    if "last_updated_at" in data and not data.get("last_updated_at"):
        data["last_updated_at"] = data.get("updated_at")
    return data


def _to_db_bool(value: object) -> int:
    return 1 if bool(value) else 0


def _to_python_bool(value: object) -> bool:
    return bool(int(value)) if isinstance(value, (bool, int)) else bool(value)


def connect_database(db_path: Path | str) -> sqlite3.Connection:
    """Create a SQLite connection with row access by column name."""

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(
    db_path: Path | str,
    *,
    schema_path: Path = SCHEMA_PATH,
) -> sqlite3.Connection:
    """Initialize the database from schema.sql and return the connection."""

    connection = connect_database(db_path)
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    migrate_database(connection)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_interventions_status ON interventions(status)",
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_external_identity
        ON jobs(company_name, ats_type, board_slug, external_job_id)
        """,
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_jobs_external_job_id ON jobs(external_job_id)",
    )
    connection.commit()
    return connection


def migrate_database(connection: sqlite3.Connection) -> None:
    """Apply lightweight schema migrations for existing local databases."""

    intervention_columns = _table_columns(connection, "interventions")
    if intervention_columns and "reason" not in intervention_columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN reason TEXT")
    if intervention_columns and "source_url" not in intervention_columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN source_url TEXT")
    if intervention_columns and "action_required" not in intervention_columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN action_required TEXT")
    if intervention_columns and "status" not in intervention_columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN status TEXT")
        connection.execute(
            "UPDATE interventions SET status = 'pending' WHERE status IS NULL OR status = ''",
        )
    if intervention_columns and "occurrence_count" not in intervention_columns:
        connection.execute(
            "ALTER TABLE interventions ADD COLUMN occurrence_count INTEGER NOT NULL DEFAULT 1"
        )
        connection.execute(
            """
            UPDATE interventions
            SET occurrence_count = 1
            WHERE occurrence_count IS NULL OR occurrence_count <= 0
            """,
        )
    if intervention_columns and "detected_at" not in intervention_columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN detected_at TEXT")
        connection.execute(
            """
            UPDATE interventions
            SET detected_at = COALESCE(created_at, CURRENT_TIMESTAMP)
            WHERE detected_at IS NULL OR detected_at = ''
            """,
        )

    job_columns = _table_columns(connection, "jobs")
    source_columns = _table_columns(connection, "sources")

    if source_columns and "ats_type" not in source_columns:
        connection.execute("ALTER TABLE sources ADD COLUMN ats_type TEXT")
    if source_columns and "last_collector" not in source_columns:
        connection.execute("ALTER TABLE sources ADD COLUMN last_collector TEXT")
    if source_columns and "last_status" not in source_columns:
        connection.execute("ALTER TABLE sources ADD COLUMN last_status TEXT")
    if source_columns and "last_error" not in source_columns:
        connection.execute("ALTER TABLE sources ADD COLUMN last_error TEXT")
    if source_columns and "fallback_used" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN fallback_used INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "intervention_required" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN intervention_required INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "jobs_discovered" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN jobs_discovered INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "jobs_scored" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN jobs_scored INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "jobs_relevant" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN jobs_relevant INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "jobs_saved" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN jobs_saved INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "jobs_inserted" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN jobs_inserted INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "jobs_updated" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN jobs_updated INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "jobs_unchanged" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN jobs_unchanged INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "duplicates_skipped" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN duplicates_skipped INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "last_success_at" not in source_columns:
        connection.execute("ALTER TABLE sources ADD COLUMN last_success_at TEXT")
    if source_columns and "consecutive_failures" not in source_columns:
        connection.execute(
            "ALTER TABLE sources ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0"
        )
    if source_columns and "readiness_label" not in source_columns:
        connection.execute("ALTER TABLE sources ADD COLUMN readiness_label TEXT")

    if not job_columns:
        return

    if "risk_flags" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN risk_flags TEXT")
        connection.execute(
            "UPDATE jobs SET risk_flags = '[]' WHERE risk_flags IS NULL OR risk_flags = ''",
        )
    if "external_job_id" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN external_job_id TEXT")
    if "ats_type" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN ats_type TEXT")
    if "board_slug" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN board_slug TEXT")
    if "raw_payload_json" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN raw_payload_json TEXT")
    if "content_hash" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN content_hash TEXT")
    if "first_seen_at" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN first_seen_at TEXT")
        connection.execute(
            """
            UPDATE jobs
            SET first_seen_at = COALESCE(first_seen, created_at, CURRENT_TIMESTAMP)
            WHERE first_seen_at IS NULL OR first_seen_at = ''
            """,
        )
    if "last_seen_at" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN last_seen_at TEXT")
        connection.execute(
            """
            UPDATE jobs
            SET last_seen_at = COALESCE(last_seen, updated_at, created_at, CURRENT_TIMESTAMP)
            WHERE last_seen_at IS NULL OR last_seen_at = ''
            """,
        )
    if "last_updated_at" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN last_updated_at TEXT")
        connection.execute(
            """
            UPDATE jobs
            SET last_updated_at = COALESCE(updated_at, last_seen, created_at, CURRENT_TIMESTAMP)
            WHERE last_updated_at IS NULL OR last_updated_at = ''
            """,
        )


def _default_action_required(reason: str | None) -> str:
    lookup = {
        "login_required": "Sign in manually or mark source manual-only.",
        "captcha_detected": "Review manually. Do not continue automatically.",
        "cookie_blocked": "Clear the blocking cookie banner and retry manually.",
        "location_selection_required": "Choose a location manually, then retry.",
        "unclear_layout": "Inspect the page manually before continuing.",
        "extraction_failed": "Review extraction issues and decide whether to retry.",
    }
    return lookup.get(reason or "", "Review manually before continuing.")


def _normalize_intervention_company(value: str | None) -> str:
    return normalize_job_text(value)


def _normalize_intervention_reason(
    reason: str | None,
    intervention_type: str | None,
) -> str:
    return normalize_job_text(reason or intervention_type)


def _normalize_intervention_source_url(value: str | None) -> str:
    return normalize_job_text(normalize_job_url(value))


def _merge_intervention_notes(existing_notes: str | None, new_notes: str | None) -> str | None:
    existing = str(existing_notes or "").strip()
    incoming = str(new_notes or "").strip()
    if not incoming:
        return existing or None
    if not existing:
        return incoming
    if incoming == existing or incoming in existing:
        return existing
    return f"{existing}\n\n{incoming}"


def _intervention_identity_key(record: Mapping[str, Any]) -> tuple[str, str]:
    company_key = _normalize_intervention_company(record.get("company_name"))
    source_url_key = _normalize_intervention_source_url(record.get("source_url"))
    return (company_key, source_url_key or company_key)


def _intervention_sort_key(record: Mapping[str, Any]) -> tuple[str, int]:
    detected = str(record.get("detected_at") or record.get("created_at") or "")
    return (detected, int(record.get("id") or 0))


def _pending_reason_history_note(existing: Mapping[str, Any], new_reason: str | None) -> str | None:
    previous_reason = str(existing.get("reason") or existing.get("intervention_type") or "").strip()
    latest_reason = str(new_reason or "").strip()
    if not previous_reason or not latest_reason or previous_reason == latest_reason:
        return None
    return f"Previous reason: {previous_reason}"


def _collapse_intervention_records(
    records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = _intervention_identity_key(record)
        grouped.setdefault(key, []).append(dict(record))

    collapsed: list[dict[str, Any]] = []
    for items in grouped.values():
        ordered = sorted(items, key=_intervention_sort_key, reverse=True)
        latest = dict(ordered[0])
        latest["occurrence_count"] = sum(
            max(1, int(item.get("occurrence_count", 1) or 1)) for item in ordered
        )
        latest["active_row_count"] = len(ordered)
        latest["reason_history"] = [
            reason
            for reason in dict.fromkeys(
                str(item.get("reason") or item.get("intervention_type") or "").strip()
                for item in ordered
            )
            if reason
        ]
        latest["previous_reasons"] = latest["reason_history"][1:]
        collapsed.append(latest)

    return sorted(collapsed, key=_intervention_sort_key, reverse=True)


def _intervention_summary_by_source(
    records: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    summary: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = _intervention_identity_key(record)
        existing = summary.get(key)
        if existing is None:
            summary[key] = {
                "count": 1,
                "latest": dict(record),
            }
            continue
        existing["count"] += 1
        if _intervention_sort_key(record) > _intervention_sort_key(existing["latest"]):
            existing["latest"] = dict(record)
    return summary


def _match_intervention_summary(
    summary: Mapping[tuple[str, str], dict[str, Any]],
    *,
    company_name: str | None,
    source_url: str | None,
) -> dict[str, Any] | None:
    company_key = _normalize_intervention_company(company_name)
    source_url_key = _normalize_intervention_source_url(source_url)
    exact_key = (company_key, source_url_key or company_key)
    exact_match = summary.get(exact_key)
    if exact_match is not None:
        return exact_match

    company_matches = [
        value for key, value in summary.items() if key[0] == company_key
    ]
    if len(company_matches) == 1:
        return company_matches[0]
    return None


def find_open_intervention(
    connection: sqlite3.Connection,
    *,
    company_name: str | None = None,
    source_url: str | None = None,
    intervention_type: str,
    reason: str | None = None,
) -> dict[str, Any] | None:
    """Return an existing unresolved intervention for the same active source."""

    company_key = _normalize_intervention_company(company_name)
    source_url_key = _normalize_intervention_source_url(source_url)

    rows = connection.execute(
        """
        SELECT *
        FROM interventions
        WHERE COALESCE(status, 'pending') = 'pending'
          AND lower(trim(COALESCE(company_name, ''))) = ?
        ORDER BY COALESCE(detected_at, created_at) DESC, id DESC
        """,
        (company_key,),
    ).fetchall()

    for row in rows:
        record = _row_to_dict(row)
        if _normalize_intervention_source_url(record.get("source_url")) != source_url_key:
            continue
        return record
    return None


def upsert_companies(
    connection: sqlite3.Connection,
    companies: Iterable[Mapping[str, Any]],
) -> int:
    """Insert or update company records and their source rows."""

    count = 0
    for company in companies:
        connection.execute(
            """
            INSERT INTO companies (
                name,
                sector,
                category,
                careers_url,
                website_category,
                ats_hint,
                canada_hubs_notes,
                role_families,
                keywords,
                priority,
                monitoring_hint,
                status,
                source_mode,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(name) DO UPDATE SET
                sector = excluded.sector,
                category = excluded.category,
                careers_url = excluded.careers_url,
                website_category = excluded.website_category,
                ats_hint = excluded.ats_hint,
                canada_hubs_notes = excluded.canada_hubs_notes,
                role_families = excluded.role_families,
                keywords = excluded.keywords,
                priority = excluded.priority,
                monitoring_hint = excluded.monitoring_hint,
                status = excluded.status,
                source_mode = excluded.source_mode,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                company["name"],
                company["sector"],
                company["category"],
                company.get("careers_url"),
                company.get("website_category"),
                company.get("ats_hint"),
                company.get("canada_hubs_notes"),
                _ensure_list_json(company.get("role_families")),
                _ensure_list_json(company.get("keywords")),
                company.get("priority"),
                company.get("monitoring_hint"),
                company.get("status"),
                company["source_mode"],
            ),
        )
        connection.execute(
            """
            INSERT INTO sources (
                company_name,
                source_name,
                source_mode,
                careers_url,
                website_category,
                ats_hint,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(company_name, source_name) DO UPDATE SET
                source_mode = excluded.source_mode,
                careers_url = excluded.careers_url,
                website_category = excluded.website_category,
                ats_hint = excluded.ats_hint,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                company["name"],
                company.get("website_category") or company["name"],
                company["source_mode"],
                company.get("careers_url"),
                company.get("website_category"),
                company.get("ats_hint"),
            ),
        )
        count += 1

    connection.commit()
    return count


def _prepare_job_for_storage(
    job: Mapping[str, Any],
    *,
    now: str | None = None,
) -> dict[str, Any]:
    timestamp = now or _current_timestamp()
    first_seen_at = (
        _serialize_timestamp(job.get("first_seen_at") or job.get("first_seen")) or timestamp
    )
    last_seen_at = (
        _serialize_timestamp(job.get("last_seen_at") or job.get("last_seen")) or timestamp
    )

    prepared = {
        "company_name": str(job["company_name"]).strip(),
        "title": str(job["title"]).strip(),
        "location": str(job.get("location") or "").strip() or None,
        "job_url": normalize_job_url(job.get("job_url")),
        "apply_url": normalize_job_url(job.get("apply_url")),
        "source_name": str(job.get("source_name") or "").strip() or None,
        "source_mode": str(job["source_mode"]).strip(),
        "description": str(job.get("description") or "").strip() or None,
        "date_posted": _serialize_timestamp(job.get("date_posted")),
        "external_job_id": str(job.get("external_job_id") or "").strip() or None,
        "ats_type": str(job.get("ats_type") or "").strip() or None,
        "board_slug": str(job.get("board_slug") or "").strip() or None,
        "raw_payload_json": str(job.get("raw_payload_json") or "").strip() or None,
        "first_seen_at": first_seen_at,
        "last_seen_at": last_seen_at,
        "last_updated_at": (
            _serialize_timestamp(job.get("last_updated_at") or job.get("updated_at"))
            or last_seen_at
        ),
        "first_seen": _serialize_timestamp(job.get("first_seen")) or first_seen_at,
        "last_seen": _serialize_timestamp(job.get("last_seen")) or last_seen_at,
        "match_score": int(job.get("match_score", 0)),
        "match_reasons": job.get("match_reasons"),
        "risk_flags": job.get("risk_flags"),
        "status": str(job.get("status") or "new").strip(),
    }
    prepared["content_hash"] = compute_content_hash(prepared)
    return prepared


def _build_identity_candidates(job: Mapping[str, Any]) -> list[tuple[str, ...]]:
    strongest = build_job_identity(job)
    candidates = [strongest]
    normalized_url = normalize_job_url(job.get("job_url"))
    company_name = normalize_job_text(job.get("company_name"))
    title = normalize_job_text(job.get("title"))
    location = normalize_job_text(job.get("location"))
    source_name = normalize_job_text(job.get("source_name"))

    if strongest[0] != "job_url" and normalized_url:
        candidates.append(("job_url", normalized_url))
    fallback = ("company_title_location_source", company_name, title, location, source_name)
    if strongest[0] in {"job_url", "company_title_location_source"}:
        candidates.append(fallback)

    seen: set[tuple[str, ...]] = set()
    deduped: list[tuple[str, ...]] = []
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def _find_existing_job_row(
    connection: sqlite3.Connection,
    job: Mapping[str, Any],
) -> sqlite3.Row | None:
    for identity in _build_identity_candidates(job):
        kind = identity[0]
        if kind == "company_ats_board_external":
            row = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE lower(trim(company_name)) = ?
                  AND lower(trim(COALESCE(ats_type, ''))) = ?
                  AND lower(trim(COALESCE(board_slug, ''))) = ?
                  AND lower(trim(COALESCE(external_job_id, ''))) = ?
                """,
                identity[1:],
            ).fetchone()
        elif kind == "company_ats_external":
            row = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE lower(trim(company_name)) = ?
                  AND lower(trim(COALESCE(ats_type, ''))) = ?
                  AND lower(trim(COALESCE(external_job_id, ''))) = ?
                """,
                identity[1:],
            ).fetchone()
        elif kind == "job_url":
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_url = ?",
                (identity[1],),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE lower(trim(company_name)) = ?
                  AND lower(trim(title)) = ?
                  AND lower(trim(COALESCE(location, ''))) = ?
                  AND lower(trim(COALESCE(source_name, ''))) = ?
                """,
                identity[1:],
            ).fetchone()

        if row is not None:
            return row
    return None


def _job_fields_changed(
    existing: Mapping[str, Any],
    prepared: Mapping[str, Any],
    *,
    reasons_json: str,
    risk_flags_json: str,
) -> bool:
    comparisons = {
        "title": prepared["title"],
        "location": prepared["location"],
        "job_url": prepared["job_url"],
        "apply_url": prepared["apply_url"],
        "source_name": prepared["source_name"],
        "source_mode": prepared["source_mode"],
        "description": prepared["description"],
        "date_posted": prepared["date_posted"],
        "external_job_id": prepared["external_job_id"],
        "ats_type": prepared["ats_type"],
        "board_slug": prepared["board_slug"],
        "raw_payload_json": prepared["raw_payload_json"],
        "content_hash": prepared["content_hash"],
        "match_score": prepared["match_score"],
        "status": prepared["status"],
    }
    for field, expected in comparisons.items():
        if existing.get(field) != expected:
            return True
    if _ensure_list_json(existing.get("match_reasons")) != reasons_json:
        return True
    if _ensure_list_json(existing.get("risk_flags")) != risk_flags_json:
        return True
    return False


def upsert_job_record(connection: sqlite3.Connection, job: Mapping[str, Any]) -> JobUpsertResult:
    """Insert or update one job and return a structured change summary."""

    prepared = _prepare_job_for_storage(job)
    reasons_json = _ensure_list_json(prepared.get("match_reasons"))
    risk_flags_json = _ensure_list_json(prepared.get("risk_flags"))
    existing_row = _find_existing_job_row(connection, prepared)

    if existing_row is None:
        cursor = connection.execute(
            """
            INSERT INTO jobs (
                company_name,
                title,
                location,
                job_url,
                apply_url,
                source_name,
                source_mode,
                description,
                date_posted,
                external_job_id,
                ats_type,
                board_slug,
                raw_payload_json,
                content_hash,
                first_seen,
                last_seen,
                first_seen_at,
                last_seen_at,
                last_updated_at,
                match_score,
                match_reasons,
                risk_flags,
                status,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )
            """,
            (
                prepared["company_name"],
                prepared["title"],
                prepared["location"],
                prepared["job_url"],
                prepared["apply_url"],
                prepared["source_name"],
                prepared["source_mode"],
                prepared["description"],
                prepared["date_posted"],
                prepared["external_job_id"],
                prepared["ats_type"],
                prepared["board_slug"],
                prepared["raw_payload_json"],
                prepared["content_hash"],
                prepared["first_seen"],
                prepared["last_seen"],
                prepared["first_seen_at"],
                prepared["last_seen_at"],
                prepared["last_updated_at"],
                prepared["match_score"],
                reasons_json,
                risk_flags_json,
                prepared["status"],
            ),
        )
        connection.commit()
        return JobUpsertResult(
            job_id=int(cursor.lastrowid),
            action="inserted",
            content_changed=True,
        )

    existing = _row_to_dict(existing_row)
    changed = _job_fields_changed(
        existing,
        prepared,
        reasons_json=reasons_json,
        risk_flags_json=risk_flags_json,
    )

    if not changed:
        connection.execute(
            """
            UPDATE jobs
            SET last_seen = ?,
                last_seen_at = ?
            WHERE id = ?
            """,
            (
                prepared["last_seen"],
                prepared["last_seen_at"],
                int(existing_row["id"]),
            ),
        )
        connection.commit()
        return JobUpsertResult(
            job_id=int(existing_row["id"]),
            action="unchanged",
            content_changed=False,
        )

    connection.execute(
        """
        UPDATE jobs
        SET company_name = ?,
            title = ?,
            location = ?,
            job_url = ?,
            apply_url = ?,
            source_name = ?,
            source_mode = ?,
            description = ?,
            date_posted = ?,
            external_job_id = ?,
            ats_type = ?,
            board_slug = ?,
            raw_payload_json = ?,
            content_hash = ?,
            last_seen = ?,
            last_seen_at = ?,
            last_updated_at = ?,
            match_score = ?,
            match_reasons = ?,
            risk_flags = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            prepared["company_name"],
            prepared["title"],
            prepared["location"],
            prepared["job_url"],
            prepared["apply_url"],
            prepared["source_name"],
            prepared["source_mode"],
            prepared["description"],
            prepared["date_posted"],
            prepared["external_job_id"],
            prepared["ats_type"],
            prepared["board_slug"],
            prepared["raw_payload_json"],
            prepared["content_hash"],
            prepared["last_seen"],
            prepared["last_seen_at"],
            prepared["last_seen_at"],
            prepared["match_score"],
            reasons_json,
            risk_flags_json,
            prepared["status"],
            int(existing_row["id"]),
        ),
    )
    connection.commit()
    return JobUpsertResult(
        job_id=int(existing_row["id"]),
        action="updated",
        content_changed=True,
    )


def upsert_job(connection: sqlite3.Connection, job: Mapping[str, Any]) -> int:
    """Insert a new job or update the existing matching record."""

    return upsert_job_record(connection, job).job_id


def upsert_jobs(connection: sqlite3.Connection, jobs: Iterable[Mapping[str, Any]]) -> list[int]:
    """Bulk upsert jobs and return their ids."""

    return [upsert_job(connection, job) for job in jobs]


def get_new_jobs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return jobs still marked as new."""

    rows = connection.execute(
        """
        SELECT *
        FROM jobs
        WHERE status = 'new'
        ORDER BY match_score DESC, COALESCE(last_seen_at, last_seen) DESC, created_at DESC
        """,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_jobs(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return jobs joined with company metadata for dashboard views."""

    query = """
        SELECT
            jobs.*,
            companies.sector,
            companies.category,
            companies.priority,
            companies.ats_hint,
            companies.monitoring_hint
        FROM jobs
        LEFT JOIN companies ON companies.name = jobs.company_name
    """
    params: tuple[Any, ...] = ()
    if status is not None:
        query += " WHERE jobs.status = ?"
        params = (status,)
    query += (
        " ORDER BY jobs.match_score DESC, "
        "COALESCE(jobs.last_seen_at, jobs.last_seen) DESC, jobs.id DESC"
    )
    rows = connection.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_companies(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return all companies for the dashboard watchlist."""

    rows = connection.execute(
        """
        SELECT *
        FROM companies
        ORDER BY
            CASE priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            name ASC
        """,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_companies_by_source_mode(
    connection: sqlite3.Connection,
    source_mode: str,
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return companies filtered by source mode."""

    query = """
        SELECT *
        FROM companies
        WHERE source_mode = ?
        ORDER BY
            CASE priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            name ASC
    """
    params: tuple[Any, ...] = (source_mode,)
    if limit is not None:
        query += " LIMIT ?"
        params += (limit,)

    rows = connection.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_companies_needing_url(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return companies whose source mode still requires manual URL discovery."""

    rows = connection.execute(
        """
        SELECT *
        FROM companies
        WHERE source_mode = 'needs_url'
           OR careers_url IS NULL
           OR TRIM(COALESCE(careers_url, '')) = ''
        ORDER BY priority DESC, name ASC
        """,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_source_status_rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return source rows joined with company metadata for reporting and dashboard views."""

    rows = connection.execute(
        """
        SELECT
            sources.id,
            sources.company_name,
            sources.source_name,
            sources.source_mode,
            sources.careers_url AS source_url,
            sources.website_category,
            sources.ats_hint,
            sources.ats_type,
            sources.last_collector,
            sources.last_status,
            sources.last_error,
            sources.fallback_used,
            sources.intervention_required,
            sources.jobs_discovered,
            sources.jobs_scored,
            sources.jobs_relevant,
            sources.jobs_saved,
            sources.jobs_inserted,
            sources.jobs_updated,
            sources.jobs_unchanged,
            sources.duplicates_skipped,
            sources.last_success_at,
            sources.last_checked,
            sources.consecutive_failures,
            sources.readiness_label,
            sources.updated_at,
            companies.sector,
            companies.category,
            companies.priority,
            companies.status AS company_status
        FROM sources
        LEFT JOIN companies ON companies.name = sources.company_name
        ORDER BY
            CASE companies.priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            sources.company_name ASC,
            sources.source_name ASC
        """
    ).fetchall()

    pending_summary = _intervention_summary_by_source(get_intervention_queue(connection))
    history_summary = _intervention_summary_by_source(get_intervention_history(connection))
    source_rows: list[dict[str, Any]] = []
    for row in rows:
        record = _row_to_dict(row)
        record["fallback_used"] = _to_python_bool(record.get("fallback_used", 0))
        record["intervention_required"] = _to_python_bool(
            record.get("intervention_required", 0)
        )
        record["status"] = record.get("last_status")
        record["collector"] = record.get("last_collector")
        record["error"] = record.get("last_error")
        record["source_url"] = record.get("source_url")
        record["readiness_label"] = compute_source_readiness(record)
        pending = _match_intervention_summary(
            pending_summary,
            company_name=record.get("company_name"),
            source_url=record.get("source_url"),
        )
        history = _match_intervention_summary(
            history_summary,
            company_name=record.get("company_name"),
            source_url=record.get("source_url"),
        )
        record["pending_intervention_count"] = int(pending["count"]) if pending else 0
        record["resolved_history_count"] = int(history["count"]) if history else 0
        record["latest_pending_reason"] = (
            pending["latest"].get("reason") if pending else None
        )
        record["latest_pending_detected_at"] = (
            pending["latest"].get("detected_at") if pending else None
        )
        record["latest_pending_action_required"] = (
            pending["latest"].get("action_required") if pending else None
        )
        remediation = build_source_remediation(record)
        record.update(remediation)
        source_rows.append(record)
    return source_rows


def get_dashboard_overview(connection: sqlite3.Connection) -> dict[str, int]:
    """Return top-level counts for the overview section."""

    total_companies = connection.execute(
        "SELECT COUNT(*) AS count FROM companies",
    ).fetchone()["count"]
    ready_companies = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM companies
        WHERE source_mode IN ('api_allowed', 'browser_allowed', 'human_in_loop')
        """,
    ).fetchone()["count"]
    missing_url = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM companies
        WHERE source_mode = 'needs_url'
           OR careers_url IS NULL
           OR TRIM(COALESCE(careers_url, '')) = ''
        """,
    ).fetchone()["count"]
    jobs_found = connection.execute(
        "SELECT COUNT(*) AS count FROM jobs",
    ).fetchone()["count"]
    interventions_pending = len(get_intervention_queue(connection))
    interventions_resolved = len(get_intervention_history(connection))
    source_metrics = summarize_source_metrics(get_source_status_rows(connection))

    return {
        "total_companies": int(total_companies),
        "companies_ready_to_search": int(ready_companies),
        "companies_missing_url": int(missing_url),
        "jobs_found": int(jobs_found),
        "interventions_pending": int(interventions_pending),
        "interventions_resolved_history": int(interventions_resolved),
        "total_sources_checked": int(source_metrics["sources_checked"]),
        "jobs_discovered_latest": int(source_metrics["jobs_discovered"]),
        "jobs_relevant_latest": int(source_metrics["jobs_relevant"]),
        "jobs_saved_latest": int(source_metrics["jobs_saved"]),
        "api_sources_used": int(source_metrics["api_sources_used"]),
        "browser_fallbacks": int(source_metrics["browser_fallback_used"]),
        "interventions_required_sources": int(source_metrics["interventions_required"]),
        "source_errors": int(source_metrics["errors"]),
    }


def get_interventions(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return recorded manual interventions."""

    rows = connection.execute(
        "SELECT * FROM interventions ORDER BY created_at DESC, id DESC",
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_intervention_queue(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return active pending interventions collapsed to one row per source."""

    rows = connection.execute(
        """
        SELECT
            interventions.id,
            interventions.company_name,
            COALESCE(interventions.source_url, companies.careers_url) AS source_url,
            COALESCE(interventions.reason, interventions.intervention_type) AS reason,
            COALESCE(interventions.detected_at, interventions.created_at) AS detected_at,
            COALESCE(interventions.action_required, '') AS action_required,
            COALESCE(interventions.status, 'pending') AS status,
            COALESCE(interventions.occurrence_count, 1) AS occurrence_count,
            COALESCE(interventions.notes, '') AS notes,
            interventions.resolved_at
        FROM interventions
        LEFT JOIN companies ON companies.name = interventions.company_name
        WHERE COALESCE(interventions.status, 'pending') = 'pending'
        ORDER BY
            COALESCE(interventions.detected_at, interventions.created_at) DESC,
            interventions.id DESC
        """,
    ).fetchall()
    queue = _collapse_intervention_records(_row_to_dict(row) for row in rows)
    for item in queue:
        item.update(build_source_remediation(item))
    return queue


def get_intervention_history(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return resolved/manual-only/skipped intervention history rows."""

    rows = connection.execute(
        """
        SELECT
            interventions.id,
            interventions.company_name,
            COALESCE(interventions.source_url, companies.careers_url) AS source_url,
            COALESCE(interventions.reason, interventions.intervention_type) AS reason,
            COALESCE(interventions.detected_at, interventions.created_at) AS detected_at,
            COALESCE(interventions.action_required, '') AS action_required,
            COALESCE(interventions.status, 'pending') AS status,
            COALESCE(interventions.occurrence_count, 1) AS occurrence_count,
            COALESCE(interventions.notes, '') AS notes,
            interventions.resolved_at
        FROM interventions
        LEFT JOIN companies ON companies.name = interventions.company_name
        WHERE COALESCE(interventions.status, 'pending') <> 'pending'
        ORDER BY
            COALESCE(interventions.resolved_at, interventions.detected_at, interventions.created_at)
                DESC,
            interventions.id DESC
        """,
    ).fetchall()
    history = [_row_to_dict(row) for row in rows]
    for item in history:
        item.update(build_source_remediation(item))
    return history


def create_intervention(
    connection: sqlite3.Connection,
    *,
    intervention_type: str,
    company_name: str | None = None,
    job_id: int | None = None,
    source_url: str | None = None,
    reason: str | None = None,
    action_required: str | None = None,
    status: str = "pending",
    notes: str | None = None,
) -> int:
    """Insert one intervention record and return its id."""

    if status not in INTERVENTION_STATUS_VALUES:
        raise ValueError(f"Invalid intervention status: {status}")

    normalized_source_url = normalize_job_url(source_url)
    normalized_reason = str(reason or "").strip() or None
    resolved_action_required = action_required or _default_action_required(reason)
    open_intervention = None
    if status == "pending":
        open_intervention = find_open_intervention(
            connection,
            company_name=company_name,
            source_url=normalized_source_url,
            intervention_type=intervention_type,
            reason=normalized_reason,
        )
    if open_intervention is not None:
        merged_notes = _merge_intervention_notes(
            open_intervention.get("notes"),
            _pending_reason_history_note(open_intervention, normalized_reason),
        )
        merged_notes = _merge_intervention_notes(merged_notes, notes)
        connection.execute(
            """
            UPDATE interventions
            SET job_id = COALESCE(?, job_id),
                intervention_type = COALESCE(?, intervention_type),
                reason = COALESCE(?, reason),
                source_url = COALESCE(?, source_url),
                action_required = COALESCE(?, action_required),
                occurrence_count = COALESCE(occurrence_count, 1) + 1,
                notes = ?,
                status = 'pending',
                detected_at = CURRENT_TIMESTAMP,
                resolved_at = NULL
            WHERE id = ?
            """,
            (
                job_id,
                intervention_type,
                normalized_reason,
                normalized_source_url,
                resolved_action_required,
                merged_notes,
                int(open_intervention["id"]),
            ),
        )
        connection.commit()
        return int(open_intervention["id"])

    cursor = connection.execute(
        """
        INSERT INTO interventions (
            job_id,
            company_name,
            intervention_type,
            reason,
            source_url,
            action_required,
            status,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            company_name,
            intervention_type,
            normalized_reason,
            normalized_source_url,
            resolved_action_required,
            status,
            notes,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_intervention_status(
    connection: sqlite3.Connection,
    intervention_id: int,
    status: str,
) -> None:
    """Update intervention queue status."""

    if status not in INTERVENTION_STATUS_VALUES:
        raise ValueError(f"Invalid intervention status: {status}")

    resolved_at = "CURRENT_TIMESTAMP" if status in {"resolved", "manual_only", "skipped"} else None
    if resolved_at is None:
        connection.execute(
            """
            UPDATE interventions
            SET status = ?,
                resolved_at = NULL
            WHERE id = ?
            """,
            (status, intervention_id),
        )
    else:
        connection.execute(
            f"""
            UPDATE interventions
            SET status = ?,
                resolved_at = {resolved_at}
            WHERE id = ?
            """,
            (status, intervention_id),
        )
    connection.commit()


def resolve_pending_interventions_for_company(
    connection: sqlite3.Connection,
    *,
    company_name: str,
) -> int:
    """Resolve pending interventions for a company after a successful rerun."""

    cursor = connection.execute(
        """
        UPDATE interventions
        SET status = 'resolved',
            resolved_at = CURRENT_TIMESTAMP
        WHERE company_name = ?
          AND COALESCE(status, 'pending') = 'pending'
        """,
        (company_name,),
    )
    connection.commit()
    return int(cursor.rowcount or 0)


def append_intervention_notes(
    connection: sqlite3.Connection,
    intervention_id: int,
    notes: str,
) -> None:
    """Append notes to an intervention record."""

    existing = connection.execute(
        "SELECT notes FROM interventions WHERE id = ?",
        (intervention_id,),
    ).fetchone()
    if existing is None:
        raise ValueError(f"Unknown intervention id: {intervention_id}")

    previous = (existing["notes"] or "").strip()
    combined = notes.strip() if not previous else f"{previous}\n\n{notes.strip()}"
    connection.execute(
        "UPDATE interventions SET notes = ? WHERE id = ?",
        (combined, intervention_id),
    )
    connection.commit()


def create_daily_run(
    connection: sqlite3.Connection,
    *,
    source_name: str,
    notes: str | None = None,
) -> int:
    """Create a daily run record and return its id."""

    cursor = connection.execute(
        """
        INSERT INTO daily_runs (
            source_name,
            notes
        )
        VALUES (?, ?)
        """,
        (source_name, notes),
    )
    connection.commit()
    return int(cursor.lastrowid)


def finish_daily_run(
    connection: sqlite3.Connection,
    run_id: int,
    *,
    status: str,
    jobs_seen: int = 0,
    jobs_new: int = 0,
    notes: str | None = None,
) -> None:
    """Finalize a daily run record."""

    connection.execute(
        """
        UPDATE daily_runs
        SET completed_at = CURRENT_TIMESTAMP,
            status = ?,
            jobs_seen = ?,
            jobs_new = ?,
            notes = COALESCE(?, notes)
        WHERE id = ?
        """,
        (status, jobs_seen, jobs_new, notes, run_id),
    )
    connection.commit()


def record_source_observation(
    connection: sqlite3.Connection,
    *,
    company_name: str,
    source_name: str,
    source_mode: str,
    careers_url: str | None = None,
    website_category: str | None = None,
    ats_hint: str | None = None,
    ats_type: str | None = None,
    collector: str | None = None,
    status: str | None = None,
    error: str | None = None,
    fallback_used: bool = False,
    intervention_required: bool = False,
    jobs_discovered: int = 0,
    jobs_scored: int = 0,
    jobs_relevant: int = 0,
    jobs_saved: int = 0,
    jobs_inserted: int = 0,
    jobs_updated: int = 0,
    jobs_unchanged: int = 0,
    duplicates_skipped: int = 0,
) -> None:
    """Persist the latest source-level routing and collection outcome."""

    existing = connection.execute(
        """
        SELECT consecutive_failures, last_success_at
        FROM sources
        WHERE company_name = ?
          AND source_name = ?
        """,
        (company_name, source_name),
    ).fetchone()
    timestamp = _current_timestamp()
    normalized_status = str(status or "").strip() or None
    normalized_error = str(error or "").strip() or None
    readiness_label = compute_source_readiness(
        {
            "source_mode": source_mode,
            "collector": collector,
            "status": normalized_status,
            "intervention_required": intervention_required,
        }
    )

    previous_failures = int(existing["consecutive_failures"]) if existing is not None else 0
    previous_success_at = existing["last_success_at"] if existing is not None else None

    if is_error_status(normalized_status) or normalized_status == "paused":
        consecutive_failures = previous_failures + 1
    elif is_success_status(normalized_status):
        consecutive_failures = 0
    else:
        consecutive_failures = 0

    last_success_at = timestamp if is_success_status(normalized_status) else previous_success_at
    last_error = (
        normalized_error
        if normalized_error
        else (normalized_status if is_error_status(normalized_status) else None)
    )

    connection.execute(
        """
        INSERT INTO sources (
            company_name,
            source_name,
            source_mode,
            careers_url,
            website_category,
            ats_hint,
            ats_type,
            last_collector,
            last_status,
            last_error,
            fallback_used,
            intervention_required,
            jobs_discovered,
            jobs_scored,
            jobs_relevant,
            jobs_saved,
            jobs_inserted,
            jobs_updated,
            jobs_unchanged,
            duplicates_skipped,
            last_success_at,
            consecutive_failures,
            readiness_label,
            last_checked,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(company_name, source_name) DO UPDATE SET
            source_mode = excluded.source_mode,
            careers_url = excluded.careers_url,
            website_category = COALESCE(excluded.website_category, sources.website_category),
            ats_hint = COALESCE(excluded.ats_hint, sources.ats_hint),
            ats_type = excluded.ats_type,
            last_collector = excluded.last_collector,
            last_status = excluded.last_status,
            last_error = excluded.last_error,
            fallback_used = excluded.fallback_used,
            intervention_required = excluded.intervention_required,
            jobs_discovered = excluded.jobs_discovered,
            jobs_scored = excluded.jobs_scored,
            jobs_relevant = excluded.jobs_relevant,
            jobs_saved = excluded.jobs_saved,
            jobs_inserted = excluded.jobs_inserted,
            jobs_updated = excluded.jobs_updated,
            jobs_unchanged = excluded.jobs_unchanged,
            duplicates_skipped = excluded.duplicates_skipped,
            last_success_at = excluded.last_success_at,
            consecutive_failures = excluded.consecutive_failures,
            readiness_label = excluded.readiness_label,
            last_checked = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            company_name,
            source_name,
            source_mode,
            careers_url,
            website_category,
            ats_hint,
            ats_type,
            collector,
            normalized_status,
            last_error,
            _to_db_bool(fallback_used),
            _to_db_bool(intervention_required),
            int(jobs_discovered),
            int(jobs_scored),
            int(jobs_relevant),
            int(jobs_saved),
            int(jobs_inserted),
            int(jobs_updated),
            int(jobs_unchanged),
            int(duplicates_skipped),
            last_success_at,
            consecutive_failures,
            readiness_label,
        ),
    )
    connection.commit()


def mark_source_checked(
    connection: sqlite3.Connection,
    *,
    company_name: str,
    source_name: str,
) -> None:
    """Update the last-checked timestamp for a source."""

    connection.execute(
        """
        UPDATE sources
        SET last_checked = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE company_name = ?
          AND source_name = ?
        """,
        (company_name, source_name),
    )
    connection.commit()


def update_company_source(
    connection: sqlite3.Connection,
    *,
    company_name: str,
    careers_url: str | None,
    source_mode: str,
    source_name: str | None = None,
) -> None:
    """Update a company's careers URL and source mode."""

    company = connection.execute(
        """
        SELECT name, website_category, ats_hint
        FROM companies
        WHERE name = ?
        """,
        (company_name,),
    ).fetchone()
    if company is None:
        raise ValueError(f"Unknown company: {company_name}")

    resolved_source_name = source_name or company["website_category"] or company_name
    connection.execute(
        """
        UPDATE companies
        SET careers_url = ?,
            source_mode = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE name = ?
        """,
        (careers_url, source_mode, company_name),
    )
    connection.execute(
        """
        INSERT INTO sources (
            company_name,
            source_name,
            source_mode,
            careers_url,
            website_category,
            ats_hint,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(company_name, source_name) DO UPDATE SET
            source_mode = excluded.source_mode,
            careers_url = excluded.careers_url,
            website_category = excluded.website_category,
            ats_hint = excluded.ats_hint,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            company_name,
            resolved_source_name,
            source_mode,
            careers_url,
            company["website_category"],
            company["ats_hint"],
        ),
    )
    connection.commit()


def update_job_status(connection: sqlite3.Connection, job_id: int, status: str) -> None:
    """Update a job status with validation."""

    if status not in JOB_STATUS_VALUES:
        raise ValueError(f"Invalid job status: {status}")

    connection.execute(
        """
        UPDATE jobs
        SET status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, job_id),
    )
    connection.commit()


def export_jobs(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    output_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Export jobs as dictionaries and optionally write them to CSV."""

    query = "SELECT * FROM jobs"
    params: tuple[Any, ...] = ()
    if status is not None:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY match_score DESC, COALESCE(last_seen_at, last_seen) DESC, id DESC"

    rows = [_row_to_dict(row) for row in connection.execute(query, params).fetchall()]

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if rows:
            fieldnames = list(rows[0].keys())
        else:
            fieldnames = [
                "id",
                "company_name",
                "title",
                "location",
                "job_url",
                "apply_url",
                "source_name",
                "source_mode",
                "description",
                "date_posted",
                "external_job_id",
                "ats_type",
                "board_slug",
                "content_hash",
                "first_seen",
                "last_seen",
                "first_seen_at",
                "last_seen_at",
                "last_updated_at",
                "match_score",
                "match_reasons",
                "risk_flags",
                "status",
                "created_at",
                "updated_at",
            ]
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                serializable_row = row.copy()
                serializable_row["match_reasons"] = json.dumps(row.get("match_reasons", []))
                serializable_row["risk_flags"] = json.dumps(row.get("risk_flags", []))
                writer.writerow(serializable_row)

    return rows


def get_job_by_id(connection: sqlite3.Connection, job_id: int) -> dict[str, Any] | None:
    """Return one job row by id."""

    row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return None if row is None else _row_to_dict(row)
