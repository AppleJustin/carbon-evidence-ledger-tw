"""Convert pipeline DataFrames into user-facing display tables.

Source PipelineRunResult frames are never mutated. Display labels hide
internal status codes from primary UI surfaces and honor UI language.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from carbon_ledger.cfp_p_02 import redact_api_key_from_url
from carbon_ledger.pipeline import PipelineRunResult
from carbon_ledger.ui.i18n import DEFAULT_LANG, status_label, t

REPO_ROOT = Path(__file__).resolve().parents[3]

ACTIVITY_KEYS = {
    "grid_electricity": "activity.grid_electricity",
    "natural_gas": "activity.natural_gas",
    "diesel": "activity.diesel",
    "refrigerant_refill": "activity.refrigerant_refill",
    "refrigerant_actual_refill": "activity.refrigerant_refill",
    "purchased_steel": "activity.purchased_steel",
    "finished_goods_output": "activity.finished_goods_output",
    "third_party_transport": "activity.third_party_transport",
    "scrap_output": "activity.scrap_output",
    "other": "activity.other",
    "unknown": "activity.unknown",
}

CUSTOMER_SCHEMA_LABEL_KEYS = {
    "activity_type": "intake.field.activity_type",
    "activity_value": "intake.field.activity_value",
    "unit": "intake.field.unit",
    "activity_start_date": "intake.field.start",
    "activity_end_date": "intake.field.end",
    "site_id": "intake.field.site_id",
    "refrigerant_code": "intake.field.refrigerant_code",
    "refill_confirmed": "intake.field.refill_confirmed",
    "ownership_control": "intake.field.ownership_control",
    "organizational_boundary_status": (
        "intake.field.organizational_boundary_status"
    ),
    "calculation_method": "intake.field.calculation_method",
    "supplier_name": "intake.field.supplier_name",
    "steel_product_type": "intake.field.steel_product_type",
    "product_identifier": "intake.field.product_identifier",
    "emission_factor_value": "intake.field.emission_factor_value",
    "emission_factor_unit": "intake.field.emission_factor_unit",
    "factor_boundary": "intake.field.factor_boundary",
    "factor_geography": "intake.field.factor_geography",
    "factor_year": "intake.field.factor_year",
    "factor_source_id": "intake.field.factor_source_id",
    "evidence_reference": "intake.field.evidence_reference",
    "includes_pre_tier1_supply_chain_transport": (
        "intake.field.includes_pre_tier1_transport"
    ),
    "includes_tier1_to_reporting_company_transport": (
        "intake.field.includes_inbound_transport"
    ),
    "factor_includes_tier1_to_reporting_company_transport": (
        "intake.field.factor_includes_inbound_transport"
    ),
    "tier1_to_reporting_company_transport_control": (
        "intake.field.transport_control"
    ),
    "source_document_id": "intake.field.source_document_id",
}

_UNCONFIRMED_SITE_TOKENS = frozenset(
    {"", "unknown", "site_main", "n/a", "na", "none"}
)

CBAM_ROLE_KEYS = {
    "supporting_energy_evidence": "cbam.role.supporting_energy",
    "direct_emissions_activity_candidate": "cbam.role.direct_candidate",
    "outside_process_boundary": "cbam.role.outside",
    "possible_precursor_candidate": "cbam.role.precursor",
    "product_quantity_denominator_candidate": "cbam.role.product_qty",
}

ATTENTION_TITLE_KEYS = {
    "blocked_missing_conversion": "status.attention_blocked",
    "blocked_natural_gas_type_required": "status.attention_blocked",
    "no_factor_configured": "status.attention_factor",
    "no_matching_factor": "status.attention_factor",
    "blocked_missing_product_type": "status.attention_blocked",
    "blocked_ambiguous_factor": "status.attention_blocked",
}

ATTENTION_ACTION_KEYS = {
    "natural_gas": "dash.attention_gas_action",
    "diesel": "dash.attention_diesel_action",
    "purchased_steel": "dash.attention_steel_action",
}

GHG_RATIONALE_KEYS = {
    "refrigerant_third_party_unmapped": "ghg.rationale.refrigerant_third_party",
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def public_source_url(url: str) -> str:
    """Redact secrets and encode query values so the whole URL is one href."""
    return redact_api_key_from_url(_text(url))


def source_url_markdown(url: str) -> str:
    """Markdown link whose href keeps sort, desc, and format as one target."""
    href = public_source_url(url)
    if not href:
        return ""
    return f"[{href}]({href})"


def format_display_year(value: Any) -> str:
    """Format a year for display only. Source values are not mutated.

    Integer years such as ``2013.0`` render as ``2013``. Non-year numbers
    and non-numeric text are left unchanged.
    """
    text = _text(value)
    if not text:
        return ""
    try:
        number = float(text)
    except (TypeError, ValueError):
        return text
    if number.is_integer():
        year = int(number)
        if 1000 <= abs(year) <= 9999:
            return str(year)
    return text


def _format_scope3_tco2e(value: float) -> str:
    text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    return text or "0"


def _scope3_category_code(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    match = re.match(r"(category_\d+)", text.lower())
    return match.group(1) if match else text


def _scope3_category_label(code: str, lang: str) -> str:
    key = f"dash.scope3.category.{code}"
    label = t(key, lang)
    if label != key:
        return label
    match = re.match(r"category_(\d+)$", code)
    if match:
        return f"Category {match.group(1)}"
    return code


def _scope3_category_sort_key(code: str) -> tuple[int, int | str]:
    match = re.match(r"category_(\d+)$", code)
    if match:
        return (0, int(match.group(1)))
    return (1, code)


def not_run_label(lang: str = DEFAULT_LANG) -> str:
    """Return the disabled-adapter label."""
    return t("common.not_run", lang)


def customer_schema_label(field: str, lang: str = DEFAULT_LANG) -> str:
    """Presentation-only label for a backend schema field name."""
    key = CUSTOMER_SCHEMA_LABEL_KEYS.get(str(field or "").strip())
    return t(key, lang) if key else str(field or "")


def customer_site_display(value: Any, lang: str = DEFAULT_LANG) -> str:
    """Human location name; unknown/internal tokens need confirmation."""
    text = _text(value)
    if text.casefold() in _UNCONFIRMED_SITE_TOKENS:
        return t("intake.site_unconfirmed", lang)
    return text


def activity_display_name(
    activity_type: str,
    lang: str = DEFAULT_LANG,
) -> str:
    """Return a human-readable activity name."""
    key = _text(activity_type)
    msg_key = ACTIVITY_KEYS.get(key)
    if msg_key:
        return t(msg_key, lang)
    return key.replace("_", " ").title() or "Activity"


def calculation_label(status: str, lang: str = DEFAULT_LANG) -> str:
    """Return the primary user-facing calculation label."""
    return status_label(status, lang)


def calculation_explanation(
    status: str,
    lang: str = DEFAULT_LANG,
    *,
    activity_type: str = "",
) -> str:
    """Return a short explanation for a calculation status."""
    key = _text(status)
    if _text(activity_type) == "purchased_steel":
        steel_key = f"explain.steel.{key}"
        labeled = t(steel_key, lang)
        if labeled != steel_key:
            return labeled
    msg = f"explain.{key}"
    if msg in {
        "explain.calculated",
        "explain.blocked_missing_conversion",
        "explain.blocked_natural_gas_type_required",
        "explain.no_factor_configured",
        "explain.no_matching_factor",
        "explain.not_emissions_activity",
    }:
        return t(msg, lang)
    known = t(msg, lang)
    if known != msg:
        return known
    return t("explain.no_factor_configured", lang)


def calculation_next_action(status: str, lang: str = DEFAULT_LANG) -> str:
    """Return the recommended next action for a calculation status."""
    key = _text(status)
    msg = f"next.{key}"
    known = {
        "next.calculated",
        "next.blocked_missing_conversion",
        "next.blocked_natural_gas_type_required",
        "next.no_factor_configured",
        "next.no_matching_factor",
        "next.not_emissions_activity",
    }
    if msg in known:
        return t(msg, lang)
    return t("next.no_factor_configured", lang)


def status_presentation(code: str, lang: str = DEFAULT_LANG) -> dict[str, str]:
    """Return label, explanation, and next action for a technical status code."""
    key = _text(code)
    return {
        "code": key,
        "label": calculation_label(key, lang),
        "explanation": calculation_explanation(key, lang),
        "next_action": calculation_next_action(key, lang),
    }


def ghg_rationale_display(
    ghg_row: pd.Series | None,
    lang: str = DEFAULT_LANG,
) -> str:
    """Customer-facing GHG rationale via i18n. Never hard-code language here."""
    if ghg_row is None:
        return ""
    mapping_code = _text(ghg_row.get("mapping_code"))
    key = GHG_RATIONALE_KEYS.get(mapping_code)
    if key:
        return t(key, lang)
    return _text(ghg_row.get("rationale"))


def ghg_display_label(
    ghg_row: pd.Series | None,
    lang: str = DEFAULT_LANG,
) -> str:
    """Build a GHG Protocol label from an evaluation row."""
    if ghg_row is None:
        return not_run_label(lang)
    mapping_status = _text(ghg_row.get("mapping_status"))
    if mapping_status == "outside_boundary":
        return t("status.outside_boundary", lang)
    if mapping_status == "needs_review":
        return t("status.needs_review", lang)
    scope = _text(ghg_row.get("ghg_scope"))
    category = _text(ghg_row.get("scope3_category"))
    if scope == "scope_3" and "category_1" in category:
        return t("ghg.scope_3_cat1", lang)
    if scope == "scope_1":
        return t("ghg.scope_1", lang)
    if scope == "scope_2":
        return t("ghg.scope_2", lang)
    if scope == "scope_3":
        return t("ghg.scope_3", lang)
    if scope == "not_applicable" or _text(ghg_row.get("mapping_status")) == (
        "not_applicable"
    ):
        return t("status.not_applicable", lang)
    return scope.replace("_", " ").title() or not_run_label(lang)


def cbam_display_label(
    cbam_row: pd.Series | None,
    *,
    enabled: bool,
    lang: str = DEFAULT_LANG,
) -> str:
    """Build a CBAM role label from an evaluation row."""
    if not enabled or cbam_row is None:
        return not_run_label(lang)
    role = _text(cbam_row.get("data_role"))
    role_key = CBAM_ROLE_KEYS.get(role)
    if role_key:
        return t(role_key, lang)
    status = _text(cbam_row.get("mapping_status"))
    return status_label(status, lang)


def ifrs_display_label(
    ifrs_row: pd.Series | None,
    *,
    enabled: bool,
    lang: str = DEFAULT_LANG,
) -> str:
    """Build an IFRS S2 readiness label from an evaluation row."""
    if not enabled or ifrs_row is None:
        return not_run_label(lang)
    readiness = _text(ifrs_row.get("readiness_status"))
    return status_label(readiness, lang)


def qa_display_label(
    issues: pd.DataFrame,
    record_id: str,
    lang: str = DEFAULT_LANG,
) -> str:
    """Summarize open QA attention for one activity."""
    if issues.empty:
        return t("status.no_open_issue", lang)
    matched = issues[issues["record_id"].astype(str) == record_id]
    if matched.empty:
        return t("status.no_open_issue", lang)
    severity = _text(matched.iloc[0].get("severity"))
    return t(f"severity.{severity}", lang) if severity else t(
        "status.no_open_issue", lang
    )


def _row_by_record(frame: pd.DataFrame, record_id: str) -> pd.Series | None:
    if frame is None or frame.empty or "record_id" not in frame.columns:
        return None
    matched = frame[frame["record_id"].astype(str) == record_id]
    if matched.empty:
        return None
    return matched.iloc[0]


def build_activity_overview(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Build a unified activity overview without mutating source frames."""
    activities = result.activity_records_accepted.copy()
    calculations = result.calculation_results.copy()
    ghg = result.ghg_evaluations.copy()
    cbam = result.cbam_evaluations.copy()
    ifrs = result.ifrs_s2_evaluations.copy()
    issues = result.core_qa_issues.copy()
    idle = not_run_label(lang)

    rows: list[dict[str, Any]] = []
    for _, activity in activities.iterrows():
        record_id = _text(activity.get("record_id"))
        activity_type = _text(activity.get("activity_type"))
        calc_row = _row_by_record(calculations, record_id)
        calc_status = (
            _text(calc_row.get("calculation_status")) if calc_row is not None else ""
        )
        calculated_tco2e = None
        if calc_row is not None and calc_status == "calculated":
            value = calc_row.get("calculated_tco2e")
            try:
                if value is not None and not pd.isna(value):
                    calculated_tco2e = float(value)
            except (TypeError, ValueError):
                calculated_tco2e = None

        attention = False
        if not issues.empty and "record_id" in issues.columns:
            attention = bool((issues["record_id"].astype(str) == record_id).any())

        amount = activity.get("activity_value")
        try:
            amount_value = (
                float(amount) if amount is not None and not pd.isna(amount) else None
            )
        except (TypeError, ValueError):
            amount_value = None

        rows.append(
            {
                "record_id": record_id,
                "activity_name": activity_display_name(activity_type, lang),
                "activity_type": activity_type,
                "activity_amount": amount_value,
                "activity_unit": _text(activity.get("unit")),
                "refrigerant_code": _text(activity.get("refrigerant_code"))
                or (
                    _text(calc_row.get("refrigerant_code"))
                    if calc_row is not None
                    else ""
                ),
                "gwp_value": (
                    calc_row.get("gwp_value") if calc_row is not None else None
                ),
                "calculation_status": calc_status,
                "calculation_label": calculation_label(calc_status, lang),
                "calculation_explanation": calculation_explanation(
                    calc_status,
                    lang,
                    activity_type=activity_type,
                ),
                "calculated_tco2e": calculated_tco2e,
                "ghg_label": (
                    ghg_display_label(_row_by_record(ghg, record_id), lang)
                    if result.include_ghg
                    else idle
                ),
                "cbam_label": cbam_display_label(
                    _row_by_record(cbam, record_id),
                    enabled=result.include_cbam,
                    lang=lang,
                ),
                "ifrs_s2_label": ifrs_display_label(
                    _row_by_record(ifrs, record_id),
                    enabled=result.include_ifrs_s2,
                    lang=lang,
                ),
                "qa_label": qa_display_label(issues, record_id, lang),
                "attention_required": attention,
                "source_document_id": _text(activity.get("source_document_id")),
            }
        )
    return pd.DataFrame(rows)


def dashboard_kpi_counts(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> dict[str, int]:
    """Compute dashboard KPI values from the current result."""
    overview = build_activity_overview(result, lang)
    calculated = 0
    if not overview.empty:
        calculated = int(
            (overview["calculation_status"].astype(str) == "calculated").sum()
        )
    return {
        "activities": int(len(result.activity_records_accepted)),
        "calculated": calculated,
        "open_qa_issues": int(len(result.core_qa_issues)),
        "source_documents": int(len(result.source_documents_accepted)),
    }


def calculated_emissions_summary(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> dict[str, Any]:
    """Summarize technically calculated emissions, including excluded rows.

    This is an audit/detail total. It is not the company inventory total.
    """
    calculations = result.calculation_results.copy()
    empty = {
        "calculated_tco2e": None,
        "calculated_row_count": 0,
        "partial": True,
        "label": t("common.partial_result", lang),
    }
    if calculations.empty or "calculation_status" not in calculations.columns:
        return empty
    calculated = calculations[
        calculations["calculation_status"].astype(str) == "calculated"
    ].copy()
    if calculated.empty:
        return empty
    numeric = pd.to_numeric(calculated["calculated_tco2e"], errors="coerce")
    return {
        "calculated_tco2e": float(numeric.fillna(0).sum()),
        "calculated_row_count": int(len(calculated)),
        "partial": True,
        "label": t("common.partial_result", lang),
    }


def _company_inventory_rows(result: PipelineRunResult) -> pd.DataFrame:
    """Calculated rows that are mapped Scope 1 or Scope 2 inside the inventory."""
    calculations = result.calculation_results.copy()
    ghg = result.ghg_evaluations.copy()
    empty = pd.DataFrame(columns=["record_id", "ghg_scope", "calculated_tco2e"])
    if calculations.empty or ghg.empty:
        return empty
    calculated = calculations[
        calculations["calculation_status"].astype(str) == "calculated"
    ].copy()
    if calculated.empty:
        return empty
    keep = ["record_id"]
    if "ghg_scope" in ghg.columns:
        keep.append("ghg_scope")
    if "mapping_status" in ghg.columns:
        keep.append("mapping_status")
    overlap = [
        column
        for column in keep
        if column != "record_id" and column in calculated.columns
    ]
    if overlap:
        calculated = calculated.drop(columns=overlap)
    merged = calculated.merge(ghg[keep], on="record_id", how="left")
    merged["calculated_tco2e"] = pd.to_numeric(
        merged["calculated_tco2e"], errors="coerce"
    )
    merged = merged.dropna(subset=["calculated_tco2e"])
    mapped = merged[
        (merged["mapping_status"].astype(str) == "mapped")
        & (merged["ghg_scope"].astype(str).isin(["scope_1", "scope_2"]))
    ].copy()
    if mapped.empty:
        return empty
    return mapped[["record_id", "ghg_scope", "calculated_tco2e"]].reset_index(
        drop=True
    )


def inventory_source_shares(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> list[dict[str, Any]]:
    """Share of company-inventory tCO2e by activity name. Dynamic, never hardcoded."""
    summary = company_inventory_emissions_summary(result, lang)
    total = float(summary.get("inventory_tco2e") or 0.0)
    if total <= 0:
        return []
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return []
    included_ids = set(_company_inventory_rows(result)["record_id"].astype(str))
    calculated = overview[
        overview["record_id"].astype(str).isin(included_ids)
    ].copy()
    if calculated.empty:
        return []
    calculated["tco2e"] = pd.to_numeric(
        calculated["calculated_tco2e"], errors="coerce"
    )
    grouped = (
        calculated.dropna(subset=["tco2e"])
        .groupby("activity_name", dropna=False)["tco2e"]
        .sum()
        .sort_values(ascending=False)
    )
    rows: list[dict[str, Any]] = []
    for name, value in grouped.items():
        amount = float(value or 0.0)
        rows.append(
            {
                "activity_name": str(name or ""),
                "tco2e": amount,
                "percent": round(100.0 * amount / total, 2),
            }
        )
    return rows


def company_inventory_record_ids(result: PipelineRunResult) -> set[str]:
    """Record IDs currently included in the company inventory total."""
    rows = _company_inventory_rows(result)
    if rows.empty:
        return set()
    return set(rows["record_id"].astype(str).tolist())


def company_inventory_emissions_summary(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> dict[str, Any]:
    """Company inventory total: mapped Scope 1 + mapped Scope 2 only."""
    rows = _company_inventory_rows(result)
    empty = {
        "inventory_tco2e": None,
        "inventory_row_count": 0,
        "scope_1": 0.0,
        "scope_2": 0.0,
        "partial": True,
        "label": t("dash.kpi.inventory", lang),
    }
    if rows.empty:
        return empty
    scope_1 = float(
        rows.loc[rows["ghg_scope"].astype(str) == "scope_1", "calculated_tco2e"].sum()
    )
    scope_2 = float(
        rows.loc[rows["ghg_scope"].astype(str) == "scope_2", "calculated_tco2e"].sum()
    )
    return {
        "inventory_tco2e": float(scope_1 + scope_2),
        "inventory_row_count": int(len(rows)),
        "scope_1": scope_1,
        "scope_2": scope_2,
        "partial": True,
        "label": t("dash.kpi.inventory", lang),
    }


def _scope3_category1_rows(result: PipelineRunResult) -> pd.DataFrame:
    """Calculated Scope 3 Category 1 rows from official output fields.

    Category 1 is never inferred from activity type. Rows missing
    ``ghg_scope`` or ``scope_3_category``, or whose values are not exactly
    ``scope_3`` / ``category_1``, are excluded.
    """
    calculations = result.calculation_results.copy()
    empty = pd.DataFrame()
    if calculations.empty:
        return empty
    if "ghg_scope" not in calculations.columns:
        return empty
    if "scope_3_category" not in calculations.columns:
        return empty
    calculated = calculations[
        calculations["calculation_status"].astype(str) == "calculated"
    ].copy()
    if calculated.empty:
        return empty
    scope = calculated["ghg_scope"].map(_text)
    category = calculated["scope_3_category"].map(_text)
    selected = calculated[
        (scope == "scope_3") & (category == "category_1")
    ].copy()
    if selected.empty:
        return empty
    selected["calculated_tco2e"] = pd.to_numeric(
        selected["calculated_tco2e"], errors="coerce"
    )
    selected = selected.dropna(subset=["calculated_tco2e"])
    return selected.reset_index(drop=True)


def scope3_category1_emissions_summary(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> dict[str, Any]:
    """Independent Scope 3 Category 1 subtotal. Never added to Scope 1+2."""
    rows = _scope3_category1_rows(result)
    empty = {
        "tco2e": None,
        "row_count": 0,
        "label": t("dash.scope3_cat1.title", lang),
        "not_in_inventory": t("dash.scope3_cat1.not_in_inventory", lang),
        "rows": [],
    }
    if rows.empty:
        return empty
    detail: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        factor_year = format_display_year(row.get("factor_year"))
        reporting_year = format_display_year(row.get("reporting_year"))
        announcement_year = format_display_year(row.get("announcement_year"))
        temporal_warning = False
        try:
            if factor_year and reporting_year:
                temporal_warning = int(factor_year) < int(reporting_year)
        except (TypeError, ValueError):
            temporal_warning = False
        detail.append(
            {
                "record_id": _text(row.get("record_id")),
                "tco2e": float(row["calculated_tco2e"]),
                "calculation_method": _text(row.get("calculation_method")),
                "supplier_name": _text(row.get("supplier_name")),
                "steel_product_type": _text(row.get("steel_product_type"))
                or _text(row.get("product_identifier")),
                "official_name": _text(row.get("official_name"))
                or _text(row.get("steel_product_type")),
                "factor_value": row.get("factor_value"),
                "factor_unit": (
                    f"{_text(row.get('factor_numerator_unit'))}/"
                    f"{_text(row.get('factor_denominator_unit'))}"
                    if _text(row.get("factor_numerator_unit"))
                    and _text(row.get("factor_denominator_unit"))
                    else ""
                ),
                "publisher": _text(row.get("publisher")),
                "announcement_year": announcement_year,
                "retrieved_at": _text(row.get("retrieved_at")),
                "factor_year": factor_year,
                "reporting_year": reporting_year,
                "factor_id": _text(row.get("factor_id")),
                "factor_version": _text(row.get("factor_version")),
                "factor_source_id": _text(row.get("factor_source_id")),
                "source_record_id": _text(row.get("source_record_id")),
                "source_url": public_source_url(row.get("source_url")),
                "snapshot_hash": _text(row.get("snapshot_hash")),
                "match_reason": _text(row.get("match_reason")),
                "evidence_reference": _text(row.get("evidence_reference")),
                "factor_boundary": _text(row.get("factor_boundary")),
                "factor_geography": _text(row.get("factor_geography")),
                "temporal_warning": temporal_warning,
                "status_label": t("dash.scope3_cat1.estimated", lang),
            }
        )
    return {
        "tco2e": float(rows["calculated_tco2e"].sum()),
        "row_count": int(len(rows)),
        "label": t("dash.scope3_cat1.title", lang),
        "not_in_inventory": t("dash.scope3_cat1.not_in_inventory", lang),
        "rows": detail,
    }


def _qualifying_scope3_rows(result: PipelineRunResult) -> pd.DataFrame:
    """Calculated, mapped Scope 3 rows that have an explicit category.

    Scope is never inferred from ``activity_type``. Blocked, needs-review,
    outside-boundary, not-applicable, no-matching-factor, and missing rows
    are excluded. These rows are never added to the Scope 1 + Scope 2
    company inventory.
    """
    calculations = result.calculation_results.copy()
    ghg = result.ghg_evaluations.copy()
    empty = pd.DataFrame()
    if calculations.empty or ghg.empty:
        return empty
    if "mapping_status" not in ghg.columns or "ghg_scope" not in ghg.columns:
        return empty
    calculated = calculations[
        calculations["calculation_status"].astype(str) == "calculated"
    ].copy()
    if calculated.empty:
        return empty
    keep = ["record_id", "mapping_status", "ghg_scope"]
    overlap = [
        column
        for column in ("mapping_status", "ghg_scope")
        if column in calculated.columns
    ]
    left = calculated.drop(columns=overlap) if overlap else calculated
    merged = left.merge(ghg[keep], on="record_id", how="left")
    merged["calculated_tco2e"] = pd.to_numeric(
        merged["calculated_tco2e"], errors="coerce"
    )
    merged = merged.dropna(subset=["calculated_tco2e"])
    if merged.empty:
        return empty
    ghg_category: dict[str, str] = {}
    for _, grow in ghg.iterrows():
        record_id = _text(grow.get("record_id"))
        category = _text(grow.get("scope_3_category")) or _text(
            grow.get("scope3_category")
        )
        if record_id and category and record_id not in ghg_category:
            ghg_category[record_id] = category

    def _row_category(row: pd.Series) -> str:
        category = _text(row.get("scope_3_category")) or _text(
            row.get("scope3_category")
        )
        if category:
            return category
        return ghg_category.get(_text(row.get("record_id")), "")

    merged["_scope3_category"] = merged.apply(_row_category, axis=1)
    selected = merged[
        (merged["mapping_status"].astype(str) == "mapped")
        & (merged["ghg_scope"].astype(str) == "scope_3")
        & (merged["_scope3_category"].map(_text) != "")
    ].copy()
    if selected.empty:
        return empty
    return selected.reset_index(drop=True)


def scope3_emissions_summary(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> dict[str, Any]:
    """Independent Scope 3 card total. Never added to Scope 1 + Scope 2."""
    rows = _qualifying_scope3_rows(result)
    empty = {
        "tco2e": None,
        "row_count": 0,
        "categories": [],
        "category_labels": [],
        "caption": t("dash.scope3.empty", lang),
        "partial": True,
    }
    if rows.empty:
        return empty
    codes: list[str] = []
    seen: set[str] = set()
    for raw in rows["_scope3_category"].tolist():
        code = _scope3_category_code(raw)
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)
    codes.sort(key=_scope3_category_sort_key)
    labels = [_scope3_category_label(code, lang) for code in codes]
    total = float(rows["calculated_tco2e"].sum())
    value_text = _format_scope3_tco2e(total)
    return {
        "tco2e": total,
        "row_count": int(len(rows)),
        "categories": codes,
        "category_labels": labels,
        "caption": t(
            "dash.scope3.partial",
            lang,
            value=value_text,
            categories="、".join(labels),
        ),
        "partial": True,
    }


def inventory_status_counts(result: PipelineRunResult) -> dict[str, int]:
    """Split technical calculation from inventory inclusion."""
    calculations = result.calculation_results.copy()
    ghg = result.ghg_evaluations.copy()
    counts = {
        "technically_calculated": 0,
        "included_in_inventory": 0,
        "needs_review": 0,
        "outside_boundary": 0,
        "activities": int(len(result.activity_records_accepted)),
    }
    if calculations.empty:
        return counts
    status = calculations["calculation_status"].astype(str)
    counts["technically_calculated"] = int((status == "calculated").sum())
    if ghg.empty:
        return counts
    keep = ["record_id"]
    if "mapping_status" in ghg.columns:
        keep.append("mapping_status")
    if "ghg_scope" in ghg.columns:
        keep.append("ghg_scope")
    overlap = [
        column
        for column in keep
        if column != "record_id" and column in calculations.columns
    ]
    left = calculations
    if overlap:
        left = calculations.drop(columns=overlap)
    merged = left.merge(ghg[keep], on="record_id", how="left")
    mapping = merged["mapping_status"].astype(str)
    scope = merged["ghg_scope"].astype(str)
    calc_ok = merged["calculation_status"].astype(str) == "calculated"
    counts["included_in_inventory"] = int(
        (
            calc_ok
            & (mapping == "mapped")
            & scope.isin(["scope_1", "scope_2"])
        ).sum()
    )
    counts["needs_review"] = int((mapping == "needs_review").sum())
    counts["outside_boundary"] = int((mapping == "outside_boundary").sum())
    return counts


def pending_refrigerant_boundary_rows(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> list[dict[str, Any]]:
    """Refrigerant refill rows whose GHG mapping still needs human confirmation."""
    from carbon_ledger.activity_boundary_decisions import reporting_year_from_activity

    activities = result.activity_records_accepted.copy()
    calculations = result.calculation_results.copy()
    ghg = result.ghg_evaluations.copy()
    if activities.empty or ghg.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, activity in activities.iterrows():
        if _text(activity.get("activity_type")) != "refrigerant_refill":
            continue
        record_id = _text(activity.get("record_id"))
        ghg_row = _row_by_record(ghg, record_id)
        if ghg_row is None:
            continue
        if _text(ghg_row.get("mapping_status")) != "needs_review":
            continue
        calc_row = _row_by_record(calculations, record_id)
        tco2e = None
        calc_status = ""
        if calc_row is not None:
            calc_status = _text(calc_row.get("calculation_status"))
            if calc_status == "calculated":
                try:
                    value = calc_row.get("calculated_tco2e")
                    if value is not None and not pd.isna(value):
                        tco2e = float(value)
                except (TypeError, ValueError):
                    tco2e = None
        rows.append(
            {
                "record_id": record_id,
                "refrigerant_code": _text(activity.get("refrigerant_code")),
                "activity_value": activity.get("activity_value"),
                "unit": _text(activity.get("unit")) or "kg",
                "calculated_tco2e": tco2e,
                "calculation_status": calc_status,
                "mapping_status": _text(ghg_row.get("mapping_status")),
                "ghg_scope": _text(ghg_row.get("ghg_scope")),
                "ghg_label": ghg_display_label(ghg_row, lang),
                "rationale": ghg_rationale_display(ghg_row, lang),
                "ownership_control": _text(activity.get("ownership_control")),
                "organizational_boundary_status": _text(
                    activity.get("organizational_boundary_status")
                ),
                "reporting_year": reporting_year_from_activity(activity),
                "reporting_period_id": _text(activity.get("reporting_period_id")),
            }
        )
    return rows


def calculated_emissions_by_ghg_scope(
    result: PipelineRunResult,
) -> dict[str, float]:
    """Sum calculated tCO2e by GHG scope. Blocked rows are excluded."""
    calculations = result.calculation_results.copy()
    ghg = result.ghg_evaluations.copy()
    totals: dict[str, float] = {}
    if calculations.empty or ghg.empty:
        return totals
    calculated = calculations[
        calculations["calculation_status"].astype(str) == "calculated"
    ].copy()
    if calculated.empty:
        return totals
    ghg_right = ghg[["record_id", "ghg_scope"]].copy()
    if "ghg_scope" in calculated.columns:
        calculated = calculated.drop(columns=["ghg_scope"])
    merged = calculated.merge(
        ghg_right,
        on="record_id",
        how="left",
    )
    merged["calculated_tco2e"] = pd.to_numeric(
        merged["calculated_tco2e"], errors="coerce"
    )
    merged = merged.dropna(subset=["calculated_tco2e"])
    for scope, group in merged.groupby(merged["ghg_scope"].astype(str)):
        totals[str(scope)] = float(group["calculated_tco2e"].sum())
    return totals


def calculated_emissions_by_product_scope(
    result: PipelineRunResult,
) -> dict[str, float | None]:
    """Customer Scope totals for the company inventory.

    Only mapped Scope 1 and Scope 2 enter the total. Activity-type fallback
    is not used, so refrigerant and other unmapped rows cannot be silently
    included. Scope 3 is omitted from this inventory total.
    """
    rows = _company_inventory_rows(result)
    totals: dict[str, float | None] = {"scope_1": 0.0, "scope_2": 0.0}
    if rows.empty:
        return totals
    for scope in ("scope_1", "scope_2"):
        totals[scope] = float(
            rows.loc[rows["ghg_scope"].astype(str) == scope, "calculated_tco2e"].sum()
        )
    return totals


def should_show_coverage_chart(calculated: int, total: int) -> bool:
    """Show compact coverage only when calculation is partial, never at 100%."""
    return 0 < int(calculated) < int(total)


def should_show_unresolved_cta(unresolved: int) -> bool:
    """Issue CTAs exist only when the customer has something to fix."""
    return int(unresolved) > 0


def executive_emissions_insights(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> list[str]:
    """At most two deterministic sentences. Source share first. No LLM."""
    summary = company_inventory_emissions_summary(result, lang)
    total = float(summary.get("inventory_tco2e") or 0.0)
    if total <= 0:
        return []
    scopes = calculated_emissions_by_product_scope(result)
    scope_1 = float(scopes.get("scope_1") or 0.0)
    scope_2 = float(scopes.get("scope_2") or 0.0)
    leading_scope = "Scope 1" if scope_1 >= scope_2 else "Scope 2"
    leading_value = max(scope_1, scope_2)
    leading_share = leading_value / total
    overview = build_activity_overview(result, lang)
    top_name = ""
    top_value = 0.0
    if not overview.empty:
        included_ids = set(_company_inventory_rows(result)["record_id"].astype(str))
        calculated = overview[
            overview["record_id"].astype(str).isin(included_ids)
        ].copy()
        if not calculated.empty:
            calculated["tco2e"] = pd.to_numeric(
                calculated["calculated_tco2e"], errors="coerce"
            )
            grouped = (
                calculated.dropna(subset=["tco2e"])
                .groupby("activity_name", dropna=False)["tco2e"]
                .sum()
                .sort_values(ascending=False)
            )
            if not grouped.empty:
                top_name = str(grouped.index[0] or "")
                top_value = float(grouped.iloc[0] or 0.0)
    items: list[str] = []
    if top_name and top_value > 0:
        percent = round(100.0 * top_value / total, 2)
        items.append(
            t(
                "dash.insight.top_source_share",
                lang,
                name=top_name,
                percent=percent,
            )
        )
    elif top_name:
        items.append(t("dash.insight.top_source", lang, name=top_name))
    if 0.5 <= leading_share < 0.95:
        percent = int(round(100.0 * leading_share))
        items.append(
            t(
                "dash.insight.top_scope",
                lang,
                scope=leading_scope,
                percent=percent,
            )
        )
    elif not items and leading_value > 0:
        percent = int(round(100.0 * leading_share))
        items.append(
            t(
                "dash.insight.top_scope",
                lang,
                scope=leading_scope,
                percent=percent,
            )
        )
    return items[:2]


def executive_emissions_insight(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> str:
    """Primary deterministic insight. No LLM."""
    items = executive_emissions_insights(result, lang)
    return items[0] if items else ""


def scope_kpi_states(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> dict[str, dict[str, Any]]:
    """Distinguish calculated Scope totals from unresolved / empty Scope 3."""
    totals = calculated_emissions_by_product_scope(result)
    calculated_present = {"scope_1": False, "scope_2": False}
    inventory = _company_inventory_rows(result)
    if not inventory.empty:
        for scope in inventory["ghg_scope"].astype(str).tolist():
            if scope in calculated_present:
                calculated_present[scope] = True
    states: dict[str, dict[str, Any]] = {}
    for key in ("scope_1", "scope_2"):
        if calculated_present[key]:
            states[key] = {
                "state": "calculated",
                "value": float(totals.get(key) or 0.0),
            }
        else:
            states[key] = {"state": "pending", "value": None}
    scope3 = scope3_emissions_summary(result, lang)
    if scope3["row_count"] > 0 and scope3.get("tco2e") is not None:
        states["scope_3"] = {
            "state": "calculated",
            "value": float(scope3["tco2e"]),
            "caption": scope3["caption"],
            "categories": list(scope3["categories"]),
        }
    else:
        states["scope_3"] = {
            "state": "empty",
            "value": None,
            "caption": scope3["caption"],
            "categories": [],
        }
    return states


def attention_issue_cards(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> list[dict[str, str]]:
    """Build short dashboard attention cards from core QA issues."""
    issues = result.core_qa_issues.copy()
    activities = result.activity_records_accepted.copy()
    if issues.empty:
        return []

    type_by_record = {
        _text(row.get("record_id")): _text(row.get("activity_type"))
        for _, row in activities.iterrows()
    }
    cards: list[dict[str, str]] = []
    for _, issue in issues.iterrows():
        record_id = _text(issue.get("record_id"))
        activity_type = type_by_record.get(record_id, "")
        source_status = _text(issue.get("source_status"))
        title_key = ATTENTION_TITLE_KEYS.get(source_status)
        title = (
            t(title_key, lang)
            if title_key
            else calculation_label(source_status, lang)
        )
        action_key = ATTENTION_ACTION_KEYS.get(activity_type)
        action_hint = (
            t(action_key, lang)
            if action_key
            else calculation_next_action(source_status, lang)
        )
        severity_code = _text(issue.get("severity"))
        cards.append(
            {
                "record_id": record_id,
                "activity_name": activity_display_name(activity_type, lang),
                "activity_type": activity_type,
                "severity": t(f"severity.{severity_code}", lang),
                "title": title,
                "action_hint": action_hint,
                "reason": _text(issue.get("issue_summary")),
                "recommended_action": _text(issue.get("recommended_action")),
                "issue_id": _text(issue.get("issue_id")),
            }
        )
    return cards


def framework_coverage_cards(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> list[dict[str, Any]]:
    """Build compact framework coverage summaries."""
    return [
        {
            "name": "GHG Protocol",
            "enabled": bool(result.include_ghg),
            "row_count": (
                int(len(result.ghg_evaluations)) if result.include_ghg else 0
            ),
            "purpose": t("fw.purpose_ghg", lang),
        },
        {
            "name": "EU CBAM",
            "enabled": bool(result.include_cbam),
            "row_count": (
                int(len(result.cbam_evaluations)) if result.include_cbam else 0
            ),
            "purpose": t("fw.purpose_cbam", lang),
        },
        {
            "name": "IFRS S2",
            "enabled": bool(result.include_ifrs_s2),
            "row_count": (
                int(len(result.ifrs_s2_evaluations))
                if result.include_ifrs_s2
                else 0
            ),
            "purpose": t("fw.purpose_ifrs", lang),
        },
    ]


def issues_table(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Build the Issues & Actions display table."""
    issues = result.core_qa_issues.copy()
    activities = result.activity_records_accepted.copy()
    documents = result.source_documents_accepted.copy()
    columns = [
        "Priority",
        "Activity",
        "Issue",
        "Why it matters",
        "Recommended action",
        "record_id",
        "issue_id",
        "severity_code",
        "issue_code",
        "allowed_use",
        "prohibited_use",
        "source_document_id",
        "document_label",
        "period_label",
    ]
    if issues.empty:
        return pd.DataFrame(columns=columns)

    name_by_record = {
        _text(row.get("record_id")): activity_display_name(
            _text(row.get("activity_type")), lang
        )
        for _, row in activities.iterrows()
    }
    period_by_record = {
        _text(row.get("record_id")): (
            f"{_text(row.get('activity_start_date'))[:7]}"
            if _text(row.get("activity_start_date"))
            else "—"
        )
        for _, row in activities.iterrows()
    }
    doc_name_by_id = {
        _text(row.get("source_document_id")): (
            _text(row.get("file_name")) or _text(row.get("issuer")) or "—"
        )
        for _, row in documents.iterrows()
    }
    rows: list[dict[str, Any]] = []
    for _, issue in issues.iterrows():
        record_id = _text(issue.get("record_id"))
        severity_code = _text(issue.get("severity"))
        doc_id = _text(issue.get("source_document_id"))
        if not doc_id and not activities.empty:
            act = activities[activities["record_id"].astype(str) == record_id]
            if not act.empty:
                doc_id = _text(act.iloc[0].get("source_document_id"))
        rows.append(
            {
                "Priority": t(f"severity.{severity_code}", lang),
                "Activity": name_by_record.get(record_id, record_id or "—"),
                "Issue": _text(issue.get("issue_summary")),
                "Why it matters": _text(issue.get("source_reason"))
                or _text(issue.get("issue_summary")),
                "Recommended action": _text(issue.get("recommended_action")),
                "record_id": record_id,
                "issue_id": _text(issue.get("issue_id")),
                "severity_code": severity_code,
                "issue_code": _text(issue.get("issue_code")),
                "allowed_use": _text(issue.get("allowed_use")),
                "prohibited_use": _text(issue.get("prohibited_use")),
                "source_document_id": doc_id,
                "document_label": doc_name_by_id.get(doc_id, "—"),
                "period_label": period_by_record.get(record_id, "—"),
                "blocking_dependency": _text(issue.get("blocking_dependency")),
                "rule_id": _text(issue.get("rule_id")),
            }
        )
    return pd.DataFrame(rows)


def ghg_framework_table(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Build the GHG Protocol frameworks table."""
    if not result.include_ghg:
        return pd.DataFrame()
    overview = build_activity_overview(result, lang)
    ghg = result.ghg_evaluations.copy()
    rows: list[dict[str, Any]] = []
    for _, activity in overview.iterrows():
        record_id = _text(activity.get("record_id"))
        ghg_row = _row_by_record(ghg, record_id)
        combustion = ""
        if ghg_row is not None:
            code = _text(ghg_row.get("mapping_code"))
            if "stationary" in code:
                combustion = "Stationary combustion"
            elif "mobile" in code:
                combustion = "Mobile combustion"
            elif "category1" in code or "purchased" in code:
                combustion = "Purchased goods and services"
            elif "electricity" in code:
                combustion = "Purchased electricity"
            elif "not_emissions" in code:
                combustion = "Not an emissions activity"
            status = status_label(_text(ghg_row.get("mapping_status")), lang)
            reason = ghg_rationale_display(ghg_row, lang)
        else:
            status = not_run_label(lang)
            reason = ""
        rows.append(
            {
                "Activity": _text(activity.get("activity_name")),
                "Scope": _text(activity.get("ghg_label")),
                "Category / combustion type": combustion,
                "Status": status,
                "Reason": reason,
                "record_id": record_id,
            }
        )
    return pd.DataFrame(rows)


def cbam_framework_table(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Build the EU CBAM frameworks table."""
    if not result.include_cbam:
        return pd.DataFrame()
    overview = build_activity_overview(result, lang)
    cbam = result.cbam_evaluations.copy()
    rows: list[dict[str, Any]] = []
    for _, activity in overview.iterrows():
        record_id = _text(activity.get("record_id"))
        cbam_row = _row_by_record(cbam, record_id)
        missing = ""
        relevance = ""
        status = ""
        if cbam_row is not None:
            missing = _text(cbam_row.get("required_data"))
            if missing.lower() == "not_applicable":
                missing = "—"
            relevance = status_label(_text(cbam_row.get("cbam_relevance")), lang)
            status = status_label(_text(cbam_row.get("mapping_status")), lang)
        rows.append(
            {
                "Activity": _text(activity.get("activity_name")),
                "CBAM role": _text(activity.get("cbam_label")),
                "Relevance": relevance,
                "Status": status,
                "What is missing": missing,
                "record_id": record_id,
            }
        )
    return pd.DataFrame(rows)


def ifrs_framework_table(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Build the IFRS S2 frameworks table."""
    if not result.include_ifrs_s2:
        return pd.DataFrame()
    overview = build_activity_overview(result, lang)
    ifrs = result.ifrs_s2_evaluations.copy()
    rows: list[dict[str, Any]] = []
    for _, activity in overview.iterrows():
        record_id = _text(activity.get("record_id"))
        ifrs_row = _row_by_record(ifrs, record_id)
        role = ""
        missing = ""
        if ifrs_row is not None:
            role = _text(ifrs_row.get("data_role")).replace("_", " ")
            missing = _text(ifrs_row.get("missing_data"))
        rows.append(
            {
                "Activity": _text(activity.get("activity_name")),
                "Evidence role": role.title() if role else "—",
                "Readiness": _text(activity.get("ifrs_s2_label")),
                "Missing data": missing,
                "record_id": record_id,
            }
        )
    return pd.DataFrame(rows)


def _document_type_label(document_type: str, lang: str) -> str:
    key = f"ev.doc_type.{document_type}"
    labeled = t(key, lang)
    if labeled != key:
        return labeled
    return document_type.replace("_", " ") or "—"


def _document_review_status(
    doc: pd.Series,
    *,
    activity_statuses: list[str],
    lang: str,
) -> str:
    """Derive customer-facing review status — never hard-code synthetic."""
    is_synthetic = bool(doc.get("is_synthetic"))
    origin = _text(doc.get("data_origin")).lower()
    if is_synthetic or origin in {"synthetic", "synthetic_demo", "demo"}:
        return t("ev.status.demo", lang)
    if any(status == "needs_review" for status in activity_statuses):
        return t("ev.status.needs_action", lang)
    if activity_statuses and all(
        status in {"approved", "not_required"} for status in activity_statuses
    ):
        return t("ev.status.verified", lang)
    if activity_statuses:
        return t("ev.status.pending", lang)
    return t("ev.status.imported", lang)


def _document_reuse_labels(
    result: PipelineRunResult,
    source_document_id: str,
    lang: str,
) -> list[str]:
    """Return verified reuse labels for one evidence document (no fabrication)."""
    activities = result.activity_records_accepted
    if activities.empty or "source_document_id" not in activities.columns:
        return []
    linked = activities[
        activities["source_document_id"].astype(str) == source_document_id
    ]
    if linked.empty:
        return []
    labels: list[str] = []
    record_ids = {_text(row.get("record_id")) for _, row in linked.iterrows()}
    calcs = result.calculation_results
    calculated = False
    if not calcs.empty and "record_id" in calcs.columns:
        matched = calcs[calcs["record_id"].astype(str).isin(record_ids)]
        if not matched.empty:
            if "calculation_status" in matched.columns:
                calculated = (
                    matched["calculation_status"].astype(str).eq("calculated").any()
                )
            else:
                calculated = True
    if result.include_ghg and not result.ghg_evaluations.empty:
        ghg = result.ghg_evaluations
        ghg_linked = ghg[ghg["record_id"].astype(str).isin(record_ids)]
        if not ghg_linked.empty:
            labels.append(t("ev.reuse.ghg", lang))
            scopes = {
                _text(row.get("ghg_scope")).lower()
                for _, row in ghg_linked.iterrows()
            }
            if calculated and "scope_2" in scopes:
                labels.append(t("ev.reuse.scope2", lang))
            elif calculated and "scope_1" in scopes:
                labels.append(t("ev.reuse.scope1", lang))
            elif calculated:
                labels.append(t("ev.reuse.calculation", lang))
    elif calculated:
        labels.append(t("ev.reuse.calculation", lang))
    if result.include_ifrs_s2 and not result.ifrs_s2_evaluations.empty:
        ifrs = result.ifrs_s2_evaluations
        if "record_id" in ifrs.columns and ifrs["record_id"].astype(str).isin(
            record_ids
        ).any():
            labels.append(t("ev.reuse.ifrs", lang))
    # Preserve order, drop duplicates
    seen: set[str] = set()
    ordered: list[str] = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            ordered.append(label)
    return ordered


def evidence_documents_table(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Customer-facing evidence register (no hash / raw IDs as lead columns)."""
    docs = result.source_documents_accepted.copy()
    columns = [
        "file_name",
        "document_type_label",
        "period",
        "source_name",
        "used_for",
        "status",
        "source_document_id",
        "sha256",
        "data_origin",
        "ingested_at",
        "is_synthetic",
        "document_date",
        "issuer",
        "source_locator",
    ]
    if docs.empty:
        return pd.DataFrame(columns=columns)

    activities = result.activity_records_accepted
    review_by_doc: dict[str, list[str]] = {}
    if not activities.empty and "source_document_id" in activities.columns:
        for _, act in activities.iterrows():
            doc_id = _text(act.get("source_document_id"))
            review_by_doc.setdefault(doc_id, []).append(
                _text(act.get("human_review_status"))
            )

    rows: list[dict[str, Any]] = []
    for _, doc in docs.iterrows():
        doc_id = _text(doc.get("source_document_id"))
        period = _text(doc.get("document_date"))
        if period and len(period) >= 7:
            period = period[:7]
        reuse = _document_reuse_labels(result, doc_id, lang)
        rows.append(
            {
                "file_name": _text(doc.get("file_name")) or "—",
                "document_type_label": _document_type_label(
                    _text(doc.get("document_type")), lang
                ),
                "period": period or "—",
                "source_name": _text(doc.get("issuer"))
                or _text(doc.get("file_name"))
                or "—",
                "used_for": " · ".join(reuse) if reuse else t("ev.reuse.none", lang),
                "status": _document_review_status(
                    doc,
                    activity_statuses=review_by_doc.get(doc_id, []),
                    lang=lang,
                ),
                "source_document_id": doc_id,
                "sha256": _text(doc.get("sha256")),
                "data_origin": _text(doc.get("data_origin")),
                "ingested_at": _text(doc.get("ingested_at")),
                "is_synthetic": bool(doc.get("is_synthetic")),
                "document_date": _text(doc.get("document_date")),
                "issuer": _text(doc.get("issuer")),
                "source_locator": _text(doc.get("source_path"))
                or _text(doc.get("source_locator")),
            }
        )
    return pd.DataFrame(rows)


def evidence_documents_customer_view(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> pd.DataFrame:
    """Default customer columns only (no hash / IDs)."""
    full = evidence_documents_table(result, lang)
    if full.empty:
        return pd.DataFrame(
            columns=[
                t("ev.col.name", lang),
                t("ev.col.type", lang),
                t("ev.col.period", lang),
                t("ev.col.source", lang),
                t("ev.col.used_for", lang),
                t("ev.col.status", lang),
            ]
        )
    return full[
        [
            "file_name",
            "document_type_label",
            "period",
            "source_name",
            "used_for",
            "status",
        ]
    ].rename(
        columns={
            "file_name": t("ev.col.name", lang),
            "document_type_label": t("ev.col.type", lang),
            "period": t("ev.col.period", lang),
            "source_name": t("ev.col.source", lang),
            "used_for": t("ev.col.used_for", lang),
            "status": t("ev.col.status", lang),
        }
    )


def audit_summary(result: PipelineRunResult) -> dict[str, Any]:
    """Build compact audit metrics and run metadata."""
    ingested = result.ingested_at
    if ingested is None or (isinstance(ingested, float) and pd.isna(ingested)):
        ingested_at = "unavailable"
    else:
        ingested_at = str(ingested)
    return {
        "accepted_source_documents": int(len(result.source_documents_accepted)),
        "accepted_activities": int(len(result.activity_records_accepted)),
        "calculation_rows": int(len(result.calculation_results)),
        "qa_issues": int(len(result.core_qa_issues)),
        "run_id": result.run_id,
        "ingested_at": ingested_at,
        "include_ghg": bool(result.include_ghg),
        "include_cbam": bool(result.include_cbam),
        "include_ifrs_s2": bool(result.include_ifrs_s2),
    }


def official_reference_status_view(
    repo_root: Any,
    lang: str = DEFAULT_LANG,
) -> dict[str, Any]:
    """Build beginner/admin official-reference status for Audit & Export."""
    from pathlib import Path

    from carbon_ledger.reference_sync import reference_sync_status

    status = reference_sync_status(Path(repo_root))
    state_labels = {
        "available": t("aud.ref_year_available", lang),
        "candidate": t("aud.ref_year_candidate", lang),
        "unavailable": t("aud.ref_year_unavailable", lang),
        "needs_parser_review": t("aud.ref_year_candidate", lang),
    }
    electricity_rows = [
        {
            "year": year,
            "state": state,
            "label": state_labels.get(state, state),
        }
        for year, state in status.electricity_years.items()
    ]
    heating_rows = [
        {
            "fuel": fuel,
            "latest_year": (
                t("aud.ref_unregistered", lang)
                if year == "unregistered"
                else year
            ),
        }
        for fuel, year in status.heating_value_latest.items()
    ]
    return {
        "last_checked_at": status.last_checked_at,
        "electricity_rows": electricity_rows,
        "heating_rows": heating_rows,
        "snapshot_count": status.snapshot_count,
        "candidate_count": status.candidate_count,
        "source_count": status.source_count,
        "upstream_factor_authority": status.upstream_factor_authority,
        "operational_source_authority": status.operational_source_authority,
        "upstream_source_status": status.upstream_source_status,
        "operational_source_status": status.operational_source_status,
        "upstream_canonical_url": status.upstream_canonical_url,
        "operational_source_url": status.operational_source_url,
    }


def _load_emission_factor_lookup(repo_root: str) -> dict[str, dict[str, Any]]:
    path = Path(repo_root) / "data" / "reference" / "emission_factors.csv"
    if not path.is_file():
        return {}
    frame = pd.read_csv(path)
    if frame.empty or "factor_id" not in frame.columns:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        factor_id = _text(row.get("factor_id"))
        if not factor_id:
            continue
        lookup[factor_id] = {
            "factor_year": _text(row.get("factor_year")),
            "factor_value": row.get("factor_value"),
            "numerator_unit": _text(row.get("numerator_unit")),
            "denominator_unit": _text(row.get("denominator_unit")),
            "source_reference_id": _text(row.get("source_reference_id")),
        }
    return lookup


@lru_cache(maxsize=4)
def _cached_emission_factor_lookup(repo_root: str) -> dict[str, dict[str, Any]]:
    return _load_emission_factor_lookup(repo_root)


def factor_registry_row(
    factor_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any] | None:
    """Look up factor metadata for UI traces without mutating calculations."""
    cleaned = _text(factor_id)
    if not cleaned:
        return None
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    return _cached_emission_factor_lookup(str(root)).get(cleaned)


def calculation_trace_fields(
    result: PipelineRunResult,
    record_id: str,
    lang: str = DEFAULT_LANG,
    *,
    repo_root: Path | None = None,
    official_source: bool = False,
) -> dict[str, Any]:
    """Build beginner-facing calculation trace values from real outputs."""
    detail = activity_detail_context(result, record_id, lang)
    if not detail:
        return {}
    calc = detail.get("calculation") or {}
    overview = detail.get("overview") or {}
    status = _text(overview.get("calculation_status"))
    factor_id = _text(calc.get("factor_id"))
    registry = factor_registry_row(factor_id, repo_root=repo_root) or {}
    factor_value = calc.get("factor_value")
    try:
        if factor_value is not None and pd.isna(factor_value):
            factor_value = registry.get("factor_value")
    except (TypeError, ValueError):
        pass
    if factor_value is None:
        factor_value = registry.get("factor_value")
    factor_year = _text(registry.get("factor_year"))
    source_label = (
        t("act.trace_source_official", lang)
        if official_source
        else t("act.trace_source_demo", lang)
    )
    return {
        "status": status,
        "activity_name": overview.get("activity_name"),
        "activity_amount": overview.get("activity_amount"),
        "activity_unit": _text(overview.get("activity_unit")),
        "refrigerant_code": _text(overview.get("refrigerant_code"))
        or _text(calc.get("refrigerant_code")),
        "factor_id": factor_id,
        "factor_value": factor_value,
        "gwp_value": calc.get("gwp_value"),
        "gwp_id": _text(calc.get("gwp_id")) or factor_id,
        "formula_id": _text(calc.get("formula_id")),
        "formula_version": _text(calc.get("formula_version")),
        "source_reference_id": _text(calc.get("source_reference_id"))
        or _text(calc.get("gwp_source_reference_id")),
        "calculation_trace": calc.get("calculation_trace"),
        "factor_year": factor_year,
        "calculated_kgco2e": calc.get("calculated_kgco2e"),
        "calculated_tco2e": calc.get("calculated_tco2e"),
        "source_label": source_label,
        "missing": detail.get("calculation_explanation", ""),
        "next_step": detail.get("calculation_next_action", ""),
        "is_calculated": status == "calculated",
    }


def uncalculable_activity_cards(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Return beginner cards for activities that are not currently calculable."""
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return []
    cards: list[dict[str, Any]] = []
    for _, row in overview.iterrows():
        status = _text(row.get("calculation_status"))
        if status in {"calculated", "not_emissions_activity"}:
            continue
        cards.append(
            {
                "record_id": _text(row.get("record_id")),
                "activity_name": _text(row.get("activity_name")),
                "title": t("dash.uncalculable_title", lang),
                "missing": calculation_explanation(
                    status,
                    lang,
                    activity_type=_text(row.get("activity_type")),
                ),
                "next_step": calculation_next_action(status, lang),
                "status": status,
            }
        )
        if len(cards) >= limit:
            break
    return cards


def priority_action_cards(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
    *,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Concise beginner priority cards (no internal QA codes)."""
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return []
    # Prefer one card per activity type that is blocked.
    seen_types: set[str] = set()
    cards: list[dict[str, Any]] = []
    for _, row in overview.iterrows():
        status = _text(row.get("calculation_status"))
        if status in {"calculated", "not_emissions_activity"}:
            continue
        activity_type = _text(row.get("activity_type"))
        if activity_type in seen_types:
            continue
        seen_types.add(activity_type)
        if status == "blocked_missing_conversion":
            reason = t("dash.priority.missing_conversion", lang)
        elif status == "blocked_natural_gas_type_required":
            reason = t("explain.blocked_natural_gas_type_required", lang)
        elif status == "no_factor_configured":
            if activity_type == "purchased_steel":
                reason = calculation_explanation(
                    status,
                    lang,
                    activity_type=activity_type,
                )
            else:
                reason = t("dash.priority.missing_factor", lang)
        else:
            reason = calculation_explanation(
                status,
                lang,
                activity_type=activity_type,
            )
        same_type = overview[
            overview["activity_type"].astype(str) == (activity_type or "")
        ]
        affected_count = int(
            (
                ~same_type["calculation_status"].isin(
                    {"calculated", "not_emissions_activity"}
                )
            ).sum()
        )
        cards.append(
            {
                "record_id": _text(row.get("record_id")),
                "activity_name": _text(row.get("activity_name")),
                "reason": reason,
                "status": status,
                "affected_count": max(1, affected_count),
            }
        )
        if len(cards) >= limit:
            break
    return cards


def calculation_table_rows(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
    *,
    repo_root: Path | None = None,
) -> pd.DataFrame:
    """Structured calculation table with factor year for beginner results."""
    overview = build_activity_overview(result, lang)
    if overview.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    calcs = result.calculation_results
    for _, row in overview.iterrows():
        record_id = _text(row.get("record_id"))
        status = _text(row.get("calculation_status"))
        calc = _row_by_record(calcs, record_id)
        factor_value = None
        factor_year = ""
        if calc is not None:
            raw_factor = calc.get("factor_value")
            try:
                if raw_factor is not None and not pd.isna(raw_factor):
                    factor_value = float(raw_factor)
            except (TypeError, ValueError):
                factor_value = None
            factor_id = _text(calc.get("factor_id"))
            registry = factor_registry_row(factor_id, repo_root=repo_root) or {}
            factor_year = _text(calc.get("factor_year")) or _text(
                registry.get("factor_year")
            )
        if status == "calculated" and row.get("calculated_tco2e") is not None:
            emissions_cell: Any = float(row["calculated_tco2e"])
        elif status == "not_emissions_activity":
            emissions_cell = "—"
        else:
            emissions_cell = t("chart.source.not_calculated", lang)
        rows.append(
            {
                "record_id": record_id,
                t("dash.col.activity", lang): row.get("activity_name"),
                t("dash.col.amount", lang): row.get("activity_amount"),
                t("intake.col.unit", lang): row.get("activity_unit"),
                t("dash.col.factor", lang): (
                    f"{factor_value:.6g}" if factor_value is not None else "—"
                ),
                t("dash.col.factor_year", lang): factor_year or "—",
                t("dash.col.emissions", lang): (
                    f"{emissions_cell:.6g}"
                    if isinstance(emissions_cell, float)
                    else emissions_cell
                ),
                t("dash.col.calc", lang): row.get("calculation_label"),
            }
        )
    return pd.DataFrame(rows)


def beginner_result_summary(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> dict[str, Any]:
    """Summarize five beginner questions for the results page."""
    kpis = dashboard_kpi_counts(result, lang)
    emissions = calculated_emissions_summary(result, lang)
    needs_work = max(0, int(kpis["activities"]) - int(kpis["calculated"]))
    return {
        "activities": kpis["activities"],
        "calculated": kpis["calculated"],
        "needs_work": needs_work,
        "open_qa_issues": kpis["open_qa_issues"],
        "source_documents": kpis["source_documents"],
        "calculated_tco2e": emissions["calculated_tco2e"],
        "emissions_label": emissions["label"],
        "calculated_row_count": emissions["calculated_row_count"],
    }


DISPOSITION_CALCULATED = "calculated"
DISPOSITION_NEEDS_CONFIRMATION = "needs_confirmation"
DISPOSITION_EXCLUDED_DUPLICATE = "excluded_duplicate"
DISPOSITION_EXCLUDED_OUT_OF_SCOPE = "excluded_out_of_scope"
DISPOSITION_NO_MATCHING_FACTOR = "no_matching_factor"
DISPOSITION_UNSUPPORTED = "unsupported"
DISPOSITION_INVALID = "invalid"

_DISPOSITIONS = (
    DISPOSITION_CALCULATED,
    DISPOSITION_NEEDS_CONFIRMATION,
    DISPOSITION_EXCLUDED_DUPLICATE,
    DISPOSITION_EXCLUDED_OUT_OF_SCOPE,
    DISPOSITION_NO_MATCHING_FACTOR,
    DISPOSITION_UNSUPPORTED,
    DISPOSITION_INVALID,
)

_INVALID_ISSUE_CODES = frozenset(
    {
        "INVALID_ACTIVITY_VALUE",
        "UNMAPPED_ACTIVITY_TYPE",
        "UNMAPPED_UNIT",
        "SCHEMA_VALIDATION_FAILED",
        "INVALID_DATE",
        "ACTIVITY_UNIT_MISMATCH",
        "UNSUPPORTED_UNIT",
        "invalid_normalized_input",
    }
)
_HELD_ISSUE_CODES = frozenset(
    {
        "HELD_NG_CONTEXT",
        "HELD_DIESEL_CONTEXT",
        "HELD_ELEC_CONTEXT",
        "HELD_PENDING_ACTUAL_HV",
    }
)
_UNSUPPORTED_CALC_STATUSES = frozenset(
    {
        "unsupported_activity_type",
        "blocked_missing_conversion",
        "blocked_ambiguous_conversion",
        "unsupported_conversion",
    }
)
_NEEDS_CONFIRM_CALC_STATUSES = frozenset(
    {
        "blocked_natural_gas_type_required",
    }
)


def _locator_source_row(locator: Any) -> int:
    from carbon_ledger.potential_duplicates import source_row_from_locator

    return int(source_row_from_locator(locator) or 0)


def _in_scope_source_rows(uploaded_table: Any, intake_result: Any) -> list[int]:
    rows: list[int] = []
    frame = getattr(uploaded_table, "frame", None)
    if uploaded_table is not None and frame is not None:
        header = int(getattr(uploaded_table, "header_row_index", 0) or 0)
        for offset, (_, row) in enumerate(frame.iterrows()):
            texts = [str(value).strip() for value in row.tolist() if value is not None]
            if not any(texts) or all(
                text.lower() in {"", "nan", "<na>", "none"} for text in texts
            ):
                continue
            rows.append(offset + header + 2)
        if rows:
            return rows
    population: set[int] = set()
    if intake_result is not None:
        accepted = getattr(intake_result, "accepted_activities", None)
        if accepted is not None and not getattr(accepted, "empty", True):
            if "source_locator" in accepted.columns:
                population.update(
                    _locator_source_row(value)
                    for value in accepted["source_locator"].tolist()
                )
        rejected = getattr(intake_result, "rejected_rows", None)
        if rejected is not None and not getattr(rejected, "empty", True):
            if "source_row" in rejected.columns:
                population.update(
                    int(value)
                    for value in rejected["source_row"].tolist()
                    if int(value or 0) > 0
                )
    return sorted(row for row in population if row > 0)


def reconcile_row_dispositions(
    *,
    uploaded_table: Any | None = None,
    intake_result: Any | None = None,
    pipeline_result: PipelineRunResult | None = None,
    duplicate_excluded_ids: Iterable[str] | None = None,
    duplicate_candidate_ids: Iterable[str] | None = None,
    duplicate_unresolved: bool = False,
    is_uploaded_analysis: bool = False,
) -> dict[str, Any]:
    """Assign exactly one customer disposition per original uploaded row."""
    from carbon_ledger.intake import classify_activity_analysis_readiness

    excluded_ids = {str(item) for item in (duplicate_excluded_ids or ())}
    candidate_ids = {str(item) for item in (duplicate_candidate_ids or ())}
    population = _in_scope_source_rows(uploaded_table, intake_result)
    if not population and pipeline_result is not None:
        activities = pipeline_result.activity_records_accepted
        if activities is not None and not activities.empty:
            if "source_locator" in activities.columns:
                population = sorted(
                    {
                        _locator_source_row(value)
                        for value in activities["source_locator"].tolist()
                        if _locator_source_row(value) > 0
                    }
                )
    by_row: dict[int, str] = {}
    record_by_row: dict[int, str] = {}
    calc_by_record: dict[str, str] = {}
    readiness_by_record: dict[str, str] = {}
    activity_type_by_record: dict[str, str] = {}
    method_by_record: dict[str, str] = {}
    mapping_by_record: dict[str, str] = {}
    ghg_scope_by_record: dict[str, str] = {}

    if pipeline_result is not None:
        activities = pipeline_result.activity_records_accepted
        if activities is not None and not activities.empty:
            for _, row in activities.iterrows():
                record_id = _text(row.get("record_id"))
                source_row = _locator_source_row(row.get("source_locator"))
                if source_row:
                    record_by_row[source_row] = record_id
                activity_type_by_record[record_id] = _text(row.get("activity_type"))
                method_by_record[record_id] = _text(row.get("calculation_method"))
        calcs = pipeline_result.calculation_results
        if calcs is not None and not calcs.empty:
            for _, row in calcs.iterrows():
                calc_by_record[_text(row.get("record_id"))] = _text(
                    row.get("calculation_status")
                )
        readiness = pipeline_result.activity_readiness
        if readiness is not None and not readiness.empty:
            for _, row in readiness.iterrows():
                readiness_by_record[_text(row.get("record_id"))] = _text(
                    row.get("calculation_readiness")
                )
        ghg = pipeline_result.ghg_evaluations
        if ghg is not None and not ghg.empty:
            for _, row in ghg.iterrows():
                record_id = _text(row.get("record_id"))
                mapping_by_record[record_id] = _text(row.get("mapping_status"))
                ghg_scope_by_record[record_id] = _text(row.get("ghg_scope"))

    rejected_by_row: dict[int, str] = {}
    if intake_result is not None:
        accepted = getattr(intake_result, "accepted_activities", None)
        if accepted is not None and not getattr(accepted, "empty", True):
            for _, row in accepted.iterrows():
                source_row = _locator_source_row(row.get("source_locator"))
                record_id = _text(row.get("record_id"))
                if source_row and record_id:
                    record_by_row.setdefault(source_row, record_id)
                if record_id:
                    activity_type_by_record.setdefault(
                        record_id, _text(row.get("activity_type"))
                    )
                    method_by_record.setdefault(
                        record_id, _text(row.get("calculation_method"))
                    )
        rejected = getattr(intake_result, "rejected_rows", None)
        if rejected is not None and not getattr(rejected, "empty", True):
            for _, row in rejected.iterrows():
                source_row = int(row.get("source_row") or 0)
                if source_row:
                    rejected_by_row[source_row] = _text(row.get("issue_code"))

    if not population:
        population = sorted(set(record_by_row) | set(rejected_by_row))

    for source_row in population:
        record_id = record_by_row.get(source_row, "")
        issue_code = rejected_by_row.get(source_row, "")
        calc_status = calc_by_record.get(record_id, "")
        ready_status = readiness_by_record.get(record_id, "")
        if record_id and record_id in excluded_ids:
            by_row[source_row] = DISPOSITION_EXCLUDED_DUPLICATE
            continue
        if issue_code in _HELD_ISSUE_CODES or (
            duplicate_unresolved and record_id and record_id in candidate_ids
        ):
            by_row[source_row] = DISPOSITION_NEEDS_CONFIRMATION
            continue
        if calc_status == "not_emissions_activity":
            by_row[source_row] = DISPOSITION_EXCLUDED_OUT_OF_SCOPE
            continue
        activity_type = activity_type_by_record.get(record_id, "")
        if activity_type == "purchased_steel":
            method = method_by_record.get(record_id, "")
            if calc_status == "calculated":
                mapping_status = mapping_by_record.get(record_id, "")
                ghg_scope = ghg_scope_by_record.get(record_id, "")
                if mapping_status == "outside_boundary":
                    by_row[source_row] = DISPOSITION_EXCLUDED_OUT_OF_SCOPE
                    continue
                if not mapping_status or (
                    mapping_status == "mapped" and ghg_scope == "scope_3"
                ):
                    by_row[source_row] = DISPOSITION_CALCULATED
                    continue
                by_row[source_row] = DISPOSITION_NEEDS_CONFIRMATION
                continue
            if calc_status in {
                "no_factor_configured",
                "no_matching_factor",
            } and method in {
                "average_data",
                "supplier_specific",
            }:
                by_row[source_row] = DISPOSITION_NO_MATCHING_FACTOR
                continue
            by_row[source_row] = DISPOSITION_NEEDS_CONFIRMATION
            continue
        if (
            calc_status in _UNSUPPORTED_CALC_STATUSES
            or ready_status in _UNSUPPORTED_CALC_STATUSES
            or ready_status == "unsupported"
        ):
            by_row[source_row] = DISPOSITION_UNSUPPORTED
            continue
        if record_id and not calc_status:
            activity_type = activity_type_by_record.get(record_id, "")
            if activity_type:
                preview = classify_activity_analysis_readiness(
                    activity_type=activity_type,
                    fuel_subtype="",
                    process_use="",
                    activity_start=None,
                    activity_end=None,
                )
                if preview == "unsupported":
                    by_row[source_row] = DISPOSITION_UNSUPPORTED
                    continue
        if (
            issue_code in _INVALID_ISSUE_CODES
            or calc_status == "invalid_normalized_input"
        ):
            by_row[source_row] = DISPOSITION_INVALID
            continue
        if (
            calc_status in _NEEDS_CONFIRM_CALC_STATUSES
            or ready_status in _NEEDS_CONFIRM_CALC_STATUSES
            or ready_status == "needs_confirm"
            or issue_code
        ):
            by_row[source_row] = DISPOSITION_NEEDS_CONFIRMATION
            continue
        if calc_status == "calculated":
            mapping_status = mapping_by_record.get(record_id, "")
            ghg_scope = ghg_scope_by_record.get(record_id, "")
            activity_type = activity_type_by_record.get(record_id, "")
            if mapping_status == "outside_boundary":
                by_row[source_row] = DISPOSITION_EXCLUDED_OUT_OF_SCOPE
                continue
            if activity_type == "purchased_steel" and (
                not mapping_status
                or (
                    mapping_status == "mapped"
                    and ghg_scope == "scope_3"
                )
            ):
                by_row[source_row] = DISPOSITION_CALCULATED
                continue
            if mapping_status == "mapped" and ghg_scope in {
                "scope_1",
                "scope_2",
            }:
                by_row[source_row] = DISPOSITION_CALCULATED
                continue
            by_row[source_row] = DISPOSITION_NEEDS_CONFIRMATION
            continue
        by_row[source_row] = DISPOSITION_NEEDS_CONFIRMATION

    counts = {name: 0 for name in _DISPOSITIONS}
    for disposition in by_row.values():
        counts[disposition] = int(counts.get(disposition, 0)) + 1
    included = int(counts[DISPOSITION_CALCULATED])
    needs_confirmation = int(counts[DISPOSITION_NEEDS_CONFIRMATION])
    no_matching_factor = int(counts[DISPOSITION_NO_MATCHING_FACTOR])
    remaining_open = (
        needs_confirmation
        + no_matching_factor
        + int(counts[DISPOSITION_UNSUPPORTED])
        + int(counts[DISPOSITION_INVALID])
    )
    excluded = (
        int(counts[DISPOSITION_EXCLUDED_DUPLICATE])
        + int(counts[DISPOSITION_EXCLUDED_OUT_OF_SCOPE])
    )
    total = len(population)
    complete = bool(
        is_uploaded_analysis
        and included >= 1
        and remaining_open == 0
        and total == sum(counts.values())
        and total == len(by_row)
    )
    return {
        "by_row": by_row,
        "counts": counts,
        "total": total,
        "included": included,
        "needs_confirmation": needs_confirmation,
        "no_matching_factor": no_matching_factor,
        "unsupported": int(counts[DISPOSITION_UNSUPPORTED]),
        "actionable_open": needs_confirmation + no_matching_factor,
        "remaining_open": remaining_open,
        "excluded": excluded,
        "complete": complete,
        "preliminary": remaining_open > 0,
    }


def first_calculated_electricity_record_id(
    result: PipelineRunResult,
) -> str | None:
    """Return a calculated grid_electricity record_id for trace examples."""
    activities = result.activity_records_accepted
    calcs = result.calculation_results
    if activities.empty or calcs.empty:
        return None
    electricity = activities[
        activities["activity_type"].astype(str) == "grid_electricity"
    ]
    if electricity.empty:
        return None
    for record_id in electricity["record_id"].astype(str).tolist():
        calc_row = calcs[calcs["record_id"].astype(str) == record_id]
        if calc_row.empty:
            continue
        if _text(calc_row.iloc[0].get("calculation_status")) == "calculated":
            return record_id
    return None


def activity_detail_context(
    result: PipelineRunResult,
    record_id: str,
    lang: str = DEFAULT_LANG,
) -> dict[str, Any]:
    """Assemble detail-panel data for one activity without mutating sources."""
    overview = build_activity_overview(result, lang)
    matched = overview[overview["record_id"] == record_id]
    if matched.empty:
        return {}
    row = matched.iloc[0]
    activity = _row_by_record(result.activity_records_accepted.copy(), record_id)
    calc = _row_by_record(result.calculation_results.copy(), record_id)
    normalized = _row_by_record(result.normalized_records.copy(), record_id)
    ghg = _row_by_record(result.ghg_evaluations.copy(), record_id)
    cbam = _row_by_record(result.cbam_evaluations.copy(), record_id)
    ifrs = _row_by_record(result.ifrs_s2_evaluations.copy(), record_id)
    issues = result.core_qa_issues.copy()
    record_issues = (
        issues[issues["record_id"].astype(str) == record_id]
        if not issues.empty and "record_id" in issues.columns
        else pd.DataFrame()
    )
    calc_status = _text(row.get("calculation_status"))
    return {
        "overview": row.to_dict(),
        "activity": activity.to_dict() if activity is not None else {},
        "calculation": calc.to_dict() if calc is not None else {},
        "normalized": normalized.to_dict() if normalized is not None else {},
        "ghg": ghg.to_dict() if ghg is not None else {},
        "cbam": cbam.to_dict() if cbam is not None else {},
        "ifrs_s2": ifrs.to_dict() if ifrs is not None else {},
        "issues": record_issues,
        "calculation_label": calculation_label(calc_status, lang),
        "calculation_explanation": calculation_explanation(
            calc_status,
            lang,
            activity_type=_text(row.get("activity_type")),
        ),
        "calculation_next_action": calculation_next_action(calc_status, lang),
    }


def ghg_scope_counts(
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
) -> dict[str, int]:
    """Count GHG evaluation rows by display scope label."""
    if not result.include_ghg:
        return {}
    table = ghg_framework_table(result, lang)
    if table.empty:
        return {}
    counts = table["Scope"].value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def labeled_scope_hero_caption(
    scope_states: Mapping[str, Any],
    lang: str = DEFAULT_LANG,
) -> str:
    """Compact hero caption for the company inventory (Scope 1 + Scope 2).

    Scope 3 is shown on its own card and is never mixed into this caption.
    """
    bits: list[str] = []
    for scope_key, label_key in (
        ("scope_1", "dash.kpi.scope1"),
        ("scope_2", "dash.hero.scope2_location"),
    ):
        state = scope_states.get(scope_key) or {}
        if state.get("state") != "calculated":
            continue
        bits.append(
            t(
                "dash.hero.scope_value",
                lang,
                label=t(label_key, lang),
                value=f"{float(state.get('value') or 0.0):.2f}",
            )
        )
    return " · ".join(bits)


def hero_result_status_and_disposition(
    *,
    uploaded: bool,
    dispositions: Mapping[str, Any],
    calculated_count: int,
    activity_count: int,
    needs_work: int,
    lang: str = DEFAULT_LANG,
    inventory_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Separate uploaded-row and demo-result copy. Never mix the two counts."""
    counts = dict(inventory_counts or {})
    if uploaded:
        included = int(
            counts.get("included_in_inventory", dispositions.get("included") or 0)
        )
        total = int(dispositions.get("total") or 0)
        remaining_open = int(dispositions.get("remaining_open") or 0)
        actionable_open = int(
            dispositions.get("actionable_open", remaining_open) or 0
        )
        unsupported = int(dispositions.get("unsupported") or 0)
        no_factor = int(dispositions.get("no_matching_factor") or 0)
        excluded_n = int(
            counts.get("outside_boundary", dispositions.get("excluded") or 0)
        )
        complete = bool(dispositions.get("complete"))
        technically = int(
            counts.get("technically_calculated", calculated_count)
        )
        needs_review = int(
            dispositions.get(
                "needs_confirmation",
                counts.get("needs_review", remaining_open),
            )
        )
        status_line = t(
            "dash.result_preliminary_body",
            lang,
            calculated=technically,
            included=included,
            needs_review=needs_review,
            unsupported=unsupported,
            outside=excluded_n,
        )
        if no_factor:
            status_line = (
                f"{status_line} "
                f"{t('dash.result_no_factor', lang, n=no_factor)}"
            )
        if remaining_open > 0 or needs_review > 0:
            status = t("dash.result_preliminary", lang)
            disposition = status_line if included >= 1 or technically >= 1 else ""
            incomplete = (
                t("dash.result_incomplete_sources", lang)
                if actionable_open > 0
                else ""
            )
        elif complete and included >= 1:
            status = t("dash.coverage_complete", lang, total=total)
            disposition = t(
                "dash.hero.included",
                lang,
                included=included,
                total=total,
            )
            incomplete = ""
        else:
            status = t("dash.result_preliminary", lang)
            disposition = status_line if technically >= 1 else ""
            incomplete = ""
        return {
            "status_label": status,
            "disposition_caption": disposition,
            "incomplete_caption": incomplete,
            "excluded_caption": (
                t("dash.hero.excluded", lang, n=excluded_n)
                if excluded_n
                else ""
            ),
            "included": included,
            "hero_done": included,
            "hero_total": total,
            "complete": complete,
            "remaining_open": remaining_open,
            "actionable_open": actionable_open,
            "unresolved": remaining_open,
        }

    complete_demo = int(calculated_count) > 0
    return {
        "status_label": (
            t("dash.coverage_complete_demo", lang)
            if complete_demo
            else t("dash.result_preliminary", lang)
        ),
        "disposition_caption": "",
        "incomplete_caption": "",
        "excluded_caption": "",
        "included": 0,
        "total": int(activity_count),
        "remaining_open": int(needs_work),
        "actionable_open": int(needs_work),
        "complete": complete_demo,
        "hero_done": int(calculated_count),
        "hero_total": int(activity_count),
        "unresolved": int(needs_work),
    }
