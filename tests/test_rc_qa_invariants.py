"""RC QA — independent calculation, year, subtype, boundary, and mutation tests."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from rc_qa_support import (
    ELEC_2024_KG_PER_KWH,
    GWP_CH4,
    GWP_N2O,
    HERO_JS_SHA,
    HV_DIESEL,
    HV_NG1_LOW,
    HV_NG2_LOW,
    REPO_ROOT,
    assert_blocked_not_zero,
    calculated_rows,
    calculated_tco2e_sum,
    diesel_tco2e,
    electricity_tco2e,
    intake_and_run,
    mapping_for,
    metadata,
    ng1_tco2e,
    ng2_tco2e,
)

from carbon_ledger.heating import normalize_fuel_subtype, select_heating_value
from carbon_ledger.intake import (
    IntakeError,
    build_and_validate_intake,
    parse_uploaded_table,
)
from carbon_ledger.ui.formatting import RESULT_TCO2E_DECIMALS
from carbon_ledger.ui.motion import customer_safe_analysis_error
from carbon_ledger.ui.view_models import (
    build_activity_overview,
    calculated_emissions_by_product_scope,
    calculated_emissions_summary,
    scope_kpi_states,
)

HERO_JS = REPO_ROOT / "src/carbon_ledger/ui/hero_emissions_countup.js"
LIVE_REFERENCE = REPO_ROOT / "data" / "reference"
ELEC_2024_CSV = (
    "活動類型,用量,單位,開始日期,結束日期,廠場\n"
    "外購電力,50000,kWh,2024-01-01,2024-01-31,高雄廠\n"
)
NG_CSV = (
    "活動類型,用量,單位,開始日期,結束日期,廠場\n"
    "{activity},{qty},m3,{start},{end},高雄廠\n"
)
DIESEL_CSV = (
    "活動類型,用量,單位,開始日期,結束日期,廠場\n"
    "柴油,{qty},L,{start},{end},高雄廠\n"
)
MIXED_CSV = (
    "活動類型,用量,單位,開始日期,結束日期,廠場\n"
    "外購電力,50000,kWh,2025-01-01,2025-01-31,高雄廠\n"
    "天然氣 NG1,8000,m3,2025-01-01,2025-01-31,高雄廠\n"
    "柴油,1200,L,2025-01-01,2025-01-31,高雄廠\n"
    "採購鋼材,10,t,2025-01-01,2025-01-31,高雄廠\n"
)


def _approx(actual: Decimal, expected: Decimal, *, places: int = 9) -> None:
    assert abs(actual - expected) < Decimal(10) ** -places, (
        f"actual={actual} expected={expected}"
    )


def _heating_table() -> pd.DataFrame:
    return pd.read_csv(LIVE_REFERENCE / "fuel_heating_values.csv", dtype=str)


def _copy_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "config", root / "config")
    shutil.copytree(LIVE_REFERENCE, root / "data" / "reference")
    return root


def test_official_locked_values_unchanged() -> None:
    heating = _heating_table()
    ng1 = heating.loc[
        heating["heating_value_id"] == "hv_tw_natural_gas_ng1_2025"
    ].iloc[0]
    ng2 = heating.loc[
        heating["heating_value_id"] == "hv_tw_natural_gas_ng2_2025"
    ].iloc[0]
    diesel = heating.loc[heating["heating_value_id"] == "hv_tw_diesel_l_2025"].iloc[0]
    assert Decimal(str(ng1["heating_value"])) == HV_NG1_LOW
    assert Decimal(str(ng2["heating_value"])) == HV_NG2_LOW
    assert Decimal(str(diesel["heating_value"])) == HV_DIESEL
    gwp = pd.read_csv(LIVE_REFERENCE / "gwp_values.csv", dtype=str)
    ch4 = gwp.loc[gwp["gwp_id"] == "gwp_ar5_ch4_fuel_combustion"].iloc[0]
    n2o = gwp.loc[gwp["gwp_id"] == "gwp_ar5_n2o_fuel_combustion"].iloc[0]
    assert Decimal(str(ch4["gwp_value"])) == GWP_CH4
    assert Decimal(str(n2o["gwp_value"])) == GWP_N2O
    factors = pd.read_csv(LIVE_REFERENCE / "emission_factors.csv", dtype=str)
    elec = factors.loc[factors["factor_id"] == "ef_tw_grid_electricity_2024"].iloc[0]
    assert Decimal(str(elec["factor_value"])) == ELEC_2024_KG_PER_KWH
    digest = hashlib.sha256(HERO_JS.read_bytes()).hexdigest()
    assert digest == HERO_JS_SHA


def test_electricity_2024_independent_oracle() -> None:
    expected_kg = Decimal("50000") * ELEC_2024_KG_PER_KWH
    expected_t = expected_kg / Decimal("1000")
    assert expected_kg == Decimal("23700")
    assert expected_t == Decimal("23.7")
    result, _ = intake_and_run(ELEC_2024_CSV, run_id="rc_elec_2024")
    rows = calculated_rows(result)
    assert len(rows) == 1
    actual = Decimal(str(rows.iloc[0]["calculated_tco2e"]))
    _approx(actual, electricity_tco2e(Decimal("50000")))
    assert actual == Decimal("23.7")


def test_2025_ng1_independent_oracle() -> None:
    qty = Decimal("8000")
    expected = ng1_tco2e(qty)
    csv = NG_CSV.format(
        activity="天然氣 NG1", qty="8000", start="2025-01-01", end="2025-01-31"
    )
    result, _ = intake_and_run(csv, run_id="rc_ng1")
    actual = Decimal(str(calculated_rows(result).iloc[0]["calculated_tco2e"]))
    _approx(actual, expected)
    row = calculated_rows(result).iloc[0]
    assert Decimal(str(row["heating_value"])) == HV_NG1_LOW
    assert str(row["heating_value_id"]) == "hv_tw_natural_gas_ng1_2025"


def test_2025_ng2_independent_oracle() -> None:
    qty = Decimal("8000")
    expected = ng2_tco2e(qty)
    csv = NG_CSV.format(
        activity="天然氣 NG2", qty="8000", start="2025-01-01", end="2025-01-31"
    )
    result, _ = intake_and_run(csv, run_id="rc_ng2", natural_gas_subtype="NG2")
    actual = Decimal(str(calculated_rows(result).iloc[0]["calculated_tco2e"]))
    _approx(actual, expected)
    assert Decimal(str(calculated_rows(result).iloc[0]["heating_value"])) == HV_NG2_LOW
    assert ng1_tco2e(qty) != ng2_tco2e(qty)


def test_2025_diesel_independent_oracle() -> None:
    qty = Decimal("1200")
    expected = diesel_tco2e(qty)
    csv = DIESEL_CSV.format(qty="1200", start="2025-01-01", end="2025-01-31")
    result, _ = intake_and_run(csv, run_id="rc_diesel")
    actual = Decimal(str(calculated_rows(result).iloc[0]["calculated_tco2e"]))
    _approx(actual, expected)
    assert Decimal(str(calculated_rows(result).iloc[0]["heating_value"])) == HV_DIESEL


def test_total_equals_sum_of_calculated_rows_only() -> None:
    result, _ = intake_and_run(MIXED_CSV, run_id="rc_mixed")
    summary = calculated_emissions_summary(result)
    independent = calculated_tco2e_sum(result)
    _approx(Decimal(str(summary["calculated_tco2e"])), independent, places=8)
    assert_blocked_not_zero(result)
    steel_ids = result.activity_records_accepted.loc[
        result.activity_records_accepted["activity_type"] == "purchased_steel",
        "record_id",
    ]
    steel = result.calculation_results[
        result.calculation_results["record_id"].isin(steel_ids)
    ]
    assert not steel.empty
    assert (steel["calculation_status"].astype(str) != "calculated").all()


def test_scope_totals_exclude_blocked_and_unsupported() -> None:
    result, _ = intake_and_run(MIXED_CSV, run_id="rc_scope")
    scopes = calculated_emissions_by_product_scope(result)
    activities = result.activity_records_accepted.set_index("record_id")
    calcs = result.calculation_results.set_index("record_id")
    scope1 = Decimal("0")
    scope2 = Decimal("0")
    for record_id, row in activities.iterrows():
        status = str(calcs.loc[record_id, "calculation_status"])
        if status != "calculated":
            continue
        value = Decimal(str(calcs.loc[record_id, "calculated_tco2e"]))
        activity = str(row["activity_type"])
        if activity in {"natural_gas", "diesel"}:
            scope1 += value
        elif activity == "grid_electricity":
            scope2 += value
    _approx(Decimal(str(scopes["scope_1"])), scope1, places=8)
    _approx(Decimal(str(scopes["scope_2"])), scope2, places=8)
    hero = Decimal(str(calculated_emissions_summary(result)["calculated_tco2e"]))
    displayed = Decimal(str(scopes["scope_1"])) + Decimal(str(scopes["scope_2"]))
    quant = Decimal(10) ** -RESULT_TCO2E_DECIMALS
    assert abs(hero - displayed) < quant
    states = scope_kpi_states(result)
    assert states["scope_1"]["state"] == "calculated"
    assert states["scope_2"]["state"] == "calculated"
    assert states["scope_3"]["state"] == "empty"
    assert states["scope_3"]["value"] is None


def test_2024_natural_gas_does_not_use_2025_heating_value() -> None:
    csv = NG_CSV.format(
        activity="天然氣 NG1", qty="100", start="2024-01-01", end="2024-01-31"
    )
    result, _ = intake_and_run(csv, run_id="rc_ng_2024")
    row = result.calculation_results.iloc[0]
    assert str(row["calculation_status"]) != "calculated"
    selection = select_heating_value(
        _heating_table(),
        fuel_type="natural_gas",
        activity_start="2024-01-01",
        activity_end="2024-01-31",
        fuel_subtype="NG1",
    )
    assert selection.status == "missing"
    assert "2025" in selection.reason


def test_2024_diesel_does_not_use_2025_heating_value() -> None:
    csv = DIESEL_CSV.format(qty="10", start="2024-06-01", end="2024-06-30")
    result, _ = intake_and_run(csv, run_id="rc_diesel_2024")
    assert str(result.calculation_results.iloc[0]["calculation_status"]) != "calculated"


def test_future_year_without_verified_heat_value_fails_safe() -> None:
    csv = NG_CSV.format(
        activity="天然氣 NG1", qty="100", start="2026-01-01", end="2026-01-31"
    )
    result, _ = intake_and_run(csv, run_id="rc_ng_2026")
    assert str(result.calculation_results.iloc[0]["calculation_status"]) != "calculated"
    assert_blocked_not_zero(result)


def test_ng_blank_and_unknown_are_blocked() -> None:
    csv = NG_CSV.format(
        activity="天然氣", qty="100", start="2025-01-01", end="2025-01-31"
    )
    blank, _ = intake_and_run(
        csv, run_id="rc_ng_blank", natural_gas_subtype="unknown"
    )
    unknown, _ = intake_and_run(
        csv, run_id="rc_ng_unknown", natural_gas_subtype="unknown"
    )
    for result in (blank, unknown):
        status = str(result.calculation_results.iloc[0]["calculation_status"])
        assert status == "blocked_natural_gas_type_required"
    assert_blocked_not_zero(blank)


def test_invalid_ng_subtype_is_review_state() -> None:
    csv = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "天然氣 NG3,100,m3,2025-01-01,2025-01-31,高雄廠\n"
    )
    result, intake = intake_and_run(
        csv, run_id="rc_ng3", natural_gas_subtype="unknown"
    )
    subtype = str(intake.accepted_activities.iloc[0]["fuel_subtype"])
    assert subtype not in {"NG1", "NG2"}
    assert str(result.calculation_results.iloc[0]["calculation_status"]) != "calculated"


def test_ng_case_and_whitespace_follow_existing_normalization() -> None:
    assert normalize_fuel_subtype("ng1") == "NG1"
    assert normalize_fuel_subtype(" NG1 ") == "NG1"
    assert normalize_fuel_subtype("ng2") == "NG2"
    csv = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "ng1,100,m3,2025-01-01,2025-01-31,高雄廠\n"
    )
    result, intake = intake_and_run(
        csv, run_id="rc_ng_lower", natural_gas_subtype="unknown"
    )
    assert str(intake.accepted_activities.iloc[0]["fuel_subtype"]) == "NG1"
    assert str(result.calculation_results.iloc[0]["calculation_status"]) == "calculated"


def test_diesel_missing_context_blocked_and_non_vehicle_not_auto_classified() -> None:
    csv = DIESEL_CSV.format(qty="10", start="2025-01-01", end="2025-01-31")
    result, intake = intake_and_run(
        csv, run_id="rc_diesel_unknown", diesel_context="unknown"
    )
    assert str(intake.accepted_activities.iloc[0]["process_use"]) != "company_vehicle"
    assert str(result.calculation_results.iloc[0]["calculation_status"]) != "calculated"
    generator = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "廠內柴油鍋爐,10,L,2025-01-01,2025-01-31,高雄廠\n"
    )
    other, other_intake = intake_and_run(
        generator, run_id="rc_diesel_boiler", diesel_context="unknown"
    )
    assert str(other_intake.accepted_activities.iloc[0]["process_use"]) != (
        "company_vehicle"
    )
    assert str(other.calculation_results.iloc[0]["calculation_status"]) != "calculated"


def test_quantity_zero_is_rejected_not_calculated_zero() -> None:
    csv = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,0,kWh,2025-01-01,2025-01-31,高雄廠\n"
    )
    table = parse_uploaded_table(file_name="zero.csv", data=csv.encode("utf-8"))
    intake = build_and_validate_intake(table, mapping_for(table), metadata())
    assert intake.accepted_count == 0
    assert intake.rejected_count == 1
    assert "greater than zero" in str(intake.rejected_rows.iloc[0]["issue_message"])


def test_negative_quantity_rejected() -> None:
    csv = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,-5,kWh,2025-01-01,2025-01-31,高雄廠\n"
    )
    table = parse_uploaded_table(file_name="neg.csv", data=csv.encode("utf-8"))
    intake = build_and_validate_intake(table, mapping_for(table), metadata())
    assert intake.accepted_count == 0
    assert intake.rejected_count == 1


def test_missing_and_blank_quantity_not_treated_as_zero() -> None:
    csv = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,,kWh,2025-01-01,2025-01-31,高雄廠\n"
        "外購電力, ,kWh,2025-01-01,2025-01-31,高雄廠\n"
    )
    table = parse_uploaded_table(file_name="blank.csv", data=csv.encode("utf-8"))
    intake = build_and_validate_intake(table, mapping_for(table), metadata())
    assert intake.accepted_count == 0
    messages = " ".join(intake.rejected_rows["issue_message"].astype(str))
    assert "missing" in messages


def test_extreme_and_small_quantities_stay_finite() -> None:
    csv = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,1000000000,kWh,2025-01-01,2025-01-31,高雄廠\n"
        "天然氣 NG1,0.001,m3,2025-01-01,2025-01-31,高雄廠\n"
    )
    result, _ = intake_and_run(csv, run_id="rc_bounds")
    values = [
        float(v)
        for v in calculated_rows(result)["calculated_tco2e"].tolist()
        if v is not None and not pd.isna(v)
    ]
    assert values
    assert all(math.isfinite(v) and v >= 0 for v in values)


def test_duplicate_looking_rows_are_both_counted_no_product_dedupe() -> None:
    csv = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,100,kWh,2025-01-01,2025-01-31,高雄廠\n"
        "外購電力,100,kWh,2025-01-01,2025-01-31,高雄廠\n"
    )
    result, intake = intake_and_run(csv, run_id="rc_dup")
    assert intake.accepted_count == 2
    assert len(calculated_rows(result)) == 2
    one = electricity_tco2e(Decimal("100"), Decimal("0.466"))
    _approx(calculated_tco2e_sum(result), one * 2, places=6)


def test_blocked_display_is_not_zero() -> None:
    result, _ = intake_and_run(MIXED_CSV, run_id="rc_zero_ui")
    overview = build_activity_overview(result)
    steel = overview[overview["activity_type"] == "purchased_steel"]
    assert not steel.empty
    value = steel.iloc[0]["calculated_tco2e"]
    assert value is None or pd.isna(value)
    assert str(steel.iloc[0]["calculation_status"]) != "calculated"
    label = str(steel.iloc[0]["calculation_label"])
    assert "0 tCO" not in label
    ng_unknown = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "天然氣,10,m3,2025-01-01,2025-01-31,高雄廠\n"
    )
    blocked, _ = intake_and_run(
        ng_unknown, run_id="rc_ng_zero_ui", natural_gas_subtype="unknown"
    )
    ng = build_activity_overview(blocked).iloc[0]
    assert ng["calculated_tco2e"] is None or pd.isna(ng["calculated_tco2e"])
    assert "尚未" in str(ng["calculation_label"]) or "確認" in str(
        ng["calculation_label"]
    )


def test_fuel_provenance_complete_for_calculated_rows() -> None:
    csv = (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "天然氣 NG1,50,m3,2025-01-01,2025-01-31,高雄廠\n"
        "柴油,20,L,2025-01-01,2025-01-31,高雄廠\n"
        "外購電力,10,kWh,2025-01-01,2025-01-31,高雄廠\n"
    )
    result, _ = intake_and_run(csv, run_id="rc_prov")
    required_fuel = (
        "heating_value_id",
        "heating_value_source_reference_id",
        "engineering_conversion_id",
        "co2_factor_id",
        "ch4_factor_id",
        "n2o_factor_id",
        "formula_id",
        "gwp_source_reference_id",
    )
    calcs = calculated_rows(result)
    fuels = calcs[calcs["activity_type"].isin(["natural_gas", "diesel"])]
    assert len(fuels) == 2
    for _, row in fuels.iterrows():
        for field in required_fuel:
            assert str(row.get(field) or "").strip(), f"missing {field}"
        assert Decimal(str(row["ch4_gwp"])) == GWP_CH4
        assert Decimal(str(row["n2o_gwp"])) == GWP_N2O
        trace = json.loads(str(row["calculation_trace"]))
        assert trace["energy"]["conversion_id"]
        assert trace["gases"]["CO2"]["factor_id"]
        assert trace["formula_id"]
    elec = calcs[calcs["activity_type"] == "grid_electricity"].iloc[0]
    assert str(elec["factor_id"]).strip()
    assert str(elec["source_reference_id"]).strip()


def test_analysis_makes_zero_live_network_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _boom(*args: object, **kwargs: object) -> None:
        calls.append(repr(args))
        raise AssertionError("network I/O during analysis")

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    monkeypatch.setattr("urllib.request.urlretrieve", _boom)
    result, _ = intake_and_run(ELEC_2024_CSV, run_id="rc_offline")
    assert not calls
    assert not calculated_rows(result).empty
    src = (REPO_ROOT / "src/carbon_ledger/pipeline.py").read_text(encoding="utf-8")
    assert "urllib" not in src
    assert "requests" not in src


def test_pipeline_exception_maps_to_customer_safe_error() -> None:
    message = customer_safe_analysis_error(RuntimeError("boom traceback"), "zh-TW")
    assert "traceback" not in message.lower()
    assert "分析未完成" in message


def test_invalid_upload_schema_fails_closed() -> None:
    csv = "說明\n這不是活動資料\n"
    table = parse_uploaded_table(file_name="bad.csv", data=csv.encode("utf-8"))
    with pytest.raises(IntakeError):
        build_and_validate_intake(table, mapping_for(table), metadata())


def test_mutation_ch4_gwp_29_is_detected(tmp_path: Path) -> None:
    root = _copy_repo(tmp_path)
    gwp_path = root / "data" / "reference" / "gwp_values.csv"
    frame = pd.read_csv(gwp_path, dtype=str)
    mask = frame["gwp_id"] == "gwp_ar5_ch4_fuel_combustion"
    frame.loc[mask, "gwp_value"] = "29"
    frame.to_csv(gwp_path, index=False)
    csv = NG_CSV.format(
        activity="天然氣 NG1", qty="8000", start="2025-01-01", end="2025-01-31"
    )
    mutated, _ = intake_and_run(csv, run_id="mut_gwp", repo_root=root)
    official = ng1_tco2e(Decimal("8000"))
    with pytest.raises(AssertionError):
        rows = calculated_rows(mutated)
        assert not rows.empty
        _approx(Decimal(str(rows.iloc[0]["calculated_tco2e"])), official)


def test_mutation_ng1_heating_value_is_detected(tmp_path: Path) -> None:
    root = _copy_repo(tmp_path)
    path = root / "data" / "reference" / "fuel_heating_values.csv"
    frame = pd.read_csv(path, dtype=str)
    mask = frame["heating_value_id"] == "hv_tw_natural_gas_ng1_2025"
    frame.loc[mask, "heating_value"] = "8000"
    frame.to_csv(path, index=False)
    csv = NG_CSV.format(
        activity="天然氣 NG1", qty="8000", start="2025-01-01", end="2025-01-31"
    )
    mutated, _ = intake_and_run(csv, run_id="mut_ng1", repo_root=root)
    official = ng1_tco2e(Decimal("8000"))
    with pytest.raises(AssertionError):
        rows = calculated_rows(mutated)
        assert not rows.empty
        _approx(Decimal(str(rows.iloc[0]["calculated_tco2e"])), official)


def test_mutation_diesel_heating_value_is_detected(tmp_path: Path) -> None:
    root = _copy_repo(tmp_path)
    path = root / "data" / "reference" / "fuel_heating_values.csv"
    frame = pd.read_csv(path, dtype=str)
    mask = frame["heating_value_id"] == "hv_tw_diesel_l_2025"
    frame.loc[mask, "heating_value"] = "8000"
    frame.to_csv(path, index=False)
    csv = DIESEL_CSV.format(qty="1200", start="2025-01-01", end="2025-01-31")
    mutated, _ = intake_and_run(csv, run_id="mut_diesel", repo_root=root)
    official = diesel_tco2e(Decimal("1200"))
    with pytest.raises(AssertionError):
        rows = calculated_rows(mutated)
        assert not rows.empty
        _approx(Decimal(str(rows.iloc[0]["calculated_tco2e"])), official)


def test_mutation_electricity_2024_factor_is_detected(tmp_path: Path) -> None:
    root = _copy_repo(tmp_path)
    path = root / "data" / "reference" / "emission_factors.csv"
    frame = pd.read_csv(path, dtype=str)
    mask = frame["factor_id"] == "ef_tw_grid_electricity_2024"
    frame.loc[mask, "factor_value"] = "0.500"
    frame.to_csv(path, index=False)
    mutated, _ = intake_and_run(ELEC_2024_CSV, run_id="mut_elec", repo_root=root)
    official = electricity_tco2e(Decimal("50000"))
    with pytest.raises(AssertionError):
        rows = calculated_rows(mutated)
        assert not rows.empty
        _approx(Decimal(str(rows.iloc[0]["calculated_tco2e"])), official)


def test_mutation_blocked_contributing_zero_is_detected() -> None:
    result, _ = intake_and_run(MIXED_CSV, run_id="mut_zero")
    mutated = result.calculation_results.copy()
    blocked = mutated["calculation_status"].astype(str) != "calculated"
    mutated.loc[blocked, "calculated_tco2e"] = 0.0

    class _Mutated:
        calculation_results = mutated
        activity_records_accepted = result.activity_records_accepted
        ghg_evaluations = result.ghg_evaluations
        core_qa_issues = result.core_qa_issues
        include_ghg = True
        include_cbam = False
        include_ifrs_s2 = True

    with pytest.raises(AssertionError):
        assert_blocked_not_zero(_Mutated())


def test_error_injection_missing_heating_and_gwp(tmp_path: Path) -> None:
    root = _copy_repo(tmp_path)
    heating = pd.read_csv(
        root / "data" / "reference" / "fuel_heating_values.csv", dtype=str
    )
    heating = heating[heating["fuel_type"] != "natural_gas"]
    heating.to_csv(root / "data" / "reference" / "fuel_heating_values.csv", index=False)
    csv = NG_CSV.format(
        activity="天然氣 NG1", qty="10", start="2025-01-01", end="2025-01-31"
    )
    result, _ = intake_and_run(csv, run_id="err_hv", repo_root=root)
    assert str(result.calculation_results.iloc[0]["calculation_status"]) != "calculated"
    assert_blocked_not_zero(result)

    root2 = _copy_repo(tmp_path / "gwp")
    gwp = pd.read_csv(root2 / "data" / "reference" / "gwp_values.csv", dtype=str)
    gwp = gwp[gwp["gas"] != "CH4"]
    gwp.to_csv(root2 / "data" / "reference" / "gwp_values.csv", index=False)
    missing_gwp, _ = intake_and_run(csv, run_id="err_gwp", repo_root=root2)
    assert str(missing_gwp.calculation_results.iloc[0]["calculation_status"]) != (
        "calculated"
    )


def test_error_injection_pipeline_exception_does_not_store_fake_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected pipeline failure")

    monkeypatch.setattr(
        "carbon_ledger.pipeline.calculate_activity_emissions",
        _boom,
    )
    with pytest.raises(RuntimeError, match="injected pipeline failure"):
        intake_and_run(ELEC_2024_CSV, run_id="err_pipe")
