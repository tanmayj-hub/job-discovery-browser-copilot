"""Daily run orchestration and report generation."""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from classifier.source_classifier import classify_source
from collectors.browser_collector import collect_companies_with_browser
from processing.score import score_job
from storage.db import (
    get_companies,
    get_intervention_queue,
    get_job_by_id,
    initialize_database,
    upsert_companies,
    upsert_job,
)

CollectorFunc = Callable[[Any, list[dict[str, Any]]], list[dict[str, Any]]]

ELIGIBLE_SOURCE_MODES = {"api_allowed", "browser_allowed", "human_in_loop"}
SKIPPED_SOURCE_MODES = {"needs_url", "manual_only", "avoid"}


@dataclass(slots=True)
class DailyRunArtifacts:
    """Output paths for the daily run."""

    report_path: Path
    csv_path: Path


@dataclass(slots=True)
class DailyRunResult:
    """Structured daily run summary."""

    run_date: str
    companies_checked: list[str]
    companies_skipped: list[dict[str, str]]
    interventions_needed: list[dict[str, Any]]
    errors: list[str]
    jobs_discovered: int
    jobs_scored: int
    jobs_relevant: int
    jobs_saved: list[dict[str, Any]]
    location_scope_used: bool
    keyword_scope_used: bool
    artifacts: DailyRunArtifacts


def load_companies_yaml(path: Path) -> list[dict[str, Any]]:
    """Load company records from YAML."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    companies = payload.get("companies", [])
    return companies if isinstance(companies, list) else []


def _existing_company_map(connection) -> dict[str, dict[str, Any]]:
    return {company["name"]: company for company in get_companies(connection)}


def classify_company_sources(
    companies: list[dict[str, Any]],
    existing_companies: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Classify sources while preserving deliberate skip/manual choices."""

    existing_companies = existing_companies or {}
    classified: list[dict[str, Any]] = []

    for company in companies:
        merged = dict(company)
        existing = existing_companies.get(str(company["name"]))
        if existing:
            if existing.get("careers_url"):
                merged["careers_url"] = existing["careers_url"]
            if existing.get("source_mode") in {"manual_only", "avoid"}:
                merged["source_mode"] = existing["source_mode"]
            if existing.get("status"):
                merged["status"] = existing["status"]

        explicit_mode = str(merged.get("source_mode") or "").strip()
        if explicit_mode == "avoid":
            classified.append(merged)
            continue
        if explicit_mode == "manual_only":
            classified.append(merged)
            continue

        result = classify_source(
            {
                "name": merged["name"],
                "source_name": merged.get("website_category") or merged["name"],
                "website_category": merged.get("website_category"),
                "careers_url": merged.get("careers_url"),
                "ats_hint": merged.get("ats_hint"),
            }
        )
        merged["source_mode"] = result.source_mode
        classified.append(merged)

    return classified


def normalize_job(raw_job: dict[str, Any], company: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw collector job object into the storage shape."""

    return {
        "company_name": str(raw_job.get("company_name") or company["name"]).strip(),
        "title": str(raw_job.get("title") or "").strip(),
        "location": str(raw_job.get("location") or "").strip() or None,
        "job_url": str(raw_job.get("job_url") or "").strip() or None,
        "apply_url": str(raw_job.get("apply_url") or "").strip() or None,
        "source_name": str(
            raw_job.get("source_name")
            or company.get("website_category")
            or company["name"]
        ).strip(),
        "source_mode": str(raw_job.get("source_mode") or company["source_mode"]).strip(),
        "description": str(raw_job.get("description") or "").strip() or None,
        "date_posted": raw_job.get("date_posted"),
        "status": str(raw_job.get("status") or "new").strip(),
    }


def score_normalized_job(job: dict[str, Any]) -> dict[str, Any]:
    """Apply deterministic relevance scoring after collection and dedupe."""

    scored = dict(job)
    score_result = score_job(scored)
    scored["match_score"] = score_result.match_score
    scored["match_reasons"] = score_result.match_reasons
    scored["risk_flags"] = score_result.risk_flags
    return scored


def is_relevant_scored_job(job: dict[str, Any]) -> bool:
    """Return True when a scored job has more than location-only relevance."""

    if int(job.get("match_score", 0)) <= 0:
        return False
    reasons = [str(reason).lower() for reason in job.get("match_reasons", [])]
    return any(
        reason.startswith("title matches")
        or reason.startswith("description mentions")
        or reason.startswith("matched skills")
        or reason.startswith("support/ops signals")
        for reason in reasons
    )


def deduplicate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate normalized jobs in memory before persistence."""

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for job in jobs:
        key = (
            job.get("job_url") or "",
            job.get("company_name") or "",
            job.get("title") or "",
            job.get("location") or "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(job)
    return deduped


def save_jobs(connection, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Persist normalized jobs and return the saved records."""

    saved_jobs: list[dict[str, Any]] = []
    for job in jobs:
        existing = None
        if job.get("job_url"):
            existing = connection.execute(
                "SELECT id FROM jobs WHERE job_url = ?",
                (job["job_url"],),
            ).fetchone()
        job_id = upsert_job(connection, job)
        saved = get_job_by_id(connection, job_id)
        if saved is not None:
            saved["was_new"] = existing is None
            saved_jobs.append(saved)
    return saved_jobs


def default_collectors() -> dict[str, CollectorFunc]:
    """Return default collector functions keyed by source mode."""

    def browser_batch(connection, companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return collect_companies_with_browser(
            connection,
            companies=companies,
            headless=False,
            save_jobs=False,
            allowed_source_modes=ELIGIBLE_SOURCE_MODES,
        )

    return {
        "api_allowed": browser_batch,
        "browser_allowed": browser_batch,
        "human_in_loop": browser_batch,
    }


def build_daily_artifact_paths(
    exports_dir: Path,
    *,
    run_date: date,
) -> DailyRunArtifacts:
    """Build output paths for report and CSV export."""

    exports_dir.mkdir(parents=True, exist_ok=True)
    stamp = run_date.isoformat()
    return DailyRunArtifacts(
        report_path=exports_dir / f"daily-report-{stamp}.md",
        csv_path=exports_dir / f"jobs-{stamp}.csv",
    )


def write_daily_report(
    path: Path,
    *,
    run_date: str,
    companies_checked: list[str],
    companies_skipped: list[dict[str, str]],
    interventions_needed: list[dict[str, Any]],
    errors: list[str],
    jobs: list[dict[str, Any]],
    jobs_discovered: int,
    jobs_scored: int,
    jobs_relevant: int,
    location_scope_used: bool,
    keyword_scope_used: bool,
) -> None:
    """Write a Markdown summary report."""

    top_jobs = sorted(jobs, key=lambda job: int(job.get("match_score", 0)), reverse=True)[:10]

    lines = [
        f"# Daily Job Discovery Report - {run_date}",
        "",
        "## Run Summary",
        f"- Companies checked: {len(companies_checked)}",
        f"- Companies skipped: {len(companies_skipped)}",
        f"- Jobs discovered before scoring: {jobs_discovered}",
        f"- Jobs scored: {jobs_scored}",
        f"- Jobs relevant: {jobs_relevant}",
        f"- Jobs saved: {len(jobs)}",
        f"- Location scope used: {location_scope_used}",
        f"- Keyword scope used: {keyword_scope_used}",
        f"- Interventions needed: {len(interventions_needed)}",
        f"- Errors: {len(errors)}",
        "",
        "## Top Matched Jobs",
    ]

    if top_jobs:
        for job in top_jobs:
            lines.append(
                f"- {job['company_name']} | {job['title']} | score {job['match_score']} | "
                f"{job.get('job_url') or 'no URL'}"
            )
    else:
        lines.append("- No jobs saved in this run.")

    lines.extend(["", "## Companies Checked"])
    if companies_checked:
        lines.extend(f"- {name}" for name in companies_checked)
    else:
        lines.append("- None")

    lines.extend(["", "## Companies Skipped"])
    if companies_skipped:
        lines.extend(
            f"- {item['company_name']} | {item['source_mode']} | {item['reason']}"
            for item in companies_skipped
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Interventions Needed"])
    if interventions_needed:
        lines.extend(
            f"- {item.get('company_name') or '-'} | {item.get('reason') or '-'} | "
            f"{item.get('action_required') or '-'} | {item.get('status') or '-'}"
            for item in interventions_needed
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Errors"])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- None")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_jobs_csv(path: Path, jobs: list[dict[str, Any]]) -> None:
    """Write a CSV export of saved jobs."""

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
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for job in jobs:
            row = {field: job.get(field) for field in fieldnames}
            row["match_reasons"] = yaml.safe_dump(
                job.get("match_reasons", []),
                default_flow_style=True,
            ).strip()
            row["risk_flags"] = yaml.safe_dump(
                job.get("risk_flags", []),
                default_flow_style=True,
            ).strip()
            writer.writerow(row)


def run_daily_workflow(
    *,
    config_path: Path,
    db_path: Path,
    exports_dir: Path,
    run_date: date | None = None,
    collectors: dict[str, CollectorFunc] | None = None,
) -> DailyRunResult:
    """Execute the end-to-end daily workflow."""

    effective_date = run_date or date.today()
    connection = initialize_database(db_path)
    existing_companies = _existing_company_map(connection)
    loaded_companies = load_companies_yaml(config_path)
    classified_companies = classify_company_sources(loaded_companies, existing_companies)
    upsert_companies(connection, classified_companies)

    by_name = {company["name"]: company for company in classified_companies}
    collectors_by_mode = collectors or default_collectors()

    companies_checked: list[str] = []
    companies_skipped: list[dict[str, str]] = []
    errors: list[str] = []
    normalized_jobs: list[dict[str, Any]] = []
    jobs_discovered = 0
    location_scope_used = False
    keyword_scope_used = False

    for company in classified_companies:
        mode = str(company.get("source_mode") or "")
        if mode in SKIPPED_SOURCE_MODES:
            companies_skipped.append(
                {
                    "company_name": company["name"],
                    "source_mode": mode,
                    "reason": f"source mode {mode}",
                }
            )
            continue
        if mode not in ELIGIBLE_SOURCE_MODES:
            companies_skipped.append(
                {
                    "company_name": company["name"],
                    "source_mode": mode or "unknown",
                    "reason": "source mode not eligible",
                }
            )
            continue

        companies_checked.append(company["name"])
        collector = collectors_by_mode.get(mode)
        if collector is None:
            errors.append(f"No collector configured for {company['name']} ({mode})")
            continue

        results = collector(connection, [company])
        for result in results:
            status = str(result.get("status") or "")
            raw_jobs = result.get("jobs", [])
            job_items = raw_jobs if isinstance(raw_jobs, list) else []
            jobs_discovered += int(result.get("jobs_discovered", len(job_items)) or 0)
            location_scope_used = location_scope_used or bool(
                result.get("location_scope_used", False)
            )
            keyword_scope_used = keyword_scope_used or bool(
                result.get("keyword_scope_used", False)
            )
            if status == "error":
                errors.append(
                    f"{result.get('company_name')}: {result.get('error') or 'collector error'}"
                )
            if status == "skipped":
                companies_skipped.append(
                    {
                        "company_name": str(result.get("company_name") or company["name"]),
                        "source_mode": mode,
                        "reason": str(result.get("reason") or "collector skipped"),
                    }
                )
            for raw_job in job_items:
                company_key = str(raw_job.get("company_name") or company["name"])
                normalized_jobs.append(
                    normalize_job(raw_job, by_name[company_key])
                )

    deduped_jobs = deduplicate_jobs(normalized_jobs)
    scored_jobs = [score_normalized_job(job) for job in deduped_jobs]
    relevant_jobs = [job for job in scored_jobs if is_relevant_scored_job(job)]
    saved_jobs = save_jobs(connection, relevant_jobs)
    artifacts = build_daily_artifact_paths(exports_dir, run_date=effective_date)
    write_jobs_csv(artifacts.csv_path, saved_jobs)
    write_daily_report(
        artifacts.report_path,
        run_date=effective_date.isoformat(),
        companies_checked=companies_checked,
        companies_skipped=companies_skipped,
        interventions_needed=get_intervention_queue(connection),
        errors=errors,
        jobs=saved_jobs,
        jobs_discovered=jobs_discovered,
        jobs_scored=len(scored_jobs),
        jobs_relevant=len(relevant_jobs),
        location_scope_used=location_scope_used,
        keyword_scope_used=keyword_scope_used,
    )

    return DailyRunResult(
        run_date=effective_date.isoformat(),
        companies_checked=companies_checked,
        companies_skipped=companies_skipped,
        interventions_needed=get_intervention_queue(connection),
        errors=errors,
        jobs_discovered=jobs_discovered,
        jobs_scored=len(scored_jobs),
        jobs_relevant=len(relevant_jobs),
        jobs_saved=saved_jobs,
        location_scope_used=location_scope_used,
        keyword_scope_used=keyword_scope_used,
        artifacts=artifacts,
    )
