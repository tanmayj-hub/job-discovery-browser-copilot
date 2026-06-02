"""Helpers for starter career URL suggestions used in the dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_STARTER_PATH = Path(__file__).resolve().parents[2] / "config" / "starter_career_urls.yaml"


def load_starter_career_url_entries(path: Path = DEFAULT_STARTER_PATH) -> list[dict[str, Any]]:
    """Load starter career URL entries from YAML."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    companies = payload.get("companies", [])
    return companies if isinstance(companies, list) else []


def build_starter_career_url_map(path: Path = DEFAULT_STARTER_PATH) -> dict[str, dict[str, Any]]:
    """Build a company-name keyed map of starter career URL entries."""

    entries = load_starter_career_url_entries(path)
    return {
        str(entry.get("name") or "").strip(): entry
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("name") or "").strip()
    }
