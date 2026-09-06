"""Stage 4 GHG calculation coverage tests.

Official 114-year heating values live in the production registry.
Independent TEST_FIXTURE_NOT_OFFICIAL rows remain in tests/fixtures/stage4/
and must not be treated as official evidence.
"""

from __future__ import annotations

import json
import shutil
from decimal import Decimal
from pathlib import Path

import pandas as pd

from carbon_ledger.calculate import (
    COMBUSTION_FORMULA_ID,
    COMBUSTION_FORMULA_VERSION,
    FORMULA_ID,
    calculate_activity_emissions,
)
from carbon_ledger.factors import validate_factor_registry
from carbon_ledger.heating import (
    heating_value_has_complete_provenance,
    select_heating_value,
)
from carbon_ledger.match_factors import match_activity_factors
from carbon_ledger.pipeline import run_demo_pipeline, run_uploaded_pipeline
from carbon_ledger.reference_sync import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_CANDIDATE,
    LIFECYCLE_REJECTED,
    WRONG_DOCUMENT_FOR_SOURCE,
    validate_candidate_row,
    validate_candidates,
)
from carbon_ledger.ui.view_models import (
    calculated_emissions_by_ghg_scope,
    calculated_emissions_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_REFERENCE = REPO_ROOT / "data" / "reference"
STAGE4_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "stage4"
KCAL_TO_TJ = Decimal("4.1868E-9")
TEST_HV_NG = Decimal("9000")
TEST_HV_DIESEL = Decimal("8000")
OFFICIAL_HV_DIESEL = Decimal("8636")
OFFICIAL_HV_NG1_LOW = Decimal("8067")
OFFICIAL_HV_NG1_HIGH = Decimal("8963")
OFFICIAL_HV_NG2_LOW = Decimal("8728")
OFFICIAL_HV_NG2_HIGH = Decimal("9698")
OFFICIAL_HV_SNAPSHOT = "snap_src_tw_moenv_fuel_heating_values_80585dc0f2bd"
OFFICIAL_HV_SHA256 = (
    "80585dc0f2bd92f6abe0405a9855ccace2bc745e92b7f1be9b5c67e8cdb5c8c7"
)
NG_M3 = Decimal("8000")
DIESEL_L = Decimal("1200")
CO2_NG = Decimal("56100")
CH4_NG = Decimal("1")
N2O_NG = Decimal("0.1")
CO2_DIESEL = Decimal("74100")
CH4_DIESEL = Decimal("3.9")
N2O_DIESEL = Decimal("3.9")
GWP_CH4_COMBUSTION = Decimal("28")
GWP_N2O = Decimal("265")
GWP_CO2 = Decimal("1")
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00")


def _expected_combustion(
    activity: Decimal,
    heating_value: Decimal,
    co2: Decimal,
    ch4: Decimal,
    n2o: Decimal,
) -> dict[str, Decimal]:
    energy_kcal = activity * heating_value
    energy_tj = energy_kcal * KCAL_TO_TJ
    co2_kg = energy_tj * co2
    ch4_kg = energy_tj * ch4
    n2o_kg = energy_tj * n2o
    co2e_co2 = co2_kg * GWP_CO2
    co2e_ch4 = ch4_kg * GWP_CH4_COMBUSTION
    co2e_n2o = n2o_kg * GWP_N2O
    kg = co2e_co2 + co2e_ch4 + co2e_n2o
    return {
        "energy_kcal": energy_kcal,
        "energy_tj": energy_tj,
        "co2_kg": co2_kg,
        "ch4_kg": ch4_kg,
        "n2o_kg": n2o_kg,
        "co2e_from_co2_kg": co2e_co2,
        "co2e_from_ch4_kg": co2e_ch4,
        "co2e_from_n2o_kg": co2e_n2o,
        "kgco2e": kg,
        "tco2e": kg / Decimal("1000"),
    }


def _seed_repo_with_test_heating(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "config", root / "config")
    shutil.copytree(LIVE_REFERENCE, root / "data" / "reference")
    heating = pd.read_csv(STAGE4_FIXTURES / "fuel_heating_values.csv", dtype=str)
    heating.to_csv(root / "data" / "reference" / "fuel_heating_values.csv", index=False)
    refs = pd.read_csv(
        root / "data" / "reference" / "regulatory_references.csv", dtype=str
    )
    extra = pd.DataFrame(
        [
            {
                "reference_id": "ref_test_fixture_heating_values_2025",
                "framework": "corporate_ghg",
                "title": "TEST FIXTURE heating values (not official)",
                "publisher": "TEST_FIXTURE_NOT_OFFICIAL",
                "identifier": "",
                "publication_date": "2025-01-01",
                "effective_from": "2025-01-01",
                "authority_level": "test_fixture",
                "binding_status": "test_only",
                "source_location": "tests/fixtures/stage4/fuel_heating_values.csv",
                "notes": (
                    "TEST_FIXTURE_NOT_OFFICIAL. Not the 114-year MOENV "
                    "heating-value announcement."
                ),
            }
        ]
    )
    refs = pd.concat([refs, extra], ignore_index=True)
    refs.to_csv(root / "data" / "reference" / "regulatory_references.csv", index=False)
    return root


def _activity(
    *,
    record_id: str,
    activity_type: str,
    unit: str,
    value: float,
    process_use: str,
    start: str,
    end: str,
    record_type: str = "emission_activity",
    fuel_subtype: str = "",
) -> dict[str, object]:
    row: dict[str, object] = {
        "record_id": record_id,
        "source_document_id": f"doc_{record_id}",
        "record_type": record_type,
        "activity_type": activity_type,
        "unit": unit,
        "normalized_unit": unit,
        "activity_value": value,
        "process_use": process_use,
        "activity_start_date": pd.Timestamp(start),
        "activity_end_date": pd.Timestamp(end),
        "organizational_boundary_status": "inside",
        "ownership_control": "owned",
    }
    if fuel_subtype:
        row["fuel_subtype"] = fuel_subtype
    return row


def _normalized_from_activity(row: dict[str, object]) -> dict[str, object]:
    return {
        "record_id": row["record_id"],
        "activity_type": row["activity_type"],
        "original_value": row["activity_value"],
        "original_unit": row["unit"],
        "normalized_value": row["activity_value"],
        "normalized_unit": row["unit"],
        "normalization_status": "already_canonical",
        "normalization_reason": "test",
        "activity_start_date": row["activity_start_date"],
        "activity_end_date": row["activity_end_date"],
    }


def _run_calc(
    registry,
    activities: pd.DataFrame,
) -> tuple[pd.DataFrame, object]:
    records = activities.to_dict("records")
    normalized = pd.DataFrame(
        [_normalized_from_activity(row) for row in records]
    )
    matching = match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
        heating_values=registry.fuel_heating_values,
    )
    return calculate_activity_emissions(
        normalized,
        matching.candidate_matches,
        matching.activity_readiness,
        registry.emission_factors,
        heating_values=registry.fuel_heating_values,
        gwp_values=registry.gwp_values,
        engineering_conversions=registry.engineering_conversions,
        activity_records=activities,
    ), matching


def test_mislabeled_heating_value_snapshot_is_not_activated() -> None:
    candidates = pd.read_csv(LIVE_REFERENCE / "reference_candidates.csv", dtype=str)
    row = candidates.loc[
        candidates["candidate_id"] == "cand_review_f809a27150c0"
    ].iloc[0]
    assert row["lifecycle_status"] == LIFECYCLE_REJECTED
    assert row["lifecycle_status"] != LIFECYCLE_ACTIVE
    assert "WRONG_DOCUMENT_FOR_SOURCE" in row["reason"]


def test_revalidating_mislabeled_heating_value_keeps_wrong_document(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    shutil.copytree(LIVE_REFERENCE, root / "data" / "reference")
    candidates_csv = root / "data" / "reference" / "reference_candidates.csv"
    frame = pd.read_csv(candidates_csv, dtype=str)
    mask = frame["candidate_id"] == "cand_review_f809a27150c0"
    frame.loc[mask, "reason"] = "factor_value is not numeric"
    frame.loc[mask, "validation_messages"] = "factor_value is not numeric"
    frame.to_csv(candidates_csv, index=False)
    validate_candidates(
        candidates_csv,
        candidate_ids=["cand_review_f809a27150c0"],
    )
    row = pd.read_csv(candidates_csv, dtype=str).loc[mask].iloc[0]
    assert WRONG_DOCUMENT_FOR_SOURCE in row["reason"]
    assert WRONG_DOCUMENT_FOR_SOURCE in row["validation_messages"]
    assert row["lifecycle_status"] == LIFECYCLE_REJECTED
    assert row["lifecycle_status"] != LIFECYCLE_ACTIVE
    snaps = pd.read_csv(
        root / "data" / "reference" / "reference_snapshots.csv", dtype=str
    )
    snap = snaps.loc[
        snaps["snapshot_id"] == "snap_src_tw_moenv_fuel_heating_values_f809a27150c0"
    ].iloc[0]
    assert WRONG_DOCUMENT_FOR_SOURCE in snap["notes"]


def test_heating_value_emission_factor_pdf_fails_closed_as_wrong_document() -> None:
    locator = (
        "https://ghgregistry.moenv.gov.tw/upload/Tools/AI/"
        "113%E5%B9%B42%E6%9C%885%E6%97%A5%E5%85%AC%E5%91%8A"
        "%E6%BA%AB%E5%AE%A4%E6%B0%A3%E9%AB%94%E6%8E%92%E6%94%BE"
        "%E4%BF%82%E6%95%B8.pdf"
    )
    issues = validate_candidate_row(
        {
            "lifecycle_status": LIFECYCLE_CANDIDATE,
            "reference_type": "fuel_heating_values",
            "source_id": "src_tw_moenv_fuel_heating_values",
            "source_locator": locator,
            "source_url": locator,
            "source_location": locator,
            "factor_value": "",
            "factor_year": "",
            "geography": "",
            "factor_category": "",
            "numerator_unit": "",
            "factor_unit": "",
            "snapshot_id": "snap_src_tw_moenv_fuel_heating_values_f809a27150c0",
            "parser_version": "reference_sync_v1",
            "source_sha256": "f809a27150c014e1cb3bde3133cc433a8be5fe1f14105e63",
            "reason": "factor_value is not numeric",
            "notes": "Misclassified heating-value candidate.",
        }
    )
    assert WRONG_DOCUMENT_FOR_SOURCE in issues
    assert issues[0] == WRONG_DOCUMENT_FOR_SOURCE
    assert "factor_value is not numeric" in issues


def test_emission_factor_pdf_cannot_satisfy_heating_value_dependency() -> None:
    snaps = pd.read_csv(LIVE_REFERENCE / "reference_snapshots.csv", dtype=str)
    row = snaps.loc[
        snaps["snapshot_id"] == "snap_src_tw_moenv_fuel_heating_values_f809a27150c0"
    ].iloc[0]
    assert "113" in row["retrieved_url"] or "排放係數" in row["retrieved_url"]
    assert "WRONG_DOCUMENT_FOR_SOURCE" in row["notes"]
    heating = pd.read_csv(LIVE_REFERENCE / "fuel_heating_values.csv", dtype=str)
    ready = heating.loc[heating["status"].astype(str) == "ready"]
    assert not ready.empty
    assert "snap_src_tw_moenv_fuel_heating_values_f809a27150c0" not in set(
        ready["snapshot_id"].astype(str)
    )
    assert OFFICIAL_HV_SNAPSHOT in set(ready["snapshot_id"].astype(str))


def test_ready_heating_value_requires_verified_source_metadata(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    heating_path = root / "data" / "reference" / "fuel_heating_values.csv"
    heating = pd.read_csv(heating_path, dtype=str)
    heating.loc[heating["fuel_type"] == "natural_gas", "authority"] = ""
    heating.loc[heating["fuel_type"] == "natural_gas", "source_locator"] = ""
    heating.to_csv(heating_path, index=False)
    registry = validate_factor_registry(root / "data" / "reference")
    assert not registry.issues.empty
    codes = set(registry.issues["issue_code"])
    assert "INCOMPLETE_HEATING_VALUE_PROVENANCE" in codes
    incomplete = registry.fuel_heating_values.iloc[0]
    assert heating_value_has_complete_provenance(incomplete) is False


def test_incorrect_year_heating_value_cannot_match(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    registry = validate_factor_registry(root / "data" / "reference")
    selected = select_heating_value(
        registry.fuel_heating_values,
        fuel_type="natural_gas",
        activity_start="2024-01-01",
        activity_end="2024-01-31",
    )
    assert selected.status == "missing"
    assert selected.row is None


def test_2025_heating_value_does_not_unblock_2024_demo(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    shutil.copytree(REPO_ROOT / "data" / "raw", root / "data" / "raw")
    result = run_demo_pipeline(
        root,
        run_id="stage4_demo_2024",
        ingested_at=pd.Timestamp("2024-02-01T00:00:00"),
    )
    gas = result.calculation_results.loc[
        result.calculation_results["record_id"] == "rec_gas_001"
    ].iloc[0]
    diesel = result.calculation_results.loc[
        result.calculation_results["record_id"] == "rec_diesel_001"
    ].iloc[0]
    elec = result.calculation_results.loc[
        result.calculation_results["record_id"] == "rec_electricity_001"
    ].iloc[0]
    assert elec["calculation_status"] == "calculated"
    assert float(elec["calculated_tco2e"]) == 23.7
    assert gas["calculation_status"] == "blocked_missing_conversion"
    assert diesel["calculation_status"] == "blocked_missing_conversion"
    assert pd.isna(gas["calculated_tco2e"])
    assert pd.isna(diesel["calculated_tco2e"])


def test_2025_natural_gas_calculates_with_test_heating_value(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    registry = validate_factor_registry(root / "data" / "reference")
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_ng_2025",
                activity_type="natural_gas",
                unit="m3",
                value=8000.0,
                process_use="heat_treatment",
                start="2025-01-01",
                end="2025-01-31",
            )
        ]
    )
    result, matching = _run_calc(registry, activities)
    row = result.iloc[0]
    assert matching.activity_readiness.iloc[0]["calculation_readiness"] == "ready"
    assert row["calculation_status"] == "calculated"
    assert row["formula_id"] == COMBUSTION_FORMULA_ID
    assert row["formula_version"] == COMBUSTION_FORMULA_VERSION
    expected = _expected_combustion(NG_M3, TEST_HV_NG, CO2_NG, CH4_NG, N2O_NG)
    assert abs(
        Decimal(str(row["energy_tj"])) - expected["energy_tj"]
    ) < Decimal("1e-18")
    assert abs(Decimal(str(row["co2_kg"])) - expected["co2_kg"]) < Decimal("1e-8")
    assert abs(Decimal(str(row["ch4_kg"])) - expected["ch4_kg"]) < Decimal("1e-12")
    assert abs(Decimal(str(row["n2o_kg"])) - expected["n2o_kg"]) < Decimal("1e-12")
    assert float(row["ch4_gwp"]) == 28.0
    assert float(row["n2o_gwp"]) == 265.0
    assert abs(
        Decimal(str(row["calculated_kgco2e"])) - expected["kgco2e"]
    ) < Decimal("1e-6")
    assert abs(
        Decimal(str(row["co2e_from_co2_kg"]))
        + Decimal(str(row["co2e_from_ch4_kg"]))
        + Decimal(str(row["co2e_from_n2o_kg"]))
        - Decimal(str(row["calculated_kgco2e"]))
    ) < Decimal("1e-8")
    assert abs(
        Decimal(str(row["calculated_tco2e"])) - expected["tco2e"]
    ) < Decimal("1e-9")
    assert row["heating_value_id"] == "hv_test_natural_gas_2025"
    assert row["co2_factor_id"] == "ef_tw_natural_gas_stationary_co2_2024"
    assert row["ch4_factor_id"] == "ef_tw_natural_gas_stationary_ch4_2024"
    assert row["n2o_factor_id"] == "ef_tw_natural_gas_stationary_n2o_2024"
    assert row["gwp_source_reference_id"] == "ref_tw_moenv_2024_emission_factors"
    trace = json.loads(row["calculation_trace"])
    assert trace["formula_id"] == COMBUSTION_FORMULA_ID
    assert Decimal(trace["gases"]["CH4"]["gwp"]) == GWP_CH4_COMBUSTION
    assert Decimal(trace["total"]["kgco2e"]) == expected["kgco2e"]


def test_2025_generic_natural_gas_requires_subtype() -> None:
    registry = validate_factor_registry(LIVE_REFERENCE)
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_ng_2025_blocked",
                activity_type="natural_gas",
                unit="m3",
                value=8000.0,
                process_use="heat_treatment",
                start="2025-01-01",
                end="2025-01-31",
            )
        ]
    )
    result, matching = _run_calc(registry, activities)
    row = result.iloc[0]
    assert (
        matching.activity_readiness.iloc[0]["calculation_readiness"]
        == "blocked_natural_gas_type_required"
    )
    assert row["calculation_status"] == "blocked_natural_gas_type_required"
    assert pd.isna(row["calculated_kgco2e"])
    assert pd.isna(row["calculated_tco2e"])


def test_missing_one_gas_factor_blocks_partial_total(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    factors_path = root / "data" / "reference" / "emission_factors.csv"
    factors = pd.read_csv(factors_path, dtype=str)
    factors = factors.loc[
        factors["factor_id"] != "ef_tw_natural_gas_stationary_n2o_2024"
    ]
    factors.to_csv(factors_path, index=False)
    registry = validate_factor_registry(root / "data" / "reference")
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_ng_incomplete",
                activity_type="natural_gas",
                unit="m3",
                value=8000.0,
                process_use="heat_treatment",
                start="2025-01-01",
                end="2025-01-31",
            )
        ]
    )
    result, matching = _run_calc(registry, activities)
    assert (
        matching.activity_readiness.iloc[0]["calculation_readiness"]
        == "blocked_incomplete_gas_factors"
    )
    assert result.iloc[0]["calculation_status"] == "blocked_incomplete_gas_factors"
    assert pd.isna(result.iloc[0]["calculated_tco2e"])


def test_conflicting_gas_factor_versions_are_blocked(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    factors_path = root / "data" / "reference" / "emission_factors.csv"
    factors = pd.read_csv(factors_path, dtype=str)
    mask = factors["factor_id"] == "ef_tw_natural_gas_stationary_ch4_2024"
    factors.loc[mask, "source_reference_id"] = "ref_tw_moea_2024_electricity_factor"
    factors.loc[mask, "factor_year"] = "other_version"
    factors.to_csv(factors_path, index=False)
    registry = validate_factor_registry(root / "data" / "reference")
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_ng_conflict",
                activity_type="natural_gas",
                unit="m3",
                value=8000.0,
                process_use="heat_treatment",
                start="2025-01-01",
                end="2025-01-31",
            )
        ]
    )
    result, matching = _run_calc(registry, activities)
    assert (
        matching.activity_readiness.iloc[0]["calculation_readiness"]
        == "blocked_conflicting_factor_group"
    )
    assert result.iloc[0]["calculation_status"] == "blocked_conflicting_factor_group"
    assert pd.isna(result.iloc[0]["calculated_kgco2e"])


def test_2025_company_vehicle_diesel_calculates(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    registry = validate_factor_registry(root / "data" / "reference")
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_diesel_2025",
                activity_type="diesel",
                unit="L",
                value=1200.0,
                process_use="company_vehicle",
                start="2025-06-01",
                end="2025-06-30",
            )
        ]
    )
    result, _matching = _run_calc(registry, activities)
    row = result.iloc[0]
    expected = _expected_combustion(
        DIESEL_L, TEST_HV_DIESEL, CO2_DIESEL, CH4_DIESEL, N2O_DIESEL
    )
    assert row["calculation_status"] == "calculated"
    assert row["formula_id"] == COMBUSTION_FORMULA_ID
    assert abs(
        Decimal(str(row["energy_tj"])) - expected["energy_tj"]
    ) < Decimal("1e-18")
    assert abs(Decimal(str(row["co2_kg"])) - expected["co2_kg"]) < Decimal("1e-8")
    assert float(row["ch4_gwp"]) == 28.0
    assert float(row["n2o_gwp"]) == 265.0
    assert abs(
        Decimal(str(row["calculated_kgco2e"])) - expected["kgco2e"]
    ) < Decimal("1e-6")
    assert row["co2_factor_id"] == "ef_tw_diesel_mobile_co2_2024"
    trace = json.loads(row["calculation_trace"])
    assert Decimal(trace["energy"]["multiplier"]) == KCAL_TO_TJ
    assert Decimal(trace["gases"]["CH4"]["gwp"]) == Decimal("28")


def test_non_company_vehicle_diesel_does_not_use_mobile_route(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    registry = validate_factor_registry(root / "data" / "reference")
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_diesel_generator",
                activity_type="diesel",
                unit="L",
                value=1200.0,
                process_use="stationary_generator",
                start="2025-06-01",
                end="2025-06-30",
            )
        ]
    )
    result, matching = _run_calc(registry, activities)
    assert matching.candidate_matches.empty
    assert result.iloc[0]["calculation_status"] == "no_factor_configured"
    assert pd.isna(result.iloc[0]["calculated_tco2e"])


def test_2024_diesel_does_not_use_2025_heating_value() -> None:
    registry = validate_factor_registry(LIVE_REFERENCE)
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_diesel_2024_blocked",
                activity_type="diesel",
                unit="L",
                value=1200.0,
                process_use="company_vehicle",
                start="2024-06-01",
                end="2024-06-30",
            )
        ]
    )
    result, _matching = _run_calc(registry, activities)
    assert result.iloc[0]["calculation_status"] == "blocked_missing_conversion"
    assert pd.isna(result.iloc[0]["calculated_tco2e"])


def test_2024_demo_electricity_still_23_7_tco2e() -> None:
    result = run_demo_pipeline(
        REPO_ROOT,
        run_id="stage4_elec_reg",
        ingested_at=pd.Timestamp("2024-02-01T00:00:00"),
    )
    row = result.calculation_results.loc[
        result.calculation_results["record_id"] == "rec_electricity_001"
    ].iloc[0]
    assert row["calculation_status"] == "calculated"
    assert row["formula_id"] == FORMULA_ID
    assert float(row["calculated_kgco2e"]) == 23700.0
    assert float(row["calculated_tco2e"]) == 23.7
    summary = calculated_emissions_summary(result)
    assert summary["calculated_tco2e"] == 23.7
    assert summary["calculated_row_count"] == 1


def test_hero_countup_script_unchanged() -> None:
    import hashlib

    path = REPO_ROOT / "src" / "carbon_ledger" / "ui" / "hero_emissions_countup.js"
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha == "70cd43b7f1fa2bedf4485bc7846278b736e1c183961c6c7117d6cc8b5f5828c0"


def test_2025_enterprise_electricity_factor_is_0_466(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    registry = validate_factor_registry(root / "data" / "reference")
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_elec_2025",
                activity_type="grid_electricity",
                unit="kWh",
                value=1000.0,
                process_use="general_factory",
                start="2025-03-01",
                end="2025-03-31",
            )
        ]
    )
    result, matching = _run_calc(registry, activities)
    row = result.iloc[0]
    assert matching.candidate_matches.iloc[0]["factor_id"] == (
        "ef_tw_grid_electricity_2025_industrial_enterprise_inventory"
    )
    assert float(row["factor_value"]) == 0.466
    assert float(row["calculated_kgco2e"]) == 466.0


def test_public_sales_and_residential_factors_are_not_substituted(
    tmp_path: Path,
) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    factors_path = root / "data" / "reference" / "emission_factors.csv"
    factors = pd.read_csv(factors_path, dtype=str)
    extras = pd.DataFrame(
        [
            {
                **factors.loc[
                    factors["factor_id"]
                    == "ef_tw_grid_electricity_2025_industrial_enterprise_inventory"
                ]
                .iloc[0]
                .to_dict(),
                "factor_id": "ef_tw_grid_electricity_2025_public_sales",
                "factor_value": "0.467",
                "notes": "category=public_sales_average; test decoy",
            },
            {
                **factors.loc[
                    factors["factor_id"]
                    == "ef_tw_grid_electricity_2025_industrial_enterprise_inventory"
                ]
                .iloc[0]
                .to_dict(),
                "factor_id": "ef_tw_grid_electricity_2025_residential",
                "factor_value": "0.471",
                "notes": "category=residential; test decoy",
            },
        ]
    )
    factors = pd.concat([factors, extras], ignore_index=True)
    factors.to_csv(factors_path, index=False)
    registry = validate_factor_registry(root / "data" / "reference")
    factory = pd.DataFrame(
        [
            _activity(
                record_id="rec_elec_factory",
                activity_type="grid_electricity",
                unit="kWh",
                value=1000.0,
                process_use="general_factory",
                start="2025-03-01",
                end="2025-03-31",
            )
        ]
    )
    unknown = pd.DataFrame(
        [
            _activity(
                record_id="rec_elec_unknown",
                activity_type="grid_electricity",
                unit="kWh",
                value=1000.0,
                process_use="",
                start="2025-03-01",
                end="2025-03-31",
            )
        ]
    )
    factory_result, factory_match = _run_calc(registry, factory)
    unknown_result, unknown_match = _run_calc(registry, unknown)
    assert factory_match.candidate_matches.iloc[0]["factor_id"].endswith(
        "industrial_enterprise_inventory"
    )
    assert float(factory_result.iloc[0]["factor_value"]) == 0.466
    assert unknown_match.candidate_matches.empty
    assert unknown_result.iloc[0]["calculation_status"] == "no_factor_configured"


def test_combustion_does_not_use_fossil_methane_gwp_30(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    registry = validate_factor_registry(root / "data" / "reference")
    fossil = registry.gwp_values.loc[
        registry.gwp_values["emission_context"] == "fossil_methane_process"
    ]
    assert float(fossil.iloc[0]["gwp_value"]) == 30.0
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_ng_gwp",
                activity_type="natural_gas",
                unit="m3",
                value=8000.0,
                process_use="heat_treatment",
                start="2025-01-01",
                end="2025-01-31",
            )
        ]
    )
    result, _matching = _run_calc(registry, activities)
    assert float(result.iloc[0]["ch4_gwp"]) == 28.0
    assert float(result.iloc[0]["ch4_gwp"]) != 30.0


def test_missing_gwp_blocks_calculation(tmp_path: Path) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    gwp_path = root / "data" / "reference" / "gwp_values.csv"
    gwp = pd.read_csv(gwp_path, dtype=str)
    gwp = gwp.loc[gwp["gwp_id"] != "gwp_ar5_ch4_fuel_combustion"]
    gwp.to_csv(gwp_path, index=False)
    registry = validate_factor_registry(root / "data" / "reference")
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_ng_no_gwp",
                activity_type="natural_gas",
                unit="m3",
                value=8000.0,
                process_use="heat_treatment",
                start="2025-01-01",
                end="2025-01-31",
            )
        ]
    )
    result, _matching = _run_calc(registry, activities)
    assert result.iloc[0]["calculation_status"] == "blocked_missing_gwp"
    assert pd.isna(result.iloc[0]["calculated_tco2e"])


def test_totals_sum_calculated_records_only_and_steel_stays_unsupported(
    tmp_path: Path,
) -> None:
    root = _seed_repo_with_test_heating(tmp_path)
    docs = pd.DataFrame(
        [
            {
                "source_document_id": "doc_a",
                "file_name": "a.csv",
                "document_type": "invoice",
            }
        ]
    )
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_ng_2025",
                activity_type="natural_gas",
                unit="m3",
                value=8000.0,
                process_use="heat_treatment",
                start="2025-01-01",
                end="2025-01-31",
            ),
            _activity(
                record_id="rec_diesel_2025",
                activity_type="diesel",
                unit="L",
                value=1200.0,
                process_use="company_vehicle",
                start="2025-06-01",
                end="2025-06-30",
            ),
            _activity(
                record_id="rec_elec_2025",
                activity_type="grid_electricity",
                unit="kWh",
                value=1000.0,
                process_use="general_factory",
                start="2025-03-01",
                end="2025-03-31",
            ),
            _activity(
                record_id="rec_steel_2025",
                activity_type="purchased_steel",
                unit="t",
                value=10.0,
                process_use="not_applicable",
                start="2025-01-01",
                end="2025-01-31",
                record_type="material_input",
            ),
        ]
    )
    result = run_uploaded_pipeline(
        root,
        run_id="stage4_scope",
        ingested_at=FIXED_INGESTED_AT,
        source_documents=docs,
        accepted_activities=activities,
        include_ghg=True,
    )
    calcs = result.calculation_results.set_index("record_id")
    assert calcs.loc["rec_ng_2025", "calculation_status"] == "calculated"
    assert calcs.loc["rec_diesel_2025", "calculation_status"] == "calculated"
    assert calcs.loc["rec_elec_2025", "calculation_status"] == "calculated"
    assert calcs.loc["rec_steel_2025", "calculation_status"] == "no_factor_configured"
    assert pd.isna(calcs.loc["rec_steel_2025", "calculated_tco2e"])
    blocked = calcs.loc[calcs["calculation_status"] != "calculated"]
    assert blocked["calculated_tco2e"].isna().all()
    summary = calculated_emissions_summary(result)
    expected_total = (
        float(calcs.loc["rec_ng_2025", "calculated_tco2e"])
        + float(calcs.loc["rec_diesel_2025", "calculated_tco2e"])
        + float(calcs.loc["rec_elec_2025", "calculated_tco2e"])
    )
    assert abs(summary["calculated_tco2e"] - expected_total) < 1e-9
    assert summary["calculated_row_count"] == 3
    scopes = calculated_emissions_by_ghg_scope(result)
    assert "scope_1" in scopes
    assert "scope_2" in scopes
    assert scopes["scope_1"] == (
        float(calcs.loc["rec_ng_2025", "calculated_tco2e"])
        + float(calcs.loc["rec_diesel_2025", "calculated_tco2e"])
    )
    assert scopes["scope_2"] == float(calcs.loc["rec_elec_2025", "calculated_tco2e"])
    assert "scope_3" not in scopes or scopes.get("scope_3", 0) == 0
    ng_trace = json.loads(calcs.loc["rec_ng_2025", "calculation_trace"])
    assert abs(
        float(ng_trace["total"]["tco2e"])
        - float(calcs.loc["rec_ng_2025", "calculated_tco2e"])
    ) < 1e-12


def test_production_heating_values_match_official_114() -> None:
    heating = pd.read_csv(LIVE_REFERENCE / "fuel_heating_values.csv", dtype=str)
    ready = heating.loc[heating["status"].astype(str) == "ready"]
    diesel = ready.loc[ready["fuel_type"].astype(str) == "diesel"].iloc[0]
    ng1 = ready.loc[ready["fuel_subtype"].astype(str) == "NG1"].iloc[0]
    ng2 = ready.loc[ready["fuel_subtype"].astype(str) == "NG2"].iloc[0]
    assert diesel["heating_value_id"] == "hv_tw_diesel_l_2025"
    assert Decimal(str(diesel["heating_value"])) == OFFICIAL_HV_DIESEL
    assert diesel["unit"] == "kcal/L"
    assert diesel["factor_year"] == "2025"
    assert ng1["heating_value_id"] == "hv_tw_natural_gas_ng1_2025"
    assert Decimal(str(ng1["heating_value"])) == OFFICIAL_HV_NG1_LOW
    assert Decimal(str(ng1["high_heating_value"])) == OFFICIAL_HV_NG1_HIGH
    assert ng1["unit"] == "kcal/m3"
    assert ng1["high_heating_value_unit"] == "kcal/m3"
    assert ng2["heating_value_id"] == "hv_tw_natural_gas_ng2_2025"
    assert Decimal(str(ng2["heating_value"])) == OFFICIAL_HV_NG2_LOW
    assert Decimal(str(ng2["high_heating_value"])) == OFFICIAL_HV_NG2_HIGH
    assert ng2["unit"] == "kcal/m3"
    for row in (diesel, ng1, ng2):
        assert row["snapshot_id"] == OFFICIAL_HV_SNAPSHOT
        assert row["snapshot_sha256"] == OFFICIAL_HV_SHA256
        assert "moenv_114_fuel_heating_values_2026-02-10.pdf" in row[
            "snapshot_local_path"
        ]
        assert row["source_reference_id"] == "ref_tw_moenv_114_fuel_heating_values"


def test_2025_production_ng1_calculates() -> None:
    registry = validate_factor_registry(LIVE_REFERENCE)
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_ng1_2025",
                activity_type="natural_gas",
                unit="m3",
                value=8000.0,
                process_use="heat_treatment",
                start="2025-01-01",
                end="2025-01-31",
                fuel_subtype="NG1",
            )
        ]
    )
    result, matching = _run_calc(registry, activities)
    row = result.iloc[0]
    expected = _expected_combustion(
        NG_M3, OFFICIAL_HV_NG1_LOW, CO2_NG, CH4_NG, N2O_NG
    )
    assert matching.activity_readiness.iloc[0]["calculation_readiness"] == "ready"
    assert row["calculation_status"] == "calculated"
    assert row["heating_value_id"] == "hv_tw_natural_gas_ng1_2025"
    assert Decimal(str(row["heating_value"])) == OFFICIAL_HV_NG1_LOW
    assert abs(Decimal(str(row["calculated_tco2e"])) - expected["tco2e"]) < Decimal(
        "1e-9"
    )
    trace = json.loads(row["calculation_trace"])
    assert trace["heating_value"]["snapshot_id"] == OFFICIAL_HV_SNAPSHOT
    assert trace["heating_value"]["snapshot_sha256"] == OFFICIAL_HV_SHA256
    assert trace["heating_value"]["high_heating_value"] == "8963"
    assert Decimal(trace["gases"]["CH4"]["gwp"]) == Decimal("28")
    assert Decimal(trace["gases"]["N2O"]["gwp"]) == Decimal("265")


def test_2025_production_ng2_calculates() -> None:
    registry = validate_factor_registry(LIVE_REFERENCE)
    activities = pd.DataFrame(
        [
            _activity(
                record_id="rec_ng2_2025",
                activity_type="natural_gas",
                unit="m3",
                value=8000.0,
                process_use="heat_treatment",
                start="2025-01-01",
                end="2025-01-31",
                fuel_subtype="NG2",
            )
        ]
    )
    result, _matching = _run_calc(registry, activities)
    row = result.iloc[0]
    expected = _expected_combustion(
        NG_M3, OFFICIAL_HV_NG2_LOW, CO2_NG, CH4_NG, N2O_NG
    )
    assert row["calculation_status"] == "calculated"
    assert row["heating_value_id"] == "hv_tw_natural_gas_ng2_2025"
    assert Decimal(str(row["heating_value"])) == OFFICIAL_HV_NG2_LOW
    assert abs(Decimal(str(row["calculated_tco2e"])) - expected["tco2e"]) < Decimal(
        "1e-9"
    )


def test_ng1_and_ng2_results_differ_for_same_volume() -> None:
    registry = validate_factor_registry(LIVE_REFERENCE)
    ng1, _ = _run_calc(
        registry,
        pd.DataFrame(
            [
                _activity(
                    record_id="rec_ng1_same",
                    activity_type="natural_gas",
                    unit="m3",
                    value=8000.0,
                    process_use="heat_treatment",
                    start="2025-01-01",
                    end="2025-01-31",
                    fuel_subtype="NG1",
                )
            ]
        ),
    )
    ng2, _ = _run_calc(
        registry,
        pd.DataFrame(
            [
                _activity(
                    record_id="rec_ng2_same",
                    activity_type="natural_gas",
                    unit="m3",
                    value=8000.0,
                    process_use="heat_treatment",
                    start="2025-01-01",
                    end="2025-01-31",
                    fuel_subtype="NG2",
                )
            ]
        ),
    )
    assert ng1.iloc[0]["calculation_status"] == "calculated"
    assert ng2.iloc[0]["calculation_status"] == "calculated"
    assert float(ng1.iloc[0]["calculated_tco2e"]) != float(
        ng2.iloc[0]["calculated_tco2e"]
    )


def test_unknown_natural_gas_subtype_is_blocked() -> None:
    registry = validate_factor_registry(LIVE_REFERENCE)
    result, _matching = _run_calc(
        registry,
        pd.DataFrame(
            [
                _activity(
                    record_id="rec_ng_unknown",
                    activity_type="natural_gas",
                    unit="m3",
                    value=8000.0,
                    process_use="heat_treatment",
                    start="2025-01-01",
                    end="2025-01-31",
                    fuel_subtype="unknown",
                )
            ]
        ),
    )
    assert result.iloc[0]["calculation_status"] == "blocked_natural_gas_type_required"
    assert pd.isna(result.iloc[0]["calculated_tco2e"])


def test_invalid_natural_gas_subtype_fails_review() -> None:
    registry = validate_factor_registry(LIVE_REFERENCE)
    result, matching = _run_calc(
        registry,
        pd.DataFrame(
            [
                _activity(
                    record_id="rec_ng_invalid",
                    activity_type="natural_gas",
                    unit="m3",
                    value=8000.0,
                    process_use="heat_treatment",
                    start="2025-01-01",
                    end="2025-01-31",
                    fuel_subtype="NG3",
                )
            ]
        ),
    )
    assert (
        matching.activity_readiness.iloc[0]["calculation_readiness"]
        == "factor_match_inconsistent"
    )
    assert result.iloc[0]["calculation_status"] == "factor_match_inconsistent"
    assert pd.isna(result.iloc[0]["calculated_tco2e"])


def test_2024_ng1_does_not_use_2025_heating_value() -> None:
    registry = validate_factor_registry(LIVE_REFERENCE)
    result, _matching = _run_calc(
        registry,
        pd.DataFrame(
            [
                _activity(
                    record_id="rec_ng1_2024",
                    activity_type="natural_gas",
                    unit="m3",
                    value=8000.0,
                    process_use="heat_treatment",
                    start="2024-01-01",
                    end="2024-01-31",
                    fuel_subtype="NG1",
                )
            ]
        ),
    )
    assert result.iloc[0]["calculation_status"] == "blocked_missing_conversion"
    assert pd.isna(result.iloc[0]["calculated_tco2e"])


def test_2025_production_diesel_calculates() -> None:
    registry = validate_factor_registry(LIVE_REFERENCE)
    result, _matching = _run_calc(
        registry,
        pd.DataFrame(
            [
                _activity(
                    record_id="rec_diesel_2025_official",
                    activity_type="diesel",
                    unit="L",
                    value=1200.0,
                    process_use="company_vehicle",
                    start="2025-06-01",
                    end="2025-06-30",
                )
            ]
        ),
    )
    row = result.iloc[0]
    expected = _expected_combustion(
        DIESEL_L, OFFICIAL_HV_DIESEL, CO2_DIESEL, CH4_DIESEL, N2O_DIESEL
    )
    assert row["calculation_status"] == "calculated"
    assert row["heating_value_id"] == "hv_tw_diesel_l_2025"
    assert Decimal(str(row["heating_value"])) == OFFICIAL_HV_DIESEL
    assert abs(Decimal(str(row["calculated_tco2e"])) - expected["tco2e"]) < Decimal(
        "1e-9"
    )
    trace = json.loads(row["calculation_trace"])
    assert trace["heating_value"]["snapshot_sha256"] == OFFICIAL_HV_SHA256
    assert Decimal(trace["gases"]["CH4"]["gwp"]) == Decimal("28")
    assert Decimal(trace["gases"]["N2O"]["gwp"]) == Decimal("265")


def test_live_2024_demo_fuels_remain_blocked_after_official_activation() -> None:
    result = run_demo_pipeline(
        REPO_ROOT,
        run_id="stage4_live_2024_isolation",
        ingested_at=pd.Timestamp("2024-02-01T00:00:00"),
    )
    gas = result.calculation_results.loc[
        result.calculation_results["record_id"] == "rec_gas_001"
    ].iloc[0]
    diesel = result.calculation_results.loc[
        result.calculation_results["record_id"] == "rec_diesel_001"
    ].iloc[0]
    steel = result.calculation_results.loc[
        result.calculation_results["record_id"] == "rec_steel_001"
    ].iloc[0]
    elec = result.calculation_results.loc[
        result.calculation_results["record_id"] == "rec_electricity_001"
    ].iloc[0]
    assert elec["calculation_status"] == "calculated"
    assert float(elec["calculated_tco2e"]) == 23.7
    assert gas["calculation_status"] == "blocked_missing_conversion"
    assert diesel["calculation_status"] == "blocked_missing_conversion"
    assert steel["calculation_status"] == "no_factor_configured"
    assert pd.isna(gas["calculated_tco2e"])
    assert pd.isna(diesel["calculated_tco2e"])
