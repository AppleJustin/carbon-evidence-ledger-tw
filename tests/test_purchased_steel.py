"""Purchased-steel Scope 3 Category 1 evidence model and validation."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from carbon_ledger.factors import validate_factor_registry
from carbon_ledger.purchased_steel import (
    ACTIVITY_TYPE,
    ALLOWED_CALCULATION_METHODS,
    BLOCKED_STATUSES,
    FACTOR_BOUNDARY_CRADLE_TO_GATE,
    FORMULA_ID,
    FORMULA_VERSION,
    GHG_SCOPE,
    METHOD_AVERAGE_DATA,
    METHOD_SUPPLIER_SPECIFIC,
    SCOPE3_CATEGORY,
    STATUS_BLOCKED_AMBIGUOUS_FACTOR,
    STATUS_BLOCKED_COMPANY_CONTROLLED_TRANSPORT_REQUIRES_SCOPE1_OR2_SPLIT,
    STATUS_BLOCKED_FACTOR_INCLUSION_UNCONFIRMED,
    STATUS_BLOCKED_INCOMPATIBLE_BOUNDARY,
    STATUS_BLOCKED_INCOMPATIBLE_UNIT,
    STATUS_BLOCKED_INVALID_PERIOD,
    STATUS_BLOCKED_INVALID_QUANTITY,
    STATUS_BLOCKED_MISSING_FACTOR_YEAR,
    STATUS_BLOCKED_MISSING_GEOGRAPHY,
    STATUS_BLOCKED_MISSING_METHOD,
    STATUS_BLOCKED_MISSING_PRODUCT_TYPE,
    STATUS_BLOCKED_MISSING_QUANTITY,
    STATUS_BLOCKED_MISSING_RECORD_ID,
    STATUS_BLOCKED_MISSING_SOURCE,
    STATUS_BLOCKED_MISSING_SUPPLIER_OR_PRODUCT,
    STATUS_BLOCKED_MISSING_UNIT,
    STATUS_BLOCKED_PRODUCT_MISMATCH,
    STATUS_BLOCKED_TIER1_INBOUND_REQUIRES_CATEGORY4_SPLIT,
    STATUS_BLOCKED_TRANSPORT_CONTROL_UNCONFIRMED,
    STATUS_BLOCKED_TRANSPORT_NOT_CATEGORY_1,
    STATUS_BLOCKED_UNSUPPORTED_METHOD,
    STATUS_CALCULATED,
    STATUS_NO_FACTOR_CONFIGURED,
    STATUS_NO_MATCHING_FACTOR,
    PurchasedSteelEvidence,
    RegisteredSteelFactor,
    calculate_purchased_steel,
    parse_emission_factor_unit,
    parse_purchased_steel_evidence,
    registered_steel_factors_from_frame,
    validate_purchased_steel_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = REPO_ROOT / "data" / "reference"
PURCHASED_STEEL_SOURCE = (
    REPO_ROOT / "src" / "carbon_ledger" / "purchased_steel.py"
).read_text(encoding="utf-8")


def _supplier_specific(**fields: object) -> dict[str, object]:
    record: dict[str, object] = {
        "record_id": "rec_steel_supplier_001",
        "calculation_method": METHOD_SUPPLIER_SPECIFIC,
        "supplier_name": "Demo Steel Supplier",
        "steel_product_type": "steel wire rod",
        "purchased_quantity": 10,
        "purchased_unit": "t",
        "emission_factor_value": "1.85",
        "emission_factor_unit": "tCO2e/t",
        "factor_boundary": FACTOR_BOUNDARY_CRADLE_TO_GATE,
        "factor_geography": "TW",
        "factor_year": 2025,
        "factor_source_id": "ref_supplier_epd_wire_rod_2025",
        "evidence_reference": "doc_steel_supplier_epd_001",
        "reporting_year": 2025,
        "reporting_period_id": "period-2025",
        "source_document_id": "doc_steel_001",
        "activity_type": ACTIVITY_TYPE,
        "record_type": "material_input",
        "factor_includes_tier1_to_reporting_company_transport": False,
    }
    record.update(fields)
    return record


def _registered_wire_rod_factor(**fields: object) -> dict[str, object]:
    row: dict[str, object] = {
        "factor_id": "ef_steel_wire_rod_tw_2025_v1",
        "activity_type": ACTIVITY_TYPE,
        "steel_product_type": "steel wire rod",
        "factor_value": "1.85",
        "numerator_unit": "tCO2e",
        "denominator_unit": "t",
        "factor_boundary": FACTOR_BOUNDARY_CRADLE_TO_GATE,
        "geography": "TW",
        "factor_year": "2025",
        "source_reference_id": "ref_registered_steel_wire_rod_2025",
        "factor_status": "ready",
        "factor_version": "v1",
        "valid_from": "2025-01-01",
        "valid_to": "2025-12-31",
    }
    row.update(fields)
    return row


def _average_data(**fields: object) -> dict[str, object]:
    record: dict[str, object] = {
        "record_id": "rec_steel_average_001",
        "calculation_method": METHOD_AVERAGE_DATA,
        "steel_product_type": "steel wire rod",
        "purchased_quantity": 10,
        "purchased_unit": "t",
        "factor_geography": "TW",
        "factor_year": 2025,
        "reporting_year": 2025,
        "reporting_period_id": "period-2025",
        "activity_type": ACTIVITY_TYPE,
        "record_type": "material_input",
        "factor_includes_tier1_to_reporting_company_transport": False,
    }
    record.update(fields)
    return record


def _ten_tonne_current_pipeline_record() -> dict[str, object]:
    return {
        "record_id": "rec_steel_2025",
        "activity_type": ACTIVITY_TYPE,
        "record_type": "material_input",
        "purchased_quantity": 10.0,
        "purchased_unit": "t",
        "reporting_year": 2025,
        "reporting_period_id": "period-2025",
    }


def test_evidence_model_exposes_required_fields() -> None:
    evidence = parse_purchased_steel_evidence(_supplier_specific())
    for field in (
        "calculation_method",
        "supplier_name",
        "steel_product_type",
        "purchased_quantity",
        "purchased_unit",
        "emission_factor_value",
        "emission_factor_unit",
        "factor_boundary",
        "factor_geography",
        "factor_year",
        "factor_source_id",
        "evidence_reference",
    ):
        assert hasattr(evidence, field)
        assert getattr(evidence, field) not in (None, "")


def test_v1_allows_only_supplier_specific_and_average_data() -> None:
    assert ALLOWED_CALCULATION_METHODS == {
        METHOD_SUPPLIER_SPECIFIC,
        METHOD_AVERAGE_DATA,
    }


def test_supplier_specific_complete_evidence_calculates_mass_times_factor() -> None:
    result = calculate_purchased_steel(_supplier_specific())
    assert result.calculation_status == STATUS_CALCULATED
    assert result.calculated_tco2e == 18.5
    assert result.calculated_kgco2e == 18500.0
    assert result.normalized_value == 10.0
    assert result.normalized_unit == "t"
    assert result.formula_id == FORMULA_ID
    assert result.formula_version == FORMULA_VERSION
    assert result.ghg_scope == GHG_SCOPE
    assert result.scope3_category == SCOPE3_CATEGORY
    assert result.calculation_method == METHOD_SUPPLIER_SPECIFIC
    assert result.factor_boundary == FACTOR_BOUNDARY_CRADLE_TO_GATE
    assert result.factor_year == 2025
    assert "factor_year" in result.calculation_trace
    assert "includes_tier1_to_reporting_company_transport" in result.calculation_trace
    assert "includes_upstream_transport" not in result.calculation_trace
    row = result.to_calculation_row()
    assert row["calculation_status"] == STATUS_CALCULATED
    assert row["calculated_tco2e"] == 18.5


def test_supplier_specific_product_type_without_supplier_is_blocked() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(supplier_name="", steel_product_type="steel wire rod")
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_SUPPLIER_OR_PRODUCT
    assert result.calculated_tco2e is None
    assert result.calculated_kgco2e is None


def test_supplier_specific_supplier_without_product_type_is_blocked() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(steel_product_type="")
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_PRODUCT_TYPE
    assert result.calculated_tco2e is None


def test_supplier_specific_accepts_product_identifier_instead_of_type() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(
            steel_product_type="",
            product_identifier="SKU-WIRE-ROD-001",
        )
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.calculated_tco2e == 18.5


def test_supplier_specific_missing_supplier_and_product_is_blocked() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(supplier_name="", steel_product_type="")
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_SUPPLIER_OR_PRODUCT
    assert result.calculated_tco2e is None
    assert result.calculated_kgco2e is None


def test_supplier_specific_missing_factor_is_no_factor_configured() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(emission_factor_value=None)
    )
    assert result.calculation_status == STATUS_NO_FACTOR_CONFIGURED
    assert result.calculated_tco2e is None


def test_supplier_specific_missing_factor_unit_is_blocked() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(emission_factor_unit="")
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_UNIT
    assert result.calculated_kgco2e is None


def test_supplier_specific_missing_source_and_evidence_is_blocked() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(
            factor_source_id="",
            evidence_reference="",
            source_document_id="",
        )
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_SOURCE
    assert result.calculated_tco2e is None


def test_supplier_specific_gate_to_gate_boundary_is_blocked() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(factor_boundary="gate_to_gate")
    )
    assert result.calculation_status == STATUS_BLOCKED_INCOMPATIBLE_BOUNDARY
    assert result.calculated_tco2e is None


def test_kg_quantity_converts_before_tonne_factor() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(purchased_quantity=10000, purchased_unit="kg")
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.normalized_value == 10.0
    assert result.calculated_tco2e == 18.5


def test_average_data_uses_registered_factor_not_inline_value() -> None:
    result = calculate_purchased_steel(
        _average_data(emission_factor_value="9.99", emission_factor_unit="tCO2e/t"),
        registered_factors=pd.DataFrame([_registered_wire_rod_factor()]),
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.factor_id == "ef_steel_wire_rod_tw_2025_v1"
    assert result.factor_value == 1.85
    assert result.calculated_tco2e == 18.5
    assert result.calculation_method == METHOD_AVERAGE_DATA
    assert "9.99" not in result.calculation_trace


def test_average_data_without_registered_factor_is_no_matching_factor() -> None:
    result = calculate_purchased_steel(
        _average_data(emission_factor_value="1.85", emission_factor_unit="tCO2e/t")
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_tco2e is None
    assert result.calculated_kgco2e is None


def test_average_data_does_not_use_production_registry_steel_factor() -> None:
    registry = validate_factor_registry(REFERENCE_DIR)
    steel_factors = registered_steel_factors_from_frame(registry.emission_factors)
    assert steel_factors == ()
    result = calculate_purchased_steel(
        _average_data(),
        registered_factors=registry.emission_factors,
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR


def test_average_data_product_mismatch_is_blocked() -> None:
    result = calculate_purchased_steel(
        _average_data(steel_product_type="stainless coil"),
        registered_factors=pd.DataFrame([_registered_wire_rod_factor()]),
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_tco2e is None


def test_average_data_year_mismatch_does_not_substitute_another_year() -> None:
    result = calculate_purchased_steel(
        _average_data(reporting_year=2024, factor_year=2024),
        registered_factors=pd.DataFrame([_registered_wire_rod_factor()]),
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_tco2e is None


def test_average_data_geography_mismatch_is_no_matching_factor() -> None:
    result = calculate_purchased_steel(
        _average_data(factor_geography="CN"),
        registered_factors=pd.DataFrame([_registered_wire_rod_factor()]),
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR


def test_average_data_missing_product_type_is_blocked() -> None:
    result = calculate_purchased_steel(
        _average_data(steel_product_type=""),
        registered_factors=pd.DataFrame([_registered_wire_rod_factor()]),
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_PRODUCT_TYPE


def test_average_data_missing_geography_is_blocked() -> None:
    result = calculate_purchased_steel(
        _average_data(factor_geography=""),
        registered_factors=pd.DataFrame([_registered_wire_rod_factor()]),
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_GEOGRAPHY


def test_average_data_skips_incomplete_registered_rows() -> None:
    incomplete = _registered_wire_rod_factor(
        source_reference_id="",
        factor_version="",
        factor_id="",
    )
    parsed = registered_steel_factors_from_frame(pd.DataFrame([incomplete]))
    assert parsed == ()
    result = calculate_purchased_steel(
        _average_data(),
        registered_factors=pd.DataFrame([incomplete]),
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR


def test_average_data_ambiguous_registered_factors_are_blocked() -> None:
    factors = pd.DataFrame(
        [
            _registered_wire_rod_factor(),
            _registered_wire_rod_factor(
                factor_id="ef_steel_wire_rod_tw_2025_v2",
                factor_version="v2",
            ),
        ]
    )
    result = calculate_purchased_steel(
        _average_data(),
        registered_factors=factors,
    )
    assert result.calculation_status == STATUS_BLOCKED_AMBIGUOUS_FACTOR
    assert result.calculated_tco2e is None


def test_average_data_two_covering_versions_do_not_pick_latest() -> None:
    factors = pd.DataFrame(
        [
            _registered_wire_rod_factor(
                factor_id="ef_steel_wire_rod_tw_2023_v1",
                factor_year="2023",
                factor_version="v1",
                valid_from="2023-01-01",
                valid_to="2025-12-31",
            ),
            _registered_wire_rod_factor(
                factor_id="ef_steel_wire_rod_tw_2024_v1",
                factor_year="2024",
                factor_version="v1",
                valid_from="2024-01-01",
                valid_to="2025-12-31",
            ),
        ]
    )
    result = calculate_purchased_steel(
        _average_data(reporting_year=2025),
        registered_factors=factors,
    )
    assert result.calculation_status == STATUS_BLOCKED_AMBIGUOUS_FACTOR
    assert result.calculated_tco2e is None


def test_average_data_2023_factor_covering_2025_is_usable() -> None:
    factors = pd.DataFrame(
        [
            _registered_wire_rod_factor(
                factor_id="ef_steel_wire_rod_tw_2023_v1",
                factor_year="2023",
                factor_version="v1",
                valid_from="2023-01-01",
                valid_to="2025-12-31",
                source_reference_id="ref_registered_steel_wire_rod_2023",
            )
        ]
    )
    result = calculate_purchased_steel(
        _average_data(reporting_year=2025, factor_year=2023),
        registered_factors=factors,
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.factor_year == 2023
    assert result.calculated_tco2e == 18.5
    assert '"factor_year": 2023' in result.calculation_trace


def test_average_data_expired_2024_factor_cannot_cover_2025() -> None:
    factors = pd.DataFrame(
        [
            _registered_wire_rod_factor(
                factor_id="ef_steel_wire_rod_tw_2024_expired",
                factor_year="2024",
                factor_version="v1",
                valid_from="2024-01-01",
                valid_to="2024-12-31",
            )
        ]
    )
    result = calculate_purchased_steel(
        _average_data(reporting_year=2025, factor_year=2024),
        registered_factors=factors,
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_tco2e is None


def test_average_data_midyear_2025_factor_cannot_represent_full_year() -> None:
    factors = pd.DataFrame(
        [
            _registered_wire_rod_factor(
                factor_id="ef_steel_wire_rod_tw_2025_mid",
                factor_year="2025",
                valid_from="2025-07-01",
                valid_to="2025-12-31",
            )
        ]
    )
    result = calculate_purchased_steel(
        _average_data(reporting_year=2025),
        registered_factors=factors,
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_tco2e is None


def test_average_data_malformed_valid_to_is_not_open_ended() -> None:
    factors = pd.DataFrame(
        [
            _registered_wire_rod_factor(
                factor_id="ef_steel_wire_rod_tw_malformed_to",
                factor_year="2023",
                valid_from="2023-01-01",
                valid_to="not-a-date",
            )
        ]
    )
    result = calculate_purchased_steel(
        _average_data(reporting_year=2025),
        registered_factors=factors,
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_tco2e is None


def test_supplier_specific_missing_factor_year_is_not_filled() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(factor_year="", reporting_year=2025)
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_FACTOR_YEAR
    assert result.factor_year is None
    assert result.calculated_tco2e is None
    assert result.reporting_year == 2025


def test_average_data_factor_year_need_not_equal_reporting_year() -> None:
    result = calculate_purchased_steel(
        _average_data(factor_year=2023, reporting_year=2025),
        registered_factors=pd.DataFrame(
            [
                _registered_wire_rod_factor(
                    factor_id="ef_steel_wire_rod_tw_2023_open",
                    factor_year="2023",
                    valid_from="2023-01-01",
                    valid_to="2025-12-31",
                )
            ]
        ),
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.factor_year == 2023
    assert result.reporting_year == 2025


def test_missing_method_is_no_factor_configured() -> None:
    status, issues = validate_purchased_steel_evidence(
        parse_purchased_steel_evidence(_ten_tonne_current_pipeline_record())
    )
    assert status == STATUS_NO_FACTOR_CONFIGURED
    assert issues[0].field == "calculation_method"


def test_unsupported_method_is_blocked() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(calculation_method="spend_based")
    )
    assert result.calculation_status == STATUS_BLOCKED_UNSUPPORTED_METHOD
    assert result.calculated_tco2e is None


def test_missing_reporting_year_is_blocked() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(reporting_year="", reporting_period_id="period-2025")
    )
    assert result.calculation_status == STATUS_BLOCKED_INVALID_PERIOD
    assert result.calculated_tco2e is None


def test_missing_quantity_is_blocked_not_zero() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(purchased_quantity=None)
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_QUANTITY
    assert result.calculated_tco2e is None
    assert result.calculated_kgco2e is None


def test_zero_quantity_is_blocked_not_zero_emissions() -> None:
    result = calculate_purchased_steel(_supplier_specific(purchased_quantity=0))
    assert result.calculation_status == STATUS_BLOCKED_INVALID_QUANTITY
    assert result.calculated_tco2e is None


def test_missing_purchased_unit_is_blocked() -> None:
    result = calculate_purchased_steel(_supplier_specific(purchased_unit=""))
    assert result.calculation_status == STATUS_BLOCKED_MISSING_UNIT


def test_incompatible_purchased_unit_is_blocked() -> None:
    result = calculate_purchased_steel(_supplier_specific(purchased_unit="m3"))
    assert result.calculation_status == STATUS_BLOCKED_INCOMPATIBLE_UNIT


def test_pre_tier1_upstream_transport_is_allowed_in_category_1() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(
            includes_upstream_transport=True,
            includes_tier2_to_tier1_transport=True,
        )
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.calculated_tco2e == 18.5
    assert result.scope3_category == SCOPE3_CATEGORY
    assert "Upstream transport is excluded" not in result.calculation_reason
    assert "Pre-Tier-1 supply-chain transport may be included" in (
        result.calculation_reason
    )
    assert "all upstream transport excluded" not in result.calculation_reason.lower()
    assert "Category 4" not in result.calculation_reason
    assert '"includes_pre_tier1_supply_chain_transport": true' in (
        result.calculation_trace
    )
    assert '"includes_tier1_to_reporting_company_transport": false' in (
        result.calculation_trace
    )
    assert '"factor_includes_tier1_to_reporting_company_transport": false' in (
        result.calculation_trace
    )


def test_pre_tier1_flag_does_not_claim_all_upstream_transport_excluded() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(includes_pre_tier1_supply_chain_transport=True)
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert "Upstream transport is excluded" not in result.calculation_reason
    assert "may be included in the cradle-to-gate factor" in result.calculation_reason
    assert "all upstream transport excluded" not in result.calculation_reason.lower()
    assert (
        "does not inventory a separate Tier 1 to reporting-company"
        in result.calculation_reason
    )
    assert '"includes_pre_tier1_supply_chain_transport": true' in (
        result.calculation_trace
    )
    assert '"includes_tier1_to_reporting_company_transport": false' in (
        result.calculation_trace
    )


def test_unconfirmed_factor_inclusion_does_not_calculate() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(
            factor_includes_tier1_to_reporting_company_transport="",
            includes_tier1_to_reporting_company_transport="",
        )
    )
    assert result.calculation_status == STATUS_BLOCKED_FACTOR_INCLUSION_UNCONFIRMED
    assert result.calculated_tco2e is None


def test_factor_inclusion_blank_legacy_boolean_is_not_false() -> None:
    evidence = parse_purchased_steel_evidence(
        {
            **_supplier_specific(),
            "factor_includes_tier1_to_reporting_company_transport": "",
            "includes_tier1_to_reporting_company_transport": "",
        }
    )
    assert evidence.factor_includes_tier1_to_reporting_company_transport is None
    assert evidence.includes_tier1_to_reporting_company_transport is None


def test_legacy_boolean_true_without_control_does_not_infer_category_4() -> None:
    record = _supplier_specific()
    del record["factor_includes_tier1_to_reporting_company_transport"]
    record["includes_tier1_to_reporting_company_transport"] = True
    result = calculate_purchased_steel(record)
    assert result.calculation_status == STATUS_BLOCKED_TRANSPORT_CONTROL_UNCONFIRMED
    assert result.calculated_tco2e is None
    assert result.scope3_category == SCOPE3_CATEGORY


def test_third_party_inbound_in_factor_requires_category4_split() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(
            factor_includes_tier1_to_reporting_company_transport=True,
            tier1_to_reporting_company_transport_control="third_party",
        )
    )
    assert (
        result.calculation_status
        == STATUS_BLOCKED_TIER1_INBOUND_REQUIRES_CATEGORY4_SPLIT
    )
    assert result.calculated_tco2e is None
    assert result.calculated_kgco2e is None
    assert "Category 4" in result.calculation_reason


def test_company_controlled_inbound_in_factor_requires_scope1_or2_split() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(
            factor_includes_tier1_to_reporting_company_transport=True,
            tier1_to_reporting_company_transport_control="reporting_company",
        )
    )
    assert (
        result.calculation_status
        == STATUS_BLOCKED_COMPANY_CONTROLLED_TRANSPORT_REQUIRES_SCOPE1_OR2_SPLIT
    )
    assert result.calculated_tco2e is None
    assert "Category 4" not in result.calculation_reason
    assert "Scope 1" in result.calculation_reason


def test_factor_excludes_inbound_transport_calculates_category_1() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(
            factor_includes_tier1_to_reporting_company_transport=False,
            tier1_to_reporting_company_transport_control="third_party",
        )
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.calculated_tco2e == 18.5
    assert '"tier1_to_reporting_company_transport_control": "not_applicable"' in (
        result.calculation_trace
    )


def test_third_party_transport_record_is_not_category_1() -> None:
    result = calculate_purchased_steel(
        _supplier_specific(
            activity_type="third_party_transport",
            record_type="transport_activity",
        )
    )
    assert result.calculation_status == STATUS_BLOCKED_TRANSPORT_NOT_CATEGORY_1


def test_missing_record_id_is_blocked() -> None:
    result = calculate_purchased_steel(_supplier_specific(record_id=""))
    assert result.calculation_status == STATUS_BLOCKED_MISSING_RECORD_ID


def test_ten_tonne_purchase_without_factor_stays_no_factor_configured() -> None:
    result = calculate_purchased_steel(_ten_tonne_current_pipeline_record())
    assert result.calculation_status == STATUS_NO_FACTOR_CONFIGURED
    assert result.calculated_kgco2e is None
    assert result.calculated_tco2e is None
    row = result.to_calculation_row()
    assert pd.isna(row["calculated_kgco2e"])
    assert pd.isna(row["calculated_tco2e"])


def test_blocked_statuses_never_write_zero_emissions() -> None:
    blocked_records = [
        _ten_tonne_current_pipeline_record(),
        _supplier_specific(emission_factor_value=None),
        _supplier_specific(calculation_method="hybrid"),
        _average_data(),
        _supplier_specific(
            factor_includes_tier1_to_reporting_company_transport=True,
            tier1_to_reporting_company_transport_control="third_party",
        ),
    ]
    for record in blocked_records:
        result = calculate_purchased_steel(record)
        assert result.calculation_status in BLOCKED_STATUSES
        assert result.calculated_kgco2e is None
        assert result.calculated_tco2e is None


def test_average_data_pre_tier1_comes_from_registry_not_activity_row() -> None:
    factors = pd.DataFrame(
        [
            _registered_wire_rod_factor(
                includes_pre_tier1_supply_chain_transport=True
            )
        ]
    )
    result = calculate_purchased_steel(
        _average_data(includes_pre_tier1_supply_chain_transport=False),
        registered_factors=factors,
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.calculated_tco2e == 18.5
    assert '"includes_pre_tier1_supply_chain_transport": true' in (
        result.calculation_trace
    )


def test_missing_pre_tier1_flag_does_not_claim_upstream_transport_excluded() -> None:
    result = calculate_purchased_steel(_supplier_specific())
    assert result.calculation_status == STATUS_CALCULATED
    assert "all upstream transport excluded" not in result.calculation_reason.lower()
    assert '"includes_pre_tier1_supply_chain_transport": null' in (
        result.calculation_trace
    )
    assert "1.85" not in PURCHASED_STEEL_SOURCE
    assert "DEFAULT_STEEL_FACTOR" not in PURCHASED_STEEL_SOURCE
    assert "GENERIC_STEEL_EF" not in PURCHASED_STEEL_SOURCE


def test_parse_emission_factor_unit_rejects_unknown_units() -> None:
    assert parse_emission_factor_unit("kgCO2e/t") is not None
    assert parse_emission_factor_unit("tCO2e/kg") is not None
    assert parse_emission_factor_unit("kgCO2e/kWh") is None
    assert parse_emission_factor_unit("TJ/t") is None


def test_registered_factor_match_uses_typed_sequence() -> None:
    unit = parse_emission_factor_unit("kgCO2e/t")
    assert unit is not None
    factor = RegisteredSteelFactor(
        factor_id="ef_test_wire_rod",
        steel_product_type="steel wire rod",
        factor_value=Decimal("1850"),
        factor_unit=unit,
        factor_boundary=FACTOR_BOUNDARY_CRADLE_TO_GATE,
        factor_geography="TW",
        factor_year=2025,
        factor_source_id="ref_test_steel",
        factor_status="ready",
        factor_version="v1",
        valid_from="2025-01-01",
        valid_to="2025-12-31",
    )
    result = calculate_purchased_steel(
        _average_data(),
        registered_factors=(factor,),
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.calculated_kgco2e == 18500.0
    assert result.calculated_tco2e == 18.5


def test_typed_evidence_instance_can_be_calculated_directly() -> None:
    evidence = PurchasedSteelEvidence(
        record_id="rec_steel_direct",
        calculation_method=METHOD_SUPPLIER_SPECIFIC,
        supplier_name="Demo Steel Supplier",
        steel_product_type="steel wire rod",
        purchased_quantity=Decimal("10"),
        purchased_unit="t",
        emission_factor_value=Decimal("1.85"),
        emission_factor_unit="tCO2e/t",
        factor_boundary=FACTOR_BOUNDARY_CRADLE_TO_GATE,
        factor_source_id="ref_supplier_epd_wire_rod_2025",
        factor_year=2025,
        reporting_year=2025,
        factor_includes_tier1_to_reporting_company_transport=False,
        includes_tier1_to_reporting_company_transport=False,
    )
    result = calculate_purchased_steel(evidence)
    assert result.calculation_status == STATUS_CALCULATED
    assert result.calculated_tco2e == 18.5


def test_all_documented_blocked_statuses_are_named() -> None:
    expected = {
        STATUS_NO_FACTOR_CONFIGURED,
        STATUS_NO_MATCHING_FACTOR,
        STATUS_BLOCKED_MISSING_RECORD_ID,
        STATUS_BLOCKED_MISSING_METHOD,
        STATUS_BLOCKED_UNSUPPORTED_METHOD,
        STATUS_BLOCKED_MISSING_QUANTITY,
        STATUS_BLOCKED_INVALID_QUANTITY,
        STATUS_BLOCKED_MISSING_UNIT,
        STATUS_BLOCKED_INCOMPATIBLE_UNIT,
        STATUS_BLOCKED_MISSING_SOURCE,
        STATUS_BLOCKED_MISSING_SUPPLIER_OR_PRODUCT,
        STATUS_BLOCKED_MISSING_PRODUCT_TYPE,
        STATUS_BLOCKED_INCOMPATIBLE_BOUNDARY,
        STATUS_BLOCKED_PRODUCT_MISMATCH,
        STATUS_BLOCKED_INVALID_PERIOD,
        STATUS_BLOCKED_MISSING_GEOGRAPHY,
        STATUS_BLOCKED_MISSING_FACTOR_YEAR,
        STATUS_BLOCKED_AMBIGUOUS_FACTOR,
        STATUS_BLOCKED_TRANSPORT_NOT_CATEGORY_1,
        STATUS_BLOCKED_FACTOR_INCLUSION_UNCONFIRMED,
        STATUS_BLOCKED_TRANSPORT_CONTROL_UNCONFIRMED,
        STATUS_BLOCKED_TIER1_INBOUND_REQUIRES_CATEGORY4_SPLIT,
        STATUS_BLOCKED_COMPANY_CONTROLLED_TRANSPORT_REQUIRES_SCOPE1_OR2_SPLIT,
    }
    assert expected <= BLOCKED_STATUSES
