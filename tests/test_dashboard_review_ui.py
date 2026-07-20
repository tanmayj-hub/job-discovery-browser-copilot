from __future__ import annotations

from pathlib import Path

from dashboard.app import (
    DASHBOARD_PRIMARY_TABS,
    _filter_current_review_rows,
    display_change_type,
    display_decision,
    display_relevance_tier,
    display_review_state,
    stable_review_widget_key,
    truncate_text,
)


def test_dashboard_defaults_to_jobs_with_source_verified_view_available() -> None:
    assert DASHBOARD_PRIMARY_TABS[0] == "Jobs"
    assert "All Source-Verified Jobs" in DASHBOARD_PRIMARY_TABS


def test_dashboard_uses_human_readable_review_labels() -> None:
    assert display_relevance_tier("core_target_fit") == "Core technical fit"
    assert (
        display_relevance_tier("adjacent_customer_facing_technical_fit") == "Adjacent technical fit"
    )
    assert display_decision("already_applied") == "Already applied"
    assert display_change_type("Existing") == "Still active"
    assert display_review_state("", "useful") == "Previously reviewed"


def test_dashboard_truncation_keeps_long_titles_readable() -> None:
    value = "Cloud Platform Engineer " * 8
    display_value = truncate_text(value, limit=52)

    assert display_value.endswith("...")
    assert len(display_value) <= 52


def test_review_selection_resets_cleanly_after_filters_change() -> None:
    rows = [
        {
            "company": "RBC",
            "title": "Cloud Engineer",
            "location": "Toronto, ON, Canada",
            "relevance_tier": "core_target_fit",
            "score": "80",
            "user_decision": "useful",
            "review_state": "Previously reviewed",
        },
        {
            "company": "Scotiabank",
            "title": "Solution Engineer",
            "location": "Scarborough, ON, Canada",
            "relevance_tier": "adjacent_customer_facing_technical_fit",
            "score": "64",
            "user_decision": "",
            "review_state": "Newly selected after calibration",
        },
    ]

    filtered = _filter_current_review_rows(
        rows,
        selected_company="All",
        selected_tier="All",
        minimum_score=0,
        selected_decision="Review needed",
        selected_location="All",
        keyword="",
    )

    assert [row["title"] for row in filtered] == ["Solution Engineer"]
    assert stable_review_widget_key("select", "https://jobs.example.com/1") == (
        stable_review_widget_key("select", "https://jobs.example.com/1")
    )


def test_all_verified_jobs_is_not_rendered_twice_by_workspace_default() -> None:
    dashboard_source = Path("src/dashboard/app.py").read_text(encoding="utf-8")
    main_source = dashboard_source.split("def main()", maxsplit=1)[1]

    assert main_source.count("render_jobs_tab(connection)") == 1


def test_review_needed_is_the_first_load_filter() -> None:
    dashboard_source = Path("src/dashboard/app.py").read_text(encoding="utf-8")
    review_options = dashboard_source.split("decisions = [", maxsplit=1)[1].split(
        "]", maxsplit=1
    )[0]

    assert review_options.index('"Review needed"') < review_options.index('"All"')


def test_review_workspace_keeps_scrolling_within_the_opportunity_list() -> None:
    dashboard_source = Path("src/dashboard/app.py").read_text(encoding="utf-8")
    workspace_source = dashboard_source.split(
        "def render_current_slice_review", maxsplit=1
    )[1].split("def render_current_slice_run_details", maxsplit=1)[0]

    assert 'with st.expander("Filters", expanded=False):' in workspace_source
    assert "with st.container(height=330, border=False):" in workspace_source
    detail_source = workspace_source.split("with detail_column:", maxsplit=1)[1]
    assert "with st.container(height=" not in detail_source
    assert 'st.button("Review this job", use_container_width=True)' in detail_source
    assert "def render_current_job_review_dialog" in dashboard_source
