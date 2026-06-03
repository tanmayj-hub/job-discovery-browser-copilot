"""Deterministic ATS and job-board detection helpers."""

from __future__ import annotations

from urllib.parse import urlparse

RESTRICTED_DOMAINS = ("linkedin.com", "indeed.com", "glassdoor.com")

ATS_URL_PATTERNS: dict[str, tuple[str, ...]] = {
    "greenhouse": (
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "boards-api.greenhouse.io",
    ),
    "lever": (
        "jobs.lever.co",
        "api.lever.co",
    ),
    "ashby": (
        "ashbyhq.com",
        "jobs.ashbyhq.com",
    ),
    "smartrecruiters": (
        "smartrecruiters.com",
        "jobs.smartrecruiters.com",
    ),
    "workday": (
        "myworkdayjobs.com",
        "workdayjobs.com",
    ),
    "successfactors": (
        "successfactors.com",
        "sapsf.com",
    ),
    "oracle_hcm": (
        "oraclecloud.com",
        "fa-ext.oraclecloud.com",
    ),
    "icims": (
        "icims.com",
    ),
    "phenom": (
        "phenompeople.com",
    ),
}

ATS_HINT_PATTERNS: dict[str, tuple[str, ...]] = {
    "greenhouse": ("greenhouse",),
    "lever": ("lever",),
    "ashby": ("ashby", "ashbyhq"),
    "smartrecruiters": ("smartrecruiters", "smart recruiters", "smart_recruiters"),
    "workday": ("workday",),
    "successfactors": ("successfactors", "success factors", "success_factors", "sapsf"),
    "oracle_hcm": ("oracle", "oraclecloud", "oracle cloud", "oracle_hcm"),
    "icims": ("icims",),
    "phenom": ("phenom",),
}

API_ALLOWED_ATS = {"greenhouse", "lever", "ashby", "smartrecruiters"}
HUMAN_IN_LOOP_ATS = {"workday", "successfactors", "oracle_hcm", "icims", "phenom", "ultipro"}

NORMALIZED_HINTS = {
    "ashbyhq": "ashby",
    "greenhouseio": "greenhouse",
    "oraclecloud": "oracle_hcm",
    "oracle_hcm": "oracle_hcm",
    "oracle": "oracle_hcm",
    "sapsf": "successfactors",
    "smart_recruiters": "smartrecruiters",
    "success_factors": "successfactors",
}


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip().lower()


def _is_valid_public_url(url: str | None) -> bool:
    text = str(url or "").strip()
    if not text:
        return False
    parsed = urlparse(text)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_ats_hint(ats_hint: str | None) -> str | None:
    """Normalize ATS hint text to one supported canonical value."""

    text = _normalize_text(ats_hint).replace("-", "_").replace(" ", "_")
    if not text:
        return None
    text = NORMALIZED_HINTS.get(text, text)
    if text in ATS_HINT_PATTERNS or text == "restricted_board" or text == "ultipro":
        return text
    return None


def is_restricted_job_board(url: str | None) -> bool:
    """Return True when the URL points to a manual-only public job board."""

    if not _is_valid_public_url(url):
        return False
    hostname = urlparse(str(url)).netloc.lower()
    return any(domain in hostname for domain in RESTRICTED_DOMAINS)


def detect_ats_type(
    url: str | None,
    ats_hint: str | None = None,
    website_category: str | None = None,
) -> str | None:
    """Detect the ATS type from a URL and optional hint fields."""

    if is_restricted_job_board(url):
        return "restricted_board"

    for candidate in (ats_hint, website_category):
        candidate_text = _normalize_text(candidate)
        if any(term in candidate_text for term in ("linkedin", "indeed", "glassdoor")):
            return "restricted_board"
        normalized_hint = normalize_ats_hint(candidate)
        if normalized_hint:
            return normalized_hint
        for ats_type, patterns in ATS_HINT_PATTERNS.items():
            if any(pattern in candidate_text for pattern in patterns):
                return ats_type

    if not _is_valid_public_url(url):
        return None

    parsed = urlparse(str(url))
    hostname = parsed.netloc.lower()
    for ats_type, patterns in ATS_URL_PATTERNS.items():
        if any(hostname == pattern or hostname.endswith(f".{pattern}") for pattern in patterns):
            return ats_type
    return None


def select_source_mode(
    url: str | None,
    ats_type: str | None,
    current_source_mode: str | None = None,
) -> str:
    """Select the operating mode for a source based on ATS type and URL."""

    explicit_mode = _normalize_text(current_source_mode)
    if explicit_mode in {"manual_only", "avoid"}:
        return explicit_mode
    if not _is_valid_public_url(url):
        return "needs_url"
    if ats_type == "restricted_board":
        return "manual_only"
    if ats_type in API_ALLOWED_ATS:
        return "api_allowed"
    if ats_type in HUMAN_IN_LOOP_ATS:
        return "human_in_loop"
    return "browser_allowed"
