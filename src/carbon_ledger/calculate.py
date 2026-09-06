"""Limited and auditable emissions calculation for ready activities only.

Phase 5C / Stage 4 calculates emissions only when readiness, factor matching,
units, and values all agree. It does not invent fallbacks or framework mappings.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from carbon_ledger.factors import (
    GWP_CONTEXT_FUEL_COMBUSTION,
    gwp_context_for_combustion,
    select_gwp_row,
)
from carbon_ledger.heating import (
    STATUS_AMBIGUOUS,
    STATUS_INCOMPLETE_PROVENANCE,
    STATUS_INVALID_SUBTYPE,
    STATUS_MISSING,
    STATUS_READY,
    STATUS_SUBTYPE_REQUIRED,
    activity_energy_kcal,
    empty_heating_values,
    kcal_to_tj,
    lookup_kcal_to_tj_conversion,
    select_heating_value,
)

FORMULA_ID = "activity_value_times_direct_co2e_factor"
FORMULA_VERSION = "1.0"

COMBUSTION_FORMULA_ID = "fuel_activity_to_energy_to_multigas_co2e"
COMBUSTION_FORMULA_VERSION = "1.0"

REQUIRED_COMBUSTION_GASES = ("CO2", "CH4", "N2O")
GAS_NUMERATOR_UNITS = {
    "CO2": "kgCO2",
    "CH4": "kgCH4",
    "N2O": "kgN2O",
}

OUTPUT_COLUMNS = [
    "calculation_id",
    "record_id",
    "activity_type",
    "normalized_value",
    "normalized_unit",
    "factor_id",
    "factor_value",
    "factor_numerator_unit",
    "factor_denominator_unit",
    "source_reference_id",
    "formula_id",
    "formula_version",
    "heating_value_id",
    "heating_value",
    "heating_value_unit",
    "heating_value_source_reference_id",
    "energy_tj",
    "co2_factor_id",
    "ch4_factor_id",
    "n2o_factor_id",
    "co2_kg",
    "ch4_kg",
    "n2o_kg",
    "co2_gwp",
    "ch4_gwp",
    "n2o_gwp",
    "co2e_from_co2_kg",
    "co2e_from_ch4_kg",
    "co2e_from_n2o_kg",
    "gwp_source_reference_id",
    "engineering_conversion_id",
    "calculation_trace",
    "calculated_kgco2e",
    "calculated_tco2e",
    "calculation_status",
    "calculation_reason",
]

PASSTHROUGH_STATUSES = {
    "blocked_missing_conversion",
    "blocked_ambiguous_conversion",
    "blocked_ambiguous_factor",
    "blocked_incomplete_gas_factors",
    "blocked_conflicting_factor_group",
    "blocked_natural_gas_type_required",
    "no_factor_configured",
    "no_matching_factor",
    "not_emissions_activity",
    "unsupported_activity_type",
}

TRACE_EMPTY = pd.NA


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def _text(value: Any) -> str:
    if _is_blank(value):
        return ""
    return str(value).strip()


def _to_decimal(value: Any) -> Decimal | None:
    """Parse a positive finite number via Decimal from its string form."""
    if isinstance(value, bool):
        return None
    if _is_blank(value):
        return None
    try:
        if isinstance(value, float) and not math.isfinite(value):
            return None
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not number.is_finite():
        return None
    if number <= 0:
        return None
    return number


def _decimal_to_float(value: Decimal) -> float:
    return float(value)


def _empty_result_fields() -> dict[str, Any]:
    return {
        "factor_id": pd.NA,
        "factor_value": pd.NA,
        "factor_numerator_unit": pd.NA,
        "factor_denominator_unit": pd.NA,
        "source_reference_id": pd.NA,
        "formula_id": pd.NA,
        "formula_version": pd.NA,
        "heating_value_id": pd.NA,
        "heating_value": pd.NA,
        "heating_value_unit": pd.NA,
        "heating_value_source_reference_id": pd.NA,
        "energy_tj": pd.NA,
        "co2_factor_id": pd.NA,
        "ch4_factor_id": pd.NA,
        "n2o_factor_id": pd.NA,
        "co2_kg": pd.NA,
        "ch4_kg": pd.NA,
        "n2o_kg": pd.NA,
        "co2_gwp": pd.NA,
        "ch4_gwp": pd.NA,
        "n2o_gwp": pd.NA,
        "co2e_from_co2_kg": pd.NA,
        "co2e_from_ch4_kg": pd.NA,
        "co2e_from_n2o_kg": pd.NA,
        "gwp_source_reference_id": pd.NA,
        "engineering_conversion_id": pd.NA,
        "calculation_trace": TRACE_EMPTY,
        "calculated_kgco2e": pd.NA,
        "calculated_tco2e": pd.NA,
    }


def _result_row(
    *,
    record_id: str,
    activity_type: str,
    normalized_value: Any,
    normalized_unit: Any,
    calculation_status: str,
    calculation_reason: str,
    **fields: Any,
) -> dict[str, Any]:
    row = {
        "calculation_id": f"calc_{record_id}",
        "record_id": record_id,
        "activity_type": activity_type,
        "normalized_value": normalized_value,
        "normalized_unit": normalized_unit,
        "calculation_status": calculation_status,
        "calculation_reason": calculation_reason,
        **_empty_result_fields(),
    }
    for key, value in fields.items():
        if key in row:
            row[key] = value
    return row


def _lookup_normalized(
    normalized_records: pd.DataFrame, record_id: str
) -> pd.Series | None:
    if normalized_records.empty or "record_id" not in normalized_records.columns:
        return None
    matches = normalized_records.loc[
        normalized_records["record_id"].astype(str) == record_id
    ]
    if matches.empty:
        return None
    return matches.iloc[0]


def _lookup_factor(
    emission_factors: pd.DataFrame, factor_id: str
) -> pd.Series | None:
    if emission_factors.empty or "factor_id" not in emission_factors.columns:
        return None
    matches = emission_factors.loc[
        emission_factors["factor_id"].astype(str) == factor_id
    ]
    if matches.empty:
        return None
    return matches.iloc[0]


def _ready_candidates(
    candidate_matches: pd.DataFrame, record_id: str
) -> pd.DataFrame:
    if candidate_matches.empty:
        return pd.DataFrame(columns=candidate_matches.columns)
    mask = candidate_matches["record_id"].astype(str) == record_id
    mask &= candidate_matches["match_status"].astype(str) == "matched_ready"
    return candidate_matches.loc[mask].copy()


def _passthrough_reason(readiness_row: pd.Series) -> str:
    status = _text(readiness_row.get("calculation_readiness"))
    dependency = readiness_row.get("blocking_dependency")
    readiness_reason = _text(readiness_row.get("readiness_reason"))

    if status == "blocked_missing_conversion":
        dependency_text = _text(dependency)
        if dependency_text:
            return (
                "Calculation blocked until verified conversion "
                f"{dependency_text} is available."
            )
        return "Calculation blocked by a missing verified conversion."

    if status == "blocked_natural_gas_type_required":
        return (
            readiness_reason
            or (
                "Natural-gas type NG1 or NG2 is required before the official "
                "heating value can be applied."
            )
        )

    if status == "blocked_ambiguous_conversion":
        return (
            readiness_reason
            or "Multiple conflicting heating values match this activity year."
        )

    if status == "blocked_ambiguous_factor":
        return (
            readiness_reason
            or "Multiple ready factors cover this activity period."
        )

    if status == "blocked_incomplete_gas_factors":
        return (
            readiness_reason
            or "CO2, CH4, and N2O factors are not all present for this activity."
        )

    if status == "blocked_conflicting_factor_group":
        return (
            readiness_reason
            or "CO2/CH4/N2O factors do not belong to one official source family."
        )

    if status in {"no_factor_configured", "no_matching_factor"}:
        return (
            readiness_reason
            or "No suitable emission factor is configured for calculation."
        )

    if status == "not_emissions_activity":
        return (
            readiness_reason
            or (
                "Operational or production evidence is not itself an "
                "emissions activity."
            )
        )

    if status == "unsupported_activity_type":
        return (
            readiness_reason
            or "No calculation method exists for this activity type."
        )

    return readiness_reason or f"Calculation not performed ({status})."


def _blocked(
    *,
    record_id: str,
    activity_type: str,
    normalized_value: Any,
    normalized_unit: Any,
    status: str,
    reason: str,
) -> dict[str, Any]:
    return _result_row(
        record_id=record_id,
        activity_type=activity_type,
        normalized_value=normalized_value,
        normalized_unit=normalized_unit,
        calculation_status=status,
        calculation_reason=reason,
        **_empty_result_fields(),
    )


def _dump_trace(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _candidate_heating_value_id(ready_candidates: pd.DataFrame) -> str:
    if "heating_value_id" not in ready_candidates.columns:
        return ""
    ids = {
        _text(value)
        for value in ready_candidates["heating_value_id"].tolist()
        if not _is_blank(value)
    }
    if len(ids) != 1:
        return ""
    return next(iter(ids))


def _factor_group_consistent(factor_rows: list[pd.Series]) -> bool:
    sources = {_text(row.get("source_reference_id")) for row in factor_rows}
    years = {_text(row.get("factor_year")) for row in factor_rows}
    contexts = {_text(row.get("combustion_context")) for row in factor_rows}
    return (
        len(factor_rows) == 3
        and len(sources) == 1
        and "" not in sources
        and len(years) == 1
        and len(contexts) == 1
        and "" not in contexts
    )


def _calculate_direct_co2e(
    *,
    record_id: str,
    activity_type: str,
    normalized_decimal: Decimal,
    normalized_unit: str,
    candidate: pd.Series,
    emission_factors: pd.DataFrame,
) -> dict[str, Any]:
    factor_id = _text(candidate.get("factor_id"))
    factor_row = _lookup_factor(emission_factors, factor_id)
    if factor_row is None:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="factor_match_inconsistent",
            reason=(
                f"Candidate factor_id {factor_id!r} was not found in the "
                "emission-factor registry."
            ),
        )

    gas = _text(factor_row.get("gas"))
    numerator_unit = _text(factor_row.get("numerator_unit"))
    denominator_unit = _text(factor_row.get("denominator_unit"))
    factor_decimal = _to_decimal(factor_row.get("factor_value"))
    source_reference_id = _text(factor_row.get("source_reference_id"))

    if gas != "CO2e" or numerator_unit != "kgCO2e":
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="factor_match_inconsistent",
            reason=(
                "Ready calculation requires a direct CO2e factor with "
                "numerator unit kgCO2e."
            ),
        )

    if denominator_unit != normalized_unit:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="factor_match_inconsistent",
            reason=(
                f"Factor denominator {denominator_unit!r} does not match "
                f"normalized unit {normalized_unit!r}."
            ),
        )

    if factor_decimal is None:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="factor_match_inconsistent",
            reason="Factor value must be a finite number greater than zero.",
        )

    kgco2e = normalized_decimal * factor_decimal
    tco2e = kgco2e / Decimal("1000")
    return _result_row(
        record_id=record_id,
        activity_type=activity_type,
        normalized_value=float(normalized_decimal),
        normalized_unit=normalized_unit,
        factor_id=factor_id,
        factor_value=float(factor_decimal),
        factor_numerator_unit=numerator_unit,
        factor_denominator_unit=denominator_unit,
        source_reference_id=source_reference_id or pd.NA,
        formula_id=FORMULA_ID,
        formula_version=FORMULA_VERSION,
        calculated_kgco2e=float(kgco2e),
        calculated_tco2e=float(tco2e),
        calculation_status="calculated",
        calculation_reason=(
            "Calculated using normalized activity value times a direct "
            "CO2e emission factor."
        ),
    )


def _calculate_combustion(
    *,
    record_id: str,
    activity_type: str,
    normalized_decimal: Decimal,
    normalized_unit: str,
    ready_candidates: pd.DataFrame,
    emission_factors: pd.DataFrame,
    heating_values: pd.DataFrame,
    gwp_values: pd.DataFrame,
    engineering_conversions: pd.DataFrame,
    activity_start: Any,
    activity_end: Any,
    fuel_subtype: Any = "",
) -> dict[str, Any]:
    factor_rows: dict[str, pd.Series] = {}
    for _, candidate in ready_candidates.iterrows():
        factor_id = _text(candidate.get("factor_id"))
        factor_row = _lookup_factor(emission_factors, factor_id)
        if factor_row is None:
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="factor_match_inconsistent",
                reason=(
                    f"Candidate factor_id {factor_id!r} was not found in the "
                    "emission-factor registry."
                ),
            )
        gas = _text(factor_row.get("gas"))
        if gas in factor_rows:
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="blocked_incomplete_gas_factors",
                reason=f"Duplicate {gas} factor candidates for one activity.",
            )
        factor_rows[gas] = factor_row

    if set(factor_rows) != set(REQUIRED_COMBUSTION_GASES):
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_incomplete_gas_factors",
            reason=(
                "Multi-gas calculation requires exactly CO2, CH4, and N2O "
                "factors. Partial CO2e totals are not calculated."
            ),
        )

    ordered_rows = [factor_rows[gas] for gas in REQUIRED_COMBUSTION_GASES]
    if not _factor_group_consistent(ordered_rows):
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_conflicting_factor_group",
            reason=(
                "CO2/CH4/N2O factors must share one source_reference_id, "
                "factor_year, and combustion_context."
            ),
        )

    combustion_context = _text(ordered_rows[0].get("combustion_context"))
    gwp_context = gwp_context_for_combustion(combustion_context)
    if gwp_context != GWP_CONTEXT_FUEL_COMBUSTION:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_missing_gwp",
            reason=(
                "Combustion GWP context could not be determined. Fossil-methane "
                "GWP 30 is not used for fuel combustion."
            ),
        )

    hv_id = _candidate_heating_value_id(ready_candidates)
    hv_selection = select_heating_value(
        heating_values,
        fuel_type=activity_type,
        activity_start=activity_start,
        activity_end=activity_end,
        fuel_subtype=fuel_subtype,
    )
    if hv_selection.status == STATUS_AMBIGUOUS:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_ambiguous_conversion",
            reason=hv_selection.reason,
        )
    if hv_selection.status == STATUS_SUBTYPE_REQUIRED:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_natural_gas_type_required",
            reason=hv_selection.reason,
        )
    if hv_selection.status == STATUS_INVALID_SUBTYPE:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="factor_match_inconsistent",
            reason=hv_selection.reason,
        )
    if hv_selection.status in {STATUS_MISSING, STATUS_INCOMPLETE_PROVENANCE}:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_missing_conversion",
            reason=hv_selection.reason,
        )
    if hv_selection.status != STATUS_READY or hv_selection.row is None:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_missing_conversion",
            reason=hv_selection.reason,
        )
    if hv_id and hv_id != hv_selection.heating_value_id:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="factor_match_inconsistent",
            reason=(
                "Matched heating_value_id does not equal the year-specific "
                "heating-value selection."
            ),
        )

    heating_row = hv_selection.row
    energy_kcal = activity_energy_kcal(
        normalized_decimal, heating_row, normalized_unit
    )
    if energy_kcal is None:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="factor_match_inconsistent",
            reason=(
                "Heating-value unit is incompatible with the activity unit. "
                "Source heating-value units are not rewritten."
            ),
        )

    conversion_row = lookup_kcal_to_tj_conversion(engineering_conversions)
    if conversion_row is None:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_missing_conversion",
            reason="Ready kcal→TJ engineering conversion is missing or ambiguous.",
        )
    energy_tj_value = kcal_to_tj(energy_kcal, conversion_row)
    if energy_tj_value is None:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_missing_conversion",
            reason="kcal→TJ conversion multiplier is invalid.",
        )

    masses: dict[str, Decimal] = {}
    gwp_values_by_gas: dict[str, Decimal] = {}
    gwp_rows: dict[str, pd.Series] = {}
    co2e_parts: dict[str, Decimal] = {}
    for gas in REQUIRED_COMBUSTION_GASES:
        factor_row = factor_rows[gas]
        expected_numerator = GAS_NUMERATOR_UNITS[gas]
        if _text(factor_row.get("numerator_unit")) != expected_numerator:
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="factor_match_inconsistent",
                reason=(
                    f"{gas} factor numerator must be {expected_numerator!r}."
                ),
            )
        if _text(factor_row.get("denominator_unit")) != "TJ":
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="factor_match_inconsistent",
                reason=f"{gas} factor denominator must be 'TJ'.",
            )
        factor_decimal = _to_decimal(factor_row.get("factor_value"))
        if factor_decimal is None:
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="factor_match_inconsistent",
                reason=f"{gas} factor value must be finite and greater than zero.",
            )
        gwp_row = select_gwp_row(
            gwp_values,
            gas=gas,
            emission_context=gwp_context,
            activity_date=activity_end or activity_start,
        )
        if gwp_row is None:
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="blocked_missing_gwp",
                reason=(
                    f"No unique ready GWP for {gas} in context "
                    f"{gwp_context!r}. Combustion does not use "
                    "fossil-methane GWP 30."
                ),
            )
        gwp_decimal = _to_decimal(gwp_row.get("gwp_value"))
        if gwp_decimal is None:
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="blocked_missing_gwp",
                reason=f"GWP value for {gas} is missing or invalid.",
            )
        if gas == "CH4" and gwp_decimal != Decimal("28"):
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="blocked_missing_gwp",
                reason=(
                    "Combustion methane must use CH4 GWP 28, not fossil-methane "
                    f"GWP {gwp_decimal}."
                ),
            )
        if gas == "N2O" and gwp_decimal != Decimal("265"):
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="blocked_missing_gwp",
                reason=f"Combustion N2O must use GWP 265, got {gwp_decimal}.",
            )
        if gas == "CO2" and gwp_decimal != Decimal("1"):
            return _blocked(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=float(normalized_decimal),
                normalized_unit=normalized_unit,
                status="blocked_missing_gwp",
                reason=f"Combustion CO2 must use GWP 1, got {gwp_decimal}.",
            )
        mass_kg = energy_tj_value * factor_decimal
        co2e_kg = mass_kg * gwp_decimal
        masses[gas] = mass_kg
        gwp_values_by_gas[gas] = gwp_decimal
        gwp_rows[gas] = gwp_row
        co2e_parts[gas] = co2e_kg

    assessment_bases = {
        _text(gwp_rows[gas].get("assessment_basis"))
        for gas in REQUIRED_COMBUSTION_GASES
    }
    assessment_bases.discard("")
    if len(assessment_bases) > 1:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="blocked_missing_gwp",
            reason=(
                "GWP assessment bases must not be mixed in one calculation: "
                + ", ".join(sorted(assessment_bases))
            ),
        )

    total_kg = (
        co2e_parts["CO2"] + co2e_parts["CH4"] + co2e_parts["N2O"]
    )
    total_t = total_kg / Decimal("1000")
    co2_factor = factor_rows["CO2"]
    trace = {
        "formula_id": COMBUSTION_FORMULA_ID,
        "formula_version": COMBUSTION_FORMULA_VERSION,
        "input": {
            "activity_value": str(normalized_decimal),
            "activity_unit": normalized_unit,
            "fuel_type": activity_type,
            "combustion_context": combustion_context,
        },
        "heating_value": {
            "heating_value_id": _text(heating_row.get("heating_value_id")),
            "value": str(heating_row.get("heating_value")).strip(),
            "unit": _text(heating_row.get("unit")),
            "fuel_subtype": _text(heating_row.get("fuel_subtype")),
            "high_heating_value": _text(heating_row.get("high_heating_value")),
            "high_heating_value_unit": _text(
                heating_row.get("high_heating_value_unit")
            ),
            "factor_year": _text(heating_row.get("factor_year")),
            "source_reference_id": _text(heating_row.get("source_reference_id")),
            "source_locator": _text(heating_row.get("source_locator")),
            "snapshot_id": _text(heating_row.get("snapshot_id")),
            "snapshot_sha256": _text(heating_row.get("snapshot_sha256")),
            "snapshot_local_path": _text(heating_row.get("snapshot_local_path")),
        },
        "energy": {
            "kcal": str(energy_kcal),
            "tj": str(energy_tj_value),
            "conversion_id": _text(conversion_row.get("conversion_id")),
            "multiplier": str(conversion_row.get("multiplier")).strip(),
            "source_unit": "kcal",
            "target_unit": "TJ",
        },
        "gases": {
            gas: {
                "factor_id": _text(factor_rows[gas].get("factor_id")),
                "factor_value": str(factor_rows[gas].get("factor_value")).strip(),
                "factor_unit": (
                    f"{GAS_NUMERATOR_UNITS[gas]}/TJ"
                ),
                "mass_kg": str(masses[gas]),
                "gwp": str(gwp_values_by_gas[gas]),
                "gwp_id": _text(gwp_rows[gas].get("gwp_id")),
                "gwp_emission_context": GWP_CONTEXT_FUEL_COMBUSTION,
                "co2e_kg": str(co2e_parts[gas]),
            }
            for gas in REQUIRED_COMBUSTION_GASES
        },
        "total": {
            "kgco2e": str(total_kg),
            "tco2e": str(total_t),
        },
    }
    gwp_source = _text(gwp_rows["CH4"].get("source_reference_id"))
    return _result_row(
        record_id=record_id,
        activity_type=activity_type,
        normalized_value=float(normalized_decimal),
        normalized_unit=normalized_unit,
        factor_id=_text(co2_factor.get("factor_id")),
        factor_value=float(_to_decimal(co2_factor.get("factor_value")) or 0),
        factor_numerator_unit=_text(co2_factor.get("numerator_unit")),
        factor_denominator_unit=_text(co2_factor.get("denominator_unit")),
        source_reference_id=_text(co2_factor.get("source_reference_id")) or pd.NA,
        formula_id=COMBUSTION_FORMULA_ID,
        formula_version=COMBUSTION_FORMULA_VERSION,
        heating_value_id=_text(heating_row.get("heating_value_id")),
        heating_value=float(_to_decimal(heating_row.get("heating_value")) or 0),
        heating_value_unit=_text(heating_row.get("unit")),
        heating_value_source_reference_id=_text(
            heating_row.get("source_reference_id")
        ),
        energy_tj=_decimal_to_float(energy_tj_value),
        co2_factor_id=_text(factor_rows["CO2"].get("factor_id")),
        ch4_factor_id=_text(factor_rows["CH4"].get("factor_id")),
        n2o_factor_id=_text(factor_rows["N2O"].get("factor_id")),
        co2_kg=_decimal_to_float(masses["CO2"]),
        ch4_kg=_decimal_to_float(masses["CH4"]),
        n2o_kg=_decimal_to_float(masses["N2O"]),
        co2_gwp=_decimal_to_float(gwp_values_by_gas["CO2"]),
        ch4_gwp=_decimal_to_float(gwp_values_by_gas["CH4"]),
        n2o_gwp=_decimal_to_float(gwp_values_by_gas["N2O"]),
        co2e_from_co2_kg=_decimal_to_float(co2e_parts["CO2"]),
        co2e_from_ch4_kg=_decimal_to_float(co2e_parts["CH4"]),
        co2e_from_n2o_kg=_decimal_to_float(co2e_parts["N2O"]),
        gwp_source_reference_id=gwp_source or pd.NA,
        engineering_conversion_id=_text(conversion_row.get("conversion_id")),
        calculation_trace=_dump_trace(trace),
        calculated_kgco2e=_decimal_to_float(total_kg),
        calculated_tco2e=_decimal_to_float(total_t),
        calculation_status="calculated",
        calculation_reason=(
            "Calculated using fuel activity × heating value → TJ, then "
            "CO2/CH4/N2O factors × combustion GWP (CH4=28, N2O=265)."
        ),
    )


def _calculate_ready_row(
    *,
    record_id: str,
    activity_type: str,
    normalized_row: pd.Series | None,
    ready_candidates: pd.DataFrame,
    emission_factors: pd.DataFrame,
    heating_values: pd.DataFrame,
    gwp_values: pd.DataFrame,
    engineering_conversions: pd.DataFrame,
    activity_start: Any = None,
    activity_end: Any = None,
    fuel_subtype: Any = "",
) -> dict[str, Any]:
    if normalized_row is None:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=pd.NA,
            normalized_unit=pd.NA,
            status="invalid_normalized_input",
            reason="Normalized activity record is missing for this record_id.",
        )

    normalized_value_raw = normalized_row.get("normalized_value")
    normalized_unit = _text(normalized_row.get("normalized_unit"))
    normalized_decimal = _to_decimal(normalized_value_raw)
    if activity_start is None:
        activity_start = normalized_row.get("activity_start_date")
    if activity_end is None:
        activity_end = normalized_row.get("activity_end_date")

    if normalized_decimal is None or not normalized_unit:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=normalized_value_raw,
            normalized_unit=normalized_unit or pd.NA,
            status="invalid_normalized_input",
            reason=(
                "Normalized value/unit must be present, finite, and greater "
                "than zero."
            ),
        )

    if ready_candidates.empty:
        return _blocked(
            record_id=record_id,
            activity_type=activity_type,
            normalized_value=float(normalized_decimal),
            normalized_unit=normalized_unit,
            status="factor_match_inconsistent",
            reason=(
                "Readiness is ready but the number of matched_ready candidates "
                f"is {len(ready_candidates)}, expected exactly 1 or a CO2/CH4/"
                "N2O group."
            ),
        )

    candidate_gases = {
        _text(value) for value in ready_candidates.get("gas", pd.Series(dtype=str))
    }
    if len(ready_candidates) == 1 and candidate_gases <= {"CO2e", ""}:
        return _calculate_direct_co2e(
            record_id=record_id,
            activity_type=activity_type,
            normalized_decimal=normalized_decimal,
            normalized_unit=normalized_unit,
            candidate=ready_candidates.iloc[0],
            emission_factors=emission_factors,
        )

    if set(REQUIRED_COMBUSTION_GASES).issubset(candidate_gases) or (
        len(ready_candidates) == 3 and candidate_gases == set(REQUIRED_COMBUSTION_GASES)
    ):
        return _calculate_combustion(
            record_id=record_id,
            activity_type=activity_type,
            normalized_decimal=normalized_decimal,
            normalized_unit=normalized_unit,
            ready_candidates=ready_candidates,
            emission_factors=emission_factors,
            heating_values=heating_values,
            gwp_values=gwp_values,
            engineering_conversions=engineering_conversions,
            activity_start=activity_start,
            activity_end=activity_end,
            fuel_subtype=fuel_subtype,
        )

    return _blocked(
        record_id=record_id,
        activity_type=activity_type,
        normalized_value=float(normalized_decimal),
        normalized_unit=normalized_unit,
        status="factor_match_inconsistent",
        reason=(
            "Readiness is ready but the number of matched_ready candidates "
            f"is {len(ready_candidates)}, expected exactly 1."
        ),
        )


def _same_calendar_reporting_year(start: Any, end: Any) -> int | None:
    start_ts = pd.to_datetime(start, errors="coerce")
    end_ts = pd.to_datetime(end, errors="coerce")
    if pd.isna(start_ts) or pd.isna(end_ts):
        return None
    start_year = int(start_ts.year)
    end_year = int(end_ts.year)
    if start_year != end_year:
        return None
    return start_year


_DEFAULT_REFERENCE_DIR = Path(__file__).resolve().parents[2] / "data" / "reference"
REFRIGERANT_ACTIVITY_TYPE = "refrigerant_refill"
READINESS_REFRIGERANT_ACTUAL_REFILL = "refrigerant_actual_refill"
PURCHASED_STEEL_ACTIVITY_TYPE = "purchased_steel"
READINESS_PURCHASED_STEEL_CATEGORY1 = "purchased_steel_category1"


def _purchased_steel_calc_record(
    activity_row: pd.Series | None,
    *,
    record_id: str,
    normalized_row: pd.Series | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_id": record_id,
        "activity_type": PURCHASED_STEEL_ACTIVITY_TYPE,
    }
    if normalized_row is not None:
        original_value = normalized_row.get("original_value")
        original_unit = _text(normalized_row.get("original_unit"))
        if not _is_blank(original_value):
            record["activity_value"] = original_value
        if original_unit:
            record["unit"] = original_unit
    if activity_row is None:
        return record
    reporting_year = _same_calendar_reporting_year(
        activity_row.get("activity_start_date"),
        activity_row.get("activity_end_date"),
    )
    record.update(
        {
            "record_id": _text(activity_row.get("record_id")) or record_id,
            "activity_type": _text(activity_row.get("activity_type"))
            or PURCHASED_STEEL_ACTIVITY_TYPE,
            "record_type": _text(activity_row.get("record_type")),
            "calculation_method": _text(activity_row.get("calculation_method")),
            "supplier_name": _text(activity_row.get("supplier_name")),
            "steel_product_type": _text(activity_row.get("steel_product_type")),
            "product_identifier": _text(activity_row.get("product_identifier")),
            "product_id": _text(activity_row.get("product_id")),
            "activity_value": activity_row.get("activity_value"),
            "unit": _text(activity_row.get("unit")),
            "purchased_quantity": activity_row.get("activity_value"),
            "purchased_unit": _text(activity_row.get("unit")),
            "emission_factor_value": activity_row.get("emission_factor_value"),
            "emission_factor_unit": _text(
                activity_row.get("emission_factor_unit")
            ),
            "factor_boundary": _text(activity_row.get("factor_boundary")),
            "factor_geography": _text(activity_row.get("factor_geography")),
            "factor_year": activity_row.get("factor_year"),
            "factor_source_id": _text(activity_row.get("factor_source_id")),
            "evidence_reference": _text(activity_row.get("evidence_reference"))
            or _text(activity_row.get("source_locator")),
            "source_document_id": _text(activity_row.get("source_document_id")),
            "source_locator": _text(activity_row.get("source_locator")),
            "includes_pre_tier1_supply_chain_transport": _text(
                activity_row.get("includes_pre_tier1_supply_chain_transport")
            ),
            "includes_tier1_to_reporting_company_transport": _text(
                activity_row.get(
                    "includes_tier1_to_reporting_company_transport"
                )
            ),
            "factor_includes_tier1_to_reporting_company_transport": _text(
                activity_row.get(
                    "factor_includes_tier1_to_reporting_company_transport"
                )
            ),
            "tier1_to_reporting_company_transport_control": _text(
                activity_row.get(
                    "tier1_to_reporting_company_transport_control"
                )
            ),
            "includes_tier2_to_tier1_transport": _text(
                activity_row.get("includes_tier2_to_tier1_transport")
            ),
            "technology": _text(
                activity_row.get("technology") or activity_row.get("process")
            ),
            "reporting_period_id": _text(activity_row.get("reporting_period_id")),
        }
    )
    if reporting_year is not None:
        record["reporting_year"] = reporting_year
    return record


def _calculate_purchased_steel_result(
    activity_row: pd.Series | None,
    emission_factors: pd.DataFrame,
    *,
    record_id: str,
    normalized_row: pd.Series | None = None,
) -> dict[str, Any]:
    from carbon_ledger.purchased_steel import calculate_purchased_steel

    result = calculate_purchased_steel(
        _purchased_steel_calc_record(
            activity_row,
            record_id=record_id,
            normalized_row=normalized_row,
        ),
        registered_factors=emission_factors,
    )
    return result.to_calculation_row()


def _refrigerant_calc_record(activity_row: pd.Series | None) -> dict[str, Any]:
    if activity_row is None:
        return {}
    reporting_year = _same_calendar_reporting_year(
        activity_row.get("activity_start_date"),
        activity_row.get("activity_end_date"),
    )
    record: dict[str, Any] = {
        "record_id": _text(activity_row.get("record_id")),
        "actual_refill_kg": activity_row.get("activity_value"),
        "refrigerant_code": _text(activity_row.get("refrigerant_code")),
        "refill_confirmed": _text(activity_row.get("refill_confirmed")),
        "source_document_id": _text(activity_row.get("source_document_id")),
        "evidence_reference": _text(activity_row.get("source_locator")),
        "reporting_period_id": _text(activity_row.get("reporting_period_id")),
    }
    if reporting_year is not None:
        record["reporting_year"] = reporting_year
    for key in ("actual_refill_date", "refill_date", "activity_end_date"):
        value = activity_row.get(key)
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass
        stamp = pd.to_datetime(value, errors="coerce")
        if pd.notna(stamp):
            record[key] = pd.Timestamp(stamp).strftime("%Y-%m-%d")
        else:
            text = str(value).strip()
            if text and text.lower() not in {"nan", "nat", "none"}:
                record[key] = text
    return record


def _calculate_refrigerant_result(
    activity_row: pd.Series | None,
    gwp_values: pd.DataFrame,
) -> dict[str, Any]:
    from carbon_ledger.refrigerants import (
        RefrigerantRegistryError,
        calculate_actual_refill,
        load_refrigerant_compositions,
    )

    try:
        compositions = load_refrigerant_compositions(_DEFAULT_REFERENCE_DIR)
    except RefrigerantRegistryError:
        compositions = pd.DataFrame()
    result = calculate_actual_refill(
        _refrigerant_calc_record(activity_row),
        compositions=compositions,
        gwp_values=gwp_values,
    )
    return result.to_calculation_row()


def calculate_activity_emissions(
    normalized_records: pd.DataFrame,
    candidate_matches: pd.DataFrame,
    activity_readiness: pd.DataFrame,
    emission_factors: pd.DataFrame,
    heating_values: pd.DataFrame | None = None,
    gwp_values: pd.DataFrame | None = None,
    engineering_conversions: pd.DataFrame | None = None,
    activity_records: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Calculate emissions only for fully ready and consistent activities.

    Returns one output row for every activity-readiness row. Does not mutate
    inputs and does not invent fallback factors or zeros for blocked records.
    """
    normalized = normalized_records.copy(deep=True)
    candidates = candidate_matches.copy(deep=True)
    readiness = activity_readiness.copy(deep=True)
    factors = emission_factors.copy(deep=True)
    heating = (
        heating_values.copy(deep=True)
        if heating_values is not None
        else empty_heating_values()
    )
    gwp = (
        gwp_values.copy(deep=True)
        if gwp_values is not None
        else pd.DataFrame()
    )
    conversions = (
        engineering_conversions.copy(deep=True)
        if engineering_conversions is not None
        else pd.DataFrame()
    )
    activities = (
        activity_records.copy(deep=True)
        if activity_records is not None
        else pd.DataFrame()
    )

    results: list[dict[str, Any]] = []

    for _, readiness_row in readiness.iterrows():
        record_id = _text(readiness_row.get("record_id"))
        activity_type = _text(readiness_row.get("activity_type"))
        readiness_status = _text(readiness_row.get("calculation_readiness"))
        normalized_row = _lookup_normalized(normalized, record_id)
        activity_row = None
        if not activities.empty and "record_id" in activities.columns:
            matched_activity = activities.loc[
                activities["record_id"].astype(str) == record_id
            ]
            if not matched_activity.empty:
                activity_row = matched_activity.iloc[0]

        normalized_value = (
            normalized_row.get("normalized_value")
            if normalized_row is not None
            else pd.NA
        )
        normalized_unit = (
            _text(normalized_row.get("normalized_unit"))
            if normalized_row is not None
            else ""
        )
        activity_start = (
            activity_row.get("activity_start_date")
            if activity_row is not None
            else None
        )
        activity_end = (
            activity_row.get("activity_end_date")
            if activity_row is not None
            else None
        )
        fuel_subtype = (
            activity_row.get("fuel_subtype") if activity_row is not None else ""
        )

        if activity_type == REFRIGERANT_ACTIVITY_TYPE or (
            readiness_status == READINESS_REFRIGERANT_ACTUAL_REFILL
        ):
            results.append(_calculate_refrigerant_result(activity_row, gwp))
            continue

        if activity_type == PURCHASED_STEEL_ACTIVITY_TYPE or (
            readiness_status == READINESS_PURCHASED_STEEL_CATEGORY1
        ):
            results.append(
                _calculate_purchased_steel_result(
                    activity_row,
                    factors,
                    record_id=record_id,
                    normalized_row=normalized_row,
                )
            )
            continue

        if readiness_status in PASSTHROUGH_STATUSES:
            results.append(
                _result_row(
                    record_id=record_id,
                    activity_type=activity_type,
                    normalized_value=normalized_value,
                    normalized_unit=normalized_unit or pd.NA,
                    calculation_status=readiness_status,
                    calculation_reason=_passthrough_reason(readiness_row),
                    **_empty_result_fields(),
                )
            )
            continue

        if readiness_status == "ready":
            ready_candidates = _ready_candidates(candidates, record_id)
            results.append(
                _calculate_ready_row(
                    record_id=record_id,
                    activity_type=activity_type,
                    normalized_row=normalized_row,
                    ready_candidates=ready_candidates,
                    emission_factors=factors,
                    heating_values=heating,
                    gwp_values=gwp,
                    engineering_conversions=conversions,
                    activity_start=activity_start,
                    activity_end=activity_end,
                    fuel_subtype=fuel_subtype,
                )
            )
            continue

        results.append(
            _result_row(
                record_id=record_id,
                activity_type=activity_type,
                normalized_value=normalized_value,
                normalized_unit=normalized_unit or pd.NA,
                calculation_status="factor_match_inconsistent",
                calculation_reason=(
                    f"Unrecognized or inconsistent readiness status "
                    f"{readiness_status!r}."
                ),
                **_empty_result_fields(),
            )
        )

    if not results:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    output = pd.DataFrame(results)
    for column in OUTPUT_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    extra = [column for column in output.columns if column not in OUTPUT_COLUMNS]
    output = output[list(OUTPUT_COLUMNS) + extra]
    output = output.sort_values("record_id", kind="mergesort").reset_index(
        drop=True
    )
    return output
