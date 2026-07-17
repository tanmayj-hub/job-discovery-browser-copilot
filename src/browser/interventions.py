"""Detection and recording of browser-side interventions."""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from storage.db import create_intervention

BARRIER_SIGNAL_LOGIN = "login_required"
BARRIER_SIGNAL_CAPTCHA = "captcha_detected"
BARRIER_SIGNAL_COOKIE = "cookie_blocked"
BARRIER_SIGNAL_LOCATION = "location_selection_required"
BARRIER_SIGNAL_UNCLEAR = "unclear_layout"
BARRIER_SIGNAL_EXTRACTION_FAILED = "extraction_failed"


def _has_captcha_challenge(text: str, html: str) -> bool:
    """Detect an actual CAPTCHA challenge instead of a sitewide hidden widget."""

    explicit_text_markers = (
        "captcha",
        "i'm not a robot",
        "verify you are human",
        "made us think that you are a bot",
        "please solve this captcha",
        "security check",
    )
    if any(marker in text for marker in explicit_text_markers):
        return True

    has_captcha_widget = "g-recaptcha" in html or "hcaptcha" in html
    hidden_widget_markers = (
        "size=invisible",
        'display: none',
        'aria-hidden="true"',
    )
    return has_captcha_widget and not all(marker in html for marker in hidden_widget_markers)


def _has_login_gate(text: str, html: str) -> bool:
    """Detect a real login gate without flagging a harmless navigation link."""

    gate_phrases = (
        "sign in to continue",
        "log in to continue",
        "please sign in",
        "please log in",
        "login required",
        "sign in required",
        "create an account to continue",
        "sign in or create an account",
    )
    if any(phrase in text for phrase in gate_phrases):
        return True

    has_password_field = 'type="password"' in html
    has_auth_copy = (
        "password" in text and "email" in text
    ) or "username" in text or "forgot password" in text
    return has_password_field or has_auth_copy


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

    if _has_captcha_challenge(text, html):
        signals.append(BARRIER_SIGNAL_CAPTCHA)

    if _has_login_gate(text, html):
        signals.append(BARRIER_SIGNAL_LOGIN)

    # A footer "Cookie Settings" link is not a blocking banner. Require nearby
    # consent-action language before pausing an otherwise usable job board.
    if re.search(
        r"(?:cookie|consent).{0,500}(?:accept|reject|manage preferences)"
        r"|(?:accept|reject|manage preferences).{0,500}(?:cookie|consent)",
        text,
        flags=re.DOTALL,
    ):
        signals.append(BARRIER_SIGNAL_COOKIE)

    if (
        "select location" in text
        or "choose location" in text
        or "location required" in text
        or "please select a location" in text
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
