"""E2E + required screenshots for Emissions Data UX closure."""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

E2E_DIR = Path(__file__).resolve().parent
if str(E2E_DIR) not in sys.path:
    sys.path.insert(0, str(E2E_DIR))

from helpers import (  # noqa: E402
    ARTIFACTS,
    INTAKE_APPLY,
    NAV_EVIDENCE,
    NG_CUSTOMER_LABEL,
    analysis_hero_first_snapshot,
    analysis_hero_samples,
    analysis_result_overlap_events,
    assert_above_fold,
    assert_analysis_overlay_unmounted,
    assert_english_nav_readable,
    assert_no_modal_overlay,
    choose_radio,
    confirm_intake_reading,
    dismiss_tutorial_if_present,
    install_analysis_result_overlap_watch,
    open_fresh_app,
    parse_metric_number,
    resolve_intake_exceptions,
    save_step_screenshot,
    start_uploaded_coverage_analysis,
    visible_text,
    wait_for_analysis_progress,
    wait_for_analysis_view_unmounted,
    wait_for_hero_countup_mid,
    wait_for_hero_first_attach,
    wait_for_hero_settled,
    wait_streamlit_idle,
)

from carbon_ledger.intake import (  # noqa: E402
    IntakeMetadata,
    build_and_validate_intake,
    parse_uploaded_table,
    suggest_column_mapping_with_confidence,
)
from carbon_ledger.intake_exceptions import (  # noqa: E402
    hold_unknown_context_rows,
    initialize_committed,
    mapping_from_committed,
)
from carbon_ledger.pipeline import run_uploaded_pipeline  # noqa: E402
from carbon_ledger.ui.formatting import format_result_tco2e_amount  # noqa: E402
from carbon_ledger.ui.i18n import t  # noqa: E402
from carbon_ledger.ui.view_models import (  # noqa: E402
    calculated_emissions_by_product_scope,
    calculated_emissions_summary,
    hero_result_status_and_disposition,
    labeled_scope_hero_caption,
    reconcile_row_dispositions,
    scope_kpi_states,
)

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[2]
ZH = "zh-TW"
EN = "en"
FIXED_INGESTED_AT = pd.Timestamp("2025-02-01T00:00:00Z")

UNLABELED_NOT_CALCULATED = re.compile(
    r"tCO₂e\s*[·•]\s*(尚未計算|Not yet calculated|Not calculated)\b",
    re.I,
)
INCLUDED_RATIO = re.compile(r"納入\s*(\d+)／(\d+)\s*筆")
PRELIMINARY_RATIO = re.compile(r"目前納入\s*(\d+)／(\d+)\s*筆")

THREE_QUESTIONS = (
    "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
    "外購電力,1000,kWh,2025-01-01,2025-01-31,高雄廠\n"
    "天然氣,8000,m3,2025-01-01,2025-01-31,高雄廠\n"
    "柴油,10,L,2025-01-01,2025-01-31,高雄廠\n"
)
CLEAN_POWER = (
    "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
    "外購電力,1000,kWh,2025-01-01,2025-01-31,高雄廠\n"
)
COMPLETE_CLEAN = (
    "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
    "外購電力,50000,kWh,2025-01-01,2025-01-31,高雄廠\n"
    "外購電力,1000,kWh,2025-02-01,2025-02-28,高雄廠\n"
)
EXPLICIT_NG1 = (
    "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
    "天然氣 NG1,8000,m3,2025-01-01,2025-01-31,高雄廠\n"
    "外購電力,1000,kWh,2025-01-01,2025-01-31,高雄廠\n"
)
AMBIGUOUS_NG = (
    "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
    "天然氣,8000,m3,2025-01-01,2025-01-31,高雄廠\n"
)
PRELIMINARY_MIX = (
    "活動類型,使用量,單位,開始日期,結束日期,廠場\n"
    "外購電力,50000,kWh,2025-01-01,2025-01-31,高雄廠\n"
    "天然氣,8000,m3,2025-01-01,2025-01-31,高雄廠\n"
)


def _goto_intake(page) -> None:
    open_fresh_app(page)
    page.get_by_role("link", name=re.compile(NAV_EVIDENCE)).first.click()
    wait_streamlit_idle(page)
    page.get_by_text("上傳能源與營運資料").first.wait_for(
        state="visible", timeout=20_000
    )


def _upload_csv(page, name: str, content: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    csv_path = ARTIFACTS / name
    csv_path.write_text(content, encoding="utf-8")
    uploader = page.locator('[data-testid="stFileUploader"] input[type="file"]')
    uploader.first.wait_for(state="attached", timeout=30_000)
    uploader.first.set_input_files(str(csv_path))
    wait_streamlit_idle(page, timeout=40)
    page.get_by_text(
        re.compile(r"資料已讀取|File read successfully"),
        exact=False,
    ).first.wait_for(state="visible", timeout=20_000)


def _switch_language(page, token: str) -> None:
    option = page.get_by_text(token, exact=True)
    if option.count() == 0:
        option = page.get_by_role("button", name=re.compile(rf"^{token}$"))
    option.first.wait_for(state="visible", timeout=15_000)
    option.first.click()
    wait_streamlit_idle(page)
    page.wait_for_timeout(400)


def _expected_uploaded(
    csv: str, *, hold_ng: bool = False, natural_gas_subtype: str = ""
) -> dict[str, object]:
    table = parse_uploaded_table(file_name="ops.csv", data=csv.encode("utf-8"))
    detailed = suggest_column_mapping_with_confidence(
        list(table.columns), frame=table.frame
    )
    committed = initialize_committed(table, detailed)
    mapping = mapping_from_committed(table, committed)
    mapping.electricity_context = "enterprise"
    if hold_ng:
        mapping.natural_gas_subtype = "unknown"
    elif natural_gas_subtype:
        mapping.natural_gas_subtype = natural_gas_subtype
        mapping.diesel_context = "company_vehicle"
    metadata = IntakeMetadata(
        source_name="ops.csv",
        site_id="高雄廠",
        document_date=date(2025, 1, 31),
        data_quality_tier="unknown",
        intake_run_id="ux_closure_e2e",
        ingested_at=FIXED_INGESTED_AT,
    )
    intake = hold_unknown_context_rows(
        build_and_validate_intake(table, mapping, metadata), mapping
    )
    result = run_uploaded_pipeline(
        REPO_ROOT,
        run_id="ux_closure_e2e",
        ingested_at=FIXED_INGESTED_AT,
        source_documents=intake.source_documents,
        accepted_activities=intake.accepted_activities,
        include_ghg=True,
        include_ifrs_s2=True,
    )
    recon = reconcile_row_dispositions(
        uploaded_table=table,
        intake_result=intake,
        pipeline_result=result,
        is_uploaded_analysis=True,
    )
    emissions = calculated_emissions_summary(result)
    scopes = calculated_emissions_by_product_scope(result)
    copy = hero_result_status_and_disposition(
        uploaded=True,
        dispositions=recon,
        calculated_count=int(recon["included"]),
        activity_count=int(recon["total"]),
        needs_work=int(recon["remaining_open"]),
        lang=ZH,
    )
    return {
        "recon": recon,
        "copy": copy,
        "total_tco2e": float(emissions["calculated_tco2e"]),
        "scope_caption": labeled_scope_hero_caption(scope_kpi_states(result), ZH),
        "scope_caption_en": labeled_scope_hero_caption(
            scope_kpi_states(result), EN
        ),
        "scope_sum": float(scopes.get("scope_1") or 0.0)
        + float(scopes.get("scope_2") or 0.0),
        "scope_1": float(scopes.get("scope_1") or 0.0),
        "scope_2": float(scopes.get("scope_2") or 0.0),
        "formatted": format_result_tco2e_amount(emissions["calculated_tco2e"]),
    }


def _assert_question_workspace_above_fold(page, *, question: int) -> None:
    title = page.locator(".cel-exception-card").first
    assert_above_fold(title, page, label=f"question {question} title")
    why = page.locator('[data-testid="stCaption"]').filter(
        has_text=re.compile(r"為什麼|天然氣|電力|柴油|Why|natural gas")
    )
    if why.count():
        assert_above_fold(why.first, page, label=f"question {question} explanation")
    radios = page.locator('[data-testid="stRadioOption"]')
    assert radios.count() >= 1, f"question {question} has no choices"
    assert_above_fold(radios.first, page, label=f"question {question} first choice")
    assert_above_fold(radios.last, page, label=f"question {question} last choice")
    apply = page.get_by_role("button", name=re.compile(INTAKE_APPLY))
    assert_above_fold(apply, page, label=f"question {question} primary action")
    if question >= 2:
        previous = page.get_by_role("button", name=re.compile(r"上一題|Previous"))
        assert_above_fold(previous, page, label="Previous")


def _assert_scope_semantics(text: str, *, lang: str) -> None:
    assert UNLABELED_NOT_CALCULATED.search(text) is None
    if lang == ZH:
        assert "Scope 2（地區基準）：" in text
        assert t("dash.scope3.empty", ZH) in text
        assert "tCO₂e · 尚未計算" not in text
        assert "tCO₂e ·尚未計算" not in text
    else:
        assert "Scope 2 (location-based):" in text
        assert t("dash.scope3.empty", EN) in text
        assert "tCO₂e · Not calculated" not in text
        assert "tCO2e · Not calculated" not in text


def test_emissions_data_navigation_screenshots(page) -> None:
    open_fresh_app(page)
    save_step_screenshot(page, "qa_emissions_data_navigation_zh", required=True)
    text = visible_text(page)
    assert "排放資料與計算" in text
    _switch_language(page, "EN")
    page.get_by_text("Emissions Data", exact=False).first.wait_for(
        state="visible", timeout=15_000
    )
    assert_english_nav_readable(page)
    save_step_screenshot(
        page, "qa_emissions_data_navigation_en", required=True, full_page=False
    )
    assert "Emissions Data & Calculations" in re.sub(
        r"\s+", " ", visible_text(page)
    )


def test_recognition_questions_one_at_a_time(page) -> None:
    _goto_intake(page)
    _upload_csv(page, "ux_three_questions.csv", THREE_QUESTIONS)
    text = visible_text(page)
    assert "需要確認 1／3" in text
    assert page.get_by_role("button", name=re.compile(INTAKE_APPLY)).count() == 1
    _assert_question_workspace_above_fold(page, question=1)
    save_step_screenshot(
        page, "qa_recognition_question_1_of_3", required=True, full_page=False
    )
    choose_radio(page, NG_CUSTOMER_LABEL["NG1"])
    page.get_by_role("button", name=re.compile(INTAKE_APPLY)).first.click()
    wait_streamlit_idle(page, timeout=40)
    mid = visible_text(page)
    assert "需要確認 2／3" in mid
    _assert_question_workspace_above_fold(page, question=2)
    save_step_screenshot(
        page, "qa_recognition_question_2_of_3", required=True, full_page=False
    )


def test_calculation_coverage_review_screenshot(page) -> None:
    _goto_intake(page)
    _upload_csv(page, "ux_clean_power.csv", CLEAN_POWER)
    confirm_intake_reading(page)
    page.get_by_text("檢查計算範圍", exact=False).first.wait_for(
        state="visible", timeout=20_000
    )
    text = visible_text(page)
    assert "可納入計算" in text
    save_step_screenshot(page, "qa_calculation_coverage_review", required=True)


def test_complete_and_preliminary_result_screenshots(page) -> None:
    expected = _expected_uploaded(COMPLETE_CLEAN)
    recon = expected["recon"]
    assert int(recon["included"]) > 0
    assert int(recon["included"]) == int(recon["total"])
    assert int(recon["remaining_open"]) == 0
    _goto_intake(page)
    _upload_csv(page, "ux_complete_clean.csv", COMPLETE_CLEAN)
    confirm_intake_reading(page)
    start_uploaded_coverage_analysis(page)
    page.get_by_text("碳排計算完成", exact=False).first.wait_for(
        state="visible", timeout=40_000
    )
    wait_streamlit_idle(page, timeout=20)
    hero = wait_for_hero_settled(page)
    text = visible_text(page)
    included_match = INCLUDED_RATIO.search(text)
    assert included_match, f"uploaded inclusion ratio missing: {text[:800]}"
    displayed_included = int(included_match.group(1))
    displayed_total = int(included_match.group(2))
    assert displayed_included > 0
    assert displayed_included == displayed_total
    assert displayed_included == int(recon["included"])
    assert displayed_total == int(recon["total"])
    assert int(recon["remaining_open"]) == 0
    assert expected["copy"]["disposition_caption"] in text
    hero_value = parse_metric_number(hero["text"])
    assert hero["text"] == expected["formatted"]
    assert hero_value == pytest.approx(float(expected["total_tco2e"]), abs=0.005)
    assert hero_value == pytest.approx(float(expected["scope_sum"]), abs=0.005)
    assert hero_value == pytest.approx(float(hero["target"]), abs=0.005)
    assert hero_value != pytest.approx(0.0, abs=0.005)
    assert "納入 0／" not in text
    _assert_scope_semantics(text, lang=ZH)
    assert expected["scope_caption"] in text
    save_step_screenshot(
        page, "qa_complete_emissions_result_top", required=True, full_page=False
    )
    _switch_language(page, "EN")
    en_text = visible_text(page)
    _assert_scope_semantics(en_text, lang=EN)
    assert expected["scope_caption_en"] in en_text

    expected_pre = _expected_uploaded(PRELIMINARY_MIX, hold_ng=True)
    pre_recon = expected_pre["recon"]
    _goto_intake(page)
    _upload_csv(page, "ux_preliminary_mix.csv", PRELIMINARY_MIX)
    confirm_intake_reading(page, ng_choice="我現在無法確認，暫不納入計算")
    start_uploaded_coverage_analysis(page)
    page.get_by_text("初步碳排結果", exact=False).first.wait_for(
        state="visible", timeout=40_000
    )
    wait_streamlit_idle(page, timeout=20)
    pre_hero = wait_for_hero_settled(page)
    pre_text = visible_text(page)
    pre_match = PRELIMINARY_RATIO.search(pre_text) or INCLUDED_RATIO.search(pre_text)
    assert pre_match, f"preliminary ratio missing: {pre_text[:800]}"
    assert int(pre_match.group(1)) == int(pre_recon["included"])
    assert int(pre_match.group(2)) == int(pre_recon["total"])
    pre_value = parse_metric_number(pre_hero["text"])
    assert pre_hero["text"] != "0.00"
    assert pre_hero["text"] == expected_pre["formatted"]
    assert pre_value == pytest.approx(
        float(expected_pre["total_tco2e"]), abs=0.005
    )
    assert pre_value == pytest.approx(float(expected_pre["scope_sum"]), abs=0.005)
    assert pre_value == pytest.approx(float(pre_hero["target"]), abs=0.005)
    _assert_scope_semantics(pre_text, lang=ZH)
    save_step_screenshot(
        page,
        "qa_preliminary_emissions_result_top",
        required=True,
        full_page=False,
    )


def test_ng1_auto_and_ambiguous_question_screenshots(page) -> None:
    _goto_intake(page)
    _upload_csv(page, "ux_explicit_ng1.csv", EXPLICIT_NG1)
    text = visible_text(page)
    assert "確認天然氣種類" not in text
    save_step_screenshot(page, "qa_ng1_auto_resolved", required=True)
    _goto_intake(page)
    _upload_csv(page, "ux_ambiguous_ng.csv", AMBIGUOUS_NG)
    page.get_by_text("確認天然氣種類", exact=False).first.wait_for(
        state="visible", timeout=20_000
    )
    assert "我現在無法確認" in visible_text(page)
    save_step_screenshot(page, "qa_ng_ambiguous_customer_question", required=True)
    choose_radio(page, "我現在無法確認，暫不納入計算")


def test_supporting_documents_audit_trail_screenshot(page) -> None:
    open_fresh_app(page)
    dismiss_tutorial_if_present(page)
    demo = page.get_by_role(
        "button", name=re.compile(r"使用示範資料|Try demo")
    )
    if demo.count():
        demo.first.click(force=True)
        wait_streamlit_idle(page, timeout=90)
    page.get_by_text("碳排計算完成", exact=False).first.wait_for(
        state="visible", timeout=40_000
    )
    wait_for_hero_settled(page)
    dismiss_tutorial_if_present(page)
    assert_no_modal_overlay(page)
    records = page.get_by_role(
        "button",
        name=re.compile(
            r"查看佐證文件|View supporting documents|查看文件|View files"
        ),
    )
    if records.count() == 0:
        learn = page.locator('[data-testid="stExpander"]').filter(
            has_text=re.compile(r"了解結果涵蓋範圍|What this result includes")
        )
        if learn.count():
            learn.first.click(force=True)
            wait_streamlit_idle(page)
        records = page.get_by_role(
            "button",
            name=re.compile(
                r"查看佐證文件|View supporting documents|查看文件|View files"
            ),
        )
    records.first.wait_for(state="visible", timeout=20_000)
    records.first.click(force=True)
    wait_streamlit_idle(page)
    dismiss_tutorial_if_present(page)
    title = page.get_by_text("佐證文件與稽核紀錄", exact=False)
    title.first.wait_for(state="visible", timeout=20_000)
    assert title.first.is_visible()
    title_box = title.first.bounding_box()
    assert title_box is not None and title_box["height"] > 8
    detail = page.get_by_text("文件詳情", exact=False)
    detail.first.wait_for(state="visible", timeout=20_000)
    assert detail.first.is_visible()
    table = page.locator('[data-testid="stDataFrame"]').first
    table.wait_for(state="attached", timeout=20_000)
    table_box = table.bounding_box()
    assert table_box is not None, "source-document table has no box"
    assert table_box["height"] > 40 and table_box["width"] > 80
    audit = page.get_by_text("稽核追溯資訊", exact=False)
    audit.first.wait_for(state="attached", timeout=20_000)
    assert_no_modal_overlay(page)
    save_step_screenshot(
        page,
        "qa_supporting_documents_audit_trail",
        required=True,
        full_page=False,
    )


_CONTRAST_JS = """el => {
  const parse = (color) => {
    const m = String(color).match(
      /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([0-9.]+))?\\)/i
    );
    if (!m) return null;
    const alpha = m[4] === undefined ? 1 : Number(m[4]);
    return [Number(m[1]), Number(m[2]), Number(m[3]), alpha];
  };
  const lin = (channel) => {
    const c = channel / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const lum = (rgb) => (
    0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2])
  );
  const contrast = (a, b) => {
    const lighter = Math.max(a, b);
    const darker = Math.min(a, b);
    return (lighter + 0.05) / (darker + 0.05);
  };
  const fg = parse(getComputedStyle(el).color);
  let node = el;
  let bg = parse(getComputedStyle(node).backgroundColor);
  while (node && (!bg || bg[3] < 0.2)) {
    node = node.parentElement;
    if (!node) break;
    bg = parse(getComputedStyle(node).backgroundColor);
  }
  if (!fg || !bg) return 0;
  return contrast(lum(fg), lum(bg));
}"""


_BUTTON_STYLE_JS = """el => {
  const s = getComputedStyle(el);
  return {
    backgroundColor: s.backgroundColor,
    color: s.color,
    cursor: s.cursor,
    boxShadow: s.boxShadow,
    borderTopColor: s.borderTopColor,
  };
}"""


def _thousand_power_rows() -> list[tuple[object, ...]]:
    return [
        ("外購電力", 1000 + index, "kWh", "2025-01-01", "2025-01-31", "高雄廠")
        for index in range(1000)
    ]


def _thousand_power_csv() -> str:
    header = "活動類型,使用量,單位,開始日期,結束日期,廠場"
    lines = [
        f"{activity},{value},{unit},{start},{end},{site}"
        for activity, value, unit, start, end, site in _thousand_power_rows()
    ]
    return header + "\n" + "\n".join(lines) + "\n"


def _write_thousand_power_xlsx() -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / "qa_thousand_power.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "能源使用"
    sheet.append(["活動類型", "使用量", "單位", "開始日期", "結束日期", "廠場"])
    for row in _thousand_power_rows():
        sheet.append(list(row))
    workbook.save(path)
    return path


def _mixed_thousand_rows() -> list[tuple[object, ...]]:
    power = [
        ("外購電力", 1000 + index, "kWh", "2025-01-01", "2025-01-31", "高雄廠")
        for index in range(500)
    ]
    gas = [
        ("天然氣", 80 + index, "m3", "2025-01-01", "2025-01-31", "高雄廠")
        for index in range(500)
    ]
    return power + gas


def _mixed_thousand_csv() -> str:
    header = "活動類型,使用量,單位,開始日期,結束日期,廠場"
    lines = [
        f"{activity},{value},{unit},{start},{end},{site}"
        for activity, value, unit, start, end, site in _mixed_thousand_rows()
    ]
    return header + "\n" + "\n".join(lines) + "\n"


def _write_mixed_thousand_xlsx() -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / "qa_thousand_mixed_s1_s2.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "能源使用"
    sheet.append(["活動類型", "使用量", "單位", "開始日期", "結束日期", "廠場"])
    for row in _mixed_thousand_rows():
        sheet.append(list(row))
    workbook.save(path)
    return path


def _upload_path(page, path: Path) -> None:
    uploader = page.locator('[data-testid="stFileUploader"] input[type="file"]')
    uploader.first.wait_for(state="attached", timeout=30_000)
    uploader.first.set_input_files(str(path))
    wait_streamlit_idle(page, timeout=40)
    page.get_by_text(
        re.compile(r"資料已讀取|File read successfully"),
        exact=False,
    ).first.wait_for(state="visible", timeout=20_000)


def test_global_glossary_absent_from_customer_chrome(page) -> None:
    """Customer mode has no global 名詞解釋 / Glossary control any more."""
    open_fresh_app(page)
    dismiss_tutorial_if_present(page)
    viewport = page.viewport_size or {}
    assert viewport.get("width") == 1440
    assert viewport.get("height") == 900
    for label in ("名詞解釋", "Glossary"):
        assert (
            page.get_by_role("button", name=re.compile(rf"^{label}$")).count() == 0
        ), f"{label} control still visible in customer mode"
    sidebar = page.locator('section[data-testid="stSidebar"]')
    sidebar_text = sidebar.inner_text() if sidebar.count() else ""
    assert "名詞解釋" not in sidebar_text
    assert "Glossary" not in sidebar_text
    tutorial_entry = page.get_by_role("button", name=re.compile(r"操作教學|Tutorial"))
    assert tutorial_entry.count() >= 1, "操作教學 entry must remain available"
    save_step_screenshot(
        page, "qa_customer_chrome_no_glossary", required=True, full_page=False
    )
    _switch_language(page, "EN")
    assert page.get_by_role("button", name=re.compile(r"^Glossary$")).count() == 0


def test_thousand_row_progress_and_first_paint(page) -> None:
    expected = _expected_uploaded(_thousand_power_csv())
    recon = expected["recon"]
    assert int(recon["included"]) == 1000
    assert int(recon["total"]) == 1000
    assert float(expected["total_tco2e"]) > 0
    _goto_intake(page)
    _upload_path(page, _write_thousand_power_xlsx())
    page.get_by_text(re.compile(r"資料已讀取|File read successfully")).first.wait_for(
        state="visible", timeout=20_000
    )
    resolve_intake_exceptions(page)
    finish = page.get_by_role(
        "button",
        name=re.compile(r"完成確認並檢查資料|Finish confirmation"),
    )
    fix = page.get_by_role(
        "button",
        name=re.compile(r"修改系統辨識結果|Edit recognition results"),
    )
    finish.first.wait_for(state="visible", timeout=20_000)
    fix.first.wait_for(state="visible", timeout=20_000)
    enabled_primary = finish.first.evaluate(_BUTTON_STYLE_JS)
    enabled_secondary = fix.first.evaluate(_BUTTON_STYLE_JS)
    finish.first.click(force=True)
    page.wait_for_function(
        """() => {
          const marker = document.querySelector('[data-cel-intake-validating="1"]');
          const text = document.body ? document.body.innerText : '';
          const processing = /正在檢查你的資料|Checking your data/.test(text);
          const rows = /正在處理 1,000|Processing 1,000/.test(text);
          if (!(marker || processing || rows)) return false;
          const percents = [...text.matchAll(/(\\d+)\\s*%/g)].map((m) => Number(m[1]));
          if (percents.some((value) => value >= 100)) return false;
          return true;
        }""",
        timeout=20_000,
    )
    page.get_by_text(re.compile(r"正在處理 1,000|Processing 1,000")).first.wait_for(
        state="visible", timeout=20_000
    )
    processing = page.get_by_text(re.compile(r"正在處理 1,000|Processing 1,000"))
    processing_ratio = float(processing.first.evaluate(_CONTRAST_JS))
    assert processing_ratio >= 4.5, (
        f"processing count contrast {processing_ratio:.2f} < 4.5"
    )
    copies = page.locator(".cel-intake-progress-copy")
    for index in range(copies.count()):
        node = copies.nth(index)
        if not node.is_visible():
            continue
        ratio = float(node.evaluate(_CONTRAST_JS))
        assert ratio >= 4.5, f"progress copy contrast {ratio:.2f} < 4.5"
    edit = page.get_by_role("button", name=re.compile(r"^修改$|^Edit$"))
    if edit.count():
        assert edit.first.is_disabled()
    busy = page.get_by_role(
        "button",
        name=re.compile(r"完成確認並檢查資料|Finish confirmation"),
    )
    busy_fix = page.get_by_role(
        "button",
        name=re.compile(r"修改系統辨識結果|Edit recognition results"),
    )
    assert busy.count() >= 1
    assert busy.first.is_disabled()
    assert busy_fix.first.is_disabled()
    disabled_primary = busy.first.evaluate(_BUTTON_STYLE_JS)
    disabled_secondary = busy_fix.first.evaluate(_BUTTON_STYLE_JS)
    assert disabled_primary["cursor"] == "not-allowed"
    assert disabled_secondary["cursor"] == "not-allowed"
    assert disabled_primary["backgroundColor"] != enabled_primary["backgroundColor"]
    assert disabled_secondary["backgroundColor"] != enabled_secondary["backgroundColor"]
    assert disabled_primary["color"] != enabled_primary["color"]
    save_step_screenshot(
        page, "qa_intake_validation_progress", required=True, full_page=False
    )
    page.get_by_text("檢查計算範圍", exact=False).first.wait_for(
        state="visible", timeout=120_000
    )
    wait_streamlit_idle(page, timeout=40)
    coverage = visible_text(page)
    assert "可納入計算" in coverage
    start = page.get_by_role(
        "button",
        name=re.compile(r"使用這批資料開始分析|Analyze this uploaded"),
    )
    start.first.wait_for(state="visible", timeout=20_000)
    install_analysis_result_overlap_watch(page)
    start.first.click(force=True)
    wait_for_analysis_progress(page)
    assert page.locator("[data-cel-hero-emissions='1']").count() == 0
    assert page.get_by_text("碳排計算完成", exact=False).count() == 0
    wait_for_analysis_view_unmounted(page)
    settled = wait_for_hero_settled(page)
    assert_analysis_overlay_unmounted(page)
    assert analysis_result_overlap_events(page) == []
    first_value = parse_metric_number(settled["text"])
    assert settled["text"] == expected["formatted"]
    assert first_value == pytest.approx(float(expected["total_tco2e"]), abs=0.015)
    assert first_value != pytest.approx(0.0, abs=0.005)
    body = visible_text(page)
    included_match = INCLUDED_RATIO.search(body)
    assert included_match, f"inclusion ratio missing: {body[:800]}"
    assert int(included_match.group(1)) == 1000
    assert int(included_match.group(2)) == 1000


def test_mixed_thousand_row_analysis_countup_no_overlap(page) -> None:
    """1,000 mixed Scope 1+2 rows: progress-only, then one-shot hero count-up."""
    page.emulate_media(reduced_motion="no-preference")
    expected = _expected_uploaded(
        _mixed_thousand_csv(), natural_gas_subtype="NG1"
    )
    assert int(expected["recon"]["included"]) == 1000
    assert float(expected["scope_1"]) > 0
    assert float(expected["scope_2"]) > 0
    target = float(expected["total_tco2e"])
    _goto_intake(page)
    _upload_path(page, _write_mixed_thousand_xlsx())
    confirm_intake_reading(page, ng_choice="NG1")
    page.get_by_text("檢查計算範圍", exact=False).first.wait_for(
        state="visible", timeout=120_000
    )
    wait_streamlit_idle(page, timeout=40)
    start = page.get_by_role(
        "button",
        name=re.compile(r"使用這批資料開始分析|Analyze this uploaded"),
    )
    start.first.wait_for(state="visible", timeout=20_000)
    install_analysis_result_overlap_watch(page)
    start.first.click(force=True)
    wait_for_analysis_progress(page)
    assert page.locator("[data-cel-hero-emissions='1']").count() == 0
    assert page.get_by_text("碳排計算完成", exact=False).count() == 0
    assert page.locator(".cel-kpi-card-primary").count() == 0
    save_step_screenshot(
        page, "qa_analysis_progress_only_no_result", required=True, full_page=False
    )
    wait_for_analysis_view_unmounted(page)
    first = wait_for_hero_first_attach(page)
    assert first.get("progressPresent") is False, first
    assert first.get("play") == "1", first
    assert first.get("text") in {"0.00", "0"}, first
    assert_analysis_overlay_unmounted(page)
    mid_text = wait_for_hero_countup_mid(page)
    mid_value = parse_metric_number(mid_text)
    assert 0 < mid_value < target
    assert_analysis_overlay_unmounted(page)
    assert page.locator('[data-testid="stDialog"]').filter(
        has_text=re.compile(r"正在分析你的資料|Analyzing your data")
    ).count() == 0
    save_step_screenshot(
        page, "qa_result_countup_mid_no_overlay", required=True, full_page=False
    )
    settled = wait_for_hero_settled(page)
    assert settled["text"] == expected["formatted"]
    assert parse_metric_number(settled["text"]) == pytest.approx(target, abs=0.015)
    assert settled["text"] != "0.00"
    assert_analysis_overlay_unmounted(page)
    save_step_screenshot(
        page, "qa_result_countup_final_no_overlay", required=True, full_page=False
    )
    samples = analysis_hero_samples(page)
    mid_seen = False
    for sample in samples:
        value = parse_metric_number(sample)
        if 0 < value < target:
            mid_seen = True
            break
    assert mid_seen, f"count-up never left 0 or jumped to final: {samples[:12]}"
    assert analysis_result_overlap_events(page) == []
    replay_from = len(samples)
    page.get_by_role(
        "link", name=re.compile(r"合規總覽|Compliance Overview")
    ).first.click()
    wait_streamlit_idle(page, timeout=20)
    rerun_hero = wait_for_hero_settled(page)
    assert rerun_hero["text"] == expected["formatted"]
    assert page.locator("[data-cel-hero-emissions='1']").first.get_attribute(
        "data-cel-hero-play"
    ) == "0"
    later = analysis_hero_samples(page)[replay_from:]
    assert "0.00" not in later
    assert analysis_hero_first_snapshot(page).get("text") in {"0.00", "0"}
    assert analysis_result_overlap_events(page) == []

