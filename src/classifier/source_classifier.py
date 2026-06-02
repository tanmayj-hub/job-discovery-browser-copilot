"""Source classification rules for company careers sources."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict

DEFAULT_POLICIES_PATH = Path("config/policies.yaml")


class SourceClassificationResult(BaseModel):
    """Normalized source classification output."""

    model_config = ConfigDict(extra="ignore")

    company_name: str | None = None
    source_name: str | None = None
    careers_url: str | None = None
    ats_hint: str | None = None
    source_mode: str
    reasons: list[str]


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


@lru_cache(maxsize=1)
def load_policies_config(path: str = str(DEFAULT_POLICIES_PATH)) -> dict[str, Any]:
    """Load source policy configuration from YAML."""

    return _read_yaml(Path(path))


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_valid_public_url(value: object) -> bool:
    text = str(value).strip() if value is not None else ""
    if not text:
        return False
    parsed = urlparse(text)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _contains_any(text: str, terms: list[str]) -> str | None:
    for term in terms:
        normalized = term.strip().lower()
        if normalized and normalized in text:
            return term
    return None


def classify_source(
    source: dict[str, Any],
    *,
    policies_path: Path = DEFAULT_POLICIES_PATH,
) -> SourceClassificationResult:
    """Classify a source into one of the configured policy modes."""

    policies = load_policies_config(str(policies_path))
    careers_url = source.get("careers_url")
    source_name_text = _normalize_text(source.get("source_name") or source.get("website_category"))
    url_text = _normalize_text(careers_url)
    ats_hint_text = _normalize_text(source.get("ats_hint"))
    combined_text = " ".join(part for part in (source_name_text, url_text, ats_hint_text) if part)

    reasons: list[str] = []

    if not _is_valid_public_url(careers_url):
        reasons.append("missing or invalid careers URL")
        return SourceClassificationResult(
            company_name=source.get("name") or source.get("company_name"),
            source_name=source.get("source_name") or source.get("website_category"),
            careers_url=careers_url,
            ats_hint=source.get("ats_hint"),
            source_mode="needs_url",
            reasons=reasons,
        )

    restricted_match = _contains_any(combined_text, policies.get("restricted_portals", []))
    if restricted_match:
        reasons.append(f"restricted portal detected: {restricted_match}")
        return SourceClassificationResult(
            company_name=source.get("name") or source.get("company_name"),
            source_name=source.get("source_name") or source.get("website_category"),
            careers_url=careers_url,
            ats_hint=source.get("ats_hint"),
            source_mode="manual_only",
            reasons=reasons,
        )

    api_match = _contains_any(ats_hint_text, policies.get("api_allowed_ats", []))
    if api_match:
        reasons.append(f"ATS supports API-friendly collection: {api_match}")
        return SourceClassificationResult(
            company_name=source.get("name") or source.get("company_name"),
            source_name=source.get("source_name") or source.get("website_category"),
            careers_url=careers_url,
            ats_hint=source.get("ats_hint"),
            source_mode="api_allowed",
            reasons=reasons,
        )

    human_match = _contains_any(ats_hint_text, policies.get("human_in_loop_ats", []))
    if human_match:
        reasons.append(f"ATS requires human-in-the-loop workflow: {human_match}")
        return SourceClassificationResult(
            company_name=source.get("name") or source.get("company_name"),
            source_name=source.get("source_name") or source.get("website_category"),
            careers_url=careers_url,
            ats_hint=source.get("ats_hint"),
            source_mode="human_in_loop",
            reasons=reasons,
        )

    reasons.append("public careers URL with no known ATS restrictions")
    return SourceClassificationResult(
        company_name=source.get("name") or source.get("company_name"),
        source_name=source.get("source_name") or source.get("website_category"),
        careers_url=careers_url,
        ats_hint=source.get("ats_hint"),
        source_mode="browser_allowed",
        reasons=reasons,
    )
