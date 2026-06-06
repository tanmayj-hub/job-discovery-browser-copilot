"""Accuracy audit helpers for MVP trustworthiness validation."""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from storage.db import get_jobs, normalize_job_text, normalize_job_url

AUDIT_SAMPLE_FIELDS = [
    "company_name",
    "mvp_title",
    "mvp_location",
    "mvp_url",
    "mvp_external_job_id",
    "mvp_ats_type",
    "mvp_board_slug",
    "mvp_score",
    "mvp_last_seen_at",
    "manual_title",
    "manual_location",
    "manual_url",
    "manual_found",
    "manual_relevant",
    "audit_status",
    "match_confidence",
    "reason",
    "manual_notes",
]
MANUAL_TEMPLATE_FIELDS = [
    "company_name",
    "manual_title",
    "manual_location",
    "manual_url",
    "manual_external_job_id",
    "manual_source_url",
    "manual_relevant",
    "manual_notes",
]
COMPARE_OUTPUT_FIELDS = [
    "company_name",
    "mvp_title",
    "mvp_location",
    "mvp_url",
    "mvp_external_job_id",
    "mvp_ats_type",
    "mvp_board_slug",
    "mvp_score",
    "mvp_saved_at",
    "manual_title",
    "manual_location",
    "manual_url",
    "manual_external_job_id",
    "manual_source_url",
    "manual_found",
    "manual_relevant",
    "manual_notes",
    "audit_status",
    "match_confidence",
    "reason",
    "audited_by",
    "audited_at",
]
AUDIT_STATUS_VALUES = {
    "matched",
    "false_positive",
    "missing_from_mvp",
    "unclear",
    "not_relevant",
}
MATCH_CONFIDENCE_VALUES = {"high", "medium", "low"}


@dataclass(slots=True)
class AuditMetrics:
    """Precision and recall metrics for an audit slice."""

    company_name: str
    mvp_saved_count: int
    manual_relevant_count: int
    matched_count: int
    false_positive_count: int
    missing_count: int
    unclear_count: int
    precision: float
    recall: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AccuracyAuditResult:
    """Structured result of one MVP-vs-manual comparison."""

    audit_records: list[dict[str, Any]]
    overall_metrics: AuditMetrics
    per_company_metrics: list[AuditMetrics]
    companies_audited: list[str]
    report_path: Path


@dataclass(slots=True)
class ValidationResult:
    """Structured validation outcome for audit CSV files."""

    is_valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CompanyAuditPackResult:
    """Structured result for a single-company manual audit pack."""

    company_name: str
    markdown_path: Path
    mvp_output_path: Path
    manual_output_path: Path
    configured_careers_url: str
    source_mode: str
    ats_type: str
    mvp_rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["markdown_path"] = str(self.markdown_path)
        payload["mvp_output_path"] = str(self.mvp_output_path)
        payload["manual_output_path"] = str(self.manual_output_path)
        return payload


@dataclass(slots=True)
class CompanyCollectionDiagnosticResult:
    """Structured result for a single-company collection diagnostic report."""

    company_name: str
    output_path: Path

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["output_path"] = str(self.output_path)
        return payload


def parse_company_filter(raw: str | None) -> list[str]:
    """Parse a comma-separated company filter into a clean list."""

    if not raw:
        return []
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def export_audit_sample(
    connection: sqlite3.Connection,
    *,
    output_path: Path,
    companies: list[str] | None = None,
    limit_per_company: int = 10,
    include_recent_days: int = 14,
    status: str | None = "new",
) -> list[dict[str, Any]]:
    """Export a reviewable MVP audit sample CSV from saved jobs."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    allowed_companies = {item.strip() for item in (companies or []) if item.strip()}
    jobs = get_jobs(connection, status=status)
    cutoff = datetime.now(UTC) - timedelta(days=max(0, int(include_recent_days)))
    rows_by_company: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for job in jobs:
        company_name = str(job.get("company_name") or "").strip()
        if allowed_companies and company_name not in allowed_companies:
            continue
        seen_at = _parse_timestamp(
            job.get("last_seen_at") or job.get("last_seen") or job.get("updated_at")
        )
        if include_recent_days > 0 and seen_at is not None and seen_at < cutoff:
            continue
        rows_by_company[company_name].append(job)

    exported_rows: list[dict[str, Any]] = []
    for company_name in sorted(rows_by_company):
        company_jobs = sorted(
            rows_by_company[company_name],
            key=lambda item: (
                int(item.get("match_score", 0) or 0),
                str(item.get("last_seen_at") or item.get("last_seen") or ""),
                str(item.get("title") or ""),
            ),
            reverse=True,
        )
        for job in company_jobs[: max(1, int(limit_per_company))]:
            exported_rows.append(
                {
                    "company_name": company_name,
                    "mvp_title": str(job.get("title") or ""),
                    "mvp_location": str(job.get("location") or ""),
                    "mvp_url": str(job.get("job_url") or ""),
                    "mvp_external_job_id": str(job.get("external_job_id") or ""),
                    "mvp_ats_type": str(job.get("ats_type") or ""),
                    "mvp_board_slug": str(job.get("board_slug") or ""),
                    "mvp_score": str(job.get("match_score") or 0),
                    "mvp_last_seen_at": str(
                        job.get("last_seen_at") or job.get("last_seen") or ""
                    ),
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
            )

    _write_csv(output_path, AUDIT_SAMPLE_FIELDS, exported_rows)
    return exported_rows


def create_manual_template(
    *,
    output_path: Path,
    companies: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Create a blank manual-job template CSV for recall auditing."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "company_name": company_name,
            "manual_title": "",
            "manual_location": "",
            "manual_url": "",
            "manual_external_job_id": "",
            "manual_source_url": "",
            "manual_relevant": "",
            "manual_notes": "",
        }
        for company_name in (companies or [])
    ]
    _write_csv(output_path, MANUAL_TEMPLATE_FIELDS, rows)
    return rows


def build_manual_audit_link_sheet(
    connection: sqlite3.Connection,
    *,
    output_path: Path,
    companies_path: Path,
    audit_sample_path: Path,
    manual_template_path: Path,
    companies: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Generate a compact link sheet for the first manual audit pass."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    configured_urls = _load_company_urls(companies_path)
    allowed_companies = companies or sorted(configured_urls)
    sample_rows = _read_csv(audit_sample_path) if audit_sample_path.exists() else []
    manual_rows = _read_csv(manual_template_path) if manual_template_path.exists() else []
    jobs = get_jobs(connection, status="new")
    mvp_count_by_company = defaultdict(int)
    for job in jobs:
        mvp_count_by_company[str(job.get("company_name") or "").strip()] += 1
    sample_count_by_company = defaultdict(int)
    for row in sample_rows:
        sample_count_by_company[str(row.get("company_name") or "").strip()] += 1
    manual_count_by_company = defaultdict(int)
    for row in manual_rows:
        manual_count_by_company[str(row.get("company_name") or "").strip()] += 1

    rows = [
        {
            "company_name": company_name,
            "configured_careers_url": configured_urls.get(company_name, ""),
            "mvp_results_count": mvp_count_by_company.get(company_name, 0),
            "audit_sample_rows": sample_count_by_company.get(company_name, 0),
            "manual_template_rows": manual_count_by_company.get(company_name, 0),
            "notes": "",
        }
        for company_name in allowed_companies
    ]
    _write_csv(
        output_path,
        [
            "company_name",
            "configured_careers_url",
            "mvp_results_count",
            "audit_sample_rows",
            "manual_template_rows",
            "notes",
        ],
        rows,
    )
    return rows


def build_company_audit_pack(
    connection: sqlite3.Connection,
    *,
    company_name: str,
    companies_path: Path,
    markdown_output_path: Path,
    mvp_output_path: Path,
    manual_output_path: Path,
    limit_per_company: int = 10,
    include_recent_days: int = 14,
    status: str | None = "new",
) -> CompanyAuditPackResult:
    """Build a one-company manual audit pack in Markdown plus companion CSV files."""

    requested_name = str(company_name or "").strip()
    company = _find_company_record(companies_path, requested_name)
    if company is None:
        raise ValueError(f"Company not found in config/companies.yaml: {requested_name}")

    resolved_name = str(company.get("name") or "").strip()
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    mvp_rows = export_audit_sample(
        connection,
        output_path=mvp_output_path,
        companies=[resolved_name],
        limit_per_company=limit_per_company,
        include_recent_days=include_recent_days,
        status=status,
    )
    create_manual_template(
        output_path=manual_output_path,
        companies=[resolved_name],
    )

    markdown_output_path.write_text(
        _build_company_audit_markdown(
            company=company,
            mvp_rows=mvp_rows,
            mvp_output_path=mvp_output_path,
            manual_output_path=manual_output_path,
        ),
        encoding="utf-8",
    )

    return CompanyAuditPackResult(
        company_name=resolved_name,
        markdown_path=markdown_output_path,
        mvp_output_path=mvp_output_path,
        manual_output_path=manual_output_path,
        configured_careers_url=str(company.get("careers_url") or "").strip(),
        source_mode=str(company.get("source_mode") or "").strip(),
        ats_type=str(company.get("ats_type") or company.get("ats_hint") or "").strip(),
        mvp_rows=mvp_rows,
    )


def write_company_collection_diagnostic(
    *,
    output_path: Path,
    company: dict[str, Any],
    collection_result: dict[str, Any],
) -> CompanyCollectionDiagnosticResult:
    """Write a focused one-company collection diagnostic report."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    company_name = str(company.get("name") or "").strip()
    candidate_jobs = [
        job for job in collection_result.get("candidate_jobs", []) if isinstance(job, dict)
    ]
    relevant_jobs = [
        job for job in collection_result.get("relevant_jobs", []) if isinstance(job, dict)
    ]
    pages_visited = [
        str(url).strip() for url in collection_result.get("pages_visited", []) if str(url).strip()
    ]
    jobs_per_page = [
        int(count) for count in collection_result.get("jobs_extracted_per_page", [])
    ]
    location_queries = [
        str(item).strip()
        for item in collection_result.get("location_queries", [])
        if str(item).strip()
    ]
    lines = [
        f"# {company_name} Collection Diagnostic",
        "",
        "## Source",
        f"- Company: {company_name}",
        (
            "- Starting URL: "
            f"{collection_result.get('starting_url') or company.get('careers_url') or '-'}"
        ),
        f"- Final URL reached: {collection_result.get('final_url') or '-'}",
        (
            "- Source mode: "
            f"{collection_result.get('source_mode') or company.get('source_mode') or '-'}"
        ),
        f"- ATS type: {collection_result.get('ats_type') or company.get('ats_hint') or '-'}",
        "",
        "## Location Scope",
        f"- Location scope used: {bool(collection_result.get('location_scope_used', False))}",
        f"- Configured locations: {', '.join(collection_result.get('location_scope', [])) or '-'}",
        f"- Location filter/search attempted: {', '.join(location_queries) or 'none'}",
        "",
        "## Pagination",
        f"- Pagination detected: {bool(collection_result.get('pagination_detected', False))}",
        f"- Max pages per source: {collection_result.get('max_pages_per_source') or '-'}",
        f"- Pages visited: {len(pages_visited)}",
        f"- Jobs extracted per page: {jobs_per_page or '-'}",
        f"- Pagination stop reason: {collection_result.get('pagination_stop_reason') or '-'}",
        "",
        "## Counts",
        f"- Candidate jobs before scoring: {collection_result.get('jobs_discovered', 0)}",
        f"- Jobs after scoring: {collection_result.get('jobs_scored', 0)}",
        f"- Relevant jobs after scoring: {collection_result.get('jobs_relevant', 0)}",
        "",
        "## Visited Pages",
    ]
    if pages_visited:
        lines.extend(f"- {url}" for url in pages_visited)
    else:
        lines.append("- None")

    lines.extend(["", "## Candidate Jobs Before Scoring"])
    if candidate_jobs:
        for job in candidate_jobs:
            lines.append(
                f"- {job.get('title') or '-'} | {job.get('location') or '-'} | "
                f"{job.get('job_url') or 'no URL'}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Relevant Jobs After Scoring"])
    if relevant_jobs:
        for job in relevant_jobs:
            lines.append(
                f"- {job.get('title') or '-'} | score {job.get('match_score', 0)} | "
                f"{job.get('location') or '-'} | {job.get('job_url') or 'no URL'}"
            )
    else:
        lines.append("- None")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return CompanyCollectionDiagnosticResult(
        company_name=company_name,
        output_path=output_path,
    )


def validate_audit_files(
    *,
    mvp_path: Path,
    manual_path: Path,
) -> ValidationResult:
    """Validate audit CSV files before a manual compare run."""

    errors: list[str] = []
    mvp_rows, mvp_columns = _read_csv_with_columns(mvp_path)
    manual_rows, manual_columns = _read_csv_with_columns(manual_path)

    missing_mvp = sorted(set(AUDIT_SAMPLE_FIELDS) - set(mvp_columns))
    if missing_mvp:
        errors.append(f"MVP file missing required columns: {', '.join(missing_mvp)}")
    missing_manual = sorted(set(MANUAL_TEMPLATE_FIELDS) - set(manual_columns))
    if missing_manual:
        errors.append(f"Manual file missing required columns: {', '.join(missing_manual)}")

    for index, row in enumerate(mvp_rows, start=2):
        audit_status = str(row.get("audit_status") or "").strip()
        if audit_status and audit_status not in AUDIT_STATUS_VALUES:
            errors.append(
                f"MVP row {index} has invalid audit_status: {audit_status}"
            )
        match_confidence = str(row.get("match_confidence") or "").strip()
        if match_confidence and match_confidence not in MATCH_CONFIDENCE_VALUES:
            errors.append(
                f"MVP row {index} has invalid match_confidence: {match_confidence}"
            )
        manual_found = str(row.get("manual_found") or "").strip()
        if manual_found and _parse_bool(manual_found) is None:
            errors.append(f"MVP row {index} has invalid manual_found value: {manual_found}")
        manual_relevant = str(row.get("manual_relevant") or "").strip()
        if manual_relevant and _parse_bool(manual_relevant) is None:
            errors.append(
                f"MVP row {index} has invalid manual_relevant value: {manual_relevant}"
            )
        for field in ("mvp_url", "manual_url"):
            url = str(row.get(field) or "").strip()
            if url and normalize_job_url(url) is None:
                errors.append(f"MVP row {index} has invalid {field}: {url}")

    seen_manual_rows: set[tuple[str, str, str]] = set()
    for index, row in enumerate(manual_rows, start=2):
        manual_relevant = str(row.get("manual_relevant") or "").strip()
        if manual_relevant and _parse_bool(manual_relevant) is None:
            errors.append(
                f"Manual row {index} has invalid manual_relevant value: {manual_relevant}"
            )
        for field in ("manual_url", "manual_source_url"):
            url = str(row.get(field) or "").strip()
            if url and normalize_job_url(url) is None:
                errors.append(f"Manual row {index} has invalid {field}: {url}")
        identity = (
            _normalize_text(row.get("company_name")),
            _normalize_text(row.get("manual_title")),
            normalize_job_url(row.get("manual_url")) or "",
        )
        if any(identity):
            if identity in seen_manual_rows:
                errors.append(
                    f"Manual row {index} duplicates an earlier company/title/url entry."
                )
            seen_manual_rows.add(identity)

    return ValidationResult(is_valid=not errors, errors=errors)


def compare_audit_files(
    *,
    mvp_path: Path,
    manual_path: Path,
    output_path: Path,
    audited_by: str = "manual_audit",
) -> AccuracyAuditResult:
    """Compare exported MVP jobs against manually verified jobs."""

    mvp_rows = _read_csv(mvp_path)
    manual_rows = _read_csv(manual_path)
    audited_at = _current_timestamp()
    manual_entries = [_build_manual_entry(row) for row in manual_rows]
    audit_records: list[dict[str, Any]] = []

    for raw_mvp in mvp_rows:
        mvp_entry = _build_mvp_entry(raw_mvp)
        match = _match_manual_entry(mvp_entry, manual_entries)
        if match is not None:
            entry, confidence, reason = match
            entry["matched"] = True
            audit_records.append(
                _build_audit_record(
                    mvp_entry=mvp_entry,
                    manual_entry=entry,
                    audit_status="matched" if entry["manual_relevant"] else "not_relevant",
                    match_confidence=confidence,
                    reason=reason,
                    audited_by=audited_by,
                    audited_at=audited_at,
                )
            )
            continue

        manual_found = _parse_bool(raw_mvp.get("manual_found"))
        manual_relevant = _parse_bool(raw_mvp.get("manual_relevant"))
        if manual_found is False:
            audit_status = "false_positive"
            confidence = "high"
            reason = "Manual verification marked the MVP row as not found on the official source."
        elif manual_relevant is False:
            audit_status = "not_relevant"
            confidence = "high"
            reason = "Manual verification marked the MVP row as not relevant."
        elif manual_found is True and manual_relevant is True:
            audit_status = "matched"
            confidence = "low"
            reason = (
                "Manual verification marked the MVP row as relevant without a "
                "separate match row."
            )
        else:
            audit_status = "unclear"
            confidence = "low"
            reason = (
                "No deterministic manual match or completed verification fields "
                "were available."
            )
        audit_records.append(
            _build_audit_record(
                mvp_entry=mvp_entry,
                manual_entry=_build_manual_entry(raw_mvp),
                audit_status=audit_status,
                match_confidence=confidence,
                reason=reason,
                audited_by=audited_by,
                audited_at=audited_at,
            )
        )

    for entry in manual_entries:
        if entry["matched"] or not entry["manual_relevant"]:
            continue
        audit_records.append(
            _build_audit_record(
                mvp_entry={},
                manual_entry=entry,
                audit_status="missing_from_mvp",
                match_confidence="high",
                reason="Relevant manual job was not matched to any MVP-saved result.",
                audited_by=audited_by,
                audited_at=audited_at,
            )
        )

    companies_audited = sorted(
        {
            str(record.get("company_name") or "").strip()
            for record in audit_records
            if str(record.get("company_name") or "").strip()
        }
    )
    overall_metrics = calculate_metrics("Overall", audit_records)
    per_company_metrics = [calculate_metrics(name, audit_records) for name in companies_audited]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_accuracy_report(
        output_path,
        audit_records=audit_records,
        overall_metrics=overall_metrics,
        per_company_metrics=per_company_metrics,
        companies_audited=companies_audited,
        mvp_path=mvp_path,
        manual_path=manual_path,
    )
    return AccuracyAuditResult(
        audit_records=audit_records,
        overall_metrics=overall_metrics,
        per_company_metrics=per_company_metrics,
        companies_audited=companies_audited,
        report_path=output_path,
    )


def calculate_metrics(company_name: str, audit_records: list[dict[str, Any]]) -> AuditMetrics:
    """Calculate precision and recall for one company slice or overall."""

    records = (
        [
            item
            for item in audit_records
            if str(item.get("company_name") or "").strip() == company_name
        ]
        if company_name != "Overall"
        else list(audit_records)
    )
    mvp_saved_count = sum(1 for item in records if item.get("mvp_title"))
    manual_relevant_count = sum(
        1 for item in records if _parse_bool(item.get("manual_relevant")) is True
    )
    matched_count = sum(1 for item in records if item.get("audit_status") == "matched")
    false_positive_count = sum(
        1
        for item in records
        if item.get("audit_status") in {"false_positive", "not_relevant"}
    )
    missing_count = sum(1 for item in records if item.get("audit_status") == "missing_from_mvp")
    unclear_count = sum(1 for item in records if item.get("audit_status") == "unclear")
    precision = _safe_ratio(matched_count, mvp_saved_count)
    recall = _safe_ratio(matched_count, manual_relevant_count)
    return AuditMetrics(
        company_name=company_name,
        mvp_saved_count=mvp_saved_count,
        manual_relevant_count=manual_relevant_count,
        matched_count=matched_count,
        false_positive_count=false_positive_count,
        missing_count=missing_count,
        unclear_count=unclear_count,
        precision=precision,
        recall=recall,
    )


def write_accuracy_report(
    path: Path,
    *,
    audit_records: list[dict[str, Any]],
    overall_metrics: AuditMetrics,
    per_company_metrics: list[AuditMetrics],
    companies_audited: list[str],
    mvp_path: Path,
    manual_path: Path,
) -> None:
    """Write the markdown accuracy audit report."""

    verdict = _build_verdict(overall_metrics)
    matched = [item for item in audit_records if item.get("audit_status") == "matched"]
    false_positives = [
        item
        for item in audit_records
        if item.get("audit_status") in {"false_positive", "not_relevant"}
    ]
    missing = [
        item for item in audit_records if item.get("audit_status") == "missing_from_mvp"
    ]
    unclear = [item for item in audit_records if item.get("audit_status") == "unclear"]
    recommendations = _summarize_recommendations(audit_records)

    lines = [
        "# Accuracy Audit Report",
        "",
        "## Verdict",
        f"- {verdict}",
        "",
        "## Audit Scope",
        f"- MVP file: {mvp_path}",
        f"- Manual file: {manual_path}",
        f"- Audit records: {len(audit_records)}",
        f"- MVP saved rows reviewed: {overall_metrics.mvp_saved_count}",
        f"- Manual relevant rows reviewed: {overall_metrics.manual_relevant_count}",
        "",
        "## Companies Audited",
    ]
    if companies_audited:
        lines.extend(f"- {name}" for name in companies_audited)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Overall Metrics",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| MVP saved count | {overall_metrics.mvp_saved_count} |",
            f"| Manual relevant count | {overall_metrics.manual_relevant_count} |",
            f"| Matched count | {overall_metrics.matched_count} |",
            f"| False positive count | {overall_metrics.false_positive_count} |",
            f"| Missing count | {overall_metrics.missing_count} |",
            f"| Unclear count | {overall_metrics.unclear_count} |",
            f"| Precision | {overall_metrics.precision:.3f} |",
            f"| Recall | {overall_metrics.recall:.3f} |",
            "",
            "## Per-Company Metrics",
            (
                "| Company | MVP Saved | Manual Relevant | Matched | False Positives | "
                "Missing | Unclear | Precision | Recall |"
            ),
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    if per_company_metrics:
        for metric in per_company_metrics:
            lines.append(
                f"| {metric.company_name} | {metric.mvp_saved_count} | "
                f"{metric.manual_relevant_count} | {metric.matched_count} | "
                f"{metric.false_positive_count} | {metric.missing_count} | "
                f"{metric.unclear_count} | {metric.precision:.3f} | {metric.recall:.3f} |"
            )
    else:
        lines.append("| None | 0 | 0 | 0 | 0 | 0 | 0 | 0.000 | 0.000 |")

    lines.extend(["", "## Matched Jobs"])
    lines.extend(_format_record_lines(matched) or ["- None"])
    lines.extend(["", "## False Positives"])
    lines.extend(_format_record_lines(false_positives) or ["- None"])
    lines.extend(["", "## Missing Jobs"])
    lines.extend(_format_record_lines(missing) or ["- None"])
    lines.extend(["", "## Unclear Jobs"])
    lines.extend(_format_record_lines(unclear) or ["- None"])
    lines.extend(["", "## Recommended Fixes"])
    lines.extend(recommendations or ["- No recommendations from the current audit slice."])
    lines.extend(["", "## Next Action"])
    lines.extend(_next_actions(overall_metrics, missing, false_positives, unclear))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _match_manual_entry(
    mvp_entry: dict[str, Any],
    manual_entries: list[dict[str, Any]],
) -> tuple[dict[str, Any], str, str] | None:
    company_name = _normalize_text(mvp_entry.get("company_name"))
    external_job_id = _normalize_text(mvp_entry.get("mvp_external_job_id"))
    normalized_url = normalize_job_url(mvp_entry.get("mvp_url"))
    fallback_key = _fallback_match_key(
        company_name,
        mvp_entry.get("mvp_title"),
        mvp_entry.get("mvp_location"),
    )

    if external_job_id:
        for entry in manual_entries:
            if entry["matched"]:
                continue
            if _normalize_text(entry.get("company_name")) != company_name:
                continue
            if _normalize_text(entry.get("manual_external_job_id")) == external_job_id:
                return (
                    entry,
                    "high",
                    "Matched by external_job_id.",
                )

    if normalized_url:
        for entry in manual_entries:
            if entry["matched"]:
                continue
            if _normalize_text(entry.get("company_name")) != company_name:
                continue
            if normalize_job_url(entry.get("manual_url")) == normalized_url:
                return (
                    entry,
                    "high",
                    "Matched by normalized URL.",
                )

    for entry in manual_entries:
        if entry["matched"]:
            continue
        if _normalize_text(entry.get("company_name")) != company_name:
            continue
        if _fallback_match_key(
            company_name,
            entry.get("manual_title"),
            entry.get("manual_location"),
        ) == fallback_key:
            return (
                entry,
                "medium",
                "Matched by normalized title + company + location.",
            )
    return None


def _build_mvp_entry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "company_name": str(row.get("company_name") or "").strip(),
        "mvp_title": str(row.get("mvp_title") or "").strip(),
        "mvp_location": str(row.get("mvp_location") or "").strip(),
        "mvp_url": str(row.get("mvp_url") or "").strip(),
        "mvp_external_job_id": str(row.get("mvp_external_job_id") or "").strip(),
        "mvp_ats_type": str(row.get("mvp_ats_type") or "").strip(),
        "mvp_board_slug": str(row.get("mvp_board_slug") or "").strip(),
        "mvp_score": str(row.get("mvp_score") or "").strip(),
        "mvp_saved_at": str(row.get("mvp_last_seen_at") or row.get("mvp_saved_at") or "").strip(),
    }


def _build_manual_entry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "company_name": str(row.get("company_name") or "").strip(),
        "manual_title": str(row.get("manual_title") or "").strip(),
        "manual_location": str(row.get("manual_location") or "").strip(),
        "manual_url": str(row.get("manual_url") or "").strip(),
        "manual_external_job_id": str(row.get("manual_external_job_id") or "").strip(),
        "manual_source_url": str(row.get("manual_source_url") or "").strip(),
        "manual_found": _parse_bool(row.get("manual_found")),
        "manual_relevant": _parse_bool(row.get("manual_relevant")),
        "manual_notes": str(row.get("manual_notes") or "").strip(),
        "matched": False,
    }


def _build_audit_record(
    *,
    mvp_entry: dict[str, Any],
    manual_entry: dict[str, Any],
    audit_status: str,
    match_confidence: str,
    reason: str,
    audited_by: str,
    audited_at: str,
) -> dict[str, Any]:
    record = {
        "company_name": str(
            mvp_entry.get("company_name") or manual_entry.get("company_name") or ""
        ).strip(),
        "mvp_title": str(mvp_entry.get("mvp_title") or "").strip(),
        "mvp_location": str(mvp_entry.get("mvp_location") or "").strip(),
        "mvp_url": str(mvp_entry.get("mvp_url") or "").strip(),
        "mvp_external_job_id": str(mvp_entry.get("mvp_external_job_id") or "").strip(),
        "mvp_ats_type": str(mvp_entry.get("mvp_ats_type") or "").strip(),
        "mvp_board_slug": str(mvp_entry.get("mvp_board_slug") or "").strip(),
        "mvp_score": str(mvp_entry.get("mvp_score") or "").strip(),
        "mvp_saved_at": str(mvp_entry.get("mvp_saved_at") or "").strip(),
        "manual_title": str(manual_entry.get("manual_title") or "").strip(),
        "manual_location": str(manual_entry.get("manual_location") or "").strip(),
        "manual_url": str(manual_entry.get("manual_url") or "").strip(),
        "manual_external_job_id": str(
            manual_entry.get("manual_external_job_id") or ""
        ).strip(),
        "manual_source_url": str(manual_entry.get("manual_source_url") or "").strip(),
        "manual_found": manual_entry.get("manual_found"),
        "manual_relevant": manual_entry.get("manual_relevant"),
        "manual_notes": str(manual_entry.get("manual_notes") or "").strip(),
        "audit_status": audit_status,
        "match_confidence": match_confidence,
        "reason": reason,
        "audited_by": audited_by,
        "audited_at": audited_at,
    }
    return record


def _format_record_lines(records: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in records:
        title = item.get("mvp_title") or item.get("manual_title") or "-"
        url = item.get("mvp_url") or item.get("manual_url") or "no URL"
        lines.append(
            f"- {item.get('company_name') or '-'} | {title} | "
            f"{item.get('audit_status') or '-'} | {url} | {item.get('reason') or '-'}"
        )
    return lines


def _summarize_recommendations(audit_records: list[dict[str, Any]]) -> list[str]:
    categories = defaultdict(int)
    for item in audit_records:
        categories[_recommendation_for_record(item)] += 1
    return [
        f"- {category}: {count}"
        for category, count in sorted(categories.items())
        if count > 0
    ]


def _recommendation_for_record(record: dict[str, Any]) -> str:
    status = str(record.get("audit_status") or "")
    reason = str(record.get("reason") or "").lower()
    mvp_url = str(record.get("mvp_url") or "").lower()
    if status == "missing_from_mvp":
        if any(hint in reason for hint in ("login", "captcha", "manual")):
            return "manual/source limitation"
        return "extraction issue"
    if status in {"false_positive", "not_relevant"}:
        if not mvp_url:
            return "source URL issue"
        if any(
            hint in mvp_url for hint in ("/careers", "/search", "/job-search", "/locations")
        ):
            return "extraction issue"
        return "scoring issue"
    if status == "unclear":
        return "manual/source limitation"
    return "no action"


def _next_actions(
    overall_metrics: AuditMetrics,
    missing: list[dict[str, Any]],
    false_positives: list[dict[str, Any]],
    unclear: list[dict[str, Any]],
) -> list[str]:
    actions: list[str] = []
    if missing:
        actions.append(
            "- Review missing jobs first to identify extraction gaps on audited sources."
        )
    if false_positives:
        actions.append(
            "- Review false positives to decide whether extraction or scoring rules "
            "need tuning."
        )
    if unclear:
        actions.append(
            "- Resolve unclear rows with manual verification before drawing strong "
            "conclusions."
        )
    if overall_metrics.precision >= 0.8 and overall_metrics.recall >= 0.8:
        actions.append(
            "- Expand the audit to more companies to confirm the quality holds "
            "beyond this slice."
        )
    if not actions:
        actions.append(
            "- Export a fresh audit sample and continue manual verification on "
            "another source set."
        )
    return actions


def _build_verdict(metrics: AuditMetrics) -> str:
    if metrics.mvp_saved_count == 0 and metrics.manual_relevant_count == 0:
        return "No audited jobs were available yet, so precision and recall are not meaningful."
    if metrics.precision >= 0.8 and metrics.recall >= 0.8:
        return "The audited slice looks strong: both precision and recall are healthy."
    if metrics.precision >= 0.8:
        return "Precision looks better than recall; focus next on missed jobs."
    if metrics.recall >= 0.8:
        return "Recall looks better than precision; focus next on false positives."
    return "The audited slice still needs improvement in both precision and recall."


def _safe_ratio(numerator: int, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_timestamp(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_bool(value: object) -> bool | None:
    normalized = normalize_job_text(value)
    if normalized in {"true", "yes", "1", "y"}:
        return True
    if normalized in {"false", "no", "0", "n"}:
        return False
    return None


def _normalize_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize_job_text(value)).strip()


def _fallback_match_key(company_name: str, title: object, location: object) -> tuple[str, str, str]:
    return (company_name, _normalize_text(title), _normalize_text(location))


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _read_csv_with_columns(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    with path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def _load_company_urls(path: Path) -> dict[str, str]:
    companies = _load_company_records(path)
    return {
        str(item.get("name") or "").strip(): str(item.get("careers_url") or "").strip()
        for item in companies
        if str(item.get("name") or "").strip()
    }


def _load_company_records(path: Path) -> list[dict[str, Any]]:
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    companies = payload.get("companies", [])
    return companies if isinstance(companies, list) else []


def _find_company_record(path: Path, company_name: str) -> dict[str, Any] | None:
    target = _normalize_text(company_name)
    for company in _load_company_records(path):
        if _normalize_text(company.get("name")) == target:
            return company
    return None


def _build_company_audit_markdown(
    *,
    company: dict[str, Any],
    mvp_rows: list[dict[str, Any]],
    mvp_output_path: Path,
    manual_output_path: Path,
) -> str:
    company_name = str(company.get("name") or "").strip()
    careers_url = str(company.get("careers_url") or "").strip() or "Not configured"
    source_mode = str(company.get("source_mode") or "").strip() or "Unknown"
    ats_type = str(company.get("ats_type") or company.get("ats_hint") or "").strip() or "Unknown"

    lines = [
        f"# {company_name} Manual Accuracy Audit",
        "",
        "## Configured Source",
        f"- Company: {company_name}",
        f"- Careers URL: {careers_url}",
        f"- Source mode: {source_mode}",
        f"- ATS type if available: {ats_type}",
        "",
        "## MVP Jobs Found",
        f"- MVP sample CSV: `{mvp_output_path}`",
        "| # | MVP title | MVP location | MVP URL | Manual result | Relevant | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    if mvp_rows:
        for index, row in enumerate(mvp_rows, start=1):
            mvp_url = str(row.get("mvp_url") or "").strip()
            url_cell = f"[Open job]({mvp_url})" if mvp_url else "-"
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(index),
                        _escape_table_cell(row.get("mvp_title")),
                        _escape_table_cell(row.get("mvp_location")),
                        url_cell,
                        " ",
                        " ",
                        " ",
                    ]
                )
                + " |"
            )
    else:
        lines.append(
            "| - | No MVP jobs found in the selected audit slice | - | - |  |  |  |"
        )

    lines.extend(
        [
            "",
            "## Manual Website Check",
            "Instructions:",
            f"- Open the configured career URL: {careers_url}",
            "- Search broad terms:",
            "  - Cloud",
            "  - DevOps",
            "  - Infrastructure",
            "  - Platform",
            "  - Systems",
            "  - Linux",
            "  - Support",
            "  - AWS",
            "  - Engineer",
            "  - Analyst",
            "- Mark each MVP row as `correct`, `wrong`, or `unclear`.",
            "- Mark `Relevant` as `yes` or `no` based on the project target roles.",
            "",
            "## Jobs Found Manually That MVP Missed",
            f"- Manual template CSV: `{manual_output_path}`",
            "| title | location | URL | why relevant | notes |",
            "| --- | --- | --- | --- | --- |",
            "|  |  |  |  |  |",
            "|  |  |  |  |  |",
            "|  |  |  |  |  |",
            "",
            "## Summary",
            "- MVP jobs checked: ",
            "- Correct: ",
            "- Wrong: ",
            "- Unclear: ",
            "- Missed jobs found manually: ",
            "- Main issue noticed: ",
            "",
            "## How To Use This Pack",
            "- Review the MVP rows above first.",
            "- Confirm each job on the official career page.",
            "- Add missed relevant jobs to the manual template CSV.",
            "- After filling the CSVs, run:",
            (
                "  `python -m src.main audit compare --mvp <mvp-sample.csv> "
                "--manual <manual-template.csv> --output docs/accuracy-audit-report.md`"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _escape_table_cell(value: object) -> str:
    text = str(value or "").replace("|", "\\|").replace("\n", " ").strip()
    return text or "-"


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
