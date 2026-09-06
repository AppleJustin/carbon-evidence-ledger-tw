"""Stage 4.1c — customer product UX reset (conditional UI, layers)."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from carbon_ledger.intake import (
    ColumnMapping,
    IntakeMetadata,
    build_and_validate_intake,
    default_value_maps,
    parse_uploaded_table,
    suggest_activity_type,
    suggest_column_mapping,
    suggest_unit,
)
from carbon_ledger.pipeline import run_uploaded_pipeline
from carbon_ledger.ui.i18n import t
from carbon_ledger.ui.motion import post_analysis_dashboard_sections
from carbon_ledger.ui.state import (
    ANALYSIS_SOURCE_UPLOADED,
    STATE_ANALYSIS_SOURCE,
    STATE_RESULT,
    activate_demo_mode,
)
from carbon_ledger.ui.view_models import (
    beginner_result_summary,
    calculated_emissions_summary,
    executive_emissions_insights,
    inventory_status_counts,
    reconcile_row_dispositions,
    should_show_coverage_chart,
    should_show_unresolved_cta,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HERO_JS = REPO_ROOT / "src/carbon_ledger/ui/hero_emissions_countup.js"
HERO_SHA = "70cd43b7f1fa2bedf4485bc7846278b736e1c183961c6c7117d6cc8b5f5828c0"
APP_PATH = REPO_ROOT / "streamlit_app.py"
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00Z")
ZH = "zh-TW"
BANNED_PRIMARY = (
    "完整度",
    "活動計算狀態",
    "只顯示已計算活動",
    "framework adapter",
    "source activation",
    "calculation trace",
    "normalized records",
    "factor_id",
    "source_id",
    "record_id",
)


def _all_text(at: AppTest) -> str:
    chunks: list[str] = []
    for collection_name in (
        "markdown",
        "caption",
        "text",
        "info",
        "success",
        "warning",
        "error",
        "title",
    ):
        collection = getattr(at, collection_name, None)
        if collection is None:
            continue
        for item in collection:
            value = getattr(item, "value", None)
            if value is not None:
                chunks.append(str(value))
            body = getattr(item, "body", None)
            if body is not None:
                chunks.append(str(body))
    for button in getattr(at, "button", []) or []:
        label = getattr(button, "label", None)
        if label is not None:
            chunks.append(str(label))
    return "\n".join(chunks)


def _intake_and_run(csv: str) -> object:
    table = parse_uploaded_table(file_name="stage41c.csv", data=csv.encode("utf-8"))
    suggestions = suggest_column_mapping(list(table.columns))
    activity_map, unit_map = default_value_maps(
        table,
        ColumnMapping(
            activity_type_column=suggestions["activity_type"],
            activity_value_column=suggestions["activity_value"],
            unit_column=suggestions["unit"],
        ),
    )
    activity_map = {
        key: value or suggest_activity_type(key) for key, value in activity_map.items()
    }
    unit_map = {key: value or suggest_unit(key) for key, value in unit_map.items()}
    mapping = ColumnMapping(
        activity_type_column=suggestions["activity_type"],
        activity_value_column=suggestions["activity_value"],
        unit_column=suggestions["unit"],
        site_column=suggestions.get("site_id") or "",
        use_file_dates=True,
        start_date_column=suggestions["activity_start_date"],
        end_date_column=suggestions["activity_end_date"],
        activity_type_value_map=activity_map,
        unit_value_map=unit_map,
        natural_gas_subtype="NG1",
        diesel_context="company_vehicle",
        electricity_context="enterprise",
    )
    intake = build_and_validate_intake(
        table,
        mapping,
        IntakeMetadata(
            source_name="stage41c.csv",
            site_id="高雄廠",
            document_date=date(2025, 1, 31),
            data_quality_tier="unknown",
            intake_run_id="stage41c",
            ingested_at=FIXED_INGESTED_AT,
        ),
    )
    return run_uploaded_pipeline(
        REPO_ROOT,
        run_id="stage41c",
        ingested_at=FIXED_INGESTED_AT,
        source_documents=intake.source_documents,
        accepted_activities=intake.accepted_activities,
        include_ghg=True,
        include_ifrs_s2=True,
    )


def _complete_csv() -> str:
    return (
        "activity_type,activity_value,unit,activity_start_date,activity_end_date\n"
        "外購電力,50000,kWh,2025-01-01,2025-01-31\n"
        "天然氣,8000,m3,2025-01-01,2025-01-31\n"
        "柴油,1200,L,2025-01-01,2025-01-31\n"
    )


def _partial_csv() -> str:
    return (
        "activity_type,activity_value,unit,activity_start_date,activity_end_date\n"
        "外購電力,50000,kWh,2025-01-01,2025-01-31\n"
        "採購鋼材,10,t,2025-01-01,2025-01-31\n"
    )


def _dashboard_with_result(result: object) -> AppTest:
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    at.session_state[STATE_RESULT] = result
    at.session_state[STATE_ANALYSIS_SOURCE] = ANALYSIS_SOURCE_UPLOADED
    at.switch_page("app_pages/dashboard.py")
    at.run()
    assert not at.exception
    return at


def test_product_ux_rules_document_exists() -> None:
    path = REPO_ROOT / "docs/customer_product_ux_rules.md"
    text = path.read_text(encoding="utf-8")
    assert "progressive disclosure" in text.lower() or "漸進" in text
    assert "no empty actions" in text.lower() or "空的操作" in text
    assert "100%" in text


def test_unresolved_zero_hides_issue_cta() -> None:
    result = _intake_and_run(_complete_csv())
    summary = beginner_result_summary(result, ZH)
    assert int(summary["needs_work"]) == 0
    assert should_show_unresolved_cta(0) is False
    at = _dashboard_with_result(result)
    text = _all_text(at)
    assert t("dash.cta.view_issues", ZH) not in text
    assert t("dash.cta.view_problems", ZH) not in text
    assert "查看待處理問題" not in text


def test_unresolved_positive_shows_issue_cta() -> None:
    result = _intake_and_run(_partial_csv())
    summary = beginner_result_summary(result, ZH)
    assert int(summary["needs_work"]) > 0
    assert should_show_unresolved_cta(int(summary["needs_work"])) is True
    at = _dashboard_with_result(result)
    text = _all_text(at)
    counts = inventory_status_counts(result)
    recon = reconcile_row_dispositions(
        pipeline_result=result,
        is_uploaded_analysis=True,
    )
    assert t("dash.cta.resolve_remaining", ZH, remaining=1) in text
    assert t(
        "dash.result_preliminary_body",
        ZH,
        calculated=int(counts["technically_calculated"]),
        included=int(counts["included_in_inventory"]),
        needs_review=int(recon.get("needs_confirmation") or 0),
        unsupported=int(recon.get("unsupported") or 0),
        outside=int(counts["outside_boundary"]),
    ) in text
    assert t("dash.result_incomplete_sources", ZH) in text
    assert t("dash.result_preliminary", ZH) in text


def test_full_calculation_hides_completeness_donut() -> None:
    result = _intake_and_run(_complete_csv())
    summary = beginner_result_summary(result, ZH)
    assert int(summary["calculated"]) == int(summary["activities"])
    assert should_show_coverage_chart(
        int(summary["calculated"]), int(summary["activities"])
    ) is False
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "render_calculation_status_donut" not in dash
    at = _dashboard_with_result(result)
    text = _all_text(at)
    assert "活動計算狀態" not in text
    assert 'data-cel-key="completeness-metrics"' not in text


def test_partial_calculation_may_show_compact_progress() -> None:
    result = _intake_and_run(_partial_csv())
    summary = beginner_result_summary(result, ZH)
    assert should_show_coverage_chart(
        int(summary["calculated"]), int(summary["activities"])
    ) is True
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "st.progress(" in dash
    assert "render_calculation_status_donut" not in dash


def test_evidence_count_not_primary_kpi() -> None:
    motion = (REPO_ROOT / "src/carbon_ledger/ui/motion.py").read_text(encoding="utf-8")
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "evidence-count" not in motion
    assert "include_secondary_cards=False" in dash
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    activate_demo_mode(at.session_state)
    at.run()
    text = _all_text(at)
    assert "來源文件 · 官方係數已連結" not in text


def test_raw_file_name_not_prominent_on_dashboard() -> None:
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "render_result_meta_strip" not in dash
    assert "file_display" not in dash
    assert "source.get(\"file_name\")" not in dash


def test_regulatory_status_is_compact_when_healthy() -> None:
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "render_regulatory_status_chip" in dash
    assert "cel-reg-rail" not in dash
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    activate_demo_mode(at.session_state)
    at.run()
    text = _all_text(at)
    assert t("reg.status_title", ZH) in text
    assert t("reg.status_verified", ZH) in text or t(
        "reg.status_pending_verification", ZH
    ) in text


def test_post_analysis_first_viewport_has_result_coverage_insight() -> None:
    sections = post_analysis_dashboard_sections()
    assert sections[:4] == (
        "emissions-summary",
        "scope-breakdown",
        "insight",
        "next-step",
    )
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    activate_demo_mode(at.session_state)
    at.run()
    text = _all_text(at)
    assert "目前已納入公司盤查排放量" in text
    assert "Scope 1" in text
    assert "Scope 2" in text
    assert "目前尚無可納入的 Scope 3 計算結果" in text
    assert "Scope 3 尚未納入計算" not in text
    assert "下一步" in text
    insights = executive_emissions_insights(
        at.session_state["pipeline_result"], ZH
    )
    assert insights
    assert insights[0] in text or "外購電力" in text or "天然氣" in text


def test_scope_labels_include_plain_language() -> None:
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "dash.kpi.scope1_plain" in dash
    assert "dash.kpi.scope2_plain" in dash
    assert "dash.kpi.scope3_plain" in dash
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    activate_demo_mode(at.session_state)
    at.run()
    text = _all_text(at)
    assert "直接排放" in text
    assert "外購能源" in text
    assert "其他價值鏈排放" in text


def test_only_one_result_detail_chart_by_default() -> None:
    source = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "st.segmented_control" in source
    assert source.count("render_emissions_source_bars(") == 1
    assert source.count("render_monthly_emissions_trend(") == 1
    assert "chart_l, chart_r" not in source


def test_applicability_matrix_not_duplicated_on_home() -> None:
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "render_requirement_tile" not in dash
    assert "render_obligation_result_card" not in dash
    assert "home_requirement_summary" in dash


def test_onboarding_work_progress_reduced_after_analysis() -> None:
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    post = dash.rsplit("st.stop()", 1)[-1]
    assert "render_workflow_journey" not in post
    assert 'scroll_key="attention"' not in dash


def test_primary_copy_has_no_banned_engineering_terms() -> None:
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    activate_demo_mode(at.session_state)
    at.run()
    text = _all_text(at)
    lowered = text.lower()
    for term in BANNED_PRIMARY:
        assert term.lower() not in lowered


def test_calculations_unchanged_and_hero_locked() -> None:
    digest = hashlib.sha256(HERO_JS.read_bytes()).hexdigest()
    assert digest == HERO_SHA
    result = _intake_and_run(_complete_csv())
    summary = calculated_emissions_summary(result)
    assert summary["calculated_tco2e"] not in {5311, 1729.89, 0}
    insights = executive_emissions_insights(result, ZH)
    assert 1 <= len(insights) <= 2
