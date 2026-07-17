"""Accuracy audit helpers for MVP trustworthiness validation."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from processing.score import explain_job_score
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
SCORED_CANDIDATE_FIELDS = [
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
]
MANUAL_URL_AUDIT_STATUSES = {
    "saved_by_mvp",
    "extracted_and_relevant",
    "extracted_but_rejected_by_scoring",
    "missed_by_collection",
    "outside_scope",
    "inactive_or_expired",
    "active_but_not_in_current_listing",
    "outside_current_listing_scope",
    "manual_intervention_required",
    "blocked_or_not_tested",
    "unknown",
}
MANUAL_URL_AUDIT_STATUS_ORDER = [
    "saved_by_mvp",
    "extracted_and_relevant",
    "extracted_but_rejected_by_scoring",
    "outside_scope",
    "inactive_or_expired",
    "active_but_not_in_current_listing",
    "outside_current_listing_scope",
    "manual_intervention_required",
    "missed_by_collection",
    "blocked_or_not_tested",
    "unknown",
]


def _chunk_metadata_path(csv_path: Path) -> Path:
    return csv_path.with_suffix(".chunk.json")


def write_company_audit_chunk_metadata(
    *,
    csv_path: Path,
    company: dict[str, Any],
    collection_result: dict[str, Any],
) -> Path:
    """Persist deterministic, audit-only coverage evidence beside a chunk CSV."""

    metadata_path = _chunk_metadata_path(csv_path)
    payload = {
        "company": str(company.get("name") or "").strip(),
        "official_source": str(company.get("careers_url") or "").strip(),
        "source_scope_confirmed": bool(collection_result.get("source_scope_confirmed")),
        "source_scope_method": str(collection_result.get("source_scope_method") or ""),
        "sort_requested": str(collection_result.get("sort_requested") or ""),
        "sort_used": str(collection_result.get("sort_used") or ""),
        "sort_status": str(collection_result.get("sort_status") or ""),
        "requested_page_start": int(collection_result.get("requested_page_start", 1) or 1),
        "requested_page_end": int(collection_result.get("requested_page_end", 1) or 1),
        "page_numbers": [int(value) for value in collection_result.get("page_numbers", [])],
        "page_fingerprints": [
            str(value) for value in collection_result.get("page_fingerprints", [])
        ],
        "pages_visited": [str(value) for value in collection_result.get("pages_visited", [])],
        "pagination_stop_reason": str(collection_result.get("pagination_stop_reason") or ""),
        "pagination_complete": bool(collection_result.get("pagination_complete")),
        "jobs_discovered": int(collection_result.get("jobs_discovered", 0) or 0),
        "jobs_relevant": int(collection_result.get("jobs_relevant", 0) or 0),
        "full_page_serializations": int(
            collection_result.get("full_page_serializations", 0) or 0
        ),
        "page_timings_ms": collection_result.get("page_timings_ms", []),
        "operation_timings_ms": collection_result.get("operation_timings_ms", {}),
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return metadata_path


def merge_company_audit_chunks(
    *,
    company_name: str,
    inputs: list[Path],
    output_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Merge deterministic audit chunks only when their coverage evidence agrees."""

    metadata_rows: list[dict[str, Any]] = []
    for csv_path in inputs:
        metadata_path = _chunk_metadata_path(csv_path)
        if not metadata_path.exists():
            raise ValueError(f"missing audit chunk metadata: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if str(metadata.get("company") or "") != company_name:
            raise ValueError(f"chunk company mismatch: {csv_path}")
        if not bool(metadata.get("source_scope_confirmed")):
            raise ValueError(f"chunk has unconfirmed Canada scope: {csv_path}")
        metadata_rows.append(metadata)

    metadata_rows.sort(key=lambda item: int(item["requested_page_start"]))
    expected_page = int(metadata_rows[0]["requested_page_start"]) if metadata_rows else 1
    page_gaps: list[int] = []
    duplicate_pages: list[int] = []
    duplicate_fingerprints: list[str] = []
    seen_pages: set[int] = set()
    seen_fingerprints: set[str] = set()
    source_values = {str(row.get("official_source") or "") for row in metadata_rows}
    sort_values = {
        (str(row.get("sort_requested") or ""), str(row.get("sort_used") or ""))
        for row in metadata_rows
    }
    for row in metadata_rows:
        start = int(row["requested_page_start"])
        end = int(row["requested_page_end"])
        if start != expected_page:
            page_gaps.extend(range(expected_page, start))
        expected_page = end + 1
        for page_number in row.get("page_numbers", []):
            page_number = int(page_number)
            if page_number in seen_pages:
                duplicate_pages.append(page_number)
            seen_pages.add(page_number)
        for fingerprint in row.get("page_fingerprints", []):
            fingerprint = str(fingerprint)
            if fingerprint and fingerprint in seen_fingerprints:
                duplicate_fingerprints.append(fingerprint)
            seen_fingerprints.add(fingerprint)

    all_rows: list[dict[str, str]] = []
    for csv_path in inputs:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            all_rows.extend(csv.DictReader(handle))
    unique_rows: list[dict[str, str]] = []
    seen_jobs: set[str] = set()
    for row in all_rows:
        identity = normalize_job_url(str(row.get("url") or "")) or normalize_job_text(
            f"{row.get('title', '')}|{row.get('location', '')}"
        )
        if identity in seen_jobs:
            continue
        seen_jobs.add(identity)
        unique_rows.append(row)
    _write_csv(output_path, SCORED_CANDIDATE_FIELDS, unique_rows)

    target_pages = list(range(int(metadata_rows[0]["requested_page_start"]), expected_page))
    missing_pages = sorted(set(target_pages) - seen_pages)
    complete = (
        len(source_values) == 1
        and len(sort_values) == 1
        and not page_gaps
        and not missing_pages
        and not duplicate_pages
        and not duplicate_fingerprints
    )
    result = {
        "company": company_name,
        "target_pages": target_pages,
        "actual_pages": sorted(seen_pages),
        "page_gaps": page_gaps + missing_pages,
        "duplicate_pages": sorted(set(duplicate_pages)),
        "duplicate_fingerprints": len(duplicate_fingerprints),
        "discovered_before_dedupe": len(all_rows),
        "unique_discovered": len(unique_rows),
        "relevant": sum(row.get("is_relevant") == "true" for row in unique_rows),
        "complete": complete,
        "verification_eligible": complete,
        "chunks": [str(path) for path in inputs],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                f"# {company_name} Chunked Collection Audit",
                "",
                f"- Target pages: {target_pages[0]}-{target_pages[-1]}",
                f"- Actual pages covered: {', '.join(map(str, result['actual_pages']))}",
                f"- Chunk list: {', '.join(result['chunks'])}",
                f"- Page gaps: {result['page_gaps'] or 'none'}",
                f"- Duplicate pages: {result['duplicate_pages'] or 'none'}",
                f"- Duplicate fingerprints: {result['duplicate_fingerprints']}",
                f"- Total discovered before dedupe: {result['discovered_before_dedupe']}",
                f"- Unique discovered: {result['unique_discovered']}",
                f"- Scored: {result['unique_discovered']}",
                f"- Relevant/saved: {result['relevant']}",
                f"- Complete: {result['complete']}",
                f"- Verification eligibility: {result['verification_eligible']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return result


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


@dataclass(slots=True)
class ScoreExplanationResult:
    """Structured result for a one-job scoring explanation report."""

    company_name: str
    title: str
    output_path: Path
    source: str
    explanation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["output_path"] = str(self.output_path)
        return payload


@dataclass(slots=True)
class ManualUrlRecallAuditResult:
    """Structured result for manual-URL recall auditing."""

    records: list[dict[str, Any]]
    summary: dict[str, Any]
    report_path: Path

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["report_path"] = str(self.report_path)
        return payload


@dataclass(slots=True)
class ManualUrlAuditSummaryResult:
    """Structured result for a compact manual URL audit summary."""

    report_path: Path

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["report_path"] = str(self.report_path)
        return payload


def parse_company_filter(raw: str | None) -> list[str]:
    """Parse a comma-separated company filter into a clean list."""

    if not raw:
        return []
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _normalize_loaded_manual_expected_job(item: object) -> dict[str, Any] | None:
    if isinstance(item, dict):
        return dict(item)
    text = str(item or "").strip()
    if not text:
        return None
    if text.startswith(("https://", "http://")):
        return {
            "job_url": text,
            "title": "",
            "notes": "",
        }
    return None


def load_manual_expected_jobs(path: Path) -> list[dict[str, Any]]:
    """Load the structured manual expected job fixture."""

    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    companies = payload.get("companies", [])
    if not isinstance(companies, list):
        return []

    normalized_companies: list[dict[str, Any]] = []
    for raw_company in companies:
        if not isinstance(raw_company, dict):
            continue
        company = dict(raw_company)
        normalized_expected_jobs: list[dict[str, Any]] = []
        extra_notes: list[str] = []
        for item in raw_company.get("expected_jobs", []) or []:
            normalized_job = _normalize_loaded_manual_expected_job(item)
            if normalized_job is not None:
                normalized_expected_jobs.append(normalized_job)
                continue
            note_text = str(item or "").strip()
            if note_text:
                extra_notes.append(note_text)
        company["expected_jobs"] = normalized_expected_jobs
        existing_notes = str(company.get("notes") or "").strip()
        combined_notes = " ".join([part for part in [existing_notes, *extra_notes] if part]).strip()
        if combined_notes:
            company["notes"] = combined_notes
        normalized_companies.append(company)
    return normalized_companies


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


def export_scored_candidates(
    *,
    output_path: Path,
    scored_jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Export scored candidates so rejected jobs can be audited later."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for job in sorted(
        scored_jobs,
        key=lambda item: (
            int(item.get("match_score", 0) or 0),
            str(item.get("title") or ""),
        ),
        reverse=True,
    ):
        explanation = explain_job_score(job)
        rows.append(
            {
                "company": str(job.get("company_name") or "").strip(),
                "title": str(job.get("title") or "").strip(),
                "location": str(job.get("location") or "").strip(),
                "url": str(job.get("job_url") or "").strip(),
                "score": int(job.get("match_score", 0) or 0),
                "is_relevant": "true" if explanation["is_relevant"] else "false",
                "relevance_tier": explanation["relevance_tier"],
                "matched_terms": "; ".join(explanation["positive_keyword_matches"]),
                "reason": explanation["reason_summary"],
                "match_reasons": "; ".join(explanation["match_reasons"]),
                "risk_flags": "; ".join(explanation["risk_flags"]),
                "rejection_reason": (
                    explanation["reason_summary"] if not explanation["is_relevant"] else ""
                ),
                "description": str(job.get("description") or "").strip(),
                "source_mode": str(job.get("source_mode") or "").strip(),
            }
        )
    _write_csv(output_path, SCORED_CANDIDATE_FIELDS, rows)
    return rows


def write_company_collection_diagnostic(
    *,
    output_path: Path,
    company: dict[str, Any],
    collection_result: dict[str, Any],
    scored_candidates_output_path: Path | None = None,
    manual_expected_jobs: list[dict[str, Any]] | None = None,
    saved_jobs: list[dict[str, Any]] | None = None,
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
    scored_jobs = [job for job in collection_result.get("scored_jobs", []) if isinstance(job, dict)]
    if scored_candidates_output_path is not None and scored_jobs:
        export_scored_candidates(
            output_path=scored_candidates_output_path,
            scored_jobs=scored_jobs,
        )
    pages_visited = [
        str(url).strip() for url in collection_result.get("pages_visited", []) if str(url).strip()
    ]
    jobs_per_page = [
        int(count) for count in collection_result.get("jobs_extracted_per_page", [])
    ]
    page_numbers = [int(value) for value in collection_result.get("page_numbers", [])]
    page_fingerprints = [
        str(value) for value in collection_result.get("page_fingerprints", []) if str(value)
    ]
    requested_page_end = (
        collection_result.get("requested_page_end")
        or collection_result.get("max_pages_per_source")
        or "-"
    )
    page_html_snapshots = [
        snapshot
        for snapshot in collection_result.get("page_html_snapshots", [])
        if isinstance(snapshot, dict)
    ]
    location_queries = [
        str(item).strip()
        for item in collection_result.get("location_queries", [])
        if str(item).strip()
    ]
    source_scope_status = str(collection_result.get("source_scope_status") or "").strip()
    source_scope_confirmed = bool(collection_result.get("source_scope_confirmed", False))
    source_scope_method = str(collection_result.get("source_scope_method") or "").strip()
    source_scope_reason = str(collection_result.get("source_scope_reason") or "").strip()
    source_url_used = str(
        collection_result.get("source_url_used")
        or collection_result.get("final_url")
        or collection_result.get("starting_url")
        or company.get("careers_url")
        or ""
    ).strip()
    broad_diagnostic_collection = bool(
        collection_result.get("broad_diagnostic_collection", False)
    )
    non_canada_rejected = int(collection_result.get("non_canada_rejected", 0) or 0)
    unknown_location_relevant = int(
        collection_result.get("unknown_location_relevant", 0) or 0
    )
    extracted_identifiers = _collect_company_url_identities(candidate_jobs)
    manual_expected_summary = _summarize_manual_expected_coverage(
        candidate_jobs,
        manual_expected_jobs or [],
    )
    manual_expected_diagnostics = _build_manual_expected_diagnostics(
        manual_expected_jobs=manual_expected_jobs or [],
        page_html_snapshots=page_html_snapshots,
        candidate_jobs=candidate_jobs,
        scored_jobs=scored_jobs,
        saved_jobs=saved_jobs or [],
    )
    verification_decision = "needs_review"
    verification_reason = "Canada source scope was not confirmed before pagination."
    if broad_diagnostic_collection:
        verification_decision = "diagnostic_only"
        verification_reason = (
            "Broad collection was allowed only for diagnostics and must not be treated "
            "as trusted verification evidence."
        )
    elif source_scope_confirmed:
        verification_decision = "ready_for_verified_review"
        verification_reason = (
            "Canada source scope was confirmed before pagination and no diagnostic-only "
            "fallback was required."
        )
        if non_canada_rejected > 0:
            verification_reason = (
                "Canada source scope was confirmed before pagination, and the safety gate "
                "rejected explicit out-of-scope rows before any save/export step."
            )
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
        f"- Cookie banner action: {collection_result.get('cookie_dismissed') or 'none'}",
        f"- Language prompt action: {collection_result.get('language_prompt_action') or 'none'}",
        "",
        "## Source Scope Validation",
        f"- Source URL used: {source_url_used or '-'}",
        f"- Source scope status: {source_scope_status or '-'}",
        f"- Canada scope confirmed before pagination: {source_scope_confirmed}",
        f"- Source scope method: {source_scope_method or '-'}",
        f"- Source scope reason: {source_scope_reason or '-'}",
        f"- Broad diagnostic collection: {broad_diagnostic_collection}",
        "",
        "## Location Scope",
        f"- Location scope used: {bool(collection_result.get('location_scope_used', False))}",
        f"- Configured locations: {', '.join(collection_result.get('location_scope', [])) or '-'}",
        f"- Location filter/search attempted: {', '.join(location_queries) or 'none'}",
        (
            "- Exact filter method: "
            f"{collection_result.get('location_filter_method') or 'none'}"
        ),
        "",
        "## Pagination",
        (
            "- Requested page range: "
            f"{collection_result.get('requested_page_start') or 1}-"
            f"{requested_page_end}"
        ),
        f"- Page policy: {collection_result.get('page_policy') or 'capped'}",
        f"- Target page cap: {collection_result.get('target_page_cap') or 'all available'}",
        f"- Pagination detected: {bool(collection_result.get('pagination_detected', False))}",
        (
            "- Next/load-more detection result: "
            + (
                "detected"
                if collection_result.get("pagination_detected", False)
                else "not detected"
            )
        ),
        f"- Max pages per source: {collection_result.get('max_pages_per_source') or '-'}",
        f"- Pages visited: {len(pages_visited)}",
        f"- Actual page numbers: {page_numbers or '-'}",
        f"- Page fingerprints captured: {len(page_fingerprints)}",
        f"- Jobs extracted per page: {jobs_per_page or '-'}",
        f"- Pagination stop reason: {collection_result.get('pagination_stop_reason') or '-'}",
        f"- Pagination complete: {bool(collection_result.get('pagination_complete', False))}",
        f"- Normal stop: {bool(collection_result.get('pagination_stop_normal', False))}",
        (
            "- Engineering fix required: "
            f"{bool(collection_result.get('pagination_engineering_fix_required', False))}"
        ),
        "",
        "## Sort Policy",
        f"- Sort requested: {collection_result.get('sort_requested') or '-'}",
        f"- Sort used: {collection_result.get('sort_used') or '-'}",
        f"- Sort status: {collection_result.get('sort_status') or '-'}",
        f"- Sort method: {collection_result.get('sort_method') or '-'}",
        f"- Sort reason: {collection_result.get('sort_reason') or '-'}",
        "",
        "## Counts",
        f"- Candidate jobs before scoring: {collection_result.get('jobs_discovered', 0)}",
        f"- Jobs after scoring: {collection_result.get('jobs_scored', 0)}",
        f"- Relevant jobs after scoring: {collection_result.get('jobs_relevant', 0)}",
        f"- Explicit non-Canada jobs rejected by safety gate: {non_canada_rejected}",
        f"- Relevant jobs with unknown/blank location text: {unknown_location_relevant}",
        f"- Unique IBM jobIds extracted: {len(extracted_identifiers['ibm_job_ids'])}",
        f"- Unique Workday job IDs extracted: {len(extracted_identifiers['workday_job_ids'])}",
        (
            "- Scored candidates CSV: "
            f"{scored_candidates_output_path if scored_candidates_output_path is not None else '-'}"
        ),
        "",
        "## Visited Pages",
    ]
    operation_timings = collection_result.get("operation_timings_ms", {})
    page_timings = collection_result.get("page_timings_ms", [])
    if operation_timings or page_timings:
        lines.extend(
            [
                "",
                "## Timing",
                f"- Operation timings (ms): {operation_timings or '-'}",
                f"- Page timing samples (ms): {page_timings or '-'}",
                (
                    "- Full-page serializations: "
                    f"{collection_result.get('full_page_serializations', 0)}"
                ),
            ]
        )
    if pages_visited:
        lines.extend(f"- {url}" for url in pages_visited)
    else:
        lines.append("- None")

    lines.extend(["", "## Verification Decision"])
    lines.append(f"- Decision: {verification_decision}")
    lines.append(f"- Reason: {verification_reason}")

    if manual_expected_jobs:
        lines.extend(["", "## Manual Expected Coverage"])
        lines.append(f"- Manual expected URLs provided: {len(manual_expected_jobs)}")
        lines.append(
            "- Matching manual expected URLs found: "
            f"{manual_expected_summary['matched_count']} / "
            f"{manual_expected_summary['expected_count']}"
        )
        lines.append(
            "- Manual expected URLs still missing: "
            f"{manual_expected_summary['missing_count']}"
        )
        if manual_expected_summary["found_workday_job_ids"] or manual_expected_summary[
            "missing_workday_job_ids"
        ]:
            lines.append(
                "- Matching manual Workday job IDs found: "
                f"{', '.join(manual_expected_summary['found_workday_job_ids']) or 'none'}"
            )
            lines.append(
                "- Manual Workday job IDs still missing: "
                f"{', '.join(manual_expected_summary['missing_workday_job_ids']) or 'none'}"
            )
        if manual_expected_summary["found_ibm_job_ids"] or manual_expected_summary[
            "missing_ibm_job_ids"
        ]:
            lines.append(
                "- Matching manual IBM jobIds found: "
                f"{', '.join(manual_expected_summary['found_ibm_job_ids']) or 'none'}"
            )
            lines.append(
                "- Manual IBM jobIds still missing: "
                f"{', '.join(manual_expected_summary['missing_ibm_job_ids']) or 'none'}"
            )
        lines.extend(
            [
                "",
                (
                    "| Manual URL | Manual Title | Raw HTML | Anchor href | Script/JSON | "
                    "Extracted | Scored | Saved by MVP | Status | Reason |"
                ),
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in manual_expected_diagnostics:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _escape_table_cell(item.get("manual_url")),
                        _escape_table_cell(item.get("manual_title")),
                        _escape_table_cell(item.get("found_in_raw_html")),
                        _escape_table_cell(item.get("found_as_anchor_href")),
                        _escape_table_cell(item.get("found_in_script_text")),
                        _escape_table_cell(item.get("extracted_as_candidate")),
                        _escape_table_cell(item.get("scored_candidate")),
                        _escape_table_cell(item.get("saved_by_mvp")),
                        _escape_table_cell(item.get("status")),
                        _escape_table_cell(item.get("reason")),
                    ]
                )
                + " |"
            )

    lines.extend(["", "## Candidate Jobs Before Scoring"])
    if candidate_jobs:
        for job in candidate_jobs:
            lines.append(
                f"- {job.get('title') or '-'} | {job.get('location') or '-'} | "
                f"{job.get('job_url') or 'no URL'}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Scored Candidates"])
    if scored_jobs:
        for job in sorted(
            scored_jobs,
            key=lambda item: (
                int(item.get("match_score", 0) or 0),
                str(item.get("title") or ""),
            ),
            reverse=True,
        ):
            explanation = explain_job_score(job)
            lines.append(
                f"- {job.get('title') or '-'} | score {job.get('match_score', 0)} | "
                f"relevant={explanation['is_relevant']} | "
                f"tier={explanation['relevance_tier']} | "
                f"{'; '.join(explanation['match_reasons']) or 'no core matches'} | "
                f"{job.get('job_url') or 'no URL'}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Relevant Jobs After Scoring"])
    if relevant_jobs:
        for job in relevant_jobs:
            lines.append(
                f"- {job.get('title') or '-'} | score {job.get('match_score', 0)} | "
                f"tier={explain_job_score(job)['relevance_tier']} | "
                f"{job.get('location') or '-'} | {job.get('job_url') or 'no URL'}"
            )
    else:
        lines.append("- None")

    rejected_interesting_jobs = [
        job
        for job in scored_jobs
        if _is_interesting_rejected_job(job)
    ]
    lines.extend(["", "## Rejected But Interesting Jobs"])
    if rejected_interesting_jobs:
        for job in sorted(
            rejected_interesting_jobs,
            key=lambda item: (
                int(item.get("match_score", 0) or 0),
                str(item.get("title") or ""),
            ),
            reverse=True,
        ):
            explanation = explain_job_score(job)
            lines.append(
                f"- {job.get('title') or '-'} | score {job.get('match_score', 0)} | "
                f"{explanation['reason_summary']} | {job.get('job_url') or 'no URL'}"
            )
    else:
        lines.append("- None")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return CompanyCollectionDiagnosticResult(
        company_name=company_name,
        output_path=output_path,
    )


def _collect_company_url_identities(rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    identifiers = {
        "ibm_job_ids": set(),
        "workday_job_ids": set(),
    }
    for row in rows:
        identity = _url_identity(str(row.get("job_url") or row.get("url") or ""))
        if identity["ibm_job_id"]:
            identifiers["ibm_job_ids"].add(identity["ibm_job_id"])
        if identity["workday_job_id"]:
            identifiers["workday_job_ids"].add(identity["workday_job_id"])
    return identifiers


def _summarize_manual_expected_coverage(
    candidate_jobs: list[dict[str, Any]],
    manual_expected_jobs: list[dict[str, Any]],
) -> dict[str, int | list[str]]:
    found_ibm_job_ids: list[str] = []
    missing_ibm_job_ids: list[str] = []
    found_workday_job_ids: list[str] = []
    missing_workday_job_ids: list[str] = []
    matched_count = 0
    for expected_job in manual_expected_jobs:
        manual_url = str(expected_job.get("job_url") or "").strip()
        matched = _find_matching_job_record(
            manual_url,
            candidate_jobs,
            url_field="job_url",
            manual_title=str(expected_job.get("title") or "").strip(),
        )
        identity = _url_identity(manual_url)
        ibm_job_id = identity["ibm_job_id"]
        workday_job_id = identity["workday_job_id"]
        if matched is not None:
            matched_count += 1
        if ibm_job_id:
            if matched is not None:
                found_ibm_job_ids.append(ibm_job_id)
            else:
                missing_ibm_job_ids.append(ibm_job_id)
        if workday_job_id:
            if matched is not None:
                found_workday_job_ids.append(workday_job_id)
            else:
                missing_workday_job_ids.append(workday_job_id)
    return {
        "expected_count": len(manual_expected_jobs),
        "matched_count": matched_count,
        "missing_count": max(0, len(manual_expected_jobs) - matched_count),
        "found_ibm_job_ids": sorted(found_ibm_job_ids),
        "missing_ibm_job_ids": sorted(missing_ibm_job_ids),
        "found_workday_job_ids": sorted(found_workday_job_ids),
        "missing_workday_job_ids": sorted(missing_workday_job_ids),
    }


def _build_manual_expected_diagnostics(
    *,
    manual_expected_jobs: list[dict[str, Any]],
    page_html_snapshots: list[dict[str, Any]],
    candidate_jobs: list[dict[str, Any]],
    scored_jobs: list[dict[str, Any]],
    saved_jobs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    for expected_job in manual_expected_jobs:
        manual_url = str(expected_job.get("job_url") or "").strip()
        manual_title = str(expected_job.get("title") or "").strip()
        raw_presence = _find_manual_job_in_page_snapshots(
            manual_url=manual_url,
            manual_title=manual_title,
            page_html_snapshots=page_html_snapshots,
        )
        extracted_match = _find_matching_job_record(
            manual_url,
            candidate_jobs,
            url_field="job_url",
            manual_title=manual_title,
        )
        scored_match = _find_matching_job_record(
            manual_url,
            scored_jobs,
            url_field="job_url",
            manual_title=manual_title,
        )
        saved_match = _find_matching_job_record(
            manual_url,
            saved_jobs,
            url_field="job_url",
            manual_title=manual_title,
        )
        status_details = _classify_manual_expected_match(
            saved_match=saved_match,
            scored_match=scored_match,
            scored_export_exists=True,
        )
        diagnostics.append(
            {
                "manual_url": manual_url,
                "manual_title": manual_title,
                "found_in_raw_html": _yes_no(raw_presence["found_in_raw_html"]),
                "found_as_anchor_href": _yes_no(raw_presence["found_as_anchor_href"]),
                "found_in_script_text": _yes_no(raw_presence["found_in_script_text"]),
                "extracted_as_candidate": _yes_no(extracted_match is not None),
                "scored_candidate": _yes_no(scored_match is not None),
                "saved_by_mvp": _yes_no(saved_match is not None),
                "status": str(status_details["status"]),
                "reason": _manual_expected_diagnostic_reason(
                    raw_presence=raw_presence,
                    extracted_match=extracted_match,
                    status_details=status_details,
                ),
            }
        )
    return diagnostics


def _find_manual_job_in_page_snapshots(
    *,
    manual_url: str,
    manual_title: str,
    page_html_snapshots: list[dict[str, Any]],
) -> dict[str, bool]:
    manual_identity = _url_identity(manual_url)
    found_in_raw_html = False
    found_as_anchor_href = False
    found_in_script_text = False
    normalized_title = _normalize_text(manual_title)

    for snapshot in page_html_snapshots:
        html = str(snapshot.get("html") or "")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")

        if _raw_html_matches_manual_job(html, manual_identity, normalized_title):
            found_in_raw_html = True
        if _anchor_matches_manual_job(soup, manual_identity, normalized_title):
            found_as_anchor_href = True
        if _script_matches_manual_job(soup, manual_identity, normalized_title):
            found_in_script_text = True

    return {
        "found_in_raw_html": found_in_raw_html,
        "found_as_anchor_href": found_as_anchor_href,
        "found_in_script_text": found_in_script_text,
    }


def _raw_html_matches_manual_job(
    html: str,
    manual_identity: dict[str, str],
    normalized_title: str,
) -> bool:
    markers = _manual_identity_markers(manual_identity)
    if any(marker in html for marker in markers):
        return True
    if normalized_title:
        return normalized_title in _normalize_text(html)
    return False


def _anchor_matches_manual_job(
    soup: BeautifulSoup,
    manual_identity: dict[str, str],
    normalized_title: str,
) -> bool:
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if href and _url_identities_match(manual_identity, _url_identity(href)):
            return True
        anchor_text = _normalize_text(anchor.get_text(" ", strip=True))
        if normalized_title and anchor_text == normalized_title:
            return True
    return False


def _script_matches_manual_job(
    soup: BeautifulSoup,
    manual_identity: dict[str, str],
    normalized_title: str,
) -> bool:
    markers = _manual_identity_markers(manual_identity)
    for script in soup.select("script"):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        if any(marker in raw for marker in markers):
            return True
        if normalized_title and normalized_title in _normalize_text(raw):
            return True
    return False


def _manual_identity_markers(manual_identity: dict[str, str]) -> list[str]:
    markers: list[str] = []
    if manual_identity["ibm_job_id"]:
        markers.extend(
            [
                f"jobId={manual_identity['ibm_job_id']}",
                f"jobId\\u003d{manual_identity['ibm_job_id']}",
                manual_identity["ibm_job_id"],
            ]
        )
    if manual_identity["workday_job_id"]:
        markers.append(manual_identity["workday_job_id"])
    if manual_identity["njoyn_job_id"]:
        markers.extend(
            [
                f"Jobid={manual_identity['njoyn_job_id']}",
                f"jobid={manual_identity['njoyn_job_id']}",
                manual_identity["njoyn_job_id"],
            ]
        )
    if manual_identity["njoyn_brid"]:
        markers.extend(
            [
                f"BRID={manual_identity['njoyn_brid']}",
                f"brid={manual_identity['njoyn_brid']}",
                manual_identity["njoyn_brid"],
            ]
        )
    canonical_url = manual_identity["canonical_url"]
    if canonical_url:
        markers.append(canonical_url)
    return [marker for marker in markers if marker]


def _manual_expected_diagnostic_reason(
    *,
    raw_presence: dict[str, bool],
    extracted_match: dict[str, Any] | None,
    status_details: dict[str, Any],
) -> str:
    if extracted_match is not None:
        return str(status_details.get("reason") or "-")
    if raw_presence["found_as_anchor_href"]:
        return "job anchor present in DOM but extraction did not emit a candidate"
    if raw_presence["found_in_script_text"]:
        return "job identifier only appeared in script/embedded data"
    if raw_presence["found_in_raw_html"]:
        return "job identifier appeared in raw HTML but not in a matched anchor"
    return "job not present in captured page HTML"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


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


def find_job_for_score_explanation(
    connection: sqlite3.Connection,
    *,
    company_name: str,
    title: str | None = None,
    url: str | None = None,
    scored_candidates_path: Path | None = None,
    include_rejected: bool = False,
) -> tuple[dict[str, Any], str]:
    """Find one job for score explanation from saved jobs or scored candidate exports."""

    normalized_company = _normalize_text(company_name)
    normalized_title = _normalize_text(title)
    normalized_url = normalize_job_url(url)

    saved_jobs = get_jobs(connection)
    for job in saved_jobs:
        if _normalize_text(job.get("company_name")) != normalized_company:
            continue
        if normalized_title and _normalize_text(job.get("title")) != normalized_title:
            continue
        if normalized_url and normalize_job_url(job.get("job_url")) != normalized_url:
            continue
        if title or url:
            return job, "database_saved_job"

    if include_rejected and scored_candidates_path is not None and scored_candidates_path.exists():
        for row in _read_csv(scored_candidates_path):
            if _normalize_text(row.get("company")) != normalized_company:
                continue
            if normalized_title and _normalize_text(row.get("title")) != normalized_title:
                continue
            if normalized_url and normalize_job_url(row.get("url")) != normalized_url:
                continue
            return (
                {
                    "company_name": str(row.get("company") or "").strip(),
                    "title": str(row.get("title") or "").strip(),
                    "location": str(row.get("location") or "").strip(),
                    "job_url": str(row.get("url") or "").strip(),
                    "description": str(row.get("description") or "").strip(),
                    "source_mode": str(row.get("source_mode") or "").strip(),
                },
                "scored_candidates_export",
            )

    lookup = title or url or company_name
    raise ValueError(
        "No matching job found for score explanation: "
        f"{lookup}. Saved jobs were checked first"
        + (
            f", then {scored_candidates_path}."
            if include_rejected and scored_candidates_path is not None
            else "."
        )
    )


def write_score_explanation_report(
    *,
    output_path: Path,
    job: dict[str, Any],
    source: str,
) -> ScoreExplanationResult:
    """Write a focused Markdown score explanation for one job."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    explanation = explain_job_score(job)
    lines = [
        f"# {explanation['title'] or 'Job'} Score Explanation",
        "",
        "## Job",
        f"- Company: {explanation['company'] or '-'}",
        f"- Title: {explanation['title'] or '-'}",
        f"- Location: {explanation['location'] or '-'}",
        f"- URL: {job.get('job_url') or '-'}",
        f"- Source mode: {job.get('source_mode') or '-'}",
        f"- Explanation source: {source}",
        "",
        "## Score Result",
        f"- Final score: {explanation['final_score']}",
        f"- Is relevant: {explanation['is_relevant']}",
        f"- Threshold: {explanation['threshold']}",
        f"- Summary: {explanation['reason_summary']}",
        "",
        "## Positive Matches",
        f"- Title matches: {', '.join(explanation['title_matches']) or 'None'}",
        f"- Description/snippet matches: {', '.join(explanation['description_matches']) or 'None'}",
        (
            "- Positive keyword matches: "
            f"{', '.join(explanation['positive_keyword_matches']) or 'None'}"
        ),
        f"- Location/scope signals: {', '.join(explanation['location_scope_signals']) or 'None'}",
        f"- Support/ops signals: {', '.join(explanation['support_signal_matches']) or 'None'}",
        "",
        "## Negative Matches",
        (
            "- Negative keyword matches: "
            f"{', '.join(explanation['negative_keyword_matches']) or 'None'}"
        ),
        f"- Risk flags: {', '.join(explanation['risk_flags']) or 'None'}",
        "",
        "## Match Reasons",
    ]
    if explanation["match_reasons"]:
        lines.extend(f"- {reason}" for reason in explanation["match_reasons"])
    else:
        lines.append("- None")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ScoreExplanationResult(
        company_name=str(explanation["company"] or "").strip(),
        title=str(explanation["title"] or "").strip(),
        output_path=output_path,
        source=source,
        explanation=explanation,
    )


def compare_manual_expected_urls(
    connection: sqlite3.Connection,
    *,
    companies: list[dict[str, Any]],
    scored_candidates_dir: Path,
) -> dict[str, Any]:
    """Compare manually expected URLs against saved jobs and scored candidate exports."""

    saved_jobs = get_jobs(connection)
    saved_jobs_by_company: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for job in saved_jobs:
        saved_jobs_by_company[str(job.get("company_name") or "").strip()].append(job)

    records: list[dict[str, Any]] = []
    for company in companies:
        company_name = str(company.get("company_name") or "").strip()
        slug = _slugify_company_name(company_name)
        export_path = scored_candidates_dir / f"{slug}-scored-candidates.csv"
        scored_rows = _read_csv(export_path) if export_path.exists() else []
        for item in company.get("expected_jobs", []):
            record = _compare_manual_expected_job(
                company=company,
                expected_job=item,
                saved_jobs=saved_jobs_by_company.get(company_name, []),
                scored_rows=scored_rows,
                scored_export_exists=export_path.exists(),
            )
            records.append(record)

    summary = _summarize_manual_url_records(records)
    return {
        "records": records,
        "summary": summary,
    }


def write_manual_url_recall_report(
    path: Path,
    *,
    companies: list[dict[str, Any]],
    audit_records: list[dict[str, Any]],
    summary: dict[str, Any],
) -> ManualUrlRecallAuditResult:
    """Write the manual URL recall audit Markdown report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Manual URL Recall Audit",
        "",
        "## Scope",
        "- Companies audited: "
        + (", ".join(str(company.get("company_name") or "-") for company in companies) or "-"),
        "- Manual filter used: Canada only",
        "- City/province/remote filters: not applied",
        "- Pages checked manually: first 10 pages per source",
        "",
        "## Manual Expected URL Counts",
        "| Company | Expected URLs |",
        "| --- | ---: |",
    ]
    for company in companies:
        lines.append(
            f"| {company.get('company_name') or '-'} | "
            f"{len(company.get('expected_jobs', []))} |"
        )

    lines.extend(
        [
            "",
            "## Summary",
            "| Status | Count |",
            "| --- | ---: |",
        ]
    )
    for status in MANUAL_URL_AUDIT_STATUS_ORDER:
        lines.append(f"| {status} | {int(summary['status_counts'].get(status, 0))} |")

    lines.extend(["", "## Per-Company Status Counts"])
    for company in companies:
        company_name = str(company.get("company_name") or "").strip()
        company_summary = summary["per_company"].get(company_name, {})
        counts_text = ", ".join(
            f"{status}={count}"
            for status, count in (
                (status, company_summary.get(status, 0))
                for status in MANUAL_URL_AUDIT_STATUS_ORDER
                if company_summary.get(status, 0)
            )
        ) or "none"
        lines.append(f"- {company_name}: {counts_text}")

    lines.extend(["", "## Per-Company Analysis"])
    for company in companies:
        company_name = str(company.get("company_name") or "").strip()
        company_records = [
            record for record in audit_records if record.get("company_name") == company_name
        ]
        lines.extend(
            [
                f"### {company_name}",
                f"- Manual career page: {company.get('manual_career_page') or '-'}",
                f"- Filter used: {company.get('manual_filter_used') or '-'}",
                f"- Pages checked: {company.get('pages_checked') or '-'}",
                "",
                (
                    "| Manual URL | Manual Title | Status | Matched Title | Score | "
                    "Tier | Reasons | Rejection/Notes |"
                ),
                "| --- | --- | --- | --- | ---: | --- | --- | --- |",
            ]
        )
        if company_records:
            for record in company_records:
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            _escape_table_cell(record.get("manual_job_url")),
                            _escape_table_cell(record.get("manual_title")),
                            _escape_table_cell(record.get("status")),
                            _escape_table_cell(record.get("matched_title")),
                            _escape_table_cell(record.get("score")),
                            _escape_table_cell(record.get("relevance_tier")),
                            _escape_table_cell(record.get("matched_reasons")),
                            _escape_table_cell(
                                record.get("rejection_reason") or record.get("notes")
                            ),
                        ]
                    )
                    + " |"
                )
        else:
            lines.append("| - | - | - | - | - | - | - | - |")

    lines.extend(["", "## Scoring And Tier Analysis"])
    lines.append(
        "- `core_target_fit` keeps the original Cloud/DevOps/Admin/Support target intact."
    )
    lines.append(
        "- `adjacent_customer_facing_technical_fit` captures targeted solutions, "
        "customer-engineering, "
        "technical consulting, and similar adjacent roles."
    )
    lines.append(
        "- `outside_scope` is used when a manual URL was collected but still does not "
        "match the current "
        "core or adjacent target definitions."
    )

    lines.extend(["", "## Recommended Fixes"])
    lines.extend(_manual_url_recommendations(audit_records))

    lines.extend(["", "## Remaining Limitations"])
    lines.append(
        "- Saved-job comparison only reflects what already exists in SQLite; "
        "scored-candidate exports are "
        "still required to distinguish rejection from collection misses."
    )
    lines.append(
        "- IBM and other non-Workday search pages may still depend on site-specific "
        "public filters that "
        "are not uniformly exposed through one generic search control."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ManualUrlRecallAuditResult(
        records=audit_records,
        summary=summary,
        report_path=path,
    )


def write_first_manual_url_audit_summary(
    path: Path,
    *,
    companies: list[dict[str, Any]],
    audit_records: list[dict[str, Any]],
    summary: dict[str, Any],
) -> ManualUrlAuditSummaryResult:
    """Write a compact summary for the first three-company manual URL audit slice."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# First 3-Company Manual URL Audit Summary",
        "",
        "## Audit Scope",
        "- Companies: "
        + (", ".join(str(company.get("company_name") or "-") for company in companies) or "-"),
        "- Filter used: Canada only",
        "- Pages checked: first 10 pages per company",
        "- Sources reviewed: official company career pages only",
        "",
        "## Manual Expected Counts",
        "| Company | Expected URLs |",
        "| --- | ---: |",
    ]
    for company in companies:
        lines.append(
            f"| {company.get('company_name') or '-'} | "
            f"{len(company.get('expected_jobs', []))} |"
        )

    lines.extend(["", "## Final Status Counts", "| Status | Count |", "| --- | ---: |"])
    for status in MANUAL_URL_AUDIT_STATUS_ORDER:
        lines.append(f"| {status} | {int(summary['status_counts'].get(status, 0))} |")

    lines.extend(["", "## Per-Company Results"])
    for company in companies:
        company_name = str(company.get("company_name") or "").strip()
        company_records = [
            record for record in audit_records if record.get("company_name") == company_name
        ]
        company_summary = summary["per_company"].get(company_name, {})
        counts_text = ", ".join(
            f"{status}={company_summary.get(status, 0)}"
            for status in MANUAL_URL_AUDIT_STATUS_ORDER
            if company_summary.get(status, 0)
        ) or "none"
        lines.append(f"- {company_name}: {counts_text}")
        for record in company_records:
            lines.append(
                "  - "  # placeholder to be normalized below
                + f"{record.get('manual_title') or record.get('manual_job_url')}: "
                + f"{record.get('status')}"
            )

    remaining_misses = [
        record for record in audit_records if record.get("status") == "missed_by_collection"
    ]
    lines.extend(["", "## Remaining Collection Misses"])
    if remaining_misses:
        for record in remaining_misses:
            lines.append(
                f"- {record.get('company_name')}: "
                f"{record.get('manual_title') or record.get('manual_job_url')} "
                f"({record.get('manual_job_url')})"
            )
    else:
        lines.append("- None")

    scope_debates = [
        record
        for record in audit_records
        if record.get("status") in {"extracted_but_rejected_by_scoring", "outside_scope"}
    ]
    lines.extend(["", "## Remaining Scoring Or Scope Debates"])
    if scope_debates:
        for record in scope_debates:
            title_text = (
                record.get("manual_title")
                or record.get("matched_title")
                or record.get("manual_job_url")
            )
            reason_text = (
                record.get("rejection_reason")
                or record.get("matched_reasons")
                or "no additional reason"
            )
            lines.append(
                f"- {record.get('company_name')}: "
                f"{title_text} "
                f"-> {record.get('status')} "
                f"({reason_text})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Recommendation"])
    if remaining_misses:
        lines.append(
            "- Collection follow-up is still needed for the remaining missed manual URL slice."
        )
    else:
        lines.append("- No additional collection fix is required for this 3-company slice.")
    if any(record.get("status") == "extracted_but_rejected_by_scoring" for record in audit_records):
        lines.append(
            "- Scoring changes are not yet recommended broadly; "
            "review rejected-but-extracted rows case by case."
        )
    else:
        lines.append("- No immediate scoring fix is required for the current audited URLs.")
    lines.append(
        "- TD `Software Engineer II, Salesforce` remains a scope decision only if it "
        "reappears in a future collected slice; title-only evidence is not enough "
        "to promote it."
    )
    lines.append(
        "- Move to the next company audit after documenting any remaining "
        "collection gaps."
    )

    normalized_lines = [line[2:] if line.startswith("  - ") else line for line in lines]
    path.write_text("\n".join(normalized_lines) + "\n", encoding="utf-8")
    return ManualUrlAuditSummaryResult(report_path=path)


def _compare_manual_expected_job(
    *,
    company: dict[str, Any],
    expected_job: dict[str, Any],
    saved_jobs: list[dict[str, Any]],
    scored_rows: list[dict[str, Any]],
    scored_export_exists: bool,
) -> dict[str, Any]:
    manual_url = str(expected_job.get("job_url") or "").strip()
    manual_title = str(expected_job.get("title") or "").strip()
    notes = str(expected_job.get("notes") or "").strip()

    saved_match = _find_matching_job_record(
        manual_url,
        saved_jobs,
        url_field="job_url",
        manual_title=manual_title,
    )
    scored_match = _find_matching_job_record(
        manual_url,
        scored_rows,
        url_field="url",
        manual_title=manual_title,
    )
    status_details = _classify_manual_expected_match(
        saved_match=saved_match,
        scored_match=scored_match,
        scored_export_exists=scored_export_exists,
    )

    return {
        "company_name": str(company.get("company_name") or "").strip(),
        "manual_career_page": str(company.get("manual_career_page") or "").strip(),
        "manual_filter_used": str(company.get("manual_filter_used") or "").strip(),
        "pages_checked": str(company.get("pages_checked") or "").strip(),
        "manual_job_url": manual_url,
        "manual_title": manual_title,
        "matched_title": str(status_details.get("matched_title") or "").strip(),
        "matched_url": str(status_details.get("matched_url") or "").strip(),
        "status": str(status_details.get("status") or "unknown"),
        "score": status_details.get("score", ""),
        "is_relevant": bool(status_details.get("is_relevant", False)),
        "relevance_tier": str(status_details.get("relevance_tier") or "not_relevant"),
        "matched_reasons": str(status_details.get("matched_reasons") or "").strip(),
        "rejection_reason": str(status_details.get("reason") or "").strip(),
        "notes": notes,
    }


def _classify_manual_expected_match(
    *,
    saved_match: dict[str, Any] | None,
    scored_match: dict[str, Any] | None,
    scored_export_exists: bool,
) -> dict[str, Any]:
    if saved_match is not None:
        explanation = explain_job_score(saved_match)
        return {
            "matched_title": str(saved_match.get("title") or "").strip(),
            "matched_url": str(saved_match.get("job_url") or "").strip(),
            "status": "saved_by_mvp",
            "score": int(saved_match.get("match_score", 0) or 0),
            "is_relevant": True,
            "relevance_tier": explanation["relevance_tier"],
            "matched_reasons": "; ".join(explanation["match_reasons"]),
            "reason": "",
        }

    if scored_match is None:
        return {
            "matched_title": "",
            "matched_url": "",
            "status": "missed_by_collection" if scored_export_exists else "blocked_or_not_tested",
            "score": "",
            "is_relevant": False,
            "relevance_tier": "not_relevant",
            "matched_reasons": "",
            "reason": "",
        }

    if "score" in scored_match or "is_relevant" in scored_match:
        score = int(str(scored_match.get("score") or 0).strip() or 0)
        is_relevant = _parse_boolish(scored_match.get("is_relevant"))
        relevance_tier = str(scored_match.get("relevance_tier") or "not_relevant").strip()
        matched_reasons = str(scored_match.get("match_reasons") or "").strip()
        rejection_reason = str(
            scored_match.get("rejection_reason") or scored_match.get("reason") or ""
        ).strip()
    else:
        explanation = explain_job_score(scored_match)
        score = int(scored_match.get("match_score", 0) or 0)
        is_relevant = bool(explanation["is_relevant"])
        relevance_tier = str(explanation["relevance_tier"] or "not_relevant").strip()
        matched_reasons = "; ".join(explanation["match_reasons"])
        rejection_reason = str(explanation["reason_summary"] or "").strip()
    if is_relevant:
        status = "extracted_and_relevant"
    elif score <= 0 and not matched_reasons:
        status = "outside_scope"
    else:
        status = "extracted_but_rejected_by_scoring"

    return {
        "matched_title": str(scored_match.get("title") or "").strip(),
        "matched_url": str(
            scored_match.get("url") or scored_match.get("job_url") or ""
        ).strip(),
        "status": status,
        "score": score,
        "is_relevant": bool(is_relevant),
        "relevance_tier": relevance_tier,
        "matched_reasons": matched_reasons,
        "reason": rejection_reason,
    }


def _find_matching_job_record(
    manual_url: str,
    rows: list[dict[str, Any]],
    *,
    url_field: str,
    manual_title: str = "",
) -> dict[str, Any] | None:
    manual_key = _url_identity(manual_url)
    for row in rows:
        candidate_url = str(row.get(url_field) or "").strip()
        if not candidate_url:
            continue
        if _url_identities_match(manual_key, _url_identity(candidate_url)):
            return row
    if manual_title:
        normalized_title = _normalize_text(manual_title)
        title_matches = [
            row
            for row in rows
            if _normalize_text(row.get("title")) == normalized_title
        ]
        if len(title_matches) == 1:
            return title_matches[0]
    return None


def _url_identity(url: str) -> dict[str, str]:
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(str(url or "").strip())
    query = parse_qs(parsed.query)
    query_lower = {str(key).lower(): value for key, value in query.items()}
    ibm_job_id = ""
    if query_lower.get("jobid"):
        ibm_job_id = str(query_lower["jobid"][0]).strip()
    workday_match = re.search(r"(R_\d+(?:-\d+)?|JR\d+(?:-\d+)?)", str(url or ""), re.I)
    workday_id = workday_match.group(1).upper() if workday_match else ""
    workday_base_id = re.sub(r"-\d+$", "", workday_id) if workday_id else ""
    njoyn_job_id = ""
    if query_lower.get("jobid"):
        njoyn_job_id = str(query_lower["jobid"][0]).strip().upper()
    njoyn_brid = ""
    if query_lower.get("brid"):
        njoyn_brid = str(query_lower["brid"][0]).strip()
    canonical = ""
    if parsed.scheme and parsed.netloc:
        canonical = (
            f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
        )
    return {
        "ibm_job_id": ibm_job_id,
        "workday_job_id": workday_id,
        "workday_base_id": workday_base_id,
        "njoyn_job_id": njoyn_job_id,
        "njoyn_brid": njoyn_brid,
        "canonical_url": canonical,
    }


def _url_identities_match(left: dict[str, str], right: dict[str, str]) -> bool:
    if left["ibm_job_id"] or right["ibm_job_id"]:
        return bool(left["ibm_job_id"] and left["ibm_job_id"] == right["ibm_job_id"])
    if left["workday_job_id"] or right["workday_job_id"]:
        if not (left["workday_job_id"] and right["workday_job_id"]):
            return False
        return (
            left["workday_job_id"] == right["workday_job_id"]
            or bool(left["workday_base_id"])
            and left["workday_base_id"] == right["workday_base_id"]
        )
    if (
        left["njoyn_job_id"]
        or right["njoyn_job_id"]
        or left["njoyn_brid"]
        or right["njoyn_brid"]
    ):
        if left["njoyn_job_id"] and right["njoyn_job_id"]:
            return left["njoyn_job_id"] == right["njoyn_job_id"]
        if left["njoyn_brid"] and right["njoyn_brid"]:
            return left["njoyn_brid"] == right["njoyn_brid"]
        return False
    return bool(left["canonical_url"] and left["canonical_url"] == right["canonical_url"])


def _parse_boolish(value: object) -> bool:
    return normalize_job_text(value) in {"true", "yes", "1", "y"}


def _slugify_company_name(company_name: str) -> str:
    return "-".join(
        segment
        for segment in "".join(
            char if char.isalnum() else "-" for char in str(company_name or "").strip()
        ).split("-")
        if segment
    ) or "company"


def _summarize_manual_url_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_status = defaultdict(int)
    by_company: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in records:
        status = str(record.get("status") or "unknown").strip() or "unknown"
        by_status[status] += 1
        company_name = str(record.get("company_name") or "").strip()
        by_company[company_name][status] += 1
    return {
        "status_counts": dict(by_status),
        "per_company": {name: dict(counts) for name, counts in by_company.items()},
    }


def _manual_url_recommendations(records: list[dict[str, Any]]) -> list[str]:
    counts = _summarize_manual_url_records(records)["status_counts"]
    recommendations: list[str] = []
    if counts.get("missed_by_collection", 0):
        recommendations.append(
            "- Prioritize collection gaps first where the manual URL never appeared "
            "in scored candidates."
        )
    if counts.get("extracted_but_rejected_by_scoring", 0):
        recommendations.append(
            "- Review rejected-but-extracted rows next to confirm whether scoring "
            "should promote them."
        )
    if counts.get("outside_scope", 0):
        recommendations.append(
            "- Keep clearly outside-scope roles separate so recall tuning does not "
            "broaden generic software or sales roles."
        )
    if counts.get("saved_by_mvp", 0):
        recommendations.append(
            "- Preserve the current core-target scoring path for rows already saved "
            "cleanly by the MVP."
        )
    if not recommendations:
        recommendations.append(
            "- No immediate changes were suggested by the current manual URL slice."
        )
    return recommendations


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


def _is_interesting_rejected_job(job: dict[str, Any]) -> bool:
    explanation = explain_job_score(job)
    if explanation["is_relevant"]:
        return False
    title = _normalize_text(job.get("title"))
    interesting_terms = (
        "engineer",
        "support",
        "analyst",
        "admin",
        "administrator",
        "platform",
        "devops",
        "cloud",
        "linux",
        "infrastructure",
        "operations",
        "sre",
        "site reliability",
    )
    return any(term in title for term in interesting_terms)
