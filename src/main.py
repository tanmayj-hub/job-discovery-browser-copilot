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
DATABASE_PATH = PROJECT_ROOT / "data" / "job_discovery.db"


def get_collection_api():
    """Load collection helpers after the src path is available."""

    from collectors.browser_collector import collect_browser_jobs

    return {
        "collect_browser_jobs": collect_browser_jobs,
    }


def get_reports_api():
    """Load daily-run reporting workflow after the src path is available."""

    from reports.daily_run import run_daily_workflow

    return {
        "run_daily_workflow": run_daily_workflow,
    }


def get_onboarding_api():
    """Load onboarding helpers after the src path is available."""

    from onboarding.source_onboarding import (
        apply_approved_candidates,
        generate_candidates_from_input,
        refresh_sources,
        weekly_source_check,
    )

    return {
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


def load_companies_config() -> list[dict[str, object]]:
    """Load companies from YAML config."""

    payload = yaml.safe_load(COMPANIES_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    companies = payload.get("companies", [])
    return companies if isinstance(companies, list) else []


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

    subparsers.add_parser("daily-run", help="Run the full daily workflow")

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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""

    args = build_parser().parse_args(argv)
    storage_api = get_storage_api()
    collection_api = get_collection_api()
    onboarding_api = get_onboarding_api()
    reports_api = get_reports_api()
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
        result = reports_api["run_daily_workflow"](
            config_path=COMPANIES_CONFIG_PATH,
            db_path=DATABASE_PATH,
            exports_dir=PROJECT_ROOT / "data" / "exports",
        )
        print(
            {
                "run_date": result.run_date,
                "companies_checked": len(result.companies_checked),
                "companies_skipped": len(result.companies_skipped),
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

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
