"""Source classification rules for company careers sources."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from .ats_detector import detect_ats_type, select_source_mode

DEFAULT_POLICIES_PATH = Path("config/policies.yaml")


class SourceClassificationResult(BaseModel):
    """Normalized source classification output."""

    model_config = ConfigDict(extra="ignore")

    company_name: str | None = None
    source_name: str | None = None
    careers_url: str | None = None
    ats_hint: str | None = None
    ats_type: str | None = None
    source_mode: str
    classification_reason: str | None = None
    reasons: list[str]

def classify_source(
    source: dict[str, Any],
    *,
    policies_path: Path = DEFAULT_POLICIES_PATH,
) -> SourceClassificationResult:
    """Classify a source into one of the configured policy modes."""

    careers_url = source.get("careers_url")
    ats_hint = source.get("ats_hint")
    website_category = source.get("website_category")
    current_source_mode = source.get("source_mode")
    ats_type = detect_ats_type(careers_url, ats_hint=ats_hint, website_category=website_category)
    source_mode = select_source_mode(
        careers_url,
        ats_type,
        current_source_mode=current_source_mode,
    )

    if source_mode == "needs_url":
        reasons = ["missing or invalid careers URL"]
    elif (
        source_mode == "manual_only"
        and str(current_source_mode or "").strip() in {"manual_only", "avoid"}
    ):
        reasons = [f"preserving explicit safety mode: {current_source_mode}"]
    elif source_mode == "manual_only":
        reasons = ["restricted job board detected; manual-only handling required"]
    elif source_mode == "api_allowed":
        reasons = [f"detected API-friendly ATS: {ats_type}"]
    elif source_mode == "human_in_loop":
        reasons = [f"detected complex ATS requiring visible/manual support: {ats_type}"]
    elif source_mode == "avoid":
        reasons = ["preserving explicit safety mode: avoid"]
    else:
        reasons = ["public careers URL with no known ATS restrictions"]

    return SourceClassificationResult(
        company_name=source.get("name") or source.get("company_name"),
        source_name=source.get("source_name") or source.get("website_category"),
        careers_url=careers_url,
        ats_hint=ats_hint,
        ats_type=ats_type,
        source_mode=source_mode,
        classification_reason=reasons[0],
        reasons=reasons,
    )
