"""Purchased-steel confirmation overlays for the data-intake review step."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from carbon_ledger.activity_boundary_decisions import reporting_year_from_activity
from carbon_ledger.intake import (
    ColumnMapping,
    IntakeMetadata,
    build_and_validate_intake,
    classify_activity_analysis_readiness,
    default_value_maps,
    parse_uploaded_table,
    suggest_activity_type,
    suggest_column_mapping,
    suggest_unit,
    summarize_pre_analysis_readiness,
)
from carbon_ledger.pipeline import run_uploaded_pipeline
from carbon_ledger.purchased_steel import (
    CONTROL_NOT_APPLICABLE,
    CONTROL_REPORTING_COMPANY,
    CONTROL_THIRD_PARTY,
    STATUS_NO_FACTOR_CONFIGURED,
    STATUS_NO_MATCHING_FACTOR,
)
from carbon_ledger.purchased_steel_confirmations import (
    ERROR_BOUNDARY_REQUIRED,
    ERROR_EVIDENCE_REQUIRED,
    ERROR_FACTOR_UNIT_REQUIRED,
    ERROR_FACTOR_VALUE_REQUIRED,
    ERROR_FACTOR_YEAR_REQUIRED,
    ERROR_INBOUND_UNANSWERED,
    ERROR_METHOD_REQUIRED,
    ERROR_PRODUCT_REQUIRED,
    ERROR_SUPPLIER_REQUIRED,
    ERROR_TRANSPORT_CONTROL_UNANSWERED,
    METHOD_UNDECIDED,
    PurchasedSteelConfirmation,
    activity_reporting_period_id,
    apply_purchased_steel_confirmations,
    build_confirmation,
    steel_confirmation_candidates,
    validate_confirmation,
)
from carbon_ledger.ui.i18n import LANG_EN, LANG_ZH, MESSAGES, t
from carbon_ledger.ui.state import (
    STATE_INTAKE_FILE_HASH,
    STATE_INTAKE_FILE_NAME,
    STATE_INTAKE_RESULT,
    STATE_PURCHASED_STEEL_CONFIRMATIONS,
    initialize_ui_state,
    purchased_steel_confirmations_from_state,
    run_uploaded_analysis,
    save_purchased_steel_confirmation_in_session,
)
from carbon_ledger.ui.view_models import (
    DISPOSITION_NEEDS_CONFIRMATION,
    DISPOSITION_NO_MATCHING_FACTOR,
    DISPOSITION_UNSUPPORTED,
    activity_detail_context,
    company_inventory_emissions_summary,
    reconcile_row_dispositions,
    scope3_category1_emissions_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00Z")
ZH = "zh-TW"
_OLD_HEADERS = (
    "activity_type,activity_value,unit,activity_start_date,activity_end_date"
)
_I18N_KEYS = (
    "intake.steel.form.title",
    "intake.steel.save",
    "intake.steel.edit",
    "intake.steel.edit.help",
    "intake.steel.method.undecided",
    "intake.legend.format_ok",
    "intake.legend.needs_confirm",
    "intake.legend.no_factor",
    "intake.issue.steel_average_no_factor",
    "intake.result_no_factor",
    "dash.result_no_factor",
    "explain.steel.no_factor_configured",
    "explain.steel.no_matching_factor",
    "intake.issue.steel_candidate_pending_review",
    "intake.steel.form.transport_help",
    "intake.field.factor_includes_inbound_transport",
    "intake.field.transport_control",
    "explain.steel.blocked_tier1_inbound_transport_requires_category4_split",
    "explain.steel.blocked_company_controlled_transport_requires_scope1_or2_split",
)


def _metadata() -> IntakeMetadata:
    return IntakeMetadata(
        source_name="steel_confirm.csv",
        site_id="高雄廠",
        document_date=date(2025, 1, 31),
        data_quality_tier="unknown",
        intake_run_id="steel_confirm",
        ingested_at=FIXED_INGESTED_AT,
    )


def _mapping_for(table) -> ColumnMapping:
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
        key: value or suggest_activity_type(key)
        for key, value in activity_map.items()
    }
    unit_map = {
        key: value or suggest_unit(key) for key, value in unit_map.items()
    }
    return ColumnMapping(
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


def _csv(*rows: str, headers: str = _OLD_HEADERS) -> str:
    return headers + "\n" + "\n".join(rows) + "\n"


def _intake(*rows: str, headers: str = _OLD_HEADERS):
    table = parse_uploaded_table(
        file_name="steel_confirm.csv",
        data=_csv(*rows, headers=headers).encode("utf-8"),
    )
    return build_and_validate_intake(table, _mapping_for(table), _metadata())


def _steel_row(intake) -> pd.Series:
    accepted = intake.accepted_activities
    return accepted.loc[accepted["activity_type"] == "purchased_steel"].iloc[0]


def _complete_supplier(
    intake,
    *,
    supplier_name: str = "Demo Steel Supplier",
    factor_year: str = "2025",
    evidence_reference: str = "EPD-2025-001",
    inbound: str = "false",
    control: str = "",
    includes_pre_tier1_supply_chain_transport: str = "",
    file_hash: str | None = None,
    reporting_year: int | None = None,
) -> object:
    row = _steel_row(intake)
    year = reporting_year
    if year is None:
        year = reporting_year_from_activity(row)
    return build_confirmation(
        file_hash=file_hash if file_hash is not None else intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=int(year or 0),
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="supplier_specific",
        supplier_name=supplier_name,
        steel_product_type="steel wire rod",
        emission_factor_value="1.85",
        emission_factor_unit="tCO2e/t",
        factor_boundary="cradle_to_gate",
        factor_year=factor_year,
        evidence_reference=evidence_reference,
        includes_tier1_to_reporting_company_transport=inbound,
        factor_includes_tier1_to_reporting_company_transport=inbound,
        tier1_to_reporting_company_transport_control=control,
        includes_pre_tier1_supply_chain_transport=(
            includes_pre_tier1_supply_chain_transport
        ),
    )


def _complete_average(
    intake,
    *,
    product: str = "鋼板",
    inbound: str = "false",
    control: str = "",
    factor_geography: str = "TW",
    technology: str = "basic_oxygen_furnace",
) -> object:
    row = _steel_row(intake)
    return build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=int(reporting_year_from_activity(row) or 2025),
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="average_data",
        steel_product_type=product,
        product_identifier=product,
        factor_geography=factor_geography,
        technology=technology,
        includes_tier1_to_reporting_company_transport=inbound,
        factor_includes_tier1_to_reporting_company_transport=inbound,
        tier1_to_reporting_company_transport_control=control,
    )


def _pipeline(accepted, intake):
    return run_uploaded_pipeline(
        REPO_ROOT,
        run_id="steel_confirm",
        ingested_at=FIXED_INGESTED_AT,
        source_documents=intake.source_documents,
        accepted_activities=accepted,
        include_ghg=True,
    )


def test_original_ten_tonne_row_shows_confirmation_form_candidate() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    row = _steel_row(intake)
    assert str(row.get("calculation_method") or "") == ""
    assert (
        classify_activity_analysis_readiness(
            activity_type="purchased_steel",
            fuel_subtype="",
            process_use="",
            activity_start=row["activity_start_date"],
            activity_end=row["activity_end_date"],
        )
        == "needs_confirm"
    )
    candidates = steel_confirmation_candidates(intake.accepted_activities)
    assert len(candidates) == 1
    assert str(candidates.iloc[0]["record_id"]) == str(row["record_id"])
    assert summarize_pre_analysis_readiness(intake.accepted_activities)[
        "needs_confirm"
    ] == 1


def test_undecided_method_cannot_be_saved_or_calculated() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    row = _steel_row(intake)
    confirmation = build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=2025,
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method=METHOD_UNDECIDED,
        includes_tier1_to_reporting_company_transport="false",
    )
    errors = validate_confirmation(
        confirmation, current_file_hash=intake.file_hash
    )
    assert ERROR_METHOD_REQUIRED in errors
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel.get("calculation_method") or "") == ""
    result = _pipeline(overlaid, intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == STATUS_NO_FACTOR_CONFIGURED
    assert pd.isna(calc["calculated_tco2e"])
    assert scope3_category1_emissions_summary(result, ZH)["tco2e"] is None


def test_supplier_specific_missing_supplier_year_or_evidence_does_not_apply() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    original = intake.accepted_activities.copy(deep=True)
    cases = (
        ({"supplier_name": ""}, ERROR_SUPPLIER_REQUIRED),
        ({"factor_year": ""}, ERROR_FACTOR_YEAR_REQUIRED),
        ({"evidence_reference": ""}, ERROR_EVIDENCE_REQUIRED),
    )
    for fields, error in cases:
        confirmation = _complete_supplier(intake, **fields)
        errors = validate_confirmation(
            confirmation, current_file_hash=intake.file_hash
        )
        assert error in errors
        overlaid = apply_purchased_steel_confirmations(
            original,
            [confirmation],
            current_file_hash=intake.file_hash,
        )
        steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
        assert str(steel.get("calculation_method") or "") == ""
        result = _pipeline(overlaid, intake)
        calc = result.calculation_results.loc[
            result.calculation_results["record_id"] == steel["record_id"]
        ].iloc[0]
        assert calc["calculation_status"] != "calculated"
        assert pd.isna(calc["calculated_tco2e"])


def test_complete_supplier_specific_overlay_calculates_18_5() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    original = intake.accepted_activities.copy(deep=True)
    confirmation = _complete_supplier(intake)
    overlaid = apply_purchased_steel_confirmations(
        original,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    assert original.equals(intake.accepted_activities)
    steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel["calculation_method"]) == "supplier_specific"
    result = _pipeline(overlaid, intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == steel["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == "calculated"
    assert float(calc["calculated_tco2e"]) == 18.5
    summary = scope3_category1_emissions_summary(result, ZH)
    assert summary["tco2e"] == 18.5
    inventory = company_inventory_emissions_summary(result, ZH)
    assert inventory["inventory_tco2e"] in {None, 0.0}


def test_average_data_without_registry_factor_is_not_zero() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    row = _steel_row(intake)
    confirmation = build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=2025,
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="average_data",
        steel_product_type="steel wire rod",
        factor_geography="TW",
        includes_tier1_to_reporting_company_transport="false",
    )
    assert not validate_confirmation(
        confirmation, current_file_hash=intake.file_hash
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    result = _pipeline(overlaid, intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == STATUS_NO_MATCHING_FACTOR
    assert pd.isna(calc["calculated_tco2e"])
    assert scope3_category1_emissions_summary(result, ZH)["tco2e"] is None
    explanation = t("explain.steel.no_matching_factor", ZH)
    assert "暫不計算" in explanation


def test_inbound_transport_does_not_enter_category_1() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    confirmation = _complete_supplier(
        intake, inbound="true", control=CONTROL_THIRD_PARTY
    )
    assert not validate_confirmation(
        confirmation, current_file_hash=intake.file_hash
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    result = _pipeline(overlaid, intake)
    row = _steel_row(intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == (
        "blocked_tier1_inbound_transport_requires_category4_split"
    )
    assert pd.isna(calc["calculated_tco2e"])
    assert scope3_category1_emissions_summary(result, ZH)["tco2e"] is None
    zh = activity_detail_context(result, str(row["record_id"]), ZH)[
        "calculation_explanation"
    ]
    assert zh == t(
        "explain.steel.blocked_tier1_inbound_transport_requires_category4_split",
        ZH,
    )
    assert zh != str(calc["calculation_reason"])


def test_generic_average_product_is_required_even_when_transport_is_blocked() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    for control in (CONTROL_REPORTING_COMPANY, CONTROL_THIRD_PARTY):
        confirmation = _complete_average(
            intake,
            product="其他／尚不確定",
            inbound="true",
            control=control,
        )
        errors = validate_confirmation(
            confirmation,
            current_file_hash=intake.file_hash,
        )
        assert ERROR_PRODUCT_REQUIRED in errors


def test_blocked_average_overlay_keeps_product_identity_and_matching_context() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    confirmation = _complete_average(
        intake,
        inbound="true",
        control=CONTROL_REPORTING_COMPANY,
    )
    assert not validate_confirmation(
        confirmation,
        current_file_hash=intake.file_hash,
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
    assert steel["steel_product_type"] == "鋼板"
    assert steel["product_identifier"] == "鋼板"
    assert steel["factor_geography"] == "TW"
    assert steel["technology"] == "basic_oxygen_furnace"
    result = _pipeline(overlaid, intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == steel["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == (
        "blocked_company_controlled_transport_requires_scope1_or2_split"
    )
    assert pd.isna(calc["calculated_tco2e"])


def test_blocked_supplier_overlay_keeps_product_and_factor_evidence() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    row = _steel_row(intake)
    confirmation = build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=2025,
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="supplier_specific",
        supplier_name="Demo Steel Supplier",
        steel_product_type="steel wire rod",
        product_identifier="WR-001",
        emission_factor_value="1.85",
        emission_factor_unit="tCO2e/t",
        factor_boundary="cradle_to_gate",
        factor_geography="TW",
        factor_year="2025",
        factor_source_id="supplier-factor-2025",
        evidence_reference="EPD-2025-001",
        source_document_id="doc-epd-2025-001",
        technology="electric_arc_furnace",
        includes_tier1_to_reporting_company_transport="true",
        factor_includes_tier1_to_reporting_company_transport="true",
        tier1_to_reporting_company_transport_control=CONTROL_THIRD_PARTY,
    )
    assert not validate_confirmation(
        confirmation,
        current_file_hash=intake.file_hash,
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
    assert steel["supplier_name"] == "Demo Steel Supplier"
    assert steel["steel_product_type"] == "steel wire rod"
    assert steel["product_identifier"] == "WR-001"
    assert steel["emission_factor_value"] == "1.85"
    assert steel["emission_factor_unit"] == "tCO2e/t"
    assert steel["factor_boundary"] == "cradle_to_gate"
    assert steel["factor_year"] == "2025"
    assert steel["factor_source_id"] == "supplier-factor-2025"
    assert steel["evidence_reference"] == "EPD-2025-001"
    assert steel["source_document_id"] == "doc-epd-2025-001"
    assert steel["factor_geography"] == "TW"
    assert steel["technology"] == "electric_arc_furnace"


def test_blocked_supplier_still_validates_every_required_factor_field() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    complete = _complete_supplier(
        intake,
        inbound="true",
        control=CONTROL_REPORTING_COMPANY,
    )
    cases = (
        ("supplier_name", "", ERROR_SUPPLIER_REQUIRED),
        ("steel_product_type", "", ERROR_PRODUCT_REQUIRED),
        ("emission_factor_value", "not-a-number", ERROR_FACTOR_VALUE_REQUIRED),
        ("emission_factor_unit", "", ERROR_FACTOR_UNIT_REQUIRED),
        ("factor_boundary", "", ERROR_BOUNDARY_REQUIRED),
        ("factor_year", "", ERROR_FACTOR_YEAR_REQUIRED),
        ("evidence_reference", "", ERROR_EVIDENCE_REQUIRED),
    )
    for field_name, value, expected in cases:
        raw = complete.to_dict()
        raw[field_name] = value
        confirmation = PurchasedSteelConfirmation.from_dict(raw)
        errors = validate_confirmation(
            confirmation,
            current_file_hash=intake.file_hash,
        )
        assert expected in errors


def test_corrected_confirmation_replaces_identity_and_clears_control() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    state: dict = {}
    initialize_ui_state(state)
    state[STATE_INTAKE_FILE_HASH] = intake.file_hash
    wrong = _complete_average(
        intake,
        inbound="true",
        control=CONTROL_REPORTING_COMPANY,
    )
    corrected = _complete_average(
        intake,
        inbound="false",
        control=CONTROL_REPORTING_COMPANY,
    )
    assert corrected.tier1_to_reporting_company_transport_control == (
        CONTROL_NOT_APPLICABLE
    )
    save_purchased_steel_confirmation_in_session(state, wrong)
    save_purchased_steel_confirmation_in_session(state, corrected)
    saved = purchased_steel_confirmations_from_state(state)
    assert len(saved) == 1
    assert len(state[STATE_PURCHASED_STEEL_CONFIRMATIONS]) == 1
    assert saved[0].identity() == wrong.identity() == corrected.identity()
    assert saved[0].steel_product_type == "鋼板"
    assert saved[0].tier1_to_reporting_company_transport_control == (
        CONTROL_NOT_APPLICABLE
    )


def test_dashboard_has_no_full_confirmation_forms_but_intake_step3_does() -> None:
    dashboard = (REPO_ROOT / "app_pages/dashboard.py").read_text(encoding="utf-8")
    intake = (REPO_ROOT / "app_pages/data_intake.py").read_text(encoding="utf-8")
    other_customer_pages = (
        REPO_ROOT / "app_pages/activity_explorer.py",
        REPO_ROOT / "app_pages/issues_actions.py",
    )
    assert "render_refrigerant_boundary_confirmation(" not in dashboard
    assert "render_purchased_steel_confirmation_forms(" not in dashboard
    assert "accepted_activities_for_review" not in dashboard
    assert "pipeline_calculation_status_by_record" not in dashboard
    for page in other_customer_pages:
        source = page.read_text(encoding="utf-8")
        assert "render_refrigerant_boundary_confirmation(" not in source
        assert "render_purchased_steel_confirmation_forms(" not in source
    assert "render_refrigerant_boundary_confirmation(pipeline, lang)" in intake
    assert "render_purchased_steel_confirmation_forms(" in intake
    assert 't("dash.cta.edit_emissions_data", lang)' in dashboard


def test_confirmation_from_another_file_or_year_is_not_applied() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    original_method = str(_steel_row(intake).get("calculation_method") or "")
    other_file = _complete_supplier(intake, file_hash="abc123otherfile")
    other_year = _complete_supplier(intake, reporting_year=2024)
    for confirmation in (other_file, other_year):
        overlaid = apply_purchased_steel_confirmations(
            intake.accepted_activities,
            [confirmation],
            current_file_hash=intake.file_hash,
        )
        steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
        assert str(steel.get("calculation_method") or "") == original_method


def test_steel_overlay_does_not_change_scope_1_and_2_inventory() -> None:
    baseline = _intake(
        "外購電力,50000,kWh,2025-01-01,2025-01-31",
        "天然氣,8000,m3,2025-01-01,2025-01-31",
        "柴油,1200,L,2025-01-01,2025-01-31",
    )
    with_steel = _intake(
        "外購電力,50000,kWh,2025-01-01,2025-01-31",
        "天然氣,8000,m3,2025-01-01,2025-01-31",
        "柴油,1200,L,2025-01-01,2025-01-31",
        "採購鋼材,10,t,2025-01-01,2025-12-31",
    )
    confirmation = _complete_supplier(with_steel)
    overlaid = apply_purchased_steel_confirmations(
        with_steel.accepted_activities,
        [confirmation],
        current_file_hash=with_steel.file_hash,
    )
    base_result = _pipeline(baseline.accepted_activities, baseline)
    steel_result = _pipeline(overlaid, with_steel)
    base_inventory = company_inventory_emissions_summary(base_result, ZH)
    steel_inventory = company_inventory_emissions_summary(steel_result, ZH)
    assert steel_inventory["inventory_tco2e"] == base_inventory["inventory_tco2e"]
    assert steel_inventory["scope_1"] == base_inventory["scope_1"]
    assert steel_inventory["scope_2"] == base_inventory["scope_2"]
    assert scope3_category1_emissions_summary(steel_result, ZH)["tco2e"] == 18.5
    assert (
        scope3_category1_emissions_summary(steel_result, ZH)["tco2e"]
        != steel_inventory["inventory_tco2e"]
    )


def test_session_save_then_uploaded_analysis_uses_overlay() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    state: dict = {}
    initialize_ui_state(state)
    state[STATE_INTAKE_RESULT] = intake
    state[STATE_INTAKE_FILE_HASH] = intake.file_hash
    state[STATE_INTAKE_FILE_NAME] = intake.file_name
    save_purchased_steel_confirmation_in_session(
        state, _complete_supplier(intake)
    )
    result = run_uploaded_analysis(state, run_id="steel_confirm_session")
    row = _steel_row(intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert float(calc["calculated_tco2e"]) == 18.5
    original = intake.accepted_activities.loc[
        intake.accepted_activities["record_id"] == row["record_id"]
    ].iloc[0]
    assert str(original.get("calculation_method") or "") == ""


def test_confirmation_copy_exists_in_zh_and_en() -> None:
    for key in _I18N_KEYS:
        entry = MESSAGES[key]
        assert entry[LANG_ZH].strip()
        assert entry[LANG_EN].strip()
    assert MESSAGES["intake.steel.save"][LANG_ZH] == "儲存並重新分析"
    assert "格式檢查通過" in MESSAGES["intake.legend.format_ok"][LANG_ZH]
    assert "需要確認" in MESSAGES["intake.legend.needs_confirm"][LANG_ZH]
    assert "目前無符合係數" in MESSAGES["intake.legend.no_factor"][LANG_ZH]
    assert MESSAGES["intake.steel.method.undecided"][LANG_ZH] == "尚不確定"
    assert "Scope" in MESSAGES["intake.steel.form.no_scope"][LANG_ZH]
    assert MESSAGES["intake.steel.answer.included"][LANG_ZH] == "包含"
    assert MESSAGES["intake.steel.answer.excluded"][LANG_ZH] == "不包含"
    assert (
        MESSAGES["intake.field.factor_includes_inbound_transport"][LANG_ZH]
        == "此筆鋼材使用的排放係數，是否包含 Tier 1 供應商到本公司的運輸排放？"
    )
    assert (
        MESSAGES["explain.steel.blocked_tier1_inbound_transport_requires_category4_split"][
            LANG_ZH
        ]
        == (
            "此係數包含由第三方承運的 Tier 1 供應商到本公司運輸。"
            "該段應另列 Scope 3 Category 4；在取得不含該段運輸的鋼材係數"
            "或完成拆分前，本列不計入 Category 1。"
        )
    )
    assert (
        MESSAGES[
            "explain.steel.blocked_company_controlled_transport_requires_scope1_or2_split"
        ][LANG_ZH]
        == (
            "此係數包含由本公司擁有或控制之運輸排放。"
            "該段應依能源來源分別列入 Scope 1 或 Scope 2；"
            "在取得不含該段運輸的鋼材係數或完成拆分前，本列不計入 Category 1。"
        )
    )


def test_unconfirmed_factor_inclusion_stays_needs_confirmation() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    confirmation = _complete_supplier(intake, inbound="")
    errors = validate_confirmation(
        confirmation, current_file_hash=intake.file_hash
    )
    assert ERROR_INBOUND_UNANSWERED in errors
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel.get("calculation_method") or "") == ""


def test_included_transport_with_unknown_control_does_not_calculate() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    confirmation = _complete_supplier(intake, inbound="true", control="")
    errors = validate_confirmation(
        confirmation, current_file_hash=intake.file_hash
    )
    assert ERROR_TRANSPORT_CONTROL_UNANSWERED in errors
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    result = _pipeline(overlaid, intake)
    row = _steel_row(intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] != "calculated"
    assert pd.isna(calc["calculated_tco2e"])
    assert scope3_category1_emissions_summary(result, ZH)["tco2e"] is None


def test_company_controlled_transport_requires_scope1_or2_split() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    confirmation = _complete_supplier(
        intake, inbound="true", control=CONTROL_REPORTING_COMPANY
    )
    assert not validate_confirmation(
        confirmation, current_file_hash=intake.file_hash
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    result = _pipeline(overlaid, intake)
    row = _steel_row(intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == (
        "blocked_company_controlled_transport_requires_scope1_or2_split"
    )
    assert pd.isna(calc["calculated_tco2e"])
    assert scope3_category1_emissions_summary(result, ZH)["tco2e"] is None
    zh = activity_detail_context(result, str(row["record_id"]), ZH)[
        "calculation_explanation"
    ]
    assert "Category 4" not in zh
    assert zh == t(
        "explain.steel.blocked_company_controlled_transport_requires_scope1_or2_split",
        ZH,
    )
    inventory = company_inventory_emissions_summary(result, ZH)
    assert inventory["inventory_tco2e"] in {None, 0.0}


def test_excluded_inbound_clears_stale_third_party_control() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    confirmation = _complete_supplier(
        intake, inbound="false", control=CONTROL_THIRD_PARTY
    )
    assert confirmation.tier1_to_reporting_company_transport_control == (
        CONTROL_NOT_APPLICABLE
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel["tier1_to_reporting_company_transport_control"]) == (
        CONTROL_NOT_APPLICABLE
    )
    result = _pipeline(overlaid, intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == steel["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == "calculated"
    assert float(calc["calculated_tco2e"]) == 18.5


def test_confirmation_ui_does_not_ask_pre_tier1_radio() -> None:
    source = (
        REPO_ROOT / "src" / "carbon_ledger" / "ui" / "purchased_steel_confirmation.py"
    ).read_text(encoding="utf-8")
    assert 'key=_widget_key("pre_tier1"' not in source
    assert "includes_pre_tier1_supply_chain_transport" not in source
    assert "intake.steel.error.pre_tier1" not in source
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    confirmation = _complete_supplier(
        intake, includes_pre_tier1_supply_chain_transport=""
    )
    assert not validate_confirmation(
        confirmation, current_file_hash=intake.file_hash
    )


def test_supplier_specific_can_keep_source_boundary_metadata() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    confirmation = _complete_supplier(
        intake, includes_pre_tier1_supply_chain_transport="true"
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel["includes_pre_tier1_supply_chain_transport"]) == "true"
    result = _pipeline(overlaid, intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == steel["record_id"]
    ].iloc[0]
    assert '"includes_pre_tier1_supply_chain_transport": true' in str(
        calc["calculation_trace"]
    )
    assert "all upstream transport excluded" not in str(
        calc["calculation_reason"]
    ).lower()


def test_average_data_overlay_does_not_write_user_pre_tier1() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    row = _steel_row(intake)
    confirmation = build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=2025,
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="average_data",
        steel_product_type="steel wire rod",
        factor_geography="TW",
        includes_tier1_to_reporting_company_transport="false",
        includes_pre_tier1_supply_chain_transport="true",
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel.get("includes_pre_tier1_supply_chain_transport") or "") != (
        "true"
    )


def test_legacy_session_boolean_is_read_conservatively() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    row = _steel_row(intake)
    blank = PurchasedSteelConfirmation.from_dict(
        {
            "file_hash": intake.file_hash,
            "record_id": str(row["record_id"]),
            "reporting_year": 2025,
            "reporting_period_id": activity_reporting_period_id(row),
            "calculation_method": "supplier_specific",
            "includes_tier1_to_reporting_company_transport": "",
        }
    )
    assert blank.factor_includes_tier1_to_reporting_company_transport == ""
    assert blank.includes_tier1_to_reporting_company_transport == ""
    errors = validate_confirmation(blank, current_file_hash=intake.file_hash)
    assert ERROR_INBOUND_UNANSWERED in errors
    legacy_false = PurchasedSteelConfirmation.from_dict(
        {
            "file_hash": intake.file_hash,
            "record_id": str(row["record_id"]),
            "reporting_year": 2025,
            "reporting_period_id": activity_reporting_period_id(row),
            "calculation_method": "supplier_specific",
            "supplier_name": "Demo Steel Supplier",
            "steel_product_type": "steel wire rod",
            "emission_factor_value": "1.85",
            "emission_factor_unit": "tCO2e/t",
            "factor_boundary": "cradle_to_gate",
            "factor_year": "2025",
            "evidence_reference": "EPD-2025-001",
            "includes_tier1_to_reporting_company_transport": "false",
        }
    )
    assert legacy_false.factor_includes_tier1_to_reporting_company_transport == (
        "false"
    )
    assert not validate_confirmation(
        legacy_false, current_file_hash=intake.file_hash
    )


def test_confirmation_from_another_period_is_not_applied() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    row = _steel_row(intake)
    original_method = str(row.get("calculation_method") or "")
    confirmation = build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=2025,
        reporting_period_id="period-2025-other",
        calculation_method="supplier_specific",
        supplier_name="Demo Steel Supplier",
        steel_product_type="steel wire rod",
        emission_factor_value="1.85",
        emission_factor_unit="tCO2e/t",
        factor_boundary="cradle_to_gate",
        factor_year="2025",
        evidence_reference="EPD-2025-001",
        includes_tier1_to_reporting_company_transport="false",
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    steel = overlaid.loc[overlaid["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel.get("calculation_method") or "") == original_method


def test_blocked_transport_splits_do_not_change_scope_1_and_2() -> None:
    baseline = _intake(
        "外購電力,50000,kWh,2025-01-01,2025-01-31",
        "天然氣,8000,m3,2025-01-01,2025-01-31",
        "柴油,1200,L,2025-01-01,2025-01-31",
    )
    with_steel = _intake(
        "外購電力,50000,kWh,2025-01-01,2025-01-31",
        "天然氣,8000,m3,2025-01-01,2025-01-31",
        "柴油,1200,L,2025-01-01,2025-01-31",
        "採購鋼材,10,t,2025-01-01,2025-12-31",
    )
    confirmation = _complete_supplier(
        with_steel, inbound="true", control=CONTROL_THIRD_PARTY
    )
    overlaid = apply_purchased_steel_confirmations(
        with_steel.accepted_activities,
        [confirmation],
        current_file_hash=with_steel.file_hash,
    )
    base_result = _pipeline(baseline.accepted_activities, baseline)
    steel_result = _pipeline(overlaid, with_steel)
    base_inventory = company_inventory_emissions_summary(base_result, ZH)
    steel_inventory = company_inventory_emissions_summary(steel_result, ZH)
    assert steel_inventory["inventory_tco2e"] == base_inventory["inventory_tco2e"]
    assert steel_inventory["scope_1"] == base_inventory["scope_1"]
    assert steel_inventory["scope_2"] == base_inventory["scope_2"]
    assert scope3_category1_emissions_summary(steel_result, ZH)["tco2e"] is None


def test_average_data_no_factor_stays_editable_and_is_not_unsupported() -> None:
    intake = _intake("採購鋼材,10,t,2025-01-01,2025-12-31")
    row = _steel_row(intake)
    confirmation = build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=2025,
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="average_data",
        steel_product_type="熱軋碳鋼",
        factor_geography="TW",
        includes_tier1_to_reporting_company_transport="false",
        factor_includes_tier1_to_reporting_company_transport="false",
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    result = _pipeline(overlaid, intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == STATUS_NO_MATCHING_FACTOR
    assert pd.isna(calc["calculated_tco2e"])
    status_map = {
        str(row["record_id"]): str(calc["calculation_status"]),
    }
    candidates = steel_confirmation_candidates(
        overlaid, calculation_status_by_record=status_map
    )
    assert len(candidates) == 1
    recon = reconcile_row_dispositions(
        intake_result=intake,
        pipeline_result=result,
        is_uploaded_analysis=True,
    )
    assert recon["counts"][DISPOSITION_NO_MATCHING_FACTOR] == 1
    assert recon["counts"][DISPOSITION_UNSUPPORTED] == 0
    assert recon["counts"][DISPOSITION_NEEDS_CONFIRMATION] == 0
