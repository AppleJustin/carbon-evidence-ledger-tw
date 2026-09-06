"""Streamlit confirmation form for purchased-steel Category 1 rows."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from carbon_ledger.activity_boundary_decisions import reporting_year_from_activity
from carbon_ledger.intake import (
    READINESS_NEEDS_CONFIRM,
    READINESS_NO_MATCHING_FACTOR,
    READINESS_READY,
    READINESS_UNSUPPORTED,
    classify_activity_ui_readiness,
    purchased_steel_missing_fields,
)
from carbon_ledger.purchased_steel import (
    CONTROL_NOT_APPLICABLE,
    CONTROL_REPORTING_COMPANY,
    CONTROL_THIRD_PARTY,
    CONTROL_UNKNOWN,
    FACTOR_BOUNDARY_CRADLE_TO_GATE,
    METHOD_AVERAGE_DATA,
    METHOD_SUPPLIER_SPECIFIC,
)
from carbon_ledger.purchased_steel_confirmations import (
    ERROR_BOUNDARY_REQUIRED,
    ERROR_EVIDENCE_REQUIRED,
    ERROR_FACTOR_UNIT_REQUIRED,
    ERROR_FACTOR_VALUE_REQUIRED,
    ERROR_FACTOR_YEAR_REQUIRED,
    ERROR_FILE_HASH_REQUIRED,
    ERROR_GEOGRAPHY_REQUIRED,
    ERROR_IDENTITY_INCOMPLETE,
    ERROR_INBOUND_UNANSWERED,
    ERROR_METHOD_REQUIRED,
    ERROR_PRODUCT_REQUIRED,
    ERROR_REPORTING_YEAR_REQUIRED,
    ERROR_SUPPLIER_REQUIRED,
    ERROR_TRANSPORT_CONTROL_UNANSWERED,
    METHOD_UNDECIDED,
    activity_reporting_period_id,
    apply_purchased_steel_confirmations,
    build_confirmation,
    confirmation_identity,
    inclusion_from_mapping,
    is_blocked_transport_split,
    steel_confirmation_candidates,
    validate_confirmation,
)
from carbon_ledger.ui import state as ui_state
from carbon_ledger.ui.i18n import t

_FACTOR_UNITS = ("tCO2e/t", "kgCO2e/t", "tCO2e/kg", "kgCO2e/kg")
_ERROR_KEYS = {
    ERROR_METHOD_REQUIRED: "intake.steel.error.method",
    ERROR_IDENTITY_INCOMPLETE: "intake.steel.error.identity",
    ERROR_FILE_HASH_REQUIRED: "intake.steel.error.file",
    ERROR_INBOUND_UNANSWERED: "intake.steel.error.inbound",
    ERROR_TRANSPORT_CONTROL_UNANSWERED: "intake.steel.error.control",
    ERROR_SUPPLIER_REQUIRED: "intake.steel.error.supplier",
    ERROR_PRODUCT_REQUIRED: "intake.steel.error.product",
    ERROR_FACTOR_VALUE_REQUIRED: "intake.steel.error.factor_value",
    ERROR_FACTOR_UNIT_REQUIRED: "intake.steel.error.factor_unit",
    ERROR_BOUNDARY_REQUIRED: "intake.steel.error.boundary",
    ERROR_FACTOR_YEAR_REQUIRED: "intake.steel.error.factor_year",
    ERROR_EVIDENCE_REQUIRED: "intake.steel.error.evidence",
    ERROR_GEOGRAPHY_REQUIRED: "intake.steel.error.geography",
    ERROR_REPORTING_YEAR_REQUIRED: "intake.steel.error.reporting_year",
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text.lower() in {"nan", "<na>", "none", "nat"}:
        return ""
    return text


def pipeline_calculation_status_by_record(result: Any | None) -> dict[str, str]:
    """Map record_id → calculation_status from a pipeline result."""
    mapping: dict[str, str] = {}
    if result is None:
        return mapping
    calcs = getattr(result, "calculation_results", None)
    if calcs is None or getattr(calcs, "empty", True):
        return mapping
    if "record_id" not in calcs.columns or "calculation_status" not in calcs.columns:
        return mapping
    for _, row in calcs.iterrows():
        record_id = _text(row.get("record_id"))
        status = _text(row.get("calculation_status"))
        if record_id and status:
            mapping[record_id] = status
    return mapping


def attach_coverage_readiness(
    accepted: pd.DataFrame,
    *,
    calculation_status_by_record: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Attach the UI coverage bucket, splitting no-factor from unsupported."""
    if accepted is None or getattr(accepted, "empty", True):
        return pd.DataFrame()
    status_map = {
        str(key): str(value)
        for key, value in dict(calculation_status_by_record or {}).items()
    }
    rows = accepted.copy()
    buckets: list[str] = []
    for _, row in rows.iterrows():
        record_id = _text(row.get("record_id"))
        buckets.append(
            classify_activity_ui_readiness(
                activity_type=_text(row.get("activity_type")),
                fuel_subtype=_text(row.get("fuel_subtype")),
                process_use=_text(row.get("process_use")),
                activity_start=row.get("activity_start_date"),
                activity_end=row.get("activity_end_date"),
                calculation_method=_text(row.get("calculation_method")),
                supplier_name=_text(row.get("supplier_name")),
                steel_product_type=_text(row.get("steel_product_type")),
                product_identifier=_text(row.get("product_identifier")),
                emission_factor_value=row.get("emission_factor_value"),
                emission_factor_unit=_text(row.get("emission_factor_unit")),
                factor_boundary=_text(row.get("factor_boundary")),
                factor_year=row.get("factor_year"),
                factor_source_id=_text(row.get("factor_source_id")),
                evidence_reference=_text(row.get("evidence_reference")),
                source_document_id=_text(row.get("source_document_id")),
                includes_tier1_to_reporting_company_transport=row.get(
                    "includes_tier1_to_reporting_company_transport"
                ),
                factor_includes_tier1_to_reporting_company_transport=row.get(
                    "factor_includes_tier1_to_reporting_company_transport"
                ),
                tier1_to_reporting_company_transport_control=row.get(
                    "tier1_to_reporting_company_transport_control"
                ),
                factor_geography=_text(row.get("factor_geography")),
                calculation_status=status_map.get(
                    record_id, _text(row.get("calculation_status"))
                ),
            )
        )
    rows["_analysis_readiness"] = buckets
    return rows


def accepted_review_preview(
    rows: pd.DataFrame,
    *,
    lang: str,
    status: str,
    issue: str,
    calculation_status_by_record: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Customer-facing preview for one accepted-row coverage bucket."""
    from carbon_ledger.ui.view_models import (
        customer_schema_label,
        customer_site_display,
    )

    if rows is None or getattr(rows, "empty", True):
        return pd.DataFrame()
    preview = rows[
        [
            "activity_type",
            "activity_value",
            "unit",
            "activity_start_date",
            "activity_end_date",
            "site_id",
        ]
    ].copy()
    preview["activity_type"] = preview["activity_type"].map(
        lambda code: t(f"activity.{_text(code)}", lang)
    )
    preview["site_id"] = preview["site_id"].map(
        lambda value: customer_site_display(value, lang)
    )
    preview["status"] = status
    status_map = {
        str(key): str(value)
        for key, value in dict(calculation_status_by_record or {}).items()
    }
    issues: list[str] = []
    for _, row in rows.iterrows():
        activity_type = _text(row.get("activity_type"))
        if activity_type != "purchased_steel":
            issues.append(issue)
            continue
        record_id = _text(row.get("record_id"))
        calc_status = status_map.get(
            record_id, _text(row.get("calculation_status"))
        )
        if calc_status in {"no_factor_configured", "no_matching_factor"}:
            issues.append(t("intake.issue.steel_average_no_factor", lang))
            continue
        missing = purchased_steel_missing_fields(
            calculation_method=_text(row.get("calculation_method")),
            supplier_name=_text(row.get("supplier_name")),
            steel_product_type=_text(row.get("steel_product_type")),
            product_identifier=_text(row.get("product_identifier")),
            emission_factor_value=row.get("emission_factor_value"),
            emission_factor_unit=_text(row.get("emission_factor_unit")),
            factor_boundary=_text(row.get("factor_boundary")),
            factor_year=row.get("factor_year"),
            factor_source_id=_text(row.get("factor_source_id")),
            evidence_reference=_text(row.get("evidence_reference")),
            source_document_id=_text(row.get("source_document_id")),
            includes_tier1_to_reporting_company_transport=row.get(
                "includes_tier1_to_reporting_company_transport"
            ),
            factor_includes_tier1_to_reporting_company_transport=row.get(
                "factor_includes_tier1_to_reporting_company_transport"
            ),
            tier1_to_reporting_company_transport_control=row.get(
                "tier1_to_reporting_company_transport_control"
            ),
            factor_geography=_text(row.get("factor_geography")),
        )
        if missing == ("calculation_method",):
            issues.append(t("intake.issue.steel_no_method", lang))
            continue
        if missing == ("factor_includes_tier1_to_reporting_company_transport",):
            issues.append(t("intake.issue.steel_factor_inclusion", lang))
            continue
        if missing == ("tier1_to_reporting_company_transport_control",):
            issues.append(t("intake.issue.steel_transport_control", lang))
            continue
        if missing == (
            "blocked_tier1_inbound_transport_requires_category4_split",
        ):
            issues.append(
                t(
                    "explain.steel.blocked_tier1_inbound_transport_requires_category4_split",
                    lang,
                )
            )
            continue
        if missing == (
            "blocked_company_controlled_transport_requires_scope1_or2_split",
        ):
            issues.append(
                t(
                    "explain.steel.blocked_company_controlled_transport_requires_scope1_or2_split",
                    lang,
                )
            )
            continue
        if missing:
            labels = [customer_schema_label(name, lang) for name in missing]
            issues.append(
                t("intake.issue.steel_missing", lang, fields="、".join(labels))
            )
            continue
        issues.append(issue)
    preview["issue"] = issues
    return preview.rename(
        columns={
            "activity_type": t("intake.field.activity_type", lang),
            "activity_value": t("intake.field.activity_value", lang),
            "unit": t("intake.field.unit", lang),
            "activity_start_date": t("intake.field.start", lang),
            "activity_end_date": t("intake.field.end", lang),
            "site_id": t("intake.field.site_id", lang),
            "status": t("intake.col.status", lang),
            "issue": t("intake.col.issue", lang),
        }
    )


def _current_file_hash() -> str:
    return str(st.session_state.get(ui_state.STATE_INTAKE_FILE_HASH) or "").strip()


def _widget_key(
    prefix: str,
    *,
    file_hash: str,
    record_id: str,
    reporting_year: int,
    reporting_period_id: str,
) -> str:
    return (
        f"steel_{prefix}_{file_hash[:16]}_{record_id}_"
        f"{reporting_year}_{reporting_period_id}"
    )


def _radio_code(
    label: str,
    options: list[tuple[str, str]],
    *,
    key: str,
    default: str,
) -> str:
    labels = [item_label for _, item_label in options]
    lookup = {item_label: code for code, item_label in options}
    default_label = next(
        (item_label for code, item_label in options if code == default),
        labels[0],
    )
    index = labels.index(default_label) if default_label in labels else 0
    chosen = st.radio(label, labels, index=index, key=key)
    return lookup.get(str(chosen), options[0][0])


def accepted_activities_for_review(accepted: pd.DataFrame) -> pd.DataFrame:
    """Accepted rows plus current-file steel confirmation overlays."""
    return apply_purchased_steel_confirmations(
        accepted,
        ui_state.purchased_steel_confirmations_from_state(st.session_state),
        current_file_hash=_current_file_hash(),
    )


def render_steel_status_legend(lang: str) -> None:
    st.info(t("intake.legend.format_ok", lang))
    st.caption(t("intake.legend.needs_confirm", lang))
    st.caption(t("intake.legend.no_factor", lang))


def render_steel_confirm_flash(lang: str) -> None:
    flash = st.session_state.get(ui_state.STATE_STEEL_CONFIRM_FLASH) or {}
    kind = str(flash.get("kind") or "").strip()
    if not kind:
        return
    if kind == "category4_split":
        st.warning(
            t(
                "explain.steel.blocked_tier1_inbound_transport_requires_category4_split",
                lang,
            )
        )
    elif kind == "scope1_or2_split":
        st.warning(
            t(
                "explain.steel.blocked_company_controlled_transport_requires_scope1_or2_split",
                lang,
            )
        )
    elif kind == "incomplete":
        st.error(t("intake.steel.error.incomplete", lang))
    st.session_state[ui_state.STATE_STEEL_CONFIRM_FLASH] = None


def render_steel_pipeline_outcome(lang: str, pipeline_result: Any | None) -> None:
    """Show no-factor copy only after the current pipeline result exists."""
    if pipeline_result is None:
        return
    status_map = pipeline_calculation_status_by_record(pipeline_result)
    activities = getattr(pipeline_result, "activity_records_accepted", None)
    if activities is None or getattr(activities, "empty", True):
        return
    for _, row in activities.iterrows():
        if _text(row.get("activity_type")) != "purchased_steel":
            continue
        record_id = _text(row.get("record_id"))
        if status_map.get(record_id) not in {
            "no_factor_configured",
            "no_matching_factor",
        }:
            continue
        method = _text(row.get("calculation_method"))
        if method not in {METHOD_AVERAGE_DATA, METHOD_SUPPLIER_SPECIFIC}:
            continue
        st.warning(t("intake.issue.steel_average_no_factor", lang))
        return


def render_purchased_steel_confirmation_forms(
    activities: pd.DataFrame,
    lang: str,
    *,
    calculation_status_by_record: Mapping[str, str] | None = None,
) -> None:
    candidates = steel_confirmation_candidates(
        activities,
        calculation_status_by_record=calculation_status_by_record,
    )
    if candidates.empty:
        return
    st.markdown(f"**{t('intake.steel.form.title', lang)}**")
    st.caption(t("intake.steel.form.help", lang))
    file_hash = _current_file_hash()
    existing = {
        item.identity(): item
        for item in ui_state.purchased_steel_confirmations_from_state(
            st.session_state
        )
    }
    status_map = {
        str(key): str(value)
        for key, value in dict(calculation_status_by_record or {}).items()
    }
    for _, row in candidates.iterrows():
        record_id = _text(row.get("record_id"))
        year = reporting_year_from_activity(row)
        period_id = activity_reporting_period_id(row)
        if not record_id or year is None or not period_id:
            with st.expander(_text(row.get("activity_type")) or record_id):
                st.error(t("intake.steel.error.identity", lang))
            continue
        stored = existing.get(
            confirmation_identity(file_hash, record_id, year, period_id)
        )
        calc_status = status_map.get(
            record_id, _text(row.get("calculation_status"))
        )
        title = (
            f"{t('activity.purchased_steel', lang)} · {record_id} · "
            f"{row.get('activity_value')} {row.get('unit') or ''}"
        ).strip()
        if calc_status in {"no_factor_configured", "no_matching_factor"}:
            title = f"{t('intake.steel.edit', lang)} · {title}"
        with st.expander(title, expanded=True):
            if calc_status in {"no_factor_configured", "no_matching_factor"}:
                pending_key = "intake.issue.steel_candidate_pending_review"
                no_factor_key = "intake.issue.steel_average_no_factor"
                from carbon_ledger.steel_factor_catalog import (
                    pending_steel_candidates_for_product,
                )

                product = _text(row.get("steel_product_type"))
                if stored is not None:
                    product = (
                        _text(getattr(stored, "steel_product_type", "")) or product
                    )
                if not pending_steel_candidates_for_product(product).empty:
                    st.warning(t(pending_key, lang))
                else:
                    st.warning(t(no_factor_key, lang))
                st.caption(t("intake.steel.edit.help", lang))
            _render_one_form(
                row=row,
                lang=lang,
                file_hash=file_hash,
                record_id=record_id,
                reporting_year=year,
                reporting_period_id=period_id,
                stored=stored,
            )


def render_purchased_steel_coverage_review(
    accepted: pd.DataFrame,
    lang: str,
    *,
    calculation_status_by_record: Mapping[str, str] | None = None,
    pipeline_result: Any | None = None,
) -> pd.DataFrame:
    """Classify accepted rows and render the steel confirmation coverage block.

    Tests call this renderer with prepared session state / analysis results so
    the average-data no-factor path actually executes Streamlit widgets.
    """
    status_map = dict(calculation_status_by_record or {})
    if not status_map:
        status_map = pipeline_calculation_status_by_record(pipeline_result)
    classified = attach_coverage_readiness(
        accepted, calculation_status_by_record=status_map
    )
    render_steel_status_legend(lang)
    render_steel_confirm_flash(lang)
    render_steel_pipeline_outcome(lang, pipeline_result)
    if classified.empty:
        return classified
    ready_rows = classified[
        classified["_analysis_readiness"] == READINESS_READY
    ].copy()
    needs_confirm = classified[
        classified["_analysis_readiness"] == READINESS_NEEDS_CONFIRM
    ].copy()
    no_factor_rows = classified[
        classified["_analysis_readiness"] == READINESS_NO_MATCHING_FACTOR
    ].copy()
    unsupported_rows = classified[
        classified["_analysis_readiness"] == READINESS_UNSUPPORTED
    ].copy()
    render_purchased_steel_confirmation_forms(
        classified,
        lang,
        calculation_status_by_record=status_map,
    )
    tab_ok, tab_fix, tab_no_factor, tab_unsupported = st.tabs(
        [
            t("intake.result_accepted", lang),
            t("intake.result_needs_confirm", lang),
            t("intake.result_no_factor", lang),
            t("intake.result_unsupported", lang),
        ]
    )
    with tab_ok:
        if not ready_rows.empty:
            st.dataframe(
                accepted_review_preview(
                    ready_rows,
                    lang=lang,
                    status=t("intake.result_accepted", lang),
                    issue="—",
                    calculation_status_by_record=status_map,
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption(t("intake.empty.ready", lang))
    with tab_fix:
        if not needs_confirm.empty:
            st.dataframe(
                accepted_review_preview(
                    needs_confirm,
                    lang=lang,
                    status=t("intake.result_needs_confirm", lang),
                    issue=t("intake.issue.context_required", lang),
                    calculation_status_by_record=status_map,
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption(t("intake.empty.needs_confirm", lang))
    with tab_no_factor:
        if not no_factor_rows.empty:
            st.dataframe(
                accepted_review_preview(
                    no_factor_rows,
                    lang=lang,
                    status=t("intake.result_no_factor", lang),
                    issue=t("intake.issue.steel_average_no_factor", lang),
                    calculation_status_by_record=status_map,
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption(t("intake.empty.no_factor", lang))
    with tab_unsupported:
        if not unsupported_rows.empty:
            unsupported_names = sorted(
                {
                    t(f"activity.{code}", lang)
                    for code in unsupported_rows["activity_type"].astype(str)
                }
            )
            st.info(
                t(
                    "intake.unsupported.summary",
                    lang,
                    names="、".join(unsupported_names),
                )
            )
            st.dataframe(
                accepted_review_preview(
                    unsupported_rows,
                    lang=lang,
                    status=t("intake.result_unsupported", lang),
                    issue=t("intake.issue.unsupported_activity", lang),
                    calculation_status_by_record=status_map,
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption(t("intake.empty.unsupported", lang))
    return classified


def _render_one_form(
    *,
    row: pd.Series,
    lang: str,
    file_hash: str,
    record_id: str,
    reporting_year: int,
    reporting_period_id: str,
    stored: Any,
) -> None:
    error_box = st.empty()
    key_kw = {
        "file_hash": file_hash,
        "record_id": record_id,
        "reporting_year": reporting_year,
        "reporting_period_id": reporting_period_id,
    }
    quantity = row.get("activity_value")
    unit = _text(row.get("unit"))
    st.markdown(f"**{t('intake.steel.form.record', lang)}**")
    st.code(record_id)
    st.caption(
        t(
            "intake.steel.form.quantity",
            lang,
            quantity=quantity,
            unit=unit or "—",
        )
    )
    st.caption(
        t(
            "intake.steel.form.year",
            lang,
            year=reporting_year,
            period=reporting_period_id,
        )
    )
    st.caption(t("intake.steel.form.no_scope", lang))
    st.info(t("intake.steel.form.transport_help", lang))
    method_default = METHOD_UNDECIDED
    if stored is not None:
        method_default = stored.calculation_method or METHOD_UNDECIDED
    elif _text(row.get("calculation_method")) in {
        METHOD_SUPPLIER_SPECIFIC,
        METHOD_AVERAGE_DATA,
    }:
        method_default = _text(row.get("calculation_method"))
    method = _radio_code(
        t("intake.field.calculation_method", lang),
        [
            (METHOD_UNDECIDED, t("intake.steel.method.undecided", lang)),
            (
                METHOD_SUPPLIER_SPECIFIC,
                t("intake.steel.method.supplier_specific", lang),
            ),
            (METHOD_AVERAGE_DATA, t("intake.steel.method.average_data", lang)),
        ],
        key=_widget_key("method", **key_kw),
        default=method_default,
    )
    inclusion_default = inclusion_from_mapping(
        {
            "factor_includes_tier1_to_reporting_company_transport": getattr(
                stored,
                "factor_includes_tier1_to_reporting_company_transport",
                "",
            ),
            "includes_tier1_to_reporting_company_transport": (
                getattr(
                    stored,
                    "includes_tier1_to_reporting_company_transport",
                    "",
                )
                or row.get("includes_tier1_to_reporting_company_transport")
            ),
        }
    )
    if stored is None and not inclusion_default:
        inclusion_default = inclusion_from_mapping(row.to_dict())
    inclusion = _radio_code(
        t("intake.field.factor_includes_inbound_transport", lang),
        [
            ("", t("intake.steel.answer.unconfirmed", lang)),
            ("false", t("intake.steel.answer.excluded", lang)),
            ("true", t("intake.steel.answer.included", lang)),
        ],
        key=_widget_key("inbound", **key_kw),
        default=inclusion_default,
    )
    control_default = CONTROL_UNKNOWN
    stored_control = _text(
        getattr(stored, "tier1_to_reporting_company_transport_control", "")
        or row.get("tier1_to_reporting_company_transport_control")
    )
    if stored_control in {
        CONTROL_UNKNOWN,
        CONTROL_REPORTING_COMPANY,
        CONTROL_THIRD_PARTY,
        CONTROL_NOT_APPLICABLE,
    }:
        control_default = stored_control
    control = CONTROL_NOT_APPLICABLE
    if inclusion == "true":
        control = _radio_code(
            t("intake.field.transport_control", lang),
            [
                (CONTROL_UNKNOWN, t("intake.steel.answer.unconfirmed", lang)),
                (
                    CONTROL_REPORTING_COMPANY,
                    t("intake.steel.control.reporting_company", lang),
                ),
                (
                    CONTROL_THIRD_PARTY,
                    t("intake.steel.control.third_party", lang),
                ),
            ],
            key=_widget_key("control", **key_kw),
            default=(
                CONTROL_UNKNOWN
                if control_default == CONTROL_NOT_APPLICABLE
                else control_default
            ),
        )
    st.caption(t("intake.steel.form.pre_tier1_help", lang))
    if inclusion == "":
        st.warning(t("intake.issue.steel_factor_inclusion", lang))
    elif inclusion == "true" and control in {
        CONTROL_UNKNOWN,
        CONTROL_NOT_APPLICABLE,
        "",
    }:
        st.warning(t("intake.issue.steel_transport_control", lang))
    elif inclusion == "true" and control == CONTROL_THIRD_PARTY:
        st.warning(
            t(
                "explain.steel.blocked_tier1_inbound_transport_requires_category4_split",
                lang,
            )
        )
    elif inclusion == "true" and control == CONTROL_REPORTING_COMPANY:
        st.warning(
            t(
                "explain.steel.blocked_company_controlled_transport_requires_scope1_or2_split",
                lang,
            )
        )
    fields: dict[str, Any] = {}
    if method == METHOD_SUPPLIER_SPECIFIC:
        fields = _supplier_fields(row, stored, lang, key_kw)
    elif method == METHOD_AVERAGE_DATA:
        fields = _average_fields(
            row, stored, lang, key_kw, reporting_year=reporting_year
        )
        st.caption(t("intake.steel.average.help", lang))
    elif method == METHOD_UNDECIDED:
        st.caption(t("intake.steel.method.undecided_help", lang))
    save_clicked = st.button(
        t("intake.steel.save", lang),
        type="primary",
        key=_widget_key("save", **key_kw),
    )
    if not save_clicked:
        return
    _handle_save(
        lang=lang,
        error_box=error_box,
        file_hash=file_hash,
        record_id=record_id,
        reporting_year=reporting_year,
        reporting_period_id=reporting_period_id,
        calculation_method=method,
        inclusion=inclusion,
        control=control,
        fields=fields,
    )


def _supplier_fields(
    row: pd.Series,
    stored: Any,
    lang: str,
    key_kw: dict[str, Any],
) -> dict[str, Any]:
    def current(name: str) -> str:
        if stored is not None:
            value = _text(getattr(stored, name, ""))
            if value:
                return value
        return _text(row.get(name))

    supplier_name = st.text_input(
        t("intake.field.supplier_name", lang),
        value=current("supplier_name"),
        key=_widget_key("supplier", **key_kw),
    )
    steel_product_type = st.text_input(
        t("intake.field.steel_product_type", lang),
        value=current("steel_product_type"),
        key=_widget_key("product_type", **key_kw),
    )
    product_identifier = st.text_input(
        t("intake.field.product_identifier", lang),
        value=current("product_identifier"),
        key=_widget_key("product_id", **key_kw),
    )
    emission_factor_value = st.text_input(
        t("intake.field.emission_factor_value", lang),
        value=current("emission_factor_value"),
        key=_widget_key("factor_value", **key_kw),
    )
    unit_labels = [t("intake.steel.answer.unconfirmed", lang), *_FACTOR_UNITS]
    unit_default = current("emission_factor_unit")
    unit_index = (
        unit_labels.index(unit_default) if unit_default in unit_labels else 0
    )
    chosen_unit = st.selectbox(
        t("intake.field.emission_factor_unit", lang),
        unit_labels,
        index=unit_index,
        key=_widget_key("factor_unit", **key_kw),
    )
    emission_factor_unit = (
        ""
        if str(chosen_unit) == t("intake.steel.answer.unconfirmed", lang)
        else str(chosen_unit)
    )
    factor_boundary = _radio_code(
        t("intake.field.factor_boundary", lang),
        [
            ("", t("intake.steel.answer.unconfirmed", lang)),
            (
                FACTOR_BOUNDARY_CRADLE_TO_GATE,
                t("intake.steel.boundary.cradle_to_gate", lang),
            ),
        ],
        key=_widget_key("boundary", **key_kw),
        default=current("factor_boundary"),
    )
    return {
        "supplier_name": supplier_name,
        "steel_product_type": steel_product_type,
        "product_identifier": product_identifier,
        "emission_factor_value": emission_factor_value,
        "emission_factor_unit": emission_factor_unit,
        "factor_boundary": factor_boundary,
        "factor_year": st.text_input(
            t("intake.field.factor_year", lang),
            value=current("factor_year"),
            key=_widget_key("factor_year", **key_kw),
        ),
        "factor_source_id": st.text_input(
            t("intake.field.factor_source_id", lang),
            value=current("factor_source_id"),
            key=_widget_key("source_id", **key_kw),
        ),
        "evidence_reference": st.text_input(
            t("intake.field.evidence_reference", lang),
            value=current("evidence_reference"),
            key=_widget_key("evidence", **key_kw),
        ),
        "source_document_id": st.text_input(
            t("intake.field.source_document_id", lang),
            value=_text(getattr(stored, "source_document_id", "")),
            key=_widget_key("source_doc", **key_kw),
        ),
    }


def _average_fields(
    row: pd.Series,
    stored: Any,
    lang: str,
    key_kw: dict[str, Any],
    *,
    reporting_year: int,
) -> dict[str, Any]:
    def current(name: str) -> str:
        if stored is not None:
            value = _text(getattr(stored, name, ""))
            if value:
                return value
        return _text(row.get(name))

    st.text_input(
        t("intake.steel.field.reporting_year", lang),
        value=str(reporting_year),
        disabled=True,
        key=_widget_key("reporting_year", **key_kw),
    )
    from carbon_ledger.cfp_p_02 import is_generic_steel_label
    from carbon_ledger.steel_factor_catalog import (
        UNDECIDED_PRODUCT_TYPE,
        display_factor_rows,
        matchable_average_factor_rows,
        pending_steel_candidates_for_product,
        steel_product_type_choices,
    )

    choices = list(steel_product_type_choices())
    current_product = current("steel_product_type")
    if not current_product or is_generic_steel_label(current_product):
        current_product = UNDECIDED_PRODUCT_TYPE
    if current_product not in choices:
        choices = [current_product, *choices]
    product = st.selectbox(
        t("intake.field.steel_product_type", lang),
        options=choices,
        index=choices.index(current_product),
        key=_widget_key("avg_product", **key_kw),
    )
    product_identity = (
        ""
        if (
            not product
            or is_generic_steel_label(product)
            or product == UNDECIDED_PRODUCT_TYPE
        )
        else str(product)
    )
    matchable = matchable_average_factor_rows(
        steel_product_type=product_identity,
        reporting_year=reporting_year,
    )
    pending = pending_steel_candidates_for_product(product_identity)
    displayed = display_factor_rows(matchable)
    if displayed:
        st.caption(t("intake.steel.catalog.factors", lang))
        st.table(
            [
                {
                    t("intake.steel.catalog.product", lang): item.get(
                        "official_name"
                    )
                    or item["steel_product_type"],
                    t("intake.steel.catalog.value", lang): (
                        f"{item['factor_value']} {item['factor_unit']}"
                    ),
                    t("intake.steel.catalog.declared_unit", lang): (
                        item.get("publisher") or item.get("declared_unit")
                    ),
                    t("intake.steel.field.factor_year", lang): item["factor_year"],
                    t("intake.steel.catalog.version", lang): item["factor_version"],
                    t("intake.steel.catalog.boundary", lang): item["factor_boundary"],
                    t("intake.steel.catalog.geography", lang): item["geography"],
                    t("intake.steel.catalog.source", lang): item["source_url"],
                    t("intake.steel.catalog.period", lang): item[
                        "applicability_period"
                    ],
                    t("intake.steel.catalog.secondary", lang): item[
                        "is_secondary_or_proxy"
                    ],
                }
                for item in displayed
            ]
        )
    elif not pending.empty:
        st.warning(t("intake.issue.steel_candidate_pending_review", lang))
    elif product and product != UNDECIDED_PRODUCT_TYPE:
        st.warning(t("intake.issue.steel_average_no_factor", lang))
    geos = sorted({item["geography"] for item in displayed if item["geography"]})
    techs = sorted({item["technology"] for item in displayed if item["technology"]})
    geography = current("factor_geography")
    if len(geos) == 1:
        geography = geos[0]
        st.text_input(
            t("intake.field.factor_geography", lang),
            value=geography,
            disabled=True,
            key=_widget_key("geography", **key_kw),
        )
    elif geos:
        if geography not in geos:
            geography = geos[0]
        geography = st.selectbox(
            t("intake.field.factor_geography", lang),
            options=geos,
            index=geos.index(geography),
            key=_widget_key("geography", **key_kw),
        )
    technology = current("technology")
    if len(techs) == 1:
        technology = techs[0]
    elif techs:
        if technology not in techs:
            technology = techs[0]
        technology = st.selectbox(
            t("intake.steel.field.technology", lang),
            options=techs,
            index=techs.index(technology),
            key=_widget_key("technology", **key_kw),
        )
    return {
        "steel_product_type": product_identity,
        "product_identifier": product_identity,
        "factor_geography": geography,
        "technology": technology,
    }


def _handle_save(
    *,
    lang: str,
    error_box: Any,
    file_hash: str,
    record_id: str,
    reporting_year: int,
    reporting_period_id: str,
    calculation_method: str,
    inclusion: str,
    control: str,
    fields: dict[str, Any],
) -> None:
    confirmation = build_confirmation(
        file_hash=file_hash,
        record_id=record_id,
        reporting_year=reporting_year,
        reporting_period_id=reporting_period_id,
        calculation_method=calculation_method,
        factor_includes_tier1_to_reporting_company_transport=inclusion,
        includes_tier1_to_reporting_company_transport=inclusion,
        tier1_to_reporting_company_transport_control=control,
        **fields,
    )
    errors = validate_confirmation(confirmation, current_file_hash=file_hash)
    if errors:
        first = errors[0]
        error_box.error(
            t(_ERROR_KEYS.get(first, "intake.steel.error.incomplete"), lang)
        )
        st.session_state[ui_state.STATE_STEEL_CONFIRM_FLASH] = {
            "kind": "incomplete",
            "record_id": record_id,
        }
        return
    ui_state.save_purchased_steel_confirmation_in_session(
        st.session_state, confirmation
    )
    if is_blocked_transport_split(inclusion, control):
        kind = (
            "category4_split"
            if control == CONTROL_THIRD_PARTY
            else "scope1_or2_split"
        )
    else:
        kind = "saved"
    st.session_state[ui_state.STATE_STEEL_CONFIRM_FLASH] = {
        "kind": kind,
        "record_id": record_id,
    }
    ui_state.clear_analysis_result(st.session_state)
    ui_state.request_run_uploaded_analysis(st.session_state)
    st.rerun()
