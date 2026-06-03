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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""

    args = build_parser().parse_args(argv)
    storage_api = get_storage_api()
    collection_api = get_collection_api()
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
                "jobs_saved": len(result.jobs_saved),
                "report_path": str(result.artifacts.report_path),
                "csv_path": str(result.artifacts.csv_path),
            }
        )
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
