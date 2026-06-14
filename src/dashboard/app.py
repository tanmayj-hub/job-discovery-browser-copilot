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
VERIFIED_COMPANIES_CONFIG_PATH = BASE_DIR / "config" / "verified_companies.yaml"
STARTER_CAREER_URLS_PATH = BASE_DIR / "config" / "starter_career_urls.yaml"
DATABASE_PATH = BASE_DIR / "data" / "job_discovery.db"
EXPORTS_DIR = BASE_DIR / "data" / "exports"
REVIEW_EXPORT_PATH = EXPORTS_DIR / "review" / "saved-jobs-review.csv"
PENDING_APPLICATION_STATUSES = ("new", "saved", "reviewed", "needs_manual_review")
JOB_STATUS_OPTIONS = [
    "new",
    "saved",
    "applied",
    "rejected",
    "reviewed",
    "needs_manual_review",
]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def get_storage_api() -> dict[str, Any]:
    """Load storage helpers after the src path is available."""

    from storage import (
        append_intervention_notes,
        get_companies,
        get_companies_needing_url,
        get_dashboard_overview,
        get_intervention_history,
        get_intervention_queue,
        get_jobs,
        get_source_status_rows,
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
        "get_intervention_history": get_intervention_history,
        "get_intervention_queue": get_intervention_queue,
        "get_jobs": get_jobs,
        "get_source_status_rows": get_source_status_rows,
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
    from dashboard.source_status import filter_source_status_items, prepare_source_status_rows

    return {
        "filter_source_status_items": filter_source_status_items,
        "prepare_source_status_rows": prepare_source_status_rows,
        "score_and_save_manual_job": score_and_save_manual_job,
    }


def get_review_api() -> dict[str, Any]:
    """Load saved-job review helpers after the src path is available."""

    from review.saved_job_review import (
        build_saved_jobs_review_dashboard_rows,
        collect_review_export_companies,
        export_saved_jobs_review,
        load_review_export_preview,
    )

    return {
        "build_saved_jobs_review_dashboard_rows": build_saved_jobs_review_dashboard_rows,
        "collect_review_export_companies": collect_review_export_companies,
        "export_saved_jobs_review": export_saved_jobs_review,
        "load_review_export_preview": load_review_export_preview,
    }


def get_verified_api() -> dict[str, Any]:
    """Load verified-company helpers after the src path is available."""

    from dashboard.verified_view import (
        derive_last_run_timestamp,
        filter_jobs_to_latest_verified_run,
        filter_jobs_to_verified_companies,
        filter_source_rows_to_verified_companies,
    )
    from verified_companies import (
        get_usable_verified_company_names,
        load_verified_company_records,
    )

    return {
        "derive_last_run_timestamp": derive_last_run_timestamp,
        "filter_jobs_to_latest_verified_run": filter_jobs_to_latest_verified_run,
        "filter_jobs_to_verified_companies": filter_jobs_to_verified_companies,
        "filter_source_rows_to_verified_companies": filter_source_rows_to_verified_companies,
        "get_usable_verified_company_names": get_usable_verified_company_names,
        "load_verified_company_records": load_verified_company_records,
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
        div[data-baseweb="select"] > div,
        div[data-testid="stTextInputRootElement"] > div,
        div[data-testid="stTextArea"] textarea {
            border-radius: 14px;
        }
        div[data-testid="stButton"] button,
        div[data-testid="stLinkButton"] a {
            border-radius: 14px;
            border: 1px solid #cfd9ca;
            min-height: 2.75rem;
            font-weight: 600;
        }
        button[kind="primary"] {
            background: linear-gradient(135deg, #315942 0%, #44785a 100%);
            color: white;
        }
        div[data-baseweb="tab-list"] {
            gap: 0.35rem;
        }
        button[data-baseweb="tab"] {
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid #d7e0d3;
            padding: 0.45rem 1rem;
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
                "Relevance Tier": job.get("relevance_tier") or "-",
                "Score": job.get("match_score", 0),
                "Status": job.get("status") or "new",
                "Source Mode": job.get("source_mode") or "-",
                "Apply URL": job.get("apply_url") or job.get("job_url") or None,
                "Job URL": job.get("job_url") or None,
                "ATS Type": job.get("ats_type") or "-",
                "Board Slug": job.get("board_slug") or "-",
                "External ID": job.get("external_job_id") or "-",
                "First Seen": format_timestamp(job.get("first_seen_at") or job.get("first_seen")),
                "Last Seen": format_timestamp(job.get("last_seen_at") or job.get("last_seen")),
                "Match Reasons": format_list_value(job.get("match_reasons")),
                "Risk Flags": format_list_value(job.get("risk_flags")),
            }
        )
    return rows


def get_queue_label(status: object) -> str:
    """Map job statuses into application workflow queues."""

    normalized = str(status or "new").strip()
    if normalized == "applied":
        return "Applied"
    if normalized == "rejected":
        return "Rejected"
    return "Pending"


def prepare_jobs_column_config() -> dict[str, Any]:
    """Return consistent Streamlit column configuration for job tables."""

    return {
        "ID": st.column_config.NumberColumn("ID", width="small"),
        "Score": st.column_config.NumberColumn("Score", width="small"),
        "Apply URL": st.column_config.LinkColumn("Apply", width="small", display_text="Apply"),
        "Job URL": st.column_config.LinkColumn("Posting", width="small", display_text="Open"),
        "Match Reasons": st.column_config.TextColumn("Match Reasons", width="large"),
        "Risk Flags": st.column_config.TextColumn("Risk Flags", width="medium"),
    }


def filter_jobs_to_latest_verified_scope(
    jobs: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    verified_company_names: set[str],
    *,
    verified_only: bool,
    latest_verified_run_only: bool,
) -> list[dict[str, Any]]:
    """Apply verified-company scope filters before per-table filters."""

    scoped_jobs = jobs
    verified_rows = source_rows
    if verified_only:
        verified_api = get_verified_api()
        scoped_jobs = verified_api["filter_jobs_to_verified_companies"](
            scoped_jobs,
            verified_company_names,
        )
        verified_rows = verified_api["filter_source_rows_to_verified_companies"](
            source_rows,
            verified_company_names,
        )
    if verified_only and latest_verified_run_only:
        verified_api = get_verified_api()
        scoped_jobs = verified_api["filter_jobs_to_latest_verified_run"](
            scoped_jobs,
            verified_rows,
            verified_company_names,
        )
    return scoped_jobs


def filter_jobs(
    jobs: list[dict[str, Any]],
    *,
    verified_only: bool,
    verified_company_names: set[str],
    selected_company: str,
    selected_sector: str,
    selected_tier: str,
    min_score: int,
    selected_status: str,
) -> list[dict[str, Any]]:
    """Apply user-selected dashboard filters to jobs."""

    filtered: list[dict[str, Any]] = []
    for job in jobs:
        company_name = str(job.get("company_name") or "")
        if verified_only and company_name not in verified_company_names:
            continue
        if selected_company != "All" and job["company_name"] != selected_company:
            continue
        if selected_sector != "All" and (job.get("sector") or "-") != selected_sector:
            continue
        if selected_tier != "All" and (job.get("relevance_tier") or "-") != selected_tier:
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
        st.write(
            f"Status: `{job.get('status', 'new')}`  |  "
            f"Queue: `{get_queue_label(job.get('status'))}`"
        )

    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        st.write(
            f"First seen: `{format_timestamp(job.get('first_seen_at') or job.get('first_seen'))}`"
        )
    with info_col2:
        st.write(
            f"Last seen: `{format_timestamp(job.get('last_seen_at') or job.get('last_seen'))}`"
        )
    with info_col3:
        st.write(f"Sector: `{job.get('sector') or '-'}`")

    meta_col1, meta_col2, meta_col3 = st.columns(3)
    with meta_col1:
        st.write(f"ATS type: `{job.get('ats_type') or '-'}`")
    with meta_col2:
        st.write(f"Board slug: `{job.get('board_slug') or '-'}`")
    with meta_col3:
        st.write(f"External ID: `{job.get('external_job_id') or '-'}`")

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

    quick_col1, quick_col2, quick_col3 = st.columns(3)
    with quick_col1:
        if st.button(
            "Move to pending",
            key=f"{key_prefix}_pending_{job['id']}",
            use_container_width=True,
        ):
            storage_api["update_job_status"](connection, job["id"], "new")
            st.rerun()
    with quick_col2:
        if st.button(
            "Mark applied",
            key=f"{key_prefix}_applied_{job['id']}",
            use_container_width=True,
        ):
            storage_api["update_job_status"](connection, job["id"], "applied")
            st.rerun()
    with quick_col3:
        if st.button(
            "Move to rejected",
            key=f"{key_prefix}_reject_{job['id']}",
            use_container_width=True,
        ):
            storage_api["update_job_status"](connection, job["id"], "rejected")
            st.rerun()

    status_col1, status_col2 = st.columns([1.6, 1])
    current_status = str(job.get("status") or "new")
    if current_status not in JOB_STATUS_OPTIONS:
        current_status = "new"
    with status_col1:
        selected_status = st.selectbox(
            "Update status",
            options=JOB_STATUS_OPTIONS,
            index=JOB_STATUS_OPTIONS.index(current_status),
            key=f"{key_prefix}_status_select_{job['id']}",
        )
    with status_col2:
        if st.button(
            "Apply status change",
            key=f"{key_prefix}_status_apply_{job['id']}",
            use_container_width=True,
        ):
            storage_api["update_job_status"](connection, job["id"], selected_status)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_jobs_tab(connection: Any) -> None:
    """Render the Jobs Found tab."""

    storage_api = get_storage_api()
    verified_api = get_verified_api()
    jobs = storage_api["get_jobs"](connection)
    source_rows = storage_api["get_source_status_rows"](connection)
    verified_company_names = set(
        verified_api["get_usable_verified_company_names"](VERIFIED_COMPANIES_CONFIG_PATH)
    )

    render_section_heading("Jobs Found")
    st.caption(
        "Filter discovered jobs, review fit signals, and update status. "
        "The default view stays anchored to the latest verified run so stale history "
        "does not mix with the current Canada-scoped queue."
    )

    if not jobs:
        st.info(
            "No jobs are in the database yet. "
            "Run a collector or daily workflow to populate this view."
        )
        return

    verified_only = st.checkbox(
        "Verified companies only",
        value=True,
        help="Default to usable verified companies for the daily MVP workflow.",
    )
    latest_verified_run_only = st.checkbox(
        "Latest verified run only",
        value=True,
        disabled=not verified_only,
        help=(
            "Hide stale historical rows so this view stays aligned to the most recent "
            "verified run."
        ),
    )
    scoped_jobs = filter_jobs_to_latest_verified_scope(
        jobs,
        source_rows,
        verified_company_names,
        verified_only=verified_only,
        latest_verified_run_only=latest_verified_run_only,
    )
    company_pool = scoped_jobs
    companies = ["All", *sorted({job["company_name"] for job in company_pool})]
    sectors = ["All", *sorted({job.get("sector") or "-" for job in company_pool})]
    tiers = ["All", *sorted({job.get("relevance_tier") or "-" for job in company_pool})]
    statuses = ["All", *sorted({job.get("status", "new") for job in company_pool})]

    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns(5)
    with filter_col1:
        selected_company = st.selectbox("Company", companies, key="jobs_company_filter")
    with filter_col2:
        selected_sector = st.selectbox("Sector", sectors, key="jobs_sector_filter")
    with filter_col3:
        selected_tier = st.selectbox("Relevance tier", tiers, key="jobs_tier_filter")
    with filter_col4:
        min_score = st.slider("Minimum score", min_value=0, max_value=100, value=0, step=5)
    with filter_col5:
        selected_status = st.selectbox("Status", statuses, key="jobs_status_filter")

    filtered_jobs = filter_jobs(
        scoped_jobs,
        verified_only=verified_only,
        verified_company_names=verified_company_names,
        selected_company=selected_company,
        selected_sector=selected_sector,
        selected_tier=selected_tier,
        min_score=min_score,
        selected_status=selected_status,
    )
    st.caption(f"{len(filtered_jobs)} jobs match the current filters.")
    st.dataframe(
        prepare_jobs_table_rows(filtered_jobs),
        hide_index=True,
        use_container_width=True,
        column_config=prepare_jobs_column_config(),
    )

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


def render_job_queue_panel(
    connection: Any,
    jobs: list[dict[str, Any]],
    *,
    empty_message: str,
    selector_label: str,
    key_prefix: str,
) -> None:
    """Render one queue panel inside the application tracker."""

    st.caption(f"{len(jobs)} jobs in this queue.")
    if not jobs:
        st.info(empty_message)
        return

    st.dataframe(
        prepare_jobs_table_rows(jobs),
        hide_index=True,
        use_container_width=True,
        column_config=prepare_jobs_column_config(),
    )
    selected_job_id = st.selectbox(
        selector_label,
        options=[job["id"] for job in jobs],
        format_func=lambda job_id: job_option_label(
            next(job for job in jobs if job["id"] == job_id),
        ),
        key=f"{key_prefix}_selector",
    )
    selected_job = next(job for job in jobs if job["id"] == selected_job_id)
    render_job_details(connection, selected_job, key_prefix=key_prefix)


def render_application_tracker_tab(connection: Any) -> None:
    """Render the pending, applied, and rejected job workflow."""

    storage_api = get_storage_api()
    verified_api = get_verified_api()
    jobs = storage_api["get_jobs"](connection)
    source_rows = storage_api["get_source_status_rows"](connection)
    verified_company_names = set(
        verified_api["get_usable_verified_company_names"](VERIFIED_COMPANIES_CONFIG_PATH)
    )

    render_section_heading("Application Tracker")
    st.caption(
        "Work from one master pending queue, move finished applications to Applied, "
        "and keep jobs you do not want in Rejected."
    )

    if not jobs:
        st.info("No jobs are available yet.")
        return

    tracker_col1, tracker_col2 = st.columns(2)
    with tracker_col1:
        verified_only = st.checkbox(
            "Verified companies only",
            value=True,
            key="tracker_verified_only",
        )
    with tracker_col2:
        latest_verified_run_only = st.checkbox(
            "Latest verified run only",
            value=True,
            key="tracker_latest_verified_only",
            disabled=not verified_only,
            help="Use the latest verified run as the default application queue.",
        )

    scoped_jobs = filter_jobs_to_latest_verified_scope(
        jobs,
        source_rows,
        verified_company_names,
        verified_only=verified_only,
        latest_verified_run_only=latest_verified_run_only,
    )
    pending_jobs = [
        job
        for job in scoped_jobs
        if str(job.get("status") or "new") in PENDING_APPLICATION_STATUSES
    ]
    applied_jobs = [job for job in scoped_jobs if str(job.get("status") or "") == "applied"]
    rejected_jobs = [job for job in scoped_jobs if str(job.get("status") or "") == "rejected"]

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("Pending Applications", len(pending_jobs))
    with metric_col2:
        st.metric("Applied Jobs", len(applied_jobs))
    with metric_col3:
        st.metric("Rejected Jobs", len(rejected_jobs))

    pending_tab, applied_tab, rejected_tab = st.tabs(
        ["Pending Applications", "Applied Jobs", "Rejected Jobs"]
    )
    with pending_tab:
        render_job_queue_panel(
            connection,
            pending_jobs,
            empty_message="No pending jobs are waiting for application.",
            selector_label="Review pending job",
            key_prefix="pending_jobs",
        )
    with applied_tab:
        render_job_queue_panel(
            connection,
            applied_jobs,
            empty_message="No jobs are marked as applied yet.",
            selector_label="Review applied job",
            key_prefix="applied_jobs",
        )
    with rejected_tab:
        render_job_queue_panel(
            connection,
            rejected_jobs,
            empty_message="No jobs are in the rejected list yet.",
            selector_label="Review rejected job",
            key_prefix="rejected_jobs",
        )


def render_saved_job_review_tab(connection: Any) -> None:
    """Render the lightweight saved-job review workflow."""

    review_api = get_review_api()
    feedback = st.session_state.pop("saved_job_review_feedback", None)
    preview_rows = review_api["build_saved_jobs_review_dashboard_rows"](
        connection,
        verified_companies_path=VERIFIED_COMPANIES_CONFIG_PATH,
    )

    render_section_heading("Saved Job Review")
    st.caption(
        "Export the current verified saved-job queue to a simple CSV, then mark each row as "
        "`useful`, `maybe`, `not_useful`, `false_positive`, `already_applied`, or "
        "`saved_for_later`."
    )

    if feedback:
        st.success(
            f"Exported `{feedback['exported_rows']}` rows to `{feedback['output_path']}`."
        )

    action_col1, action_col2 = st.columns([1.2, 2])
    with action_col1:
        if st.button("Refresh review CSV", use_container_width=True):
            rows = review_api["export_saved_jobs_review"](
                connection,
                verified_companies_path=VERIFIED_COMPANIES_CONFIG_PATH,
                output_path=REVIEW_EXPORT_PATH,
            )
            st.session_state["saved_job_review_feedback"] = {
                "exported_rows": len(rows),
                "output_path": str(REVIEW_EXPORT_PATH),
            }
            st.rerun()
    with action_col2:
        st.caption(
            "Review file: "
            f"`{REVIEW_EXPORT_PATH}`"
        )

    if REVIEW_EXPORT_PATH.exists():
        st.download_button(
            "Download review CSV",
            data=REVIEW_EXPORT_PATH.read_bytes(),
            file_name=REVIEW_EXPORT_PATH.name,
            mime="text/csv",
            use_container_width=True,
        )

    if not preview_rows:
        st.info(
            "No verified saved-job snapshot is available yet. Run "
            "`python -m src.main daily-run --verified-only` first."
        )
        return

    companies_included = review_api["collect_review_export_companies"](
        [
            {
                "company": str(row.get("Company") or "").strip(),
            }
            for row in preview_rows
        ]
    )
    summary_col1, summary_col2 = st.columns([1, 2])
    with summary_col1:
        st.metric("Review Rows", len(preview_rows))
    with summary_col2:
        st.write("Companies included")
        st.write(", ".join(companies_included) if companies_included else "-")

    st.dataframe(
        preview_rows,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Job URL": st.column_config.LinkColumn(
                "Job URL",
                width="small",
                display_text="Open",
            ),
            "Match Reasons": st.column_config.TextColumn("Match Reasons", width="large"),
            "Risk Flags": st.column_config.TextColumn("Risk Flags", width="medium"),
        },
    )
    st.info(
        "Edit the CSV locally to fill `user_decision` and `user_notes`. Use only these "
        "decision values: `useful`, `maybe`, `not_useful`, `false_positive`, "
        "`already_applied`, `saved_for_later`."
    )


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


def render_source_readiness_tab(connection: Any) -> None:
    """Render source-level collector status, fallback, and readiness details."""

    storage_api = get_storage_api()
    dashboard_api = get_dashboard_api()
    source_rows = storage_api["get_source_status_rows"](connection)

    render_section_heading("Source Readiness")
    st.caption(
        "See which path each company source used, what happened during the latest run, "
        "and where manual follow-up is needed."
    )

    if not source_rows:
        st.info("No source status data is available yet.")
        return

    source_modes = ["All", *sorted({str(row.get("source_mode") or "-") for row in source_rows})]
    ats_types = ["All", *sorted({str(row.get("ats_type") or "-") for row in source_rows})]
    collectors = [
        "All",
        *sorted(
            {
                str(row.get("collector") or row.get("last_collector") or "-")
                for row in source_rows
            }
        ),
    ]
    statuses = [
        "All",
        *sorted(
            {
                str(row.get("status") or row.get("last_status") or "-")
                for row in source_rows
            }
        ),
    ]

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    filter_col4, filter_col5, filter_col6 = st.columns(3)
    with filter_col1:
        selected_source_mode = st.selectbox(
            "Source mode",
            source_modes,
            key="source_status_mode_filter",
        )
    with filter_col2:
        selected_ats_type = st.selectbox(
            "ATS type",
            ats_types,
            key="source_status_ats_filter",
        )
    with filter_col3:
        selected_collector = st.selectbox(
            "Collector",
            collectors,
            key="source_status_collector_filter",
        )
    with filter_col4:
        selected_status = st.selectbox(
            "Status",
            statuses,
            key="source_status_status_filter",
        )
    with filter_col5:
        selected_fallback = st.selectbox(
            "Fallback used",
            ["All", "Yes", "No"],
            key="source_status_fallback_filter",
        )
    with filter_col6:
        selected_intervention = st.selectbox(
            "Intervention required",
            ["All", "Yes", "No"],
            key="source_status_intervention_filter",
        )

    filtered_sources = dashboard_api["filter_source_status_items"](
        source_rows,
        selected_source_mode=selected_source_mode,
        selected_ats_type=selected_ats_type,
        selected_collector=selected_collector,
        selected_status=selected_status,
        selected_fallback=selected_fallback,
        selected_intervention=selected_intervention,
    )

    st.caption(f"{len(filtered_sources)} sources match the current filters.")
    st.dataframe(
        dashboard_api["prepare_source_status_rows"](filtered_sources),
        hide_index=True,
        use_container_width=True,
    )


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
    intervention_history = storage_api["get_intervention_history"](connection)

    render_section_heading("Intervention Queue")
    st.caption("Pause on blockers, keep a human in the loop, and avoid unsafe automation.")

    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric("Active Pending Sources", len(interventions))
    with metric_col2:
        st.metric("Resolved History", len(intervention_history))

    if not interventions:
        st.success("No interventions are pending right now.")
        if intervention_history:
            with st.expander("Resolved intervention history", expanded=False):
                history_rows = [
                    {
                        "ID": item["id"],
                        "Company": item.get("company_name") or "-",
                        "Reason": item.get("reason") or "-",
                        "Status": item.get("status") or "-",
                        "Resolved At": format_timestamp(item.get("resolved_at")),
                    }
                    for item in intervention_history
                ]
                st.dataframe(history_rows, hide_index=True, use_container_width=True)
        return

    rows = [
        {
            "ID": item["id"],
            "Company": item.get("company_name") or "-",
            "Source URL": item.get("source_url") or "-",
            "Reason": item.get("reason") or "-",
            "Occurrences": int(item.get("occurrence_count", 1) or 1),
            "Remediation": item.get("remediation_label") or "-",
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
    st.write(
        f"Occurrences: `{int(selected_intervention.get('occurrence_count', 1) or 1)}`"
    )
    st.write(f"Detected at: `{format_timestamp(selected_intervention.get('detected_at'))}`")
    st.write(f"Remediation: `{selected_intervention.get('remediation_label') or '-'}`")
    st.write(f"Suggested action: {selected_intervention.get('suggested_action') or '-'}")
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

    if intervention_history:
        with st.expander("Resolved intervention history", expanded=False):
            history_rows = [
                {
                    "ID": item["id"],
                    "Company": item.get("company_name") or "-",
                    "Source URL": item.get("source_url") or "-",
                    "Reason": item.get("reason") or "-",
                    "Remediation": item.get("remediation_label") or "-",
                    "Resolved At": format_timestamp(item.get("resolved_at")),
                    "Status": item.get("status") or "-",
                }
                for item in intervention_history
            ]
            st.dataframe(history_rows, hide_index=True, use_container_width=True)


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
            options=JOB_STATUS_OPTIONS,
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
    intervention_history = storage_api["get_intervention_history"](connection)
    source_rows = storage_api["get_source_status_rows"](connection)
    dashboard_api = get_dashboard_api()
    verified_api = get_verified_api()
    export_files = get_export_files()
    verified_records = verified_api["load_verified_company_records"](VERIFIED_COMPANIES_CONFIG_PATH)
    verified_company_names = set(
        verified_api["get_usable_verified_company_names"](VERIFIED_COMPANIES_CONFIG_PATH)
    )
    verified_jobs = verified_api["filter_jobs_to_verified_companies"](jobs, verified_company_names)
    verified_source_rows = verified_api["filter_source_rows_to_verified_companies"](
        source_rows,
        verified_company_names,
    )
    current_verified_jobs = verified_api["filter_jobs_to_latest_verified_run"](
        verified_jobs,
        verified_source_rows,
        verified_company_names,
    )
    pending_verified_jobs = [
        job
        for job in current_verified_jobs
        if str(job.get("status") or "new") in PENDING_APPLICATION_STATUSES
    ]
    applied_verified_jobs = [
        job for job in current_verified_jobs if str(job.get("status") or "") == "applied"
    ]
    rejected_verified_jobs = [
        job for job in current_verified_jobs if str(job.get("status") or "") == "rejected"
    ]
    last_run_timestamp = verified_api["derive_last_run_timestamp"](verified_source_rows)
    latest_inserted = sum(int(row.get("jobs_inserted", 0) or 0) for row in verified_source_rows)
    latest_updated = sum(int(row.get("jobs_updated", 0) or 0) for row in verified_source_rows)

    render_section_heading("Daily Summary")
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6 = st.columns(6)
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
    with metric_col6:
        st.metric("Resolved History", overview["interventions_resolved_history"])

    verified_metric_col1, verified_metric_col2, verified_metric_col3 = st.columns(3)
    verified_metric_col4, verified_metric_col5 = st.columns(2)
    with verified_metric_col1:
        verified_count = len(
            [item for item in verified_records if item.get("verified")]
        )
        st.metric("Verified Companies", verified_count)
    with verified_metric_col2:
        st.metric("Current Verified Jobs", len(current_verified_jobs))
    with verified_metric_col3:
        st.metric("Pending Queue", len(pending_verified_jobs))
    with verified_metric_col4:
        st.metric("Applied Queue", len(applied_verified_jobs))
    with verified_metric_col5:
        st.metric("Rejected Queue", len(rejected_verified_jobs))

    verified_metric_col6, verified_metric_col7, verified_metric_col8 = st.columns(3)
    with verified_metric_col6:
        st.metric("New Jobs (Latest Run)", latest_inserted)
    with verified_metric_col7:
        st.metric("Updated Jobs (Latest Run)", latest_updated)
    with verified_metric_col8:
        st.metric("Last Run", last_run_timestamp or "-")

    source_metric_col1, source_metric_col2, source_metric_col3, source_metric_col4 = st.columns(4)
    source_metric_col5, source_metric_col6, source_metric_col7, source_metric_col8 = st.columns(4)
    with source_metric_col1:
        st.metric("Total Sources Checked", overview["total_sources_checked"])
    with source_metric_col2:
        st.metric("Jobs Discovered", overview["jobs_discovered_latest"])
    with source_metric_col3:
        st.metric("Jobs Relevant", overview["jobs_relevant_latest"])
    with source_metric_col4:
        st.metric("Jobs Saved", overview["jobs_saved_latest"])
    with source_metric_col5:
        st.metric("API Sources Used", overview["api_sources_used"])
    with source_metric_col6:
        st.metric("Browser Fallbacks", overview["browser_fallbacks"])
    with source_metric_col7:
        st.metric("Interventions Required", overview["interventions_required_sources"])
    with source_metric_col8:
        st.metric("Errors", overview["source_errors"])

    top_jobs = current_verified_jobs[:8] or jobs[:8]
    summary_col1, summary_col2 = st.columns([1.4, 1])
    with summary_col1:
        st.write("Top matched jobs")
        if top_jobs:
            st.dataframe(
                prepare_jobs_table_rows(top_jobs),
                hide_index=True,
                use_container_width=True,
                column_config=prepare_jobs_column_config(),
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
            if intervention_history:
                st.caption(
                    f"{len(intervention_history)} resolved/manual history rows remain "
                    "available for review."
                )

        if export_files:
            latest = export_files[0]
            st.write(f"Latest export: `{latest.name}`")
        else:
            st.caption("No report or CSV exports yet.")

    if verified_source_rows:
        st.write("Verified company source health")
        verified_health_rows = [
            {
                "Company": row.get("company_name") or "-",
                "Source URL": row.get("source_url") or "-",
                "Status": row.get("status") or "-",
                "Discovered": int(row.get("jobs_discovered", 0) or 0),
                "Relevant Saved": int(row.get("jobs_saved", 0) or 0),
                "Intervention": row.get("latest_pending_reason") or "-",
            }
            for row in verified_source_rows
        ]
        st.dataframe(verified_health_rows, hide_index=True, use_container_width=True)

    if source_rows:
        st.write("Latest source outcomes")
        st.dataframe(
            dashboard_api["prepare_source_status_rows"](source_rows[:8]),
            hide_index=True,
            use_container_width=True,
        )


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
        "Source Readiness",
        "Jobs Found",
        "Saved Job Review",
        "Application Tracker",
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
    elif selected_section == "Source Readiness":
        render_source_readiness_tab(connection)
    elif selected_section == "Jobs Found":
        render_jobs_tab(connection)
    elif selected_section == "Saved Job Review":
        render_saved_job_review_tab(connection)
    elif selected_section == "Application Tracker":
        render_application_tracker_tab(connection)
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
