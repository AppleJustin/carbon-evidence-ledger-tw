"""Deterministic heating-value selection and kcal→TJ conversion.

Heating values are year-specific. A 114-year (ROC) annual heating value
applies only to calendar activity year 2025. Missing or conflicting rows
block calculation; the newest row is never chosen silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

HEATING_VALUE_COLUMNS = [
    "heating_value_id",
    "fuel_type",
    "fuel_subtype",
    "heating_value",
    "unit",
    "high_heating_value",
    "high_heating_value_unit",
    "factor_year",
    "geography",
    "authority",
    "valid_from",
    "valid_to",
    "source_reference_id",
    "source_locator",
    "snapshot_id",
    "snapshot_sha256",
    "snapshot_local_path",
    "status",
    "notes",
]

READY_HEATING_STATUS = "ready"
KCAL_UNIT = "kcal"
TJ_UNIT = "TJ"
NATURAL_GAS_HV_UNIT = "kcal/m3"
DIESEL_HV_UNIT = "kcal/L"

REQUIRED_READY_PROVENANCE_FIELDS = (
    "heating_value_id",
    "fuel_type",
    "heating_value",
    "unit",
    "factor_year",
    "geography",
    "authority",
    "source_reference_id",
    "source_locator",
    "snapshot_id",
    "status",
)

STATUS_READY = "ready"
STATUS_MISSING = "missing"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_INCOMPLETE_PROVENANCE = "incomplete_provenance"
STATUS_SUBTYPE_REQUIRED = "subtype_required"
STATUS_INVALID_SUBTYPE = "invalid_subtype"

NATURAL_GAS_SUBTYPES = frozenset({"NG1", "NG2"})
UNKNOWN_SUBTYPE_TOKENS = frozenset(
    {"", "UNKNOWN", "NOT_APPLICABLE", "NA", "N/A", "NONE"}
)


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


def _parse_timestamp(value: Any) -> pd.Timestamp | None:
    if _is_blank(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed)


def _validity_bound(value: Any) -> tuple[str, pd.Timestamp | None]:
    if _is_blank(value):
        return "blank", None
    stamp = _parse_timestamp(value)
    if stamp is None:
        return "malformed", None
    return "ok", stamp


def _heating_covers_activity_period(
    row: pd.Series,
    activity_start: Any,
    activity_end: Any,
    *,
    reporting_year: int | None = None,
) -> bool:
    from_kind, valid_from = _validity_bound(row.get("valid_from"))
    to_kind, valid_to = _validity_bound(row.get("valid_to"))
    if from_kind == "malformed" or to_kind == "malformed":
        return False
    start_kind, start = _validity_bound(activity_start)
    end_kind, end = _validity_bound(activity_end)
    if start_kind == "malformed" or end_kind == "malformed":
        return False
    if start is None:
        start = end
    if end is None:
        end = start
    if start is None or end is None:
        year = activity_calendar_year(activity_start, activity_end)
        if not year and reporting_year is not None:
            year = str(int(reporting_year))
        if not year:
            return valid_from is None and valid_to is None
        start = pd.Timestamp(int(year), 1, 1)
        end = pd.Timestamp(int(year), 12, 31)
    if valid_from is not None and valid_from > start:
        return False
    if valid_to is not None and valid_to < end:
        return False
    return True


def activity_calendar_year(activity_start: Any, activity_end: Any) -> str:
    """Return YYYY when start and end share one calendar year; else blank."""
    start = _parse_timestamp(activity_start)
    end = _parse_timestamp(activity_end)
    if start is None or end is None:
        return ""
    if int(start.year) != int(end.year):
        return ""
    return str(int(start.year))


def heating_value_has_complete_provenance(row: pd.Series) -> bool:
    """Ready heating values must carry official provenance, not just a number."""
    if _text(row.get("status")) != READY_HEATING_STATUS:
        return False
    for field in REQUIRED_READY_PROVENANCE_FIELDS:
        if _is_blank(row.get(field)):
            return False
    try:
        number = Decimal(str(row.get("heating_value")).strip())
    except (InvalidOperation, ValueError, TypeError):
        return False
    return number.is_finite() and number > 0


def empty_heating_values() -> pd.DataFrame:
    return pd.DataFrame(columns=HEATING_VALUE_COLUMNS)


def normalize_fuel_subtype(value: Any) -> str:
    """Return NG1/NG2, blank for unknown, or the raw token if invalid."""
    text = _text(value)
    if text.upper() in UNKNOWN_SUBTYPE_TOKENS:
        return ""
    if text.upper() in NATURAL_GAS_SUBTYPES:
        return text.upper()
    return text


def _row_fuel_subtype(row: pd.Series) -> str:
    if "fuel_subtype" not in row.index:
        return ""
    return _text(row.get("fuel_subtype")).upper()


def _apply_natural_gas_subtype_gate(
    matched: pd.DataFrame,
    fuel_subtype: Any,
    year: str,
) -> HeatingValueSelection | pd.DataFrame:
    """Require NG1/NG2 when subtype-specific official rows exist for the year."""
    subtype_mask = matched.apply(
        lambda row: _row_fuel_subtype(row) in NATURAL_GAS_SUBTYPES,
        axis=1,
    )
    if not bool(subtype_mask.any()):
        return matched

    requested = normalize_fuel_subtype(fuel_subtype)
    if requested == "":
        return HeatingValueSelection(
            status=STATUS_SUBTYPE_REQUIRED,
            reason=(
                "Natural-gas heating values for activity year "
                f"{year} are subtype-specific (NG1/NG2). The subtype is "
                "unknown and is not inferred."
            ),
        )
    if requested not in NATURAL_GAS_SUBTYPES:
        return HeatingValueSelection(
            status=STATUS_INVALID_SUBTYPE,
            reason=(
                f"Natural-gas subtype {requested!r} is not a valid official "
                "type. Expected NG1 or NG2."
            ),
        )
    filtered = matched.loc[
        matched["fuel_subtype"].astype(str).str.strip().str.upper() == requested
    ].copy()
    if filtered.empty:
        return HeatingValueSelection(
            status=STATUS_MISSING,
            reason=(
                f"No verified heating value for natural_gas subtype "
                f"{requested} in activity year {year}. A different subtype "
                "or year is not applied automatically."
            ),
        )
    return filtered


@dataclass(frozen=True)
class HeatingValueSelection:
    """Result of deterministic heating-value matching."""

    status: str
    reason: str
    row: pd.Series | None = None

    @property
    def heating_value_id(self) -> str:
        if self.row is None:
            return ""
        return _text(self.row.get("heating_value_id"))


def select_heating_value(
    heating_values: pd.DataFrame | None,
    *,
    fuel_type: str,
    activity_start: Any,
    activity_end: Any,
    geography: str = "TW",
    fuel_subtype: Any = "",
    reporting_year: int | None = None,
) -> HeatingValueSelection:
    """Select exactly one ready heating-value row for fuel + year + subtype.

    Natural-gas NG1/NG2 rows are not interchangeable. A generic or unknown
    natural-gas subtype is never inferred from company, region, or volume.
    """
    year = activity_calendar_year(activity_start, activity_end)
    if not year and reporting_year is not None:
        year = str(int(reporting_year))
    fuel = _text(fuel_type)
    if not year:
        return HeatingValueSelection(
            status=STATUS_MISSING,
            reason=(
                "Activity period must fall in a single calendar year before "
                "a year-specific heating value can be applied."
            ),
        )
    if heating_values is None or heating_values.empty:
        return HeatingValueSelection(
            status=STATUS_MISSING,
            reason=(
                f"No verified heating value is registered for {fuel!r} "
                f"in activity year {year}."
            ),
        )

    frame = heating_values.copy()
    if "fuel_type" not in frame.columns or "factor_year" not in frame.columns:
        return HeatingValueSelection(
            status=STATUS_MISSING,
            reason="Heating-value registry is missing required columns.",
        )

    mask = frame["fuel_type"].astype(str).str.strip() == fuel
    mask &= frame["factor_year"].astype(str).str.strip() == year
    if "status" in frame.columns:
        mask &= frame["status"].astype(str).str.strip() == READY_HEATING_STATUS
    if "geography" in frame.columns:
        geo = _text(geography) or "TW"
        mask &= frame["geography"].astype(str).str.strip().isin(
            {geo, "TW", "TW_reference"}
        )

    matched = frame.loc[mask].copy()
    if matched.empty:
        other_years = frame.loc[
            (frame["fuel_type"].astype(str).str.strip() == fuel)
            & (frame["status"].astype(str).str.strip() == READY_HEATING_STATUS)
        ]
        other = sorted(
            {
                _text(value)
                for value in other_years.get("factor_year", pd.Series(dtype=str))
                if not _is_blank(value)
            }
        )
        extra = (
            f" Ready heating-value years present: {', '.join(other)}."
            if other
            else ""
        )
        return HeatingValueSelection(
            status=STATUS_MISSING,
            reason=(
                f"No verified heating value for {fuel!r} in activity year "
                f"{year}.{extra} A different year's heating value is not "
                "applied automatically."
            ),
        )

    if fuel == "natural_gas":
        subtype_gate = _apply_natural_gas_subtype_gate(matched, fuel_subtype, year)
        if isinstance(subtype_gate, HeatingValueSelection):
            return subtype_gate
        matched = subtype_gate

    complete = [
        row
        for _, row in matched.iterrows()
        if heating_value_has_complete_provenance(row)
        and _heating_covers_activity_period(
            row,
            activity_start,
            activity_end,
            reporting_year=reporting_year,
        )
    ]
    incomplete_count = len(matched) - len(complete)
    if not complete:
        return HeatingValueSelection(
            status=STATUS_INCOMPLETE_PROVENANCE,
            reason=(
                f"Heating-value row(s) for {fuel!r} year {year} are not "
                "activated because official provenance is incomplete."
            ),
        )
    if len(complete) > 1:
        ids = ", ".join(_text(row.get("heating_value_id")) for row in complete)
        return HeatingValueSelection(
            status=STATUS_AMBIGUOUS,
            reason=(
                "Multiple conflicting ready heating values match "
                f"{fuel!r} year {year}: {ids}. Newest row is not selected."
            ),
        )
    if incomplete_count:
        return HeatingValueSelection(
            status=STATUS_AMBIGUOUS,
            reason=(
                f"Conflicting heating-value rows for {fuel!r} year {year} "
                "include provenance-incomplete records."
            ),
        )
    selected = complete[0]
    subtype_label = _row_fuel_subtype(selected)
    extra = f" subtype {subtype_label}" if subtype_label else ""
    return HeatingValueSelection(
        status=STATUS_READY,
        reason=(
            "Selected heating value "
            f"{_text(selected.get('heating_value_id'))} "
            f"for {fuel!r}{extra} year {year}."
        ),
        row=selected,
    )


def lookup_kcal_to_tj_conversion(
    engineering_conversions: pd.DataFrame | None,
) -> pd.Series | None:
    """Return the unique ready kcal→TJ physical conversion row."""
    if engineering_conversions is None or engineering_conversions.empty:
        return None
    frame = engineering_conversions.copy()
    required = {"source_unit", "target_unit", "multiplier", "status"}
    if not required.issubset(set(frame.columns)):
        return None
    mask = frame["source_unit"].astype(str).str.strip() == KCAL_UNIT
    mask &= frame["target_unit"].astype(str).str.strip() == TJ_UNIT
    mask &= frame["status"].astype(str).str.strip() == "ready"
    matched = frame.loc[mask]
    if len(matched) != 1:
        return None
    return matched.iloc[0]


def activity_energy_kcal(
    activity_value: Decimal,
    heating_row: pd.Series,
    activity_unit: str,
) -> Decimal | None:
    """activity × heating value, preserving the official heating-value unit."""
    hv_unit = _text(heating_row.get("unit"))
    expected_activity_unit = ""
    if hv_unit == NATURAL_GAS_HV_UNIT:
        expected_activity_unit = "m3"
    elif hv_unit == DIESEL_HV_UNIT:
        expected_activity_unit = "L"
    else:
        return None
    if _text(activity_unit) != expected_activity_unit:
        return None
    try:
        heating = Decimal(str(heating_row.get("heating_value")).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not heating.is_finite() or heating <= 0:
        return None
    return activity_value * heating


def kcal_to_tj(
    energy_kcal: Decimal,
    conversion_row: pd.Series,
) -> Decimal | None:
    """Convert kcal to TJ using the registered engineering multiplier."""
    try:
        multiplier = Decimal(str(conversion_row.get("multiplier")).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not multiplier.is_finite() or multiplier <= 0:
        return None
    return energy_kcal * multiplier
