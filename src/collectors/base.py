"""Shared normalized collector models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class NormalizedJob:
    """Normalized collector job record for future collector integrations."""

    company_name: str
    title: str
    location: str | None = None
    job_url: str | None = None
    apply_url: str | None = None
    source_name: str | None = None
    source_mode: str | None = None
    description: str | None = None
    date_posted: str | None = None
    external_job_id: str | None = None
    ats_type: str | None = None
    board_slug: str | None = None
    raw_payload_json: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CollectorResult:
    """Normalized collector result returned by routing helpers."""

    company_name: str
    source_name: str | None
    status: str
    collector: str
    ats_type: str | None
    source_mode: str | None
    jobs_discovered: int = 0
    jobs_scored: int = 0
    jobs_relevant: int = 0
    jobs_saved: int = 0
    jobs: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    fallback_used: bool = False
    intervention_required: bool = False
    location_scope_used: bool = False
    keyword_scope_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
