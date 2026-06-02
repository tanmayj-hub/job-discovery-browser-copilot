"""SQLite storage helpers for the job discovery app."""

from __future__ import annotations

import csv
import json
import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

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


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    for field in ("role_families", "keywords", "match_reasons", "risk_flags"):
        if field in data and isinstance(data[field], str):
            data[field] = json.loads(data[field])
    return data


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
    connection.commit()
    return connection


def migrate_database(connection: sqlite3.Connection) -> None:
    """Apply lightweight schema migrations for existing local databases."""

    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(interventions)").fetchall()
    }
    if not columns:
        return

    if "reason" not in columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN reason TEXT")
    if "source_url" not in columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN source_url TEXT")
    if "action_required" not in columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN action_required TEXT")
    if "status" not in columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN status TEXT")
        connection.execute(
            "UPDATE interventions SET status = 'pending' WHERE status IS NULL OR status = ''",
        )
    if "detected_at" not in columns:
        connection.execute("ALTER TABLE interventions ADD COLUMN detected_at TEXT")
        connection.execute(
            """
            UPDATE interventions
            SET detected_at = COALESCE(created_at, CURRENT_TIMESTAMP)
            WHERE detected_at IS NULL OR detected_at = ''
            """,
        )

    job_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
    }
    if "risk_flags" not in job_columns:
        connection.execute("ALTER TABLE jobs ADD COLUMN risk_flags TEXT")
        connection.execute(
            "UPDATE jobs SET risk_flags = '[]' WHERE risk_flags IS NULL OR risk_flags = ''",
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


def _find_existing_job_id(connection: sqlite3.Connection, job: Mapping[str, Any]) -> int | None:
    if job.get("job_url"):
        row = connection.execute(
            "SELECT id FROM jobs WHERE job_url = ?",
            (job["job_url"],),
        ).fetchone()
        if row:
            return int(row["id"])

    row = connection.execute(
        """
        SELECT id
        FROM jobs
        WHERE company_name = ?
          AND title = ?
          AND COALESCE(location, '') = COALESCE(?, '')
          AND COALESCE(source_name, '') = COALESCE(?, '')
        """,
        (
            job["company_name"],
            job["title"],
            job.get("location"),
            job.get("source_name"),
        ),
    ).fetchone()
    return None if row is None else int(row["id"])


def upsert_job(connection: sqlite3.Connection, job: Mapping[str, Any]) -> int:
    """Insert a new job or update the existing matching record."""

    reasons_json = _ensure_list_json(job.get("match_reasons"))
    risk_flags_json = _ensure_list_json(job.get("risk_flags"))
    existing_job_id = _find_existing_job_id(connection, job)

    if existing_job_id is None:
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
                first_seen,
                last_seen,
                match_score,
                match_reasons,
                risk_flags,
                status,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                COALESCE(?, CURRENT_TIMESTAMP),
                COALESCE(?, CURRENT_TIMESTAMP),
                ?, ?, ?, ?, CURRENT_TIMESTAMP
            )
            """,
            (
                job["company_name"],
                job["title"],
                job.get("location"),
                job.get("job_url"),
                job.get("apply_url"),
                job.get("source_name"),
                job["source_mode"],
                job.get("description"),
                _serialize_timestamp(job.get("date_posted")),
                _serialize_timestamp(job.get("first_seen")),
                _serialize_timestamp(job.get("last_seen")),
                int(job.get("match_score", 0)),
                reasons_json,
                risk_flags_json,
                job.get("status", "new"),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)

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
            last_seen = COALESCE(?, CURRENT_TIMESTAMP),
            match_score = ?,
            match_reasons = ?,
            risk_flags = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            job["company_name"],
            job["title"],
            job.get("location"),
            job.get("job_url"),
            job.get("apply_url"),
            job.get("source_name"),
            job["source_mode"],
            job.get("description"),
            _serialize_timestamp(job.get("date_posted")),
            _serialize_timestamp(job.get("last_seen")),
            int(job.get("match_score", 0)),
            reasons_json,
            risk_flags_json,
            job.get("status", "new"),
            existing_job_id,
        ),
    )
    connection.commit()
    return existing_job_id


def upsert_jobs(connection: sqlite3.Connection, jobs: Iterable[Mapping[str, Any]]) -> list[int]:
    """Bulk upsert jobs and return their ids."""

    return [upsert_job(connection, job) for job in jobs]


def get_new_jobs(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return jobs still marked as new."""

    rows = connection.execute(
        "SELECT * FROM jobs WHERE status = 'new' ORDER BY match_score DESC, created_at DESC",
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
    query += " ORDER BY jobs.match_score DESC, jobs.last_seen DESC, jobs.id DESC"
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
    interventions_pending = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM interventions
        WHERE status = 'pending'
        """,
    ).fetchone()["count"]

    return {
        "total_companies": int(total_companies),
        "companies_ready_to_search": int(ready_companies),
        "companies_missing_url": int(missing_url),
        "jobs_found": int(jobs_found),
        "interventions_pending": int(interventions_pending),
    }


def get_interventions(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return recorded manual interventions."""

    rows = connection.execute(
        "SELECT * FROM interventions ORDER BY created_at DESC, id DESC",
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_intervention_queue(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return dashboard-friendly intervention queue rows."""

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
            COALESCE(interventions.notes, '') AS notes,
            interventions.resolved_at
        FROM interventions
        LEFT JOIN companies ON companies.name = interventions.company_name
        ORDER BY
            CASE COALESCE(interventions.status, 'pending')
                WHEN 'pending' THEN 1
                WHEN 'manual_only' THEN 2
                WHEN 'skipped' THEN 3
                WHEN 'resolved' THEN 4
                ELSE 5
            END,
            COALESCE(interventions.detected_at, interventions.created_at) DESC,
            interventions.id DESC
        """,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


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
            reason,
            source_url,
            action_required or _default_action_required(reason),
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
    query += " ORDER BY match_score DESC, last_seen DESC, id DESC"

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
                "first_seen",
                "last_seen",
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
                writer.writerow(serializable_row)

    return rows


def get_job_by_id(connection: sqlite3.Connection, job_id: int) -> dict[str, Any] | None:
    """Return one job row by id."""

    row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return None if row is None else _row_to_dict(row)
