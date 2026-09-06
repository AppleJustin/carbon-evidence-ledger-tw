"""Deterministic emission-factor matching and calculation readiness.

Phase 5B decides which registered factors are candidates for each activity and
whether calculation is ready or blocked. It does not calculate emissions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from carbon_ledger.heating import (
    STATUS_AMBIGUOUS,
    STATUS_INVALID_SUBTYPE,
    STATUS_READY,
    STATUS_SUBTYPE_REQUIRED,
    empty_heating_values,
    select_heating_value,
)

CANDIDATE_COLUMNS = [
    "record_id",
    "activity_type",
    "factor_id",
    "gas",
    "activity_unit",
    "factor_denominator_unit",
    "match_status",
    "match_reason",
    "required_conversion",
    "heating_value_id",
]

READINESS_COLUMNS = [
    "record_id",
    "activity_type",
    "calculation_readiness",
    "candidate_factor_count",
    "blocking_dependency",
    "readiness_reason",
]

NOT_EMISSIONS_ACTIVITY_TYPES = {
    "finished_goods_output",
    "scrap_output",
}

KNOWN_EMISSIONS_ACTIVITY_TYPES = {
    "grid_electricity",
    "natural_gas",
    "diesel",
}

KNOWN_NO_FACTOR_ACTIVITY_TYPES = {
    "third_party_transport",
}

REFRIGERANT_ACTIVITY_TYPES = {
    "refrigerant_refill",
}
READINESS_REFRIGERANT_ACTUAL_REFILL = "refrigerant_actual_refill"

PURCHASED_STEEL_ACTIVITY_TYPES = {
    "purchased_steel",
}
READINESS_PURCHASED_STEEL_CATEGORY1 = "purchased_steel_category1"

ENTERPRISE_ELECTRICITY_PROCESS_USES = frozenset(
    {
        "general_factory",
        "heat_treatment",
        "forging",
    }
)
ENTERPRISE_ELECTRICITY_CATEGORIES = frozenset(
    {
        "industrial_enterprise_inventory",
        "industry",
    }
)
REQUIRED_COMBUSTION_GASES = frozenset({"CO2", "CH4", "N2O"})
COMBUSTION_FACTOR_STATUSES = frozenset(
    {"registered_missing_conversion", "ready"}
)


@dataclass
class FactorMatchingResult:
    """Candidate factor matches and per-activity calculation readiness."""

    candidate_matches: pd.DataFrame
    activity_readiness: pd.DataFrame


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


def _parse_validity_bound(value: Any) -> tuple[str, pd.Timestamp | None]:
    """Return (blank|ok|malformed, timestamp). Malformed is never open-ended."""
    if _is_blank(value):
        return "blank", None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return "malformed", None
    return "ok", pd.Timestamp(parsed)


def _parse_optional_timestamp(value: Any) -> pd.Timestamp | None:
    kind, stamp = _parse_validity_bound(value)
    if kind != "ok":
        return None
    return stamp


def _activity_unit(row: pd.Series) -> str:
    """Prefer normalized_unit when present; otherwise use original unit."""
    if "normalized_unit" in row.index and not _is_blank(row.get("normalized_unit")):
        return _text(row.get("normalized_unit"))
    return _text(row.get("unit"))


def _factor_covers_activity_period(
    factor_row: pd.Series,
    activity_start: Any,
    activity_end: Any,
    *,
    reporting_year: int | None = None,
) -> bool:
    """True only when validity covers the activity date or full reporting year.

    Malformed valid_from/valid_to are not treated as blank or open-ended.
    Blank validity remains usable for tables that never stated a period.
    """
    from_kind, valid_from = _parse_validity_bound(factor_row.get("valid_from"))
    to_kind, valid_to = _parse_validity_bound(factor_row.get("valid_to"))
    if from_kind == "malformed" or to_kind == "malformed":
        return False
    start_kind, start = _parse_validity_bound(activity_start)
    end_kind, end = _parse_validity_bound(activity_end)
    if start_kind == "malformed" or end_kind == "malformed":
        return False
    if start is None and end is None:
        if reporting_year is None:
            return valid_from is None and valid_to is None
        year_start = pd.Timestamp(int(reporting_year), 1, 1)
        year_end = pd.Timestamp(int(reporting_year), 12, 31)
        if valid_from is not None and valid_from > year_start:
            return False
        if valid_to is not None and valid_to < year_end:
            return False
        return True
    if start is None:
        start = end
    if end is None:
        end = start
    if start is None or end is None:
        return False
    if valid_from is not None and valid_from > start:
        return False
    if valid_to is not None and valid_to < end:
        return False
    return True


def _active_factors(
    emission_factors: pd.DataFrame,
    *,
    activity_type: str,
    combustion_context: str | None = None,
) -> pd.DataFrame:
    if emission_factors.empty:
        return emission_factors.copy()

    frame = emission_factors.copy()
    mask = frame["activity_type"].astype(str).str.strip() == activity_type
    mask &= frame["factor_status"].astype(str).str.strip() != "inactive"
    if combustion_context is not None:
        mask &= (
            frame["combustion_context"].astype(str).str.strip()
            == combustion_context
        )
    return frame.loc[mask].copy()


def _candidate_row(
    *,
    record_id: str,
    activity_type: str,
    factor_row: pd.Series,
    activity_unit: str,
    match_status: str,
    match_reason: str,
    heating_value_id: str = "",
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "activity_type": activity_type,
        "factor_id": _text(factor_row.get("factor_id")),
        "gas": _text(factor_row.get("gas")),
        "activity_unit": activity_unit,
        "factor_denominator_unit": _text(factor_row.get("denominator_unit")),
        "match_status": match_status,
        "match_reason": match_reason,
        "required_conversion": _text(factor_row.get("required_conversion")),
        "heating_value_id": heating_value_id,
    }


def _factor_category(factor_row: pd.Series) -> str:
    if "factor_category" in factor_row.index and not _is_blank(
        factor_row.get("factor_category")
    ):
        return _text(factor_row.get("factor_category"))
    blob = " ".join(
        [
            _text(factor_row.get("notes")),
            _text(factor_row.get("source_locator")),
        ]
    )
    marker = "category="
    if marker not in blob:
        return ""
    raw = blob.split(marker, 1)[1]
    token = raw.split(";", 1)[0].split(" ", 1)[0].strip()
    return token.strip(".,")


def _activity_electricity_category(process_use: str) -> str:
    if process_use in ENTERPRISE_ELECTRICITY_PROCESS_USES:
        return "industrial_enterprise_inventory"
    return ""


def _electricity_factor_applies(
    factor_row: pd.Series,
    process_use: str,
) -> bool:
    """Do not silently pick a categorized 2025 factor without use context."""
    category = _factor_category(factor_row)
    if not category:
        return True
    activity_category = _activity_electricity_category(process_use)
    if category in ENTERPRISE_ELECTRICITY_CATEGORIES:
        return activity_category in ENTERPRISE_ELECTRICITY_CATEGORIES
    # Residential / public-sales-average never apply without matching context.
    return activity_category == category


def _reporting_year_value(value: Any) -> int | None:
    if _is_blank(value):
        return None
    try:
        year = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if year < 1900 or year > 2100:
        return None
    return year


def _match_grid_electricity(
    *,
    record_id: str,
    activity_type: str,
    activity_unit: str,
    activity_start: Any,
    activity_end: Any,
    process_use: str,
    emission_factors: pd.DataFrame,
    reporting_year: int | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    factors = _active_factors(
        emission_factors, activity_type="grid_electricity"
    )
    for _, factor in factors.iterrows():
        if not _factor_covers_activity_period(
            factor,
            activity_start,
            activity_end,
            reporting_year=reporting_year,
        ):
            continue
        if not _electricity_factor_applies(factor, process_use):
            continue
        status = _text(factor.get("factor_status"))
        denominator = _text(factor.get("denominator_unit"))
        required_conversion = _text(factor.get("required_conversion"))
        if (
            status == "ready"
            and denominator == activity_unit
            and required_conversion == "not_required"
        ):
            candidates.append(
                _candidate_row(
                    record_id=record_id,
                    activity_type=activity_type,
                    factor_row=factor,
                    activity_unit=activity_unit,
                    match_status="matched_ready",
                    match_reason=(
                        "Ready electricity factor with compatible "
                        f"denominator unit {denominator!r}."
                    ),
                )
            )
    return candidates


def _combustion_group_state(factor_rows: list[pd.Series]) -> str:
    gases = {_text(row.get("gas")) for row in factor_rows}
    if gases != REQUIRED_COMBUSTION_GASES:
        return "incomplete"
    sources = {_text(row.get("source_reference_id")) for row in factor_rows}
    years = {_text(row.get("factor_year")) for row in factor_rows}
    contexts = {_text(row.get("combustion_context")) for row in factor_rows}
    if (
        len(sources) != 1
        or "" in sources
        or len(years) != 1
        or len(contexts) != 1
        or "" in contexts
    ):
        return "conflicting"
    return "consistent"


def _match_fuel_combustion(
    *,
    record_id: str,
    activity_type: str,
    activity_unit: str,
    activity_start: Any,
    activity_end: Any,
    emission_factors: pd.DataFrame,
    heating_values: pd.DataFrame,
    combustion_context: str,
    blocked_reason_prefix: str,
    fuel_subtype: str = "",
    reporting_year: int | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Return (candidates, group_override_status).

    group_override_status is empty, incomplete, conflicting, ambiguous,
    subtype_required, or invalid_subtype.
    """
    hv = select_heating_value(
        heating_values,
        fuel_type=activity_type,
        activity_start=activity_start,
        activity_end=activity_end,
        fuel_subtype=fuel_subtype,
        reporting_year=reporting_year,
    )
    factors = _active_factors(
        emission_factors,
        activity_type=activity_type,
        combustion_context=combustion_context,
    )
    eligible_rows: list[pd.Series] = []
    for _, factor in factors.iterrows():
        if not _factor_covers_activity_period(
            factor,
            activity_start,
            activity_end,
            reporting_year=reporting_year,
        ):
            continue
        status = _text(factor.get("factor_status"))
        if status not in COMBUSTION_FACTOR_STATUSES:
            continue
        eligible_rows.append(factor)

    heating_ready = hv.status == STATUS_READY
    heating_ambiguous = hv.status == STATUS_AMBIGUOUS
    subtype_required = hv.status == STATUS_SUBTYPE_REQUIRED
    invalid_subtype = hv.status == STATUS_INVALID_SUBTYPE
    hv_id = hv.heating_value_id if heating_ready else ""

    candidates: list[dict[str, Any]] = []
    for factor in eligible_rows:
        required_conversion = _text(factor.get("required_conversion"))
        if heating_ambiguous or subtype_required or invalid_subtype:
            match_status = "matched_blocked_dependency"
            match_reason = hv.reason
        elif heating_ready:
            match_status = "matched_ready"
            match_reason = (
                f"{blocked_reason_prefix} uses heating value "
                f"{hv_id} for the activity year."
            )
        else:
            match_status = "matched_blocked_dependency"
            match_reason = (
                f"{blocked_reason_prefix} activity unit {activity_unit!r} "
                "cannot use factor denominator "
                f"{_text(factor.get('denominator_unit'))!r} until "
                f"{required_conversion} is verified. {hv.reason}"
            )
        candidates.append(
            _candidate_row(
                record_id=record_id,
                activity_type=activity_type,
                factor_row=factor,
                activity_unit=activity_unit,
                match_status=match_status,
                match_reason=match_reason,
                heating_value_id=hv_id,
            )
        )

    if heating_ambiguous:
        return candidates, "ambiguous"
    if subtype_required:
        return candidates, "subtype_required"
    if invalid_subtype:
        return candidates, "invalid_subtype"
    if not heating_ready:
        return candidates, ""
    group_state = _combustion_group_state(eligible_rows)
    if group_state != "consistent":
        for item in candidates:
            item["match_status"] = "matched_blocked_dependency"
        return candidates, group_state
    return candidates, ""


def _match_natural_gas(
    *,
    record_id: str,
    activity_type: str,
    activity_unit: str,
    activity_start: Any,
    activity_end: Any,
    emission_factors: pd.DataFrame,
    heating_values: pd.DataFrame,
    fuel_subtype: str = "",
    reporting_year: int | None = None,
) -> tuple[list[dict[str, Any]], str]:
    return _match_fuel_combustion(
        record_id=record_id,
        activity_type=activity_type,
        activity_unit=activity_unit,
        activity_start=activity_start,
        activity_end=activity_end,
        emission_factors=emission_factors,
        heating_values=heating_values,
        combustion_context="stationary_combustion",
        blocked_reason_prefix="Natural-gas",
        fuel_subtype=fuel_subtype,
        reporting_year=reporting_year,
    )


def _match_diesel(
    *,
    record_id: str,
    activity_type: str,
    activity_unit: str,
    process_use: str,
    activity_start: Any,
    activity_end: Any,
    emission_factors: pd.DataFrame,
    heating_values: pd.DataFrame,
    reporting_year: int | None = None,
) -> tuple[list[dict[str, Any]], str]:
    if process_use != "company_vehicle":
        return [], ""
    return _match_fuel_combustion(
        record_id=record_id,
        activity_type=activity_type,
        activity_unit=activity_unit,
        activity_start=activity_start,
        activity_end=activity_end,
        emission_factors=emission_factors,
        heating_values=heating_values,
        combustion_context="mobile_combustion",
        blocked_reason_prefix="Company-vehicle diesel",
        reporting_year=reporting_year,
    )


def _activity_year_label(activity_start: Any, activity_end: Any) -> str:
    start = _parse_optional_timestamp(activity_start)
    end = _parse_optional_timestamp(activity_end)
    if start is None and end is None:
        return ""
    if start is not None and end is not None and start.year == end.year:
        return str(int(start.year))
    if start is not None:
        return str(int(start.year))
    if end is not None:
        return str(int(end.year))
    return ""


def _registered_years_for_activity(
    emission_factors: pd.DataFrame | None,
    activity_type: str,
) -> list[str]:
    if emission_factors is None or emission_factors.empty:
        return []
    if "activity_type" not in emission_factors.columns:
        return []
    rows = emission_factors.loc[
        emission_factors["activity_type"].astype(str) == activity_type
    ]
    if "factor_status" in rows.columns:
        rows = rows.loc[rows["factor_status"].astype(str) != "inactive"]
    if "factor_year" not in rows.columns:
        return []
    return sorted(
        {
            _text(value)
            for value in rows["factor_year"].tolist()
            if not _is_blank(value)
        }
    )


def _build_readiness_row(
    *,
    record_id: str,
    activity_type: str,
    candidates: list[dict[str, Any]],
    activity_start: Any = None,
    activity_end: Any = None,
    emission_factors: pd.DataFrame | None = None,
    group_override: str = "",
) -> dict[str, Any]:
    count = len(candidates)

    if activity_type in NOT_EMISSIONS_ACTIVITY_TYPES:
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "not_emissions_activity",
            "candidate_factor_count": 0,
            "blocking_dependency": pd.NA,
            "readiness_reason": (
                "Production or scrap output is operational evidence, "
                "not an emissions activity."
            ),
        }

    if activity_type in KNOWN_NO_FACTOR_ACTIVITY_TYPES:
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "no_factor_configured",
            "candidate_factor_count": 0,
            "blocking_dependency": pd.NA,
            "readiness_reason": (
                f"No suitable emission factor is configured yet for "
                f"{activity_type!r} in the current MVP."
            ),
        }

    if activity_type in REFRIGERANT_ACTIVITY_TYPES:
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": READINESS_REFRIGERANT_ACTUAL_REFILL,
            "candidate_factor_count": 0,
            "blocking_dependency": pd.NA,
            "readiness_reason": (
                "Refrigerant actual-refill uses AR5 GWP, not an "
                "emission-factor match. Leak-rate estimation is not applied."
            ),
        }

    if activity_type in PURCHASED_STEEL_ACTIVITY_TYPES:
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": READINESS_PURCHASED_STEEL_CATEGORY1,
            "candidate_factor_count": 0,
            "blocking_dependency": pd.NA,
            "readiness_reason": (
                "Purchased-steel Category 1 uses supplier-specific evidence "
                "or a registered average-data factor, not the Scope 1/2 "
                "fuel matcher."
            ),
        }

    if activity_type not in KNOWN_EMISSIONS_ACTIVITY_TYPES:
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "unsupported_activity_type",
            "candidate_factor_count": 0,
            "blocking_dependency": pd.NA,
            "readiness_reason": (
                f"Activity type {activity_type!r} is unsupported for "
                "factor matching in Phase 5B."
            ),
        }

    if count == 0:
        activity_year = _activity_year_label(activity_start, activity_end)
        registered_years = _registered_years_for_activity(
            emission_factors,
            activity_type,
        )
        if activity_type == "grid_electricity" and activity_year:
            registered = ", ".join(registered_years) if registered_years else "(none)"
            reason = (
                "尚未找到適用於這筆活動期間的官方排放係數。"
                f" 活動期間：{activity_year}。"
                f" 目前已登錄：{registered}。"
                " 系統不會自動使用不同年度的係數。"
            )
        else:
            reason = (
                f"No eligible emission-factor candidates were found for "
                f"{activity_type!r}."
            )
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "no_factor_configured",
            "candidate_factor_count": 0,
            "blocking_dependency": pd.NA,
            "readiness_reason": reason,
        }

    statuses = {item["match_status"] for item in candidates}
    if group_override == "ambiguous":
        dependency = candidates[0]["required_conversion"] if candidates else pd.NA
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "blocked_ambiguous_conversion",
            "candidate_factor_count": count,
            "blocking_dependency": dependency,
            "readiness_reason": (
                "Multiple conflicting ready heating values match this "
                "activity year. Newest row is not selected."
            ),
        }
    if group_override == "subtype_required":
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "blocked_natural_gas_type_required",
            "candidate_factor_count": count,
            "blocking_dependency": "natural_gas_type_ng1_or_ng2",
            "readiness_reason": (
                "Natural-gas type NG1 or NG2 is required before the official "
                "heating value can be applied. The type is not inferred."
            ),
        }
    if group_override == "invalid_subtype":
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "factor_match_inconsistent",
            "candidate_factor_count": count,
            "blocking_dependency": "natural_gas_type_ng1_or_ng2",
            "readiness_reason": (
                "Natural-gas subtype is not a valid official type "
                "(NG1 or NG2)."
            ),
        }
    if group_override == "incomplete":
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "blocked_incomplete_gas_factors",
            "candidate_factor_count": count,
            "blocking_dependency": pd.NA,
            "readiness_reason": (
                "A valid multi-gas group requires CO2, CH4, and N2O. "
                "Partial totals are not calculated."
            ),
        }
    if group_override == "conflicting":
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "blocked_conflicting_factor_group",
            "candidate_factor_count": count,
            "blocking_dependency": pd.NA,
            "readiness_reason": (
                "CO2/CH4/N2O factors do not share one official source/"
                "version family."
            ),
        }
    if statuses == {"matched_ready"}:
        if activity_type == "grid_electricity":
            ready_ids = {
                item["factor_id"]
                for item in candidates
                if item["match_status"] == "matched_ready"
            }
            if len(ready_ids) > 1:
                return {
                    "record_id": record_id,
                    "activity_type": activity_type,
                    "calculation_readiness": "blocked_ambiguous_factor",
                    "candidate_factor_count": count,
                    "blocking_dependency": pd.NA,
                    "readiness_reason": (
                        "Multiple ready electricity factors cover this "
                        "activity period. The newest row is not selected."
                    ),
                }
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "ready",
            "candidate_factor_count": count,
            "blocking_dependency": pd.NA,
            "readiness_reason": (
                "Eligible ready factor candidate(s) found with compatible units."
            ),
        }

    if "matched_blocked_dependency" in statuses:
        blocked = [
            item
            for item in candidates
            if item["match_status"] == "matched_blocked_dependency"
        ]
        dependency = blocked[0]["required_conversion"]
        return {
            "record_id": record_id,
            "activity_type": activity_type,
            "calculation_readiness": "blocked_missing_conversion",
            "candidate_factor_count": count,
            "blocking_dependency": dependency,
            "readiness_reason": (
                "Factor candidates exist but calculation is blocked until "
                f"{dependency} is verified."
            ),
        }

    return {
        "record_id": record_id,
        "activity_type": activity_type,
        "calculation_readiness": "no_factor_configured",
        "candidate_factor_count": count,
        "blocking_dependency": pd.NA,
        "readiness_reason": (
            "Factor candidates were found but none are ready for calculation."
        ),
    }


def match_activity_factors(
    activity_records: pd.DataFrame,
    emission_factors: pd.DataFrame,
    calculation_dependencies: pd.DataFrame,
    heating_values: pd.DataFrame | None = None,
) -> FactorMatchingResult:
    """Match registered emission factors to activities without calculating.

    ``calculation_dependencies`` is accepted for pipeline consistency.
    Heating-value year matching decides whether fuel combustion candidates
    become ``matched_ready``.
    """
    activities = activity_records.copy(deep=True)
    factors = emission_factors.copy(deep=True)
    _ = calculation_dependencies.copy(deep=True)
    heating = (
        heating_values.copy(deep=True)
        if heating_values is not None
        else empty_heating_values()
    )

    all_candidates: list[dict[str, Any]] = []
    readiness_rows: list[dict[str, Any]] = []

    for _, activity in activities.iterrows():
        record_id = _text(activity.get("record_id"))
        activity_type = _text(activity.get("activity_type"))
        activity_unit = _activity_unit(activity)
        process_use = _text(activity.get("process_use"))
        fuel_subtype = _text(activity.get("fuel_subtype"))
        start = activity.get("activity_start_date")
        end = activity.get("activity_end_date")
        reporting_year = _reporting_year_value(activity.get("reporting_year"))

        candidates: list[dict[str, Any]] = []
        group_override = ""
        if activity_type == "grid_electricity":
            candidates = _match_grid_electricity(
                record_id=record_id,
                activity_type=activity_type,
                activity_unit=activity_unit,
                activity_start=start,
                activity_end=end,
                process_use=process_use,
                emission_factors=factors,
                reporting_year=reporting_year,
            )
        elif activity_type == "natural_gas":
            candidates, group_override = _match_natural_gas(
                record_id=record_id,
                activity_type=activity_type,
                activity_unit=activity_unit,
                activity_start=start,
                activity_end=end,
                emission_factors=factors,
                heating_values=heating,
                fuel_subtype=fuel_subtype,
                reporting_year=reporting_year,
            )
        elif activity_type == "diesel":
            candidates, group_override = _match_diesel(
                record_id=record_id,
                activity_type=activity_type,
                activity_unit=activity_unit,
                process_use=process_use,
                activity_start=start,
                activity_end=end,
                emission_factors=factors,
                heating_values=heating,
                reporting_year=reporting_year,
            )

        all_candidates.extend(candidates)
        readiness_rows.append(
            _build_readiness_row(
                record_id=record_id,
                activity_type=activity_type,
                candidates=candidates,
                activity_start=start,
                activity_end=end,
                emission_factors=factors,
                group_override=group_override,
            )
        )

    if all_candidates:
        candidate_matches = pd.DataFrame(
            all_candidates, columns=CANDIDATE_COLUMNS
        )
        candidate_matches = candidate_matches.sort_values(
            ["record_id", "factor_id", "gas"],
            kind="mergesort",
        ).reset_index(drop=True)
    else:
        candidate_matches = pd.DataFrame(columns=CANDIDATE_COLUMNS)

    if readiness_rows:
        activity_readiness = pd.DataFrame(
            readiness_rows, columns=READINESS_COLUMNS
        )
    else:
        activity_readiness = pd.DataFrame(columns=READINESS_COLUMNS)

    return FactorMatchingResult(
        candidate_matches=candidate_matches,
        activity_readiness=activity_readiness,
    )
