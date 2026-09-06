"""Assemble a customer emissions-summary report from existing results.

Presentation only. Does not recalculate emissions, match factors, or alter
applicability / boundary semantics.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

import pandas as pd

from carbon_ledger.pipeline import PipelineRunResult
from carbon_ledger.ui.customer_presenters import present_assessment
from carbon_ledger.ui.i18n import DEFAULT_LANG, t
from carbon_ledger.ui.state import REPO_ROOT, activity_period_bounds
from carbon_ledger.ui.view_models import (
    DISPOSITION_CALCULATED,
    DISPOSITION_EXCLUDED_DUPLICATE,
    DISPOSITION_EXCLUDED_OUT_OF_SCOPE,
    DISPOSITION_INVALID,
    DISPOSITION_NEEDS_CONFIRMATION,
    DISPOSITION_NO_MATCHING_FACTOR,
    DISPOSITION_UNSUPPORTED,
    activity_display_name,
    beginner_result_summary,
    company_inventory_emissions_summary,
    company_inventory_record_ids,
    factor_registry_row,
    hero_result_status_and_disposition,
    inventory_status_counts,
    reconcile_row_dispositions,
    scope_kpi_states,
)

_UNSAFE_FILENAME = re.compile(r"[^\w.\-]+", re.UNICODE)
SYSTEM_VERSION = "0.1.0"
PDF_UNIT = "tCO₂e"
_FORBIDDEN_FILENAME_PARTS = frozenset(
    {
        "尚未提供",
        "Not-yet-provided",
        "Not yet provided",
        "company",
        "Company",
    }
)
_CO2E_DISPLAY = (
    ("tCO²e", "tCO₂e"),
    ("kgCO²e", "kgCO₂e"),
    ("CO²e", "CO₂e"),
    ("CO2e", "CO₂e"),
)
_SCOPE_BY_ACTIVITY = {
    "grid_electricity": "scope_2",
    "natural_gas": "scope_1",
    "diesel": "scope_1",
    "refrigerant_refill": "scope_1",
}
_QUALITY_CODES = (
    DISPOSITION_CALCULATED,
    DISPOSITION_NEEDS_CONFIRMATION,
    DISPOSITION_NO_MATCHING_FACTOR,
    DISPOSITION_EXCLUDED_DUPLICATE,
    DISPOSITION_EXCLUDED_OUT_OF_SCOPE,
    DISPOSITION_UNSUPPORTED,
    DISPOSITION_INVALID,
)
_INTERNAL_TOKENS = (
    "NEEDS_INFORMATION",
    "NEEDS_REVIEW",
    "NOT_APPLICABLE",
    "APPLICABLE",
    "FUTURE_REQUIREMENT",
    "ghg_inventory",
    "ifrs_s1_s2",
    "ifrs_reporting_entity",
    "tw_order_",
    "factor_id",
    "formula_id",
    "calculation_trace",
    "schema_version",
    "STATE_",
    "dash.",
    "nav.",
    "boundary-semantics",
    "dry-run",
)


@dataclass(frozen=True)
class ApplicabilityRow:
    title: str
    status: str
    timing: str
    reason: str


@dataclass(frozen=True)
class SourceShareRow:
    name: str
    scope_label: str
    tco2e: float
    share: float


@dataclass(frozen=True)
class MethodRow:
    activity_name: str
    method: str
    factor_label: str
    factor_unit: str
    factor_source: str
    factor_year: str
    heating: str
    usage_count: int = 1


@dataclass(frozen=True)
class FileRow:
    name: str
    sheet: str
    rows: int


@dataclass(frozen=True)
class EmissionsReportModel:
    lang: str
    complete: bool
    status_label: str
    report_title: str
    company_name: str
    reporting_period: str
    reporting_year: str
    data_coverage_period: str
    generated_at: str
    system_version: str
    total_tco2e: float | None
    scope_1_tco2e: float | None
    scope_2_tco2e: float | None
    scope_2_method: str
    included_rows: int
    population_rows: int
    pending_rows: int
    excluded_rows: int
    source_documents: int
    status_explanation: str
    scope3_note: str
    applicability: tuple[ApplicabilityRow, ...]
    applicability_disclaimer: str
    entity_name: str
    entities_included: tuple[str, ...]
    entities_pending: tuple[str, ...]
    boundary_summary: str
    sites_included: tuple[str, ...]
    boundary_pending: tuple[str, ...]
    exclusions: tuple[tuple[str, str], ...]
    sources: tuple[SourceShareRow, ...]
    site_rows: tuple[SourceShareRow, ...]
    methods: tuple[MethodRow, ...]
    assumptions: tuple[str, ...]
    quality_counts: tuple[tuple[str, int], ...]
    quality_reconciled: bool
    limitations: tuple[str, ...]
    appendix_files: tuple[FileRow, ...]
    appendix_pending: tuple[str, ...]
    coverage_partial: bool
    fingerprint: str


def sanitize_filename_part(value: str, *, fallback: str = "") -> str:
    """Keep filename characters portable and remove path punctuation."""
    cleaned = _UNSAFE_FILENAME.sub("-", str(value or "").strip())
    cleaned = cleaned.strip(".-_") or fallback
    return cleaned[:80]


def emissions_report_filename(*, company: str, period: str) -> str:
    company_part = sanitize_filename_part(company, fallback="")
    period_part = sanitize_filename_part(period, fallback="period")
    if (
        not company_part
        or company_part in _FORBIDDEN_FILENAME_PARTS
        or any(token in company_part for token in ("尚未提供", "Not-yet-provided"))
    ):
        raise ValueError("customer PDF filename requires a confirmed company name")
    return f"ghg-emissions-summary-{company_part}-{period_part}.pdf"


def present_co2e_unit(value: str) -> str:
    """Normalize presentation units to professional subscript CO₂e."""
    text = str(value or "")
    for src, dest in _CO2E_DISPLAY:
        text = text.replace(src, dest)
    return text


def format_tco2e(value: float | None, lang: str = DEFAULT_LANG) -> str:
    if value is None:
        return t("report.value_unavailable", lang)
    return present_co2e_unit(f"{float(value):.2f} {PDF_UNIT}")


def _parse_timestamp(value: Any):
    from datetime import datetime, timezone

    if value is None or value == "":
        return None
    if hasattr(value, "to_pydatetime"):
        try:
            value = value.to_pydatetime()
        except (TypeError, ValueError):
            pass
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def format_report_generated_at(value: Any, lang: str = DEFAULT_LANG) -> str:
    """Commercial Asia/Taipei timestamp. Never show raw ISO or microseconds."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    parsed = _parse_timestamp(value)
    if parsed is None:
        parsed = datetime.now(ZoneInfo("Asia/Taipei"))
    local = parsed.astimezone(ZoneInfo("Asia/Taipei")).replace(microsecond=0)
    stamp = local.strftime("%Y-%m-%d %H:%M")
    if lang == "en":
        return f"{stamp} (Asia/Taipei)"
    return f"{stamp}（Asia/Taipei）"


def now_report_generated_at() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Asia/Taipei")).replace(microsecond=0).isoformat()


def _factor_source_label(source_id: str, lang: str) -> str:
    key = f"report.factor_source.{source_id}"
    label = t(key, lang)
    if label != key:
        return label
    if source_id:
        return t("report.factor_source.official", lang)
    return t("report.value_unavailable", lang)


def _scope_label(scope_key: str, lang: str) -> str:
    if scope_key == "scope_1":
        return t("dash.kpi.scope1", lang)
    if scope_key == "scope_2":
        return t("dash.hero.scope2_location", lang)
    return "—"


def _quality_label(code: str, lang: str) -> str:
    return t(f"report.disp.{code}", lang)


def _not_provided(lang: str) -> str:
    return t("report.not_provided", lang)


def _display_or_missing(value: Any, lang: str) -> str:
    text = str(value or "").strip()
    if not text or text in {"—", "-", "nan", "None"}:
        return _not_provided(lang)
    return text


def _source_breakdown(
    result: PipelineRunResult, lang: str
) -> tuple[SourceShareRow, ...]:
    calcs = result.calculation_results
    activities = result.activity_records_accepted
    if calcs is None or calcs.empty or activities is None or activities.empty:
        return ()
    included = company_inventory_record_ids(result)
    calculated = calcs[calcs["record_id"].astype(str).isin(included)].copy()
    if calculated.empty:
        return ()
    calculated["tco2e"] = pd.to_numeric(calculated["calculated_tco2e"], errors="coerce")
    calculated = calculated.dropna(subset=["tco2e"])
    calculated = calculated[calculated["tco2e"] > 0]
    if calculated.empty:
        return ()
    type_by_id = {
        str(row.get("record_id") or ""): str(row.get("activity_type") or "")
        for _, row in activities.iterrows()
    }
    calculated["activity_type"] = calculated["record_id"].astype(str).map(type_by_id)
    grouped = (
        calculated.groupby("activity_type", dropna=False)["tco2e"]
        .sum()
        .sort_values(ascending=False)
    )
    total = float(grouped.sum()) or 1.0
    rows: list[SourceShareRow] = []
    for activity_type, value in grouped.items():
        amount = float(value)
        if amount <= 0:
            continue
        scope_key = _SCOPE_BY_ACTIVITY.get(str(activity_type), "")
        rows.append(
            SourceShareRow(
                name=activity_display_name(str(activity_type or ""), lang),
                scope_label=_scope_label(scope_key, lang),
                tco2e=amount,
                share=amount / total,
            )
        )
    return tuple(rows)


def _site_breakdown(result: PipelineRunResult, lang: str) -> tuple[SourceShareRow, ...]:
    activities = result.activity_records_accepted
    calcs = result.calculation_results
    if (
        activities is None
        or activities.empty
        or calcs is None
        or calcs.empty
        or "site_id" not in activities.columns
    ):
        return ()
    included = company_inventory_record_ids(result)
    calculated = calcs[calcs["record_id"].astype(str).isin(included)].copy()
    if calculated.empty:
        return ()
    calculated["tco2e"] = pd.to_numeric(calculated["calculated_tco2e"], errors="coerce")
    calculated = calculated.dropna(subset=["tco2e"])
    calculated = calculated[calculated["tco2e"] > 0]
    if calculated.empty:
        return ()
    site_by_id = {
        str(row.get("record_id") or ""): str(row.get("site_id") or "").strip()
        for _, row in activities.iterrows()
    }
    calculated["site_name"] = calculated["record_id"].astype(str).map(site_by_id)
    calculated = calculated[calculated["site_name"].fillna("").ne("")]
    if calculated.empty:
        return ()
    grouped = (
        calculated.groupby("site_name", dropna=False)["tco2e"]
        .sum()
        .sort_values(ascending=False)
    )
    total = float(grouped.sum()) or 1.0
    rows: list[SourceShareRow] = []
    for site, value in grouped.items():
        label = str(site or "").strip()
        if not label or label.lower() in {"nan", "<na>", "none"}:
            continue
        amount = float(value)
        rows.append(
            SourceShareRow(
                name=label,
                scope_label="",
                tco2e=amount,
                share=amount / total,
            )
        )
    return tuple(rows)


def _method_rows(result: PipelineRunResult, lang: str) -> tuple[MethodRow, ...]:
    calcs = result.calculation_results
    activities = result.activity_records_accepted
    if calcs is None or calcs.empty:
        return ()
    calculated = calcs[calcs["calculation_status"].astype(str) == "calculated"]
    if calculated.empty:
        return ()
    subtype_by_id: dict[str, str] = {}
    type_by_id: dict[str, str] = {}
    if activities is not None and not activities.empty:
        for _, activity in activities.iterrows():
            record_id = str(activity.get("record_id") or "")
            type_by_id[record_id] = str(activity.get("activity_type") or "")
            subtype = str(activity.get("fuel_subtype") or "").strip()
            if subtype in {"NG1", "NG2"}:
                subtype_by_id[record_id] = subtype
    grouped: dict[tuple[str, ...], dict[str, Any]] = {}
    for _, row in calculated.iterrows():
        record_id = str(row.get("record_id") or "")
        activity_type = str(row.get("activity_type") or type_by_id.get(record_id) or "")
        if not activity_type:
            continue
        registry = (
            factor_registry_row(str(row.get("factor_id") or ""), repo_root=REPO_ROOT)
            or {}
        )
        source_id = str(row.get("source_reference_id") or "")
        num = str(
            row.get("factor_numerator_unit") or registry.get("numerator_unit") or ""
        )
        den = str(
            row.get("factor_denominator_unit") or registry.get("denominator_unit") or ""
        )
        year = str(registry.get("factor_year") or row.get("factor_year") or "")
        factor_id = str(row.get("factor_id") or "")
        factor_value = row.get("factor_value")
        try:
            if factor_value is not None and pd.isna(factor_value):
                factor_value = registry.get("factor_value")
        except (TypeError, ValueError):
            pass
        if factor_value is None:
            factor_value = registry.get("factor_value")
        hv = row.get("heating_value")
        try:
            has_hv = hv is not None and not pd.isna(hv)
        except (TypeError, ValueError):
            has_hv = bool(hv)
        hv_text = str(hv) if has_hv else ""
        hv_unit = str(row.get("heating_value_unit") or "") if has_hv else ""
        subtype = subtype_by_id.get(record_id, "")
        key = (
            activity_type,
            factor_id,
            f"{float(factor_value):.12g}" if factor_value is not None else "",
            num,
            den,
            source_id,
            year,
            hv_text,
            hv_unit,
            subtype,
        )
        bucket = grouped.setdefault(
            key,
            {
                "activity_type": activity_type,
                "source_id": source_id,
                "num": num,
                "den": den,
                "year": year,
                "factor_value": factor_value,
                "hv": hv if has_hv else None,
                "hv_unit": hv_unit,
                "subtype": subtype,
                "count": 0,
            },
        )
        bucket["count"] += 1
    rows: list[MethodRow] = []
    for bucket in grouped.values():
        unit = present_co2e_unit(
            f"{bucket['num']}/{bucket['den']}".strip("/") or "—"
        )
        heating = ""
        if bucket["hv"] is not None:
            heating = t(
                "report.heating_used",
                lang,
                value=bucket["hv"],
                unit=bucket["hv_unit"],
            )
        factor_value = bucket["factor_value"]
        factor_label = (
            f"{float(factor_value):.6g}" if factor_value is not None else "—"
        )
        activity_name = activity_display_name(str(bucket["activity_type"]), lang)
        if bucket["subtype"]:
            activity_name = t(
                "report.activity_with_subtype",
                lang,
                activity=activity_name,
                subtype=bucket["subtype"],
            )
        rows.append(
            MethodRow(
                activity_name=activity_name,
                method=t("report.method.activity_times_factor", lang),
                factor_label=factor_label,
                factor_unit=unit,
                factor_source=_factor_source_label(str(bucket["source_id"]), lang),
                factor_year=str(bucket["year"] or "—"),
                heating=heating,
                usage_count=int(bucket["count"]),
            )
        )
    return tuple(rows)


def _appendix_files(result: PipelineRunResult, lang: str) -> tuple[FileRow, ...]:
    docs = result.source_documents_accepted
    activities = result.activity_records_accepted
    if docs is None or docs.empty:
        return ()
    rows: list[FileRow] = []
    for _, row in docs.iterrows():
        name = str(
            row.get("file_name")
            or row.get("source_file_name")
            or row.get("document_name")
            or t("report.unnamed_file", lang)
        )
        sheet = str(row.get("sheet_name") or row.get("worksheet") or "—")
        doc_id = str(row.get("source_document_id") or "")
        count = 0
        if activities is not None and not activities.empty and doc_id:
            if "source_document_id" in activities.columns:
                matched = activities["source_document_id"].astype(str) == doc_id
                count = int(matched.sum())
        if not count:
            raw = row.get("accepted_row_count") or row.get("row_count") or 0
            try:
                count = int(raw)
            except (TypeError, ValueError):
                count = 0
        rows.append(FileRow(name=name, sheet=sheet, rows=count))
    return tuple(rows[:20])


def _limitations(*, complete: bool, pending_rows: int, lang: str) -> tuple[str, ...]:
    items = [
        t("report.limit.supported_only", lang),
        t("report.limit.scope3", lang),
        t("report.limit.refrigerant", lang),
        t("report.limit.no_assurance", lang),
        t("report.limit.not_filing", lang),
        t("report.limit.not_legal", lang),
    ]
    if not complete or pending_rows:
        items.append(t("report.limit.preliminary_items", lang, n=pending_rows))
    else:
        items.append(t("report.limit.complete_not_all_sources", lang))
    return tuple(items)


def _fingerprint(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _pending_activity_names(result: PipelineRunResult, lang: str) -> tuple[str, ...]:
    calcs = result.calculation_results
    activities = result.activity_records_accepted
    if calcs is None or calcs.empty:
        return ()
    blocked = calcs[
        ~calcs["calculation_status"].astype(str).isin(
            {"calculated", "not_emissions_activity"}
        )
    ]
    if blocked.empty:
        return ()
    type_by_id = {}
    if activities is not None and not activities.empty:
        type_by_id = {
            str(row.get("record_id") or ""): str(row.get("activity_type") or "")
            for _, row in activities.iterrows()
        }
    names: list[str] = []
    seen: set[str] = set()
    for _, row in blocked.iterrows():
        activity_type = str(
            row.get("activity_type")
            or type_by_id.get(str(row.get("record_id") or ""), "")
        )
        label = activity_display_name(activity_type, lang) if activity_type else ""
        if not label or label in seen:
            continue
        seen.add(label)
        names.append(label)
        if len(names) >= 8:
            break
    return tuple(names)


def build_emissions_report_model(
    *,
    result: PipelineRunResult,
    lang: str = DEFAULT_LANG,
    company_name: str = "",
    reporting_year: str | int | None = None,
    reporting_period_start: str = "",
    reporting_period_end: str = "",
    data_coverage_start: str = "",
    data_coverage_end: str = "",
    assessment: Any = None,
    dispositions: Mapping[str, Any] | None = None,
    uploaded: bool = False,
    generated_at: str | None = None,
    entity_name: str = "",
    entities_included: tuple[str, ...] = (),
    entities_pending: tuple[str, ...] = (),
    sites_included: tuple[str, ...] = (),
    sites_pending: tuple[str, ...] = (),
    exclusions: tuple[tuple[str, str], ...] = (),
    boundary_summary: str = "",
) -> EmissionsReportModel:
    """Read existing session/result/view-model data into one report snapshot."""
    summary = beginner_result_summary(result, lang)
    emissions = company_inventory_emissions_summary(result, lang)
    scopes = scope_kpi_states(result)
    recon = dispositions or reconcile_row_dispositions(
        pipeline_result=result,
        is_uploaded_analysis=uploaded,
    )
    counts = inventory_status_counts(result)
    hero = hero_result_status_and_disposition(
        uploaded=uploaded,
        dispositions=recon,
        calculated_count=int(counts["technically_calculated"]),
        activity_count=int(summary["activities"]),
        needs_work=int(counts["needs_review"]),
        lang=lang,
        inventory_counts=counts,
    )
    complete = bool(hero["complete"])
    total = emissions.get("inventory_tco2e")
    if total is not None:
        total = float(total)
    scope_1_state = scopes.get("scope_1") or {}
    scope_2_state = scopes.get("scope_2") or {}
    scope_1 = (
        float(scope_1_state["value"])
        if scope_1_state.get("state") == "calculated"
        else None
    )
    scope_2 = (
        float(scope_2_state["value"])
        if scope_2_state.get("state") == "calculated"
        else None
    )
    company = str(company_name or "").strip()
    if company in _FORBIDDEN_FILENAME_PARTS:
        company = ""
    year_text = str(reporting_year or "").strip()
    if reporting_period_start and reporting_period_end:
        period_text = f"{reporting_period_start} – {reporting_period_end}"
        if not year_text:
            year_text = str(reporting_period_start)[:4]
    else:
        period_text = ""
    cover_start, cover_end = data_coverage_start, data_coverage_end
    if not (cover_start and cover_end):
        auto_start, auto_end = activity_period_bounds(result.activity_records_accepted)
        cover_start = cover_start or str(auto_start or "")
        cover_end = cover_end or str(auto_end or "")
    if cover_start and cover_end:
        coverage_text = f"{cover_start} – {cover_end}"
    else:
        coverage_text = ""
    coverage_partial = bool(
        period_text
        and coverage_text
        and coverage_text != period_text
        and not (
            cover_start == reporting_period_start[:7]
            and cover_end == reporting_period_end[:7]
            and reporting_period_start.endswith("-01-01")
            and reporting_period_end.endswith("-12-31")
            and cover_start.endswith("-01")
            and cover_end.endswith("-12")
        )
    )
    if generated_at:
        stamp = format_report_generated_at(generated_at, lang)
    else:
        stamp = ""
    presented = present_assessment(assessment, lang)
    applicability = tuple(
        ApplicabilityRow(
            title=item.title,
            status=item.short_status,
            timing="；".join(
                label for label, _value in item.timing_items if str(label).strip()
            ),
            reason=item.explanation,
        )
        for item in presented.presentations
    )
    counts = dict(recon.get("counts") or {})
    quality = tuple(
        (_quality_label(code, lang), int(counts.get(code) or 0))
        for code in _QUALITY_CODES
    )
    counted = sum(int(counts.get(code) or 0) for code in _QUALITY_CODES)
    population = int(recon.get("total") or summary["activities"] or 0)
    by_row = recon.get("by_row") or {}
    quality_reconciled = population == counted and population == len(by_row)
    pending_rows = int(hero["remaining_open"])
    included = int(hero["included"] or summary["calculated"])
    if not uploaded:
        included = int(summary["calculated"])
    status_explanation = str(
        hero.get("disposition_caption")
        or (
            t("report.status.complete_body", lang)
            if complete
            else t("report.status.preliminary_body", lang)
        )
    )
    methods = _method_rows(result, lang)
    assumptions = (
        t("report.assume.ghg_protocol", lang),
        t("report.assume.location_based", lang),
        t("report.assume.calculated_only", lang),
    )
    sources = _source_breakdown(result, lang)
    pending_items = list(_pending_activity_names(result, lang))
    if pending_rows and not pending_items:
        pending_items.append(t("report.pending.generic", lang, n=pending_rows))
    excluded_n = int(recon.get("excluded") or 0)
    sites = tuple(sites_included)
    pending = tuple(sites_pending)
    if not boundary_summary and company:
        boundary_summary = t(
            "report.boundary.confirmed_company", lang, company=company
        )
    elif not boundary_summary:
        boundary_summary = t("report.still_pending", lang)
    model_core = {
        "lang": lang,
        "complete": complete,
        "status_label": str(hero["status_label"]),
        "company_name": company,
        "reporting_period": period_text,
        "reporting_year": year_text,
        "data_coverage_period": coverage_text,
        "total_tco2e": total,
        "scope_1_tco2e": scope_1,
        "scope_2_tco2e": scope_2,
        "included_rows": included,
        "population_rows": int(hero["hero_total"] or population),
        "pending_rows": pending_rows,
        "excluded_rows": excluded_n,
        "source_documents": int(summary["source_documents"]),
        "sources": [asdict(row) for row in sources],
        "quality_counts": [(label, value) for label, value in quality],
        "applicability": [asdict(row) for row in applicability],
        "sites": list(sites),
        "methods": [asdict(row) for row in methods],
    }
    fingerprint = _fingerprint(model_core)
    return EmissionsReportModel(
        lang=lang,
        complete=complete,
        status_label=str(hero["status_label"]),
        report_title=t("report.title", lang),
        company_name=company,
        reporting_period=period_text,
        reporting_year=year_text or t("report.still_pending", lang),
        data_coverage_period=coverage_text,
        generated_at=stamp,
        system_version=SYSTEM_VERSION,
        total_tco2e=total,
        scope_1_tco2e=scope_1,
        scope_2_tco2e=scope_2,
        scope_2_method=t("dash.hero.scope2_location", lang),
        included_rows=included,
        population_rows=int(hero["hero_total"] or population),
        pending_rows=pending_rows,
        excluded_rows=excluded_n,
        source_documents=int(summary["source_documents"]),
        status_explanation=status_explanation,
        scope3_note=t("report.scope3_note", lang),
        applicability=applicability,
        applicability_disclaimer=t("report.applicability_disclaimer", lang),
        entity_name=entity_name or company,
        entities_included=entities_included,
        entities_pending=entities_pending,
        boundary_summary=boundary_summary,
        sites_included=sites,
        boundary_pending=pending,
        exclusions=exclusions,
        sources=sources,
        site_rows=_site_breakdown(result, lang),
        methods=methods,
        assumptions=assumptions,
        quality_counts=quality,
        quality_reconciled=bool(quality_reconciled),
        limitations=_limitations(
            complete=complete, pending_rows=pending_rows, lang=lang
        ),
        appendix_files=_appendix_files(result, lang),
        appendix_pending=tuple(pending_items),
        coverage_partial=coverage_partial,
        fingerprint=fingerprint,
    )


def has_company_and_reporting_period(session_state: Any) -> bool:
    """True when company identity and a confirmed ReportingPeriod both exist."""
    from carbon_ledger.ui.emissions_report_scope import (
        has_confirmed_company_and_reporting_period,
    )

    return has_confirmed_company_and_reporting_period(session_state)


def build_emissions_report_from_session(
    session_state: Any,
    *,
    lang: str = DEFAULT_LANG,
    generated_at: str | None = None,
) -> EmissionsReportModel | None:
    """Build the report from the same session inputs the dashboard uses."""
    from carbon_ledger.potential_duplicates import (
        excluded_record_ids,
        groups_from_intake,
        unresolved_potential_duplicate_groups,
    )
    from carbon_ledger.ui.emissions_report_scope import (
        confirmed_company_display_name,
        load_confirmed_report_scope,
    )
    from carbon_ledger.ui.state import (
        STATE_INTAKE_RESULT,
        STATE_INTAKE_TABLE,
        _ss_get,
        duplicate_review_decisions_from_state,
        get_analysis_source_summary,
        get_applicability_assessment,
        get_current_result,
        is_uploaded_analysis,
    )

    result = get_current_result(session_state)
    if result is None:
        return None
    scope = load_confirmed_report_scope(session_state, lang=lang)
    company = confirmed_company_display_name(session_state)
    if scope is None or not company:
        return None
    period = scope.reporting_period
    source = get_analysis_source_summary(session_state)
    uploaded = is_uploaded_analysis(session_state)
    intake_result = _ss_get(session_state, STATE_INTAKE_RESULT)
    uploaded_table = _ss_get(session_state, STATE_INTAKE_TABLE)
    duplicate_decisions = duplicate_review_decisions_from_state(session_state)
    dup_groups = groups_from_intake(intake_result) if intake_result is not None else []
    excluded_ids = excluded_record_ids(dup_groups, duplicate_decisions)
    unresolved_groups = unresolved_potential_duplicate_groups(
        dup_groups, duplicate_decisions
    )
    candidate_ids = {
        str(record_id)
        for group in unresolved_groups
        for record_id in group.record_ids
    }
    dispositions = reconcile_row_dispositions(
        uploaded_table=uploaded_table,
        intake_result=intake_result,
        pipeline_result=result,
        duplicate_excluded_ids=excluded_ids,
        duplicate_candidate_ids=candidate_ids,
        duplicate_unresolved=bool(unresolved_groups),
        is_uploaded_analysis=uploaded,
    )
    coverage_start = str(source.get("period_start") or "")
    coverage_end = str(source.get("period_end") or "")
    return build_emissions_report_model(
        result=result,
        lang=lang,
        company_name=scope.company_name or company,
        reporting_year=period.reporting_year_confirmed,
        reporting_period_start=period.period_start_confirmed,
        reporting_period_end=period.period_end_confirmed,
        data_coverage_start=coverage_start,
        data_coverage_end=coverage_end,
        assessment=get_applicability_assessment(session_state),
        dispositions=dispositions,
        uploaded=uploaded,
        generated_at=generated_at,
        entity_name=scope.entity_name,
        entities_included=scope.entities_included,
        entities_pending=scope.entities_pending,
        sites_included=scope.sites_included,
        sites_pending=scope.sites_pending,
        exclusions=scope.exclusions,
        boundary_summary=scope.boundary_summary,
    )


def model_contains_internal_token(model: EmissionsReportModel) -> str:
    """Return the first leaked internal token, else empty."""
    blob = json.dumps(asdict(model), ensure_ascii=False)
    for token in _INTERNAL_TOKENS:
        if token in blob:
            return token
    return ""


def text_contains_internal_token(text: str) -> str:
    for token in _INTERNAL_TOKENS:
        if token in text:
            return token
    return ""
