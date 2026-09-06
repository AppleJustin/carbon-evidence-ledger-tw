"""Emissions Data & Calculation UX closure — A–F matrix."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from carbon_ledger.intake import (
    IntakeMetadata,
    build_and_validate_intake,
    parse_uploaded_table,
    suggest_column_mapping_with_confidence,
)
from carbon_ledger.intake_exceptions import (
    ISSUE_HELD_NG_CONTEXT,
    ISSUE_HELD_PENDING_ACTUAL_HV,
    NG_VALUE_PENDING_HV,
    apply_exception,
    confirmation_timeline,
    hold_unknown_context_rows,
    initialize_committed,
    list_exceptions,
    mapping_from_committed,
)
from carbon_ledger.intake_mapping_memory import snapshot_rememberable_committed
from carbon_ledger.pipeline import run_uploaded_pipeline
from carbon_ledger.ui.i18n import t
from carbon_ledger.ui.state import (
    STATE_INTAKE_COMMITTED,
    STATE_INTAKE_EXCEPTION_CURSOR,
    STATE_INTAKE_RESULT,
    STATE_INTAKE_SHOW_MAPPING_EDITOR,
    STATE_INTAKE_STEP,
    STATE_INTAKE_TABLE,
    initialize_ui_state,
    normalize_intake_wizard_step,
)
from carbon_ledger.ui.view_models import (
    DISPOSITION_CALCULATED,
    DISPOSITION_EXCLUDED_DUPLICATE,
    DISPOSITION_NEEDS_CONFIRMATION,
    hero_result_status_and_disposition,
    labeled_scope_hero_caption,
    reconcile_row_dispositions,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "streamlit_app.py"
ZH = "zh-TW"
EN = "en"
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00Z")


def _table(csv: str, name: str = "ops.csv"):
    return parse_uploaded_table(file_name=name, data=csv.encode("utf-8"))


def _committed(table):
    detailed = suggest_column_mapping_with_confidence(
        list(table.columns), frame=table.frame
    )
    return detailed, initialize_committed(table, detailed)


def _metadata(name: str = "ops.csv") -> IntakeMetadata:
    return IntakeMetadata(
        source_name=name,
        site_id="高雄廠",
        document_date=date(2025, 1, 31),
        data_quality_tier="unknown",
        intake_run_id="ux_closure",
        ingested_at=FIXED_INGESTED_AT,
    )


def _clean_electricity_csv() -> str:
    return (
        "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,1000,kWh,2025-01-01,2025-01-31,高雄廠\n"
        "外購電力,2000,kWh,2025-02-01,2025-02-28,高雄廠\n"
    )


def _ng_and_electricity_csv() -> str:
    return (
        "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,50000,kWh,2025-01-01,2025-01-31,高雄廠\n"
        "天然氣,8000,m3,2025-01-01,2025-01-31,高雄廠\n"
    )


def _explicit_ng1_csv() -> str:
    return (
        "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
        "天然氣 NG1,8000,m3,2025-01-01,2025-01-31,高雄廠\n"
        "外購電力,1000,kWh,2025-01-01,2025-01-31,高雄廠\n"
    )


def _two_site_ng_csv() -> str:
    return (
        "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
        "天然氣,100,m3,2025-01-01,2025-01-31,A廠\n"
        "天然氣,200,m3,2025-01-01,2025-01-31,B廠\n"
    )


def _run_pipeline(table, mapping, metadata) -> object:
    intake = hold_unknown_context_rows(
        build_and_validate_intake(table, mapping, metadata), mapping
    )
    return run_uploaded_pipeline(
        REPO_ROOT,
        run_id="ux_closure",
        ingested_at=FIXED_INGESTED_AT,
        source_documents=intake.source_documents,
        accepted_activities=intake.accepted_activities,
        include_ghg=True,
        include_ifrs_s2=True,
    ), intake


def test_nav_and_audit_rename() -> None:
    assert t("nav.evidence", ZH) == "排放資料與計算"
    assert t("nav.evidence", EN) == "Emissions Data & Calculations"
    assert t("ev.title", ZH) == "佐證文件與稽核紀錄"
    assert t("ev.tab.records", ZH) == "佐證文件與稽核紀錄"
    assert t("intake.step1", ZH).startswith("01")
    assert t("intake.step4", ZH).startswith("04")
    assert "05" not in t("intake.step4", ZH)
    assert t("intake.btn.fix", ZH) == "修改系統辨識結果"


def test_normalize_maps_legacy_five_steps() -> None:
    session: dict = {
        STATE_INTAKE_TABLE: object(),
        STATE_INTAKE_RESULT: object(),
    }
    session[STATE_INTAKE_STEP] = 3
    assert normalize_intake_wizard_step(session) == 3
    session[STATE_INTAKE_RESULT] = None
    session[STATE_INTAKE_STEP] = 3
    assert normalize_intake_wizard_step(session) == 2
    session[STATE_INTAKE_RESULT] = object()
    session[STATE_INTAKE_STEP] = 4
    assert normalize_intake_wizard_step(session) == 3
    session[STATE_INTAKE_STEP] = 5
    assert normalize_intake_wizard_step(session) == 3


def test_clean_rows_are_all_calculated_and_complete() -> None:
    table = _table(_clean_electricity_csv())
    detailed, committed = _committed(table)
    mapping = mapping_from_committed(table, committed)
    mapping.electricity_context = "enterprise"
    result, intake = _run_pipeline(table, mapping, _metadata())
    recon = reconcile_row_dispositions(
        uploaded_table=table,
        intake_result=intake,
        pipeline_result=result,
        is_uploaded_analysis=True,
    )
    assert recon["total"] == 2
    assert recon["included"] == 2
    assert recon["remaining_open"] == 0
    assert recon["counts"][DISPOSITION_CALCULATED] == 2
    assert recon["complete"] is True
    assert sum(recon["counts"].values()) == recon["total"]
    assert len(recon["by_row"]) == recon["total"]


def test_held_ng_plus_calculated_electricity_is_preliminary() -> None:
    table = _table(_ng_and_electricity_csv())
    detailed, committed = _committed(table)
    mapping = mapping_from_committed(table, committed)
    mapping.electricity_context = "enterprise"
    mapping.natural_gas_subtype = "unknown"
    result, intake = _run_pipeline(table, mapping, _metadata())
    recon = reconcile_row_dispositions(
        uploaded_table=table,
        intake_result=intake,
        pipeline_result=result,
        is_uploaded_analysis=True,
    )
    assert recon["total"] == 2
    assert recon["included"] == 1
    assert recon["counts"][DISPOSITION_NEEDS_CONFIRMATION] >= 1
    assert recon["remaining_open"] >= 1
    assert recon["complete"] is False
    assert recon["preliminary"] is True
    assert recon["included"] + recon["remaining_open"] + recon["excluded"] == recon[
        "total"
    ]
    assert len(recon["by_row"]) == recon["total"]


def test_duplicate_exclusion_does_not_force_preliminary() -> None:
    table = _table(_clean_electricity_csv())
    detailed, committed = _committed(table)
    mapping = mapping_from_committed(table, committed)
    mapping.electricity_context = "enterprise"
    result, intake = _run_pipeline(table, mapping, _metadata())
    record_ids = [
        str(value)
        for value in result.activity_records_accepted["record_id"].tolist()
    ]
    excluded = {record_ids[0]}
    recon = reconcile_row_dispositions(
        uploaded_table=table,
        intake_result=intake,
        pipeline_result=result,
        duplicate_excluded_ids=excluded,
        is_uploaded_analysis=True,
    )
    assert recon["counts"][DISPOSITION_EXCLUDED_DUPLICATE] == 1
    assert recon["included"] == 1
    assert recon["remaining_open"] == 0
    assert recon["excluded"] == 1
    assert recon["complete"] is True


def test_explicit_ng1_does_not_ask_file_wide_question() -> None:
    table = _table(_explicit_ng1_csv())
    detailed, committed = _committed(table)
    exceptions = list_exceptions(table, detailed, committed)
    ng_items = [item for item in exceptions if item.field == "natural_gas"]
    assert ng_items == []
    mapping = mapping_from_committed(table, committed)
    mapping.electricity_context = "enterprise"
    intake = hold_unknown_context_rows(
        build_and_validate_intake(table, mapping, _metadata()), mapping
    )
    ng_held = intake.rejected_rows
    if ng_held is not None and not ng_held.empty:
        assert ISSUE_HELD_NG_CONTEXT not in set(
            ng_held["issue_code"].astype(str).tolist()
        )


def test_two_site_ng_answers_do_not_cross() -> None:
    table = _table(_two_site_ng_csv())
    detailed, committed = _committed(table)
    exceptions = list_exceptions(table, detailed, committed)
    ng_items = [item for item in exceptions if item.field == "natural_gas"]
    assert len(ng_items) == 2
    first = ng_items[0]
    updated = apply_exception(committed, first, {"value": "NG1"})
    remaining = [
        item
        for item in list_exceptions(table, detailed, updated)
        if item.field == "natural_gas"
    ]
    assert len(remaining) == 1
    assert remaining[0].group_id != first.group_id
    groups = updated.get("natural_gas_groups") or {}
    assert groups.get(first.group_id) == "NG1"
    assert remaining[0].group_id not in groups or groups.get(
        remaining[0].group_id
    ) not in {"NG1", "NG2"}


def test_actual_hv_is_pending_review_and_held() -> None:
    table = _table(_two_site_ng_csv())
    detailed, committed = _committed(table)
    item = next(
        exception
        for exception in list_exceptions(table, detailed, committed)
        if exception.field == "natural_gas"
    )
    updated = apply_exception(
        committed,
        item,
        {
            "value": NG_VALUE_PENDING_HV,
            "heating_value": "8900",
            "heating_unit": "kcal/m3",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "source_reference": "bill-2025",
        },
    )
    reviews = updated.get("pending_heating_value_reviews") or {}
    assert item.group_id in reviews
    assert reviews[item.group_id]["status"] == "pending_review"
    mapping = mapping_from_committed(table, updated)
    intake = hold_unknown_context_rows(
        build_and_validate_intake(table, mapping, _metadata()), mapping
    )
    codes = set(intake.rejected_rows["issue_code"].astype(str).tolist())
    assert ISSUE_HELD_PENDING_ACTUAL_HV in codes or ISSUE_HELD_NG_CONTEXT in codes
    accepted = intake.accepted_activities
    if accepted is not None and not accepted.empty:
        sites = set(accepted["site_id"].astype(str).tolist())
        assert item.group_id not in sites or item.source_label not in sites


def test_ng_stays_out_of_mapping_memory_snapshot() -> None:
    snapshot = snapshot_rememberable_committed(
        {
            "columns": {"activity_type": "活動類型"},
            "natural_gas_subtype": "NG1",
            "natural_gas_groups": {"A廠": "NG1"},
        }
    )
    assert "natural_gas_subtype" not in snapshot
    assert "natural_gas_groups" not in snapshot


def test_confirmation_timeline_keeps_answered_for_previous() -> None:
    table = _table(_two_site_ng_csv())
    detailed, committed = _committed(table)
    first = list_exceptions(table, detailed, committed)[0]
    updated = apply_exception(committed, first, {"value": "NG1"})
    timeline = confirmation_timeline(table, detailed, updated)
    assert timeline[0].item_id == first.item_id
    assert len(timeline) >= 2


def test_apptest_single_question_progress_and_coverage_terms() -> None:
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    initialize_ui_state(at.session_state)
    table = _table(
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "採購鋼材,10,t,2025-01-01,2025-01-31,高雄廠\n"
    )
    at.session_state[STATE_INTAKE_TABLE] = table
    at.session_state[STATE_INTAKE_STEP] = 2
    at.session_state[STATE_INTAKE_SHOW_MAPPING_EDITOR] = False
    at.switch_page("app_pages/data_intake.py")
    at.run()
    assert not at.exception
    text = "\n".join(
        str(getattr(item, "value", "") or getattr(item, "body", "") or "")
        for collection in (
            at.markdown,
            at.caption,
            at.info,
        )
        for item in collection
    )
    assert "需要確認 1／1" in text or "需要確認" in text
    labels = [str(button.label) for button in at.button]
    assert t("intake.ex.apply", ZH) in labels
    assert t("intake.btn.fix", ZH) in labels
    assert STATE_INTAKE_EXCEPTION_CURSOR in at.session_state


def test_guided_queue_advances_from_question_1_to_2() -> None:
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    initialize_ui_state(at.session_state)
    table = _table(
        "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,1000,kWh,2025-01-01,2025-01-31,高雄廠\n"
        "天然氣,8000,m3,2025-01-01,2025-01-31,高雄廠\n"
        "柴油,10,L,2025-01-01,2025-01-31,高雄廠\n"
    )
    at.session_state[STATE_INTAKE_TABLE] = table
    at.session_state[STATE_INTAKE_STEP] = 2
    at.session_state[STATE_INTAKE_SHOW_MAPPING_EDITOR] = False
    at.switch_page("app_pages/data_intake.py")
    at.run()
    assert not at.exception
    text = "\n".join(
        str(getattr(item, "value", "") or getattr(item, "body", "") or "")
        for collection in (at.markdown, at.caption, at.info)
        for item in collection
    )
    assert "需要確認 1／3" in text
    at.radio[0].set_value(t("intake.ng_option_1", ZH))
    apply = next(
        button
        for button in at.button
        if str(button.label) == t("intake.ex.apply", ZH)
    )
    apply.click()
    at.run()
    assert not at.exception
    after = "\n".join(
        str(getattr(item, "value", "") or getattr(item, "body", "") or "")
        for collection in (at.markdown, at.caption, at.info)
        for item in collection
    )
    assert "需要確認 2／3" in after
    committed = at.session_state[STATE_INTAKE_COMMITTED]
    groups = dict(committed.get("natural_gas_groups") or {})
    assert "NG1" in set(groups.values())


def test_coverage_step_uses_customer_terms() -> None:
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    initialize_ui_state(at.session_state)
    table = _table(_clean_electricity_csv())
    detailed, committed = _committed(table)
    mapping = mapping_from_committed(table, committed)
    mapping.electricity_context = "enterprise"
    intake = hold_unknown_context_rows(
        build_and_validate_intake(table, mapping, _metadata()), mapping
    )
    at.session_state[STATE_INTAKE_TABLE] = table
    at.session_state[STATE_INTAKE_COMMITTED] = committed
    at.session_state[STATE_INTAKE_RESULT] = intake
    at.session_state[STATE_INTAKE_STEP] = 3
    at.switch_page("app_pages/data_intake.py")
    at.run()
    assert not at.exception
    text = "\n".join(
        str(getattr(item, "value", "") or getattr(item, "body", "") or "")
        for collection in (at.markdown, at.caption, at.success, at.info)
        for item in collection
    )
    labels = [str(button.label) for button in at.button]
    assert t("intake.result_accepted", ZH) in text or "可納入計算" in text
    assert t("intake.start_analysis", ZH) in labels
    assert t("intake.step5", ZH) not in text
    assert at.session_state[STATE_INTAKE_STEP] == 3


def test_uploaded_and_demo_result_copy_are_separated() -> None:
    uploaded = hero_result_status_and_disposition(
        uploaded=True,
        dispositions={
            "included": 2,
            "total": 2,
            "remaining_open": 0,
            "excluded": 0,
            "complete": True,
        },
        calculated_count=2,
        activity_count=2,
        needs_work=0,
        lang=ZH,
    )
    assert uploaded["disposition_caption"] == t(
        "dash.hero.included", ZH, included=2, total=2
    )
    assert uploaded["status_label"] == t("dash.coverage_complete", ZH, total=2)
    demo = hero_result_status_and_disposition(
        uploaded=False,
        dispositions={
            "included": 0,
            "total": 0,
            "remaining_open": 0,
            "excluded": 0,
            "complete": False,
        },
        calculated_count=5,
        activity_count=5,
        needs_work=0,
        lang=ZH,
    )
    assert demo["disposition_caption"] == ""
    assert "納入 0" not in demo["disposition_caption"]
    assert demo["status_label"] == t("dash.coverage_complete_demo", ZH)
    mixed = hero_result_status_and_disposition(
        uploaded=False,
        dispositions={
            "included": 0,
            "total": 5,
            "remaining_open": 0,
            "excluded": 0,
            "complete": False,
        },
        calculated_count=5,
        activity_count=5,
        needs_work=0,
        lang=ZH,
    )
    assert "納入 0／5" not in mixed["disposition_caption"]
    assert mixed["disposition_caption"] == ""


def test_complete_copy_never_uses_zero_included_ratio() -> None:
    copy = hero_result_status_and_disposition(
        uploaded=True,
        dispositions={
            "included": 0,
            "total": 5,
            "remaining_open": 0,
            "excluded": 5,
            "complete": False,
        },
        calculated_count=5,
        activity_count=5,
        needs_work=0,
        lang=ZH,
    )
    assert "納入 0／" not in copy["disposition_caption"]
    assert copy["status_label"] != t("dash.coverage_complete", ZH, total=5)


def test_scope_hero_caption_keeps_scope_labels() -> None:
    states = {
        "scope_1": {"state": "pending", "value": None},
        "scope_2": {"state": "calculated", "value": 23.70},
        "scope_3": {"state": "empty", "value": None},
    }
    zh = labeled_scope_hero_caption(states, ZH)
    en = labeled_scope_hero_caption(states, EN)
    assert zh == t(
        "dash.hero.scope_value",
        ZH,
        label=t("dash.hero.scope2_location", ZH),
        value="23.70",
    )
    assert en == t(
        "dash.hero.scope_value",
        EN,
        label=t("dash.hero.scope2_location", EN),
        value="23.70",
    )
    assert "尚未計算" not in zh
    assert "Not calculated" not in en
    assert t("dash.scope3.empty", ZH) == "目前尚無可納入的 Scope 3 計算結果。"
    assert "0 tCO" not in t("dash.scope3.empty", ZH)
    assert "0 tCO" not in t("dash.scope3.empty", EN)
    assert t("nav.evidence", EN) == "Emissions Data & Calculations"
