"""Tests for Phase 5B deterministic emission-factor matching."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pandas as pd

from carbon_ledger.factors import validate_factor_registry
from carbon_ledger.ingest import ingest_evidence
from carbon_ledger.match_factors import match_activity_factors
from carbon_ledger.normalize import normalize_activity_records
from tests.reference_fixtures import (
    BASELINE_REFERENCE_DIR,
    copy_baseline_reference_tree,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
REFERENCE_DIR = BASELINE_REFERENCE_DIR
FIXED_INGESTED_AT = pd.Timestamp("2024-02-01T12:00:00")
FIXED_RUN_ID = "test_run_phase5b_001"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_raw_tree(tmp_path: Path) -> Path:
    destination = tmp_path / "raw"
    shutil.copytree(RAW_DIR, destination)
    return destination


def _copy_reference_tree(tmp_path: Path) -> Path:
    destination = tmp_path / "reference"
    return copy_baseline_reference_tree(destination)


def _baseline_matching(tmp_path: Path):
    raw = _copy_raw_tree(tmp_path)
    ingestion = ingest_evidence(
        raw_directory=raw,
        ingestion_run_id=FIXED_RUN_ID,
        ingested_at=FIXED_INGESTED_AT,
    )
    accepted = ingestion.activity_records.accepted
    normalized = normalize_activity_records(accepted)
    # Join normalized units onto accepted activity facts for matching.
    activities = accepted.merge(
        normalized[
            ["record_id", "normalized_unit", "normalization_status"]
        ],
        on="record_id",
        how="left",
    )
    registry = validate_factor_registry(REFERENCE_DIR)
    return match_activity_factors(
        activity_records=activities,
        emission_factors=registry.emission_factors,
        calculation_dependencies=registry.calculation_dependencies,
    )


def _simple_activity(**overrides: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "record_id": "rec_test_001",
        "activity_type": "grid_electricity",
        "unit": "kWh",
        "normalized_unit": "kWh",
        "process_use": "general_factory",
        "activity_start_date": pd.Timestamp("2024-01-01"),
        "activity_end_date": pd.Timestamp("2024-01-31"),
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_electricity_matches_exactly_one_factor(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    electricity = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_electricity_001"
    ]
    assert len(electricity) == 1


def test_electricity_factor_is_expected_id(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    electricity = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_electricity_001"
    ].iloc[0]
    assert electricity["factor_id"] == "ef_tw_grid_electricity_2024"


def test_electricity_readiness_is_ready(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    row = result.activity_readiness.loc[
        result.activity_readiness["record_id"] == "rec_electricity_001"
    ].iloc[0]
    assert row["calculation_readiness"] == "ready"


def test_electricity_requires_no_conversion(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    electricity = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_electricity_001"
    ].iloc[0]
    assert electricity["required_conversion"] == "not_required"
    assert electricity["match_status"] == "matched_ready"


def test_natural_gas_matches_three_gas_specific_factors(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    gas = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_gas_001"
    ]
    assert len(gas) == 3


def test_natural_gas_gases_are_co2_ch4_n2o(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    gas = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_gas_001"
    ]
    assert set(gas["gas"]) == {"CO2", "CH4", "N2O"}


def test_natural_gas_blocked_by_heating_value_dependency(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    gas = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_gas_001"
    ]
    assert (gas["match_status"] == "matched_blocked_dependency").all()
    assert (
        gas["required_conversion"]
        == "verified_natural_gas_heating_value_m3_to_TJ"
    ).all()
    readiness = result.activity_readiness.loc[
        result.activity_readiness["record_id"] == "rec_gas_001"
    ].iloc[0]
    assert readiness["calculation_readiness"] == "blocked_missing_conversion"
    assert (
        readiness["blocking_dependency"]
        == "verified_natural_gas_heating_value_m3_to_TJ"
    )


def test_diesel_matches_three_mobile_combustion_factors(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    diesel = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_diesel_001"
    ]
    assert len(diesel) == 3
    assert all("mobile" in factor_id for factor_id in diesel["factor_id"])


def test_diesel_gases_are_co2_ch4_n2o(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    diesel = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_diesel_001"
    ]
    assert set(diesel["gas"]) == {"CO2", "CH4", "N2O"}


def test_diesel_blocked_by_heating_value_dependency(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    diesel = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_diesel_001"
    ]
    assert (diesel["match_status"] == "matched_blocked_dependency").all()
    assert (
        diesel["required_conversion"]
        == "verified_diesel_heating_value_L_to_TJ"
    ).all()
    readiness = result.activity_readiness.loc[
        result.activity_readiness["record_id"] == "rec_diesel_001"
    ].iloc[0]
    assert readiness["calculation_readiness"] == "blocked_missing_conversion"
    assert (
        readiness["blocking_dependency"]
        == "verified_diesel_heating_value_L_to_TJ"
    )


def test_natural_gas_factors_not_matched_to_diesel(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    diesel = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_diesel_001"
    ]
    assert not any("natural_gas" in factor_id for factor_id in diesel["factor_id"])


def test_diesel_factors_not_matched_to_natural_gas(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    gas = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_gas_001"
    ]
    assert not any("diesel" in factor_id for factor_id in gas["factor_id"])


def test_purchased_steel_has_no_configured_factor(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    steel_candidates = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_steel_001"
    ]
    assert steel_candidates.empty
    readiness = result.activity_readiness.loc[
        result.activity_readiness["record_id"] == "rec_steel_001"
    ].iloc[0]
    assert readiness["calculation_readiness"] == "purchased_steel_category1"
    assert readiness["candidate_factor_count"] == 0


def test_production_output_is_not_emissions_activity(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    output_candidates = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_output_001"
    ]
    assert output_candidates.empty
    readiness = result.activity_readiness.loc[
        result.activity_readiness["record_id"] == "rec_output_001"
    ].iloc[0]
    assert readiness["calculation_readiness"] == "not_emissions_activity"


def test_unsupported_activity_type_remains_visible() -> None:
    registry = validate_factor_registry(REFERENCE_DIR)
    activities = _simple_activity(
        record_id="rec_unknown_001",
        activity_type="mystery_fuel",
        unit="kg",
        normalized_unit="kg",
    )
    result = match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
    )
    assert result.candidate_matches.empty
    readiness = result.activity_readiness.iloc[0]
    assert readiness["calculation_readiness"] == "unsupported_activity_type"
    assert readiness["record_id"] == "rec_unknown_001"


def test_inactive_factors_are_not_selected(tmp_path: Path) -> None:
    reference = _copy_reference_tree(tmp_path)
    path = reference / "emission_factors.csv"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    mask = frame["factor_id"] == "ef_tw_grid_electricity_2024"
    frame.loc[mask, "factor_status"] = "inactive"
    frame.to_csv(path, index=False)

    registry = validate_factor_registry(reference)
    activities = _simple_activity()
    result = match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
    )
    assert result.candidate_matches.empty
    assert (
        result.activity_readiness.iloc[0]["calculation_readiness"]
        == "no_factor_configured"
    )


def test_ready_factor_with_incompatible_denominator_not_marked_ready() -> None:
    registry = validate_factor_registry(REFERENCE_DIR)
    activities = _simple_activity(unit="MWh", normalized_unit="MWh")
    result = match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
    )
    assert result.candidate_matches.empty
    assert (
        result.activity_readiness.iloc[0]["calculation_readiness"]
        == "no_factor_configured"
    )
    assert "matched_ready" not in set(result.candidate_matches["match_status"])


def test_factor_outside_validity_period_is_not_selected() -> None:
    """Explicit electricity validity dates are still enforced when present."""
    registry = validate_factor_registry(REFERENCE_DIR)
    activities = _simple_activity(
        activity_start_date=pd.Timestamp("2025-01-01"),
        activity_end_date=pd.Timestamp("2025-01-31"),
    )
    result = match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
    )
    assert result.candidate_matches.empty


def test_blank_fuel_factor_dates_do_not_block_january_activities(
    tmp_path: Path,
) -> None:
    """Blank natural-gas/diesel validity dates do not assert an applicability period."""
    result = _baseline_matching(tmp_path)
    gas = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_gas_001"
    ]
    diesel = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_diesel_001"
    ]
    assert len(gas) == 3
    assert len(diesel) == 3


def test_candidate_output_is_deterministically_sorted(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    candidates = result.candidate_matches
    sorted_frame = candidates.sort_values(
        ["record_id", "factor_id", "gas"], kind="mergesort"
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(candidates, sorted_frame)


def test_readiness_output_preserves_one_row_per_activity(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    assert len(result.activity_readiness) == 5
    assert result.activity_readiness["record_id"].is_unique


def test_input_dataframes_are_not_mutated() -> None:
    registry = validate_factor_registry(REFERENCE_DIR)
    activities = _simple_activity()
    factors_before = registry.emission_factors.copy(deep=True)
    deps_before = registry.calculation_dependencies.copy(deep=True)
    activities_before = activities.copy(deep=True)

    match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
    )

    pd.testing.assert_frame_equal(activities, activities_before)
    pd.testing.assert_frame_equal(registry.emission_factors, factors_before)
    pd.testing.assert_frame_equal(
        registry.calculation_dependencies, deps_before
    )


def test_repeated_matching_produces_identical_outputs(tmp_path: Path) -> None:
    first = _baseline_matching(tmp_path / "a")
    second = _baseline_matching(tmp_path / "b")
    pd.testing.assert_frame_equal(
        first.candidate_matches, second.candidate_matches
    )
    pd.testing.assert_frame_equal(
        first.activity_readiness, second.activity_readiness
    )


def test_baseline_produces_seven_candidate_rows(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    assert len(result.candidate_matches) == 7


def test_baseline_produces_five_readiness_rows(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    assert len(result.activity_readiness) == 5
    readiness_counts = result.activity_readiness[
        "calculation_readiness"
    ].value_counts()
    assert readiness_counts.get("ready", 0) == 1
    assert readiness_counts.get("blocked_missing_conversion", 0) == 2
    assert readiness_counts.get("purchased_steel_category1", 0) == 1
    assert readiness_counts.get("not_emissions_activity", 0) == 1


def test_output_contains_no_calculated_tco2e(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    assert "calculated_tco2e" not in result.candidate_matches.columns
    assert "calculated_tco2e" not in result.activity_readiness.columns


def test_output_contains_no_ghg_scope(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    assert "ghg_scope" not in result.candidate_matches.columns
    assert "ghg_scope" not in result.activity_readiness.columns


def test_output_contains_no_cbam_data_role(tmp_path: Path) -> None:
    result = _baseline_matching(tmp_path)
    assert "cbam_data_role" not in result.candidate_matches.columns
    assert "cbam_data_role" not in result.activity_readiness.columns


def test_existing_raw_and_reference_files_remain_unchanged(tmp_path: Path) -> None:
    before_raw = {
        path.relative_to(RAW_DIR).as_posix(): _sha256(path)
        for path in RAW_DIR.rglob("*")
        if path.is_file()
    }
    before_ref = {
        path.relative_to(REFERENCE_DIR).as_posix(): _sha256(path)
        for path in REFERENCE_DIR.rglob("*")
        if path.is_file()
    }
    _baseline_matching(tmp_path)
    after_raw = {
        path.relative_to(RAW_DIR).as_posix(): _sha256(path)
        for path in RAW_DIR.rglob("*")
        if path.is_file()
    }
    after_ref = {
        path.relative_to(REFERENCE_DIR).as_posix(): _sha256(path)
        for path in REFERENCE_DIR.rglob("*")
        if path.is_file()
    }
    assert after_raw == before_raw
    assert after_ref == before_ref


def _electricity_factor_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "factor_id": "ef_test_grid",
        "activity_type": "grid_electricity",
        "factor_status": "ready",
        "denominator_unit": "kWh",
        "required_conversion": "not_required",
        "gas": "CO2",
        "valid_from": "2025-01-01",
        "valid_to": "2025-12-31",
        "notes": "",
        "source_locator": "",
        "factor_category": "",
    }
    row.update(overrides)
    return row


def _match_electricity(activity: pd.DataFrame, factors: pd.DataFrame):
    return match_activity_factors(
        activity_records=activity,
        emission_factors=pd.DataFrame(factors),
        calculation_dependencies=pd.DataFrame(),
    )


def test_malformed_valid_from_is_not_open_ended() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=pd.Timestamp("2025-06-01"),
            activity_end_date=pd.Timestamp("2025-06-01"),
            reporting_year=2025,
        ),
        pd.DataFrame(
            [
                _electricity_factor_row(
                    valid_from="not-a-date",
                    valid_to="",
                )
            ]
        ),
    )
    row = result.activity_readiness.iloc[0]
    assert row["calculation_readiness"] == "no_factor_configured"
    assert int(row["candidate_factor_count"]) == 0


def test_malformed_valid_to_is_not_open_ended() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=pd.Timestamp("2025-06-01"),
            activity_end_date=pd.Timestamp("2025-06-01"),
            reporting_year=2025,
        ),
        pd.DataFrame(
            [_electricity_factor_row(valid_from="2025-01-01", valid_to="31/13/2025")]
        ),
    )
    assert (
        result.activity_readiness.iloc[0]["calculation_readiness"]
        == "no_factor_configured"
    )


def test_future_factor_is_not_used_for_activity_date() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=pd.Timestamp("2025-06-01"),
            activity_end_date=pd.Timestamp("2025-06-01"),
        ),
        pd.DataFrame(
            [_electricity_factor_row(valid_from="2026-01-01", valid_to="2026-12-31")]
        ),
    )
    assert (
        result.activity_readiness.iloc[0]["calculation_readiness"]
        == "no_factor_configured"
    )


def test_expired_factor_is_not_used_for_activity_date() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=pd.Timestamp("2025-06-01"),
            activity_end_date=pd.Timestamp("2025-06-01"),
        ),
        pd.DataFrame(
            [_electricity_factor_row(valid_from="2024-01-01", valid_to="2024-12-31")]
        ),
    )
    assert (
        result.activity_readiness.iloc[0]["calculation_readiness"]
        == "no_factor_configured"
    )


def test_midyear_factor_cannot_cover_reporting_year_only() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=None,
            activity_end_date=None,
            reporting_year=2025,
        ),
        pd.DataFrame(
            [_electricity_factor_row(valid_from="2025-07-01", valid_to="2025-12-31")]
        ),
    )
    assert (
        result.activity_readiness.iloc[0]["calculation_readiness"]
        == "no_factor_configured"
    )


def test_midyear_factor_can_cover_activity_date_inside_window() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=pd.Timestamp("2025-08-01"),
            activity_end_date=pd.Timestamp("2025-08-01"),
            reporting_year=2025,
        ),
        pd.DataFrame(
            [_electricity_factor_row(valid_from="2025-07-01", valid_to="2025-12-31")]
        ),
    )
    assert result.activity_readiness.iloc[0]["calculation_readiness"] == "ready"


def test_reporting_year_requires_full_calendar_coverage() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=None,
            activity_end_date=None,
            reporting_year=2025,
        ),
        pd.DataFrame([_electricity_factor_row()]),
    )
    assert result.activity_readiness.iloc[0]["calculation_readiness"] == "ready"


def test_blank_validity_still_matches_when_table_never_stated_period() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=pd.Timestamp("2025-03-01"),
            activity_end_date=pd.Timestamp("2025-03-31"),
        ),
        pd.DataFrame([_electricity_factor_row(valid_from="", valid_to="")]),
    )
    assert result.activity_readiness.iloc[0]["calculation_readiness"] == "ready"


def test_multiple_covering_factors_are_ambiguous_not_newest() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=pd.Timestamp("2025-06-01"),
            activity_end_date=pd.Timestamp("2025-06-01"),
        ),
        pd.DataFrame(
            [
                _electricity_factor_row(factor_id="ef_a", factor_version="1"),
                _electricity_factor_row(factor_id="ef_b", factor_version="2"),
            ]
        ),
    )
    row = result.activity_readiness.iloc[0]
    assert row["calculation_readiness"] == "blocked_ambiguous_factor"
    assert int(row["candidate_factor_count"]) == 2


def test_unique_expired_historical_row_is_not_selected() -> None:
    result = _match_electricity(
        _simple_activity(
            activity_start_date=None,
            activity_end_date=None,
            reporting_year=2025,
        ),
        pd.DataFrame(
            [_electricity_factor_row(valid_from="2023-01-01", valid_to="2023-12-31")]
        ),
    )
    assert (
        result.activity_readiness.iloc[0]["calculation_readiness"]
        == "no_factor_configured"
    )
