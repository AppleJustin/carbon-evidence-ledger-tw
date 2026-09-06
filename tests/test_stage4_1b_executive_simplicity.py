"""Stage 4.1b — executive simplicity and progressive disclosure."""

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
from carbon_ledger.ui.motion import post_analysis_dashboard_sections
from carbon_ledger.ui.state import activate_demo_mode
from carbon_ledger.ui.tutorial import get_onboarding_copy, onboarding_step_titles
from carbon_ledger.ui.view_models import (
    calculated_emissions_summary,
    executive_emissions_insight,
    scope_kpi_states,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HERO_JS = REPO_ROOT / "src/carbon_ledger/ui/hero_emissions_countup.js"
HERO_SHA = "70cd43b7f1fa2bedf4485bc7846278b736e1c183961c6c7117d6cc8b5f5828c0"
APP_PATH = REPO_ROOT / "streamlit_app.py"
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00Z")


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
    return "\n".join(chunks)


def _intake_and_run(csv: str) -> object:
    table = parse_uploaded_table(file_name="stage41b.csv", data=csv.encode("utf-8"))
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
            source_name="stage41b.csv",
            site_id="高雄廠",
            document_date=date(2025, 1, 31),
            data_quality_tier="unknown",
            intake_run_id="stage41b",
            ingested_at=FIXED_INGESTED_AT,
        ),
    )
    return run_uploaded_pipeline(
        REPO_ROOT,
        run_id="stage41b",
        ingested_at=FIXED_INGESTED_AT,
        source_documents=intake.source_documents,
        accepted_activities=intake.accepted_activities,
        include_ghg=True,
        include_ifrs_s2=True,
    )


def test_welcome_is_a_centered_modal_and_coachmarks_are_fixed() -> None:
    tutorial = (REPO_ROOT / "src/carbon_ledger/ui/tutorial.py").read_text(
        encoding="utf-8"
    )
    css = (REPO_ROOT / "src/carbon_ledger/ui/visual_system.css").read_text(
        encoding="utf-8"
    )
    assert "cel-onb-welcome" in tutorial
    assert "cel-coach-card" in tutorial
    assert "translate(-50%, -50%)" in css
    assert "left: 50%" in css
    assert ".st-key-cel_onboarding_coach" in css
    assert "position: fixed !important;" in css


def test_onboarding_is_five_action_steps() -> None:
    copy = get_onboarding_copy("zh-TW")
    steps = onboarding_step_titles("zh-TW")
    assert len(steps) == 5
    assert steps[0] == "完成公司設定"
    assert steps[1] == "上傳活動資料"
    assert steps[4] == "查看計算結果"
    blob = "\n".join(
        [copy["welcome_title"], copy["welcome_body"], *steps]
    )
    assert "用 6 個步驟" not in blob
    assert "用 3 個步驟" not in blob
    assert "治理、策略" not in blob
    assert "GHG Protocol" not in blob
    assert copy["later_label"] == "稍後再說"
    assert copy["finish_label"] == "完成"


def test_emissions_result_is_first_post_analysis_section() -> None:
    sections = post_analysis_dashboard_sections()
    assert sections[0] == "emissions-summary"
    assert sections[1] == "scope-breakdown"
    assert sections[2] == "insight"
    assert sections[3] == "next-step"
    assert sections[4] == "detail"
    source = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    emissions_at = source.find('scroll_key="emissions-summary"')
    detail_at = source.find('scroll_key="detail"')
    next_at = source.find('scroll_key="next-step"')
    assert emissions_at < next_at < detail_at
    assert 'scroll_key="attention"' not in source


def test_evidence_count_is_not_a_primary_kpi() -> None:
    motion = (REPO_ROOT / "src/carbon_ledger/ui/motion.py").read_text(encoding="utf-8")
    assert "evidence-count" not in motion
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "include_secondary_cards=False" in dash
    assert "dash.evidence_line" not in dash
    assert "render_hero_result_kpis" in dash


def test_unresolved_kpi_omitted_when_zero() -> None:
    motion = (REPO_ROOT / "src/carbon_ledger/ui/motion.py").read_text(encoding="utf-8")
    assert "if int(unresolved) > 0:" in motion
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "dash.coverage_all_done" in dash


def test_scope_3_empty_is_not_zero() -> None:
    csv = (
        "activity_type,activity_value,unit,activity_start_date,activity_end_date\n"
        "外購電力,50000,kWh,2025-01-01,2025-01-31\n"
        "天然氣,8000,m3,2025-01-01,2025-01-31\n"
    )
    result = _intake_and_run(csv)
    states = scope_kpi_states(result)
    assert states["scope_3"]["state"] == "empty"
    assert states["scope_3"]["value"] is None
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "dash.scope3.empty" in dash
    assert "dash.hero.scope3_version" not in dash


def test_deterministic_key_insight_from_backend() -> None:
    csv = (
        "activity_type,activity_value,unit,activity_start_date,activity_end_date\n"
        "外購電力,50000,kWh,2025-01-01,2025-01-31\n"
        "天然氣,8000,m3,2025-01-01,2025-01-31\n"
        "柴油,1200,L,2025-01-01,2025-01-31\n"
    )
    result = _intake_and_run(csv)
    insight = executive_emissions_insight(result, "zh-TW")
    assert insight
    assert "%" in insight
    assert (
        "外購電力" in insight
        or "天然氣" in insight
        or "柴油" in insight
        or "Scope" in insight
    )
    assert "建議" not in insight


def test_only_one_detail_chart_by_default() -> None:
    source = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "dash_emission_detail_tab" in source
    assert "st.segmented_control" in source
    assert 'chart_l, chart_r = st.columns(2' not in source
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    activate_demo_mode(at.session_state)
    at.run()
    assert not at.exception
    text = _all_text(at)
    assert "排放明細" in text
    assert "依來源" in text or "排放來源" in text


def test_demo_dashboard_result_first_and_insight() -> None:
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    activate_demo_mode(at.session_state)
    at.run()
    assert not at.exception
    text = _all_text(at)
    emissions_at = text.find("排放資料摘要")
    detail_at = text.find("排放明細")
    next_at = text.find("下一步")
    assert emissions_at != -1
    assert emissions_at < detail_at
    if next_at != -1:
        assert emissions_at < next_at
    assert "目前已納入公司盤查排放量" in text
    assert "Scope 1" in text
    assert "目前尚無可納入的 Scope 3 計算結果" in text
    assert "Scope 3 尚未納入計算" not in text
    dash_src = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    notice_at = dash_src.find("dash.emissions_notice")
    coverage_at = dash_src.find("dash.coverage_learn")
    assert coverage_at != -1 and notice_at != -1
    assert coverage_at < notice_at
    insight = executive_emissions_insight(at.session_state["pipeline_result"], "zh-TW")
    assert insight
    assert insight in text or "外購電力" in text or "天然氣" in text


def test_hero_animation_still_uses_backend_values() -> None:
    digest = hashlib.sha256(HERO_JS.read_bytes()).hexdigest()
    assert digest == HERO_SHA
    motion = (REPO_ROOT / "src/carbon_ledger/ui/motion.py").read_text(encoding="utf-8")
    assert "hero_emissions" in motion
    assert "kpi_play" in motion
    csv = (
        "activity_type,activity_value,unit,activity_start_date,activity_end_date\n"
        "外購電力,50000,kWh,2025-01-01,2025-01-31\n"
    )
    result = _intake_and_run(csv)
    summary = calculated_emissions_summary(result)
    assert summary["calculated_tco2e"] not in {5311, 1729.89, 0}


def test_no_sleep_fake_progress_or_hardcoded_totals() -> None:
    dash = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    assert "time.sleep(" not in dash
    assert "1729.89" not in dash
    assert "893.34" not in dash
    tutorial = (REPO_ROOT / "src/carbon_ledger/ui/tutorial.py").read_text(
        encoding="utf-8"
    )
    assert "time.sleep(" not in tutorial
