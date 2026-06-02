"""Detection and recording of browser-side interventions."""

from __future__ import annotations

import sqlite3
from typing import Any

from storage.db import create_intervention

BARRIER_SIGNAL_LOGIN = "login_required"
BARRIER_SIGNAL_CAPTCHA = "captcha_detected"
BARRIER_SIGNAL_COOKIE = "cookie_blocked"
BARRIER_SIGNAL_LOCATION = "location_selection_required"
BARRIER_SIGNAL_UNCLEAR = "unclear_layout"
BARRIER_SIGNAL_EXTRACTION_FAILED = "extraction_failed"


def detect_browser_barriers(
    *,
    page_text: str,
    page_html: str,
    extracted_count: int,
    has_search_input: bool,
) -> list[str]:
    """Detect blocking conditions that require human intervention."""

    text = page_text.lower()
    html = page_html.lower()
    signals: list[str] = []

    if (
        "captcha" in text
        or "i'm not a robot" in text
        or "g-recaptcha" in html
        or "hcaptcha" in html
    ):
        signals.append(BARRIER_SIGNAL_CAPTCHA)

    if (
        "sign in" in text
        or "log in" in text
        or 'type="password"' in html
        or "password" in text and "email" in text
    ):
        signals.append(BARRIER_SIGNAL_LOGIN)

    if "cookie" in text and (
        "accept" in text
        or "reject" in text
        or "consent" in text
    ):
        signals.append(BARRIER_SIGNAL_COOKIE)

    if (
        "select location" in text
        or "choose location" in text
        or ("location" in text and "<select" in html)
        or 'name="location"' in html
        or 'id="location"' in html
    ):
        signals.append(BARRIER_SIGNAL_LOCATION)

    if extracted_count == 0 and not has_search_input:
        job_hints = ("career", "job", "opening", "opportunity", "position")
        if not any(hint in text for hint in job_hints):
            signals.append(BARRIER_SIGNAL_UNCLEAR)

    return list(dict.fromkeys(signals))


def create_browser_intervention(
    connection: sqlite3.Connection,
    *,
    company_name: str,
    source_name: str,
    signals: list[str],
    source_url: str | None = None,
    job_id: int | None = None,
    notes: str | None = None,
) -> int:
    """Persist a browser intervention and return its id."""

    note_text = notes or (
        f"Paused browser collection for {company_name} ({source_name}) due to: "
        f"{', '.join(signals)}"
    )
    return create_intervention(
        connection,
        company_name=company_name,
        job_id=job_id,
        intervention_type="browser_pause",
        reason=signals[0] if signals else BARRIER_SIGNAL_UNCLEAR,
        source_url=source_url,
        notes=note_text,
    )


def build_intervention_result(
    *,
    company_name: str,
    source_name: str,
    signals: list[str],
    intervention_id: int | None = None,
) -> dict[str, Any]:
    """Return a structured paused result for collectors."""

    return {
        "company_name": company_name,
        "source_name": source_name,
        "status": "paused",
        "signals": signals,
        "intervention_id": intervention_id,
        "jobs_seen": 0,
        "jobs_new": 0,
    }
