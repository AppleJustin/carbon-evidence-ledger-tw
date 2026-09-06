"""Data Intake — Phase 9A structured company-file wizard."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from carbon_ledger.domain import ACTIVITY_TYPES, SUPPORTED_UNITS
from carbon_ledger.intake import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    READINESS_NEEDS_CONFIRM,
    READINESS_NO_MATCHING_FACTOR,
    READINESS_READY,
    READINESS_UNSUPPORTED,
    ColumnMapping,
    FieldSuggestion,
    IntakeError,
    IntakeMetadata,
    blank_template_csv_bytes,
    blank_template_xlsx_bytes,
    default_value_maps,
    detect_header_row,
    extract_diesel_vehicle_context_from_text,
    extract_natural_gas_subtype_from_text,
    fuel_subtype_source_column,
    intake_validation_percent,
    list_xlsx_sheet_names,
    load_raw_tabular_frame,
    parse_uploaded_table,
    rank_xlsx_worksheets,
    reference_only_columns,
    suggest_column_mapping_with_confidence,
    summarize_pre_analysis_readiness,
    worksheet_detection_labels,
    year_month_transform_preview,
)
from carbon_ledger.intake_exceptions import (
    ISSUE_HELD_DIESEL_CONTEXT,
    ISSUE_HELD_ELEC_CONTEXT,
    ISSUE_HELD_NG_CONTEXT,
    ISSUE_HELD_PENDING_ACTUAL_HV,
    KIND_ACTIVITY_VALUE,
    KIND_COLUMN,
    KIND_CONTEXT,
    KIND_DATES,
    KIND_UNIT_VALUE,
    KIND_YEAR_MONTH,
    NG_GROUP_SINGLE,
    NG_VALUE_PENDING_HV,
    IntakeException,
    apply_exception,
    can_validate,
    confirmation_timeline,
    initialize_committed,
    list_exceptions,
    mapping_from_committed,
    summary_counts,
)
from carbon_ledger.intake_mapping_memory import (
    EVENT_CUSTOMER_CONFIRMED,
    EVENT_CUSTOMER_CORRECTED,
    EVENT_MARKED_UNKNOWN,
    EVENT_MEMORY_APPLIED,
    EVENT_MEMORY_OFFERED,
    append_provenance_event,
    customer_history_rows,
    document_id_for_hash,
    lookup_remembered_mapping,
    overlay_remembered_committed,
    record_system_suggestions,
    structural_fingerprint,
)
from carbon_ledger.potential_duplicates import (
    DECISION_EXCLUDE_DUPLICATES,
    DECISION_KEEP_ALL,
    decide_potential_duplicate_group,
    decision_to_map_payload,
    groups_from_intake,
    unresolved_potential_duplicate_groups,
)
from carbon_ledger.ui.components import (
    inject_design_system,
    render_kpi_row,
    render_section_header,
)
from carbon_ledger.ui.i18n import t
from carbon_ledger.ui.intake_validation import (
    clear_intake_validation_lock,
    execute_intake_validation,
    recover_stale_intake_validation,
)
from carbon_ledger.ui.purchased_steel_confirmation import (
    accepted_activities_for_review,
    accepted_review_preview,
    attach_coverage_readiness,
    pipeline_calculation_status_by_record,
    render_purchased_steel_confirmation_forms,
    render_steel_confirm_flash,
    render_steel_pipeline_outcome,
    render_steel_status_legend,
)
from carbon_ledger.ui.refrigerant_boundary_form import (
    render_confirmation_flash,
    render_refrigerant_boundary_confirmation,
)
from carbon_ledger.ui.state import (
    STATE_INTAKE_BYTES,
    STATE_INTAKE_COMMITTED,
    STATE_INTAKE_DUPLICATE_REVIEW,
    STATE_INTAKE_EXCEPTION_CURSOR,
    STATE_INTAKE_FILE_HASH,
    STATE_INTAKE_FILE_NAME,
    STATE_INTAKE_HEADER_CONFIRMED,
    STATE_INTAKE_HEADER_ROW,
    STATE_INTAKE_MAPPING,
    STATE_INTAKE_MEMORY_APPLIED,
    STATE_INTAKE_MEMORY_CHOICE,
    STATE_INTAKE_MEMORY_OFFERED,
    STATE_INTAKE_METADATA,
    STATE_INTAKE_RESULT,
    STATE_INTAKE_SHEET,
    STATE_INTAKE_SHEET_CONFIRMED,
    STATE_INTAKE_SHOW_DUPLICATE_REVIEW,
    STATE_INTAKE_SHOW_MAPPING_EDITOR,
    STATE_INTAKE_STEP,
    STATE_INTAKE_TABLE,
    STATE_INTAKE_VALIDATION_ERROR,
    STATE_INTAKE_VALIDATION_REQUESTED,
    STATE_INTAKE_VALIDATION_RUNNING,
    STATE_INTAKE_YEAR_MONTH_CONFIRMED,
    STATE_RUN_UPLOADED_REQUEST,
    clear_analysis_result,
    clear_duplicate_review_state,
    clear_intake_state,
    confirmed_company_ubn,
    duplicate_review_decisions_from_state,
    get_current_result,
    get_facility_master_mapping,
    get_language,
    is_uploaded_analysis,
)
from carbon_ledger.ui.tutorial import (
    note_onboarding_upload_file,
    onboarding_running,
    onboarding_target,
    record_onboarding_open_questions,
)
from carbon_ledger.ui.view_models import (
    beginner_result_summary,
    customer_schema_label,
    customer_site_display,
    should_show_unresolved_cta,
)

inject_design_system()
lang = get_language(st.session_state)
recover_stale_intake_validation(st.session_state)

# Emissions Data & Calculations workspace: upload is the default landing task.
st.markdown(
    f"""
    <p class="cel-page-kicker">{t("nav.evidence", lang)}</p>
    <h1 class="cel-page-title">{t("ev.landing.title", lang)}</h1>
    <p class="cel-page-sub">{t("ev.landing.body", lang)}</p>
    """,
    unsafe_allow_html=True,
)

QUALITY_OPTIONS = [
    ("unknown", t("intake.quality.unknown", lang)),
    ("primary", t("intake.quality.primary", lang)),
    ("secondary", t("intake.quality.secondary", lang)),
    ("estimated", t("intake.quality.estimated", lang)),
]
QUALITY_LABEL_TO_CODE = {label: code for code, label in QUALITY_OPTIONS}

ACTIVITY_OPTIONS = [t("intake.choose", lang)] + [
    t(f"activity.{code}", lang) for code in ACTIVITY_TYPES
]
ACTIVITY_LABEL_TO_CODE = {
    t(f"activity.{code}", lang): code for code in ACTIVITY_TYPES
}

UNIT_OPTIONS = [t("intake.choose", lang)] + list(SUPPORTED_UNITS)

_TEMPLATE_XLSX_BYTES: bytes | None = None
_TEMPLATE_XLSX_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _template_download_payload() -> tuple[bytes, str, str]:
    """Stable bytes for st.download_button across Streamlit reruns."""
    global _TEMPLATE_XLSX_BYTES
    if _TEMPLATE_XLSX_BYTES is None:
        try:
            _TEMPLATE_XLSX_BYTES = blank_template_xlsx_bytes()
        except Exception:  # noqa: BLE001
            return (
                blank_template_csv_bytes(),
                "carbon_evidence_template.csv",
                "text/csv",
            )
    return (
        _TEMPLATE_XLSX_BYTES,
        "carbon_evidence_template.xlsx",
        _TEMPLATE_XLSX_MIME,
    )


INTERPRET_FIELD_ORDER = (
    "activity_type",
    "activity_value",
    "unit",
    "site_id",
    "year_month",
    "activity_start_date",
    "activity_end_date",
    "fuel_subtype",
)


def _step_indicator(active: int) -> None:
    labels = [
        t("intake.step1", lang),
        t("intake.step2", lang),
        t("intake.step3", lang),
        t("intake.step4", lang),
    ]
    parts: list[str] = []
    for index, label in enumerate(labels, start=1):
        escaped = html_escape(label)
        if index < active:
            parts.append(f"✓ {escaped}")
        elif index == active:
            parts.append(f"<strong>● {escaped}</strong>")
        else:
            parts.append(f"○ {escaped}")
    st.markdown(
        f'<p class="cel-intake-stepper">{" · ".join(parts)}</p>',
        unsafe_allow_html=True,
    )


def _render_completed_step_summary(
    *,
    step_no: int,
    title: str,
    detail: str,
    edit_key: str,
    target_step: int,
    compact: bool = False,
    disabled: bool = False,
) -> None:
    if compact:
        cols = st.columns([5, 1])
        with cols[0]:
            st.markdown(
                f'<p class="cel-completed-step-compact">'
                f"✓ {html_escape(title)} · {html_escape(detail)}</p>",
                unsafe_allow_html=True,
            )
        with cols[1]:
            if st.button(
                t("intake.nav.edit", lang),
                key=edit_key,
                disabled=disabled,
            ):
                st.session_state[STATE_INTAKE_STEP] = target_step
                if target_step <= 2:
                    st.session_state[STATE_INTAKE_RESULT] = None
                    clear_duplicate_review_state(st.session_state)
                    st.session_state[STATE_INTAKE_SHOW_MAPPING_EDITOR] = False
                _ = step_no
                st.rerun()
        return
    st.markdown(
        f"""
        <div class="cel-card-secondary">
          <p class="cel-card-title">✓ {html_escape(title)}</p>
          <p class="cel-card-reason">{html_escape(detail)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(
        t("intake.nav.edit", lang),
        key=edit_key,
        disabled=disabled,
    ):
        st.session_state[STATE_INTAKE_STEP] = target_step
        if target_step <= 2:
            st.session_state[STATE_INTAKE_RESULT] = None
            clear_duplicate_review_state(st.session_state)
            st.session_state[STATE_INTAKE_SHOW_MAPPING_EDITOR] = False
        if target_step == 1:
            # Keep bytes; user may replace via uploader.
            pass
        _ = step_no
        st.rerun()


HELD_ISSUE_CODES = frozenset(
    {
        ISSUE_HELD_NG_CONTEXT,
        ISSUE_HELD_DIESEL_CONTEXT,
        ISSUE_HELD_ELEC_CONTEXT,
        ISSUE_HELD_PENDING_ACTUAL_HV,
    }
)


def _accepted_readiness_rows(accepted: pd.DataFrame) -> pd.DataFrame:
    """Attach the UI coverage bucket to format-valid rows."""
    pipeline = get_current_result(st.session_state)
    return attach_coverage_readiness(
        accepted,
        calculation_status_by_record=pipeline_calculation_status_by_record(
            pipeline
        ),
    )


def _accepted_review_preview(
    rows: pd.DataFrame,
    *,
    status: str,
    issue: str,
) -> pd.DataFrame:
    """Customer-facing preview for one accepted-row coverage bucket."""
    pipeline = get_current_result(st.session_state)
    return accepted_review_preview(
        rows,
        lang=lang,
        status=status,
        issue=issue,
        calculation_status_by_record=pipeline_calculation_status_by_record(
            pipeline
        ),
    )


def html_escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _duplicate_context_label(group: Any) -> str:
    fuel = str(getattr(group, "fuel_subtype", "") or "").strip()
    process = str(getattr(group, "process_use", "") or "").strip()
    parts: list[str] = []
    if fuel and fuel not in {"not_applicable", "unknown"}:
        parts.append(fuel)
    if process in {"company_vehicle"}:
        parts.append(t("intake.diesel_company_vehicle", lang))
    elif process in {"general_factory", "forging"}:
        parts.append(t("intake.electricity_enterprise", lang))
    elif process and process not in {"not_applicable", "unknown", "heat_treatment"}:
        parts.append(process)
    return "／".join(parts) if parts else "—"


def _sync_duplicate_review_from_widgets(groups: list[Any]) -> None:
    existing = dict(st.session_state.get(STATE_INTAKE_DUPLICATE_REVIEW) or {})
    review_session = "ui_intake"
    meta = st.session_state.get(STATE_INTAKE_METADATA)
    if meta is not None and getattr(meta, "intake_run_id", None):
        review_session = str(meta.intake_run_id)
    now = pd.Timestamp.now(tz="UTC").isoformat()
    updated: dict[str, Any] = {}
    keep_label = t("intake.dup.keep_all", lang)
    exclude_label = t("intake.dup.exclude", lang)
    for group in groups:
        key = f"intake_dup_decision_{group.group_id}"
        choice = st.session_state.get(key)
        if choice == keep_label:
            decision_code = DECISION_KEEP_ALL
        elif choice == exclude_label:
            decision_code = DECISION_EXCLUDE_DUPLICATES
        else:
            continue
        previous = existing.get(group.group_id) or {}
        reviewed_at = now
        if (
            isinstance(previous, dict)
            and previous.get("decision") == decision_code
            and previous.get("reviewed_at")
        ):
            reviewed_at = str(previous.get("reviewed_at"))
        decided = decide_potential_duplicate_group(
            group,
            decision_code,
            reviewed_at=reviewed_at,
            review_session=review_session,
        )
        updated[group.group_id] = decision_to_map_payload(decided)
    st.session_state[STATE_INTAKE_DUPLICATE_REVIEW] = updated


def _render_potential_duplicate_review(intake_result: Any) -> bool:
    """Show lookalike review. Return True when analysis may continue."""
    groups = list(groups_from_intake(intake_result))
    if not groups:
        return True
    decisions = duplicate_review_decisions_from_state(st.session_state)
    unresolved = unresolved_potential_duplicate_groups(groups, decisions)
    st.warning(t("intake.dup.title", lang))
    st.markdown(t("intake.dup.body", lang, count=len(groups)))
    if st.button(t("intake.dup.review", lang), key="intake_dup_open_review"):
        st.session_state[STATE_INTAKE_SHOW_DUPLICATE_REVIEW] = True
    show = bool(st.session_state.get(STATE_INTAKE_SHOW_DUPLICATE_REVIEW))
    if show:
        st.session_state[STATE_INTAKE_SHOW_DUPLICATE_REVIEW] = True
        keep_label = t("intake.dup.keep_all", lang)
        exclude_label = t("intake.dup.exclude", lang)
        for index, group in enumerate(groups, start=1):
            st.markdown(f"**{t('intake.dup.group', lang, n=index)}**")
            preview = pd.DataFrame(
                {
                    t("intake.dup.file_row", lang): list(group.source_rows),
                    t("intake.field.activity_type", lang): [
                        t(f"activity.{group.activity_type}", lang)
                    ]
                    * len(group.record_ids),
                    t("intake.field.activity_value", lang): [
                        group.activity_value
                    ]
                    * len(group.record_ids),
                    t("intake.field.unit", lang): [group.unit]
                    * len(group.record_ids),
                    t("intake.field.start", lang): [
                        group.activity_start_date
                    ]
                    * len(group.record_ids),
                    t("intake.field.end", lang): [group.activity_end_date]
                    * len(group.record_ids),
                    t("intake.field.site_id", lang): [
                        customer_site_display(group.site_id, lang)
                    ]
                    * len(group.record_ids),
                    t("intake.dup.context", lang): [
                        _duplicate_context_label(group)
                    ]
                    * len(group.record_ids),
                }
            )
            st.dataframe(preview, hide_index=True, width="stretch")
            st.radio(
                t("intake.dup.title", lang),
                options=[keep_label, exclude_label],
                index=None,
                key=f"intake_dup_decision_{group.group_id}",
                label_visibility="collapsed",
            )
        _sync_duplicate_review_from_widgets(groups)
        decisions = duplicate_review_decisions_from_state(st.session_state)
        unresolved = unresolved_potential_duplicate_groups(groups, decisions)
        if not unresolved:
            st.success(t("intake.dup.confirmed", lang))
            exclude_chosen = any(
                item.decision == DECISION_EXCLUDE_DUPLICATES
                for item in decisions
            )
            if exclude_chosen:
                st.caption(t("intake.dup.exclude_note", lang))
            else:
                st.caption(t("intake.dup.keep_note", lang))
        else:
            st.info(t("intake.dup.blocked", lang))
    elif unresolved:
        st.info(t("intake.dup.blocked", lang))
    return not bool(unresolved)


def _reset_for_new_file() -> None:
    clear_intake_state(st.session_state)
    clear_analysis_result(st.session_state)
    st.session_state[STATE_INTAKE_STEP] = 1


def _table_fingerprint(table: Any) -> str:
    return structural_fingerprint(
        columns=list(table.columns),
        sheet_name=str(getattr(table, "sheet_name", "") or ""),
        header_row_index=int(getattr(table, "header_row_index", 0) or 0),
    )


def _facility_suggestion_names() -> tuple[str, ...]:
    raw = get_facility_master_mapping(st.session_state)
    names: list[str] = []
    facilities = raw.get("facilities") if isinstance(raw, dict) else None
    if isinstance(facilities, list):
        for item in facilities:
            if not isinstance(item, dict):
                continue
            label = str(item.get("display_name") or item.get("name") or "").strip()
            if label:
                names.append(label)
    return tuple(names)


def _source_document_id(table: Any) -> str:
    return document_id_for_hash(str(getattr(table, "sha256", "") or ""))


def _looks_like_roc_date_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if "民國" in text:
        return True
    head = text.replace(".", "/").replace("-", "/").replace("年", "/")
    part = head.split("/", 1)[0]
    if not part.isdigit() or len(part) > 3:
        return False
    year = int(part)
    return 1 <= year <= 150 and "/" in head


def _table_dates_look_roc(table: Any) -> bool:
    frame = getattr(table, "frame", None)
    if frame is None:
        return False
    for column in list(getattr(frame, "columns", [])):
        roc = 0
        total = 0
        for value in list(frame[column].tolist())[:12]:
            text = str(value or "").strip()
            if not text:
                continue
            total += 1
            if _looks_like_roc_date_text(text):
                roc += 1
        if total and roc / total >= 0.5:
            return True
    return False


def _render_memory_offer(
    table: Any,
    remembered: dict[str, Any],
    *,
    ubn: str,
    fingerprint: str,
) -> None:
    st.markdown(f"**{t('intake.memory.found', lang)}**")
    st.caption(t("intake.memory.explain", lang))
    if _action_button(
        t("intake.memory.use", lang),
        t("intake.memory.explain", lang),
        key="intake_memory_use",
        primary=True,
    ):
        current = st.session_state.get(STATE_INTAKE_COMMITTED) or {}
        st.session_state[STATE_INTAKE_COMMITTED] = overlay_remembered_committed(
            current, remembered, frame=table.frame
        )
        st.session_state[STATE_INTAKE_MEMORY_CHOICE] = "apply"
        st.session_state[STATE_INTAKE_MEMORY_APPLIED] = True
        append_provenance_event(
            st.session_state,
            event=EVENT_MEMORY_APPLIED,
            company_ubn=ubn,
            fingerprint=fingerprint,
            source="memory",
            reason="customer reused confirmed mapping",
            source_document_id=_source_document_id(table),
        )
        st.rerun()
    if _action_button(
        t("intake.memory.recheck", lang),
        t("intake.memory.explain", lang),
        key="intake_memory_recheck",
    ):
        st.session_state[STATE_INTAKE_MEMORY_CHOICE] = "recheck"
        st.rerun()


def _render_mapping_history() -> None:
    labels = {
        field_name: _field_label(field_name) for field_name in FIELD_LABEL_KEYS
    }
    value_labels = {
        **{code: t(f"activity.{code}", lang) for code in ACTIVITY_TYPES},
        "NG1": t("intake.ng_option_1", lang),
        "NG2": t("intake.ng_option_2", lang),
        "company_vehicle": t("intake.diesel_company_vehicle", lang),
        "enterprise": t("intake.electricity_enterprise", lang),
        "emission_activity": t("intake.history.emission_activity", lang),
        "file": t("intake.dates_in_file", lang),
        "year_month": t("intake.dates_year_month", lang),
        "period": t("intake.dates_period", lang),
        "unknown": t("intake.ex.unknown_rows", lang),
    }
    rows = customer_history_rows(
        st.session_state,
        company_ubn=confirmed_company_ubn(st.session_state),
        lang=lang,
        field_labels=labels,
        value_labels=value_labels,
    )
    if not rows:
        return
    with st.expander(t("intake.memory.history", lang), expanded=False):
        for row in rows:
            bits = [row["action"]]
            if row["field"]:
                bits.append(row["field"])
            if row["detail"] and row["detail"] != row["field"]:
                bits.append(row["detail"])
            st.markdown(" · ".join(bits))


def _activity_select_label(code: str) -> str:
    if not code:
        return t("intake.choose", lang)
    return t(f"activity.{code}", lang)


def _column_index(options: list[str], preferred: str, *, allow_preselect: bool) -> int:
    if allow_preselect and preferred and preferred in options:
        return options.index(preferred)
    return 0


def _action_button(
    label: str,
    help_text: str,
    *,
    key: str,
    primary: bool = False,
    show_help: bool = False,
    disabled: bool = False,
) -> bool:
    if show_help:
        st.caption(help_text)
    return st.button(
        label,
        type="primary" if primary else "secondary",
        key=key,
        disabled=disabled,
    )


FIELD_LABEL_KEYS = {
    "activity_type": "intake.field.activity_type",
    "activity_value": "intake.field.activity_value",
    "unit": "intake.field.unit",
    "site_id": "intake.field.site_id",
    "year_month": "intake.field.year_month",
    "activity_start_date": "intake.field.start",
    "activity_end_date": "intake.field.end",
    "fuel_subtype": "intake.ng_type",
}


def _intake_validate_stage_label(stage: str) -> str:
    keys = {
        "prepare": "intake.validate.stage.prepare",
        "rows": "intake.validate.stage.rows",
        "dispositions": "intake.validate.stage.dispositions",
        "duplicates": "intake.validate.stage.duplicates",
        "complete": "intake.validate.stage.complete",
    }
    key = keys.get(stage, "intake.validate.stage.prepare")
    return t(key, lang)


def _run_intake_validation_round_two(
    table: Any,
    committed: Any,
    *,
    ubn: str,
    fingerprint: str,
    doc_id: str,
) -> None:
    """Paint 0% first, then run validation. Never start CPU on the click run."""
    mapping = st.session_state.get(STATE_INTAKE_MAPPING)
    metadata = st.session_state.get(STATE_INTAKE_METADATA)
    row_count = int(len(table.frame))
    st.markdown(
        f"### {t('intake.validate.running_title', lang)}"
    )
    st.markdown(
        '<div data-cel-intake-validating="1" role="status"></div>',
        unsafe_allow_html=True,
    )
    progress = st.progress(
        0, text=t("intake.validate.percent", lang, percent=0)
    )
    stage_box = st.empty()
    count_box = st.empty()

    def _paint_status(stage: str) -> None:
        stage_label = html_escape(_intake_validate_stage_label(stage))
        count_label = html_escape(
            t(
                "intake.validate.processing_count",
                lang,
                count=f"{row_count:,}",
            )
        )
        stage_box.markdown(
            f'<p class="cel-intake-progress-copy">{stage_label}</p>',
            unsafe_allow_html=True,
        )
        count_box.markdown(
            f'<p class="cel-intake-progress-copy">{count_label}</p>',
            unsafe_allow_html=True,
        )

    _paint_status("prepare")
    st.button(
        t("intake.btn.continue_ready", lang),
        type="primary",
        disabled=True,
        key="intake_accept_interpretation_busy",
    )
    st.button(
        t("intake.btn.fix", lang),
        disabled=True,
        key="intake_fix_interpretation_busy",
    )
    if mapping is None or metadata is None:
        clear_intake_validation_lock(
            st.session_state,
            error=t("intake.document_date_required", lang),
        )
        st.rerun()

    def _on_progress(stage: str, completed: int, total: int, message: str) -> None:
        del message
        percent = intake_validation_percent(stage, completed, total)
        progress.progress(
            min(1.0, percent / 100.0),
            text=t("intake.validate.percent", lang, percent=percent),
        )
        _paint_status(stage)

    execute_intake_validation(
        st.session_state,
        table=table,
        mapping=mapping,
        metadata=metadata,
        committed=committed,
        ubn=ubn,
        fingerprint=fingerprint,
        doc_id=doc_id,
        progress=_on_progress,
        unexpected_error=t("intake.validate.unexpected_error", lang),
    )
    st.rerun()


def _field_label(field_name: str) -> str:
    key = FIELD_LABEL_KEYS.get(field_name)
    return t(key, lang) if key else field_name


def _proposal_counts(
    table: Any,
    detailed: dict[str, FieldSuggestion],
    committed: dict[str, Any],
) -> dict[str, int]:
    return summary_counts(table, detailed, committed)


def _render_read_summary(
    table: Any,
    detailed: dict[str, FieldSuggestion],
    committed: dict[str, Any],
    *,
    show_heading: bool = True,
) -> dict[str, int]:
    counts = _proposal_counts(table, detailed, committed)
    rows: list[str] = [
        f'<p class="cel-read-file">{html_escape(table.file_name)}</p>',
        f"<p>{html_escape(t('intake.read_found', lang, n=len(table.frame)))}</p>",
    ]
    if table.sheet_name:
        rows.append(
            "<p>"
            + html_escape(t("intake.read_sheet", lang, sheet=table.sheet_name))
            + "</p>"
        )
    rows.append(
        "<p>"
        + html_escape(t("intake.read_recognized", lang, n=counts["recognized"]))
        + "</p>"
    )
    confirm = int(counts["confirm"])
    held = int(counts["waiting_rows"])
    if confirm > 0:
        rows.append(
            "<p>"
            + html_escape(t("intake.read_confirm_count", lang, confirm=confirm))
            + "</p>"
        )
    elif held > 0:
        rows.append(
            "<p>"
            + html_escape(t("intake.status.deferred", lang, n=held))
            + "</p>"
        )
    else:
        rows.append("<p>" + html_escape(t("intake.status.ready", lang)) + "</p>")
    rows.append(
        "<p>"
        + html_escape(
            t(
                "intake.read_rows",
                lang,
                ready=counts["ready_rows"],
                held=held,
            )
        )
        + "</p>"
    )
    if show_heading:
        st.markdown(f"### {t('intake.read_title', lang)}")
    st.markdown(
        f'<div class="cel-read-summary">{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )
    return counts


def _suggestion(
    detailed: dict[str, FieldSuggestion],
    field_name: str,
) -> FieldSuggestion:
    return detailed.get(
        field_name,
        FieldSuggestion(field_name, "", CONFIDENCE_LOW),
    )


def _usable_suggestion(suggestion: FieldSuggestion) -> bool:
    return bool(suggestion.source_column) and suggestion.confidence in {
        CONFIDENCE_HIGH,
        CONFIDENCE_MEDIUM,
    }


def _sample_year_month_value(table: Any, column: str) -> Any | None:
    if not column or column not in table.frame.columns:
        return None
    for item in table.frame[column].tolist():
        if item is not None and str(item).strip():
            return item
    return None


def _default_date_mode(detailed: dict[str, FieldSuggestion]) -> str:
    ym = _suggestion(detailed, "year_month")
    start = _suggestion(detailed, "activity_start_date")
    end = _suggestion(detailed, "activity_end_date")
    if (
        _usable_suggestion(ym)
        and not (
            _usable_suggestion(start)
            and _usable_suggestion(end)
        )
    ):
        return "year_month"
    if _usable_suggestion(start) and _usable_suggestion(end):
        return "file"
    return "period"


def _default_metadata(table: Any) -> IntakeMetadata:
    return IntakeMetadata(
        source_name=table.file_name,
        site_id="UNKNOWN",
        document_date=None,
        data_quality_tier="unknown",
        intake_run_id="ui_intake",
        ingested_at=pd.Timestamp.now(tz="UTC"),
    )


def _ensure_committed(
    table: Any,
    detailed: dict[str, FieldSuggestion],
) -> dict[str, Any]:
    existing = st.session_state.get(STATE_INTAKE_COMMITTED)
    if isinstance(existing, dict) and existing.get("columns") is not None:
        return existing
    committed = initialize_committed(table, detailed)
    st.session_state[STATE_INTAKE_COMMITTED] = committed
    return committed


def _metadata_from_committed(table: Any, committed: dict[str, Any]) -> IntakeMetadata:
    meta = _default_metadata(table)
    raw = committed.get("document_date")
    if raw:
        try:
            meta.document_date = date.fromisoformat(str(raw)[:10])
        except ValueError:
            meta.document_date = None
    source_name = str(committed.get("source_name") or "").strip()
    if source_name:
        meta.source_name = source_name
    site_id = str(committed.get("fallback_site_id") or "")
    meta.site_id = site_id.strip() or "UNKNOWN"
    quality = str(committed.get("data_quality_tier") or "").strip()
    if quality:
        meta.data_quality_tier = quality
    return meta


def _safe_issue_message(issue_code: str, fallback: str) -> str:
    if issue_code == "UNMAPPED_ACTIVITY_TYPE":
        return t("intake.rej.held_activity", lang)
    if issue_code == "UNMAPPED_UNIT":
        return t("intake.rej.held_unit", lang)
    if issue_code == ISSUE_HELD_NG_CONTEXT:
        return t("intake.rej.held_ng", lang)
    if issue_code == ISSUE_HELD_PENDING_ACTUAL_HV:
        return t("intake.rej.held_pending_hv", lang)
    if issue_code == ISSUE_HELD_DIESEL_CONTEXT:
        return t("intake.rej.held_diesel", lang)
    if issue_code == ISSUE_HELD_ELEC_CONTEXT:
        return t("intake.rej.held_elec", lang)
    return fallback


def _bring_guided_question_into_view() -> None:
    import streamlit.components.v1 as components

    components.html(
        """
        <script>
        (function () {
          const doc = (window.parent && window.parent.document)
            ? window.parent.document
            : document;
          const el = doc.querySelector('[data-cel-guided-question="1"]');
          if (!el || !el.scrollIntoView) return;
          const rect = el.getBoundingClientRect();
          const viewH = doc.documentElement.clientHeight || 0;
          if (rect.top < 64 || rect.bottom > viewH - 8) {
            el.scrollIntoView({ block: "start", inline: "nearest" });
          }
        })();
        </script>
        """,
        height=0,
    )


def _render_exception_card(
    item: IntakeException,
    table: Any,
    committed: dict[str, Any],
    *,
    apply_label: str,
) -> None:
    label = _field_label(item.field) if item.field in FIELD_LABEL_KEYS else ""
    question = ""
    why = t("intake.ex.column_why", lang)
    if item.kind == KIND_COLUMN:
        if item.proposed:
            question = t("intake.ex.column_q", lang, column=item.proposed)
            why = t("intake.ex.column_why_medium", lang, label=label)
        elif item.field == "activity_value":
            question = t("intake.ex.usage_q_blank", lang)
        else:
            question = t("intake.ex.column_q_blank", lang, label=label)
    elif item.kind == KIND_YEAR_MONTH:
        question = t("intake.ex.ym_q", lang, column=item.proposed or item.source_label)
    elif item.kind == KIND_DATES:
        question = (
            t("intake.ex.date_era_q", lang)
            if _table_dates_look_roc(table)
            else t("intake.ex.dates_q", lang)
        )
    elif item.kind == KIND_CONTEXT and item.field == "natural_gas":
        question = t("intake.ex.ng_q", lang)
        why = t("intake.ex.ng_why", lang)
    elif item.kind == KIND_CONTEXT and item.field == "diesel":
        question = t("intake.ex.diesel_q", lang)
        why = t("intake.ex.diesel_why", lang)
    elif item.kind == KIND_CONTEXT and item.field == "electricity":
        question = t("intake.ex.elec_q", lang)
        why = t("intake.ex.elec_why", lang)
    elif item.kind == KIND_ACTIVITY_VALUE:
        question = t("intake.ex.activity_q", lang, value=item.source_label)
        why = t("intake.ex.why_activity", lang)
    elif item.kind == KIND_UNIT_VALUE:
        question = t("intake.ex.unit_q", lang, value=item.source_label)
        why = t("intake.ex.why_activity", lang)
    st.markdown(
        f'<div class="cel-exception-card" data-cel-guided-question="1" '
        f'data-cel-tour-target="recognition-question">'
        f"<p><strong>"
        f"{html_escape(question)}</strong></p></div>",
        unsafe_allow_html=True,
    )
    st.caption(why)
    if item.kind == KIND_CONTEXT and item.field == "natural_gas":
        site_label = (
            t("intake.ex.ng_single", lang)
            if str(item.source_label or "") in {"", NG_GROUP_SINGLE}
            else str(item.source_label)
        )
        row_count = len(item.affected_source_rows) or 1
        st.caption(
            t("intake.ex.ng_group", lang, site=site_label, n=row_count)
        )
        other_answers = [
            str(value)
            for key, value in dict(committed.get("natural_gas_groups") or {}).items()
            if str(key) != str(item.group_id or "")
            and str(value) in {"NG1", "NG2"}
        ]
        if other_answers:
            st.caption(t("intake.ex.ng_hint", lang, value=other_answers[-1]))
    if item.proposed and item.kind not in {KIND_COLUMN}:
        st.caption(t("intake.ex.proposed", lang, value=item.proposed))

    payload: dict[str, Any] = {"table": table}
    choose_label = t("intake.choose", lang)
    unknown_label = t("intake.ex.unknown_rows", lang)
    draft_key = f"intake_ex_draft_{item.item_id}"
    apply_key = f"intake_ex_apply_{item.item_id}"
    st.markdown(
        "<span data-cel-tour-target='recognition-options'></span>",
        unsafe_allow_html=True,
    )

    if item.kind == KIND_COLUMN:
        options = [choose_label] + list(table.columns)
        index = options.index(item.proposed) if item.proposed in options else 0
        selected = st.selectbox(
            t("intake.ex.column_control", lang),
            options=options,
            index=index,
            key=draft_key,
        )
        payload["column"] = "" if selected == choose_label else selected
    elif item.kind == KIND_YEAR_MONTH:
        st.checkbox(
            t("intake.year_month_confirm", lang),
            value=False,
            key=draft_key,
        )
        payload["confirmed"] = bool(st.session_state.get(draft_key))
        payload["column"] = item.proposed
    elif item.kind == KIND_DATES:
        mode_labels = {
            t("intake.dates_in_file", lang): "file",
            t("intake.dates_year_month", lang): "year_month",
            t("intake.dates_period", lang): "period",
        }
        selected_mode = st.radio(
            t("intake.ex.dates_q", lang),
            options=list(mode_labels),
            index=None,
            key=draft_key,
        )
        payload["date_mode"] = mode_labels.get(selected_mode or "", "")
        cols = [choose_label] + list(table.columns)
        date_mode = payload["date_mode"]
        if date_mode == "file":
            payload["start_column"] = st.selectbox(
                t("intake.map_start", lang), cols, key=f"{draft_key}_start"
            )
            payload["end_column"] = st.selectbox(
                t("intake.map_end", lang), cols, key=f"{draft_key}_end"
            )
            if payload["start_column"] == choose_label:
                payload["start_column"] = ""
            if payload["end_column"] == choose_label:
                payload["end_column"] = ""
        elif date_mode == "year_month":
            picked = st.selectbox(
                t("intake.map_year_month", lang), cols, key=f"{draft_key}_ym"
            )
            payload["year_month_column"] = (
                "" if picked == choose_label else picked
            )
            payload["confirmed"] = st.checkbox(
                t("intake.year_month_confirm", lang),
                key=f"{draft_key}_ym_ok",
            )
        elif date_mode == "period":
            payload["period_start"] = st.date_input(
                t("intake.period_start", lang),
                value=None,
                key=f"{draft_key}_pstart",
            )
            payload["period_end"] = st.date_input(
                t("intake.period_end", lang),
                value=None,
                key=f"{draft_key}_pend",
            )
    elif item.kind == KIND_CONTEXT and item.field == "natural_gas":
        options = [
            t("intake.ng_option_1", lang),
            t("intake.ng_option_2", lang),
            t("intake.ng_option_actual_hv", lang),
            t("intake.ng_option_cannot_confirm", lang),
        ]
        selected = st.radio(
            t("intake.ng_type", lang),
            options=options,
            index=None,
            key=draft_key,
        )
        if selected == t("intake.ng_option_1", lang):
            payload["value"] = "NG1"
        elif selected == t("intake.ng_option_2", lang):
            payload["value"] = "NG2"
        elif selected == t("intake.ng_option_actual_hv", lang):
            payload["value"] = NG_VALUE_PENDING_HV
            st.markdown(f"**{t('intake.ng_pending_hv_title', lang)}**")
            st.caption(t("intake.ng_pending_hv_help", lang))
            payload["heating_value"] = st.text_input(
                t("intake.ng_pending_hv_value", lang),
                key=f"{draft_key}_hv_value",
            )
            payload["heating_unit"] = st.text_input(
                t("intake.ng_pending_hv_unit", lang),
                key=f"{draft_key}_hv_unit",
            )
            hv_period = st.columns(2)
            with hv_period[0]:
                start_date = st.date_input(
                    t("intake.period_start", lang),
                    value=None,
                    key=f"{draft_key}_hv_start",
                )
            with hv_period[1]:
                end_date = st.date_input(
                    t("intake.period_end", lang),
                    value=None,
                    key=f"{draft_key}_hv_end",
                )
            payload["period_start"] = (
                start_date.isoformat() if isinstance(start_date, date) else ""
            )
            payload["period_end"] = (
                end_date.isoformat() if isinstance(end_date, date) else ""
            )
            payload["source_reference"] = st.text_input(
                t("intake.ng_pending_hv_source", lang),
                key=f"{draft_key}_hv_source",
            )
        elif selected == t("intake.ng_option_cannot_confirm", lang):
            payload["value"] = "unknown"
    elif item.kind == KIND_CONTEXT and item.field == "diesel":
        options = [t("intake.diesel_company_vehicle", lang), unknown_label]
        selected = st.radio(
            t("intake.diesel_context", lang),
            options=options,
            index=None,
            key=draft_key,
        )
        if selected == t("intake.diesel_company_vehicle", lang):
            payload["value"] = "company_vehicle"
        elif selected == unknown_label:
            payload["value"] = "unknown"
    elif item.kind == KIND_CONTEXT and item.field == "electricity":
        options = [t("intake.electricity_enterprise", lang), unknown_label]
        selected = st.radio(
            t("intake.electricity_context", lang),
            options=options,
            index=None,
            key=draft_key,
        )
        if selected == t("intake.electricity_enterprise", lang):
            payload["value"] = "enterprise"
        elif selected == unknown_label:
            payload["value"] = "unknown"
    elif item.kind == KIND_ACTIVITY_VALUE:
        options = [choose_label] + [
            t(f"activity.{code}", lang) for code in ACTIVITY_TYPES
        ] + [unknown_label]
        selected = st.selectbox(
            item.source_label, options=options, key=draft_key
        )
        if selected == unknown_label:
            payload["value"] = "unknown"
        elif selected == choose_label:
            payload["value"] = ""
        else:
            payload["value"] = ACTIVITY_LABEL_TO_CODE.get(selected, "")
    elif item.kind == KIND_UNIT_VALUE:
        options = [choose_label] + list(SUPPORTED_UNITS) + [unknown_label]
        selected = st.selectbox(
            item.source_label, options=options, key=draft_key
        )
        if selected == unknown_label:
            payload["value"] = "unknown"
        elif selected == choose_label:
            payload["value"] = ""
        else:
            payload["value"] = selected

    st.markdown(
        "<span data-cel-tour-target='recognition-apply'></span>",
        unsafe_allow_html=True,
    )
    if st.button(apply_label, key=apply_key):
        updated = apply_exception(committed, item, payload)
        if updated is committed:
            if payload.get("value") == NG_VALUE_PENDING_HV:
                st.warning(t("intake.ng_pending_hv_help", lang))
            return
        st.session_state[STATE_INTAKE_COMMITTED] = updated
        st.session_state[STATE_INTAKE_EXCEPTION_CURSOR] = (
            int(st.session_state.get(STATE_INTAKE_EXCEPTION_CURSOR, 0) or 0) + 1
        )
        answer = str(
            payload.get("column")
            or payload.get("value")
            or payload.get("date_mode")
            or ""
        )
        unknown_chosen = str(payload.get("value") or "") in {
            "unknown",
            NG_VALUE_PENDING_HV,
        }
        previous = ""
        if item.kind == KIND_COLUMN:
            previous = str((committed.get("columns") or {}).get(item.field) or "")
        event = EVENT_CUSTOMER_CONFIRMED
        if unknown_chosen:
            event = EVENT_MARKED_UNKNOWN
        elif previous and previous != answer:
            event = EVENT_CUSTOMER_CORRECTED
        reason = "explicit apply"
        committed_value = "" if unknown_chosen else answer
        if payload.get("value") == NG_VALUE_PENDING_HV:
            reason = "pending actual heating value review"
            committed_value = " ".join(
                part
                for part in (
                    str(payload.get("heating_value") or "").strip(),
                    str(payload.get("heating_unit") or "").strip(),
                    str(payload.get("source_reference") or "").strip(),
                )
                if part
            )
        append_provenance_event(
            st.session_state,
            event=event,
            company_ubn=confirmed_company_ubn(st.session_state),
            fingerprint=_table_fingerprint(table),
            field=(
                "natural_gas_pending_hv"
                if payload.get("value") == NG_VALUE_PENDING_HV
                else item.field
            ),
            proposed=item.proposed,
            committed=committed_value,
            source="customer",
            reason=reason,
            source_document_id=_source_document_id(table),
        )
        st.rerun()


step = int(st.session_state.get(STATE_INTAKE_STEP, 1) or 1)
if step > 1:
    _step_indicator(step)

existing_table = st.session_state.get(STATE_INTAKE_TABLE)
existing_result = st.session_state.get(STATE_INTAKE_RESULT)
_validation_busy = bool(
    st.session_state.get(STATE_INTAKE_VALIDATION_REQUESTED)
    or st.session_state.get(STATE_INTAKE_VALIDATION_RUNNING)
)

# —— Step summaries for completed upstream steps (only one active workspace) ——
if step > 1 and existing_table is not None:
    _render_completed_step_summary(
        step_no=1,
        title=t("intake.uploaded_summary", lang),
        detail=(
            f"{existing_table.file_name} · "
            f"{len(existing_table.frame)} {t('intake.row_count', lang)}"
        ),
        edit_key="intake_edit_step1",
        target_step=1,
        compact=step == 2,
        disabled=_validation_busy,
    )
if step > 2 and existing_table is not None:
    _render_completed_step_summary(
        step_no=2,
        title=t("intake.step2", lang),
        detail=t("intake.journey.confirm", lang),
        edit_key="intake_edit_step2",
        target_step=2,
        disabled=_validation_busy,
    )
if step > 3 and existing_result is not None:
    _render_completed_step_summary(
        step_no=3,
        title=t("intake.step3", lang),
        detail=(
            f"{existing_result.accepted_count} ✓ / "
            f"{existing_result.rejected_count} × / "
            f"{existing_result.total_count}"
        ),
        edit_key="intake_edit_step3",
        target_step=3,
        disabled=_validation_busy,
    )

uploaded = None
if step == 1:
    with onboarding_target("upload-activity-data"):
        render_section_header(
            t("intake.upload_existing_title", lang),
            t("intake.page_lead", lang),
        )
        st.markdown(
            f'<p class="cel-upload-primary-label">'
            f"{t('ev.landing.primary', lang)}</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<span data-cel-tour-target='upload-dropzone'></span>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            t("intake.upload_label", lang),
            type=["csv", "xlsx"],
            help=t("intake.upload_limit", lang),
            key="intake_file_uploader",
        )
        st.markdown(t("intake.upload_limit", lang))
        st.caption(t("intake.upload_no_pdf", lang))
    st.markdown('<div class="cel-upload-fallback">', unsafe_allow_html=True)
    template_bytes, template_name, template_mime = _template_download_payload()
    st.download_button(
        label=t("intake.template_fallback", lang),
        data=template_bytes,
        file_name=template_name,
        mime=template_mime,
        key="intake_template_download",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    analyzed = get_current_result(st.session_state)
    if analyzed is not None:
        ev_summary = beginner_result_summary(analyzed, lang)
        ev_done = int(ev_summary["calculated"])
        ev_unresolved = int(ev_summary["needs_work"])
        st.caption("✓ " + t("ev.status_done", lang, done=ev_done))
        if should_show_unresolved_cta(ev_unresolved):
            if st.button(t("dash.cta.view_problems", lang), key="ev_view_issues"):
                st.switch_page("app_pages/issues_actions.py")
        act_col, file_col = st.columns(2)
        with act_col:
            if st.button(
                t("ev.cta.view_activities", lang),
                key="ev_view_activities",
            ):
                st.switch_page("app_pages/activity_explorer.py")
        with file_col:
            if st.button(t("ev.cta.view_files", lang), key="ev_view_files"):
                st.switch_page("app_pages/evidence_data.py")

if uploaded is not None:
    file_bytes = uploaded.getvalue()
    file_name = uploaded.name
    previous_hash = st.session_state.get(STATE_INTAKE_FILE_HASH)
    try:
        from carbon_ledger.intake import compute_bytes_sha256, validate_upload_bytes

        validate_upload_bytes(file_name, file_bytes)
        file_hash = compute_bytes_sha256(file_bytes)
    except IntakeError as exc:
        if exc.code == "FILE_TOO_LARGE":
            st.error(t("intake.err_too_large", lang))
        elif exc.code == "INVALID_ENCODING":
            st.error(t("intake.err_encoding", lang))
        elif str(file_name).lower().endswith(".pdf"):
            st.error(t("intake.err_pdf", lang))
        else:
            st.error(t("intake.err_unsupported", lang))
        st.stop()

    if previous_hash and previous_hash != file_hash:
        _reset_for_new_file()

    st.session_state[STATE_INTAKE_BYTES] = file_bytes
    st.session_state[STATE_INTAKE_FILE_HASH] = file_hash
    st.session_state[STATE_INTAKE_FILE_NAME] = file_name
    # Drop any confirmation-queue observation that belongs to another file, so
    # step 3 of the tour is decided by this file's own list_exceptions() run.
    note_onboarding_upload_file(st.session_state, file_hash)

    sheet_name = st.session_state.get(STATE_INTAKE_SHEET)
    sheet_confirmed = bool(st.session_state.get(STATE_INTAKE_SHEET_CONFIRMED))
    extension = file_name.lower().rsplit(".", 1)[-1]
    if extension == "xlsx":
        try:
            sheets = list_xlsx_sheet_names(file_bytes)
            ranked = rank_xlsx_worksheets(file_bytes)
        except Exception:
            st.error(t("intake.err_unsupported", lang))
            st.stop()
        if not sheets or not ranked:
            st.error(t("intake.err_unsupported", lang))
            st.stop()

        suggested = ranked[0]
        if len(sheets) > 1 and not sheet_confirmed:
            st.markdown(f"**{t('intake.sheet_ask', lang)}**")
            st.markdown(f"### {suggested.sheet_name}")
            st.markdown(t("intake.detect_result", lang))
            for label in worksheet_detection_labels(suggested):
                st.markdown(f"- {label}")
            btn_cols = st.columns(2)
            with btn_cols[0]:
                if _action_button(
                    t("intake.use_suggested_sheet", lang),
                    t("intake.btn.use_sheet_help", lang),
                    key="intake_use_suggested_sheet",
                    primary=True,
                ):
                    st.session_state[STATE_INTAKE_SHEET] = suggested.sheet_name
                    st.session_state[STATE_INTAKE_SHEET_CONFIRMED] = True
                    st.rerun()
            with btn_cols[1]:
                if _action_button(
                    t("intake.choose_other_sheet", lang),
                    t("intake.btn.other_sheet_help", lang),
                    key="intake_choose_other_sheet",
                ):
                    st.session_state["intake_sheet_picker_open"] = True
            if st.session_state.get("intake_sheet_picker_open"):
                default_index = (
                    sheets.index(sheet_name) if sheet_name in sheets else 0
                )
                picked = st.selectbox(
                    t("intake.sheet_label", lang),
                    options=sheets,
                    index=default_index,
                    key="intake_sheet_selector",
                )
                if _action_button(
                    t("intake.header_confirm", lang),
                    t("intake.btn.header_help", lang),
                    key="intake_confirm_sheet",
                    primary=True,
                ):
                    st.session_state[STATE_INTAKE_SHEET] = picked
                    st.session_state[STATE_INTAKE_SHEET_CONFIRMED] = True
                    st.session_state["intake_sheet_picker_open"] = False
                    st.rerun()
            st.stop()

        if not sheet_confirmed:
            st.session_state[STATE_INTAKE_SHEET] = suggested.sheet_name
            st.session_state[STATE_INTAKE_SHEET_CONFIRMED] = True
            sheet_name = suggested.sheet_name
        else:
            sheet_name = (
                st.session_state.get(STATE_INTAKE_SHEET) or suggested.sheet_name
            )

    header_row = st.session_state.get(STATE_INTAKE_HEADER_ROW)
    header_confirmed = bool(st.session_state.get(STATE_INTAKE_HEADER_CONFIRMED))

    if not header_confirmed:
        try:
            raw = load_raw_tabular_frame(
                data=file_bytes,
                file_extension=extension,
                sheet_name=sheet_name,
            )
            detection = detect_header_row(raw)
        except Exception:
            st.error(t("intake.err_unsupported", lang))
            st.stop()

        if detection.needs_confirmation:
            st.markdown(f"**{t('intake.header_ask', lang)}**")
            options = list(detection.candidate_rows) or [
                detection.header_row_index
            ]
            labels = {
                idx: t("intake.header_row_label", lang, row=idx + 1)
                for idx in options
            }
            selected_idx = st.radio(
                t("intake.header_ask", lang),
                options=options,
                index=options.index(detection.header_row_index)
                if detection.header_row_index in options
                else 0,
                format_func=lambda idx: labels.get(idx, str(idx + 1)),
                key="intake_header_radio",
            )
            preview_rows = []
            for idx in options[:5]:
                if idx < len(raw):
                    preview_rows.append(
                        {
                            t("intake.header_row_label", lang, row=idx + 1): " | ".join(
                                str(v) if v is not None else ""
                                for v in raw.iloc[idx].tolist()[:8]
                            )
                        }
                    )
            if preview_rows:
                st.dataframe(
                    pd.DataFrame(preview_rows),
                    hide_index=True,
                    width="stretch",
                )
            if _action_button(
                t("intake.header_confirm", lang),
                t("intake.btn.header_help", lang),
                key="intake_confirm_header",
                primary=True,
            ):
                st.session_state[STATE_INTAKE_HEADER_ROW] = int(selected_idx)
                st.session_state[STATE_INTAKE_HEADER_CONFIRMED] = True
                st.rerun()
            st.stop()

        st.session_state[STATE_INTAKE_HEADER_ROW] = detection.header_row_index
        st.session_state[STATE_INTAKE_HEADER_CONFIRMED] = True
        header_row = detection.header_row_index

    try:
        with st.status(t("intake.processing_title", lang), expanded=True) as status:
            st.write(t("intake.processing_body", lang))
            table = parse_uploaded_table(
                file_name=file_name,
                data=file_bytes,
                sheet_name=sheet_name,
                header_row=int(header_row) if header_row is not None else None,
            )
            status.update(label=t("intake.read_title", lang), state="complete")
    except IntakeError as exc:
        if exc.code == "INVALID_ENCODING":
            st.error(t("intake.err_encoding", lang))
        elif exc.code == "FILE_TOO_LARGE":
            st.error(t("intake.err_too_large", lang))
        else:
            st.error(t("intake.err_unsupported", lang))
        st.stop()

    st.session_state[STATE_INTAKE_TABLE] = table
    st.session_state[STATE_INTAKE_STEP] = 2
    st.session_state[STATE_INTAKE_SHOW_MAPPING_EDITOR] = False
    st.rerun()

table = st.session_state.get(STATE_INTAKE_TABLE)
if table is None:
    st.stop()

step = int(st.session_state.get(STATE_INTAKE_STEP, 1) or 1)
if step < 2:
    st.stop()

result = st.session_state.get(STATE_INTAKE_RESULT)
detailed = suggest_column_mapping_with_confidence(
    list(table.columns),
    frame=table.frame,
    facility_names=_facility_suggestion_names(),
)
show_editor = bool(st.session_state.get(STATE_INTAKE_SHOW_MAPPING_EDITOR))

# Active workspace gates: only one expanded step body at a time.
if step > 3 and result is None:
    st.session_state[STATE_INTAKE_STEP] = 2
    step = 2

# Confirmation / editor only while there is no validated result yet.
if result is None and step <= 2:
    st.write("")
    ubn = confirmed_company_ubn(st.session_state)
    fingerprint = _table_fingerprint(table)
    doc_id = _source_document_id(table)
    record_system_suggestions(
        st.session_state,
        detailed,
        company_ubn=ubn,
        fingerprint=fingerprint,
        source_document_id=doc_id,
    )
    committed = _ensure_committed(table, detailed)
    remembered = (
        lookup_remembered_mapping(
            st.session_state, ubn=ubn, fingerprint=fingerprint
        )
        if ubn
        else None
    )
    choice = str(st.session_state.get(STATE_INTAKE_MEMORY_CHOICE) or "")
    awaiting_memory = bool(remembered and choice == "")
    if awaiting_memory:
        offer_identity = "|".join((ubn, fingerprint, doc_id))
        if st.session_state.get(STATE_INTAKE_MEMORY_OFFERED) != offer_identity:
            append_provenance_event(
                st.session_state,
                event=EVENT_MEMORY_OFFERED,
                company_ubn=ubn,
                fingerprint=fingerprint,
                source="memory",
                reason="compatible structure",
                source_document_id=doc_id,
            )
            st.session_state[STATE_INTAKE_MEMORY_OFFERED] = offer_identity
        st.markdown(f"### {t('intake.read_title', lang)}")
        st.caption(table.file_name)
        _render_memory_offer(
            table, remembered, ubn=ubn, fingerprint=fingerprint
        )
        _render_mapping_history()
        st.stop()
    error_text = st.session_state.get(STATE_INTAKE_VALIDATION_ERROR)
    if error_text:
        st.error(str(error_text))
    if st.session_state.get(STATE_INTAKE_VALIDATION_REQUESTED):
        _run_intake_validation_round_two(
            table,
            committed,
            ubn=ubn,
            fingerprint=fingerprint,
            doc_id=doc_id,
        )
        st.stop()
    exceptions = list_exceptions(table, detailed, committed)
    # Observation only: lets onboarding skip the review step when this file
    # produced no questions. The queue and its answers stay owned here.
    queue_just_cleared = record_onboarding_open_questions(
        st.session_state,
        len(exceptions),
        file_hash=str(st.session_state.get(STATE_INTAKE_FILE_HASH) or ""),
    )
    if queue_just_cleared and onboarding_running(st.session_state):
        # The tour picked its step before this file's queue was known to be
        # empty. One rerun lets it resolve the next step against the settled
        # queue instead of pointing at a card that is gone. Only the first
        # empty observation of a file reruns, so this cannot loop.
        st.rerun()
    if exceptions:
        counts = _proposal_counts(table, detailed, committed)
        st.caption(
            t("intake.read_title", lang)
            + " · "
            + str(table.file_name)
            + " · "
            + t("intake.read_found", lang, n=len(table.frame))
            + " · "
            + t("intake.read_recognized", lang, n=counts["recognized"])
        )
        with st.expander(t("intake.read_title", lang), expanded=False):
            _render_read_summary(
                table, detailed, committed, show_heading=False
            )
        _render_mapping_history()
    else:
        _render_read_summary(table, detailed, committed)
        _render_mapping_history()
    ref_cols = reference_only_columns(list(table.columns))
    if ref_cols:
        st.caption(t("intake.reference_only_note", lang))
    if not show_editor:
        if exceptions:
            timeline = confirmation_timeline(table, detailed, committed)
            remaining_ids = {item.item_id for item in exceptions}
            cursor = int(st.session_state.get(STATE_INTAKE_EXCEPTION_CURSOR, 0) or 0)
            first_remaining = next(
                (
                    index
                    for index, item in enumerate(timeline)
                    if item.item_id in remaining_ids
                ),
                max(0, len(timeline) - 1),
            )
            if cursor < 0 or cursor >= len(timeline):
                cursor = first_remaining
            current_item = timeline[cursor]
            st.markdown(
                '<div class="cel-guided-question-anchor" '
                'data-cel-guided-question="1"></div>',
                unsafe_allow_html=True,
            )
            progress_cols = st.columns([3, 1])
            with progress_cols[0]:
                st.caption(
                    t("intake.ex.queue_title", lang)
                    + " · "
                    + t(
                        "intake.ex.progress",
                        lang,
                        current=cursor + 1,
                        total=len(timeline),
                    )
                )
            with progress_cols[1]:
                if cursor > 0 and st.button(
                    t("intake.ex.previous", lang),
                    key="intake_exception_previous",
                ):
                    st.session_state[STATE_INTAKE_EXCEPTION_CURSOR] = cursor - 1
                    st.rerun()
            with onboarding_target("recognition-question"):
                _render_exception_card(
                    current_item,
                    table,
                    committed,
                    apply_label=t("intake.ex.apply", lang),
                )
            remaining_n = len(exceptions)
            st.caption(t("intake.btn.continue_blocked", lang, n=remaining_n))
            _bring_guided_question_into_view()
        else:
            held = int(summary_counts(table, detailed, committed)["waiting_rows"])
            if held > 0:
                st.info(t("intake.status.deferred", lang, n=held))
            else:
                st.success(t("intake.status.ready", lang))
            if _action_button(
                t("intake.btn.continue_ready", lang),
                t("intake.btn.accept_help", lang),
                key="intake_accept_interpretation",
                primary=True,
            ):
                if not can_validate(table, detailed, committed):
                    st.warning(
                        t(
                            "intake.btn.continue_blocked",
                            lang,
                            n=len(list_exceptions(table, detailed, committed)),
                        )
                    )
                    st.stop()
                mapping = mapping_from_committed(table, committed)
                metadata = _metadata_from_committed(table, committed)
                if metadata.document_date is None:
                    st.error(t("intake.document_date_required", lang))
                    st.stop()
                st.session_state[STATE_INTAKE_MAPPING] = mapping
                st.session_state[STATE_INTAKE_METADATA] = metadata
                st.session_state[STATE_INTAKE_YEAR_MONTH_CONFIRMED] = (
                    mapping.year_month_confirmed
                )
                st.session_state[STATE_INTAKE_VALIDATION_REQUESTED] = True
                st.session_state[STATE_INTAKE_VALIDATION_RUNNING] = False
                st.session_state[STATE_INTAKE_VALIDATION_ERROR] = None
                st.rerun()
        if _action_button(
            t("intake.btn.fix", lang),
            t("intake.btn.fix_help", lang),
            key="intake_fix_interpretation",
        ):
            st.session_state[STATE_INTAKE_SHOW_MAPPING_EDITOR] = True
            st.rerun()
        st.stop()

    st.warning(t("intake.draft_unapplied", lang))
    if _action_button(
        t("intake.btn.continue_ready", lang),
        t("intake.draft_unapplied", lang),
        key="intake_continue_with_editor_open",
    ):
        st.warning(t("intake.draft_unapplied", lang))
    st.markdown(f"**{t('intake.editor.required', lang)}**")

    # Technical mapping controls — only after the beginner asks to fix.
    column_options = [t("intake.choose", lang)] + list(table.columns)

    def _select_for(
        field_name: str,
        label_key: str,
        widget_key: str,
        *,
        required: bool = False,
    ) -> str:
        suggestion = _suggestion(detailed, field_name)
        preferred = suggestion.source_column
        confidence = suggestion.confidence
        allow_preselect = confidence in {CONFIDENCE_HIGH, CONFIDENCE_MEDIUM}
        if required and confidence == CONFIDENCE_LOW:
            st.caption(t("intake.mapping_unknown", lang))
        selected = st.selectbox(
            t(label_key, lang),
            options=column_options,
            index=_column_index(
                column_options,
                preferred,
                allow_preselect=allow_preselect,
            ),
            key=widget_key,
        )
        choose_label = t("intake.choose", lang)
        return "" if selected == choose_label else selected

    activity_type_column = _select_for(
        "activity_type",
        "intake.map_activity_type",
        "intake_map_activity_type",
        required=True,
    )
    activity_value_column = _select_for(
        "activity_value",
        "intake.map_activity_value",
        "intake_map_activity_value",
        required=True,
    )
    unit_column = _select_for(
        "unit",
        "intake.map_unit",
        "intake_map_unit",
        required=True,
    )

    st.markdown(f"**{t('intake.editor.optional', lang)}**")
    site_column = _select_for(
        "site_id",
        "intake.map_site",
        "intake_map_site",
    )
    fuel_subtype_column = _select_for(
        "fuel_subtype",
        "intake.map_ng_type_column",
        "intake_map_fuel_subtype",
    )

    st.markdown(f"**{t('intake.editor.dates', lang)}**")
    default_date_mode = _default_date_mode(detailed)
    if "intake_date_mode" not in st.session_state:
        st.session_state["intake_date_mode"] = default_date_mode

    date_mode = st.radio(
        label=(
            t("intake.dates_in_file", lang)
            + " / "
            + t("intake.dates_year_month", lang)
            + " / "
            + t("intake.dates_period", lang)
        ),
        options=["file", "year_month", "period"],
        format_func=lambda key: {
            "file": t("intake.dates_in_file", lang),
            "year_month": t("intake.dates_year_month", lang),
            "period": t("intake.dates_period", lang),
        }[key],
        horizontal=True,
        key="intake_date_mode",
    )

    use_file_dates = date_mode == "file"
    use_year_month = date_mode == "year_month"
    start_date_column = ""
    end_date_column = ""
    year_month_column = ""
    period_start: date | None = None
    period_end: date | None = None
    year_month_confirmed = bool(
        st.session_state.get(STATE_INTAKE_YEAR_MONTH_CONFIRMED, False)
    )

    if use_file_dates:
        date_cols = st.columns(2)
        with date_cols[0]:
            start_date_column = _select_for(
                "activity_start_date",
                "intake.map_start",
                "intake_map_start",
            )
        with date_cols[1]:
            end_date_column = _select_for(
                "activity_end_date",
                "intake.map_end",
                "intake_map_end",
            )
    elif use_year_month:
        year_month_column = _select_for(
            "year_month",
            "intake.map_year_month",
            "intake_map_year_month",
        )
        if year_month_column and year_month_column in table.frame.columns:
            sample_value = _sample_year_month_value(table, year_month_column)
            if sample_value is not None:
                try:
                    preview = year_month_transform_preview(sample_value)
                    st.markdown(f"**{year_month_column}**")
                    st.write(preview["source"])
                    st.markdown(
                        f"**{t('intake.year_month_preview_title', lang)}**"
                    )
                    st.write(
                        f"{t('intake.field.start', lang)}: "
                        f"{preview['activity_start_date']}"
                    )
                    st.write(
                        f"{t('intake.field.end', lang)}: "
                        f"{preview['activity_end_date']}"
                    )
                except ValueError:
                    st.warning(t("intake.mapping_unknown", lang))
            year_month_confirmed = st.checkbox(
                t("intake.year_month_confirm", lang),
                value=year_month_confirmed,
                key="intake_year_month_confirm_box",
            )
            st.session_state[STATE_INTAKE_YEAR_MONTH_CONFIRMED] = (
                year_month_confirmed
            )
    else:
        st.caption(t("intake.period_required", lang))
        period_cols = st.columns(2)
        with period_cols[0]:
            period_start = st.date_input(
                t("intake.period_start", lang),
                value=None,
                key="intake_period_start",
            )
        with period_cols[1]:
            period_end = st.date_input(
                t("intake.period_end", lang),
                value=None,
                key="intake_period_end",
            )

    draft_mapping = ColumnMapping(
        activity_type_column=activity_type_column,
        activity_value_column=activity_value_column,
        unit_column=unit_column,
        site_column=site_column,
        use_file_dates=use_file_dates,
        use_year_month=use_year_month,
        year_month_column=year_month_column,
        year_month_confirmed=year_month_confirmed,
        start_date_column=start_date_column,
        end_date_column=end_date_column,
        period_start=period_start,
        period_end=period_end,
    )
    suggested_activity_map, suggested_unit_map = default_value_maps(
        table, draft_mapping
    )

    st.markdown(f"**{t('intake.editor.values', lang)}**")
    st.markdown(f"**{t('intake.value_map_activity', lang)}**")
    activity_type_value_map: dict[str, str] = {}
    if activity_type_column:
        for source_value, suggestion in suggested_activity_map.items():
            default_label = _activity_select_label(suggestion)
            index = (
                ACTIVITY_OPTIONS.index(default_label)
                if default_label in ACTIVITY_OPTIONS
                else 0
            )
            selected = st.selectbox(
                source_value,
                options=ACTIVITY_OPTIONS,
                index=index,
                key=f"intake_act_map_{source_value}",
            )
            activity_type_value_map[source_value] = ACTIVITY_LABEL_TO_CODE.get(
                selected, ""
            )

    natural_gas_subtype = "unknown"
    diesel_context = "unknown"
    electricity_context = "unknown"
    mapped_types = set(activity_type_value_map.values())
    unknown_label = t("intake.ng_type_unknown", lang)
    saved_mapping = st.session_state.get(STATE_INTAKE_MAPPING)
    committed_now = _ensure_committed(table, detailed)
    subtype_col = fuel_subtype_column or fuel_subtype_source_column(
        list(table.columns), saved_mapping
    )

    if "natural_gas" in mapped_types:
        source_has_explicit_ng = False
        extracted_subtypes: set[str] = set()
        if activity_type_column:
            for source_value, mapped in activity_type_value_map.items():
                if mapped != "natural_gas":
                    continue
                extracted = extract_natural_gas_subtype_from_text(source_value)
                if extracted:
                    source_has_explicit_ng = True
                    extracted_subtypes.add(extracted)
        if subtype_col and subtype_col in table.frame.columns:
            for _, row in table.frame.iterrows():
                source_text = str(row.get(activity_type_column) or "").strip()
                mapped = activity_type_value_map.get(source_text) or ""
                if mapped != "natural_gas":
                    continue
                extracted = extract_natural_gas_subtype_from_text(row.get(subtype_col))
                if extracted:
                    source_has_explicit_ng = True
                    extracted_subtypes.add(extracted)
        saved_subtype = str(committed_now.get("natural_gas_subtype") or "").strip()
        if saved_subtype not in {"NG1", "NG2"} and saved_mapping is not None:
            saved_subtype = str(
                getattr(saved_mapping, "natural_gas_subtype", "unknown") or "unknown"
            )
        if source_has_explicit_ng:
            st.caption(t("intake.ng_type_from_file", lang))
            if len(extracted_subtypes) == 1:
                natural_gas_subtype = next(iter(extracted_subtypes))
            elif saved_subtype in {"NG1", "NG2"}:
                natural_gas_subtype = saved_subtype
            else:
                natural_gas_subtype = "unknown"
        else:
            ng_label_1 = t("intake.ng_option_1", lang)
            ng_label_2 = t("intake.ng_option_2", lang)
            ng_options = [ng_label_1, ng_label_2, unknown_label]
            if saved_subtype == "NG1":
                default_ng = ng_label_1
            elif saved_subtype == "NG2":
                default_ng = ng_label_2
            else:
                default_ng = unknown_label
            st.markdown(f"**{t('intake.ng_type', lang)}**")
            selected_ng = st.radio(
                t("intake.ng_type", lang),
                options=ng_options,
                index=ng_options.index(default_ng),
                key="intake_natural_gas_subtype",
                label_visibility="collapsed",
            )
            st.caption(t("intake.ng_type_help", lang))
            with st.expander(t("intake.ng_learn_title", lang), expanded=False):
                st.write(t("intake.ng_learn_body", lang))
            if selected_ng == ng_label_1:
                natural_gas_subtype = "NG1"
            elif selected_ng == ng_label_2:
                natural_gas_subtype = "NG2"
            else:
                natural_gas_subtype = "unknown"

    if "diesel" in mapped_types:
        diesel_options = [
            t("intake.diesel_company_vehicle", lang),
            unknown_label,
        ]
        source_has_vehicle_diesel = any(
            mapped == "diesel" and extract_diesel_vehicle_context_from_text(source)
            for source, mapped in activity_type_value_map.items()
        )
        saved_diesel = str(committed_now.get("diesel_context") or "").strip()
        if saved_diesel != "company_vehicle" and saved_mapping is not None:
            saved_diesel = str(
                getattr(saved_mapping, "diesel_context", "unknown") or "unknown"
            )
        if source_has_vehicle_diesel:
            diesel_context = "company_vehicle"
            st.caption(t("intake.diesel_company_vehicle", lang))
        else:
            default_diesel = (
                diesel_options[0]
                if saved_diesel == "company_vehicle"
                else unknown_label
            )
            st.markdown(f"**{t('intake.diesel_context', lang)}**")
            selected_diesel = st.radio(
                t("intake.diesel_context", lang),
                options=diesel_options,
                index=diesel_options.index(default_diesel),
                key="intake_diesel_context",
                label_visibility="collapsed",
            )
            st.caption(t("intake.diesel_context_help", lang))
            diesel_context = (
                "company_vehicle"
                if selected_diesel == t("intake.diesel_company_vehicle", lang)
                else "unknown"
            )

    if "grid_electricity" in mapped_types:
        elec_options = [
            t("intake.electricity_enterprise", lang),
            unknown_label,
        ]
        saved_elec = str(committed_now.get("electricity_context") or "").strip()
        if saved_elec != "enterprise" and saved_mapping is not None:
            saved_elec = str(
                getattr(saved_mapping, "electricity_context", "unknown")
                or "unknown"
            )
        default_elec = (
            elec_options[0] if saved_elec == "enterprise" else unknown_label
        )
        st.markdown(f"**{t('intake.electricity_context', lang)}**")
        selected_elec = st.radio(
            t("intake.electricity_context", lang),
            options=elec_options,
            index=elec_options.index(default_elec),
            key="intake_electricity_context",
            label_visibility="collapsed",
        )
        st.caption(t("intake.electricity_context_help", lang))
        electricity_context = (
            "enterprise"
            if selected_elec == t("intake.electricity_enterprise", lang)
            else "unknown"
        )

    st.markdown(f"**{t('intake.value_map_unit', lang)}**")
    unit_value_map: dict[str, str] = {}
    choose_label = t("intake.choose", lang)
    if unit_column:
        for source_value, suggestion in suggested_unit_map.items():
            default_unit = (
                suggestion if suggestion in UNIT_OPTIONS else choose_label
            )
            index = UNIT_OPTIONS.index(default_unit)
            selected_unit = st.selectbox(
                source_value,
                options=UNIT_OPTIONS,
                index=index,
                key=f"intake_unit_map_{source_value}",
            )
            unit_value_map[source_value] = (
                "" if selected_unit == choose_label else selected_unit
            )

    meta_cols = st.columns(2)
    with meta_cols[0]:
        source_name = st.text_input(
            t("intake.source_name", lang),
            value=table.file_name,
            key="intake_source_name",
        )
        site_id = ""
        if not site_column:
            site_id = st.text_input(
                t("intake.site_name", lang),
                value="",
                key="intake_site_id",
                placeholder=t("intake.site_placeholder", lang),
                help=t("intake.site_unknown_help", lang),
            )
    with meta_cols[1]:
        existing_doc = None
        raw_doc = committed.get("document_date")
        if raw_doc:
            try:
                existing_doc = date.fromisoformat(str(raw_doc)[:10])
            except ValueError:
                existing_doc = None
        document_date = st.date_input(
            t("intake.document_date", lang),
            value=existing_doc,
            key="intake_document_date",
        )
        quality_label = st.selectbox(
            t("intake.data_quality", lang),
            options=[label for _, label in QUALITY_OPTIONS],
            index=0,
            key="intake_data_quality",
        )

    confirmed_document_date = (
        document_date if isinstance(document_date, date) else existing_doc
    )
    if confirmed_document_date is None:
        st.info(t("intake.document_date_required", lang))

    if _action_button(
        t("intake.ex.editor_apply", lang),
        t("intake.draft_unapplied", lang),
        key="intake_apply_editor",
        primary=True,
    ):
        if confirmed_document_date is None:
            st.error(t("intake.document_date_required", lang))
            st.stop()
        next_committed = dict(_ensure_committed(table, detailed))
        next_committed["columns"] = dict(next_committed.get("columns") or {})
        next_committed["columns"]["activity_type"] = activity_type_column
        next_committed["columns"]["activity_value"] = activity_value_column
        next_committed["columns"]["unit"] = unit_column
        if site_column:
            next_committed["columns"]["site_id"] = site_column
        if fuel_subtype_column:
            next_committed["columns"]["fuel_subtype"] = fuel_subtype_column
        next_committed["date_mode"] = date_mode
        next_committed["year_month_confirmed"] = year_month_confirmed
        if year_month_column:
            next_committed["columns"]["year_month"] = year_month_column
        if start_date_column:
            next_committed["columns"]["activity_start_date"] = start_date_column
        if end_date_column:
            next_committed["columns"]["activity_end_date"] = end_date_column
        if period_start:
            next_committed["period_start"] = period_start.isoformat()
        if period_end:
            next_committed["period_end"] = period_end.isoformat()
        next_committed["activity_type_value_map"] = activity_type_value_map
        next_committed["unit_value_map"] = unit_value_map
        applied_ids = set(next_committed.get("applied_ids") or [])
        applied_ids.update(
            f"activity_value:{source}"
            for source, mapped in activity_type_value_map.items()
            if str(mapped or "").strip()
        )
        applied_ids.update(
            f"unit_value:{source}"
            for source, mapped in unit_value_map.items()
            if str(mapped or "").strip()
        )
        next_committed["applied_ids"] = sorted(applied_ids)
        next_committed["natural_gas_subtype"] = natural_gas_subtype
        next_committed["diesel_context"] = diesel_context
        next_committed["electricity_context"] = electricity_context
        next_committed["source_name"] = source_name.strip() or table.file_name
        next_committed["fallback_site_id"] = site_id.strip()
        next_committed["data_quality_tier"] = QUALITY_LABEL_TO_CODE.get(
            quality_label, "unknown"
        )
        if confirmed_document_date is not None:
            next_committed["document_date"] = confirmed_document_date.isoformat()
        previous_columns = dict(
            (_ensure_committed(table, detailed).get("columns") or {})
        )
        next_columns = dict(next_committed.get("columns") or {})
        for field_name, column in next_columns.items():
            answer = str(column or "").strip()
            if not answer:
                continue
            previous = str(previous_columns.get(field_name) or "").strip()
            if previous == answer:
                continue
            append_provenance_event(
                st.session_state,
                event=(
                    EVENT_CUSTOMER_CORRECTED
                    if previous
                    else EVENT_CUSTOMER_CONFIRMED
                ),
                company_ubn=confirmed_company_ubn(st.session_state),
                fingerprint=_table_fingerprint(table),
                field=field_name,
                proposed=previous,
                committed=answer,
                source="customer",
                reason="editor apply",
                source_document_id=_source_document_id(table),
            )
        st.session_state[STATE_INTAKE_COMMITTED] = next_committed
        st.session_state[STATE_INTAKE_SHOW_MAPPING_EDITOR] = False
        st.rerun()
    st.stop()

# Coverage review (step 3) and analysis start — no separate customer step 5.
if result is None:
    st.stop()

step = int(st.session_state.get(STATE_INTAKE_STEP, 3) or 3)
if step >= 4 and is_uploaded_analysis(st.session_state) and get_current_result(
    st.session_state
) is not None:
    if st.button(t("intake.step4", lang), key="intake_open_results"):
        st.switch_page("app_pages/dashboard.py")
    st.stop()
if step != 3:
    st.session_state[STATE_INTAKE_STEP] = 3
    step = 3

nav_cols = st.columns([1, 1, 2])
with nav_cols[0]:
    if st.button(t("intake.nav.back", lang), key="intake_nav_back_results"):
        st.session_state[STATE_INTAKE_STEP] = 2
        st.session_state[STATE_INTAKE_SHOW_MAPPING_EDITOR] = False
        st.session_state[STATE_INTAKE_RESULT] = None
        clear_duplicate_review_state(st.session_state)
        st.rerun()

st.write("")
render_section_header(t("intake.step3", lang))
render_steel_status_legend(lang)
render_steel_confirm_flash(lang)
pipeline = get_current_result(st.session_state)
render_confirmation_flash(pipeline, lang)
render_refrigerant_boundary_confirmation(pipeline, lang)
render_steel_pipeline_outcome(lang, pipeline)
_render_mapping_history()
rejected = result.rejected_rows
held_count = 0
cannot_count = 0
if rejected is not None and not getattr(rejected, "empty", True):
    codes = (
        rejected["issue_code"].tolist()
        if "issue_code" in rejected.columns
        else []
    )
    for code in codes:
        if str(code) in HELD_ISSUE_CODES:
            held_count += 1
        else:
            cannot_count += 1
accepted = accepted_activities_for_review(result.accepted_activities)
readiness_rows = _accepted_readiness_rows(accepted)
status_map = pipeline_calculation_status_by_record(
    get_current_result(st.session_state)
)
if readiness_rows.empty:
    ready_rows = readiness_rows.copy()
    accepted_needs_confirm = readiness_rows.copy()
    no_factor_rows = readiness_rows.copy()
    unsupported_rows = readiness_rows.copy()
else:
    ready_rows = readiness_rows[
        readiness_rows["_analysis_readiness"] == READINESS_READY
    ].copy()
    accepted_needs_confirm = readiness_rows[
        readiness_rows["_analysis_readiness"] == READINESS_NEEDS_CONFIRM
    ].copy()
    no_factor_rows = readiness_rows[
        readiness_rows["_analysis_readiness"] == READINESS_NO_MATCHING_FACTOR
    ].copy()
    unsupported_rows = readiness_rows[
        readiness_rows["_analysis_readiness"] == READINESS_UNSUPPORTED
    ].copy()
needs_confirm_count = held_count + len(accepted_needs_confirm)

with onboarding_target("calculation-coverage"):
    render_kpi_row(
        [
            (len(ready_rows), t("intake.result_accepted", lang), "teal"),
            (
                needs_confirm_count,
                t("intake.result_needs_confirm", lang),
                "amber",
            ),
            (
                len(no_factor_rows),
                t("intake.result_no_factor", lang),
                "amber",
            ),
            (
                len(unsupported_rows),
                t("intake.result_unsupported", lang),
                "blue",
            ),
            (cannot_count, t("intake.result_invalid", lang), "blue"),
        ],
        tour_target="coverage-summary",
    )
render_purchased_steel_confirmation_forms(
    accepted,
    lang,
    calculation_status_by_record=status_map,
)
tab_ok, tab_fix, tab_no_factor, tab_unsupported, tab_bad = st.tabs(
    [
        t("intake.result_accepted", lang),
        t("intake.result_needs_confirm", lang),
        t("intake.result_no_factor", lang),
        t("intake.result_unsupported", lang),
        t("intake.result_invalid", lang),
    ]
)
with tab_ok:
    if not ready_rows.empty:
        st.dataframe(
            _accepted_review_preview(
                ready_rows,
                status=t("intake.result_accepted", lang),
                issue="—",
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption(t("intake.empty.ready", lang))
with tab_fix:
    if not accepted_needs_confirm.empty:
        st.dataframe(
            _accepted_review_preview(
                accepted_needs_confirm,
                status=t("intake.result_needs_confirm", lang),
                issue=t("intake.issue.context_required", lang),
            ),
            hide_index=True,
            width="stretch",
        )
    if held_count > 0 and rejected is not None:
        held_rows = rejected[
            rejected["issue_code"].astype(str).isin(HELD_ISSUE_CODES)
        ].copy()
        if "issue_code" in held_rows.columns:
            held_rows["issue_message"] = [
                _safe_issue_message(str(code), str(message))
                for code, message in zip(
                    held_rows["issue_code"].tolist(),
                    held_rows["issue_message"].tolist(),
                    strict=True,
                )
            ]
        if "field" in held_rows.columns:
            held_rows["field"] = held_rows["field"].map(
                lambda name: customer_schema_label(str(name), lang)
            )
        held_rows = held_rows.rename(
            columns={
                "source_row": t("intake.rej.row", lang),
                "field": t("intake.rej.field", lang),
                "issue_message": t("intake.rej.issue", lang),
                "uploaded_value": t("intake.rej.value", lang),
            }
        )
        st.dataframe(
            held_rows[
                [
                    t("intake.rej.row", lang),
                    t("intake.rej.field", lang),
                    t("intake.rej.issue", lang),
                    t("intake.rej.value", lang),
                ]
            ],
            hide_index=True,
            width="stretch",
        )
    elif accepted_needs_confirm.empty:
        st.caption(t("intake.empty.needs_confirm", lang))
with tab_no_factor:
    if not no_factor_rows.empty:
        st.dataframe(
            _accepted_review_preview(
                no_factor_rows,
                status=t("intake.result_no_factor", lang),
                issue=t("intake.issue.steel_average_no_factor", lang),
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
            _accepted_review_preview(
                unsupported_rows,
                status=t("intake.result_unsupported", lang),
                issue=t("intake.issue.unsupported_activity", lang),
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption(t("intake.empty.unsupported", lang))
with tab_bad:
    if cannot_count > 0 and rejected is not None:
        bad_rows = rejected[
            ~rejected["issue_code"].astype(str).isin(HELD_ISSUE_CODES)
        ].copy()
        if "issue_code" in bad_rows.columns:
            bad_rows["issue_message"] = [
                _safe_issue_message(str(code), str(message))
                for code, message in zip(
                    bad_rows["issue_code"].tolist(),
                    bad_rows["issue_message"].tolist(),
                    strict=True,
                )
            ]
        if "field" in bad_rows.columns:
            bad_rows["field"] = bad_rows["field"].map(
                lambda name: customer_schema_label(str(name), lang)
            )
        bad_rows = bad_rows.rename(
            columns={
                "source_row": t("intake.rej.row", lang),
                "field": t("intake.rej.field", lang),
                "issue_message": t("intake.rej.issue", lang),
                "uploaded_value": t("intake.rej.value", lang),
            }
        )
        st.dataframe(
            bad_rows[
                [
                    t("intake.rej.row", lang),
                    t("intake.rej.field", lang),
                    t("intake.rej.issue", lang),
                    t("intake.rej.value", lang),
                ]
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption(t("intake.empty.invalid", lang))
duplicates_ready = _render_potential_duplicate_review(result)

st.write("")
st.markdown(t("intake.ready_body", lang, count=result.accepted_count))
st.markdown(t("intake.ready_next", lang))
st.markdown(
    f"**{t('intake.review.rows', lang)}：** {result.accepted_count}"
)
if accepted is not None and not accepted.empty:
    starts = pd.to_datetime(accepted["activity_start_date"], errors="coerce")
    ends = pd.to_datetime(accepted["activity_end_date"], errors="coerce")
    start_label = (
        starts.min().strftime("%Y-%m") if not starts.isna().all() else "—"
    )
    end_label = ends.max().strftime("%Y-%m") if not ends.isna().all() else "—"
    st.markdown(
        f"**{t('intake.review.period', lang)}：** {start_label} "
        f"{t('intake.review.period_to', lang)} {end_label}"
    )
    site_values = sorted(
        {
            customer_site_display(value, lang)
            for value in accepted["site_id"].tolist()
        }
    )
    st.markdown(
        f"**{t('intake.field.site_id', lang)}：** {'、'.join(site_values) or '—'}"
    )
    type_count = int(accepted["activity_type"].nunique())
    st.markdown(f"**{t('intake.review.activity_types', lang)}：** {type_count}")
    readiness = summarize_pre_analysis_readiness(accepted)
    st.markdown(
        f"**{t('intake.review.ready', lang)}：** "
        f"{readiness.get('ready', 0)}"
    )
    st.markdown(
        f"**{t('intake.review.needs_confirm', lang)}：** "
        f"{readiness.get('needs_confirm', 0)}"
    )
    st.markdown(
        f"**{t('intake.review.no_factor', lang)}：** "
        f"{int(len(no_factor_rows))}"
    )
    st.markdown(
        f"**{t('intake.review.unsupported', lang)}：** "
        f"{readiness.get('unsupported', 0)}"
    )
st.markdown(
    f"**{t('intake.review.pending', lang)}：** {held_count}"
)
st.caption(
    f"{t('intake.file_name', lang)}: "
    f"{st.session_state.get(STATE_INTAKE_FILE_NAME) or '—'}"
)
if result.accepted_count > 0 and duplicates_ready:
    with onboarding_target("start-analysis"):
        st.markdown(
            "<span data-cel-tour-target='coverage-cta'></span>",
            unsafe_allow_html=True,
        )
        if st.button(
            t("intake.start_analysis", lang),
            type="primary",
            use_container_width=True,
            key="intake_start_uploaded_analysis",
        ):
            st.session_state[STATE_RUN_UPLOADED_REQUEST] = True
            st.rerun()
elif result.accepted_count <= 0:
    st.info(t("intake.next_phase", lang))
