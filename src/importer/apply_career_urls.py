"""Apply starter career URLs to config/companies.yaml."""

from __future__ import annotations

import argparse
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from classifier.source_classifier import classify_source
    from importer.excel_importer import is_real_url, update_company_record_in_yaml
except ModuleNotFoundError:  # pragma: no cover
    classify_source = import_module("src.classifier.source_classifier").classify_source
    importer_module = import_module("src.importer.excel_importer")
    is_real_url = importer_module.is_real_url
    update_company_record_in_yaml = importer_module.update_company_record_in_yaml

DEFAULT_STARTER_PATH = PROJECT_ROOT / "config" / "starter_career_urls.yaml"
DEFAULT_COMPANIES_PATH = PROJECT_ROOT / "config" / "companies.yaml"


def load_yaml_companies(path: Path) -> list[dict[str, Any]]:
    """Load companies from a YAML file with a top-level companies list."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    companies = payload.get("companies", [])
    return companies if isinstance(companies, list) else []


def summarize_companies(companies: list[dict[str, Any]], updated: int) -> dict[str, int]:
    """Build a summary for console output."""

    still_missing = sum(
        1
        for company in companies
        if not is_real_url(company.get("careers_url"))
        or str(company.get("source_mode") or "").strip() == "needs_url"
    )
    return {
        "updated": updated,
        "still_missing": still_missing,
        "api_allowed": sum(
            1 for company in companies if company.get("source_mode") == "api_allowed"
        ),
        "browser_allowed": sum(
            1 for company in companies if company.get("source_mode") == "browser_allowed"
        ),
        "human_in_loop": sum(
            1 for company in companies if company.get("source_mode") == "human_in_loop"
        ),
    }


def apply_career_url_updates(
    *,
    starter_path: Path = DEFAULT_STARTER_PATH,
    companies_path: Path = DEFAULT_COMPANIES_PATH,
) -> dict[str, int]:
    """Apply starter career URL entries to the main companies config."""

    starter_companies = load_yaml_companies(starter_path)
    existing_companies = {
        str(company.get("name") or "").strip(): company
        for company in load_yaml_companies(companies_path)
        if isinstance(company, dict)
    }

    updated = 0
    for starter in starter_companies:
        if not isinstance(starter, dict):
            continue
        company_name = str(starter.get("name") or "").strip()
        careers_url = str(starter.get("careers_url") or "").strip()
        if not company_name or not is_real_url(careers_url):
            continue
        company = existing_companies.get(company_name)
        if company is None:
            continue

        classification = classify_source(
            {
                "name": company_name,
                "source_name": company.get("website_category") or company_name,
                "website_category": company.get("website_category"),
                "careers_url": careers_url,
                "ats_hint": company.get("ats_hint"),
            }
        )
        update_company_record_in_yaml(
            companies_path,
            company_name=company_name,
            updates={
                "careers_url": careers_url,
                "source_mode": classification.source_mode,
            },
        )
        existing_companies[company_name] = {
            **company,
            "careers_url": careers_url,
            "source_mode": classification.source_mode,
        }
        updated += 1

    summary = summarize_companies(list(existing_companies.values()), updated)
    return summary


def print_summary(summary: dict[str, int]) -> None:
    """Print the summary in the requested format."""

    print(f"updated: {summary['updated']}")
    print(f"still missing: {summary['still_missing']}")
    print(f"api_allowed: {summary['api_allowed']}")
    print(f"browser_allowed: {summary['browser_allowed']}")
    print(f"human_in_loop: {summary['human_in_loop']}")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        description="Apply starter career URLs to config/companies.yaml.",
    )
    parser.add_argument(
        "--starter",
        type=Path,
        default=DEFAULT_STARTER_PATH,
        help="Path to config/starter_career_urls.yaml.",
    )
    parser.add_argument(
        "--companies",
        type=Path,
        default=DEFAULT_COMPANIES_PATH,
        help="Path to config/companies.yaml.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = build_parser().parse_args(argv)
    summary = apply_career_url_updates(
        starter_path=args.starter,
        companies_path=args.companies,
    )
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
