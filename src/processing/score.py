"""Deterministic keyword scoring for normalized job objects."""

from __future__ import annotations

import re
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
    relevance_tier: str = "not_relevant"


class JobScoreExplanation(BaseModel):
    """Human-readable explanation of deterministic scoring output."""

    title: str
    company: str
    location: str
    final_score: int
    threshold: str
    is_relevant: bool
    relevance_tier: str
    positive_keyword_matches: list[str] = Field(default_factory=list)
    negative_keyword_matches: list[str] = Field(default_factory=list)
    title_matches: list[str] = Field(default_factory=list)
    description_matches: list[str] = Field(default_factory=list)
    location_scope_signals: list[str] = Field(default_factory=list)
    support_signal_matches: list[str] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    reason_summary: str


CORE_REASON_PREFIXES = (
    "title matches",
    "description mentions",
    "matched skills",
    "support/ops signals",
)
ADJACENT_REASON_PREFIX = "adjacent customer-facing technical fit"
CORE_TARGET_TIER = "core_target_fit"
ADJACENT_TARGET_TIER = "adjacent_customer_facing_technical_fit"
NOT_RELEVANT_TIER = "not_relevant"
TECHNICAL_SUPPORT_CONTEXT_TERMS = (
    "technical",
    "technology",
    "it ",
    " it",
    "platform",
    "cloud",
    "system",
    "systems",
    "software",
    "application",
    "applications",
    "production",
    "infrastructure",
    "linux",
    "network",
    "desktop",
    "endpoint",
    "trading",
    "marketview",
)
ALWAYS_REJECT_TITLE_PATTERNS = (
    "executive assistant",
)
CONDITIONAL_REJECT_TITLE_PATTERNS = (
    "mortgage specialist",
    "banking advisor",
    "private banking officer",
    "branch advisor",
    "customer experience associate",
    "wealth management associate program",
    "customer service representative",
    "client service representative",
    "sales associate",
    "client delivery associate",
    "sales specialist",
)
STRONG_TECHNICAL_CONTEXT_TERMS = (
    "cloud",
    "platform",
    "systems",
    "software",
    "infrastructure",
    "devops",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "linux",
    "security",
    "integration",
    "implementation",
    "architecture",
    "architect",
    "engineer",
    "technical support",
    "support engineer",
    "customer engineer",
    "solutions engineer",
    "technical account manager",
    "data",
    "api",
)
ADJACENT_TITLE_TECHNICAL_HINTS = (
    "engineer",
    "architect",
    "technical",
    "cloud",
    "platform",
    "systems",
    "software",
    "data",
    "security",
    "api",
    "infrastructure",
    "devops",
    "support",
)
ADJACENT_TECHNICAL_CONTEXT_TERMS = (
    "technical",
    "platform",
    "cloud",
    "software",
    "system",
    "systems",
    "implementation",
    "integration",
    "architecture",
    "architect",
    "salesforce",
    "dynamics",
    "crm",
    "saas",
    "data",
    "security",
    "api",
    "infrastructure",
    "devops",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "linux",
)


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
            parts.extend(_clean_search_text(str(item)) for item in value if item is not None)
        elif value is not None:
            parts.append(_clean_search_text(str(value)))
    return " ".join(parts).lower()


def _match_first(text: str, phrases: list[str]) -> str | None:
    for phrase in phrases:
        normalized = phrase.strip().lower()
        if _contains_phrase(text, normalized):
            return phrase
    return None


def _match_many(text: str, lookup: dict[str, list[str]]) -> list[str]:
    matches: list[str] = []
    for canonical, patterns in lookup.items():
        normalized_patterns = [pattern.strip().lower() for pattern in patterns if pattern.strip()]
        if any(_contains_phrase(text, pattern) for pattern in normalized_patterns):
            matches.append(canonical)
    return matches


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _clean_search_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return " ".join(text.split())


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_text = str(text or "").strip().lower()
    normalized_phrase = str(phrase or "").strip().lower()
    if not normalized_text or not normalized_phrase:
        return False
    escaped = re.escape(normalized_phrase)
    escaped = escaped.replace(r"\ ", r"\s+")
    pattern = re.compile(rf"(?<!\w){escaped}(?!\w)")
    return bool(pattern.search(normalized_text))


def is_relevant_score(
    match_score: int,
    match_reasons: list[str],
) -> bool:
    """Return True when a score qualifies for saving under current MVP rules."""

    if int(match_score) <= 0:
        return False
    normalized_reasons = [str(reason).lower() for reason in match_reasons]
    return any(
        reason.startswith(prefix)
        for reason in normalized_reasons
        for prefix in (*CORE_REASON_PREFIXES, ADJACENT_REASON_PREFIX)
    )


def _determine_relevance_tier(
    match_score: int,
    match_reasons: list[str],
) -> str:
    if int(match_score) <= 0:
        return NOT_RELEVANT_TIER

    normalized_reasons = [str(reason).lower() for reason in match_reasons]
    if any(
        reason.startswith(prefix)
        for reason in normalized_reasons
        for prefix in CORE_REASON_PREFIXES[:2]
    ):
        return CORE_TARGET_TIER
    if any(reason.startswith(ADJACENT_REASON_PREFIX) for reason in normalized_reasons):
        return ADJACENT_TARGET_TIER
    if any(
        reason.startswith(prefix)
        for reason in normalized_reasons
        for prefix in CORE_REASON_PREFIXES[2:]
    ):
        return CORE_TARGET_TIER
    return NOT_RELEVANT_TIER


def _has_technical_support_context(
    title_text: str,
    full_text: str,
    matched_skills: list[str],
) -> bool:
    support_title_patterns = (
        "support analyst",
        "support engineer",
        "support administrator",
        "support specialist",
        "it support",
    )
    if any(pattern in title_text for pattern in support_title_patterns):
        return True
    if matched_skills:
        return True
    return any(term in full_text for term in TECHNICAL_SUPPORT_CONTEXT_TERMS)


def _filter_contextual_skill_matches(
    title_text: str,
    full_text: str,
    matched_skills: list[str],
) -> list[str]:
    gated_skills = {"support", "troubleshooting"}
    non_gated_matches = [skill for skill in matched_skills if skill not in gated_skills]
    support_context = _has_technical_support_context(
        title_text,
        full_text,
        non_gated_matches,
    )
    filtered_matches: list[str] = []
    for skill in matched_skills:
        if skill in gated_skills and not support_context:
            continue
        filtered_matches.append(skill)
    return filtered_matches


def _has_strong_technical_context(text: str) -> bool:
    return any(_contains_phrase(text, term) for term in STRONG_TECHNICAL_CONTEXT_TERMS)


def _has_adjacent_title_technical_hint(title_text: str) -> bool:
    return any(_contains_phrase(title_text, term) for term in ADJACENT_TITLE_TECHNICAL_HINTS)


def _match_rejected_title_pattern(title_text: str) -> str | None:
    for pattern in ALWAYS_REJECT_TITLE_PATTERNS:
        if _contains_phrase(title_text, pattern):
            return pattern
    for pattern in CONDITIONAL_REJECT_TITLE_PATTERNS:
        if _contains_phrase(title_text, pattern):
            return pattern
    return None


def _analyze_job_score(
    job: dict[str, Any],
    *,
    keywords_path: Path,
    scoring_path: Path,
) -> dict[str, Any]:
    keywords = load_keywords_config(str(keywords_path))
    scoring = load_scoring_config(str(scoring_path))
    weights = scoring["weights"]

    title_text = _normalize_text(job.get("title"))
    full_text = _build_search_text(job)
    location_text = _normalize_text(job.get("location"))

    rejected_title_pattern = _match_rejected_title_pattern(title_text)
    if rejected_title_pattern in ALWAYS_REJECT_TITLE_PATTERNS:
        return {
            "final_score": 0,
            "match_reasons": [],
            "risk_flags": [f"hard reject title: {rejected_title_pattern}"],
            "positive_keyword_matches": [],
            "negative_keyword_matches": [rejected_title_pattern],
            "title_matches": [],
            "description_matches": [],
            "location_scope_signals": [],
            "support_signal_matches": [],
            "relevance_tier": NOT_RELEVANT_TIER,
        }
    if (
        rejected_title_pattern in CONDITIONAL_REJECT_TITLE_PATTERNS
        and not _has_strong_technical_context(full_text)
    ):
        return {
            "final_score": 0,
            "match_reasons": [],
            "risk_flags": [f"hard reject title: {rejected_title_pattern}"],
            "positive_keyword_matches": [],
            "negative_keyword_matches": [rejected_title_pattern],
            "title_matches": [],
            "description_matches": [],
            "location_scope_signals": [],
            "support_signal_matches": [],
            "relevance_tier": NOT_RELEVANT_TIER,
        }

    match_score = 0
    match_reasons: list[str] = []
    risk_flags: list[str] = []
    positive_keyword_matches: list[str] = []
    negative_keyword_matches: list[str] = []
    title_matches: list[str] = []
    description_matches: list[str] = []
    location_scope_signals: list[str] = []
    support_signal_matches: list[str] = []

    target_roles = keywords.get("target_roles", [])
    title_role = _match_first(title_text, target_roles)
    if title_role:
        match_score += int(weights["role_in_title"])
        title_matches.append(title_role)
        positive_keyword_matches.append(title_role)
        match_reasons.append(f"title matches target role: {title_role}")
    else:
        text_role = _match_first(full_text, target_roles)
        if text_role:
            match_score += int(weights["role_in_text"])
            description_matches.append(text_role)
            positive_keyword_matches.append(text_role)
            match_reasons.append(f"description mentions target role: {text_role}")

    matched_skills = _filter_contextual_skill_matches(
        title_text,
        full_text,
        _match_many(full_text, keywords.get("target_skills", {})),
    )
    if matched_skills:
        skill_points = min(
            len(matched_skills) * int(weights["skill_per_match"]),
            int(weights["skill_cap"]),
        )
        match_score += skill_points
        positive_keyword_matches.extend(matched_skills)
        description_matches.extend(matched_skills)
        match_reasons.append("matched skills: " + ", ".join(matched_skills))

    matched_locations = [
        location
        for location in keywords.get("locations", [])
        if _contains_phrase(location_text, location.strip().lower())
        or _contains_phrase(full_text, location.strip().lower())
    ]
    if matched_locations:
        location_points = min(
            len(matched_locations) * int(weights["location_per_match"]),
            int(weights["location_cap"]),
        )
        match_score += location_points
        location_scope_signals.extend(matched_locations)
        match_reasons.append("location signals: " + ", ".join(matched_locations))

    support_lookup = {signal: [signal] for signal in scoring.get("support_signals", [])}
    matched_support = _match_many(full_text, support_lookup)
    if matched_support and _has_technical_support_context(
        title_text,
        full_text,
        matched_skills,
    ):
        support_points = min(
            len(matched_support) * int(weights["support_signal_bonus"]),
            int(weights["support_signal_cap"]),
        )
        match_score += support_points
        support_signal_matches.extend(matched_support)
        positive_keyword_matches.extend(matched_support)
        description_matches.extend(matched_support)
        match_reasons.append("support/ops signals: " + ", ".join(matched_support))

    adjacent_roles = keywords.get("adjacent_roles", [])
    conditional_adjacent_roles = keywords.get("conditional_adjacent_roles", [])
    adjacent_context_terms = keywords.get("adjacent_technical_context", [])
    adjacent_context_lookup = {
        signal: [signal]
        for signal in adjacent_context_terms
    }
    adjacent_context_matches = _match_many(full_text, adjacent_context_lookup)
    adjacent_technical_context_lookup = {
        signal: [signal]
        for signal in ADJACENT_TECHNICAL_CONTEXT_TERMS
    }
    adjacent_technical_context_matches = _match_many(
        full_text,
        adjacent_technical_context_lookup,
    )
    has_conditional_adjacent_context = bool(
        adjacent_context_matches or matched_skills or matched_support
    )
    has_adjacent_technical_context = bool(
        adjacent_technical_context_matches
        or matched_skills
        or matched_support
        or _has_adjacent_title_technical_hint(title_text)
    )

    title_adjacent_role = _match_first(title_text, adjacent_roles)
    if title_adjacent_role and has_adjacent_technical_context:
        match_score += int(weights["adjacent_role_in_title"])
        title_matches.append(title_adjacent_role)
        positive_keyword_matches.append(title_adjacent_role)
        match_reasons.append(f"{ADJACENT_REASON_PREFIX}: {title_adjacent_role}")
    else:
        text_adjacent_role = _match_first(full_text, adjacent_roles)
        if text_adjacent_role and has_adjacent_technical_context:
            match_score += int(weights["adjacent_role_in_text"])
            description_matches.append(text_adjacent_role)
            positive_keyword_matches.append(text_adjacent_role)
            match_reasons.append(f"{ADJACENT_REASON_PREFIX}: {text_adjacent_role}")

    conditional_title_role = _match_first(title_text, conditional_adjacent_roles)
    if conditional_title_role and has_conditional_adjacent_context:
        match_score += int(weights["conditional_adjacent_role_bonus"])
        title_matches.append(conditional_title_role)
        positive_keyword_matches.append(conditional_title_role)
        positive_keyword_matches.extend(adjacent_context_matches)
        description_matches.extend(adjacent_context_matches)
        match_reasons.append(
            f"{ADJACENT_REASON_PREFIX}: {conditional_title_role} (technical context)"
        )
    elif has_conditional_adjacent_context:
        conditional_text_role = _match_first(full_text, conditional_adjacent_roles)
        if conditional_text_role:
            match_score += int(weights["adjacent_role_in_text"])
            description_matches.append(conditional_text_role)
            description_matches.extend(adjacent_context_matches)
            positive_keyword_matches.append(conditional_text_role)
            positive_keyword_matches.extend(adjacent_context_matches)
            match_reasons.append(
                f"{ADJACENT_REASON_PREFIX}: {conditional_text_role} (technical context)"
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
        negative_keyword_matches.extend(matched_negatives)
        risk_flags.extend(f"negative signal: {signal}" for signal in matched_negatives)

    final_score = _clamp_score(match_score)
    relevance_tier = _determine_relevance_tier(final_score, match_reasons)
    return {
        "final_score": final_score,
        "match_reasons": match_reasons,
        "risk_flags": risk_flags,
        "positive_keyword_matches": list(dict.fromkeys(positive_keyword_matches)),
        "negative_keyword_matches": negative_keyword_matches,
        "title_matches": title_matches,
        "description_matches": list(dict.fromkeys(description_matches)),
        "location_scope_signals": location_scope_signals,
        "support_signal_matches": support_signal_matches,
        "relevance_tier": relevance_tier,
    }


def score_job(
    job: dict[str, Any],
    *,
    keywords_path: Path = DEFAULT_KEYWORDS_PATH,
    scoring_path: Path = DEFAULT_SCORING_PATH,
) -> JobScoreResult:
    """Score a normalized job object using deterministic keyword rules."""
    analysis = _analyze_job_score(
        job,
        keywords_path=keywords_path,
        scoring_path=scoring_path,
    )
    return JobScoreResult(
        match_score=analysis["final_score"],
        match_reasons=analysis["match_reasons"],
        risk_flags=analysis["risk_flags"],
        relevance_tier=analysis["relevance_tier"],
    )


def explain_job_score(
    job: dict[str, Any],
    *,
    keywords_path: Path = DEFAULT_KEYWORDS_PATH,
    scoring_path: Path = DEFAULT_SCORING_PATH,
) -> dict[str, Any]:
    """Explain how deterministic scoring evaluated a normalized job."""

    analysis = _analyze_job_score(
        job,
        keywords_path=keywords_path,
        scoring_path=scoring_path,
    )
    is_relevant = is_relevant_score(
        analysis["final_score"],
        analysis["match_reasons"],
    )
    relevance_tier = analysis["relevance_tier"]
    if relevance_tier == CORE_TARGET_TIER:
        reason_summary = (
            "Saved as relevant because the job had a positive score and at least one "
            "core non-location signal."
        )
    elif relevance_tier == ADJACENT_TARGET_TIER:
        reason_summary = (
            "Saved as an adjacent customer-facing technical fit because the role matched "
            "the secondary relevance bucket."
        )
    elif analysis["final_score"] <= 0:
        reason_summary = "Rejected because no positive scoring signals survived after penalties."
    elif analysis["match_reasons"]:
        reason_summary = (
            "Rejected because the score came from weak or location-only signals and did not "
            "include a core role, skill, or support/ops reason."
        )
    else:
        reason_summary = "Rejected because the job did not match the current target role profile."

    explanation = JobScoreExplanation(
        title=str(job.get("title") or "").strip(),
        company=str(job.get("company_name") or "").strip(),
        location=str(job.get("location") or "").strip(),
        final_score=analysis["final_score"],
        threshold=(
            "Relevant jobs must score above 0 and include at least one core or adjacent "
            "scoring reason: title match, description role match, matched skills, "
            "support/ops signals, or adjacent customer-facing technical fit."
        ),
        is_relevant=is_relevant,
        relevance_tier=relevance_tier,
        positive_keyword_matches=analysis["positive_keyword_matches"],
        negative_keyword_matches=analysis["negative_keyword_matches"],
        title_matches=analysis["title_matches"],
        description_matches=analysis["description_matches"],
        location_scope_signals=analysis["location_scope_signals"],
        support_signal_matches=analysis["support_signal_matches"],
        match_reasons=analysis["match_reasons"],
        risk_flags=analysis["risk_flags"],
        reason_summary=reason_summary,
    )
    return explanation.model_dump()
