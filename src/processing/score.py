"""Deterministic keyword scoring for normalized job objects."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

DEFAULT_KEYWORDS_PATH = Path("config/keywords.yaml")
DEFAULT_SCORING_PATH = Path("config/scoring.yaml")
SEARCH_FIELDS = (
    "title",
    "location",
    "description",
    "summary",
    "requirements",
    "responsibilities",
    "notes",
)


class JobScoreResult(BaseModel):
    """Structured score output for a normalized job."""

    match_score: int
    match_reasons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


@lru_cache(maxsize=1)
def load_keywords_config(path: str = str(DEFAULT_KEYWORDS_PATH)) -> dict[str, Any]:
    """Load keyword configuration from YAML."""

    return _read_yaml(Path(path))


@lru_cache(maxsize=1)
def load_scoring_config(path: str = str(DEFAULT_SCORING_PATH)) -> dict[str, Any]:
    """Load scoring configuration from YAML."""

    return _read_yaml(Path(path))


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _build_search_text(job: dict[str, Any], fields: tuple[str, ...] = SEARCH_FIELDS) -> str:
    parts: list[str] = []
    for field in fields:
        value = job.get(field)
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value if item is not None)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def _match_first(text: str, phrases: list[str]) -> str | None:
    for phrase in phrases:
        normalized = phrase.strip().lower()
        if normalized and normalized in text:
            return phrase
    return None


def _match_many(text: str, lookup: dict[str, list[str]]) -> list[str]:
    matches: list[str] = []
    for canonical, patterns in lookup.items():
        normalized_patterns = [pattern.strip().lower() for pattern in patterns if pattern.strip()]
        if any(pattern in text for pattern in normalized_patterns):
            matches.append(canonical)
    return matches


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def score_job(
    job: dict[str, Any],
    *,
    keywords_path: Path = DEFAULT_KEYWORDS_PATH,
    scoring_path: Path = DEFAULT_SCORING_PATH,
) -> JobScoreResult:
    """Score a normalized job object using deterministic keyword rules."""

    keywords = load_keywords_config(str(keywords_path))
    scoring = load_scoring_config(str(scoring_path))
    weights = scoring["weights"]

    title_text = _normalize_text(job.get("title"))
    full_text = _build_search_text(job)
    location_text = _normalize_text(job.get("location"))

    match_score = 0
    match_reasons: list[str] = []
    risk_flags: list[str] = []

    target_roles = keywords.get("target_roles", [])
    title_role = _match_first(title_text, target_roles)
    if title_role:
        match_score += int(weights["role_in_title"])
        match_reasons.append(f"title matches target role: {title_role}")
    else:
        text_role = _match_first(full_text, target_roles)
        if text_role:
            match_score += int(weights["role_in_text"])
            match_reasons.append(f"description mentions target role: {text_role}")

    matched_skills = _match_many(full_text, keywords.get("target_skills", {}))
    if matched_skills:
        skill_points = min(
            len(matched_skills) * int(weights["skill_per_match"]),
            int(weights["skill_cap"]),
        )
        match_score += skill_points
        match_reasons.append(
            "matched skills: " + ", ".join(matched_skills)
        )

    matched_locations = [
        location
        for location in keywords.get("locations", [])
        if location.strip().lower() in location_text or location.strip().lower() in full_text
    ]
    if matched_locations:
        location_points = min(
            len(matched_locations) * int(weights["location_per_match"]),
            int(weights["location_cap"]),
        )
        match_score += location_points
        match_reasons.append(
            "location signals: " + ", ".join(matched_locations)
        )

    support_lookup = {signal: [signal] for signal in scoring.get("support_signals", [])}
    matched_support = _match_many(full_text, support_lookup)
    if matched_support:
        support_points = min(
            len(matched_support) * int(weights["support_signal_bonus"]),
            int(weights["support_signal_cap"]),
        )
        match_score += support_points
        match_reasons.append(
            "support/ops signals: " + ", ".join(matched_support)
        )

    negative_lookup = {
        signal: [signal]
        for signal in keywords.get("negative_signals", [])
    }
    matched_negatives = _match_many(full_text, negative_lookup)
    if matched_negatives:
        penalty = min(
            len(matched_negatives) * int(weights["negative_penalty"]),
            int(weights["negative_cap"]),
        )
        match_score -= penalty
        risk_flags.extend(f"negative signal: {signal}" for signal in matched_negatives)

    return JobScoreResult(
        match_score=_clamp_score(match_score),
        match_reasons=match_reasons,
        risk_flags=risk_flags,
    )
