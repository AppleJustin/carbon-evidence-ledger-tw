"""Wire purchased-steel Category 1 into the existing Excel → pipeline path."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from carbon_ledger.calculate import calculate_activity_emissions
from carbon_ledger.factors import validate_factor_registry
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
from carbon_ledger.match_factors import match_activity_factors
from carbon_ledger.normalize import normalize_activity_records
from carbon_ledger.pipeline import run_uploaded_pipeline
from carbon_ledger.ui.i18n import t
from carbon_ledger.ui.view_models import (
    activity_detail_context,
    calculated_emissions_by_product_scope,
    company_inventory_emissions_summary,
    scope3_category1_emissions_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = REPO_ROOT / "data" / "reference"
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00Z")
ZH = "zh-TW"

_STEEL_HEADERS = (
    "activity_type,activity_value,unit,activity_start_date,activity_end_date,"
    "calculation_method,supplier_name,steel_product_type,product_identifier,"
    "emission_factor_value,emission_factor_unit,factor_boundary,"
    "factor_geography,factor_year,factor_source_id,evidence_reference,"
    "includes_pre_tier1_supply_chain_transport,"
    "includes_tier1_to_reporting_company_transport,"
    "tier1_to_reporting_company_transport_control"
)
_OLD_HEADERS = (
    "activity_type,activity_value,unit,activity_start_date,activity_end_date"
)
_MIXED_BASE = (
    "外購電力,50000,kWh,2025-01-01,2025-01-31\n"
    "天然氣,8000,m3,2025-01-01,2025-01-31\n"
    "柴油,1200,L,2025-01-01,2025-01-31\n"
)


def _metadata() -> IntakeMetadata:
    return IntakeMetadata(
        source_name="steel_pipeline.csv",
        site_id="高雄廠",
        document_date=date(2025, 1, 31),
        data_quality_tier="unknown",
        intake_run_id="steel_pipeline",
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


def _csv(*rows: str, headers: str = _STEEL_HEADERS) -> str:
    return headers + "\n" + "\n".join(rows) + "\n"


def _supplier_row(
    *,
    quantity: str = "10",
    unit: str = "t",
    method: str = "supplier_specific",
    supplier: str = "Demo Steel Supplier",
    product: str = "steel wire rod",
    product_id: str = "WR-001",
    factor_value: str = "1.85",
    factor_unit: str = "tCO2e/t",
    boundary: str = "cradle_to_gate",
    geography: str = "TW",
    factor_year: str = "2025",
    source_id: str = "ref_supplier_epd_wire_rod_2025",
    evidence: str = "EPD-2025-001",
    pre_tier1: str = "",
    inbound: str = "false",
    control: str = "",
    start: str = "2025-01-01",
    end: str = "2025-12-31",
    activity: str = "採購鋼材",
) -> str:
    return (
        f"{activity},{quantity},{unit},{start},{end},{method},{supplier},"
        f"{product},{product_id},{factor_value},{factor_unit},{boundary},"
        f"{geography},{factor_year},{source_id},{evidence},{pre_tier1},"
        f"{inbound},{control}"
    )


def _average_row(
    *,
    product: str = "steel wire rod",
    geography: str = "TW",
    inbound: str = "false",
    pre_tier1: str = "",
    control: str = "",
) -> str:
    values = [""] * len(_STEEL_HEADERS.split(","))
    values[0] = "採購鋼材"
    values[1] = "10"
    values[2] = "t"
    values[3] = "2025-01-01"
    values[4] = "2025-12-31"
    values[5] = "average_data"
    values[7] = product
    values[11] = "cradle_to_gate"
    values[12] = geography
    values[13] = "2023"
    values[16] = pre_tier1
    values[17] = inbound
    values[18] = control
    return ",".join(values)


def _intake(csv_text: str, **mapping_overrides: object):
    table = parse_uploaded_table(
        file_name="steel_pipeline.csv",
        data=csv_text.encode("utf-8"),
    )
    mapping = _mapping_for(table, **mapping_overrides)
    return build_and_validate_intake(table, mapping, _metadata())


def _pipeline(csv_text: str):
    intake = _intake(csv_text)
    result = run_uploaded_pipeline(
        REPO_ROOT,
        run_id="steel_cat1_upload",
        ingested_at=FIXED_INGESTED_AT,
        source_documents=intake.source_documents,
        accepted_activities=intake.accepted_activities,
        include_ghg=True,
        include_ifrs_s2=False,
    )
    return result, intake


def _steel_factor_row(**fields: object) -> dict[str, object]:
    row: dict[str, object] = {
        "factor_id": "ef_steel_wire_rod_tw_test_v1",
        "activity_type": "purchased_steel",
        "combustion_context": "not_applicable",
        "gas": "CO2e",
        "factor_value": "1.85",
        "numerator_unit": "tCO2e",
        "denominator_unit": "t",
        "geography": "TW",
        "factor_year": "2023",
        "valid_from": "2023-01-01",
        "valid_to": "2025-12-31",
        "source_reference_id": "ref_registered_steel_wire_rod_2023",
        "source_locator": "test registered steel factor",
        "factor_status": "ready",
        "required_conversion": "not_required",
        "notes": "",
        "steel_product_type": "steel wire rod",
        "factor_boundary": "cradle_to_gate",
        "factor_version": "v1",
    }
    row.update(fields)
    return row


def _calculate_with_factors(csv_text: str, extra_factors: list[dict[str, object]]):
    intake = _intake(csv_text)
    accepted = intake.accepted_activities
    normalized = normalize_activity_records(accepted)
    activities = accepted.merge(
        normalized[["record_id", "normalized_unit", "normalization_status"]],
        on="record_id",
        how="left",
    )
    registry = validate_factor_registry(REFERENCE_DIR)
    factors = pd.concat(
        [registry.emission_factors, pd.DataFrame(extra_factors)],
        ignore_index=True,
        sort=False,
    )
    matching = match_activity_factors(
        activities,
        factors,
        registry.calculation_dependencies,
        heating_values=registry.fuel_heating_values,
    )
    calcs = calculate_activity_emissions(
        normalized_records=normalized,
        candidate_matches=matching.candidate_matches,
        activity_readiness=matching.activity_readiness,
        emission_factors=factors,
        activity_records=accepted,
    )
    return calcs, intake, matching


def _steel_calc(result) -> pd.Series:
    activities = result.activity_records_accepted
    steel_id = activities.loc[
        activities["activity_type"].astype(str) == "purchased_steel",
        "record_id",
    ].iloc[0]
    return result.calculation_results.loc[
        result.calculation_results["record_id"] == steel_id
    ].iloc[0]


def test_complete_supplier_specific_excel_calculates_category_1() -> None:
    result, intake = _pipeline(_csv(_supplier_row()))
    assert intake.rejected_count == 0
    steel = _steel_calc(result)
    assert steel["calculation_status"] == "calculated"
    assert float(steel["calculated_tco2e"]) == 18.5
    assert str(steel["ghg_scope"]) == "scope_3"
    assert str(steel["scope_3_category"]) == "category_1"
    ghg = result.ghg_evaluations.loc[
        result.ghg_evaluations["record_id"] == steel["record_id"]
    ].iloc[0]
    assert str(ghg["mapping_status"]) == "mapped"
    assert str(ghg["ghg_scope"]) == "scope_3"
    assert "category_1" in str(ghg["scope3_category"])


def test_supplier_specific_missing_supplier_name_is_blocked() -> None:
    result, _ = _pipeline(_csv(_supplier_row(supplier="")))
    steel = _steel_calc(result)
    assert steel["calculation_status"] == "blocked_missing_supplier_or_product"
    assert pd.isna(steel["calculated_tco2e"])


def test_supplier_specific_missing_factor_year_not_filled() -> None:
    result, intake = _pipeline(_csv(_supplier_row(factor_year="")))
    row = intake.accepted_activities.iloc[0]
    assert str(row.get("factor_year") or "") == ""
    steel = _steel_calc(result)
    assert steel["calculation_status"] == "blocked_missing_factor_year"
    assert pd.isna(steel["calculated_kgco2e"])
    factor_year = steel.get("factor_year")
    assert factor_year is None or pd.isna(factor_year) or str(factor_year) in {
        "",
        "<NA>",
    }
    assert int(steel["reporting_year"]) == 2025


def test_product_type_without_supplier_is_not_calculated() -> None:
    result, _ = _pipeline(_csv(_supplier_row(supplier="", product="steel wire rod")))
    steel = _steel_calc(result)
    assert steel["calculation_status"] != "calculated"
    assert steel["calculation_status"] == "blocked_missing_supplier_or_product"


def test_older_factor_year_calculates_with_temporal_limit() -> None:
    result, _ = _pipeline(_csv(_supplier_row(factor_year="2023")))
    steel = _steel_calc(result)
    assert steel["calculation_status"] == "calculated"
    assert int(steel["factor_year"]) == 2023
    assert int(steel["reporting_year"]) == 2025
    trace = str(steel["calculation_trace"])
    assert "2023" in trace
    summary = scope3_category1_emissions_summary(result, ZH)
    assert summary["rows"][0]["temporal_warning"] is True
    assert summary["rows"][0]["factor_year"] == "2023"
    warning = t(
        "dash.scope3_cat1.temporal",
        ZH,
        factor_year="2023",
        reporting_year="2025",
    )
    assert "2023" in warning
    assert "已驗證" not in warning
    assert "已確信" not in warning


def test_average_data_without_registered_factor_stays_no_factor() -> None:
    result, _ = _pipeline(_csv(_average_row()))
    steel = _steel_calc(result)
    assert steel["calculation_status"] == "no_matching_factor"
    assert pd.isna(steel["calculated_tco2e"])
    explanation = activity_detail_context(
        result, str(steel["record_id"]), ZH
    )["calculation_explanation"]
    assert explanation == t("explain.steel.no_matching_factor", ZH)
    assert "0" not in explanation


def test_average_data_steel_plate_ten_tonnes_uses_approved_fixture_factor() -> None:
    calcs, _, _ = _calculate_with_factors(
        _csv(_average_row(product="鋼板")),
        [
            _steel_factor_row(
                factor_id="ef_steel_plate_test_v1",
                steel_product_type="鋼板",
                factor_value="2.415",
                numerator_unit="kgCO2e",
                denominator_unit="kg",
                factor_year="2023",
                valid_from="2023-01-01",
                valid_to="2025-12-31",
                source_reference_id="ref_test_cfp_steel_plate",
            )
        ],
    )
    row = calcs.iloc[0]
    assert row["calculation_status"] == "calculated"
    assert float(row["calculated_kgco2e"]) == 24150.0
    assert float(row["calculated_tco2e"]) == 24.15
    assert row["ghg_scope"] == "scope_3"
    assert row["scope_3_category"] == "category_1"


def test_average_data_2023_factor_covering_2025_is_usable() -> None:
    calcs, _, _ = _calculate_with_factors(
        _csv(_average_row()),
        [_steel_factor_row(valid_from="2023-01-01", valid_to="2025-12-31")],
    )
    row = calcs.iloc[0]
    assert row["calculation_status"] == "calculated"
    assert float(row["calculated_tco2e"]) == 18.5
    assert int(row["factor_year"]) == 2023


def test_average_data_expired_in_2024_cannot_cover_2025() -> None:
    calcs, _, _ = _calculate_with_factors(
        _csv(_average_row()),
        [_steel_factor_row(valid_from="2023-01-01", valid_to="2024-12-31")],
    )
    row = calcs.iloc[0]
    assert row["calculation_status"] == "no_matching_factor"
    assert pd.isna(row["calculated_tco2e"])


def test_average_data_mid_2025_start_cannot_represent_full_year() -> None:
    calcs, _, _ = _calculate_with_factors(
        _csv(_average_row()),
        [_steel_factor_row(valid_from="2025-07-01", valid_to="2026-12-31")],
    )
    row = calcs.iloc[0]
    assert row["calculation_status"] == "no_matching_factor"
    assert pd.isna(row["calculated_tco2e"])


def test_malformed_valid_to_is_not_open_ended() -> None:
    calcs, _, _ = _calculate_with_factors(
        _csv(_average_row()),
        [
            _steel_factor_row(
                valid_from="2023-01-01",
                valid_to="not-a-date",
            )
        ],
    )
    row = calcs.iloc[0]
    assert row["calculation_status"] == "no_matching_factor"
    assert pd.isna(row["calculated_tco2e"])


def test_ambiguous_covering_factors_are_not_auto_selected() -> None:
    calcs, _, _ = _calculate_with_factors(
        _csv(_average_row()),
        [
            _steel_factor_row(
                factor_id="ef_steel_a",
                factor_version="v1",
                factor_year="2023",
            ),
            _steel_factor_row(
                factor_id="ef_steel_b",
                factor_version="v2",
                factor_year="2024",
                source_reference_id="ref_registered_steel_wire_rod_2024",
            ),
        ],
    )
    row = calcs.iloc[0]
    assert row["calculation_status"] == "blocked_ambiguous_factor"
    assert pd.isna(row["calculated_tco2e"])


def test_pre_tier1_transport_does_not_block_category_1() -> None:
    result, _ = _pipeline(_csv(_supplier_row(pre_tier1="是")))
    steel = _steel_calc(result)
    assert steel["calculation_status"] == "calculated"
    trace = str(steel["calculation_trace"])
    assert "includes_pre_tier1_supply_chain_transport" in trace
    assert "true" in trace.lower()
    assert "Upstream transport is excluded" not in str(steel["calculation_reason"])


def test_inbound_tier1_transport_is_not_counted_in_category_1() -> None:
    result, _ = _pipeline(
        _csv(_supplier_row(inbound="true", control="third_party"))
    )
    steel = _steel_calc(result)
    assert steel["calculation_status"] == (
        "blocked_tier1_inbound_transport_requires_category4_split"
    )
    assert pd.isna(steel["calculated_tco2e"])
    reason = str(steel["calculation_reason"])
    assert "Category 4" in reason
    assert "Upstream transport is excluded" not in reason
    trace = str(steel["calculation_trace"])
    assert "includes_tier1_to_reporting_company_transport" in trace
    zh = activity_detail_context(result, str(steel["record_id"]), ZH)[
        "calculation_explanation"
    ]
    assert "Category 4" in zh or "第三方" in zh
    assert zh != reason
    assert "The factor includes" not in zh


def test_company_controlled_inbound_is_not_category_4() -> None:
    result, _ = _pipeline(
        _csv(_supplier_row(inbound="true", control="reporting_company"))
    )
    steel = _steel_calc(result)
    assert steel["calculation_status"] == (
        "blocked_company_controlled_transport_requires_scope1_or2_split"
    )
    assert pd.isna(steel["calculated_tco2e"])
    reason = str(steel["calculation_reason"])
    assert "Category 4" not in reason
    zh = activity_detail_context(result, str(steel["record_id"]), ZH)[
        "calculation_explanation"
    ]
    assert "Scope 1" in zh or "本公司" in zh
    assert zh != reason
    assert scope3_category1_emissions_summary(result, ZH)["tco2e"] is None


def test_blank_inbound_flag_is_not_treated_as_excluded() -> None:
    result, _ = _pipeline(_csv(_supplier_row(inbound="")))
    steel = _steel_calc(result)
    assert steel["calculation_status"] == "blocked_factor_inclusion_unconfirmed"
    assert pd.isna(steel["calculated_tco2e"])


def test_original_ten_tonne_row_stays_no_factor_configured() -> None:
    result, _ = _pipeline(
        _csv(
            "採購鋼材,10,t,2025-01-01,2025-01-31",
            headers=_OLD_HEADERS,
        )
    )
    steel = _steel_calc(result)
    assert steel["calculation_status"] == "no_factor_configured"
    assert pd.isna(steel["calculated_kgco2e"])
    assert pd.isna(steel["calculated_tco2e"])


def test_steel_result_scope_is_category_1() -> None:
    result, _ = _pipeline(_csv(_supplier_row()))
    steel = _steel_calc(result)
    assert str(steel["ghg_scope"]) == "scope_3"
    assert str(steel["scope_3_category"]) == "category_1"
    ghg = result.ghg_evaluations.loc[
        result.ghg_evaluations["record_id"] == steel["record_id"]
    ].iloc[0]
    assert str(ghg["mapping_status"]) == "mapped"
    assert str(ghg["ghg_scope"]) == "scope_3"


def _energy_row(activity: str, quantity: str, unit: str) -> str:
    values = [""] * len(_STEEL_HEADERS.split(","))
    values[0] = activity
    values[1] = quantity
    values[2] = unit
    values[3] = "2025-01-01"
    values[4] = "2025-01-31"
    return ",".join(values)


def test_steel_does_not_change_scope_1_and_2_inventory_total() -> None:
    baseline, _ = _pipeline(
        _csv(
            _energy_row("外購電力", "50000", "kWh"),
            _energy_row("天然氣", "8000", "m3"),
            _energy_row("柴油", "1200", "L"),
        )
    )
    with_steel, _ = _pipeline(
        _csv(
            _energy_row("外購電力", "50000", "kWh"),
            _energy_row("天然氣", "8000", "m3"),
            _energy_row("柴油", "1200", "L"),
            _supplier_row(),
        )
    )
    base_scopes = calculated_emissions_by_product_scope(baseline)
    steel_scopes = calculated_emissions_by_product_scope(with_steel)
    assert steel_scopes["scope_1"] == base_scopes["scope_1"]
    assert steel_scopes["scope_2"] == base_scopes["scope_2"]
    assert steel_scopes.get("scope_3") is None
    inventory = company_inventory_emissions_summary(with_steel, ZH)
    base_inventory = company_inventory_emissions_summary(baseline, ZH)
    assert inventory["inventory_tco2e"] == base_inventory["inventory_tco2e"]
    cat1 = scope3_category1_emissions_summary(with_steel, ZH)
    assert cat1["tco2e"] == 18.5
    assert cat1["tco2e"] != inventory["inventory_tco2e"]


def test_category_1_subtotal_requires_official_scope_3_category_field() -> None:
    result, _ = _pipeline(_csv(_supplier_row()))
    before = scope3_category1_emissions_summary(result, ZH)
    inventory_before = company_inventory_emissions_summary(result, ZH)
    assert before["tco2e"] == 18.5

    category_4 = result.calculation_results.copy()
    category_4["scope_3_category"] = "category_4"
    excluded = replace(result, calculation_results=category_4)
    after_category_4 = scope3_category1_emissions_summary(excluded, ZH)
    assert after_category_4["tco2e"] is None
    assert after_category_4["row_count"] == 0
    assert (
        company_inventory_emissions_summary(excluded, ZH)["inventory_tco2e"]
        == inventory_before["inventory_tco2e"]
    )

    missing = result.calculation_results.drop(columns=["scope_3_category"])
    dropped = replace(result, calculation_results=missing)
    after_missing = scope3_category1_emissions_summary(dropped, ZH)
    assert after_missing["tco2e"] is None
    assert after_missing["row_count"] == 0
    assert (
        company_inventory_emissions_summary(dropped, ZH)["inventory_tco2e"]
        == inventory_before["inventory_tco2e"]
    )

    long_name_only = result.calculation_results.copy()
    long_name_only["scope3_category"] = "category_4_upstream_transportation"
    still_category_1 = replace(result, calculation_results=long_name_only)
    after_long_name = scope3_category1_emissions_summary(still_category_1, ZH)
    assert after_long_name["tco2e"] == before["tco2e"]
    assert after_long_name["row_count"] == before["row_count"]


def test_dashboard_shows_independent_category_1_subtotal() -> None:
    result, _ = _pipeline(_csv(_supplier_row()))
    summary = scope3_category1_emissions_summary(result, ZH)
    assert summary["label"] == t("dash.scope3_cat1.title", ZH)
    assert "Scope 3 Category 1" in summary["label"]
    assert "採購商品與服務" in summary["label"]
    assert summary["tco2e"] == 18.5
    assert "未納入" in summary["not_in_inventory"]
    assert summary["rows"][0]["status_label"] == t("dash.scope3_cat1.estimated", ZH)
    assert "已驗證" not in summary["rows"][0]["status_label"]
    assert "已確信" not in summary["label"]


def test_zh_tw_ui_does_not_show_english_calculation_reason() -> None:
    result, _ = _pipeline(_csv(_supplier_row(supplier="")))
    steel = _steel_calc(result)
    english_reason = str(steel["calculation_reason"])
    assert "supplier_specific requires" in english_reason
    zh = activity_detail_context(result, str(steel["record_id"]), ZH)
    explanation = str(zh["calculation_explanation"])
    assert "supplier_specific requires" not in explanation
    assert "calculation_method is required" not in explanation
    assert explanation == t(
        "explain.steel.blocked_missing_supplier_or_product", ZH
    )


def test_legacy_excel_without_steel_columns_still_ingests() -> None:
    pytest.importorskip("openpyxl")
    frame = pd.DataFrame(
        [
            {
                "activity_type": "外購電力",
                "activity_value": 50000,
                "unit": "kWh",
                "activity_start_date": "2025-01-01",
                "activity_end_date": "2025-01-31",
            },
            {
                "activity_type": "採購鋼材",
                "activity_value": 10,
                "unit": "t",
                "activity_start_date": "2025-01-01",
                "activity_end_date": "2025-01-31",
            },
        ]
    )
    buffer = BytesIO()
    frame.to_excel(buffer, index=False)
    table = parse_uploaded_table(
        file_name="legacy_steel.xlsx",
        data=buffer.getvalue(),
    )
    result = build_and_validate_intake(table, _mapping_for(table), _metadata())
    assert result.rejected_count == 0
    assert result.accepted_count == 2
    steel = result.accepted_activities.loc[
        result.accepted_activities["activity_type"] == "purchased_steel"
    ].iloc[0]
    assert str(steel.get("calculation_method") or "") == ""
    pipeline = run_uploaded_pipeline(
        REPO_ROOT,
        run_id="legacy_excel",
        ingested_at=FIXED_INGESTED_AT,
        source_documents=result.source_documents,
        accepted_activities=result.accepted_activities,
        include_ghg=True,
    )
    calc = pipeline.calculation_results.loc[
        pipeline.calculation_results["record_id"] == steel["record_id"]
    ].iloc[0]
    assert calc["calculation_status"] == "no_factor_configured"


def test_existing_fuel_and_electricity_results_unchanged() -> None:
    result, _ = _pipeline(
        _csv(
            *_MIXED_BASE.strip().split("\n"),
            "採購鋼材,10,t,2025-01-01,2025-01-31",
            headers=_OLD_HEADERS,
        )
    )
    by_type = result.activity_records_accepted.set_index("record_id")
    calcs = result.calculation_results.set_index("record_id")
    statuses = {
        str(by_type.loc[record_id, "activity_type"]): str(
            calcs.loc[record_id, "calculation_status"]
        )
        for record_id in by_type.index
    }
    assert statuses["grid_electricity"] == "calculated"
    assert statuses["natural_gas"] == "calculated"
    assert statuses["diesel"] == "calculated"
    assert statuses["purchased_steel"] == "no_factor_configured"
    electricity = calcs.loc[
        by_type["activity_type"] == "grid_electricity"
    ].iloc[0]
    assert float(electricity["calculated_tco2e"]) > 0
    steel = calcs.loc[by_type["activity_type"] == "purchased_steel"].iloc[0]
    assert pd.isna(steel["calculated_tco2e"])


def test_intake_does_not_infer_method_from_steel_activity_name() -> None:
    intake = _intake(
        _csv("採購鋼材,10,t,2025-01-01,2025-01-31", headers=_OLD_HEADERS)
    )
    row = intake.accepted_activities.iloc[0]
    assert str(row["activity_type"]) == "purchased_steel"
    assert str(row.get("calculation_method") or "") == ""
    summary = summarize_pre_analysis_readiness(intake.accepted_activities)
    assert summary["ready"] == 0
    assert summary["needs_confirm"] == 1
    assert classify_activity_analysis_readiness(
        activity_type="purchased_steel",
        fuel_subtype="not_applicable",
        process_use="not_applicable",
        activity_start="2025-01-01",
        activity_end="2025-01-31",
    ) == "needs_confirm"


def test_complete_supplier_specific_is_ready_not_unsupported() -> None:
    intake = _intake(_csv(_supplier_row()))
    summary = summarize_pre_analysis_readiness(intake.accepted_activities)
    assert summary["ready"] == 1
    assert summary["unsupported"] == 0


def test_chinese_steel_headers_enter_existing_alias_path() -> None:
    csv_text = (
        "活動類型,用量,單位,開始日期,結束日期,計算方法,供應商名稱,"
        "鋼材產品類型,供應商排放係數,係數單位,係數邊界,係數地理範圍,"
        "係數年份,係數來源,證據參照\n"
        "採購鋼材,10,t,2025-01-01,2025-12-31,供應商特定,中鋼,"
        "steel wire rod,1.85,tCO2e/t,搖籃到大門,TW,2025,ref_epd,EPD-1\n"
    )
    result, intake = _pipeline(csv_text)
    row = intake.accepted_activities.iloc[0]
    assert str(row["calculation_method"]) == "supplier_specific"
    assert str(row["supplier_name"]) == "中鋼"
    assert str(row["factor_boundary"]) == "cradle_to_gate"
    steel = _steel_calc(result)
    assert steel["calculation_status"] == "blocked_factor_inclusion_unconfirmed"
    assert pd.isna(steel["calculated_tco2e"])
