"""Policy evaluation helpers for source handling and manual interventions."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from classifier.source_classifier import DEFAULT_POLICIES_PATH, classify_source
from storage.db import create_intervention


class PolicyDecision(BaseModel):
    """Outcome of source policy evaluation."""

    source_mode: str
    reasons: list[str] = Field(default_factory=list)
    pause: bool = False
    intervention_id: int | None = None


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


@lru_cache(maxsize=1)
def load_policies_config(path: str = str(DEFAULT_POLICIES_PATH)) -> dict[str, Any]:
    """Load policy configuration from YAML."""

    return _read_yaml(Path(path))


def evaluate_source_policy(
    source: dict[str, Any],
    *,
    policies_path: Path = DEFAULT_POLICIES_PATH,
) -> PolicyDecision:
    """Evaluate a source and return its operating mode."""

    classification = classify_source(source, policies_path=policies_path)
    return PolicyDecision(
        source_mode=classification.source_mode,
        reasons=classification.reasons,
        pause=classification.source_mode in {"manual_only", "needs_url"},
    )


def handle_browsing_barrier(
    connection: sqlite3.Connection,
    *,
    company_name: str,
    job_id: int | None = None,
    detected_signals: list[str] | None = None,
    notes: str | None = None,
    policies_path: Path = DEFAULT_POLICIES_PATH,
) -> PolicyDecision:
    """Record a CAPTCHA/login barrier and return a paused policy decision."""

    policies = load_policies_config(str(policies_path))
    normalized_signals = [
        signal.strip().lower()
        for signal in detected_signals or []
        if signal.strip()
    ]
    barrier_signals = {signal.strip().lower() for signal in policies.get("barrier_signals", [])}
    matched_signals = [signal for signal in normalized_signals if signal in barrier_signals]

    if not matched_signals:
        return PolicyDecision(
            source_mode="browser_allowed",
            reasons=["no blocking CAPTCHA or login signal detected"],
            pause=False,
        )

    intervention_notes = notes or f"Browsing paused due to: {', '.join(matched_signals)}"
    intervention_id = create_intervention(
        connection,
        company_name=company_name,
        job_id=job_id,
        intervention_type="barrier_detected",
        notes=intervention_notes,
    )
    return PolicyDecision(
        source_mode="manual_only",
        reasons=[f"manual intervention required: {', '.join(matched_signals)}"],
        pause=True,
        intervention_id=intervention_id,
    )
