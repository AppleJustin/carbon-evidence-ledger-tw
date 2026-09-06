"""Eight-row inventory fixture: website mapping → session → dashboard path."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook
from streamlit.testing.v1 import AppTest

from carbon_ledger.intake import (
    IntakeMetadata,
    build_and_validate_intake,
    parse_uploaded_table,
    suggest_column_mapping_with_confidence,
)
from carbon_ledger.intake_exceptions import (
    apply_exception,
    can_validate,
    hold_unknown_context_rows,
    initialize_committed,
    list_exceptions,
    mapping_from_committed,
)
from carbon_ledger.ui.i18n import LANG_EN, LANG_ZH, t
from carbon_ledger.ui.state import (
    ANALYSIS_ENGINE_REVISION,
    ANALYSIS_SOURCE_UPLOADED,
    STATE_ANALYSIS_ENGINE_REVISION,
    STATE_ANALYSIS_FILE_HASH,
    STATE_ANALYSIS_PERIOD_START,
    STATE_ANALYSIS_SOURCE,
    STATE_COMPANY_PROFILE,
    STATE_INCLUDE_GHG,
    STATE_INCLUDE_IFRS,
    STATE_INTAKE_COMMITTED,
    STATE_INTAKE_FILE_HASH,
    STATE_INTAKE_FILE_NAME,
    STATE_INTAKE_MAPPING,
    STATE_INTAKE_MAPPING_MEMORY,
    STATE_INTAKE_METADATA,
    STATE_INTAKE_RESULT,
    STATE_INTAKE_TABLE,
    STATE_LANGUAGE,
    STATE_RESULT,
    STATE_RESULT_ENGINE_REVISION,
    format_data_period_label,
    get_analysis_source_summary,
    get_current_result,
    initialize_ui_state,
    run_uploaded_analysis,
    uploaded_data_period_bounds,
)
from carbon_ledger.ui.view_models import (
    DISPOSITION_CALCULATED,
    DISPOSITION_EXCLUDED_OUT_OF_SCOPE,
    DISPOSITION_NEEDS_CONFIRMATION,
    DISPOSITION_UNSUPPORTED,
    company_inventory_emissions_summary,
    executive_emissions_insights,
    ghg_framework_table,
    inventory_source_shares,
    inventory_status_counts,
    pending_refrigerant_boundary_rows,
    reconcile_row_dispositions,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "eight_row_inventory.csv"
)
APP_PATH = REPO_ROOT / "streamlit_app.py"
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00Z")
ZH = LANG_ZH
EN = LANG_EN

EXPECTED_CSV = (
    "活動類型,用量,單位,開始日期,結束日期,廠場,天然氣類型,冷媒種類,"
    "補充量已確認,設備控制方式,組織盤查邊界\n"
    "外購電力,50000,kWh,2025-01-01,2025-01-31,高雄廠,,,,,\n"
    "天然氣,8000,m3,2025-01-01,2025-01-31,高雄廠,NG2,,,,\n"
    "公司車輛柴油,1200,L,2025-01-01,2025-01-31,高雄廠,,,,,\n"
    "採購鋼材,10,t,2025-01-01,2025-01-31,高雄廠,,,,,\n"
    "冷媒實際補充,15,kg,2025-02-01,2025-02-28,高雄廠,,R-134a,是,公司所有,納入\n"
    "冷媒實際補充,10,kg,2025-03-01,2025-03-31,台北廠,,R-32,是,營運控制,納入\n"
    "冷媒實際補充,3,kg,2025-04-01,2025-04-30,高雄廠,,R-32,是,公司所有,不納入\n"
    "冷媒實際補充,2,kg,2025-05-01,2025-05-31,台北廠,,R-410A,是,第三方,納入\n"
)

NG_TCO2E = 16.416157
DIESEL_TCO2E = 3.264679
SCOPE1_UNCONFIRMED = 45.950836
ELECTRICITY_TCO2E = 23.30
INVENTORY_AFTER_ELEC = 69.250836
R410A_TCO2E = 3.847
R32_OUTSIDE_TCO2E = 2.031
REFRIGERANT_INCLUDED_TCO2E = 26.27
SHARE_BEFORE_ELEC = 57.17
SHARE_AFTER_ELEC = 37.93
ENGLISH_THIRD_PARTY = (
    "Third-party refrigerant equipment is not automatically mapped "
    "to Scope 1; Scope 3 is not guessed."
)


def _csv_bytes() -> bytes:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    return text.encode("utf-8")


def _xlsx_bytes() -> bytes:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    headers = lines[0].split(",")
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for line in lines[1:]:
        sheet.append(line.split(","))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _parse(name: str, data: bytes):
    return parse_uploaded_table(file_name=name, data=data)


def _apply_named(table, detailed, committed, item_id: str, payload: dict) -> dict:
    item = next(
        row
        for row in list_exceptions(table, detailed, committed)
        if row.item_id == item_id
    )
    return apply_exception(committed, item, payload)


def _website_committed(table, *, electricity_context: str):
    detailed = suggest_column_mapping_with_confidence(
        list(table.columns), frame=table.frame
    )
    committed = initialize_committed(table, detailed)
    committed = _apply_named(
        table,
        detailed,
        committed,
        "column:activity_value",
        {"column": "用量", "table": table},
    )
    ids = {item.item_id for item in list_exceptions(table, detailed, committed)}
    assert "context:natural_gas" not in ids
    assert "context:diesel" not in ids
    committed = _apply_named(
        table,
        detailed,
        committed,
        "context:electricity",
        {"value": electricity_context},
    )
    assert can_validate(table, detailed, committed)
    return detailed, committed


def _metadata(table, committed) -> IntakeMetadata:
    raw = str(committed.get("document_date") or "2025-05-31")[:10]
    return IntakeMetadata(
        source_name=table.file_name,
        site_id="UNKNOWN",
        document_date=date.fromisoformat(raw),
        data_quality_tier="unknown",
        intake_run_id="eight_row",
        ingested_at=FIXED_INGESTED_AT,
    )


def _validate(table, committed):
    mapping = mapping_from_committed(table, committed)
    intake = hold_unknown_context_rows(
        build_and_validate_intake(table, mapping, _metadata(table, committed)),
        mapping,
    )
    return mapping, intake


def _session(table, committed, mapping, intake) -> dict:
    state: dict = {}
    initialize_ui_state(state)
    state[STATE_LANGUAGE] = ZH
    state[STATE_INCLUDE_GHG] = True
    state[STATE_INCLUDE_IFRS] = True
    state[STATE_INTAKE_TABLE] = table
    state[STATE_INTAKE_FILE_HASH] = str(table.sha256)
    state[STATE_INTAKE_COMMITTED] = committed
    state[STATE_INTAKE_MAPPING] = mapping
    state[STATE_INTAKE_METADATA] = _metadata(table, committed)
    state[STATE_INTAKE_RESULT] = intake
    state[STATE_COMPANY_PROFILE] = {
        "company_name": "測試公司",
        "reporting_year": 2026,
    }
    return state


def _run(table, *, electricity_context: str, name: str):
    detailed, committed = _website_committed(
        table, electricity_context=electricity_context
    )
    mapping, intake = _validate(table, committed)
    state = _session(table, committed, mapping, intake)
    result = run_uploaded_analysis(
        state,
        include_ghg=True,
        include_ifrs_s2=True,
        run_id=f"eight_row_{name}",
        repo_root=REPO_ROOT,
    )
    return detailed, committed, mapping, intake, state, result


def _activity(accepted: pd.DataFrame, **equals):
    frame = accepted
    for key, value in equals.items():
        series = frame[key]
        if key == "activity_value":
            numeric = pd.to_numeric(series, errors="coerce")
            frame = frame[numeric == float(value)]
            continue
        frame = frame[series.astype(str) == str(value)]
    assert len(frame) == 1, (equals, frame)
    return frame.iloc[0]


def _calc(result, record_id: str):
    rows = result.calculation_results
    return rows[rows["record_id"].astype(str) == record_id].iloc[0]


def _ghg(result, record_id: str):
    rows = result.ghg_evaluations
    return rows[rows["record_id"].astype(str) == record_id].iloc[0]


def test_fixture_matches_specified_eight_rows() -> None:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    assert text == EXPECTED_CSV


def test_initialize_invalidates_legacy_upload_state_but_keeps_raw_file() -> None:
    table = _parse("eight_row.xlsx", _xlsx_bytes())
    state = {
        STATE_ANALYSIS_ENGINE_REVISION: "legacy-engine",
        STATE_ANALYSIS_SOURCE: ANALYSIS_SOURCE_UPLOADED,
        STATE_ANALYSIS_PERIOD_START: "2026-01",
        STATE_INTAKE_FILE_NAME: "eight_row.xlsx",
        STATE_INTAKE_TABLE: table,
        STATE_INTAKE_COMMITTED: {"activity_value_column": "用量"},
        STATE_INTAKE_MAPPING: object(),
        STATE_INTAKE_METADATA: object(),
        STATE_INTAKE_RESULT: object(),
        STATE_INTAKE_MAPPING_MEMORY: {"old": "mapping"},
        STATE_RESULT: object(),
    }

    initialize_ui_state(state)

    assert state[STATE_ANALYSIS_ENGINE_REVISION] == ANALYSIS_ENGINE_REVISION
    assert state[STATE_INTAKE_TABLE] is table
    assert state[STATE_INTAKE_FILE_NAME] == "eight_row.xlsx"
    assert state[STATE_INTAKE_COMMITTED] is None
    assert state[STATE_INTAKE_MAPPING] is None
    assert state[STATE_INTAKE_RESULT] is None
    assert state[STATE_INTAKE_MAPPING_MEMORY] is None
    assert state[STATE_RESULT] is None
    assert state[STATE_ANALYSIS_SOURCE] == ""
    assert state[STATE_ANALYSIS_PERIOD_START] is None


def test_initialize_keeps_current_engine_upload_state() -> None:
    marker = object()
    state = {
        STATE_ANALYSIS_ENGINE_REVISION: ANALYSIS_ENGINE_REVISION,
        STATE_INTAKE_RESULT: marker,
        STATE_RESULT: marker,
    }

    initialize_ui_state(state)

    assert state[STATE_INTAKE_RESULT] is marker
    assert state[STATE_RESULT] is marker


def test_uploaded_result_is_bound_to_engine_revision_and_current_file() -> None:
    table = _parse("eight_row.xlsx", _xlsx_bytes())
    _, _, _, _, state, result = _run(
        table, electricity_context="enterprise", name="result_identity"
    )

    assert get_current_result(state) is result
    assert state[STATE_RESULT_ENGINE_REVISION] == ANALYSIS_ENGINE_REVISION
    assert state[STATE_ANALYSIS_FILE_HASH] == table.sha256

    state[STATE_INTAKE_FILE_HASH] = "different-upload"
    assert get_current_result(state) is None


def test_uploaded_result_without_result_revision_is_rejected() -> None:
    table = _parse("eight_row.xlsx", _xlsx_bytes())
    _, _, _, _, state, _ = _run(
        table, electricity_context="enterprise", name="legacy_result"
    )

    state.pop(STATE_RESULT_ENGINE_REVISION)
    assert get_current_result(state) is None


def test_xlsx_website_path_maps_ng2_and_vehicle_diesel() -> None:
    table = _parse("eight_row.xlsx", _xlsx_bytes())
    _, committed, mapping, intake, state, result = _run(
        table, electricity_context="unknown", name="xlsx"
    )
    _assert_unconfirmed_inventory(table, committed, mapping, intake, state, result)


def test_csv_website_path_matches_xlsx_normalization() -> None:
    csv_table = _parse("eight_row.csv", _csv_bytes())
    xlsx_table = _parse("eight_row.xlsx", _xlsx_bytes())
    _, csv_committed, csv_mapping, csv_intake, csv_state, csv_result = _run(
        csv_table, electricity_context="unknown", name="csv"
    )
    _, _, xlsx_mapping, xlsx_intake, _, xlsx_result = _run(
        xlsx_table, electricity_context="unknown", name="xlsx2"
    )
    _assert_unconfirmed_inventory(
        csv_table, csv_committed, csv_mapping, csv_intake, csv_state, csv_result
    )
    csv_ng = _activity(csv_intake.accepted_activities, activity_type="natural_gas")
    xlsx_ng = _activity(xlsx_intake.accepted_activities, activity_type="natural_gas")
    assert str(csv_ng["fuel_subtype"]) == str(xlsx_ng["fuel_subtype"]) == "NG2"
    csv_diesel = _activity(csv_intake.accepted_activities, activity_type="diesel")
    xlsx_diesel = _activity(xlsx_intake.accepted_activities, activity_type="diesel")
    assert (
        str(csv_diesel["process_use"])
        == str(xlsx_diesel["process_use"])
        == "company_vehicle"
    )
    csv_s1 = float(company_inventory_emissions_summary(csv_result, ZH)["scope_1"])
    xlsx_s1 = float(company_inventory_emissions_summary(xlsx_result, ZH)["scope_1"])
    assert csv_s1 == pytest.approx(xlsx_s1, abs=1e-6)


def test_ng2_survives_mapping_session_and_rerun() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _detailed, committed = _website_committed(table, electricity_context="unknown")
    mapping, intake = _validate(table, committed)
    assert mapping.natural_gas_subtype_column == "天然氣類型"
    assert mapping.natural_gas_subtype == "NG2"
    ng = _activity(intake.accepted_activities, activity_type="natural_gas")
    assert str(ng["fuel_subtype"]) == "NG2"

    wiped = dict(committed)
    wiped["natural_gas_subtype"] = "unknown"
    wiped["diesel_context"] = "unknown"
    mapping_wiped, intake_wiped = _validate(table, wiped)
    assert mapping_wiped.natural_gas_subtype_column == "天然氣類型"
    ng_wiped = _activity(intake_wiped.accepted_activities, activity_type="natural_gas")
    assert str(ng_wiped["fuel_subtype"]) == "NG2"
    diesel_wiped = _activity(intake_wiped.accepted_activities, activity_type="diesel")
    assert str(diesel_wiped["process_use"]) == "company_vehicle"

    state = _session(table, wiped, mapping_wiped, intake_wiped)
    first = run_uploaded_analysis(
        state, include_ghg=True, run_id="eight_row_ng_rerun_1", repo_root=REPO_ROOT
    )
    assert state[STATE_INTAKE_MAPPING].natural_gas_subtype_column == "天然氣類型"
    second = run_uploaded_analysis(
        state, include_ghg=True, run_id="eight_row_ng_rerun_2", repo_root=REPO_ROOT
    )
    ng_first = _activity(first.activity_records_accepted, activity_type="natural_gas")
    ng_second = _activity(second.activity_records_accepted, activity_type="natural_gas")
    assert str(ng_first["fuel_subtype"]) == str(ng_second["fuel_subtype"]) == "NG2"


def test_company_vehicle_diesel_survives_mapping_session_and_rerun() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, _committed, mapping, intake, state, result = _run(
        table, electricity_context="unknown", name="diesel"
    )
    assert mapping.diesel_context == "company_vehicle"
    diesel = _activity(intake.accepted_activities, activity_type="diesel")
    assert str(diesel["process_use"]) == "company_vehicle"
    calc = _calc(result, str(diesel["record_id"]))
    assert str(calc["calculation_status"]) == "calculated"
    assert float(calc["calculated_tco2e"]) == pytest.approx(DIESEL_TCO2E, abs=1e-6)
    rerun = run_uploaded_analysis(
        state, include_ghg=True, run_id="eight_row_diesel_rerun", repo_root=REPO_ROOT
    )
    diesel_rerun = _activity(rerun.activity_records_accepted, activity_type="diesel")
    assert str(diesel_rerun["process_use"]) == "company_vehicle"


def test_electricity_unconfirmed_is_not_calculated() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, _, mapping, intake, _, result = _run(
        table, electricity_context="unknown", name="elec_hold"
    )
    assert mapping.electricity_context == "unknown"
    accepted_types = set(intake.accepted_activities["activity_type"].astype(str))
    assert "grid_electricity" not in accepted_types
    assert "grid_electricity" not in set(
        result.activity_records_accepted["activity_type"].astype(str)
    )
    inventory = company_inventory_emissions_summary(result, ZH)
    assert float(inventory["scope_2"] or 0.0) == pytest.approx(0.0, abs=1e-9)


def test_electricity_enterprise_calculates_scope_2_23_30() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, committed = _website_committed(table, electricity_context="unknown")
    confirmed = dict(committed)
    confirmed["electricity_context"] = "enterprise"
    mapping, intake = _validate(table, confirmed)
    assert mapping.electricity_context == "enterprise"
    state = _session(table, confirmed, mapping, intake)
    result = run_uploaded_analysis(
        state, include_ghg=True, run_id="eight_row_elec", repo_root=REPO_ROOT
    )
    elec = _activity(intake.accepted_activities, activity_type="grid_electricity")
    assert str(elec["process_use"]) == "general_factory"
    assert str(elec["ownership_control"]) == "owned"
    assert str(elec["organizational_boundary_status"]) == "inside"
    calc = _calc(result, str(elec["record_id"]))
    ghg = _ghg(result, str(elec["record_id"]))
    assert str(calc["calculation_status"]) == "calculated"
    assert float(calc["calculated_tco2e"]) == pytest.approx(
        ELECTRICITY_TCO2E,
        abs=0.005,
    )
    assert str(ghg["mapping_status"]) == "mapped"
    assert str(ghg["ghg_scope"]) == "scope_2"
    rerun = run_uploaded_analysis(
        state, include_ghg=True, run_id="eight_row_elec_rerun", repo_root=REPO_ROOT
    )
    assert state[STATE_INTAKE_MAPPING].electricity_context == "enterprise"
    elec_rerun = _activity(
        rerun.activity_records_accepted, activity_type="grid_electricity"
    )
    assert str(elec_rerun["process_use"]) == "general_factory"


def test_data_period_is_2025_not_company_2026_profile() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, _, _, _intake, state, result = _run(
        table, electricity_context="unknown", name="period"
    )
    start, end = uploaded_data_period_bounds(state)
    assert start == "2025-01"
    assert end == "2025-05"
    label = format_data_period_label(start, end)
    assert "2025-01" in label and "2025-05" in label
    source = get_analysis_source_summary(state)
    assert source["period_start"] == "2025-01"
    assert source["period_end"] == "2025-05"
    state[STATE_RESULT] = result
    state[STATE_ANALYSIS_SOURCE] = ANALYSIS_SOURCE_UPLOADED
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    for key, value in state.items():
        at.session_state[key] = value
    at.switch_page("app_pages/dashboard.py")
    at.run()
    assert not at.exception
    chunks: list[str] = []
    for collection_name in (
        "markdown",
        "caption",
        "text",
        "info",
        "success",
        "warning",
        "error",
        "title",
    ):
        for item in getattr(at, collection_name, []) or []:
            value = getattr(item, "value", None)
            if value is not None:
                chunks.append(str(value))
            body = getattr(item, "body", None)
            if body is not None:
                chunks.append(str(body))
    for button in getattr(at, "button", []) or []:
        label = getattr(button, "label", None)
        if label is not None:
            chunks.append(str(label))
    text = "\n".join(chunks)
    assert "2025-01" in text
    assert "2025-05" in text
    assert "FY2026-05" not in text
    assert t("dash.legal_year_label", ZH, year="2026") in text


def test_unconfirmed_electricity_scope1_and_counts() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, _, _, intake, _, result = _run(
        table, electricity_context="unknown", name="s1"
    )
    inventory = company_inventory_emissions_summary(result, ZH)
    counts = inventory_status_counts(result)
    recon = reconcile_row_dispositions(
        uploaded_table=table,
        intake_result=intake,
        pipeline_result=result,
        is_uploaded_analysis=True,
    )
    assert counts["technically_calculated"] == 6
    assert counts["included_in_inventory"] == 4
    assert float(inventory["scope_1"]) == pytest.approx(SCOPE1_UNCONFIRMED, abs=1e-6)
    assert float(inventory["scope_2"] or 0.0) == pytest.approx(0.0, abs=1e-9)
    assert recon["counts"][DISPOSITION_CALCULATED] == 4
    assert recon["counts"][DISPOSITION_NEEDS_CONFIRMATION] == 3
    assert recon["counts"][DISPOSITION_UNSUPPORTED] == 0
    assert recon["counts"][DISPOSITION_EXCLUDED_OUT_OF_SCOPE] == 1
    assert recon["actionable_open"] == 3
    assert sum(recon["counts"].values()) == 8
    assert recon["total"] == 8


def test_confirmed_electricity_company_inventory_total() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, committed = _website_committed(table, electricity_context="unknown")
    confirmed = dict(committed)
    confirmed["electricity_context"] = "enterprise"
    mapping, intake = _validate(table, confirmed)
    state = _session(table, confirmed, mapping, intake)
    result = run_uploaded_analysis(
        state, include_ghg=True, run_id="eight_row_total", repo_root=REPO_ROOT
    )
    inventory = company_inventory_emissions_summary(result, ZH)
    counts = inventory_status_counts(result)
    assert counts["technically_calculated"] == 7
    assert counts["included_in_inventory"] == 5
    assert float(inventory["scope_1"]) == pytest.approx(SCOPE1_UNCONFIRMED, abs=1e-6)
    assert float(inventory["scope_2"]) == pytest.approx(ELECTRICITY_TCO2E, abs=0.005)
    assert float(inventory["inventory_tco2e"]) == pytest.approx(
        INVENTORY_AFTER_ELEC, abs=1e-6
    )


def test_outside_r32_and_pending_r410a_excluded_from_inventory() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, _, _, intake, _, result = _run(
        table, electricity_context="unknown", name="boundary"
    )
    accepted = intake.accepted_activities
    outside = _activity(
        accepted,
        activity_type="refrigerant_refill",
        refrigerant_code="R-32",
        organizational_boundary_status="outside",
    )
    pending = _activity(
        accepted,
        activity_type="refrigerant_refill",
        refrigerant_code="R-410A",
    )
    outside_calc = _calc(result, str(outside["record_id"]))
    pending_calc = _calc(result, str(pending["record_id"]))
    outside_ghg = _ghg(result, str(outside["record_id"]))
    pending_ghg = _ghg(result, str(pending["record_id"]))
    assert str(outside_calc["calculation_status"]) == "calculated"
    assert float(outside_calc["calculated_tco2e"]) == pytest.approx(
        R32_OUTSIDE_TCO2E, abs=0.001
    )
    assert str(outside_ghg["mapping_status"]) == "outside_boundary"
    assert str(pending_calc["calculation_status"]) == "calculated"
    assert float(pending_calc["calculated_tco2e"]) == pytest.approx(
        R410A_TCO2E, abs=0.001
    )
    assert str(pending_ghg["mapping_status"]) == "needs_review"
    inventory = company_inventory_emissions_summary(result, ZH)
    included_ids = set(
        result.ghg_evaluations.loc[
            (result.ghg_evaluations["mapping_status"].astype(str) == "mapped")
            & (
                result.ghg_evaluations["ghg_scope"]
                .astype(str)
                .isin(["scope_1", "scope_2"])
            )
        ]["record_id"].astype(str)
    )
    assert str(outside["record_id"]) not in included_ids
    assert str(pending["record_id"]) not in included_ids
    assert float(inventory["inventory_tco2e"]) == pytest.approx(
        SCOPE1_UNCONFIRMED, abs=1e-6
    )


def test_technical_total_stays_separate_from_company_inventory() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, _, _, _intake, _, result = _run(
        table, electricity_context="unknown", name="split"
    )
    counts = inventory_status_counts(result)
    inventory = company_inventory_emissions_summary(result, ZH)
    technical = float(
        pd.to_numeric(result.calculation_results["calculated_tco2e"], errors="coerce")
        .fillna(0)
        .sum()
    )
    assert counts["technically_calculated"] == 6
    assert counts["included_in_inventory"] == 4
    assert technical > float(inventory["inventory_tco2e"])
    assert technical == pytest.approx(
        float(inventory["inventory_tco2e"]) + R410A_TCO2E + R32_OUTSIDE_TCO2E,
        abs=0.01,
    )


def test_disposition_categories_cover_all_eight_rows() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, _, _, intake, _, result = _run(
        table, electricity_context="unknown", name="disp"
    )
    recon = reconcile_row_dispositions(
        uploaded_table=table,
        intake_result=intake,
        pipeline_result=result,
        is_uploaded_analysis=True,
    )
    assert recon["total"] == 8
    assert sum(recon["counts"].values()) == 8
    assert recon["included"] + recon["remaining_open"] + recon["excluded"] == 8
    assert recon["actionable_open"] == recon["needs_confirmation"] == 3
    assert recon["unsupported"] == 0
    assert recon["excluded"] == 1


def test_refrigerant_share_is_dynamic_from_inventory_rows() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, _, _, _, _, before = _run(
        table, electricity_context="unknown", name="share_before"
    )
    shares_before = inventory_source_shares(before, ZH)
    inventory_before = company_inventory_emissions_summary(before, ZH)
    refrigerant_before = next(
        row for row in shares_before if "冷媒" in str(row["activity_name"])
    )
    expected_before = round(
        100.0
        * float(refrigerant_before["tco2e"])
        / float(inventory_before["inventory_tco2e"]),
        2,
    )
    assert refrigerant_before["percent"] == expected_before
    assert float(refrigerant_before["tco2e"]) == pytest.approx(
        REFRIGERANT_INCLUDED_TCO2E, abs=0.01
    )
    assert expected_before == pytest.approx(SHARE_BEFORE_ELEC, abs=0.05)
    insights = executive_emissions_insights(before, ZH)
    assert any("已納入公司盤查排放量" in item for item in insights)
    assert all("100%" not in item for item in insights)

    _, committed = _website_committed(table, electricity_context="unknown")
    confirmed = dict(committed)
    confirmed["electricity_context"] = "enterprise"
    mapping, intake = _validate(table, confirmed)
    state = _session(table, confirmed, mapping, intake)
    after = run_uploaded_analysis(
        state, include_ghg=True, run_id="eight_row_share_after", repo_root=REPO_ROOT
    )
    shares_after = inventory_source_shares(after, ZH)
    inventory_after = company_inventory_emissions_summary(after, ZH)
    refrigerant_after = next(
        row for row in shares_after if "冷媒" in str(row["activity_name"])
    )
    expected_after = round(
        100.0
        * float(refrigerant_after["tco2e"])
        / float(inventory_after["inventory_tco2e"]),
        2,
    )
    assert refrigerant_after["percent"] == expected_after
    assert expected_after == pytest.approx(SHARE_AFTER_ELEC, abs=0.05)


def test_zh_interface_does_not_show_english_third_party_rationale() -> None:
    table = _parse("eight_row.csv", _csv_bytes())
    _, _, _, _, _, result = _run(
        table, electricity_context="unknown", name="i18n"
    )
    zh_table = ghg_framework_table(result, ZH)
    zh_reasons = (
        "\n".join(zh_table["Reason"].astype(str).tolist()) if not zh_table.empty else ""
    )
    assert ENGLISH_THIRD_PARTY not in zh_reasons
    assert t("ghg.rationale.refrigerant_third_party", ZH) in zh_reasons
    pending = pending_refrigerant_boundary_rows(result, ZH)
    pending_text = "\n".join(str(row.get("rationale") or "") for row in pending)
    assert ENGLISH_THIRD_PARTY not in pending_text
    en_table = ghg_framework_table(result, EN)
    en_reasons = (
        "\n".join(en_table["Reason"].astype(str).tolist()) if not en_table.empty else ""
    )
    assert ENGLISH_THIRD_PARTY in en_reasons


def _assert_unconfirmed_inventory(
    table, committed, mapping, intake, state, result
) -> None:
    assert mapping.natural_gas_subtype_column == "天然氣類型"
    assert mapping.natural_gas_subtype == "NG2"
    assert mapping.diesel_context == "company_vehicle"
    assert mapping.electricity_context == "unknown"
    assert mapping.refrigerant_code_column == "冷媒種類"

    ng = _activity(intake.accepted_activities, activity_type="natural_gas")
    diesel = _activity(intake.accepted_activities, activity_type="diesel")
    r134a = _activity(
        intake.accepted_activities,
        activity_type="refrigerant_refill",
        activity_value="15",
    )
    assert str(r134a["refrigerant_code"]).upper() == "R-134A"
    r32_in = _activity(
        intake.accepted_activities,
        activity_type="refrigerant_refill",
        refrigerant_code="R-32",
        organizational_boundary_status="inside",
    )
    r32_out = _activity(
        intake.accepted_activities,
        activity_type="refrigerant_refill",
        refrigerant_code="R-32",
        organizational_boundary_status="outside",
    )
    r410a = _activity(
        intake.accepted_activities,
        activity_type="refrigerant_refill",
        refrigerant_code="R-410A",
    )

    assert str(ng["activity_type"]) == "natural_gas"
    assert str(ng["fuel_subtype"]) == "NG2"
    assert str(ng["process_use"]) == "heat_treatment"
    ng_calc = _calc(result, str(ng["record_id"]))
    ng_ghg = _ghg(result, str(ng["record_id"]))
    assert str(ng_calc["calculation_status"]) == "calculated"
    assert float(ng_calc["calculated_tco2e"]) == pytest.approx(NG_TCO2E, abs=1e-6)
    assert str(ng_ghg["mapping_status"]) == "mapped"
    assert str(ng_ghg["ghg_scope"]) == "scope_1"

    assert str(diesel["activity_type"]) == "diesel"
    assert str(diesel["process_use"]) == "company_vehicle"
    diesel_calc = _calc(result, str(diesel["record_id"]))
    diesel_ghg = _ghg(result, str(diesel["record_id"]))
    assert str(diesel_calc["calculation_status"]) == "calculated"
    assert float(diesel_calc["calculated_tco2e"]) == pytest.approx(
        DIESEL_TCO2E, abs=1e-6
    )
    assert str(diesel_ghg["mapping_status"]) == "mapped"
    assert str(diesel_ghg["ghg_scope"]) == "scope_1"

    for row in (r134a, r32_in):
        calc = _calc(result, str(row["record_id"]))
        ghg = _ghg(result, str(row["record_id"]))
        assert str(calc["calculation_status"]) == "calculated"
        assert str(ghg["mapping_status"]) == "mapped"
        assert str(ghg["ghg_scope"]) == "scope_1"

    r32_out_calc = _calc(result, str(r32_out["record_id"]))
    r32_out_ghg = _ghg(result, str(r32_out["record_id"]))
    assert str(r32_out_calc["calculation_status"]) == "calculated"
    assert str(r32_out_ghg["mapping_status"]) == "outside_boundary"

    r410a_calc = _calc(result, str(r410a["record_id"]))
    r410a_ghg = _ghg(result, str(r410a["record_id"]))
    assert str(r410a_calc["calculation_status"]) == "calculated"
    assert str(r410a_ghg["mapping_status"]) == "needs_review"

    steel = _activity(intake.accepted_activities, activity_type="purchased_steel")
    steel_calc = _calc(result, str(steel["record_id"]))
    assert str(steel_calc["calculation_status"]) != "calculated"

    start, end = uploaded_data_period_bounds(state)
    assert (start, end) == ("2025-01", "2025-05")
    _ = table
    _ = committed
