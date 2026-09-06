"""Stage 4.1 — customer product integration for verified Stage 4 calculations."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from carbon_ledger.intake import (
    ColumnMapping,
    IntakeMetadata,
    build_and_validate_intake,
    classify_activity_analysis_readiness,
    default_value_maps,
    extract_natural_gas_subtype_from_text,
    parse_uploaded_table,
    suggest_activity_type,
    suggest_column_mapping,
    suggest_unit,
    summarize_pre_analysis_readiness,
)
from carbon_ledger.pipeline import run_uploaded_pipeline
from carbon_ledger.ui.i18n import t
from carbon_ledger.ui.motion import (
    analysis_stage_keys,
    begin_analysis_presentation_reset,
    render_animated_metric,
)
from carbon_ledger.ui.state import (
    STATE_ANALYSIS_RUNNING,
    STATE_HERO_EMISSIONS_PLAY,
    STATE_LAST_ANIMATED_RESULT,
    STATE_RESULT,
    STATE_RESULT_REVEAL_PENDING,
    initialize_ui_state,
)
from carbon_ledger.ui.view_models import (
    calculated_emissions_by_product_scope,
    calculated_emissions_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HERO_JS = REPO_ROOT / "src/carbon_ledger/ui/hero_emissions_countup.js"
HERO_SHA = "70cd43b7f1fa2bedf4485bc7846278b736e1c183961c6c7117d6cc8b5f5828c0"
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00Z")

_CSV_2025 = (
    "activity_type,activity_value,unit,activity_start_date,activity_end_date\n"
    "外購電力,50000,kWh,2025-01-01,2025-01-31\n"
    "天然氣,8000,m3,2025-01-01,2025-01-31\n"
    "柴油,1200,L,2025-01-01,2025-01-31\n"
    "採購鋼材,10,t,2025-01-01,2025-01-31\n"
)


def _metadata() -> IntakeMetadata:
    return IntakeMetadata(
        source_name="company_2025.csv",
        site_id="高雄廠",
        document_date=date(2025, 1, 31),
        data_quality_tier="unknown",
        intake_run_id="stage41",
        ingested_at=FIXED_INGESTED_AT,
    )


def _mapping_for(table, **overrides: object) -> ColumnMapping:
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
        use_file_dates=True,
        start_date_column=suggestions["activity_start_date"],
        end_date_column=suggestions["activity_end_date"],
        activity_type_value_map=activity_map,
        unit_value_map=unit_map,
        natural_gas_subtype="NG1",
        diesel_context="company_vehicle",
        electricity_context="enterprise",
    )
    for key, value in overrides.items():
        setattr(mapping, key, value)
    return mapping


def _intake(csv_text: str = _CSV_2025, **mapping_overrides: object):
    table = parse_uploaded_table(
        file_name="company_2025.csv",
        data=csv_text.encode("utf-8"),
    )
    mapping = _mapping_for(table, **mapping_overrides)
    return build_and_validate_intake(table, mapping, _metadata())


def _run_upload(csv_text: str = _CSV_2025, **mapping_overrides: object):
    intake = _intake(csv_text, **mapping_overrides)
    return run_uploaded_pipeline(
        REPO_ROOT,
        run_id="stage41_upload",
        ingested_at=FIXED_INGESTED_AT,
        source_documents=intake.source_documents,
        accepted_activities=intake.accepted_activities,
        include_ghg=True,
        include_ifrs_s2=True,
    ), intake


def _status_by_type(result) -> dict[str, str]:
    activities = result.activity_records_accepted.set_index("record_id")
    calcs = result.calculation_results.set_index("record_id")
    out: dict[str, str] = {}
    for record_id, row in activities.iterrows():
        activity_type = str(row["activity_type"])
        out[activity_type] = str(calcs.loc[record_id, "calculation_status"])
    return out


def _tco2e_by_type(result) -> dict[str, float]:
    activities = result.activity_records_accepted.set_index("record_id")
    calcs = result.calculation_results.set_index("record_id")
    out: dict[str, float] = {}
    for record_id, row in activities.iterrows():
        status = str(calcs.loc[record_id, "calculation_status"])
        if status != "calculated":
            continue
        out[str(row["activity_type"])] = float(
            calcs.loc[record_id, "calculated_tco2e"]
        )
    return out


def test_uploaded_2025_electricity_reaches_calculation() -> None:
    result, _ = _run_upload()
    assert _status_by_type(result)["grid_electricity"] == "calculated"
    assert "grid_electricity" in _tco2e_by_type(result)


def test_uploaded_2025_ng1_reaches_calculation() -> None:
    result, intake = _run_upload()
    ng = intake.accepted_activities[
        intake.accepted_activities["activity_type"] == "natural_gas"
    ].iloc[0]
    assert str(ng["fuel_subtype"]) == "NG1"
    assert _status_by_type(result)["natural_gas"] == "calculated"


def test_uploaded_2025_ng2_reaches_calculation_and_differs_from_ng1() -> None:
    ng1_result, _ = _run_upload(natural_gas_subtype="NG1")
    ng2_result, _ = _run_upload(natural_gas_subtype="NG2")
    ng1 = _tco2e_by_type(ng1_result)["natural_gas"]
    ng2 = _tco2e_by_type(ng2_result)["natural_gas"]
    assert _status_by_type(ng2_result)["natural_gas"] == "calculated"
    assert ng1 != ng2


def test_uploaded_2025_company_diesel_reaches_calculation() -> None:
    result, intake = _run_upload()
    diesel = intake.accepted_activities[
        intake.accepted_activities["activity_type"] == "diesel"
    ].iloc[0]
    assert str(diesel["process_use"]) == "company_vehicle"
    assert _status_by_type(result)["diesel"] == "calculated"


def test_unknown_natural_gas_subtype_remains_blocked() -> None:
    result, intake = _run_upload(natural_gas_subtype="unknown")
    ng = intake.accepted_activities[
        intake.accepted_activities["activity_type"] == "natural_gas"
    ].iloc[0]
    assert str(ng["fuel_subtype"]) == "unknown"
    assert _status_by_type(result)["natural_gas"] == (
        "blocked_natural_gas_type_required"
    )
    assert "natural_gas" not in _tco2e_by_type(result)
    assert _status_by_type(result)["grid_electricity"] == "calculated"
    assert _status_by_type(result)["diesel"] == "calculated"


def test_explicit_ng1_in_source_is_preserved() -> None:
    csv = (
        "activity_type,activity_value,unit,activity_start_date,activity_end_date\n"
        "天然氣 NG1,8000,m3,2025-01-01,2025-01-31\n"
    )
    intake = _intake(csv, natural_gas_subtype="NG2")
    row = intake.accepted_activities.iloc[0]
    assert str(row["fuel_subtype"]) == "NG1"
    assert extract_natural_gas_subtype_from_text("天然氣 NG1") == "NG1"


def test_steel_remains_unsupported() -> None:
    result, _ = _run_upload()
    assert _status_by_type(result)["purchased_steel"] == "no_factor_configured"
    calcs = result.calculation_results
    steel = calcs[
        calcs["record_id"].isin(
            result.activity_records_accepted.loc[
                result.activity_records_accepted["activity_type"]
                == "purchased_steel",
                "record_id",
            ]
        )
    ].iloc[0]
    assert pd.isna(steel["calculated_tco2e"])


def test_blocked_rows_do_not_contribute_zero_to_total() -> None:
    result, _ = _run_upload(natural_gas_subtype="unknown")
    calcs = result.calculation_results
    blocked = calcs[calcs["calculation_status"].astype(str) != "calculated"]
    assert not blocked.empty
    assert blocked["calculated_tco2e"].isna().all()
    summary = calculated_emissions_summary(result)
    calculated = calcs[calcs["calculation_status"].astype(str) == "calculated"]
    expected = float(
        pd.to_numeric(calculated["calculated_tco2e"], errors="coerce").sum()
    )
    assert summary["calculated_tco2e"] == pytest.approx(expected)
    assert summary["calculated_row_count"] == int(len(calculated))


def test_scope_1_and_scope_2_aggregation_match_calculated_rows() -> None:
    result, _ = _run_upload()
    by_type = _tco2e_by_type(result)
    scopes = calculated_emissions_by_product_scope(result)
    assert scopes["scope_1"] == pytest.approx(
        by_type["natural_gas"] + by_type["diesel"]
    )
    assert scopes["scope_2"] == pytest.approx(by_type["grid_electricity"])
    assert scopes.get("scope_3") is None


def test_calculated_total_equals_calculated_records_sum() -> None:
    result, _ = _run_upload()
    summary = calculated_emissions_summary(result)
    by_type = _tco2e_by_type(result)
    assert summary["calculated_tco2e"] == pytest.approx(sum(by_type.values()))
    assert summary["calculated_row_count"] == 3


def test_pre_analysis_readiness_counts() -> None:
    ready = _intake()
    summary = summarize_pre_analysis_readiness(ready.accepted_activities)
    assert summary["ready"] == 3
    assert summary["needs_confirm"] == 1
    assert summary["unsupported"] == 0
    unknown = _intake(natural_gas_subtype="unknown", diesel_context="unknown")
    unknown_summary = summarize_pre_analysis_readiness(unknown.accepted_activities)
    assert unknown_summary["needs_confirm"] >= 2
    assert classify_activity_analysis_readiness(
        activity_type="purchased_steel",
        fuel_subtype="not_applicable",
        process_use="not_applicable",
        activity_start="2025-01-01",
        activity_end="2025-01-31",
    ) == "needs_confirm"


def test_old_results_hidden_when_new_analysis_begins() -> None:
    state: dict = {}
    initialize_ui_state(state)
    state[STATE_RESULT] = object()
    state[STATE_HERO_EMISSIONS_PLAY] = "old-token"
    state[STATE_RESULT_REVEAL_PENDING] = "old-token"
    state[STATE_LAST_ANIMATED_RESULT] = "old-token"
    begin_analysis_presentation_reset(state)
    assert state[STATE_RESULT] is None
    assert state[STATE_HERO_EMISSIONS_PLAY] is None
    assert state[STATE_RESULT_REVEAL_PENDING] is None
    assert state[STATE_LAST_ANIMATED_RESULT] is None
    assert state[STATE_ANALYSIS_RUNNING] is True


def test_progress_events_use_actual_pipeline_stages() -> None:
    keys = [key for key, _ in analysis_stage_keys()]
    assert keys == [
        "reading",
        "normalize",
        "factors",
        "calculate",
        "quality",
        "issues",
    ]
    source = (REPO_ROOT / "src/carbon_ledger/ui/motion.py").read_text(
        encoding="utf-8"
    )
    assert "time.sleep(" not in source
    assert '"ingest": "reading"' in source
    assert '"normalize": "normalize"' in source
    assert t("analysis.running_title", "zh-TW") == "正在分析你的資料"
    assert "render_skeleton_kpi_row" in source
    assert "render_skeleton_charts" in source


def test_hero_emissions_countup_js_unchanged() -> None:
    digest = hashlib.sha256(HERO_JS.read_bytes()).hexdigest()
    assert digest == HERO_SHA
    script = HERO_JS.read_text(encoding="utf-8")
    assert "data-cel-hero-emissions" in script
    assert "5311" not in script


def test_reusable_kpi_uses_dynamic_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def _fake_markdown(body: str, **kwargs: object) -> None:
        captured.append(str(body))

    monkeypatch.setattr("carbon_ledger.ui.motion.st.markdown", _fake_markdown)
    monkeypatch.setattr(
        "carbon_ledger.ui.motion.inject_animated_kpi_runtime", lambda: None
    )
    render_animated_metric(42.1376, decimals=2, suffix="tCO₂e", key="total", play=True)
    html_body = "\n".join(captured)
    assert 'data-cel-kpi-metric="1"' in html_body
    assert 'data-cel-target="42.1376"' in html_body
    assert "42.14" in html_body
    assert "5311" not in html_body
    assert "23.7" not in html_body
    kpi_js = (REPO_ROOT / "src/carbon_ledger/ui/animated_kpi.js").read_text(
        encoding="utf-8"
    )
    assert "prefers-reduced-motion" in kpi_js
    assert "data-cel-final" in kpi_js
    assert "5311" not in kpi_js
    assert "23.7" not in kpi_js
    hero = HERO_JS.read_text(encoding="utf-8")
    assert hero != kpi_js


def test_scope_kpis_use_backend_scope_results() -> None:
    result, _ = _run_upload()
    scopes = calculated_emissions_by_product_scope(result)
    summary = calculated_emissions_summary(result)
    assert scopes["scope_1"] > 0
    assert scopes["scope_2"] > 0
    assert summary["calculated_tco2e"] == pytest.approx(
        float(scopes["scope_1"]) + float(scopes["scope_2"])
    )


def test_reanalysis_resets_animation_target_from_zero() -> None:
    from carbon_ledger.ui.motion import animation_run_token
    from carbon_ledger.ui.state import STATE_ANIMATION_RUN

    first, _ = _run_upload(natural_gas_subtype="NG1")
    second, _ = _run_upload(natural_gas_subtype="NG2")
    state_a: dict = {}
    initialize_ui_state(state_a)
    begin_analysis_presentation_reset(state_a)
    token_a = animation_run_token(state_a, first)
    state_b: dict = {}
    initialize_ui_state(state_b)
    begin_analysis_presentation_reset(state_b)
    token_b = animation_run_token(state_b, second)
    assert token_a != token_b
    assert state_a[STATE_ANIMATION_RUN] != state_b[STATE_ANIMATION_RUN]
    kpi_js = (REPO_ROOT / "src/carbon_ledger/ui/animated_kpi.js").read_text(
        encoding="utf-8"
    )
    assert "fmt(0, decimals)" in kpi_js
    hero = HERO_JS.read_text(encoding="utf-8")
    assert "fmt(0, decimals)" in hero


def test_reduced_motion_returns_final_value() -> None:
    kpi_js = (REPO_ROOT / "src/carbon_ledger/ui/animated_kpi.js").read_text(
        encoding="utf-8"
    )
    assert "prefers-reduced-motion" in kpi_js
    assert "showFinal" in kpi_js
    assert "data-cel-final" in kpi_js


def test_dashboard_immediately_consumes_latest_result() -> None:
    from streamlit.testing.v1 import AppTest

    from carbon_ledger.ui.state import (
        STATE_INTAKE_FILE_NAME,
        STATE_INTAKE_RESULT,
        run_uploaded_analysis,
    )

    intake = _intake()
    at = AppTest.from_file(str(REPO_ROOT / "streamlit_app.py"), default_timeout=120)
    at.run()
    at.session_state[STATE_INTAKE_RESULT] = intake
    at.session_state[STATE_INTAKE_FILE_NAME] = intake.file_name
    result = run_uploaded_analysis(at.session_state)
    at.switch_page("app_pages/dashboard.py")
    at.run()
    chunks: list[str] = []
    for name in ("markdown", "caption", "text", "info", "success"):
        collection = getattr(at, name, None)
        if collection is None:
            continue
        for item in collection:
            value = getattr(item, "value", None) or getattr(item, "body", None)
            if value is not None:
                chunks.append(str(value))
    text = "\n".join(chunks)
    summary = calculated_emissions_summary(result)
    scopes = calculated_emissions_by_product_scope(result)
    assert "data-cel-hero-emissions" in text
    assert "data-cel-kpi-metric" in text
    assert "data-cel-target=" in text
    assert "Scope 1" in text
    assert "Scope 2" in text
    assert t("dash.scope3.empty", "zh-TW") in text
    assert summary["calculated_row_count"] == 3
    assert float(scopes["scope_1"] or 0) > 0
    assert float(scopes["scope_2"] or 0) > 0
    assert "採購鋼材" in text
    assert not at.exception


def test_customer_labels_hide_backend_enums() -> None:
    assert t("activity.natural_gas", "zh-TW") == "天然氣"
    assert t("activity.diesel", "zh-TW") == "柴油"
    assert t("activity.grid_electricity", "zh-TW") == "外購電力"
    motion = (REPO_ROOT / "src/carbon_ledger/ui/motion.py").read_text(encoding="utf-8")
    assert "grid_electricity" not in motion
    assert "stationary_combustion" not in motion
    assert "mobile_combustion" not in motion
