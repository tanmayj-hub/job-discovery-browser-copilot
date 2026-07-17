"""CLI entrypoint for local project workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

COMPANIES_CONFIG_PATH = PROJECT_ROOT / "config" / "companies.yaml"
VERIFIED_COMPANIES_CONFIG_PATH = PROJECT_ROOT / "config" / "verified_companies.yaml"
DATABASE_PATH = PROJECT_ROOT / "data" / "job_discovery.db"
REVIEW_EXPORT_PATH = PROJECT_ROOT / "data" / "exports" / "review" / "saved-jobs-review.csv"
VERIFIED_REVIEW_SNAPSHOT_PATH = (
    PROJECT_ROOT / "data" / "exports" / "review" / "latest-verified-saved-jobs.csv"
)


def get_collection_api():
    """Load collection helpers after the src path is available."""

    from collectors.browser_collector import (
        collect_browser_jobs,
        collect_single_company_with_browser,
        load_audit_max_pages_per_source,
        load_audit_scope_locations,
    )

    return {
        "collect_browser_jobs": collect_browser_jobs,
        "collect_single_company_with_browser": collect_single_company_with_browser,
        "load_audit_max_pages_per_source": load_audit_max_pages_per_source,
        "load_audit_scope_locations": load_audit_scope_locations,
    }


def get_reports_api():
    """Load daily-run reporting workflow after the src path is available."""

    from reports.daily_run import run_daily_workflow

    return {
        "run_daily_workflow": run_daily_workflow,
    }


def get_audit_api():
    """Load accuracy audit helpers after the src path is available."""

    from audit.accuracy_audit import (
        build_company_audit_pack,
        build_manual_audit_link_sheet,
        compare_audit_files,
        compare_manual_expected_urls,
        create_manual_template,
        export_audit_sample,
        find_job_for_score_explanation,
        load_manual_expected_jobs,
        merge_company_audit_chunks,
        parse_company_filter,
        validate_audit_files,
        write_company_audit_chunk_metadata,
        write_company_collection_diagnostic,
        write_manual_url_recall_report,
        write_score_explanation_report,
    )

    return {
        "build_company_audit_pack": build_company_audit_pack,
        "build_manual_audit_link_sheet": build_manual_audit_link_sheet,
        "compare_manual_expected_urls": compare_manual_expected_urls,
        "compare_audit_files": compare_audit_files,
        "create_manual_template": create_manual_template,
        "export_audit_sample": export_audit_sample,
        "find_job_for_score_explanation": find_job_for_score_explanation,
        "load_manual_expected_jobs": load_manual_expected_jobs,
        "merge_company_audit_chunks": merge_company_audit_chunks,
        "parse_company_filter": parse_company_filter,
        "validate_audit_files": validate_audit_files,
        "write_manual_url_recall_report": write_manual_url_recall_report,
        "write_score_explanation_report": write_score_explanation_report,
        "write_company_collection_diagnostic": write_company_collection_diagnostic,
        "write_company_audit_chunk_metadata": write_company_audit_chunk_metadata,
    }


def get_onboarding_api():
    """Load onboarding helpers after the src path is available."""

    from onboarding.source_onboarding import (
        apply_approved_candidates,
        audit_large_company_list,
        generate_candidates_from_input,
        refresh_sources,
        weekly_source_check,
    )

    return {
        "audit_large_company_list": audit_large_company_list,
        "apply_approved_candidates": apply_approved_candidates,
        "generate_candidates_from_input": generate_candidates_from_input,
        "refresh_sources": refresh_sources,
        "weekly_source_check": weekly_source_check,
    }


def get_storage_api():
    """Load storage helpers after the src path is available."""

    from storage.db import get_dashboard_overview, initialize_database, upsert_companies

    return {
        "get_dashboard_overview": get_dashboard_overview,
        "initialize_database": initialize_database,
        "upsert_companies": upsert_companies,
    }


def get_verified_companies_api():
    """Load verified-company helpers after the src path is available."""

    from verified_companies import (
        get_usable_verified_company_names,
        load_verified_company_records,
    )

    return {
        "get_usable_verified_company_names": get_usable_verified_company_names,
        "load_verified_company_records": load_verified_company_records,
    }


def get_review_api():
    """Load saved-job review helpers after the src path is available."""

    from review.saved_job_review import (
        collect_review_export_companies,
        export_saved_jobs_review,
    )

    return {
        "collect_review_export_companies": collect_review_export_companies,
        "export_saved_jobs_review": export_saved_jobs_review,
    }


def load_companies_config() -> list[dict[str, object]]:
    """Load companies from YAML config."""

    payload = yaml.safe_load(COMPANIES_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    companies = payload.get("companies", [])
    return companies if isinstance(companies, list) else []


def parse_company_filter(raw: str | None) -> list[str]:
    """Parse a comma-separated company filter into a clean list."""

    if not raw:
        return []
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def seed_companies_if_needed(connection) -> None:
    """Populate companies into SQLite the first time the CLI runs."""

    storage_api = get_storage_api()
    overview = storage_api["get_dashboard_overview"](connection)
    if overview["total_companies"] == 0:
        storage_api["upsert_companies"](connection, load_companies_config())


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description="Job Discovery Browser Co-Pilot CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Run job collection")
    collect_parser.add_argument(
        "--mode",
        choices=["browser"],
        required=True,
        help="Collection mode to run.",
    )
    collect_parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum number of companies to process.",
    )

    daily_run_parser = subparsers.add_parser("daily-run", help="Run the full daily workflow")
    daily_run_scope = daily_run_parser.add_mutually_exclusive_group()
    daily_run_scope.add_argument(
        "--company",
        type=str,
        default=None,
        help="Optional comma-separated company filter for exact-name daily-run slices.",
    )
    daily_run_scope.add_argument(
        "--verified-only",
        action="store_true",
        help="Run only companies marked verified and usable in config/verified_companies.yaml.",
    )
    daily_run_scope.add_argument(
        "--list-verified",
        action="store_true",
        help="List verified-company statuses without running collection.",
    )

    onboarding_parser = subparsers.add_parser(
        "onboard",
        help="Generate or apply review-first source onboarding candidates",
    )
    onboarding_subparsers = onboarding_parser.add_subparsers(
        dest="onboarding_command",
        required=True,
    )

    onboarding_generate = onboarding_subparsers.add_parser(
        "generate",
        help="Generate reviewable onboarding candidates",
    )
    onboarding_generate.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to a TXT, CSV, or XLSX file with company names.",
    )
    onboarding_generate.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "source-onboarding-candidates.yaml",
        help="Output YAML or CSV path for generated candidates.",
    )
    onboarding_generate.add_argument(
        "--live-discovery",
        action="store_true",
        help="Enable opt-in live careers page discovery from provided or known URLs.",
    )
    onboarding_generate.add_argument(
        "--max-pages-per-company",
        type=int,
        default=8,
        help="Maximum number of HTML pages to fetch per company during live discovery.",
    )

    onboarding_refresh = onboarding_subparsers.add_parser(
        "refresh-sources",
        help="Generate reviewable replacement candidates for existing sources",
    )
    onboarding_refresh.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "source-refresh-candidates.yaml",
        help="Output YAML or CSV path for source refresh candidates.",
    )
    onboarding_refresh.add_argument(
        "--only-problem-sources",
        action="store_true",
        help="Only check sources that appear stale or problematic.",
    )
    onboarding_refresh.add_argument(
        "--company",
        type=str,
        default=None,
        help="Optional company name filter.",
    )
    onboarding_refresh.add_argument(
        "--force",
        action="store_true",
        help="Ignore min-days-between-checks and refresh now.",
    )
    onboarding_refresh.add_argument(
        "--max-pages-per-company",
        type=int,
        default=8,
        help="Maximum number of HTML pages to fetch per company during refresh.",
    )
    onboarding_refresh.add_argument(
        "--min-days-between-checks",
        type=int,
        default=7,
        help="Minimum days between refresh checks unless --force is used.",
    )

    onboarding_weekly = onboarding_subparsers.add_parser(
        "weekly-source-check",
        help="Run the lightweight weekly source health check workflow",
    )
    onboarding_weekly.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "weekly-source-refresh-candidates.yaml",
        help="Output YAML or CSV path for weekly refresh candidates.",
    )
    onboarding_weekly.add_argument(
        "--only-problem-sources",
        action="store_true",
        help="Restrict the weekly check to problem sources only.",
    )
    onboarding_weekly.add_argument(
        "--force",
        action="store_true",
        help="Ignore min-days-between-checks and refresh now.",
    )
    onboarding_weekly.add_argument(
        "--max-pages-per-company",
        type=int,
        default=8,
        help="Maximum number of HTML pages to fetch per company during refresh.",
    )
    onboarding_weekly.add_argument(
        "--min-days-between-checks",
        type=int,
        default=7,
        help="Minimum days between refresh checks unless --force is used.",
    )

    onboarding_apply = onboarding_subparsers.add_parser(
        "apply",
        help="Apply only approved onboarding candidates",
    )
    onboarding_apply.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to onboarding candidates YAML or CSV.",
    )
    onboarding_apply.add_argument(
        "--update-existing",
        action="store_true",
        help="Allow approved candidates to update existing companies.",
    )

    onboarding_audit = onboarding_subparsers.add_parser(
        "audit-large-list",
        help="Audit the 150-company spreadsheet for readiness without changing config",
    )
    onboarding_audit.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "input" / "Rishi canada companies list (1).xlsx",
        help="Spreadsheet path to audit.",
    )
    onboarding_audit.add_argument(
        "--readiness-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "company-input-readiness.csv",
        help="CSV output for readiness rows.",
    )
    onboarding_audit.add_argument(
        "--candidates-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "large-list-source-candidates.yaml",
        help="YAML output for reviewable source candidates.",
    )
    onboarding_audit.add_argument(
        "--report-output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "large-company-list-readiness-report.md",
        help="Markdown output for the readiness report.",
    )
    onboarding_audit.add_argument(
        "--needs-website-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "large-list-needs-website-input.csv",
        help="Optional CSV output for companies that still need a website URL.",
    )

    audit_parser = subparsers.add_parser(
        "audit",
        help="Export and compare manual accuracy-audit artifacts",
    )
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command", required=True)

    audit_export = audit_subparsers.add_parser(
        "export-sample",
        help="Export a reviewable MVP audit sample CSV",
    )
    audit_export.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "accuracy-audit-sample.csv",
        help="CSV output path for the MVP audit sample.",
    )
    audit_export.add_argument(
        "--companies",
        type=str,
        default=None,
        help="Optional comma-separated company filter.",
    )
    audit_export.add_argument(
        "--limit-per-company",
        type=int,
        default=10,
        help="Maximum number of rows to export per company.",
    )
    audit_export.add_argument(
        "--include-recent-days",
        type=int,
        default=14,
        help="Only include rows seen within this many days when possible.",
    )
    audit_export.add_argument(
        "--status",
        type=str,
        default="new",
        help="Optional job status filter.",
    )

    audit_template = audit_subparsers.add_parser(
        "create-manual-template",
        help="Create a blank manual-job template CSV for recall auditing",
    )
    audit_template.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "manual-job-audit-template.csv",
        help="CSV output path for the manual template.",
    )
    audit_template.add_argument(
        "--companies",
        type=str,
        default=None,
        help="Optional comma-separated company list to prefill blank rows.",
    )

    audit_compare = audit_subparsers.add_parser(
        "compare",
        help="Compare MVP audit sample rows against manually collected jobs",
    )
    audit_compare.add_argument(
        "--mvp",
        type=Path,
        required=True,
        help="Path to the filled MVP audit sample CSV.",
    )
    audit_compare.add_argument(
        "--manual",
        type=Path,
        required=True,
        help="Path to the manual-job audit CSV.",
    )
    audit_compare.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "accuracy-audit-report.md",
        help="Markdown output path for the audit report.",
    )
    audit_compare.add_argument(
        "--audited-by",
        type=str,
        default="manual_audit",
        help="Name to record in the generated audit rows.",
    )

    audit_validate = audit_subparsers.add_parser(
        "validate-files",
        help="Validate manual audit CSV files before compare",
    )
    audit_validate.add_argument(
        "--mvp",
        type=Path,
        required=True,
        help="Path to the MVP audit sample CSV.",
    )
    audit_validate.add_argument(
        "--manual",
        type=Path,
        required=True,
        help="Path to the manual-job audit CSV.",
    )

    audit_company_pack = audit_subparsers.add_parser(
        "company-pack",
        help="Create a simple one-company manual audit pack",
    )
    audit_company_pack.add_argument(
        "--company",
        type=str,
        required=True,
        help="Company name to audit.",
    )
    audit_company_pack.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Markdown output path for the company audit pack.",
    )
    audit_company_pack.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of MVP rows to include.",
    )
    audit_company_pack.add_argument(
        "--include-recent-days",
        type=int,
        default=14,
        help="Only include rows seen within this many days when possible.",
    )
    audit_company_pack.add_argument(
        "--status",
        type=str,
        default="new",
        help="Optional job status filter.",
    )

    audit_diagnose = audit_subparsers.add_parser(
        "diagnose-company-collection",
        help="Run a focused one-company browser collection diagnostic",
    )
    audit_diagnose.add_argument(
        "--company",
        type=str,
        required=True,
        help="Company name to diagnose.",
    )
    audit_diagnose.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Markdown output path for the collection diagnostic.",
    )
    audit_diagnose.add_argument(
        "--export-scored-candidates",
        type=Path,
        default=None,
        help="Optional CSV output path for scored candidates, including rejected rows.",
    )
    audit_diagnose.add_argument(
        "--use-audit-scope",
        action="store_true",
        help="Use the Canada-only audit scope from config/discovery.yaml.",
    )
    audit_diagnose.add_argument(
        "--page-cap",
        type=int,
        default=None,
        help="Audit-only pagination cap override; does not change production configuration.",
    )
    audit_diagnose.add_argument(
        "--page-start",
        type=int,
        default=1,
        help="Audit-only first RBC page to scan (1-based).",
    )
    audit_diagnose.add_argument(
        "--page-end",
        type=int,
        default=None,
        help="Audit-only final RBC page to scan (inclusive).",
    )

    audit_merge_chunks = audit_subparsers.add_parser(
        "merge-company-chunks",
        help="Validate and merge deterministic company audit chunk CSVs",
    )
    audit_merge_chunks.add_argument("--company", type=str, required=True)
    audit_merge_chunks.add_argument("--inputs", type=Path, nargs="+", required=True)
    audit_merge_chunks.add_argument("--output", type=Path, required=True)
    audit_merge_chunks.add_argument("--report", type=Path, required=True)

    audit_manual_urls = audit_subparsers.add_parser(
        "compare-manual-urls",
        help="Compare manually expected job URLs against saved and scored MVP results",
    )
    audit_manual_urls.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the manual expected jobs YAML fixture.",
    )
    audit_manual_urls.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "audits" / "manual-url-recall-audit.md",
        help="Markdown output path for the manual URL recall audit report.",
    )
    audit_manual_urls.add_argument(
        "--scored-candidates-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "audits",
        help="Directory containing per-company scored candidate exports.",
    )

    audit_explain = audit_subparsers.add_parser(
        "explain-score",
        help="Explain why a saved or rejected job did or did not qualify as relevant",
    )
    audit_explain.add_argument(
        "--company",
        type=str,
        required=True,
        help="Company name for the job to explain.",
    )
    audit_explain.add_argument(
        "--title",
        type=str,
        default=None,
        help="Optional exact job title match.",
    )
    audit_explain.add_argument(
        "--url",
        type=str,
        default=None,
        help="Optional exact job URL match.",
    )
    audit_explain.add_argument(
        "--include-rejected",
        action="store_true",
        help="Also search the scored-candidates export for rejected jobs.",
    )
    audit_explain.add_argument(
        "--scored-candidates",
        type=Path,
        default=None,
        help="Optional scored-candidates CSV path to search for rejected jobs.",
    )
    audit_explain.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Markdown output path for the score explanation.",
    )

    review_parser = subparsers.add_parser(
        "review",
        help="Export lightweight saved-job review artifacts",
    )
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)

    review_export = review_subparsers.add_parser(
        "export-saved-jobs",
        help="Export the latest verified saved jobs for manual review",
    )
    review_export.add_argument(
        "--output",
        type=Path,
        default=REVIEW_EXPORT_PATH,
        help="CSV output path for the saved-job review file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""

    args = build_parser().parse_args(argv)
    if args.command == "daily-run" and args.list_verified:
        verified_api = get_verified_companies_api()
        records = verified_api["load_verified_company_records"](VERIFIED_COMPANIES_CONFIG_PATH)
        if not records:
            print({"verified_companies": [], "usable_companies": []})
            return 0
        for record in records:
            print(
                {
                    "company_name": str(record.get("company_name") or "").strip(),
                    "verified": bool(record.get("verified")),
                    "status": str(record.get("status") or "").strip(),
                    "scope": str(record.get("scope") or "").strip(),
                    "verified_at": str(record.get("verified_at") or "").strip(),
                    "notes": str(record.get("notes") or "").strip(),
                }
            )
        return 0

    storage_api = get_storage_api()
    collection_api = get_collection_api()
    onboarding_api = get_onboarding_api()
    reports_api = get_reports_api()
    audit_api = get_audit_api()
    review_api = get_review_api()
    connection = storage_api["initialize_database"](DATABASE_PATH)
    seed_companies_if_needed(connection)

    if args.command == "collect" and args.mode == "browser":
        results = collection_api["collect_browser_jobs"](
            connection,
            limit=args.limit,
            headless=False,
        )
        for result in results:
            print(json.dumps(result, ensure_ascii=True))
        return 0

    if args.command == "daily-run":
        verified_api = get_verified_companies_api()
        companies: list[str] = []
        run_scope = "all"
        if args.verified_only:
            companies = verified_api["get_usable_verified_company_names"](
                VERIFIED_COMPANIES_CONFIG_PATH
            )
            run_scope = "verified_only"
            if not companies:
                print(
                    {
                        "run_scope": run_scope,
                        "verified_companies": [],
                        "status": "no_usable_verified_companies",
                    }
                )
                return 0
        elif args.company:
            companies = parse_company_filter(args.company)
            run_scope = "company_filter"
        result = reports_api["run_daily_workflow"](
            config_path=COMPANIES_CONFIG_PATH,
            db_path=DATABASE_PATH,
            exports_dir=PROJECT_ROOT / "data" / "exports",
            company_names=companies or None,
            run_scope=run_scope,
        )
        print(
            {
                "run_date": result.run_date,
                "run_scope": result.run_scope,
                "companies_checked": len(result.companies_checked),
                "companies_skipped": len(result.companies_skipped),
                "company_filter": companies or "all",
                "jobs_discovered": result.jobs_discovered,
                "jobs_scored": result.jobs_scored,
                "jobs_relevant": result.jobs_relevant,
                "jobs_saved": len(result.jobs_saved),
                "location_scope_used": result.location_scope_used,
                "keyword_scope_used": result.keyword_scope_used,
                "report_path": str(result.artifacts.report_path),
                "csv_path": str(result.artifacts.csv_path),
            }
        )
        return 0

    if args.command == "onboard" and args.onboarding_command == "generate":
        candidates = onboarding_api["generate_candidates_from_input"](
            input_path=args.input,
            output_path=args.output,
            companies_path=COMPANIES_CONFIG_PATH,
            starter_path=PROJECT_ROOT / "config" / "starter_career_urls.yaml",
            live_discovery=args.live_discovery,
            max_pages_per_company=args.max_pages_per_company,
        )
        print(
            {
                "generated": len(candidates),
                "output_path": str(args.output),
                "high_confidence": sum(
                    1 for item in candidates if item.confidence == "high"
                ),
                "needs_review": sum(1 for item in candidates if item.needs_review),
            }
        )
        return 0

    if args.command == "onboard" and args.onboarding_command == "refresh-sources":
        candidates = onboarding_api["refresh_sources"](
            output_path=args.output,
            companies_path=COMPANIES_CONFIG_PATH,
            db_path=DATABASE_PATH,
            state_path=PROJECT_ROOT / "data" / "exports" / "source-health-state.json",
            only_problem_sources=args.only_problem_sources,
            company_name=args.company,
            force=args.force,
            max_pages_per_company=args.max_pages_per_company,
            min_days_between_checks=args.min_days_between_checks,
        )
        print(
            {
                "generated": len(candidates),
                "output_path": str(args.output),
                "needs_review": sum(1 for item in candidates if item.needs_review),
            }
        )
        return 0

    if args.command == "onboard" and args.onboarding_command == "weekly-source-check":
        candidates = onboarding_api["weekly_source_check"](
            output_path=args.output,
            companies_path=COMPANIES_CONFIG_PATH,
            db_path=DATABASE_PATH,
            state_path=PROJECT_ROOT / "data" / "exports" / "source-health-state.json",
            only_problem_sources=args.only_problem_sources or True,
            force=args.force,
            max_pages_per_company=args.max_pages_per_company,
            min_days_between_checks=args.min_days_between_checks,
        )
        print(
            {
                "generated": len(candidates),
                "output_path": str(args.output),
                "needs_review": sum(1 for item in candidates if item.needs_review),
            }
        )
        return 0

    if args.command == "onboard" and args.onboarding_command == "apply":
        summary = onboarding_api["apply_approved_candidates"](
            input_path=args.input,
            companies_path=COMPANIES_CONFIG_PATH,
            update_existing=args.update_existing,
        )
        print(summary)
        return 0

    if args.command == "onboard" and args.onboarding_command == "audit-large-list":
        result = onboarding_api["audit_large_company_list"](
            input_path=args.input,
            companies_path=COMPANIES_CONFIG_PATH,
            starter_path=PROJECT_ROOT / "config" / "starter_career_urls.yaml",
            readiness_output_path=args.readiness_output,
            candidates_output_path=args.candidates_output,
            report_output_path=args.report_output,
            needs_website_output_path=args.needs_website_output,
        )
        print(
            {
                "total_companies": result["summary"]["total_companies"],
                "already_configured_count": result["summary"]["already_configured_count"],
                "usable_url_count": result["summary"]["usable_url_count"],
                "missing_url_count": result["summary"]["missing_url_count"],
                "spreadsheet_hyperlink_count": result["summary"]["spreadsheet_hyperlink_count"],
                "starter_url_match_count": result["summary"]["starter_url_match_count"],
                "candidate_count": result["summary"]["candidate_count"],
                "readiness_output_path": str(args.readiness_output),
                "candidates_output_path": str(args.candidates_output),
                "report_output_path": str(args.report_output),
            }
        )
        return 0

    if args.command == "audit" and args.audit_command == "export-sample":
        companies = audit_api["parse_company_filter"](args.companies)
        rows = audit_api["export_audit_sample"](
            connection,
            output_path=args.output,
            companies=companies,
            limit_per_company=args.limit_per_company,
            include_recent_days=args.include_recent_days,
            status=args.status,
        )
        print(
            {
                "exported_rows": len(rows),
                "companies": companies or "all",
                "output_path": str(args.output),
            }
        )
        return 0

    if args.command == "audit" and args.audit_command == "create-manual-template":
        companies = audit_api["parse_company_filter"](args.companies)
        rows = audit_api["create_manual_template"](
            output_path=args.output,
            companies=companies,
        )
        audit_api["build_manual_audit_link_sheet"](
            connection,
            output_path=PROJECT_ROOT / "data" / "exports" / "manual-audit-link-sheet.csv",
            companies_path=COMPANIES_CONFIG_PATH,
            audit_sample_path=PROJECT_ROOT / "data" / "exports" / "accuracy-audit-sample.csv",
            manual_template_path=args.output,
            companies=companies,
        )
        print(
            {
                "template_rows": len(rows),
                "companies": companies or [],
                "output_path": str(args.output),
            }
        )
        return 0

    if args.command == "audit" and args.audit_command == "compare":
        result = audit_api["compare_audit_files"](
            mvp_path=args.mvp,
            manual_path=args.manual,
            output_path=args.output,
            audited_by=args.audited_by,
        )
        print(
            {
                "companies_audited": result.companies_audited,
                "overall_metrics": result.overall_metrics.to_dict(),
                "report_path": str(result.report_path),
            }
        )
        return 0

    if args.command == "audit" and args.audit_command == "validate-files":
        result = audit_api["validate_audit_files"](
            mvp_path=args.mvp,
            manual_path=args.manual,
        )
        print(result.to_dict())
        return 0 if result.is_valid else 1

    if args.command == "audit" and args.audit_command == "company-pack":
        slug = _slugify_company_name(args.company)
        markdown_output = args.output or (
            PROJECT_ROOT / "docs" / "audits" / f"{slug}-audit-pack.md"
        )
        audits_export_dir = PROJECT_ROOT / "data" / "exports" / "audits"
        result = audit_api["build_company_audit_pack"](
            connection,
            company_name=args.company,
            companies_path=COMPANIES_CONFIG_PATH,
            markdown_output_path=markdown_output,
            mvp_output_path=audits_export_dir / f"{slug}-mvp-sample.csv",
            manual_output_path=audits_export_dir / f"{slug}-manual-template.csv",
            limit_per_company=args.limit,
            include_recent_days=args.include_recent_days,
            status=args.status,
        )
        print(result.to_dict())
        return 0

    if args.command == "audit" and args.audit_command == "diagnose-company-collection":
        if args.page_start < 1 or (
            args.page_end is not None and args.page_end < args.page_start
        ):
            raise ValueError("--page-start must be positive and no greater than --page-end")
        company = _find_company_config(args.company)
        slug = _slugify_company_name(args.company)
        output_path = args.output or (
            PROJECT_ROOT / "docs" / "audits" / f"{slug}-collection-diagnostic.md"
        )
        scored_candidates_output_path = args.export_scored_candidates or (
            PROJECT_ROOT / "data" / "exports" / "audits" / f"{slug}-scored-candidates.csv"
        )
        location_scope_override = None
        max_pages_per_source_override = args.page_cap
        force_location_scope_search = False
        if args.use_audit_scope:
            location_scope_override = collection_api["load_audit_scope_locations"]()
            force_location_scope_search = True
        manual_expected_jobs: list[dict[str, object]] = []
        manual_expected_fixture_path = (
            PROJECT_ROOT / "data" / "exports" / "audits" / "manual-expected-jobs-next-slice.yaml"
        )
        if not manual_expected_fixture_path.exists():
            manual_expected_fixture_path = (
                PROJECT_ROOT
                / "tests"
                / "fixtures"
                / "audit"
                / "manual_expected_jobs_td_ibm_sunlife.yaml"
            )
        if manual_expected_fixture_path.exists():
            for fixture_company in audit_api["load_manual_expected_jobs"](
                manual_expected_fixture_path
            ):
                if _slugify_company_name(
                    str(fixture_company.get("company_name") or "")
                ) == slug:
                    manual_expected_jobs = list(
                        fixture_company.get("expected_jobs", []) or []
                    )
                    break
        result = collection_api["collect_single_company_with_browser"](
            connection,
            company=company,
            headless=False,
            save_jobs=False,
            allowed_source_modes={"browser_allowed", "human_in_loop"},
            location_scope_override=location_scope_override,
            max_pages_per_source_override=max_pages_per_source_override,
            use_audit_page_policy=args.use_audit_scope,
            force_location_scope_search=force_location_scope_search,
            capture_page_html=str(company.get("name") or "") != "RBC",
            allow_broad_diagnostic_collection=True,
            audit_page_start=args.page_start,
            audit_page_end=args.page_end,
        )
        from storage.db import get_jobs

        diagnostic = audit_api["write_company_collection_diagnostic"](
            output_path=output_path,
            company=company,
            collection_result=result,
            scored_candidates_output_path=scored_candidates_output_path,
            manual_expected_jobs=manual_expected_jobs,
            saved_jobs=[
                job
                for job in get_jobs(connection)
                if str(job.get("company_name") or "").strip()
                == str(company.get("name") or "").strip()
            ],
        )
        chunk_metadata_path = audit_api["write_company_audit_chunk_metadata"](
            csv_path=scored_candidates_output_path,
            company=company,
            collection_result=result,
        )
        print(
            {
                **diagnostic.to_dict(),
                "jobs_discovered": result.get("jobs_discovered", 0),
                "jobs_relevant": result.get("jobs_relevant", 0),
                "scored_candidates_output_path": str(scored_candidates_output_path),
                "pages_visited": result.get("pages_visited", []),
                "pagination_stop_reason": result.get("pagination_stop_reason"),
                "chunk_metadata_path": str(chunk_metadata_path),
            }
        )
        return 0

    if args.command == "audit" and args.audit_command == "merge-company-chunks":
        result = audit_api["merge_company_audit_chunks"](
            company_name=args.company,
            inputs=args.inputs,
            output_path=args.output,
            report_path=args.report,
        )
        print(result)
        return 0

    if args.command == "audit" and args.audit_command == "compare-manual-urls":
        fixture = audit_api["load_manual_expected_jobs"](args.input)
        result = audit_api["compare_manual_expected_urls"](
            connection,
            companies=fixture,
            scored_candidates_dir=args.scored_candidates_dir,
        )
        audit_api["write_manual_url_recall_report"](
            args.output,
            companies=fixture,
            audit_records=result["records"],
            summary=result["summary"],
        )
        print(
            {
                "companies": [item["company_name"] for item in fixture],
                "record_count": len(result["records"]),
                "summary": result["summary"],
                "report_path": str(args.output),
            }
        )
        return 0

    if args.command == "audit" and args.audit_command == "explain-score":
        if not args.title and not args.url:
            raise ValueError("Provide --title or --url for audit explain-score.")
        slug = _slugify_company_name(args.company)
        scored_candidates_path = args.scored_candidates or (
            PROJECT_ROOT / "data" / "exports" / "audits" / f"{slug}-scored-candidates.csv"
        )
        output_path = args.output or (
            PROJECT_ROOT / "docs" / "audits" / f"{slug}-score-explanation.md"
        )
        job, source = audit_api["find_job_for_score_explanation"](
            connection,
            company_name=args.company,
            title=args.title,
            url=args.url,
            scored_candidates_path=scored_candidates_path,
            include_rejected=args.include_rejected,
        )
        explanation = audit_api["write_score_explanation_report"](
            output_path=output_path,
            job=job,
            source=source,
        )
        print(explanation.to_dict())
        return 0

    if args.command == "review" and args.review_command == "export-saved-jobs":
        rows = review_api["export_saved_jobs_review"](
            connection,
            verified_companies_path=VERIFIED_COMPANIES_CONFIG_PATH,
            output_path=args.output,
            saved_jobs_snapshot_path=VERIFIED_REVIEW_SNAPSHOT_PATH,
        )
        print(
            {
                "exported_rows": len(rows),
                "companies_included": review_api["collect_review_export_companies"](rows),
                "output_path": str(args.output),
            }
        )
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


def _slugify_company_name(company_name: str) -> str:
    return "-".join(
        segment for segment in "".join(
            char if char.isalnum() else "-" for char in str(company_name or "").strip()
        ).split("-") if segment
    ) or "company"


def _find_company_config(company_name: str) -> dict[str, object]:
    target = _slugify_company_name(company_name)
    for company in load_companies_config():
        if _slugify_company_name(str(company.get("name") or "")) == target:
            return company
    raise ValueError(f"Company not found in config/companies.yaml: {company_name}")


if __name__ == "__main__":
    raise SystemExit(main())
