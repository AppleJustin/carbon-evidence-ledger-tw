"""Issues & Actions — compact horizontal summary and actionable to-do list."""

from __future__ import annotations

import streamlit as st

from carbon_ledger.ui.charts import render_issue_gap_bars
from carbon_ledger.ui.components import (
    inject_design_system,
    render_empty_state,
    render_page_header,
    render_page_help,
    render_saas_kpi_row,
    render_section_header,
    render_viz_panel_end,
    render_viz_panel_start,
)
from carbon_ledger.ui.formatting import format_int
from carbon_ledger.ui.i18n import t
from carbon_ledger.ui.motion import mark_chart_reveal
from carbon_ledger.ui.state import get_current_result, get_language
from carbon_ledger.ui.view_models import issues_table

inject_design_system()
lang = get_language(st.session_state)
result = get_current_result(st.session_state)

render_page_header(t("ev.title", lang), t("ev.subtitle", lang))
render_section_header(t("iss.title", lang), t("iss.subtitle", lang))
render_page_help(t("iss.help", lang))

if result is None:
    render_empty_state(
        t("empty.no_analysis_title", lang),
        t("empty.no_analysis_body", lang),
    )
    st.stop()

table = issues_table(result, lang)
open_issues = int(len(table))
critical = int((table["severity_code"] == "critical").sum()) if open_issues else 0
high = int((table["severity_code"] == "high").sum()) if open_issues else 0
affected = int(table["record_id"].nunique()) if open_issues else 0

# Horizontal compact cards — viewport stagger + one-time count-up.
render_saas_kpi_row(
    [
        {
            "label": t("iss.metric_open", lang),
            "value": format_int(open_issues),
            "accent": "amber",
            "icon": "!",
            "count": {
                "target": float(open_issues),
                "decimals": 0,
                "final": format_int(open_issues),
            },
        },
        {
            "label": t("iss.metric_critical", lang),
            "value": format_int(critical),
            "accent": "coral",
            "icon": "✕",
            "count": {
                "target": float(critical),
                "decimals": 0,
                "final": format_int(critical),
            },
        },
        {
            "label": t("iss.metric_high", lang),
            "value": format_int(high),
            "accent": "amber",
            "icon": "↑",
            "count": {
                "target": float(high),
                "decimals": 0,
                "final": format_int(high),
            },
        },
        {
            "label": t("iss.metric_affected", lang),
            "value": format_int(affected),
            "accent": "slate",
            "icon": "▣",
            "count": {
                "target": float(affected),
                "decimals": 0,
                "final": format_int(affected),
            },
        },
    ],
    variant="compact",
    reveal_on_scroll=True,
    scroll_key="issues-kpi",
)

if open_issues == 0:
    render_empty_state(t("iss.empty", lang), t("iss.empty", lang))
    st.stop()

render_viz_panel_start(
    t("iss.gap_title", lang),
    scroll_key="issues-gap-panel",
    chart_kind="bars",
)
mark_chart_reveal("issues-gap", chart="bars")
render_issue_gap_bars(result, lang)
render_viz_panel_end()

st.write("")
filter_cols = st.columns(3)
severities = [t("act.filter_all", lang)] + sorted(
    table["Priority"].dropna().unique().tolist()
)
issue_types = [t("act.filter_all", lang)] + sorted(
    table["issue_code"].dropna().unique().tolist()
)
activities = [t("act.filter_all", lang)] + sorted(
    table["Activity"].dropna().unique().tolist()
)
with filter_cols[0]:
    severity_filter = st.selectbox(t("iss.filter_severity", lang), severities)
with filter_cols[1]:
    issue_filter = st.selectbox(t("iss.filter_type", lang), issue_types)
with filter_cols[2]:
    activity_filter = st.selectbox(t("iss.filter_activity", lang), activities)

filtered = table.copy()
all_label = t("act.filter_all", lang)
if severity_filter != all_label:
    filtered = filtered[filtered["Priority"] == severity_filter]
if issue_filter != all_label:
    filtered = filtered[filtered["issue_code"] == issue_filter]
if activity_filter != all_label:
    filtered = filtered[filtered["Activity"] == activity_filter]

if filtered.empty:
    render_empty_state(t("iss.empty", lang), t("iss.help", lang))
    st.stop()

render_section_header(
    t("iss.todo_title", lang),
    t("iss.todo_help", lang),
    scroll_key="issues-todo",
)
st.markdown(
    (
        '<div data-cel-reveal="section" data-cel-key="issues-table" '
        'data-cel-animation-type="section"></div>'
    ),
    unsafe_allow_html=True,
)
display = filtered[    [
        "Priority",
        "Activity",
        "Issue",
        "Why it matters",
        "Recommended action",
        "issue_id",
    ]
].rename(
    columns={
        "Priority": t("iss.col.priority", lang),
        "Activity": t("iss.col.activity", lang),
        "Issue": t("iss.col.issue", lang),
        "Why it matters": t("iss.col.why", lang),
        "Recommended action": t("iss.col.next", lang),
    }
)
event = st.dataframe(
    display.drop(columns=["issue_id"]),
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    key="issues_table",
)

selected_rows = []
if event is not None and getattr(event, "selection", None) is not None:
    selected_rows = list(event.selection.rows)
selected_index = selected_rows[0] if selected_rows else 0
selected = filtered.iloc[selected_index]

st.write("")
render_section_header(t("iss.detail.problem", lang))
detail_cols = st.columns(2)
with detail_cols[0]:
    st.markdown(f"**{t('iss.detail.problem', lang)}**")
    st.write(selected["Issue"])
    st.markdown(f"**{t('iss.detail.why', lang)}**")
    st.write(selected["Why it matters"])
    st.markdown(f"**{t('iss.detail.next', lang)}**")
    st.write(selected["Recommended action"])
with detail_cols[1]:
    st.markdown(f"**{t('iss.detail.allowed', lang)}**")
    st.write(selected.get("allowed_use") or "—")
    st.markdown(f"**{t('iss.detail.prohibited', lang)}**")
    st.write(selected.get("prohibited_use") or "—")
    st.markdown(f"**{t('iss.related.activity', lang)}**")
    st.write(selected["Activity"])
    st.markdown(f"**{t('iss.related.document', lang)}**")
    st.write(selected.get("document_label") or "—")
    st.markdown(f"**{t('iss.related.period', lang)}**")
    st.write(selected.get("period_label") or "—")
    if st.button(t("iss.related.view_source", lang), key="iss_view_source"):
        st.switch_page("app_pages/activity_explorer.py")
    with st.expander(t("iss.audit_trace", lang), expanded=False):
        st.write(
            {
                "record_id": selected.get("record_id"),
                "source_document_id": selected.get("source_document_id"),
                "issue_id": selected.get("issue_id"),
                "rule_id": selected.get("rule_id"),
                "issue_code": selected.get("issue_code"),
            }
        )
