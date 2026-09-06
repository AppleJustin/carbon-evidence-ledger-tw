"""Session-state helpers for the Streamlit product workspace.

Keeps at most one PipelineRunResult in memory and avoids re-running the
pipeline on ordinary page navigation or language changes.

Stage 3B.3: CUSTOMER mode starts empty — demo analysis is never auto-run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from carbon_ledger.pipeline import (
    PipelineRunResult,
    ProgressCallback,
    run_demo_pipeline,
    run_uploaded_pipeline,
)
from carbon_ledger.ui.app_mode import (
    STATE_APP_MODE,
    AppMode,
    ensure_app_mode,
    set_app_mode,
)
from carbon_ledger.ui.i18n import DEFAULT_LANG, STATE_LANGUAGE, normalize_lang
from carbon_ledger.ui.tutorial import (
    STATE_TUTORIAL_KEEP_OPEN,
    STATE_TUTORIAL_OPEN_COUNT,
    STATE_TUTORIAL_VISIBLE,
    ensure_tutorial_state,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN_ID = "ui_demo"
UPLOADED_RUN_ID = "ui_uploaded"
FIXED_INGESTED_AT = pd.Timestamp("2024-02-01T00:00:00Z")

ANALYSIS_SOURCE_DEMO = "demo"
ANALYSIS_SOURCE_UPLOADED = "uploaded"
ANALYSIS_SOURCE_NONE = ""
STATE_ANALYSIS_RUNNING = "analysis_running"
STATE_ANALYSIS_PHASE = "analysis_phase"
STATE_ANALYSIS_FAILURE = "analysis_failure_message"
ANALYSIS_PHASE_IDLE = "idle"
ANALYSIS_PHASE_ANALYZING = "analyzing"
ANALYSIS_PHASE_COMPLETE = "analysis_complete"
ANALYSIS_PHASE_CLOSING = "overlay_closing"
ANALYSIS_PHASE_REVEAL = "result_reveal"
ANALYSIS_PHASE_FAILED = "failed"

STATE_RESULT = "pipeline_result"
STATE_RESULT_ENGINE_REVISION = "pipeline_result_engine_revision"
STATE_INCLUDE_GHG = "include_ghg"
STATE_INCLUDE_CBAM = "include_cbam"
STATE_INCLUDE_IFRS = "include_ifrs_s2"
STATE_RUN_ID = "run_id"
STATE_LAST_CONFIG = "last_run_config"
STATE_INITIALIZED = "ui_initialized"
STATE_ERROR = "ui_error"
STATE_FOCUS_RECORD = "focus_record_id"
STATE_RUN_ANALYSIS_REQUEST = "run_analysis_request"
STATE_RUN_UPLOADED_REQUEST = "run_uploaded_analysis_request"
STATE_NAVIGATE_TO_RESULTS = "navigate_to_results_after_analysis"
STATE_ANALYSIS_UPLOADED_MODE = "analysis_uploaded_mode"
STATE_RESULT_REVEAL_PENDING = "result_reveal_pending_token"
STATE_LAST_ANIMATED_RESULT = "last_animated_result_token"
STATE_HERO_EMISSIONS_PLAY = "hero_emissions_play_token"
STATE_ANIMATION_RUN = "analysis_animation_run"
STATE_COUNTUP_RUNTIME_READY = "countup_runtime_ready"

STATE_ANALYSIS_SOURCE = "analysis_data_source"
STATE_ANALYSIS_FILE_NAME = "analysis_source_file_name"
STATE_ANALYSIS_PERIOD_START = "analysis_period_start"
STATE_ANALYSIS_PERIOD_END = "analysis_period_end"
STATE_ANALYSIS_ACTIVITY_COUNT = "analysis_activity_count"
STATE_UPLOADED_ANALYSIS_COMPLETED = "uploaded_analysis_completed"
# Identity of the uploaded file behind the stored result ("" for demo runs).
STATE_ANALYSIS_FILE_HASH = "analysis_source_file_hash"
# Bump this whenever uploaded-intake interpretation or inventory inclusion
# semantics change.  Streamlit can reconnect an existing browser session after
# a deployment, so an in-memory PipelineRunResult produced by older code must
# never be presented as if it came from the current analysis engine.
ANALYSIS_ENGINE_REVISION = "uploaded-intake-2026-09-02-v2"
STATE_ANALYSIS_ENGINE_REVISION = "analysis_engine_revision"

# Phase 9A structured intake (session-only; never written to disk)
STATE_INTAKE_FILE_HASH = "uploaded_file_hash"
STATE_INTAKE_FILE_NAME = "uploaded_file_name"
STATE_INTAKE_TABLE = "uploaded_table"
STATE_INTAKE_BYTES = "uploaded_file_bytes"
STATE_INTAKE_SHEET = "intake_selected_sheet"
STATE_INTAKE_SHEET_CONFIRMED = "intake_sheet_confirmed"
STATE_INTAKE_HEADER_ROW = "intake_header_row"
STATE_INTAKE_HEADER_CONFIRMED = "intake_header_confirmed"
STATE_INTAKE_YEAR_MONTH_CONFIRMED = "intake_year_month_confirmed"
STATE_INTAKE_SHOW_MAPPING_EDITOR = "intake_show_mapping_editor"
STATE_INTAKE_COMMITTED = "intake_committed_decisions"
STATE_INTAKE_MAPPING = "intake_mapping"
STATE_INTAKE_METADATA = "intake_metadata"
STATE_INTAKE_RESULT = "validated_intake_result"
STATE_INTAKE_STEP = "intake_wizard_step"
STATE_INTAKE_EXCEPTION_CURSOR = "intake_exception_cursor"
STATE_INTAKE_DUPLICATE_REVIEW = "intake_duplicate_review"
STATE_INTAKE_SHOW_DUPLICATE_REVIEW = "intake_show_duplicate_review"
STATE_INTAKE_MEMORY_CHOICE = "intake_memory_choice"
STATE_INTAKE_MEMORY_APPLIED = "intake_memory_applied"
STATE_INTAKE_MEMORY_OFFERED = "intake_memory_offered_fp"
STATE_INTAKE_SUGGESTIONS_RECORDED = "intake_suggestions_recorded_for"
# Session-scoped mapping memory/provenance: survive _reset_for_new_file.
STATE_INTAKE_MAPPING_MEMORY = "intake_mapping_memory"
STATE_INTAKE_MAPPING_PROVENANCE = "intake_mapping_provenance"
STATE_ACTIVITY_BOUNDARY_DECISIONS = "activity_boundary_decisions"
STATE_BOUNDARY_CONFIRM_FLASH = "activity_boundary_confirm_flash"
STATE_PURCHASED_STEEL_CONFIRMATIONS = "purchased_steel_confirmations"
STATE_STEEL_CONFIRM_FLASH = "purchased_steel_confirm_flash"
STATE_INTAKE_VALIDATION_REQUESTED = "intake_validation_requested"
STATE_INTAKE_VALIDATION_RUNNING = "intake_validation_running"
STATE_INTAKE_VALIDATION_ERROR = "intake_validation_error"
DUPLICATE_WIDGET_PREFIX = "intake_dup_"

# Stage 3B company profile + applicability assessment (session-only)
STATE_COMPANY_PROFILE = "company_profile"
STATE_APPLICABILITY_ASSESSMENT = "applicability_assessment"
STATE_COMPANY_PROFILE_EDITING = "company_profile_editing"
STATE_APPLICABILITY_WIZARD_STEP = "applicability_wizard_step"
STATE_COMPANY_MASTER = "company_master"
STATE_FACILITY_MASTER = "facility_master"
STATE_COMPANY_LOOKUP_MANUAL = "company_lookup_manual"
STATE_COMPANY_LOOKUP_NOT_FOUND = "company_lookup_not_found"
STATE_CAPITAL_LOOKUP_GEN = "capital_lookup_generation"
STATE_CAPITAL_PLAY_UBN = "capital_play_ubn"
STATE_CAPITAL_RUNTIME_READY = "capital_countup_runtime_ready"
STATE_FACILITY_EXCEPTION_MODE = "facility_exception_mode"
STATE_FACILITY_EXCEPTION_DIRTY = "facility_exception_draft_dirty"
STATE_IFRS_TIMELINE_LAST_RUN = "ifrs_timeline_last_run"
STATE_IFRS_TIMELINE_RUNTIME_READY = "ifrs_timeline_runtime_ready"
STATE_WIZARD_MAX_STEP = 4
STATE_BOUNDARY_WIZARD_STEP = "boundary_wizard_step"
STATE_BOUNDARY_TASK_INDEX = "boundary_wizard_task_index"
STATE_BOUNDARY_COMPANY_INDEX = "boundary_wizard_company_index"
STATE_BOUNDARY_SITE_INDEX = "boundary_wizard_site_index"
STATE_BOUNDARY_SITE_CARD = "boundary_wizard_site_card"
STATE_BOUNDARY_RECONCILIATION_INDEX = "boundary_wizard_reconciliation_index"
STATE_BOUNDARY_OPERATING_INDEX = "boundary_wizard_operating_index"
STATE_BOUNDARY_MEMBERSHIP_INDEX = "boundary_wizard_membership_index"
STATE_BOUNDARY_EVIDENCE_INDEX = "boundary_wizard_evidence_index"
STATE_BOUNDARY_WIZARD_DEFERRED = "boundary_wizard_deferred"
STATE_BOUNDARY_WIZARD_RESULTS = "boundary_wizard_results_visible"


def _ss_get(session_state: Any, key: str, default: Any = None) -> Any:
    """Read session state without relying on SessionState.get (AppTest-safe)."""
    try:
        if key in session_state:
            return session_state[key]
    except Exception:  # noqa: BLE001 - AppTest proxies vary
        pass
    try:
        return session_state[key]
    except Exception:  # noqa: BLE001
        return default


def _default_adapter_flags() -> dict[str, bool]:
    return {
        STATE_INCLUDE_GHG: True,
        # V1 product hides CBAM; backend capability remains for future V2.
        STATE_INCLUDE_CBAM: False,
        STATE_INCLUDE_IFRS: True,
    }


def get_language(session_state: Any) -> str:
    """Return the active UI language code."""
    return normalize_lang(_ss_get(session_state, STATE_LANGUAGE, DEFAULT_LANG))


def set_language(session_state: Any, lang: str) -> None:
    """Store UI language without touching pipeline results."""
    session_state[STATE_LANGUAGE] = normalize_lang(lang)
    if bool(_ss_get(session_state, STATE_TUTORIAL_VISIBLE)):
        session_state[STATE_TUTORIAL_KEEP_OPEN] = True


def activity_period_bounds(
    activities: pd.DataFrame,
) -> tuple[str | None, str | None]:
    """Return YYYY-MM start/end labels from activity date columns."""
    if activities is None or activities.empty:
        return None, None
    starts = activities.get("activity_start_date")
    ends = activities.get("activity_end_date")
    if starts is None or ends is None:
        return None, None
    start_ts = pd.to_datetime(starts, errors="coerce").dropna()
    end_ts = pd.to_datetime(ends, errors="coerce").dropna()
    if start_ts.empty or end_ts.empty:
        return None, None
    start_label = pd.Timestamp(start_ts.min()).strftime("%Y-%m")
    end_label = pd.Timestamp(end_ts.max()).strftime("%Y-%m")
    return start_label, end_label


def format_data_period_label(start: str | None, end: str | None) -> str:
    """Format YYYY-MM bounds as a customer-facing data-period label."""
    start_text = str(start or "").strip()
    end_text = str(end or "").strip()
    if start_text and end_text:
        return f"{start_text}－{end_text}"
    return start_text or end_text


def uploaded_data_period_bounds(
    session_state: Any,
) -> tuple[str | None, str | None]:
    """Data period from accepted uploaded activities, never company FY."""
    intake = get_intake_result(session_state)
    accepted = getattr(intake, "accepted_activities", None)
    start, end = activity_period_bounds(accepted)
    if start and end:
        return start, end
    return (
        _ss_get(session_state, STATE_ANALYSIS_PERIOD_START),
        _ss_get(session_state, STATE_ANALYSIS_PERIOD_END),
    )


def _store_analysis_source_demo(session_state: Any, result: PipelineRunResult) -> None:
    session_state[STATE_RESULT_ENGINE_REVISION] = ANALYSIS_ENGINE_REVISION
    session_state[STATE_ANALYSIS_SOURCE] = ANALYSIS_SOURCE_DEMO
    session_state[STATE_ANALYSIS_FILE_NAME] = None
    session_state[STATE_ANALYSIS_FILE_HASH] = ""
    start, end = activity_period_bounds(result.activity_records_accepted)
    session_state[STATE_ANALYSIS_PERIOD_START] = start
    session_state[STATE_ANALYSIS_PERIOD_END] = end
    session_state[STATE_ANALYSIS_ACTIVITY_COUNT] = int(
        len(result.activity_records_accepted)
    )
    session_state[STATE_UPLOADED_ANALYSIS_COMPLETED] = False


def _store_analysis_source_uploaded(
    session_state: Any,
    result: PipelineRunResult,
    *,
    file_name: str,
) -> None:
    session_state[STATE_RESULT_ENGINE_REVISION] = ANALYSIS_ENGINE_REVISION
    session_state[STATE_ANALYSIS_SOURCE] = ANALYSIS_SOURCE_UPLOADED
    session_state[STATE_ANALYSIS_FILE_NAME] = file_name
    # Which uploaded file this result belongs to. Lets callers tell a current
    # result apart from a demo run or a previously uploaded file.
    session_state[STATE_ANALYSIS_FILE_HASH] = str(
        _ss_get(session_state, STATE_INTAKE_FILE_HASH, "") or ""
    )
    intake = get_intake_result(session_state)
    accepted = getattr(intake, "accepted_activities", None)
    start, end = activity_period_bounds(
        accepted if accepted is not None else result.activity_records_accepted
    )
    session_state[STATE_ANALYSIS_PERIOD_START] = start
    session_state[STATE_ANALYSIS_PERIOD_END] = end
    session_state[STATE_ANALYSIS_ACTIVITY_COUNT] = int(
        len(result.activity_records_accepted)
    )
    session_state[STATE_UPLOADED_ANALYSIS_COMPLETED] = True


def get_analysis_source(session_state: Any) -> str:
    """Return demo, uploaded, or empty when no analysis is active."""
    value = _ss_get(session_state, STATE_ANALYSIS_SOURCE, ANALYSIS_SOURCE_NONE)
    if value == ANALYSIS_SOURCE_UPLOADED:
        return ANALYSIS_SOURCE_UPLOADED
    if value == ANALYSIS_SOURCE_DEMO:
        return ANALYSIS_SOURCE_DEMO
    return ANALYSIS_SOURCE_NONE


def is_uploaded_analysis(session_state: Any) -> bool:
    """True when the active pipeline result came from uploaded company data."""
    return get_analysis_source(session_state) == ANALYSIS_SOURCE_UPLOADED


def has_validated_uploaded_data(session_state: Any) -> bool:
    """True when intake validation produced at least one accepted activity."""
    intake = get_intake_result(session_state)
    if intake is None:
        return False
    accepted = getattr(intake, "accepted_activities", None)
    count = int(getattr(intake, "accepted_count", 0) or 0)
    if accepted is None or getattr(accepted, "empty", True):
        return False
    return count > 0


def get_analysis_source_summary(session_state: Any) -> dict[str, Any]:
    """Return beginner-facing labels for the active analysis dataset."""
    source = get_analysis_source(session_state)
    if source == ANALYSIS_SOURCE_UPLOADED:
        file_name = _ss_get(
            session_state, STATE_ANALYSIS_FILE_NAME
        ) or _ss_get(session_state, STATE_INTAKE_FILE_NAME)
        start, end = uploaded_data_period_bounds(session_state)
        return {
            "source": source,
            "file_name": str(file_name or "").strip() or "uploaded_file",
            "period_start": start,
            "period_end": end,
            "activity_count": int(
                _ss_get(session_state, STATE_ANALYSIS_ACTIVITY_COUNT) or 0
            ),
            "is_demo": False,
        }
    if source == ANALYSIS_SOURCE_DEMO:
        return {
            "source": ANALYSIS_SOURCE_DEMO,
            "file_name": None,
            "period_start": _ss_get(session_state, STATE_ANALYSIS_PERIOD_START),
            "period_end": _ss_get(session_state, STATE_ANALYSIS_PERIOD_END),
            "activity_count": int(
                _ss_get(session_state, STATE_ANALYSIS_ACTIVITY_COUNT) or 0
            ),
            "is_demo": True,
        }
    return {
        "source": ANALYSIS_SOURCE_NONE,
        "file_name": None,
        "period_start": None,
        "period_end": None,
        "activity_count": 0,
        "is_demo": False,
    }


def initialize_ui_state(session_state: Any, *, force: bool = False) -> None:
    """Ensure session defaults exist. CUSTOMER mode does not auto-run demo."""
    _invalidate_stale_uploaded_analysis(session_state)
    defaults = _default_adapter_flags()
    ensure_app_mode(session_state)
    if STATE_LANGUAGE not in session_state:
        session_state[STATE_LANGUAGE] = DEFAULT_LANG
    else:
        session_state[STATE_LANGUAGE] = normalize_lang(
            session_state[STATE_LANGUAGE]
        )
    if STATE_INCLUDE_GHG not in session_state:
        session_state[STATE_INCLUDE_GHG] = defaults[STATE_INCLUDE_GHG]
    if STATE_INCLUDE_CBAM not in session_state:
        session_state[STATE_INCLUDE_CBAM] = defaults[STATE_INCLUDE_CBAM]
    if STATE_INCLUDE_IFRS not in session_state:
        session_state[STATE_INCLUDE_IFRS] = defaults[STATE_INCLUDE_IFRS]
    if STATE_RUN_ID not in session_state:
        session_state[STATE_RUN_ID] = DEFAULT_RUN_ID
    if STATE_ERROR not in session_state:
        session_state[STATE_ERROR] = None
    if STATE_FOCUS_RECORD not in session_state:
        session_state[STATE_FOCUS_RECORD] = None
    if STATE_RUN_ANALYSIS_REQUEST not in session_state:
        session_state[STATE_RUN_ANALYSIS_REQUEST] = False
    if STATE_RUN_UPLOADED_REQUEST not in session_state:
        session_state[STATE_RUN_UPLOADED_REQUEST] = False
    if STATE_NAVIGATE_TO_RESULTS not in session_state:
        session_state[STATE_NAVIGATE_TO_RESULTS] = False
    if STATE_ANALYSIS_UPLOADED_MODE not in session_state:
        session_state[STATE_ANALYSIS_UPLOADED_MODE] = False
    if STATE_RESULT_REVEAL_PENDING not in session_state:
        session_state[STATE_RESULT_REVEAL_PENDING] = None
    if STATE_LAST_ANIMATED_RESULT not in session_state:
        session_state[STATE_LAST_ANIMATED_RESULT] = None
    if STATE_HERO_EMISSIONS_PLAY not in session_state:
        session_state[STATE_HERO_EMISSIONS_PLAY] = None
    if STATE_ANIMATION_RUN not in session_state:
        session_state[STATE_ANIMATION_RUN] = None
    if STATE_COUNTUP_RUNTIME_READY not in session_state:
        session_state[STATE_COUNTUP_RUNTIME_READY] = False
    if STATE_ANALYSIS_SOURCE not in session_state:
        session_state[STATE_ANALYSIS_SOURCE] = ANALYSIS_SOURCE_NONE
    if STATE_UPLOADED_ANALYSIS_COMPLETED not in session_state:
        session_state[STATE_UPLOADED_ANALYSIS_COMPLETED] = False
    if STATE_INTAKE_STEP not in session_state:
        session_state[STATE_INTAKE_STEP] = 1
    if STATE_INTAKE_EXCEPTION_CURSOR not in session_state:
        session_state[STATE_INTAKE_EXCEPTION_CURSOR] = 0
    if STATE_INTAKE_DUPLICATE_REVIEW not in session_state:
        session_state[STATE_INTAKE_DUPLICATE_REVIEW] = {}
    if STATE_INTAKE_SHOW_DUPLICATE_REVIEW not in session_state:
        session_state[STATE_INTAKE_SHOW_DUPLICATE_REVIEW] = False
    if STATE_ACTIVITY_BOUNDARY_DECISIONS not in session_state:
        session_state[STATE_ACTIVITY_BOUNDARY_DECISIONS] = []
    if STATE_PURCHASED_STEEL_CONFIRMATIONS not in session_state:
        session_state[STATE_PURCHASED_STEEL_CONFIRMATIONS] = []
    if STATE_STEEL_CONFIRM_FLASH not in session_state:
        session_state[STATE_STEEL_CONFIRM_FLASH] = None
    if STATE_COMPANY_PROFILE not in session_state:
        session_state[STATE_COMPANY_PROFILE] = {}
    if STATE_APPLICABILITY_ASSESSMENT not in session_state:
        session_state[STATE_APPLICABILITY_ASSESSMENT] = None
    if STATE_COMPANY_PROFILE_EDITING not in session_state:
        session_state[STATE_COMPANY_PROFILE_EDITING] = True
    if STATE_COMPANY_MASTER not in session_state:
        session_state[STATE_COMPANY_MASTER] = {}
    if STATE_FACILITY_MASTER not in session_state:
        session_state[STATE_FACILITY_MASTER] = {}
    if STATE_COMPANY_LOOKUP_MANUAL not in session_state:
        session_state[STATE_COMPANY_LOOKUP_MANUAL] = False
    if STATE_COMPANY_LOOKUP_NOT_FOUND not in session_state:
        session_state[STATE_COMPANY_LOOKUP_NOT_FOUND] = False
    if STATE_CAPITAL_LOOKUP_GEN not in session_state:
        session_state[STATE_CAPITAL_LOOKUP_GEN] = 0
    if STATE_CAPITAL_PLAY_UBN not in session_state:
        session_state[STATE_CAPITAL_PLAY_UBN] = ""
    if STATE_CAPITAL_RUNTIME_READY not in session_state:
        session_state[STATE_CAPITAL_RUNTIME_READY] = False
    if STATE_FACILITY_EXCEPTION_MODE not in session_state:
        session_state[STATE_FACILITY_EXCEPTION_MODE] = False
    if STATE_FACILITY_EXCEPTION_DIRTY not in session_state:
        session_state[STATE_FACILITY_EXCEPTION_DIRTY] = False
    if STATE_IFRS_TIMELINE_LAST_RUN not in session_state:
        session_state[STATE_IFRS_TIMELINE_LAST_RUN] = ""
    if STATE_IFRS_TIMELINE_RUNTIME_READY not in session_state:
        session_state[STATE_IFRS_TIMELINE_RUNTIME_READY] = False
    if STATE_TUTORIAL_OPEN_COUNT not in session_state:
        session_state[STATE_TUTORIAL_OPEN_COUNT] = 0
    if STATE_ANALYSIS_RUNNING not in session_state:
        session_state[STATE_ANALYSIS_RUNNING] = False
    if STATE_ANALYSIS_PHASE not in session_state:
        session_state[STATE_ANALYSIS_PHASE] = ANALYSIS_PHASE_IDLE
    if STATE_ANALYSIS_FAILURE not in session_state:
        session_state[STATE_ANALYSIS_FAILURE] = None
    if STATE_RESULT not in session_state:
        session_state[STATE_RESULT] = None
    if STATE_INTAKE_VALIDATION_REQUESTED not in session_state:
        session_state[STATE_INTAKE_VALIDATION_REQUESTED] = False
    if STATE_INTAKE_VALIDATION_RUNNING not in session_state:
        session_state[STATE_INTAKE_VALIDATION_RUNNING] = False
    if STATE_INTAKE_VALIDATION_ERROR not in session_state:
        session_state[STATE_INTAKE_VALIDATION_ERROR] = None
    ensure_tutorial_state(session_state)
    normalize_intake_wizard_step(session_state)

    if bool(_ss_get(session_state, STATE_INITIALIZED)) and not force:
        return
    # No automatic demo pipeline — CUSTOMER starts empty.
    session_state[STATE_INITIALIZED] = True


def _invalidate_stale_uploaded_analysis(session_state: Any) -> None:
    """Drop derived upload state created by an older analysis engine.

    Raw uploaded bytes/table and company settings are intentionally retained so
    the customer can re-confirm the same file without uploading it again.  The
    mapping, validation and pipeline result are all derived values and must be
    rebuilt together; keeping only some of them is what previously allowed an
    old 2026/26.27 result to survive after the corrected parser was deployed.
    """
    stored_revision = str(
        _ss_get(session_state, STATE_ANALYSIS_ENGINE_REVISION, "") or ""
    )
    if stored_revision == ANALYSIS_ENGINE_REVISION:
        return

    has_uploaded_state = any(
        _ss_get(session_state, key) is not None
        for key in (
            STATE_INTAKE_TABLE,
            STATE_INTAKE_RESULT,
            STATE_INTAKE_MAPPING,
            STATE_INTAKE_COMMITTED,
        )
    ) or bool(_ss_get(session_state, STATE_UPLOADED_ANALYSIS_COMPLETED, False))

    if has_uploaded_state:
        for key in (
            STATE_RESULT,
            STATE_RESULT_ENGINE_REVISION,
            STATE_LAST_CONFIG,
            STATE_INTAKE_COMMITTED,
            STATE_INTAKE_MAPPING,
            STATE_INTAKE_METADATA,
            STATE_INTAKE_RESULT,
            STATE_INTAKE_MAPPING_MEMORY,
            STATE_INTAKE_MAPPING_PROVENANCE,
            STATE_INTAKE_MEMORY_CHOICE,
            STATE_INTAKE_MEMORY_APPLIED,
            STATE_INTAKE_MEMORY_OFFERED,
            STATE_INTAKE_SUGGESTIONS_RECORDED,
        ):
            try:
                session_state[key] = None
            except Exception:  # noqa: BLE001 - AppTest proxies vary
                pass
        session_state[STATE_ANALYSIS_SOURCE] = ANALYSIS_SOURCE_NONE
        session_state[STATE_ANALYSIS_FILE_NAME] = None
        session_state[STATE_ANALYSIS_FILE_HASH] = ""
        session_state[STATE_ANALYSIS_PERIOD_START] = None
        session_state[STATE_ANALYSIS_PERIOD_END] = None
        session_state[STATE_ANALYSIS_ACTIVITY_COUNT] = 0
        session_state[STATE_UPLOADED_ANALYSIS_COMPLETED] = False
        session_state[STATE_RUN_UPLOADED_REQUEST] = False
        session_state[STATE_ANALYSIS_RUNNING] = False
        session_state[STATE_ANALYSIS_PHASE] = ANALYSIS_PHASE_IDLE
        session_state[STATE_ANALYSIS_FAILURE] = None
        session_state[STATE_INTAKE_VALIDATION_REQUESTED] = False
        session_state[STATE_INTAKE_VALIDATION_RUNNING] = False
        session_state[STATE_INTAKE_VALIDATION_ERROR] = None
        session_state[STATE_INTAKE_STEP] = (
            2 if _ss_get(session_state, STATE_INTAKE_TABLE) is not None else 1
        )

    session_state[STATE_ANALYSIS_ENGINE_REVISION] = ANALYSIS_ENGINE_REVISION


def normalize_intake_wizard_step(session_state: Any) -> int:
    """Map legacy 1–5 intake steps onto the four-step customer journey."""
    raw = _ss_get(session_state, STATE_INTAKE_STEP, 1)
    try:
        stored = int(raw or 1)
    except (TypeError, ValueError):
        stored = 1
    has_table = _ss_get(session_state, STATE_INTAKE_TABLE) is not None
    has_result = _ss_get(session_state, STATE_INTAKE_RESULT) is not None
    uploaded_done = bool(_ss_get(session_state, STATE_UPLOADED_ANALYSIS_COMPLETED))
    uploaded_result = is_uploaded_analysis(session_state) and (
        get_current_result(session_state) is not None
    )
    if stored <= 1:
        step = 1
    elif stored == 2:
        step = 2
    elif stored == 3:
        step = 3 if has_result else 2
    elif stored == 4:
        if uploaded_done or uploaded_result:
            step = 4
        elif has_result:
            step = 3
        else:
            step = 2
    elif stored == 5:
        if uploaded_done or uploaded_result:
            step = 4
        elif has_result:
            step = 3
        else:
            step = 2
    else:
        if uploaded_done or uploaded_result:
            step = 4
        elif has_result:
            step = 3
        elif has_table:
            step = 2
        else:
            step = 1
    if step >= 3 and not has_result:
        step = 2 if has_table else 1
    if step == 4 and not (uploaded_done or uploaded_result):
        step = 3 if has_result else (2 if has_table else 1)
    session_state[STATE_INTAKE_STEP] = step
    return step


def activate_demo_mode(session_state: Any, *, force: bool = False) -> PipelineRunResult:
    """Explicitly load synthetic demo analysis (Demo Mode)."""
    set_app_mode(session_state, AppMode.DEMO)
    if (
        not force
        and get_current_result(session_state) is not None
        and get_analysis_source(session_state) == ANALYSIS_SOURCE_DEMO
    ):
        return get_current_result(session_state)  # type: ignore[return-value]
    return run_analysis(
        session_state,
        include_ghg=bool(_ss_get(session_state, STATE_INCLUDE_GHG, True)),
        include_cbam=bool(_ss_get(session_state, STATE_INCLUDE_CBAM, False)),
        include_ifrs_s2=bool(_ss_get(session_state, STATE_INCLUDE_IFRS, True)),
        run_id=DEFAULT_RUN_ID,
    )


def clear_analysis_result(session_state: Any) -> None:
    """Clear stored analysis so customer empty-state returns."""
    session_state[STATE_RESULT] = None
    session_state[STATE_RESULT_ENGINE_REVISION] = None
    session_state[STATE_ANALYSIS_SOURCE] = ANALYSIS_SOURCE_NONE
    session_state[STATE_UPLOADED_ANALYSIS_COMPLETED] = False
    session_state[STATE_ANALYSIS_FILE_HASH] = ""
    session_state[STATE_RESULT_REVEAL_PENDING] = None
    session_state[STATE_HERO_EMISSIONS_PLAY] = None
    session_state[STATE_ANALYSIS_RUNNING] = False
    session_state[STATE_ANALYSIS_PHASE] = ANALYSIS_PHASE_IDLE
    session_state[STATE_ANALYSIS_FAILURE] = None
    session_state[STATE_COUNTUP_RUNTIME_READY] = False


def is_synthetic_analysis(session_state: Any) -> bool:
    """True when the active analysis came from explicit Demo Mode fixtures."""
    return get_analysis_source(session_state) == ANALYSIS_SOURCE_DEMO


def run_analysis(
    session_state: Any,
    *,
    include_ghg: bool,
    include_cbam: bool,
    include_ifrs_s2: bool,
    run_id: str = DEFAULT_RUN_ID,
    repo_root: Path | None = None,
    progress_callback: ProgressCallback | None = None,
) -> PipelineRunResult:
    """Execute the reproducible demo pipeline and store the result."""
    session_state[STATE_ERROR] = None
    session_state[STATE_ANALYSIS_RUNNING] = True
    session_state[STATE_RESULT] = None
    session_state[STATE_HERO_EMISSIONS_PLAY] = None
    session_state[STATE_RESULT_REVEAL_PENDING] = None
    session_state[STATE_LAST_ANIMATED_RESULT] = None
    session_state[STATE_COUNTUP_RUNTIME_READY] = False
    try:
        result = run_demo_pipeline(
            Path(repo_root) if repo_root is not None else REPO_ROOT,
            run_id=run_id,
            ingested_at=FIXED_INGESTED_AT,
            include_ghg=include_ghg,
            include_cbam=include_cbam,
            include_ifrs_s2=include_ifrs_s2,
            progress_callback=progress_callback,
        )
    except Exception as exc:  # noqa: BLE001 - surface as UI error text
        session_state[STATE_ERROR] = str(exc)
        session_state[STATE_ANALYSIS_RUNNING] = False
        raise

    session_state[STATE_RESULT] = result
    session_state[STATE_INCLUDE_GHG] = include_ghg
    session_state[STATE_INCLUDE_CBAM] = include_cbam
    session_state[STATE_INCLUDE_IFRS] = include_ifrs_s2
    session_state[STATE_RUN_ID] = result.run_id
    session_state[STATE_LAST_CONFIG] = {
        "run_id": result.run_id,
        "ingested_at": "2024-02-01T00:00:00+00:00",
        "include_ghg": include_ghg,
        "include_cbam": include_cbam,
        "include_ifrs_s2": include_ifrs_s2,
        "analysis_data_source": ANALYSIS_SOURCE_DEMO,
    }
    _store_analysis_source_demo(session_state, result)
    set_app_mode(session_state, AppMode.DEMO)
    session_state[STATE_INITIALIZED] = True
    session_state[STATE_RUN_ANALYSIS_REQUEST] = False
    session_state[STATE_RUN_UPLOADED_REQUEST] = False
    session_state[STATE_ANALYSIS_RUNNING] = False
    return result


def run_uploaded_analysis(
    session_state: Any,
    *,
    include_ghg: bool | None = None,
    include_cbam: bool | None = None,
    include_ifrs_s2: bool | None = None,
    run_id: str = UPLOADED_RUN_ID,
    repo_root: Path | None = None,
    progress_callback: ProgressCallback | None = None,
) -> PipelineRunResult:
    """Analyze the currently validated uploaded dataset (never demo raw)."""
    intake = get_intake_result(session_state)
    if intake is None:
        raise ValueError("No validated uploaded intake result is available.")
    accepted = getattr(intake, "accepted_activities", None)
    documents = getattr(intake, "source_documents", None)
    if accepted is None or getattr(accepted, "empty", True):
        raise ValueError("Validated intake has no accepted activities.")
    if documents is None or getattr(documents, "empty", True):
        raise ValueError("Validated intake has no source documents.")

    flags = get_adapter_flags(session_state)
    ghg = flags["include_ghg"] if include_ghg is None else bool(include_ghg)
    cbam = flags["include_cbam"] if include_cbam is None else bool(include_cbam)
    ifrs = (
        flags["include_ifrs_s2"]
        if include_ifrs_s2 is None
        else bool(include_ifrs_s2)
    )

    file_name = str(
        getattr(intake, "file_name", None)
        or _ss_get(session_state, STATE_INTAKE_FILE_NAME)
        or "uploaded_file"
    ).strip()
    ingested_at = pd.Timestamp.now(tz="UTC")
    meta = _ss_get(session_state, STATE_INTAKE_METADATA)
    if meta is not None and getattr(meta, "ingested_at", None) is not None:
        ingested_at = pd.Timestamp(meta.ingested_at)

    included = included_activities_for_uploaded_analysis(session_state)

    session_state[STATE_ERROR] = None
    session_state[STATE_ANALYSIS_RUNNING] = True
    # Hide stale results while a new analysis runs.
    session_state[STATE_RESULT] = None
    session_state[STATE_HERO_EMISSIONS_PLAY] = None
    session_state[STATE_RESULT_REVEAL_PENDING] = None
    session_state[STATE_LAST_ANIMATED_RESULT] = None
    session_state[STATE_COUNTUP_RUNTIME_READY] = False
    try:
        result = run_uploaded_pipeline(
            Path(repo_root) if repo_root is not None else REPO_ROOT,
            run_id=run_id,
            ingested_at=ingested_at,
            source_documents=documents,
            accepted_activities=included,
            include_ghg=ghg,
            include_cbam=cbam,
            include_ifrs_s2=ifrs,
            progress_callback=progress_callback,
        )
    except Exception as exc:  # noqa: BLE001 - surface as UI error text
        session_state[STATE_ERROR] = str(exc)
        session_state[STATE_ANALYSIS_RUNNING] = False
        raise

    session_state[STATE_RESULT] = result
    session_state[STATE_INCLUDE_GHG] = ghg
    session_state[STATE_INCLUDE_CBAM] = cbam
    session_state[STATE_INCLUDE_IFRS] = ifrs
    session_state[STATE_RUN_ID] = result.run_id
    session_state[STATE_LAST_CONFIG] = {
        "run_id": result.run_id,
        "ingested_at": str(ingested_at),
        "include_ghg": ghg,
        "include_cbam": cbam,
        "include_ifrs_s2": ifrs,
        "analysis_data_source": ANALYSIS_SOURCE_UPLOADED,
        "file_name": file_name,
    }
    _store_analysis_source_uploaded(session_state, result, file_name=file_name)
    # Uploaded company data returns to CUSTOMER mode (not demo).
    if _ss_get(session_state, STATE_APP_MODE) != AppMode.ADMIN.value:
        set_app_mode(session_state, AppMode.CUSTOMER)
    session_state[STATE_INITIALIZED] = True
    session_state[STATE_RUN_ANALYSIS_REQUEST] = False
    session_state[STATE_RUN_UPLOADED_REQUEST] = False
    session_state[STATE_ANALYSIS_RUNNING] = False
    return result


def get_current_result(session_state: Any) -> PipelineRunResult | None:
    """Return the stored pipeline result, if any."""
    result = _ss_get(session_state, STATE_RESULT)
    if result is None:
        return None
    if not isinstance(result, PipelineRunResult):
        return None
    if get_analysis_source(session_state) == ANALYSIS_SOURCE_UPLOADED:
        result_revision = str(
            _ss_get(session_state, STATE_RESULT_ENGINE_REVISION, "") or ""
        )
        result_file_hash = str(
            _ss_get(session_state, STATE_ANALYSIS_FILE_HASH, "") or ""
        )
        current_file_hash = str(
            _ss_get(session_state, STATE_INTAKE_FILE_HASH, "") or ""
        )
        # A real upload carries a file hash. In that path, fail closed unless
        # the result was produced by this engine revision from that exact file.
        # Some report builders and compatibility callers intentionally inject a
        # PipelineRunResult without an active intake file; do not hide those
        # results merely because no file identity exists to compare. Stale
        # persisted upload sessions are still cleared by
        # _invalidate_stale_uploaded_analysis() before this function is used.
        if current_file_hash and (
            result_revision != ANALYSIS_ENGINE_REVISION
            or result_file_hash != current_file_hash
        ):
            return None
        if result_revision and result_revision != ANALYSIS_ENGINE_REVISION:
            return None
    return result


def get_adapter_flags(session_state: Any) -> dict[str, bool]:
    """Return the currently selected analysis-module flags."""
    return {
        "include_ghg": bool(_ss_get(session_state, STATE_INCLUDE_GHG, True)),
        "include_cbam": bool(_ss_get(session_state, STATE_INCLUDE_CBAM, False)),
        "include_ifrs_s2": bool(_ss_get(session_state, STATE_INCLUDE_IFRS, True)),
    }


def get_ui_error(session_state: Any) -> str | None:
    """Return the last user-facing analysis error, if any."""
    value = _ss_get(session_state, STATE_ERROR)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def set_focus_record(session_state: Any, record_id: str | None) -> None:
    """Store a record ID for Activity Explorer deep-links."""
    session_state[STATE_FOCUS_RECORD] = record_id


def get_focus_record(session_state: Any) -> str | None:
    """Return the focused record ID, if any."""
    value = _ss_get(session_state, STATE_FOCUS_RECORD)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def request_run_analysis(session_state: Any) -> None:
    """Ask the shell to run demo analysis on the next sidebar pass."""
    session_state[STATE_RUN_ANALYSIS_REQUEST] = True
    session_state[STATE_RUN_UPLOADED_REQUEST] = False


def request_run_uploaded_analysis(session_state: Any) -> None:
    """Ask the shell to analyze the validated uploaded dataset."""
    session_state[STATE_RUN_UPLOADED_REQUEST] = True
    session_state[STATE_RUN_ANALYSIS_REQUEST] = False


def get_company_profile_mapping(session_state: Any) -> dict[str, Any]:
    """Return the session company-profile mapping (never None)."""
    raw = _ss_get(session_state, STATE_COMPANY_PROFILE, {})
    return dict(raw) if isinstance(raw, dict) else {}


def save_company_profile(session_state: Any, mapping: dict[str, Any]) -> None:
    """Persist company-profile answers for the Streamlit session."""
    session_state[STATE_COMPANY_PROFILE] = dict(mapping or {})
    session_state[STATE_COMPANY_PROFILE_EDITING] = False


def get_applicability_assessment(session_state: Any) -> Any:
    """Return the last ApplicabilityAssessment stored in session, if any."""
    return _ss_get(session_state, STATE_APPLICABILITY_ASSESSMENT)


def save_applicability_assessment(session_state: Any, assessment: Any) -> None:
    """Store assessment object (single source of truth for dashboard pages)."""
    session_state[STATE_APPLICABILITY_ASSESSMENT] = assessment


def get_company_master_mapping(session_state: Any) -> dict[str, Any]:
    raw = _ss_get(session_state, STATE_COMPANY_MASTER, {})
    return dict(raw) if isinstance(raw, dict) else {}


def confirmed_company_ubn(session_state: Any) -> str:
    """Return the customer-confirmed UBN, or empty when the company is not confirmed."""
    master = get_company_master_mapping(session_state)
    if not str(master.get("customer_confirmed_at") or "").strip():
        return ""
    return str(master.get("unified_business_number") or "").strip()


def save_company_master_mapping(session_state: Any, mapping: dict[str, Any]) -> None:
    session_state[STATE_COMPANY_MASTER] = dict(mapping or {})


def get_facility_master_mapping(session_state: Any) -> dict[str, Any]:
    raw = _ss_get(session_state, STATE_FACILITY_MASTER, {})
    return dict(raw) if isinstance(raw, dict) else {}


def save_facility_master_mapping(session_state: Any, mapping: dict[str, Any]) -> None:
    session_state[STATE_FACILITY_MASTER] = dict(mapping or {})


def upload_site_names_from_session(session_state: Any) -> list[str]:
    """Unique customer-facing 廠場／營運據點 values from mapped intake."""
    import os

    from carbon_ledger.company_lookup import (
        STUB_ALIGNED_UBN,
        STUB_DIFF_UBN,
        STUB_ENV,
    )
    from carbon_ledger.company_master import extract_upload_site_names

    intake = get_intake_result(session_state)
    accepted = getattr(intake, "accepted_activities", None) if intake else None
    if accepted is not None:
        try:
            if not getattr(accepted, "empty", True) and "site_id" in accepted.columns:
                names = extract_upload_site_names(accepted["site_id"].tolist())
                if names:
                    return names
        except Exception:  # noqa: BLE001
            pass
    if str(os.environ.get(STUB_ENV) or "").strip() in {"1", "true", "yes"}:
        ubn = str(
            (get_company_master_mapping(session_state).get("unified_business_number"))
            or ""
        )
        if ubn == STUB_ALIGNED_UBN:
            return ["高雄一廠", "高雄二廠", "台南廠"]
        if ubn == STUB_DIFF_UBN:
            return ["高雄一廠", "台中辦公室"]
    return []


def clear_duplicate_review_state(session_state: Any) -> None:
    """Drop lookalike-review decisions and related widget keys."""
    session_state[STATE_INTAKE_DUPLICATE_REVIEW] = {}
    session_state[STATE_INTAKE_SHOW_DUPLICATE_REVIEW] = False
    try:
        keys = list(session_state.keys())
    except Exception:  # noqa: BLE001 - AppTest proxies vary
        keys = []
    for key in keys:
        if str(key).startswith(DUPLICATE_WIDGET_PREFIX):
            try:
                del session_state[key]
            except Exception:  # noqa: BLE001
                pass


def duplicate_review_decisions_from_state(session_state: Any) -> list[Any]:
    """Return deserialized duplicate-review decisions from session."""
    from carbon_ledger.potential_duplicates import load_review_decisions

    return load_review_decisions(
        _ss_get(session_state, STATE_INTAKE_DUPLICATE_REVIEW, {})
    )


def _company_workspace_for_session(session_state: Any) -> Any | None:
    from carbon_ledger.company_workspace import (
        CompanyWorkspace,
        default_workspace_root,
    )

    master = get_company_master_mapping(session_state)
    if not str(master.get("customer_confirmed_at") or "").strip():
        return None
    ubn = str(master.get("unified_business_number") or "").strip()
    entity_id = str(master.get("company_id") or "").strip()
    root = default_workspace_root(Path(REPO_ROOT))
    try:
        if ubn:
            return CompanyWorkspace.for_company(root=root, taiwan_ubn=ubn)
        if entity_id:
            return CompanyWorkspace.for_company(root=root, entity_id=entity_id)
    except ValueError:
        return None
    return None


def activity_boundary_decisions_from_state(session_state: Any) -> list[Any]:
    """Session decisions, merged with same-period workspace records."""
    from carbon_ledger.activity_boundary_decisions import (
        latest_decisions,
        load_decisions,
    )

    loaded = load_decisions(
        _ss_get(session_state, STATE_ACTIVITY_BOUNDARY_DECISIONS, [])
    )
    workspace = _company_workspace_for_session(session_state)
    if workspace is not None:
        try:
            loaded.extend(workspace.load_all_activity_boundary_decisions())
        except (OSError, ValueError):
            pass
    return latest_decisions(loaded)


def save_activity_boundary_decision_in_session(
    session_state: Any,
    decision: Any,
) -> Any:
    """Store one decision in session and the period workspace when available."""
    from carbon_ledger.activity_boundary_decisions import (
        decision_identity,
        latest_decisions,
        load_decisions,
    )

    current = load_decisions(
        _ss_get(session_state, STATE_ACTIVITY_BOUNDARY_DECISIONS, [])
    )
    incoming = decision_identity(
        decision.record_id,
        decision.reporting_year,
        decision.reporting_period_id,
    )
    current = [
        item
        for item in current
        if decision_identity(
            item.record_id,
            item.reporting_year,
            item.reporting_period_id,
        )
        != incoming
    ]
    current.append(decision)
    session_state[STATE_ACTIVITY_BOUNDARY_DECISIONS] = [
        item.to_dict() for item in latest_decisions(current)
    ]
    workspace = _company_workspace_for_session(session_state)
    if workspace is not None:
        workspace.save_activity_boundary_decision(decision)
    return decision


def purchased_steel_confirmations_from_state(session_state: Any) -> list[Any]:
    """Current-session purchased-steel confirmation overlays."""
    from carbon_ledger.purchased_steel_confirmations import load_confirmations

    return load_confirmations(
        _ss_get(session_state, STATE_PURCHASED_STEEL_CONFIRMATIONS, [])
    )


def save_purchased_steel_confirmation_in_session(
    session_state: Any,
    confirmation: Any,
) -> Any:
    """Replace one steel confirmation for the same upload identity."""
    from carbon_ledger.purchased_steel_confirmations import latest_confirmations

    current = purchased_steel_confirmations_from_state(session_state)
    incoming = confirmation.identity()
    current = [item for item in current if item.identity() != incoming]
    current.append(confirmation)
    session_state[STATE_PURCHASED_STEEL_CONFIRMATIONS] = [
        item.to_dict() for item in latest_confirmations(current)
    ]
    return confirmation


def withdraw_activity_boundary_decision_in_session(
    session_state: Any,
    *,
    record_id: str,
    reporting_year: int,
    reporting_period_id: str = "",
    confirmed_by: str = "",
) -> Any | None:
    from dataclasses import replace

    from carbon_ledger.activity_boundary_decisions import decision_identity

    current = activity_boundary_decisions_from_state(session_state)
    wanted = decision_identity(record_id, reporting_year, reporting_period_id)
    matched = next(
        (
            item
            for item in current
            if decision_identity(
                item.record_id,
                item.reporting_year,
                item.reporting_period_id,
            )
            == wanted
            and not item.withdrawn
        ),
        None,
    )
    if matched is None:
        return None
    withdrawn = replace(
        matched,
        withdrawn=True,
        confirmed_by=str(confirmed_by or matched.confirmed_by),
    )
    return save_activity_boundary_decision_in_session(session_state, withdrawn)


def included_activities_for_uploaded_analysis(session_state: Any) -> pd.DataFrame:
    """Confirmed included rows for final calculation. Fail-closed if unresolved."""
    from carbon_ledger.activity_boundary_decisions import (
        apply_activity_boundary_decisions,
    )
    from carbon_ledger.potential_duplicates import (
        activities_included_for_calculation,
        groups_from_intake,
    )

    intake = get_intake_result(session_state)
    if intake is None:
        raise ValueError("No validated uploaded intake result is available.")
    accepted = getattr(intake, "accepted_activities", None)
    if accepted is None or getattr(accepted, "empty", True):
        raise ValueError("Validated intake has no accepted activities.")
    included = activities_included_for_calculation(
        accepted,
        groups_from_intake(intake),
        duplicate_review_decisions_from_state(session_state),
    )
    if included is None or getattr(included, "empty", True):
        raise ValueError("Validated intake has no accepted activities.")
    from carbon_ledger.purchased_steel_confirmations import (
        apply_purchased_steel_confirmations,
    )

    included = apply_purchased_steel_confirmations(
        included,
        purchased_steel_confirmations_from_state(session_state),
        current_file_hash=str(_ss_get(session_state, STATE_INTAKE_FILE_HASH) or ""),
    )
    return apply_activity_boundary_decisions(
        included,
        activity_boundary_decisions_from_state(session_state),
    )


def duplicate_review_blocks_analysis(session_state: Any) -> bool:
    """True when lookalike groups still need customer confirmation."""
    from carbon_ledger.potential_duplicates import (
        analysis_blocked_for_potential_duplicates,
        groups_from_intake,
    )

    intake = get_intake_result(session_state)
    if intake is None:
        return False
    return analysis_blocked_for_potential_duplicates(
        groups_from_intake(intake),
        duplicate_review_decisions_from_state(session_state),
    )


def clear_intake_state(session_state: Any) -> None:
    """Clear Phase 9A intake session values without touching analysis results."""
    for key in (
        STATE_INTAKE_FILE_HASH,
        STATE_INTAKE_FILE_NAME,
        STATE_INTAKE_TABLE,
        STATE_INTAKE_BYTES,
        STATE_INTAKE_SHEET,
        STATE_INTAKE_SHEET_CONFIRMED,
        STATE_INTAKE_HEADER_ROW,
        STATE_INTAKE_HEADER_CONFIRMED,
        STATE_INTAKE_YEAR_MONTH_CONFIRMED,
        STATE_INTAKE_SHOW_MAPPING_EDITOR,
        STATE_INTAKE_COMMITTED,
        STATE_INTAKE_MAPPING,
        STATE_INTAKE_METADATA,
        STATE_INTAKE_RESULT,
        STATE_INTAKE_STEP,
        STATE_INTAKE_EXCEPTION_CURSOR,
        STATE_INTAKE_DUPLICATE_REVIEW,
        STATE_INTAKE_SHOW_DUPLICATE_REVIEW,
        STATE_INTAKE_MEMORY_CHOICE,
        STATE_INTAKE_MEMORY_APPLIED,
        STATE_INTAKE_MEMORY_OFFERED,
        STATE_INTAKE_SUGGESTIONS_RECORDED,
        STATE_INTAKE_VALIDATION_REQUESTED,
        STATE_INTAKE_VALIDATION_RUNNING,
        STATE_INTAKE_VALIDATION_ERROR,
        STATE_PURCHASED_STEEL_CONFIRMATIONS,
        STATE_STEEL_CONFIRM_FLASH,
    ):
        if key in session_state:
            del session_state[key]
    clear_duplicate_review_state(session_state)


def get_intake_result(session_state: Any) -> Any | None:
    """Return the validated intake result stored in session, if any."""
    return _ss_get(session_state, STATE_INTAKE_RESULT)
