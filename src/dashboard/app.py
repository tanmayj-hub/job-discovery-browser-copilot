"""Streamlit dashboard for the Job Discovery Browser Co-Pilot."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
BASE_DIR = SRC_DIR.parent
COMPANIES_CONFIG_PATH = BASE_DIR / "config" / "companies.yaml"
STARTER_CAREER_URLS_PATH = BASE_DIR / "config" / "starter_career_urls.yaml"
DATABASE_PATH = BASE_DIR / "data" / "job_discovery.db"
EXPORTS_DIR = BASE_DIR / "data" / "exports"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def get_storage_api() -> dict[str, Any]:
    """Load storage helpers after the src path is available."""

    from storage import (
        append_intervention_notes,
        get_companies,
        get_companies_needing_url,
        get_dashboard_overview,
        get_intervention_queue,
        get_jobs,
        initialize_database,
        update_company_source,
        update_intervention_status,
        update_job_status,
        upsert_companies,
    )

    return {
        "append_intervention_notes": append_intervention_notes,
        "get_companies": get_companies,
        "get_companies_needing_url": get_companies_needing_url,
        "get_dashboard_overview": get_dashboard_overview,
        "get_intervention_queue": get_intervention_queue,
        "get_jobs": get_jobs,
        "initialize_database": initialize_database,
        "update_company_source": update_company_source,
        "update_intervention_status": update_intervention_status,
        "update_job_status": update_job_status,
        "upsert_companies": upsert_companies,
    }


def get_classifier_api() -> dict[str, Any]:
    """Load source classification helpers after the src path is available."""

    from classifier.source_classifier import classify_source
    from importer.excel_importer import update_company_record_in_yaml

    return {
        "classify_source": classify_source,
        "update_company_record_in_yaml": update_company_record_in_yaml,
    }


def get_importer_api() -> dict[str, Any]:
    """Load importer helpers after the src path is available."""

    from dashboard.starter_urls import build_starter_career_url_map
    from importer.apply_career_urls import apply_career_url_updates

    return {
        "apply_career_url_updates": apply_career_url_updates,
        "build_starter_career_url_map": build_starter_career_url_map,
    }


def get_dashboard_api() -> dict[str, Any]:
    """Load dashboard-specific helpers after the src path is available."""

    from dashboard.manual_entry import score_and_save_manual_job

    return {
        "score_and_save_manual_job": score_and_save_manual_job,
    }


def load_companies_config() -> list[dict[str, Any]]:
    """Load the company watchlist from YAML."""

    payload = yaml.safe_load(COMPANIES_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    companies = payload.get("companies", [])
    return companies if isinstance(companies, list) else []


def seed_companies_if_needed(connection: Any) -> None:
    """Populate companies into SQLite on first dashboard launch."""

    storage_api = get_storage_api()
    overview = storage_api["get_dashboard_overview"](connection)
    if overview["total_companies"] == 0:
        storage_api["upsert_companies"](connection, load_companies_config())


@st.cache_resource(show_spinner=False)
def get_connection() -> Any:
    """Create one cached SQLite connection for the dashboard session."""

    storage_api = get_storage_api()
    connection = storage_api["initialize_database"](DATABASE_PATH)
    seed_companies_if_needed(connection)
    return connection


def render_styles() -> None:
    """Apply a clean, professional visual treatment."""

    st.set_page_config(
        page_title="Job Discovery Browser Co-Pilot",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(
                    circle at top left,
                    #eef4eb 0,
                    rgba(238, 244, 235, 0.7) 24%,
                    transparent 48%
                ),
                linear-gradient(180deg, #f6f4ee 0%, #fcfbf8 100%);
        }
        .block-container {
            max-width: 1420px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3 {
            color: #223528;
            letter-spacing: -0.02em;
        }
        p, li, label {
            color: #324538;
        }
        div[data-testid="metric-container"] {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid #d7e0d3;
            padding: 1rem;
            border-radius: 18px;
            box-shadow: 0 12px 26px rgba(36, 53, 40, 0.05);
        }
        .hero {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid #d7e0d3;
            border-radius: 22px;
            padding: 1.35rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 18px 34px rgba(36, 53, 40, 0.06);
        }
        .hero-title {
            font-size: 2rem;
            font-weight: 700;
            color: #223528;
            margin-bottom: 0.2rem;
        }
        .hero-copy {
            color: #48604d;
            font-size: 1rem;
            margin: 0;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #dde5d9;
            border-radius: 18px;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.9);
        }
        .detail-card {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid #dde5d9;
            border-radius: 18px;
            padding: 1rem 1.1rem;
            margin-top: 0.5rem;
        }
        .detail-muted {
            color: #5a6d5e;
            font-size: 0.92rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_timestamp(value: object) -> str:
    """Render timestamps consistently for dashboard tables."""

    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
    text = str(value).strip()
    if not text:
        return "-"
    return text.replace("T", " ")[:19]


def format_list_value(value: object) -> str:
    """Render list-like fields as comma-separated text."""

    if value is None:
        return "-"
    if isinstance(value, str):
        return value or "-"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value) or "-"
    return str(value)


def render_section_heading(title: str) -> None:
    """Render a consistent section heading that stays readable across themes."""

    st.markdown(
        f'<h2 style="color: #223528; margin: 0.35rem 0 0.25rem 0;">{title}</h2>',
        unsafe_allow_html=True,
    )


def prepare_jobs_table_rows(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert job records into display-ready rows."""

    rows: list[dict[str, Any]] = []
    for job in jobs:
        rows.append(
            {
                "ID": job["id"],
                "Company": job["company_name"],
                "Sector": job.get("sector") or "-",
                "Title": job["title"],
                "Location": job.get("location") or "-",
                "Score": job.get("match_score", 0),
                "Status": job.get("status") or "new",
                "Source Mode": job.get("source_mode") or "-",
                "First Seen": format_timestamp(job.get("first_seen")),
                "Last Seen": format_timestamp(job.get("last_seen")),
                "Match Reasons": format_list_value(job.get("match_reasons")),
                "Risk Flags": format_list_value(job.get("risk_flags")),
            }
        )
    return rows


def filter_jobs(
    jobs: list[dict[str, Any]],
    *,
    selected_company: str,
    selected_sector: str,
    min_score: int,
    selected_status: str,
) -> list[dict[str, Any]]:
    """Apply user-selected dashboard filters to jobs."""

    filtered: list[dict[str, Any]] = []
    for job in jobs:
        if selected_company != "All" and job["company_name"] != selected_company:
            continue
        if selected_sector != "All" and (job.get("sector") or "-") != selected_sector:
            continue
        if int(job.get("match_score", 0)) < min_score:
            continue
        if selected_status != "All" and job.get("status", "new") != selected_status:
            continue
        filtered.append(job)
    return filtered


def job_option_label(job: dict[str, Any]) -> str:
    """Build a concise job label for selection controls."""

    location = job.get("location") or "Location TBD"
    return (
        f"{job['company_name']} | {job['title']} | {location} | "
        f"Score {job.get('match_score', 0)}"
    )


def render_job_details(
    connection: Any,
    job: dict[str, Any],
    *,
    key_prefix: str,
) -> None:
    """Render one selected job and actions."""

    storage_api = get_storage_api()

    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
    title_col, meta_col = st.columns([2.2, 1.2])
    with title_col:
        st.subheader(job["title"])
        st.caption(
            f"{job['company_name']} | {job.get('location') or 'Location TBD'} | "
            f"Source mode: {job.get('source_mode') or '-'}"
        )
    with meta_col:
        st.metric("Match Score", int(job.get("match_score", 0)))
        st.write(f"Status: `{job.get('status', 'new')}`")

    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        st.write(f"First seen: `{format_timestamp(job.get('first_seen'))}`")
    with info_col2:
        st.write(f"Last seen: `{format_timestamp(job.get('last_seen'))}`")
    with info_col3:
        st.write(f"Sector: `{job.get('sector') or '-'}`")

    st.write("Match reasons")
    st.write(format_list_value(job.get("match_reasons")))
    st.write("Risk flags")
    st.write(format_list_value(job.get("risk_flags")))

    if job.get("description"):
        with st.expander("Job description preview"):
            st.write(job["description"])

    link_col1, link_col2, _ = st.columns([1, 1, 2])
    with link_col1:
        if job.get("job_url"):
            st.link_button("Open job URL", job["job_url"], use_container_width=True)
    with link_col2:
        if job.get("apply_url"):
            st.link_button("Open apply URL", job["apply_url"], use_container_width=True)

    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("Mark saved", key=f"{key_prefix}_save_{job['id']}", use_container_width=True):
            storage_api["update_job_status"](connection, job["id"], "saved")
            st.rerun()
    with action_col2:
        if st.button(
            "Mark rejected",
            key=f"{key_prefix}_reject_{job['id']}",
            use_container_width=True,
        ):
            storage_api["update_job_status"](connection, job["id"], "rejected")
            st.rerun()
    with action_col3:
        if st.button(
            "Mark reviewed",
            key=f"{key_prefix}_review_{job['id']}",
            use_container_width=True,
        ):
            storage_api["update_job_status"](connection, job["id"], "reviewed")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_jobs_tab(connection: Any) -> None:
    """Render the Jobs Found tab."""

    storage_api = get_storage_api()
    jobs = storage_api["get_jobs"](connection)

    render_section_heading("Jobs Found")
    st.caption("Filter discovered jobs, review fit signals, and update status.")

    if not jobs:
        st.info(
            "No jobs are in the database yet. "
            "Run a collector or daily workflow to populate this view."
        )
        return

    companies = ["All", *sorted({job["company_name"] for job in jobs})]
    sectors = ["All", *sorted({job.get("sector") or "-" for job in jobs})]
    statuses = ["All", *sorted({job.get("status", "new") for job in jobs})]

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        selected_company = st.selectbox("Company", companies, key="jobs_company_filter")
    with filter_col2:
        selected_sector = st.selectbox("Sector", sectors, key="jobs_sector_filter")
    with filter_col3:
        min_score = st.slider("Minimum score", min_value=0, max_value=100, value=0, step=5)
    with filter_col4:
        selected_status = st.selectbox("Status", statuses, key="jobs_status_filter")

    filtered_jobs = filter_jobs(
        jobs,
        selected_company=selected_company,
        selected_sector=selected_sector,
        min_score=min_score,
        selected_status=selected_status,
    )
    st.caption(f"{len(filtered_jobs)} jobs match the current filters.")
    st.dataframe(prepare_jobs_table_rows(filtered_jobs), hide_index=True, use_container_width=True)

    if not filtered_jobs:
        return

    selected_job_id = st.selectbox(
        "Review job",
        options=[job["id"] for job in filtered_jobs],
        format_func=lambda job_id: job_option_label(
            next(job for job in filtered_jobs if job["id"] == job_id),
        ),
        key="jobs_found_selector",
    )
    selected_job = next(job for job in filtered_jobs if job["id"] == selected_job_id)
    render_job_details(connection, selected_job, key_prefix="jobs_found")


def render_saved_jobs_tab(connection: Any) -> None:
    """Render the Saved Jobs tab."""

    storage_api = get_storage_api()
    saved_jobs = storage_api["get_jobs"](connection, status="saved")

    render_section_heading("Saved Jobs")
    st.caption("Shortlist jobs that are worth manual follow-up.")

    if not saved_jobs:
        st.info("No jobs are marked as saved yet.")
        return

    st.dataframe(prepare_jobs_table_rows(saved_jobs), hide_index=True, use_container_width=True)
    selected_job_id = st.selectbox(
        "Review saved job",
        options=[job["id"] for job in saved_jobs],
        format_func=lambda job_id: job_option_label(
            next(job for job in saved_jobs if job["id"] == job_id),
        ),
        key="saved_jobs_selector",
    )
    selected_job = next(job for job in saved_jobs if job["id"] == selected_job_id)
    render_job_details(connection, selected_job, key_prefix="saved_jobs")


def render_company_watchlist_tab(connection: Any) -> None:
    """Render the company watchlist tab."""

    storage_api = get_storage_api()
    companies = storage_api["get_companies"](connection)

    render_section_heading("Company Watchlist")
    st.caption("Track source readiness, ATS hints, and current monitoring status.")

    if not companies:
        st.info("No companies are loaded yet.")
        return

    rows = [
        {
            "Company": company["name"],
            "Sector": company.get("sector") or "-",
            "Category": company.get("category") or "-",
            "Priority": company.get("priority") or "-",
            "Source Mode": company.get("source_mode") or "-",
            "ATS Hint": company.get("ats_hint") or "-",
            "Status": company.get("status") or "-",
        }
        for company in companies
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def render_missing_urls_tab(connection: Any) -> None:
    """Render the URL completion workflow."""

    storage_api = get_storage_api()
    classifier_api = get_classifier_api()
    importer_api = get_importer_api()
    missing_companies = storage_api["get_companies_needing_url"](connection)
    feedback = st.session_state.pop("missing_urls_feedback", None)
    starter_apply_feedback = st.session_state.pop("starter_apply_feedback", None)
    starter_map = importer_api["build_starter_career_url_map"](STARTER_CAREER_URLS_PATH)

    render_section_heading("Missing URLs")
    st.caption("Fill in careers URLs and reclassify those companies into the right source mode.")

    if feedback:
        st.success(
            f"Saved {feedback['company_name']} with source mode `{feedback['source_mode']}`."
        )
        if feedback.get("reasons"):
            st.info(f"Classification reason: {' | '.join(feedback['reasons'])}")
    if starter_apply_feedback:
        st.success(
            "Applied starter career URLs. "
            f"Updated `{starter_apply_feedback['updated']}` companies."
        )
        st.info(
            " | ".join(
                [
                    f"Still missing: {starter_apply_feedback['still_missing']}",
                    f"API allowed: {starter_apply_feedback['api_allowed']}",
                    f"Browser allowed: {starter_apply_feedback['browser_allowed']}",
                    f"Human in loop: {starter_apply_feedback['human_in_loop']}",
                ]
            )
        )

    if not missing_companies:
        st.success("Every tracked company currently has a valid careers URL.")
        return

    verified_starter_count = sum(
        1 for entry in starter_map.values() if str(entry.get("careers_url") or "").strip()
    )
    action_col1, action_col2 = st.columns([1.2, 2])
    with action_col1:
        if st.button("Apply verified starter URLs", use_container_width=True):
            summary = importer_api["apply_career_url_updates"](
                starter_path=STARTER_CAREER_URLS_PATH,
                companies_path=COMPANIES_CONFIG_PATH,
            )
            storage_api["upsert_companies"](connection, load_companies_config())
            st.session_state["starter_apply_feedback"] = summary
            st.rerun()
    with action_col2:
        st.caption(
            f"{verified_starter_count} starter URLs are currently verified in "
            "`config/starter_career_urls.yaml`."
        )

    rows = [
        {
            "Company": company["name"],
            "Sector": company.get("sector") or "-",
            "Category": company.get("category") or "-",
            "Priority": company.get("priority") or "-",
            "ATS Hint": company.get("ats_hint") or "-",
            "Source Mode": company.get("source_mode") or "-",
        }
        for company in missing_companies
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)

    selected_company_name = st.selectbox(
        "Company to update",
        options=[company["name"] for company in missing_companies],
        key="missing_url_company_selector",
    )
    selected_company = next(
        company for company in missing_companies if company["name"] == selected_company_name
    )
    starter_entry = starter_map.get(selected_company_name, {})

    if starter_entry:
        st.markdown('<div class="detail-card">', unsafe_allow_html=True)
        st.write(f"Starter suggestion: `{starter_entry.get('careers_url') or '-'}`")
        st.write(f"Confidence: `{starter_entry.get('confidence') or 'low'}`")
        st.write(f"Notes: {starter_entry.get('notes') or '-'}")
        st.markdown("</div>", unsafe_allow_html=True)

    with st.form(f"company_url_form_{selected_company_name}"):
        careers_url = st.text_input(
            "Careers URL",
            value=selected_company.get("careers_url")
            or starter_entry.get("careers_url")
            or "",
            placeholder="https://company.example/careers",
        )
        st.write(f"ATS hint: `{selected_company.get('ats_hint') or '-'}`")
        st.write(f"Website category: `{selected_company.get('website_category') or '-'}`")
        submitted = st.form_submit_button("Save URL and reclassify", use_container_width=True)

    if submitted:
        classification = classifier_api["classify_source"](
            {
                **selected_company,
                "careers_url": careers_url.strip() or None,
                "source_name": selected_company.get("website_category") or selected_company["name"],
            }
        )
        storage_api["update_company_source"](
            connection,
            company_name=selected_company_name,
            careers_url=careers_url.strip() or None,
            source_mode=classification.source_mode,
            source_name=classification.source_name,
        )
        classifier_api["update_company_record_in_yaml"](
            COMPANIES_CONFIG_PATH,
            company_name=selected_company_name,
            updates={
                "careers_url": careers_url.strip() or None,
                "source_mode": classification.source_mode,
            },
        )
        st.session_state["missing_urls_feedback"] = {
            "company_name": selected_company_name,
            "source_mode": classification.source_mode,
            "reasons": classification.reasons,
        }
        st.rerun()


def render_intervention_queue_tab(connection: Any) -> None:
    """Render the human intervention queue."""

    storage_api = get_storage_api()
    companies = {company["name"]: company for company in storage_api["get_companies"](connection)}
    interventions = storage_api["get_intervention_queue"](connection)

    render_section_heading("Intervention Queue")
    st.caption("Pause on blockers, keep a human in the loop, and avoid unsafe automation.")

    if not interventions:
        st.success("No interventions are pending right now.")
        return

    rows = [
        {
            "ID": item["id"],
            "Company": item.get("company_name") or "-",
            "Source URL": item.get("source_url") or "-",
            "Reason": item.get("reason") or "-",
            "Detected At": format_timestamp(item.get("detected_at")),
            "Action Required": item.get("action_required") or "-",
            "Status": item.get("status") or "pending",
        }
        for item in interventions
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)

    selected_intervention_id = st.selectbox(
        "Review intervention",
        options=[item["id"] for item in interventions],
        format_func=lambda intervention_id: next(
            (
                f"{item.get('company_name') or 'Unknown company'} | "
                f"{item.get('reason') or 'Unknown reason'} | "
                f"{item.get('status') or 'pending'}"
            )
            for item in interventions
            if item["id"] == intervention_id
        ),
        key="intervention_selector",
    )
    selected_intervention = next(
        item for item in interventions if item["id"] == selected_intervention_id
    )

    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
    st.write(f"Company: `{selected_intervention.get('company_name') or '-'}`")
    st.write(f"Reason: `{selected_intervention.get('reason') or '-'}`")
    st.write(f"Detected at: `{format_timestamp(selected_intervention.get('detected_at'))}`")
    st.write(f"Action required: {selected_intervention.get('action_required') or '-'}")
    st.write(f"Status: `{selected_intervention.get('status') or 'pending'}`")
    if selected_intervention.get("notes"):
        st.write("Notes")
        st.write(selected_intervention["notes"])

    url = selected_intervention.get("source_url")
    if url:
        st.link_button("Open URL in browser", url, use_container_width=True)

    note_text = st.text_area(
        "Add notes",
        key=f"intervention_note_{selected_intervention_id}",
        placeholder="Capture what you observed or what should happen next.",
    )
    if st.button(
        "Save notes",
        key=f"save_intervention_note_{selected_intervention_id}",
        use_container_width=True,
    ):
        if note_text.strip():
            storage_api["append_intervention_notes"](
                connection,
                selected_intervention_id,
                note_text.strip(),
            )
            st.rerun()
        else:
            st.warning("Enter notes before saving.")

    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button(
            "Mark resolved",
            key=f"resolve_intervention_{selected_intervention_id}",
            use_container_width=True,
        ):
            storage_api["update_intervention_status"](
                connection,
                selected_intervention_id,
                "resolved",
            )
            st.rerun()
    with action_col2:
        if st.button(
            "Mark manual-only",
            key=f"manual_only_intervention_{selected_intervention_id}",
            use_container_width=True,
        ):
            company_name = selected_intervention.get("company_name")
            if company_name and company_name in companies:
                storage_api["update_company_source"](
                    connection,
                    company_name=company_name,
                    careers_url=selected_intervention.get("source_url")
                    or companies[company_name].get("careers_url"),
                    source_mode="manual_only",
                )
            storage_api["update_intervention_status"](
                connection,
                selected_intervention_id,
                "manual_only",
            )
            st.rerun()
    with action_col3:
        if st.button(
            "Skip source",
            key=f"skip_intervention_{selected_intervention_id}",
            use_container_width=True,
        ):
            storage_api["update_intervention_status"](
                connection,
                selected_intervention_id,
                "skipped",
            )
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_manual_job_entry_tab(connection: Any) -> None:
    """Render the manual job entry workflow."""

    storage_api = get_storage_api()
    dashboard_api = get_dashboard_api()
    companies = storage_api["get_companies"](connection)
    feedback = st.session_state.pop("manual_job_feedback", None)

    render_section_heading("Manual Job Entry")
    st.caption(
        "Add a job manually for manual-only sources such as LinkedIn, Indeed, "
        "or difficult career pages."
    )

    if feedback:
        st.success(
            f"Saved manual job with score `{feedback['match_score']}` and "
            f"status `{feedback['status']}`."
        )
        st.write(f"Match reasons: {format_list_value(feedback.get('match_reasons'))}")
        st.write(f"Risk flags: {format_list_value(feedback.get('risk_flags'))}")

    if not companies:
        st.warning("Load companies into the watchlist before adding manual jobs.")
        return

    with st.form("manual_job_entry_form"):
        company_name = st.selectbox(
            "Company",
            options=[company["name"] for company in companies],
            key="manual_job_company",
        )
        title = st.text_input("Job title", placeholder="Cloud Engineer")
        location = st.text_input("Location", placeholder="Toronto, Ontario, Canada")
        job_url = st.text_input("Job URL", placeholder="https://example.com/jobs/123")
        apply_url = st.text_input(
            "Apply URL (optional)",
            placeholder="https://example.com/jobs/123/apply",
        )
        source_name = st.text_input("Source name", placeholder="LinkedIn")
        source_mode = st.selectbox(
            "Source mode",
            options=[
                "manual_only",
                "browser_allowed",
                "human_in_loop",
                "api_allowed",
                "needs_url",
                "avoid",
            ],
            index=0,
            key="manual_job_source_mode",
        )
        description = st.text_area(
            "Description / notes (optional)",
            placeholder="Paste the job summary, notes, or keywords here.",
        )
        status = st.selectbox(
            "Status",
            options=["new", "saved", "rejected", "reviewed", "needs_manual_review"],
            index=0,
            key="manual_job_status",
        )
        submitted = st.form_submit_button("Score and save manual job", use_container_width=True)

    if not submitted:
        return

    if not title.strip() or not job_url.strip() or not source_name.strip():
        st.error("Company, job title, job URL, and source name are required.")
        return

    saved = dashboard_api["score_and_save_manual_job"](
        connection,
        {
            "company_name": company_name,
            "title": title,
            "location": location,
            "job_url": job_url,
            "apply_url": apply_url,
            "source_name": source_name,
            "source_mode": source_mode,
            "description": description,
            "status": status,
        },
    )
    st.session_state["manual_job_feedback"] = saved
    st.rerun()


def get_export_files() -> list[Path]:
    """Return export artifacts sorted by most recent first."""

    if not EXPORTS_DIR.exists():
        return []
    return sorted(
        [path for path in EXPORTS_DIR.iterdir() if path.is_file() and path.name != ".gitkeep"],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def render_exports_tab() -> None:
    """Render export artifacts and previews."""

    export_files = get_export_files()

    render_section_heading("Exports")
    st.caption("Review generated reports and CSV artifacts from local runs.")

    if not export_files:
        st.info("No export files are available yet.")
        return

    rows = [
        {
            "File": path.name,
            "Type": path.suffix.lstrip(".").upper() or "File",
            "Modified": format_timestamp(path.stat().st_mtime_ns // 1_000_000_000),
            "Size (KB)": round(path.stat().st_size / 1024, 1),
        }
        for path in export_files
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)

    selected_export_name = st.selectbox(
        "Preview export",
        options=[path.name for path in export_files],
        key="export_selector",
    )
    selected_export = next(path for path in export_files if path.name == selected_export_name)

    st.download_button(
        "Download selected export",
        data=selected_export.read_bytes(),
        file_name=selected_export.name,
        mime="text/plain" if selected_export.suffix == ".md" else "text/csv",
        use_container_width=True,
    )

    if selected_export.suffix.lower() == ".md":
        st.markdown(selected_export.read_text(encoding="utf-8"))
        return

    preview_lines = selected_export.read_text(encoding="utf-8").splitlines()
    st.code("\n".join(preview_lines[:25]), language="csv")


def render_daily_summary_tab(connection: Any) -> None:
    """Render top-level summary metrics and recent artifacts."""

    storage_api = get_storage_api()
    overview = storage_api["get_dashboard_overview"](connection)
    jobs = storage_api["get_jobs"](connection)
    interventions = storage_api["get_intervention_queue"](connection)
    export_files = get_export_files()

    render_section_heading("Daily Summary")
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    with metric_col1:
        st.metric("Total Companies", overview["total_companies"])
    with metric_col2:
        st.metric("Ready To Search", overview["companies_ready_to_search"])
    with metric_col3:
        st.metric("Missing URLs", overview["companies_missing_url"])
    with metric_col4:
        st.metric("Jobs Found", overview["jobs_found"])
    with metric_col5:
        st.metric("Pending Interventions", overview["interventions_pending"])

    top_jobs = jobs[:8]
    summary_col1, summary_col2 = st.columns([1.4, 1])
    with summary_col1:
        st.write("Top matched jobs")
        if top_jobs:
            st.dataframe(
                prepare_jobs_table_rows(top_jobs),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No jobs have been collected yet.")
    with summary_col2:
        st.write("Recent workflow notes")
        if interventions:
            st.write(f"{len(interventions)} interventions need review.")
            newest = interventions[0]
            recent_summary = (
                f"{newest.get('company_name') or '-'} | "
                f"{newest.get('reason') or '-'} | "
                f"{format_timestamp(newest.get('detected_at'))}"
            )
            st.write(
                f"Most recent: `{recent_summary}`"
            )
        else:
            st.success("No interventions are currently blocking work.")

        if export_files:
            latest = export_files[0]
            st.write(f"Latest export: `{latest.name}`")
        else:
            st.caption("No report or CSV exports yet.")


def main() -> None:
    """Run the Streamlit app."""

    render_styles()
    connection = get_connection()

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">Job Discovery Browser Co-Pilot</div>
            <p class="hero-copy">
                Human-in-the-loop job discovery for Canadian banks and IT consulting companies.
                Keep the workflow visible, safe, and ready for manual review.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sections = [
        "Daily Summary",
        "Jobs Found",
        "Saved Jobs",
        "Company Watchlist",
        "Missing URLs",
        "Manual Job Entry",
        "Intervention Queue",
        "Exports",
    ]
    selected_section = st.selectbox(
        "Dashboard section",
        options=sections,
        index=0,
    )

    if selected_section == "Daily Summary":
        render_daily_summary_tab(connection)
    elif selected_section == "Jobs Found":
        render_jobs_tab(connection)
    elif selected_section == "Saved Jobs":
        render_saved_jobs_tab(connection)
    elif selected_section == "Company Watchlist":
        render_company_watchlist_tab(connection)
    elif selected_section == "Missing URLs":
        render_missing_urls_tab(connection)
    elif selected_section == "Manual Job Entry":
        render_manual_job_entry_tab(connection)
    elif selected_section == "Intervention Queue":
        render_intervention_queue_tab(connection)
    else:
        render_exports_tab()


if __name__ == "__main__":
    main()
