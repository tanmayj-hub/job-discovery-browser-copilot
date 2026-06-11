"""Helpers for the local verified-company MVP workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_VERIFIED_COMPANIES_PATH = Path("config/verified_companies.yaml")


def load_verified_company_records(
    path: Path = DEFAULT_VERIFIED_COMPANIES_PATH,
) -> list[dict[str, Any]]:
    """Load verified-company records from YAML."""

    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    records = payload.get("verified_companies", [])
    return records if isinstance(records, list) else []


def is_usable_verified_company(record: dict[str, Any]) -> bool:
    """Return True when a record is verified and currently usable."""

    return bool(record.get("verified")) and str(record.get("status") or "").strip() == "usable"


def get_usable_verified_company_names(
    path: Path = DEFAULT_VERIFIED_COMPANIES_PATH,
) -> list[str]:
    """Return verified company names that are currently marked usable."""

    names: list[str] = []
    for record in load_verified_company_records(path):
        company_name = str(record.get("company_name") or "").strip()
        if not company_name or not is_usable_verified_company(record):
            continue
        names.append(company_name)
    return names
