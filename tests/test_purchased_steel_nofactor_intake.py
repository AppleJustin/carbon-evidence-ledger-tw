"""Regression for purchased-steel no-factor status, edit form, and renderer."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from carbon_ledger.activity_boundary_decisions import reporting_year_from_activity
from carbon_ledger.intake import (
    READINESS_NEEDS_CONFIRM,
    READINESS_NO_MATCHING_FACTOR,
    READINESS_UNSUPPORTED,
    IntakeMetadata,
    build_and_validate_intake,
    classify_activity_analysis_readiness,
    parse_uploaded_table,
    suggest_column_mapping_with_confidence,
)
from carbon_ledger.intake_exceptions import (
    apply_exception,
    hold_unknown_context_rows,
    initialize_committed,
    list_exceptions,
    mapping_from_committed,
)
from carbon_ledger.purchased_steel import (
    CONTROL_NOT_APPLICABLE,
    CONTROL_REPORTING_COMPANY,
    STATUS_NO_MATCHING_FACTOR,
)
from carbon_ledger.purchased_steel_confirmations import (
    activity_reporting_period_id,
    apply_purchased_steel_confirmations,
    build_confirmation,
    steel_confirmation_candidates,
)
from carbon_ledger.ui.i18n import LANG_ZH, t
from carbon_ledger.ui.purchased_steel_confirmation import (
    attach_coverage_readiness,
    pipeline_calculation_status_by_record,
)
from carbon_ledger.ui.state import (
    STATE_INCLUDE_GHG,
    STATE_INCLUDE_IFRS,
    STATE_INTAKE_COMMITTED,
    STATE_INTAKE_FILE_HASH,
    STATE_INTAKE_FILE_NAME,
    STATE_INTAKE_MAPPING,
    STATE_INTAKE_METADATA,
    STATE_INTAKE_RESULT,
    STATE_INTAKE_TABLE,
    STATE_LANGUAGE,
    STATE_PURCHASED_STEEL_CONFIRMATIONS,
    initialize_ui_state,
    purchased_steel_confirmations_from_state,
    run_uploaded_analysis,
    save_purchased_steel_confirmation_in_session,
)
from carbon_ledger.ui.view_models import (
    DISPOSITION_NO_MATCHING_FACTOR,
    DISPOSITION_UNSUPPORTED,
    company_inventory_emissions_summary,
    company_inventory_record_ids,
    reconcile_row_dispositions,
    scope3_category1_emissions_summary,
    scope3_emissions_summary,
    scope_kpi_states,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
XLSX_PATH = Path(
    "/Users/justin/Downloads/carbon-ledger-mixed-factor-validity-test.xlsx"
)
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00Z")
ZH = LANG_ZH
SCOPE1 = 45.950836
SCOPE2 = 23.30
INVENTORY = 69.250836


def _apply_named(table, detailed, committed, item_id: str, payload: dict):
    item = next(
        row
        for row in list_exceptions(table, detailed, committed)
        if row.item_id == item_id
    )
    return apply_exception(committed, item, payload)


def _load_xlsx_intake():
    table = parse_uploaded_table(
        file_name=XLSX_PATH.name, data=XLSX_PATH.read_bytes()
    )
    detailed = suggest_column_mapping_with_confidence(
        list(table.columns), frame=table.frame
    )
    committed = initialize_committed(table, detailed)
    committed = _apply_named(
        table,
        detailed,
        committed,
        "column:activity_value",
        {"column": "用量", "table": table},
    )
    committed = _apply_named(
        table,
        detailed,
        committed,
        "context:electricity",
        {"value": "enterprise"},
    )
    mapping = mapping_from_committed(table, committed)
    meta = IntakeMetadata(
        source_name=table.file_name,
        site_id="UNKNOWN",
        document_date=date(2025, 5, 31),
        data_quality_tier="unknown",
        intake_run_id="steel_nofactor",
        ingested_at=FIXED_INGESTED_AT,
    )
    intake = hold_unknown_context_rows(
        build_and_validate_intake(table, mapping, meta), mapping
    )
    return table, detailed, committed, mapping, meta, intake


def _session(table, committed, mapping, meta, intake) -> dict:
    state: dict = {}
    initialize_ui_state(state)
    state[STATE_LANGUAGE] = ZH
    state[STATE_INCLUDE_GHG] = True
    state[STATE_INCLUDE_IFRS] = True
    state[STATE_INTAKE_TABLE] = table
    state[STATE_INTAKE_FILE_HASH] = intake.file_hash
    state[STATE_INTAKE_FILE_NAME] = intake.file_name
    state[STATE_INTAKE_COMMITTED] = committed
    state[STATE_INTAKE_MAPPING] = mapping
    state[STATE_INTAKE_METADATA] = meta
    state[STATE_INTAKE_RESULT] = intake
    return state


def _steel_row(intake) -> pd.Series:
    accepted = intake.accepted_activities
    return accepted.loc[accepted["activity_type"] == "purchased_steel"].iloc[0]


def _plate_confirmation(intake):
    row = _steel_row(intake)
    year = reporting_year_from_activity(row)
    return build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=int(year or 2025),
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="average_data",
        steel_product_type="鋼板",
        product_identifier="鋼板",
        factor_geography="TW",
        factor_includes_tier1_to_reporting_company_transport="false",
        includes_tier1_to_reporting_company_transport="false",
    )


def _blocked_plate_confirmation(intake):
    row = _steel_row(intake)
    year = reporting_year_from_activity(row)
    return build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=int(year or 2025),
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="average_data",
        steel_product_type="鋼板",
        product_identifier="鋼板",
        factor_geography="TW",
        factor_includes_tier1_to_reporting_company_transport="true",
        includes_tier1_to_reporting_company_transport="true",
        tier1_to_reporting_company_transport_control=CONTROL_REPORTING_COMPANY,
    )


def _average_confirmation(intake):
    row = _steel_row(intake)
    year = reporting_year_from_activity(row)
    return build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=int(year or 2025),
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="average_data",
        steel_product_type="熱軋碳鋼",
        factor_geography="TW",
        factor_includes_tier1_to_reporting_company_transport="false",
        includes_tier1_to_reporting_company_transport="false",
    )


def _supplier_confirmation(intake):
    row = _steel_row(intake)
    year = reporting_year_from_activity(row)
    return build_confirmation(
        file_hash=intake.file_hash,
        record_id=str(row["record_id"]),
        reporting_year=int(year or 2025),
        reporting_period_id=activity_reporting_period_id(row),
        calculation_method="supplier_specific",
        supplier_name="測試鋼鐵供應商",
        steel_product_type="熱軋碳鋼",
        emission_factor_value="1.85",
        emission_factor_unit="tCO2e/t",
        factor_boundary="cradle_to_gate",
        factor_year="2023",
        factor_source_id="supplier-epd-test-2023",
        evidence_reference="測試用供應商 EPD",
        factor_includes_tier1_to_reporting_company_transport="false",
        includes_tier1_to_reporting_company_transport="false",
    )


def _statuses(result) -> dict[str, str]:
    calcs = result.calculation_results
    activities = result.activity_records_accepted
    merged = activities.merge(
        calcs[["record_id", "calculation_status", "calculated_tco2e"]],
        on="record_id",
        how="left",
    )
    out: dict[str, str] = {}
    for _, row in merged.iterrows():
        key = f"{row['activity_type']}:{row['record_id']}"
        out[key] = str(row["calculation_status"])
    return out


def _all_text(at: AppTest) -> str:
    chunks: list[str] = []
    for name in (
        "markdown",
        "text",
        "caption",
        "info",
        "warning",
        "success",
        "error",
    ):
        collection = getattr(at, name, None)
        if collection is None:
            continue
        for item in collection:
            value = getattr(item, "value", None)
            if value is not None:
                chunks.append(str(value))
            body = getattr(item, "body", None)
            if body is not None:
                chunks.append(str(body))
    for button in at.button:
        label = getattr(button, "label", None)
        if label is not None:
            chunks.append(str(label))
    for name in ("table", "dataframe"):
        collection = getattr(at, name, None)
        if collection is None:
            continue
        for item in collection:
            value = getattr(item, "value", None)
            if value is not None:
                chunks.append(str(value))
    return "\n".join(chunks)


def test_xlsx_missing_method_is_needs_confirmation() -> None:
    _table, _detailed, _committed, _mapping, _meta, intake = _load_xlsx_intake()
    row = _steel_row(intake)
    assert (
        classify_activity_analysis_readiness(
            activity_type="purchased_steel",
            fuel_subtype="",
            process_use="",
            activity_start=row["activity_start_date"],
            activity_end=row["activity_end_date"],
        )
        == READINESS_NEEDS_CONFIRM
    )
    candidates = steel_confirmation_candidates(intake.accepted_activities)
    assert len(candidates) == 1
    classified = attach_coverage_readiness(intake.accepted_activities)
    steel = classified.loc[classified["activity_type"] == "purchased_steel"]
    assert str(steel.iloc[0]["_analysis_readiness"]) == READINESS_NEEDS_CONFIRM
    assert READINESS_UNSUPPORTED not in set(steel["_analysis_readiness"])


def test_xlsx_average_data_no_factor_is_not_unsupported() -> None:
    table, _detailed, committed, mapping, meta, intake = _load_xlsx_intake()
    confirmation = _average_confirmation(intake)
    state = _session(table, committed, mapping, meta, intake)
    save_purchased_steel_confirmation_in_session(state, confirmation)
    before = run_uploaded_analysis(
        state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id="steel_nofactor_before",
        repo_root=REPO_ROOT,
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    after_state = _session(table, committed, mapping, meta, intake)
    save_purchased_steel_confirmation_in_session(after_state, confirmation)
    result = run_uploaded_analysis(
        after_state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id="steel_nofactor_avg",
        repo_root=REPO_ROOT,
    )
    row = _steel_row(intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == STATUS_NO_MATCHING_FACTOR
    assert pd.isna(calc["calculated_tco2e"])
    status_map = pipeline_calculation_status_by_record(result)
    classified = attach_coverage_readiness(
        overlaid, calculation_status_by_record=status_map
    )
    steel = classified.loc[classified["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel["_analysis_readiness"]) == READINESS_NO_MATCHING_FACTOR
    assert str(steel["_analysis_readiness"]) != READINESS_UNSUPPORTED
    candidates = steel_confirmation_candidates(
        overlaid, calculation_status_by_record=status_map
    )
    assert len(candidates) == 1
    recon = reconcile_row_dispositions(
        uploaded_table=table,
        intake_result=intake,
        pipeline_result=result,
        is_uploaded_analysis=True,
    )
    assert recon["counts"][DISPOSITION_NO_MATCHING_FACTOR] == 1
    assert recon["counts"][DISPOSITION_UNSUPPORTED] == 0
    inventory = company_inventory_emissions_summary(result, ZH)
    before_inv = company_inventory_emissions_summary(before, ZH)
    assert float(inventory["scope_1"]) == pytest.approx(
        float(before_inv["scope_1"]), abs=1e-6
    )
    assert float(inventory["scope_2"]) == pytest.approx(
        float(before_inv["scope_2"]), abs=1e-6
    )
    assert float(inventory["inventory_tco2e"]) == pytest.approx(
        float(before_inv["inventory_tco2e"]), abs=1e-6
    )
    assert float(inventory["inventory_tco2e"]) == pytest.approx(INVENTORY, abs=1e-4)
    other_before = {
        key: value
        for key, value in _statuses(before).items()
        if not key.startswith("purchased_steel:")
    }
    other_after = {
        key: value
        for key, value in _statuses(result).items()
        if not key.startswith("purchased_steel:")
    }
    assert other_before == other_after


def test_xlsx_switch_to_supplier_specific_is_18_5_category_1() -> None:
    table, _detailed, committed, mapping, meta, intake = _load_xlsx_intake()
    avg_state = _session(table, committed, mapping, meta, intake)
    save_purchased_steel_confirmation_in_session(
        avg_state, _average_confirmation(intake)
    )
    before = run_uploaded_analysis(
        avg_state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id="steel_nofactor_pre_switch",
        repo_root=REPO_ROOT,
    )
    before_inv = company_inventory_emissions_summary(before, ZH)
    state = _session(table, committed, mapping, meta, intake)
    save_purchased_steel_confirmation_in_session(
        state, _supplier_confirmation(intake)
    )
    result = run_uploaded_analysis(
        state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id="steel_nofactor_supplier",
        repo_root=REPO_ROOT,
    )
    row = _steel_row(intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == "calculated"
    assert float(calc["calculated_tco2e"]) == pytest.approx(18.5, abs=1e-9)
    assert str(calc.get("ghg_scope") or "") == "scope_3"
    assert str(calc.get("scope_3_category") or "") == "category_1"
    cat1 = scope3_category1_emissions_summary(result, ZH)
    assert cat1["tco2e"] == pytest.approx(18.5, abs=1e-9)
    inventory = company_inventory_emissions_summary(result, ZH)
    assert float(inventory["scope_1"]) == pytest.approx(
        float(before_inv["scope_1"]), abs=1e-6
    )
    assert float(inventory["scope_2"]) == pytest.approx(
        float(before_inv["scope_2"]), abs=1e-6
    )
    assert float(inventory["inventory_tco2e"]) == pytest.approx(
        float(before_inv["inventory_tco2e"]), abs=1e-6
    )
    assert float(inventory["scope_1"]) == pytest.approx(SCOPE1, abs=1e-4)
    assert float(inventory["scope_2"]) == pytest.approx(SCOPE2, abs=0.005)
    detail = str(calc.get("calculation_reason") or "")
    assert "verified" not in detail.lower()
    assert "assured" not in detail.lower()
    assert "認證" not in detail
    assert "已驗證" not in detail
    other_before = {
        key: value
        for key, value in _statuses(before).items()
        if not key.startswith("purchased_steel:")
    }
    other_after = {
        key: value
        for key, value in _statuses(result).items()
        if not key.startswith("purchased_steel:")
    }
    assert other_before == other_after


def test_confirmation_does_not_reuse_other_identity() -> None:
    _table, _detailed, _committed, _mapping, _meta, intake = _load_xlsx_intake()
    row = _steel_row(intake)
    year = int(reporting_year_from_activity(row) or 2025)
    period = activity_reporting_period_id(row)
    original = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [
            build_confirmation(
                file_hash="other-upload-hash",
                record_id=str(row["record_id"]),
                reporting_year=year,
                reporting_period_id=period,
                calculation_method="average_data",
                steel_product_type="熱軋碳鋼",
                factor_geography="TW",
                factor_includes_tier1_to_reporting_company_transport="false",
            )
        ],
        current_file_hash=intake.file_hash,
    )
    steel = original.loc[original["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel.get("calculation_method") or "") == ""
    other_record = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [
            build_confirmation(
                file_hash=intake.file_hash,
                record_id="other-record",
                reporting_year=year,
                reporting_period_id=period,
                calculation_method="average_data",
                steel_product_type="熱軋碳鋼",
                factor_geography="TW",
                factor_includes_tier1_to_reporting_company_transport="false",
            )
        ],
        current_file_hash=intake.file_hash,
    )
    steel = other_record.loc[
        other_record["activity_type"] == "purchased_steel"
    ].iloc[0]
    assert str(steel.get("calculation_method") or "") == ""
    other_year = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [
            build_confirmation(
                file_hash=intake.file_hash,
                record_id=str(row["record_id"]),
                reporting_year=year + 1,
                reporting_period_id=period,
                calculation_method="average_data",
                steel_product_type="熱軋碳鋼",
                factor_geography="TW",
                factor_includes_tier1_to_reporting_company_transport="false",
            )
        ],
        current_file_hash=intake.file_hash,
    )
    steel = other_year.loc[other_year["activity_type"] == "purchased_steel"].iloc[0]
    assert str(steel.get("calculation_method") or "") == ""
    other_period = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [
            build_confirmation(
                file_hash=intake.file_hash,
                record_id=str(row["record_id"]),
                reporting_year=year,
                reporting_period_id="period-other",
                calculation_method="average_data",
                steel_product_type="熱軋碳鋼",
                factor_geography="TW",
                factor_includes_tier1_to_reporting_company_transport="false",
            )
        ],
        current_file_hash=intake.file_hash,
    )
    steel = other_period.loc[
        other_period["activity_type"] == "purchased_steel"
    ].iloc[0]
    assert str(steel.get("calculation_method") or "") == ""


def test_coverage_renderer_average_no_factor_does_not_raise() -> None:
    table, _detailed, committed, mapping, meta, intake = _load_xlsx_intake()
    confirmation = _average_confirmation(intake)
    state = _session(table, committed, mapping, meta, intake)
    save_purchased_steel_confirmation_in_session(state, confirmation)
    result = run_uploaded_analysis(
        state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id="steel_nofactor_render",
        repo_root=REPO_ROOT,
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    status_map = pipeline_calculation_status_by_record(result)
    harness = Path(__file__).resolve().parent / "steel_coverage_review_harness.py"
    at = AppTest.from_file(str(harness), default_timeout=120)
    for key, value in state.items():
        at.session_state[key] = value
    at.session_state["steel_review_accepted"] = overlaid
    at.session_state["steel_review_lang"] = ZH
    at.session_state["steel_review_status"] = status_map
    at.session_state["steel_review_result"] = result
    at.run()
    assert not at.exception
    text = _all_text(at)
    assert t("intake.issue.steel_average_no_factor", ZH) in text
    assert t("intake.steel.save", ZH) in text or t("intake.steel.edit", ZH) in text
    assert t("intake.issue.unsupported_activity", ZH) not in text
    assert "Traceback" not in text


def test_coverage_form_can_select_catalog_product_and_reanalyse() -> None:
    table, _detailed, committed, mapping, meta, intake = _load_xlsx_intake()
    confirmation = _average_confirmation(intake)
    state = _session(table, committed, mapping, meta, intake)
    save_purchased_steel_confirmation_in_session(state, confirmation)
    result = run_uploaded_analysis(
        state,
        include_ghg=True,
        include_ifrs_s2=False,
        run_id="steel_select_product",
        repo_root=REPO_ROOT,
    )
    overlaid = apply_purchased_steel_confirmations(
        intake.accepted_activities,
        [confirmation],
        current_file_hash=intake.file_hash,
    )
    harness = Path(__file__).resolve().parent / "steel_coverage_review_harness.py"
    at = AppTest.from_file(str(harness), default_timeout=120)
    for key, value in state.items():
        at.session_state[key] = value
    at.session_state["steel_review_accepted"] = overlaid
    at.session_state["steel_review_lang"] = ZH
    at.session_state["steel_review_status"] = pipeline_calculation_status_by_record(
        result
    )
    at.session_state["steel_review_result"] = result
    at.run()
    assert not at.exception
    product_boxes = [
        box
        for box in at.selectbox
        if "鋼板" in [str(option) for option in getattr(box, "options", [])]
    ]
    assert product_boxes, "product type selectbox should list catalog/taxonomy names"
    box = product_boxes[0]
    if hasattr(box, "select"):
        box.select("鋼板")
    elif hasattr(box, "set_value"):
        box.set_value("鋼板")
    else:
        box.select_index([str(option) for option in box.options].index("鋼板"))
    save_buttons = [
        button
        for button in at.button
        if t("intake.steel.save", ZH) in str(getattr(button, "label", ""))
    ]
    assert save_buttons
    save_buttons[0].click()
    at.run()
    assert not at.exception
    text = _all_text(at)
    assert t("intake.issue.unsupported_activity", ZH) not in text
    assert "目前產品不支援" not in text
    assert "Traceback" not in text


def _cell(row: pd.Series, column: str) -> str:
    if column not in row.index:
        return ""
    value = row.get(column)
    try:
        if value is None or pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _row_snapshot(result) -> list[dict[str, object]]:
    activities = result.activity_records_accepted.copy()
    calcs = result.calculation_results.copy()
    ghg = result.ghg_evaluations.copy()
    merged = activities.merge(
        calcs,
        on="record_id",
        how="left",
        suffixes=("", "_calc"),
    )
    if not ghg.empty:
        keep = [
            column
            for column in (
                "record_id",
                "mapping_status",
                "ghg_scope",
                "scope_3_category",
            )
            if column in ghg.columns
        ]
        overlap = [
            column
            for column in keep
            if column != "record_id" and column in merged.columns
        ]
        if overlap:
            merged = merged.drop(columns=overlap)
        merged = merged.merge(ghg[keep], on="record_id", how="left")
    included = company_inventory_record_ids(result)
    rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        record_id = _cell(row, "record_id")
        tco2e = row["calculated_tco2e"] if "calculated_tco2e" in row.index else None
        numeric = None
        try:
            if tco2e is not None and not pd.isna(tco2e):
                numeric = float(tco2e)
        except (TypeError, ValueError):
            numeric = None
        in_inventory = record_id in included
        reason = ""
        if not in_inventory:
            status = _cell(row, "calculation_status")
            mapping = _cell(row, "mapping_status")
            scope = _cell(row, "ghg_scope")
            if status != "calculated":
                reason = status or "not_calculated"
            elif mapping != "mapped":
                reason = mapping or "unmapped"
            elif scope not in {"scope_1", "scope_2"}:
                reason = f"{scope}:{_cell(row, 'scope_3_category')}"
            else:
                reason = "excluded_from_inventory"
        rows.append(
            {
                "activity_type": _cell(row, "activity_type"),
                "calculation_status": _cell(row, "calculation_status"),
                "mapping_status": _cell(row, "mapping_status"),
                "ghg_scope": _cell(row, "ghg_scope"),
                "scope_3_category": _cell(row, "scope_3_category"),
                "factor_id": _cell(row, "factor_id"),
                "factor_version": _cell(row, "factor_version"),
                "factor_source_id": _cell(row, "factor_source_id"),
                "calculated_tco2e": numeric,
                "in_scope12_inventory": in_inventory,
                "excluded_reason": reason,
            }
        )
    return rows


def _activity_snapshot(rows: list[dict[str, object]], activity_type: str) -> list[dict]:
    return [row for row in rows if row["activity_type"] == activity_type]


def test_xlsx_row_level_acceptance_without_active_steel_factor() -> None:
    table, _detailed, committed, mapping, meta, intake = _load_xlsx_intake()
    confirmation = _average_confirmation(intake)
    state = _session(table, committed, mapping, meta, intake)
    save_purchased_steel_confirmation_in_session(state, confirmation)
    result = run_uploaded_analysis(
        state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id="xlsx_row_acceptance",
        repo_root=REPO_ROOT,
    )
    rows = _row_snapshot(result)
    electricity = _activity_snapshot(rows, "grid_electricity")
    assert len(electricity) == 1
    assert electricity[0]["calculation_status"] == "calculated"
    assert electricity[0]["ghg_scope"] == "scope_2"
    assert electricity[0]["in_scope12_inventory"] is True
    assert electricity[0]["calculated_tco2e"] == pytest.approx(23.30, abs=1e-4)

    gas = _activity_snapshot(rows, "natural_gas")
    assert len(gas) == 1
    assert gas[0]["calculation_status"] == "calculated"
    assert gas[0]["ghg_scope"] == "scope_1"
    assert gas[0]["in_scope12_inventory"] is True
    assert gas[0]["calculated_tco2e"] == pytest.approx(16.416157, abs=1e-5)

    diesel = _activity_snapshot(rows, "diesel")
    assert len(diesel) == 1
    assert diesel[0]["calculation_status"] == "calculated"
    assert diesel[0]["ghg_scope"] == "scope_1"
    assert diesel[0]["in_scope12_inventory"] is True
    assert diesel[0]["calculated_tco2e"] == pytest.approx(3.264679, abs=1e-5)

    refrigerants = [
        row
        for row in rows
        if str(row["activity_type"]).startswith("refrigerant")
    ]
    assert len(refrigerants) == 4
    included_ref = [row for row in refrigerants if row["in_scope12_inventory"]]
    excluded_ref = [row for row in refrigerants if not row["in_scope12_inventory"]]
    assert len(included_ref) == 2
    included_total = sum(float(row["calculated_tco2e"] or 0) for row in included_ref)
    assert included_total == pytest.approx(19.5 + 6.77, abs=1e-4)
    excluded_values = sorted(
        float(row["calculated_tco2e"] or 0) for row in excluded_ref
    )
    assert excluded_values[0] == pytest.approx(2.031, abs=1e-3)
    assert excluded_values[1] == pytest.approx(3.847, abs=1e-3)

    steel = _activity_snapshot(rows, "purchased_steel")
    assert len(steel) == 1
    assert steel[0]["calculation_status"] == STATUS_NO_MATCHING_FACTOR
    assert steel[0]["ghg_scope"] == "scope_3"
    assert "category_1" in str(steel[0]["scope_3_category"])
    assert steel[0]["calculated_tco2e"] is None
    assert steel[0]["in_scope12_inventory"] is False
    assert steel[0]["factor_id"] == ""

    inventory = company_inventory_emissions_summary(result, ZH)
    assert float(inventory["scope_1"]) == pytest.approx(SCOPE1, abs=1e-5)
    assert float(inventory["scope_2"]) == pytest.approx(SCOPE2, abs=1e-4)
    assert float(inventory["inventory_tco2e"]) == pytest.approx(INVENTORY, abs=1e-4)
    cat1 = scope3_category1_emissions_summary(result, ZH)
    assert cat1["row_count"] == 0
    assert cat1["tco2e"] is None
    states = scope_kpi_states(result, ZH)
    assert states["scope_3"]["state"] == "empty"
    assert states["scope_3"]["value"] is None
    assert "目前尚無可納入的 Scope 3 計算結果" in str(states["scope_3"]["caption"])

    contrib = __import__(
        "carbon_ledger.ui.charts", fromlist=["calculated_emissions_contributions"]
    ).calculated_emissions_contributions(result, ZH)
    names = set(contrib["activity_name"].astype(str))
    assert any("電力" in name or "electricity" in name.lower() for name in names)
    assert any("天然氣" in name or "natural" in name.lower() for name in names)
    assert any("柴油" in name or "diesel" in name.lower() for name in names)
    assert any("冷媒" in name or "refrigerant" in name.lower() for name in names)
    assert not any("鋼" in name for name in names)


def test_xlsx_steel_plate_average_data_is_24_15() -> None:
    table, _detailed, committed, mapping, meta, intake = _load_xlsx_intake()
    confirmation = _plate_confirmation(intake)
    state = _session(table, committed, mapping, meta, intake)
    save_purchased_steel_confirmation_in_session(state, confirmation)
    result = run_uploaded_analysis(
        state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id="xlsx_steel_plate_2415",
        repo_root=REPO_ROOT,
    )
    row = _steel_row(intake)
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == row["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == "calculated"
    assert float(calc["purchased_quantity"]) == pytest.approx(10.0)
    assert str(calc["purchased_unit"]) in {"t", "tonne"}
    assert float(calc["calculated_kgco2e"]) == pytest.approx(24150.0, abs=1e-6)
    assert float(calc["calculated_tco2e"]) == pytest.approx(24.15, abs=1e-6)
    assert float(calc["factor_value"]) == pytest.approx(2.415, abs=1e-9)
    assert str(calc["steel_product_type"]) == "鋼板"
    assert str(calc.get("official_name") or "鋼板") == "鋼板"
    assert str(calc["ghg_scope"]) == "scope_3"
    assert "category_1" in str(calc["scope_3_category"])
    assert str(calc["factor_id"])
    assert str(calc["snapshot_hash"])
    assert str(calc["source_url"])
    assert "api_key" not in str(calc["source_url"])
    steel_href = str(calc["source_url"])
    assert "sort=" in steel_href
    assert "ImportDate%20desc" in steel_href or "ImportDate+desc" in steel_href
    assert "format=JSON" in steel_href
    assert str(calc["announcement_year"]) == "2013"
    assert "中國鋼鐵" in str(calc["publisher"])
    ghg = result.ghg_evaluations.loc[
        result.ghg_evaluations["record_id"] == row["record_id"]
    ].iloc[0]
    assert str(ghg["mapping_status"]) == "mapped"
    inventory = company_inventory_emissions_summary(result, ZH)
    assert float(inventory["scope_1"]) == pytest.approx(SCOPE1, abs=1e-5)
    assert float(inventory["scope_2"]) == pytest.approx(SCOPE2, abs=1e-4)
    assert float(inventory["inventory_tco2e"]) == pytest.approx(INVENTORY, abs=1e-4)
    cat1 = scope3_category1_emissions_summary(result, ZH)
    assert cat1["row_count"] == 1
    assert float(cat1["tco2e"]) == pytest.approx(24.15, abs=1e-6)
    assert cat1["rows"][0]["official_name"] == "鋼板"
    assert cat1["rows"][0]["snapshot_hash"]
    assert cat1["rows"][0]["source_url"]
    cat1_href = str(cat1["rows"][0]["source_url"])
    assert "api_key" not in cat1_href
    assert "sort=" in cat1_href
    assert "ImportDate%20desc" in cat1_href or "ImportDate+desc" in cat1_href
    assert "format=JSON" in cat1_href
    assert cat1["rows"][0]["factor_year"] == "2013"
    assert cat1["rows"][0]["factor_year"] != "2013.0"
    states = scope_kpi_states(result, ZH)
    scope3 = scope3_emissions_summary(result, ZH)
    assert states["scope_3"]["state"] == "calculated"
    assert float(states["scope_3"]["value"]) == pytest.approx(24.15, abs=1e-6)
    assert float(scope3["tco2e"] or 0) == pytest.approx(float(cat1["tco2e"] or 0))
    assert scope3["row_count"] == cat1["row_count"]
    assert "category_1" in scope3["categories"]
    assert "目前已計算 24.15 tCO2e" in str(states["scope_3"]["caption"])
    assert "Category 1－採購商品與服務" in str(states["scope_3"]["caption"])
    assert "尚未納入計算" not in str(states["scope_3"]["caption"])
    steel_ids = company_inventory_record_ids(result)
    assert str(row["record_id"]) not in steel_ids
    assert float(inventory["inventory_tco2e"]) == pytest.approx(INVENTORY, abs=1e-4)
    assert float(inventory["inventory_tco2e"]) != pytest.approx(
        INVENTORY + 24.15, abs=1e-4
    )


def test_wrong_then_correct_replaces_one_row_and_calculates_plate() -> None:
    table, _detailed, committed, mapping, meta, intake = _load_xlsx_intake()
    state = _session(table, committed, mapping, meta, intake)
    wrong = _blocked_plate_confirmation(intake)
    corrected = build_confirmation(
        **{
            **wrong.to_dict(),
            "factor_includes_tier1_to_reporting_company_transport": "false",
            "includes_tier1_to_reporting_company_transport": "false",
        }
    )
    save_purchased_steel_confirmation_in_session(state, wrong)
    save_purchased_steel_confirmation_in_session(state, corrected)
    confirmations = purchased_steel_confirmations_from_state(state)
    assert len(confirmations) == 1
    assert len(state[STATE_PURCHASED_STEEL_CONFIRMATIONS]) == 1
    assert confirmations[0].steel_product_type == "鋼板"
    assert confirmations[0].tier1_to_reporting_company_transport_control == (
        CONTROL_NOT_APPLICABLE
    )

    result = run_uploaded_analysis(
        state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id="xlsx_steel_wrong_then_correct",
        repo_root=REPO_ROOT,
    )
    steel_activities = result.activity_records_accepted.loc[
        result.activity_records_accepted["activity_type"] == "purchased_steel"
    ]
    assert len(steel_activities) == 1
    calc = result.calculation_results.loc[
        result.calculation_results["record_id"] == steel_activities.iloc[0]["record_id"]
    ].iloc[0]
    assert calc["factor_id"] == "ef_steel_鋼板_2013_v1"
    assert float(calc["calculated_tco2e"]) == pytest.approx(24.15, abs=1e-6)
    cat1 = scope3_category1_emissions_summary(result, ZH)
    assert cat1["row_count"] == 1
    assert float(cat1["tco2e"]) == pytest.approx(24.15, abs=1e-6)
    inventory = company_inventory_emissions_summary(result, ZH)
    assert float(inventory["scope_1"]) == pytest.approx(SCOPE1, abs=1e-5)
    assert float(inventory["scope_2"]) == pytest.approx(SCOPE2, abs=1e-4)
    assert float(inventory["inventory_tco2e"]) == pytest.approx(INVENTORY, abs=1e-4)


def test_missing_average_product_stays_on_form_without_clearing_result() -> None:
    from carbon_ledger.ui.state import (
        STATE_INTAKE_STEP,
        STATE_RESULT,
        STATE_RUN_UPLOADED_REQUEST,
    )

    app_path = REPO_ROOT / "streamlit_app.py"
    table, _detailed, committed, mapping, meta, intake = _load_xlsx_intake()
    state = _session(table, committed, mapping, meta, intake)
    existing_result = run_uploaded_analysis(
        state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id="xlsx_missing_product_existing_result",
        repo_root=REPO_ROOT,
    )
    at = AppTest.from_file(str(app_path), default_timeout=120)
    at.run()
    for key, value in state.items():
        at.session_state[key] = value
    at.session_state[STATE_INTAKE_STEP] = 3
    at.switch_page("app_pages/data_intake.py")
    at.run()
    assert not at.exception

    method_radios = [
        radio
        for radio in at.radio
        if t("intake.steel.method.average_data", ZH)
        in [str(option) for option in radio.options]
    ]
    assert len(method_radios) == 1
    method_radios[0].set_value(t("intake.steel.method.average_data", ZH))
    at.run()
    assert not at.exception
    product_boxes = [
        box for box in at.selectbox if "鋼板" in [str(option) for option in box.options]
    ]
    assert len(product_boxes) == 1
    assert product_boxes[0].value == "其他／尚不確定"
    inbound_radios = [
        radio
        for radio in at.radio
        if t("intake.steel.answer.included", ZH)
        in [str(option) for option in radio.options]
    ]
    assert len(inbound_radios) == 1
    inbound_radios[0].set_value(t("intake.steel.answer.included", ZH))
    at.run()
    control_radios = [
        radio
        for radio in at.radio
        if t("intake.steel.control.reporting_company", ZH)
        in [str(option) for option in radio.options]
    ]
    assert len(control_radios) == 1
    control_radios[0].set_value(
        t("intake.steel.control.reporting_company", ZH)
    )
    at.run()
    save_buttons = [
        button
        for button in at.button
        if button.label == t("intake.steel.save", ZH)
    ]
    assert len(save_buttons) == 1
    save_buttons[0].click()
    at.run()
    assert not at.exception
    assert t("intake.steel.error.product", ZH) in _all_text(at)
    assert at.session_state[STATE_INTAKE_STEP] == 3
    assert at.session_state[STATE_RESULT] is existing_result
    assert at.session_state[STATE_RUN_UPLOADED_REQUEST] is False
    assert len(
        at.session_state[STATE_PURCHASED_STEEL_CONFIRMATIONS]
    ) == 0
    assert len(
        [
            radio
            for radio in at.radio
            if t("intake.steel.method.average_data", ZH)
            in [str(option) for option in radio.options]
        ]
    ) == 1


def test_apptest_wrong_transport_then_correct_plate_and_dashboard() -> None:
    from carbon_ledger.ui.state import (
        STATE_INTAKE_STEP,
        STATE_RESULT,
    )

    app_path = REPO_ROOT / "streamlit_app.py"
    at = AppTest.from_file(str(app_path), default_timeout=120)
    at.run()
    at.switch_page("app_pages/data_intake.py")
    at.run()
    assert not at.exception
    assert len(at.file_uploader) == 1
    at.file_uploader[0].upload(
        XLSX_PATH.name,
        XLSX_PATH.read_bytes(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    at.run()
    assert not at.exception
    assert at.session_state[STATE_INTAKE_FILE_NAME] == XLSX_PATH.name

    table, _detailed, committed, mapping, meta, intake = _load_xlsx_intake()
    seeded = _session(table, committed, mapping, meta, intake)
    for key, value in seeded.items():
        at.session_state[key] = value
    at.session_state[STATE_INTAKE_STEP] = 3
    at.session_state[STATE_LANGUAGE] = ZH
    at.run()
    assert not at.exception

    method_radios = [
        radio
        for radio in at.radio
        if t("intake.steel.method.average_data", ZH)
        in [str(option) for option in radio.options]
    ]
    assert len(method_radios) == 1
    method_radios[0].set_value(t("intake.steel.method.average_data", ZH))
    at.run()
    product_boxes = [
        box for box in at.selectbox if "鋼板" in [str(option) for option in box.options]
    ]
    assert len(product_boxes) == 1
    product_boxes[0].select("鋼板")
    at.run()
    assert product_boxes[0].value == "鋼板"
    inbound_radios = [
        radio
        for radio in at.radio
        if t("intake.steel.answer.included", ZH)
        in [str(option) for option in radio.options]
    ]
    assert len(inbound_radios) == 1
    inbound_radios[0].set_value(t("intake.steel.answer.included", ZH))
    at.run()
    control_radios = [
        radio
        for radio in at.radio
        if t("intake.steel.control.reporting_company", ZH)
        in [str(option) for option in radio.options]
    ]
    assert len(control_radios) == 1
    control_radios[0].set_value(
        t("intake.steel.control.reporting_company", ZH)
    )
    at.run()
    save_buttons = [
        button
        for button in at.button
        if button.label == t("intake.steel.save", ZH)
    ]
    assert len(save_buttons) == 1
    save_buttons[0].click()
    at.run()
    assert not at.exception

    wrong_saved = purchased_steel_confirmations_from_state(at.session_state)
    assert len(wrong_saved) == 1
    assert wrong_saved[0].steel_product_type == "鋼板"
    assert wrong_saved[0].tier1_to_reporting_company_transport_control == (
        CONTROL_REPORTING_COMPANY
    )
    wrong_result = at.session_state[STATE_RESULT]
    wrong_steel = wrong_result.activity_records_accepted.loc[
        wrong_result.activity_records_accepted["activity_type"] == "purchased_steel"
    ]
    assert len(wrong_steel) == 1
    wrong_calc = wrong_result.calculation_results.loc[
        wrong_result.calculation_results["record_id"]
        == wrong_steel.iloc[0]["record_id"]
    ].iloc[0]
    assert wrong_calc["calculation_status"] == (
        "blocked_company_controlled_transport_requires_scope1_or2_split"
    )
    # AppTest needs the programmatically selected page made explicit before
    # the next interaction; a browser follows st.switch_page automatically.
    at.switch_page("app_pages/dashboard.py")
    at.run()
    assert not at.exception
    dashboard_text = _all_text(at)
    assert t("intake.steel.save", ZH) not in dashboard_text
    assert t("boundary.confirm.title", ZH) not in dashboard_text
    assert not [
        radio
        for radio in at.radio
        if t("intake.steel.method.average_data", ZH)
        in [str(option) for option in radio.options]
    ]
    return_buttons = [
        button
        for button in at.button
        if button.label == t("dash.cta.edit_emissions_data", ZH)
    ]
    assert len(return_buttons) == 1
    return_buttons[0].click()
    at.run()
    assert not at.exception
    assert at.session_state[STATE_INTAKE_STEP] == 3
    at.switch_page("app_pages/data_intake.py")
    at.run()
    assert not at.exception
    assert at.session_state[STATE_INTAKE_STEP] == 3
    intake_text = _all_text(at)
    assert t("boundary.confirm.title", ZH) in intake_text
    assert (
        t(
            "explain.steel.blocked_company_controlled_transport_requires_scope1_or2_split",
            ZH,
        )
        in intake_text
    )
    corrected_product_boxes = [
        box for box in at.selectbox if "鋼板" in [str(option) for option in box.options]
    ]
    assert len(corrected_product_boxes) == 1
    assert corrected_product_boxes[0].value == "鋼板"
    corrected_inbound_radios = [
        radio
        for radio in at.radio
        if t("intake.steel.answer.excluded", ZH)
        in [str(option) for option in radio.options]
    ]
    assert len(corrected_inbound_radios) == 1
    corrected_inbound_radios[0].set_value(
        t("intake.steel.answer.excluded", ZH)
    )
    at.run()
    assert not [
        radio
        for radio in at.radio
        if t("intake.steel.control.reporting_company", ZH)
        in [str(option) for option in radio.options]
    ]
    assert [
        box for box in at.selectbox if "鋼板" in [str(option) for option in box.options]
    ][0].value == "鋼板"
    corrected_save_buttons = [
        button
        for button in at.button
        if button.label == t("intake.steel.save", ZH)
    ]
    assert len(corrected_save_buttons) == 1
    corrected_save_buttons[0].click()
    at.run()
    assert not at.exception

    confirmations = purchased_steel_confirmations_from_state(at.session_state)
    assert len(confirmations) == 1
    assert len(at.session_state[STATE_PURCHASED_STEEL_CONFIRMATIONS]) == 1
    assert confirmations[0].steel_product_type == "鋼板"
    assert confirmations[0].tier1_to_reporting_company_transport_control == (
        CONTROL_NOT_APPLICABLE
    )
    pipeline_result = at.session_state[STATE_RESULT]
    steel_activities = pipeline_result.activity_records_accepted.loc[
        pipeline_result.activity_records_accepted["activity_type"]
        == "purchased_steel"
    ]
    assert len(steel_activities) == 1
    calc = pipeline_result.calculation_results.loc[
        pipeline_result.calculation_results["record_id"]
        == steel_activities.iloc[0]["record_id"]
    ].iloc[0]
    assert calc["factor_id"] == "ef_steel_鋼板_2013_v1"
    assert float(calc["calculated_tco2e"]) == pytest.approx(24.15, abs=1e-6)

    text = _all_text(at)
    assert "Traceback" not in text
    assert "Scope 3 尚未納入計算" not in text
    assert "目前已計算 24.15 tCO2e" in text
    assert "Category 1－採購商品與服務" in text
    assert "尚不代表完整 Scope 3 總量" in text
    assert "24.1500" in text
    assert "係數年份：2013" in text
    assert "2013.0" not in text
    assert "中國鋼鐵股份有限公司" in text
    inventory = company_inventory_emissions_summary(
        pipeline_result, ZH
    )
    assert float(inventory["inventory_tco2e"]) == pytest.approx(INVENTORY, abs=1e-4)
    cat1 = scope3_category1_emissions_summary(pipeline_result, ZH)
    href = str(cat1["rows"][0]["source_url"])
    assert "sort=" in href
    assert "ImportDate%20desc" in href or "ImportDate+desc" in href
    assert "format=JSON" in href
    assert "api_key" not in href
    assert "ImportDate%20desc" in text or "ImportDate+desc" in text
    assert "format=JSON" in text
    assert "api_key=" not in text
    assert float(cat1["tco2e"] or 0) == pytest.approx(24.15, abs=1e-6)
    assert len(
        [
            radio
            for radio in at.radio
            if t("intake.steel.method.average_data", ZH)
            in [str(option) for option in radio.options]
        ]
    ) == 0
    assert t("intake.steel.save", ZH) not in text
    assert t("boundary.confirm.title", ZH) not in text
    steel_status = _statuses(pipeline_result)
    assert any(
        value == "calculated"
        for key, value in steel_status.items()
        if key.startswith("purchased_steel:")
    )
