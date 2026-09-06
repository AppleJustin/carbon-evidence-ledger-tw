"""Compliance Overview — customer-first post-analysis home."""

from __future__ import annotations

import html

import streamlit as st

from carbon_ledger.potential_duplicates import (
    excluded_record_ids,
    groups_from_intake,
    unresolved_potential_duplicate_groups,
)
from carbon_ledger.ui.charts import (
    render_emissions_source_bars,
    render_monthly_emissions_trend,
)
from carbon_ledger.ui.components import (
    inject_design_system,
    render_section_header,
    render_viz_panel_end,
    render_viz_panel_start,
)
from carbon_ledger.ui.enterprise import (
    inject_enterprise_styles,
    render_greeting_block,
    render_regulatory_status_chip,
    render_workflow_journey,
)
from carbon_ledger.ui.i18n import t
from carbon_ledger.ui.motion import (
    analysis_phase,
    animation_run_token,
    consume_result_reveal,
    hero_emissions_should_play,
    mark_chart_reveal,
    render_animated_metric,
    render_hero_result_kpis,
)
from carbon_ledger.ui.refrigerant_boundary_form import (
    render_confirmation_flash,
)
from carbon_ledger.ui.state import (
    ANALYSIS_PHASE_ANALYZING,
    ANALYSIS_PHASE_COMPLETE,
    ANALYSIS_PHASE_FAILED,
    REPO_ROOT,
    STATE_ANALYSIS_PHASE,
    STATE_ANALYSIS_RUNNING,
    STATE_INTAKE_RESULT,
    STATE_INTAKE_STEP,
    STATE_INTAKE_TABLE,
    STATE_NAVIGATE_TO_RESULTS,
    duplicate_review_decisions_from_state,
    format_data_period_label,
    get_analysis_source_summary,
    get_applicability_assessment,
    get_company_profile_mapping,
    get_current_result,
    get_language,
    is_uploaded_analysis,
)
from carbon_ledger.ui.tutorial import note_entered_company_setup, onboarding_target
from carbon_ledger.ui.view_models import (
    beginner_result_summary,
    company_inventory_emissions_summary,
    executive_emissions_insights,
    hero_result_status_and_disposition,
    inventory_status_counts,
    labeled_scope_hero_caption,
    reconcile_row_dispositions,
    scope3_category1_emissions_summary,
    scope_kpi_states,
    should_show_coverage_chart,
    should_show_unresolved_cta,
    source_url_markdown,
)
from carbon_ledger.ui.view_models_compliance import (
    home_requirement_summary,
    regulatory_freshness_banner,
)

inject_design_system()
inject_enterprise_styles()
lang = get_language(st.session_state)
result = get_current_result(st.session_state)
_phase = analysis_phase(st.session_state)
if bool(st.session_state.get(STATE_ANALYSIS_RUNNING)) or _phase in {
    ANALYSIS_PHASE_ANALYZING,
    ANALYSIS_PHASE_FAILED,
}:
    # Analysis owns the main area; never paint result KPIs underneath it.
    st.stop()

if result is None:
    from carbon_ledger.ui.state import activate_demo_mode

    st.markdown(
        f"""
        <p class="cel-page-kicker">{t("dash.page_title", lang)}</p>
        <h1 class="cel-page-title">{t("onboard.welcome_title", lang)}</h1>
        <p class="cel-page-sub">{t("onboard.welcome_body", lang)}</p>
        """,
        unsafe_allow_html=True,
    )
    steps = [
        t("onboard.step1", lang),
        t("onboard.step2", lang),
        t("onboard.step3", lang),
        t("onboard.step4", lang),
        t("onboard.step5", lang),
    ]
    render_workflow_journey(
        [
            {
                "label": label,
                "state": "current" if index == 0 else "todo",
            }
            for index, label in enumerate(steps)
        ],
        lang,
    )
    cta1, cta2 = st.columns([1.2, 1])
    with cta1:
        with onboarding_target("start-setup"):
            if st.button(
                t("onboard.cta_setup", lang),
                type="primary",
                use_container_width=True,
                key="onboard_start_setup",
            ):
                note_entered_company_setup(st.session_state)
                st.switch_page("app_pages/applicability.py")
    with cta2:
        if st.button(
            t("onboard.cta_demo", lang),
            use_container_width=True,
            key="onboard_try_demo",
        ):
            activate_demo_mode(st.session_state, force=True)
            st.rerun()
    st.caption(t("onboard.demo_note", lang))
    st.stop()

source = get_analysis_source_summary(st.session_state)
uploaded = is_uploaded_analysis(st.session_state)
play_hero_count = hero_emissions_should_play(st.session_state, result)
animate = consume_result_reveal(st.session_state, result)
analysis_token = animation_run_token(st.session_state, result)

profile = get_company_profile_mapping(st.session_state)
assessment = get_applicability_assessment(st.session_state)
company_name = str(profile.get("company_name") or "") or t(
    "dash.greeting_company_fallback", lang
)
legal_year = profile.get("reporting_year") or "—"
data_period = format_data_period_label(
    source.get("period_start"), source.get("period_end")
)
reporting_year = data_period or legal_year

freshness = regulatory_freshness_banner(REPO_ROOT, lang=lang)
summary = beginner_result_summary(result, lang)
inventory = company_inventory_emissions_summary(result, lang)
inventory_counts = inventory_status_counts(result)
value = inventory["inventory_tco2e"]
done = int(inventory_counts["included_in_inventory"])
unresolved_count = int(inventory_counts["needs_review"])
total_count = int(summary["activities"])
source_count = int(summary["source_documents"])
insights = executive_emissions_insights(result, lang)
req_summary = home_requirement_summary(assessment, lang)
scope_states = scope_kpi_states(result, lang)

intake_result = st.session_state.get(STATE_INTAKE_RESULT)
uploaded_table = st.session_state.get(STATE_INTAKE_TABLE)
duplicate_decisions = duplicate_review_decisions_from_state(st.session_state)
dup_groups = groups_from_intake(intake_result) if intake_result is not None else []
excluded_ids = excluded_record_ids(dup_groups, duplicate_decisions)
unresolved_groups = unresolved_potential_duplicate_groups(
    dup_groups, duplicate_decisions
)
candidate_ids = {
    str(record_id)
    for group in unresolved_groups
    for record_id in group.record_ids
}
dispositions = reconcile_row_dispositions(
    uploaded_table=uploaded_table,
    intake_result=intake_result,
    pipeline_result=result,
    duplicate_excluded_ids=excluded_ids,
    duplicate_candidate_ids=candidate_ids,
    duplicate_unresolved=bool(unresolved_groups),
    is_uploaded_analysis=uploaded,
)
hero_copy = hero_result_status_and_disposition(
    uploaded=uploaded,
    dispositions=dispositions,
    calculated_count=int(inventory_counts["technically_calculated"]),
    activity_count=total_count,
    needs_work=unresolved_count,
    lang=lang,
    inventory_counts=inventory_counts,
)
included = int(hero_copy["included"])
remaining_open = int(hero_copy["remaining_open"])
actionable_open = int(hero_copy.get("actionable_open", remaining_open))
population = int(hero_copy["hero_total"])
complete = bool(hero_copy["complete"])
show_issues = actionable_open > 0 if uploaded else should_show_unresolved_cta(
    unresolved_count
)
show_coverage_bar = should_show_coverage_chart(
    int(hero_copy["hero_done"]), population
)

st.markdown(
    f'<p class="cel-page-kicker">{t("dash.page_title", lang)}</p>',
    unsafe_allow_html=True,
)
# 1. 排放資料摘要 — hero first
render_section_header(
    t("dash.emissions_section", lang),
    scroll_key="emissions-summary",
)
scope_caption = labeled_scope_hero_caption(scope_states, lang)
render_hero_result_kpis(
    emissions_value=value,
    emissions_label=t("dash.kpi.inventory", lang),
    emissions_subtitle="",
    done=int(hero_copy["hero_done"]),
    total=int(hero_copy["hero_total"]),
    completion_label=t("dash.kpi.completion", lang),
    completion_subtitle=t(
        "dash.emissions_ratio",
        lang,
        done=int(hero_copy["hero_done"]),
        total=int(hero_copy["hero_total"]),
    ),
    unresolved=int(hero_copy["unresolved"]),
    unresolved_label=t("dash.kpi.unresolved", lang),
    unresolved_subtitle=t("dash.kpi.unresolved_hint", lang),
    sources=source_count,
    sources_label=t("dash.kpi.source", lang),
    sources_subtitle=t("dash.kpi.source_hint", lang),
    animate=animate,
    animation_token=analysis_token,
    play_hero_count=play_hero_count,
    include_secondary_cards=False,
    status_label=hero_copy["status_label"],
    disposition_caption=hero_copy["disposition_caption"],
    scope_caption=scope_caption,
    excluded_caption=hero_copy["excluded_caption"],
    meta_caption=t(
        "dash.hero.meta",
        lang,
        company=company_name,
        period=data_period or t("dash.period_unknown", lang),
        sources=source_count,
    ),
)
if st.button(t("dash.hero.factor_details", lang), key="dash_hero_factor_details"):
    st.switch_page("app_pages/activity_explorer.py")

render_confirmation_flash(result, lang)
if uploaded and st.button(
    t("dash.cta.edit_emissions_data", lang),
    key="dash_edit_emissions_data",
):
    st.session_state[STATE_INTAKE_STEP] = 3
    st.session_state[STATE_ANALYSIS_PHASE] = ANALYSIS_PHASE_COMPLETE
    st.session_state[STATE_NAVIGATE_TO_RESULTS] = False
    st.switch_page("app_pages/data_intake.py")

render_greeting_block(
    company=company_name,
    reporting_year=legal_year,
    data_period=data_period,
    attention_count=0,
    lang=lang,
)
render_regulatory_status_chip(freshness, lang)

if uploaded and remaining_open > 0:
    if hero_copy.get("disposition_caption"):
        st.warning("⚠ " + str(hero_copy["disposition_caption"]))
    if hero_copy.get("incomplete_caption") and actionable_open > 0:
        st.caption(str(hero_copy["incomplete_caption"]))
    if actionable_open > 0 and st.button(
        t("dash.cta.resolve_remaining", lang, remaining=actionable_open),
        key="dash_resolve_remaining",
    ):
        st.switch_page("app_pages/issues_actions.py")
elif show_issues:
    st.warning(
        "⚠ " + t("dash.issues_banner", lang, count=unresolved_count)
    )
    if show_coverage_bar:
        st.progress(float(done) / float(max(1, total_count)))
        st.caption(
            t(
                "dash.coverage_partial",
                lang,
                done=done,
                total=total_count,
            )
        )
    if st.button(t("dash.cta.view_problems", lang), key="dash_view_issues"):
        st.switch_page("app_pages/issues_actions.py")
elif uploaded and complete and included >= 1:
    st.success("✓ " + t("dash.coverage_complete", lang, total=population))
    st.caption("✓ " + t("dash.coverage_all_done", lang))
elif not uploaded and complete:
    st.success("✓ " + t("dash.coverage_complete_demo", lang))
    st.caption("✓ " + t("dash.coverage_all_done", lang))

# 2. Scope 分解
scope_states = scope_kpi_states(result, lang)
render_section_header(
    t("dash.section_scope_main", lang),
    scroll_key="scope-breakdown",
)
scope_cols = st.columns(3)


def _render_scope_kpi(
    scope_key: str, label_key: str, plain_key: str, metric_key: str
) -> None:
    st.markdown(f"**{t(label_key, lang)}**")
    st.caption(t(plain_key, lang))
    state = scope_states.get(scope_key) or {}
    if state.get("state") == "calculated":
        render_animated_metric(
            float(state.get("value") or 0.0),
            decimals=2,
            suffix="tCO₂e",
            key=metric_key,
            play=play_hero_count,
            run=analysis_token,
        )
        if scope_key == "scope_3":
            caption = str(state.get("caption") or t("dash.scope3.partial", lang))
            st.markdown(
                "<div data-cel-tour-target='results-scope3'>"
                f"{html.escape(caption)}"
                "</div>",
                unsafe_allow_html=True,
            )
        return
    if scope_key == "scope_3":
        st.markdown(
            "<div data-cel-tour-target='results-scope3'>"
            f"{html.escape(t('dash.scope3.empty', lang))}"
            "</div>",
            unsafe_allow_html=True,
        )
        return
    st.write(t("dash.scope_pending", lang))


with scope_cols[0]:
    _render_scope_kpi(
        "scope_1", "dash.kpi.scope1", "dash.kpi.scope1_plain", "scope-1"
    )
with scope_cols[1]:
    _render_scope_kpi(
        "scope_2", "dash.kpi.scope2", "dash.kpi.scope2_plain", "scope-2"
    )
with scope_cols[2]:
    _render_scope_kpi(
        "scope_3", "dash.kpi.scope3", "dash.kpi.scope3_plain", "scope-3"
    )
with st.expander(t("dash.scope_help_title", lang), expanded=False):
    st.markdown(t("dash.scope_help_body", lang))

cat1 = scope3_category1_emissions_summary(result, lang)
render_section_header(t("dash.scope3_cat1.title", lang))
if cat1.get("row_count"):
    st.markdown(f"**{t('dash.scope3_cat1.estimated', lang)}**")
    st.write(f"{float(cat1['tco2e']):.4f} tCO₂e")
    st.caption(str(cat1["not_in_inventory"]))
    for row in cat1.get("rows") or []:
        method_code = str(row.get("calculation_method") or "")
        method_key = f"dash.scope3_cat1.method.{method_code}"
        method_label = t(method_key, lang)
        if method_label == method_key:
            method_label = method_code
        st.markdown(
            f"- {t('dash.scope3_cat1.method', lang)}：{method_label}"
        )
        if row.get("supplier_name"):
            st.markdown(
                f"- {t('dash.scope3_cat1.supplier', lang)}："
                f"{row['supplier_name']}"
            )
        if row.get("steel_product_type"):
            st.markdown(
                f"- {t('dash.scope3_cat1.product', lang)}："
                f"{row.get('official_name') or row['steel_product_type']}"
            )
        if row.get("factor_id"):
            st.markdown(
                f"- {t('dash.scope3_cat1.factor_id', lang)}："
                f"{row['factor_id']}"
            )
        if row.get("factor_value") not in (None, ""):
            unit = row.get("factor_unit") or ""
            st.markdown(
                f"- {t('dash.scope3_cat1.factor_value', lang)}："
                f"{row['factor_value']} {unit}".rstrip()
            )
        if row.get("publisher"):
            st.markdown(
                f"- {t('dash.scope3_cat1.publisher', lang)}："
                f"{row['publisher']}"
            )
        if row.get("factor_version"):
            st.markdown(
                f"- {t('dash.scope3_cat1.factor_version', lang)}："
                f"{row['factor_version']}"
            )
        if row.get("announcement_year") or row.get("factor_year"):
            st.markdown(
                f"- {t('dash.scope3_cat1.announcement_year', lang)}："
                f"{row.get('announcement_year') or row.get('factor_year')}"
            )
        if row.get("factor_year"):
            st.markdown(
                f"- {t('dash.scope3_cat1.factor_year', lang)}："
                f"{row['factor_year']}"
            )
        if row.get("factor_source_id") or row.get("evidence_reference"):
            st.markdown(
                f"- {t('dash.scope3_cat1.factor_source', lang)}："
                f"{row.get('factor_source_id') or row.get('evidence_reference')}"
            )
        if row.get("source_url"):
            st.markdown(
                f"- {t('dash.scope3_cat1.source_url', lang)}："
                f"{source_url_markdown(row['source_url'])}"
            )
        if row.get("snapshot_hash"):
            st.markdown(
                f"- {t('dash.scope3_cat1.snapshot', lang)}："
                f"{row['snapshot_hash']}"
            )
        if row.get("factor_boundary"):
            st.markdown(
                f"- {t('dash.scope3_cat1.boundary', lang)}："
                f"{row['factor_boundary']}"
            )
        st.caption(t("dash.scope3_cat1.boundary_note", lang))
        if row.get("temporal_warning"):
            st.info(
                t(
                    "dash.scope3_cat1.temporal",
                    lang,
                    factor_year=row.get("factor_year"),
                    reporting_year=row.get("reporting_year")
                    or row.get("factor_year"),
                )
            )
else:
    st.caption(t("dash.scope3_cat1.empty", lang))

# 3. Insights — one primary, one optional
if insights:
    st.info(insights[0])
    if len(insights) > 1:
        st.caption(insights[1])
    st.markdown(
        '<div data-cel-scroll="insight" id="cel-insight"></div>',
        unsafe_allow_html=True,
    )

# 4. 下一步 — one action, not a repeated matrix
render_section_header(t("dash.section_next", lang), scroll_key="next-step")
if req_summary["cta"] == "complete":
    st.markdown(f"**{t('dash.next.applicability', lang)}**")
    st.caption(t("dash.next.applicability_body", lang))
    if st.button(
        t("dash.cta.complete_now", lang),
        type="primary",
        key="dash_start_apl",
    ):
        st.switch_page("app_pages/applicability.py")
else:
    render_section_header(
        t("dash.section_requirements", lang),
        scroll_key="requirements",
    )
    st.markdown(f"**{t('dash.req.headline', lang)}**")
    for line in req_summary["lines"]:
        st.markdown(f"- {line}")
    if st.button(t("dash.cta.view_requirements", lang), key="dash_view_req"):
        st.switch_page("app_pages/applicability.py")

# 5. 排放明細 — one chart at a time
render_section_header(
    t("dash.section_detail", lang),
    t("dash.section_detail_help", lang),
    scroll_key="detail",
)
source_tab = t("dash.detail.source", lang)
trend_tab = t("dash.detail.trend", lang)
selected_detail = st.segmented_control(
    t("dash.cta.view_detail", lang),
    options=[source_tab, trend_tab],
    default=source_tab,
    key="dash_emission_detail_tab",
)
if selected_detail == trend_tab:
    render_viz_panel_start(
        t("dash.detail.trend_title", lang),
        scroll_key="trend",
        chart_kind="trend",
    )
    mark_chart_reveal("trend", chart="trend")
    render_monthly_emissions_trend(result, lang)
    render_viz_panel_end()
else:
    render_viz_panel_start(
        t("dash.section_sources", lang),
        scroll_key="sources",
        chart_kind="bars",
    )
    mark_chart_reveal("sources", chart="bars")
    render_emissions_source_bars(result, lang)
    render_viz_panel_end()

# 6. Professional detail on request
with st.expander(t("dash.coverage_learn", lang), expanded=False):
    st.markdown(
        '<div data-cel-scroll="professional" id="cel-professional"></div>',
        unsafe_allow_html=True,
    )
    st.write(t("dash.coverage_learn_body", lang))
    st.caption(t("dash.emissions_notice", lang))
    period_start = source.get("period_start")
    period_end = source.get("period_end")
    if period_start and period_end:
        st.caption(
            t(
                "dash.period_line",
                lang,
                start=period_start,
                end=period_end,
            )
        )
    st.caption(t("dash.source_files_line", lang, count=source_count))
    if st.button(
        t("dash.cta.view_calc_basis", lang),
        key="dash_go_activity",
    ):
        st.switch_page("app_pages/activity_explorer.py")
    st.markdown(
        "<span data-cel-tour-target='results-evidence'></span>",
        unsafe_allow_html=True,
    )
    if st.button(
        t("dash.cta.view_evidence", lang),
        key="dash_go_evidence_records",
    ):
        st.switch_page("app_pages/evidence_data.py")
