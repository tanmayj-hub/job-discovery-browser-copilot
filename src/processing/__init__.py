"""Parsing, deduplication, and enrichment package."""

from .score import (
    JobScoreExplanation,
    JobScoreResult,
    explain_job_score,
    is_relevant_score,
    score_job,
)

__all__ = [
    "JobScoreExplanation",
    "JobScoreResult",
    "explain_job_score",
    "is_relevant_score",
    "score_job",
]
