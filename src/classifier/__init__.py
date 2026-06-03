"""Company and job classification package."""

from .ats_detector import (
    detect_ats_type,
    is_restricted_job_board,
    normalize_ats_hint,
    select_source_mode,
)
from .policy_engine import PolicyDecision, evaluate_source_policy, handle_browsing_barrier
from .source_classifier import SourceClassificationResult, classify_source

__all__ = [
    "PolicyDecision",
    "SourceClassificationResult",
    "classify_source",
    "detect_ats_type",
    "evaluate_source_policy",
    "handle_browsing_barrier",
    "is_restricted_job_board",
    "normalize_ats_hint",
    "select_source_mode",
]
