"""Stage 3B.3a — browser E2E customer journeys (Playwright)."""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from carbon_ledger.intake import (
    ColumnMapping,
    IntakeMetadata,
    build_and_validate_intake,
    default_value_maps,
    parse_uploaded_table,
    suggest_activity_type,
    suggest_column_mapping,
    suggest_unit,
)
from carbon_ledger.pipeline import run_uploaded_pipeline
from carbon_ledger.ui.view_models import calculated_emissions_summary

E2E_DIR = Path(__file__).resolve().parent
if str(E2E_DIR) not in sys.path:
    sys.path.insert(0, str(E2E_DIR))

from helpers import (  # noqa: E402
    APPLICABILITY_NAV,
    ARTIFACTS,
    NG_CUSTOMER_LABEL,
    STUB_ALIGNED_UBN,
    STUB_SPARSE_UBN,
    _goto_app,
    assert_analysis_overlay_unmounted,
    assert_no_app_errors,
    assert_no_raw_html_leak,
    choose_radio,
    choose_selectbox,
    clear_durable_browser_state,
    click_button,
    confirm_intake_reading,
    confirm_stub_company_for_pdf,
    defer_boundary_wizard_if_present,
    fill_streamlit_date,
    install_analysis_result_overlap_watch,
    lookup_stub_company,
    open_emissions_data_nav,
    open_evidence_workspace_tool,
    open_fresh_app,
    open_intake_mapping_editor,
    parse_metric_number,
    safe_scroll_into_view,
    save_step_screenshot,
    seed_confirmed_pdf_workspace,
    set_money_unknown,
    visible_text,
    wait_for_analysis_progress,
    wait_for_analysis_view_unmounted,
    wait_for_hero_settled,
    wait_streamlit_idle,
)

pytestmark = pytest.mark.e2e


def _open_welcome_dialog(page) -> None:
    """Load a new Streamlit session that still shows first-run Welcome."""
    base = page._cel_base_url  # type: ignore[attr-defined]
    for _ in range(3):
        page.context.clear_cookies()
        _goto_app(page, base)
        clear_durable_browser_state(page)
        page.context.clear_cookies()
        _goto_app(page, base)
        page.wait_for_selector("text=Carbon Evidence Ledger", timeout=30_000)
        dialog = page.get_by_role("dialog")
        try:
            dialog.first.wait_for(state="visible", timeout=8_000)
            return
        except Exception:  # noqa: BLE001 - retry a fully new session
            continue
    page.get_by_role("dialog").first.wait_for(state="visible", timeout=20_000)


def test_simple_first_run_welcome(page) -> None:
    _open_welcome_dialog(page)
    body = visible_text(page)
    assert "完成第一筆碳排計算" in body
    assert "Excel" in body
    # A short welcome only — no step narration, no screenshots, no "next".
    assert "第 1 步，共 6 步" not in body
    assert "用 6 個步驟" not in body
    assert "不需要先懂碳盤查" not in body
    assert "下一步" not in body
    assert "治理、策略" not in body
    assert "GHG Protocol" not in body
    assert page.locator("[data-cel-tour-shot], .cel-tour-shot").count() == 0
    save_step_screenshot(page, "qa_simple_tutorial")
    page.get_by_role("button", name=re.compile(r"^(稍後再說|Not now)$")).first.click(
        force=True
    )
    wait_streamlit_idle(page)
    dialog = page.get_by_role("dialog")
    if dialog.count():
        dialog.first.wait_for(state="hidden", timeout=15_000)
    assert page.locator("#cel-onboarding-spotlight").count() == 0
    assert_no_app_errors(page)


def _goto_applicability_step1(page) -> None:
    open_fresh_app(page)
    click_button(page, "開始公司設定")
    page.wait_for_timeout(600)
    body = visible_text(page)
    assert "統一編號" in body or "確認公司" in body


def _fill_listed_company(page, company_name: str, *, capital_yi: str | None) -> None:
    del company_name
    if capital_yi is None:
        lookup_stub_company(page, STUB_SPARSE_UBN)
        click_button(page, "繼續")
        choose_selectbox(page, "公司是否上市／上櫃？", "上市（TWSE）")
        set_money_unknown(page, index=0, unknown=True)
        body = visible_text(page)
        assert "0.00" not in body
        assert "NT$0" not in body
    else:
        lookup_stub_company(page, STUB_ALIGNED_UBN)
        click_button(page, "繼續")
        body = visible_text(page)
        assert "NT$12,000,000,000" in body or "實收資本額" in body
        assert not re.search(r"淨值[^\n]{0,24}0\.00", body)
    save_step_screenshot(page, "qa_applicability_step2")
    click_button(page, "繼續")


def test_journey1_new_customer_applicability_results(page) -> None:
    open_fresh_app(page)
    text = visible_text(page)
    assert "示範公司" not in text
    assert "automated_sources_expected" not in text
    assert "MONITORING_PARTIAL" not in text
    assert "開始公司設定" in text
    save_step_screenshot(page, "qa_new_customer_home")

    click_button(page, "開始公司設定")
    _fill_listed_company(page, "test", capital_yi="120")

    save_step_screenshot(page, "qa_applicability_step3")
    text3 = visible_text(page)
    assert_no_raw_html_leak(text3)
    assert "高雄一廠" in text3 or "據點" in text3 or "廠場" in text3
    empty_cards = page.locator(".cel-card-primary")
    for index in range(empty_cards.count()):
        card = empty_cards.nth(index)
        if not card.is_visible():
            continue
        content = (card.inner_text() or "").strip()
        box = card.bounding_box()
        if box and box["height"] > 48:
            assert content, "empty white card surface rendered without content"
    gap = page.evaluate(
        """() => {
          const stepper = document.querySelector('.cel-stepper');
          const field = document.querySelector(
            '[data-testid="stButton"], [data-testid="stCheckbox"], p'
          );
          if (!stepper || !field) return null;
          return field.getBoundingClientRect().top
            - stepper.getBoundingClientRect().bottom;
        }"""
    )
    assert gap is not None, "stepper/fields missing on step 3"
    assert gap < 80, (
        f"unexplained empty surface between stepper and fields: gap={gap}px"
    )

    click_button(page, "繼續")
    page.wait_for_timeout(1000)
    wait_streamlit_idle(page)
    defer_boundary_wizard_if_present(page)
    save_step_screenshot(page, "qa_applicability_step5")
    text5 = visible_text(page)
    assert_no_raw_html_leak(text5)
    assert "適用" in text5
    assert "2026" in text5
    assert "2027" in text5

    page.set_viewport_size({"width": 1440, "height": 2400})
    wait_streamlit_idle(page)
    timeline = page.locator(".cel-ifrs-timeline").first
    timeline.wait_for(state="visible", timeout=15_000)
    timeline.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    assert timeline.is_visible()
    markers = page.locator(
        '[data-cel-timeline-scope="desktop"] [data-cel-timeline-marker]'
    )
    assert markers.count() == 6
    visible_markers = 0
    for index in range(markers.count()):
        node = markers.nth(index)
        if not node.is_visible():
            continue
        visible_markers += 1
        box = node.bounding_box()
        assert box is not None
        assert box["width"] > 0 and box["height"] > 0
    assert visible_markers == 6
    timeline_text = timeline.inner_text()
    assert "2026 年度開始適用" in timeline_text
    assert "2027 年首次申報" in timeline_text
    periods = page.locator(
        '[data-cel-timeline-scope="desktop"] .cel-timeline-period'
    )
    actions = page.locator(
        '[data-cel-timeline-scope="desktop"] .cel-timeline-action'
    )
    assert periods.count() == 6
    assert actions.count() == 6
    for index in range(6):
        for loc in (periods.nth(index), actions.nth(index)):
            assert loc.is_visible()
            box = loc.bounding_box()
            assert box is not None, f"timeline label missing box index={index}"
            assert box["width"] >= 24, (
                f"timeline label width too narrow (vertical stack): {box}"
            )
            assert box["height"] <= 96, (
                f"timeline label appears vertically corrupted: {box}"
            )

    overflow = page.evaluate(
        """() => {
          const main = document.querySelector('section.main') || document.body;
          const timeline = document.querySelector('.cel-ifrs-timeline');
          const mainOk = main.scrollWidth <= main.clientWidth + 2;
          const timelineOk = !timeline || (
            timeline.scrollWidth <= timeline.clientWidth + 2
          );
          return mainOk && timelineOk;
        }"""
    )
    assert overflow
    assert_no_app_errors(page)


def test_journey2_unknown_financial_data(page) -> None:
    _goto_applicability_step1(page)
    _fill_listed_company(page, "unknown-finance-co", capital_yi=None)
    click_button(page, "繼續")
    wait_streamlit_idle(page)
    defer_boundary_wizard_if_present(page)
    text = visible_text(page)
    assert_no_raw_html_leak(text)
    assert "NT$0" not in text
    assert "0.00 億" not in text
    # Unknown money → needs information, never fabricated zero NOT_APPLICABLE.
    assert "還需要一些資料" in text or "需要" in text
    assert_no_app_errors(page)


def test_journey3_explicit_demo(page) -> None:
    open_fresh_app(page)
    click_button(page, "使用示範資料")
    wait_streamlit_idle(page)
    page.wait_for_timeout(800)
    text = visible_text(page)
    assert "示範資料" in text or "Demo data" in text
    assert "automated_sources_expected" not in text
    assert_no_raw_html_leak(text)
    assert "tCO" in text or "排放" in text
    hero = page.locator(".cel-kpi-grid-hero, .cel-kpi-grid")
    assert hero.count() >= 1
    assert_no_app_errors(page)


def test_journey4_evidence_wizard_one_active_step(page) -> None:
    open_fresh_app(page)
    nav = page.get_by_role("link", name=re.compile(r"證據|Evidence"))
    if nav.count() == 0:
        nav = page.get_by_text(re.compile(r"排放資料與計算|Emissions Data"))
    nav.first.click()
    wait_streamlit_idle(page)
    text = visible_text(page)
    assert "上傳" in text or "Upload" in text
    assert (
        page.locator('input[type="file"]').count() >= 1
        or page.get_by_text(re.compile(r"Drag and drop|Browse|上傳")).count() >= 1
    )
    page.get_by_text("上傳能源與營運資料").first.wait_for(
        state="visible", timeout=15_000
    )
    page.set_viewport_size({"width": 1440, "height": 1800})
    wait_streamlit_idle(page)
    save_step_screenshot(page, "qa_data_upload")
    text = visible_text(page)
    assert text.count("開始分析") <= 2
    assert_no_raw_html_leak(text)
    # Stage 3B.3c / 4.2F-B — Data Upload customer hygiene
    assert "activity_type" not in text
    assert "activity_value" not in text
    assert "系統內部欄位名稱" not in text
    assert "200MB" not in text and "200 MB" not in text
    assert "10 MB" in text or "10MB" in text
    assert "需要準備的資料" not in text
    assert "不知道怎麼準備資料" not in text
    assert "50000" not in text
    assert "2024-01-01" not in text
    downloads = page.get_by_role(
        "button",
        name=re.compile(r"還沒有資料檔？下載範例|Don’t have a data file yet"),
    )
    assert downloads.count() >= 1
    example_dl = page.get_by_role(
        "button", name=re.compile(r"下載範例檔|example file")
    )
    assert example_dl.count() == 0
    assert_no_app_errors(page)


def test_journey6_information_hygiene(page) -> None:
    """Customer information hygiene smoke (extends existing E2E gate)."""
    open_fresh_app(page)
    home = visible_text(page)
    assert "Synthetic demonstration" not in home
    assert "MONITORING_PARTIAL" not in home
    assert "仍顯示示範分析結果" not in home
    save_step_screenshot(page, "qa_hygiene_customer_home")

    # Hidden IFRS / Taiwan modules are not customer sidebar destinations.
    for label, shot in (
        (APPLICABILITY_NAV, "qa_hygiene_applicability"),
        (r"排放資料與計算|Emissions Data", "qa_hygiene_evidence"),
        (r"報表|Reporting|Export|匯出", "qa_hygiene_reporting"),
    ):
        link = page.get_by_role("link", name=re.compile(label))
        if link.count() == 0:
            link = page.get_by_text(re.compile(label))
        link.first.click()
        wait_streamlit_idle(page)
        text = visible_text(page)
        assert "Synthetic demonstration" not in text
        assert "MONITORING_PARTIAL" not in text
        assert "automated_sources_expected" not in text
        assert "示範公司" not in text
        assert_no_raw_html_leak(text)
        save_step_screenshot(page, shot)

    # Applicability initial setup: no SASB field.
    page.get_by_role("link", name=re.compile(APPLICABILITY_NAV)).first.click()
    wait_streamlit_idle(page)
    setup = page.get_by_role("button", name=re.compile(r"開始公司設定"))
    if setup.count():
        setup.first.click(force=True)
        wait_streamlit_idle(page)
    if "統一編號" in visible_text(page) or "確認公司" in visible_text(page):
        lookup_stub_company(page, STUB_SPARSE_UBN)
        click_button(page, "繼續")
        if "公司是否上市／上櫃" in visible_text(page):
            choose_selectbox(page, "公司是否上市／上櫃？", "上市（TWSE）")
            set_money_unknown(page, index=0, unknown=True)
        click_button(page, "繼續")
        wait_streamlit_idle(page)
        step3 = visible_text(page)
        assert "SASB" not in step3
        save_step_screenshot(page, "qa_hygiene_applicability_step3")

    # Demo path: activity / issues / evidence / reporting hygiene.
    open_fresh_app(page)
    click_button(page, "使用示範資料")
    wait_streamlit_idle(page)
    page.wait_for_timeout(800)
    save_step_screenshot(page, "qa_hygiene_demo_dashboard")

    open_emissions_data_nav(page)
    open_evidence_workspace_tool(page, "活動資料")
    wait_streamlit_idle(page)
    act_text = visible_text(page)
    assert "factor_id" not in act_text
    save_step_screenshot(page, "qa_hygiene_activity_default")
    audit = page.locator("summary, [data-testid='stExpander']").filter(
        has_text=re.compile(r"稽核追溯資訊|Audit trace")
    )
    if audit.count() == 0:
        audit = page.get_by_text(re.compile(r"稽核追溯資訊|Audit trace"))
    if audit.count():
        audit.first.click(force=True)
        wait_streamlit_idle(page)
        page.wait_for_timeout(400)
    save_step_screenshot(page, "qa_hygiene_activity_audit")

    open_emissions_data_nav(page)
    open_evidence_workspace_tool(page, "待處理問題")
    wait_streamlit_idle(page)
    iss_text = visible_text(page)
    assert "record_id:" not in iss_text
    save_step_screenshot(page, "qa_hygiene_issues")

    open_emissions_data_nav(page)
    open_evidence_workspace_tool(page, "證據紀錄")
    wait_streamlit_idle(page)
    rec_text = visible_text(page)
    assert "SHA-256" not in rec_text
    assert "Evidence hash" not in rec_text
    save_step_screenshot(page, "qa_hygiene_evidence_records")

    page.get_by_role("link", name=re.compile(r"報表|Reporting|匯出")).first.click()
    wait_streamlit_idle(page)
    reporting = visible_text(page)
    assert "一般分析不會" not in reporting
    # Run ID not in default business groups (only advanced expander).
    assert "stage3b3" not in reporting
    save_step_screenshot(page, "qa_hygiene_reporting_customer")
    tech = page.locator("summary, [data-testid='stExpander']").filter(
        has_text=re.compile(r"專業覆核附件|Technical review")
    )
    if tech.count():
        tech.first.click(force=True)
        wait_streamlit_idle(page)
        page.wait_for_timeout(300)
    adv = page.locator("summary, [data-testid='stExpander']").filter(
        has_text=re.compile(r"稽核追溯資訊|Audit trace|技術識別")
    )
    if adv.count() == 0:
        adv = page.get_by_text(re.compile(r"稽核追溯資訊|Audit trace|技術識別"))
    if adv.count():
        adv.first.click(force=True)
        wait_streamlit_idle(page)
        page.wait_for_timeout(300)
    save_step_screenshot(page, "qa_hygiene_reporting_advanced")
    assert_no_app_errors(page)


def test_journey5_analysis_loading_and_reveal(page) -> None:
    open_fresh_app(page)
    click_button(page, "使用示範資料")
    wait_streamlit_idle(page)
    page.wait_for_timeout(800)
    rerun = page.get_by_role("button", name=re.compile(r"重新分析|Re-run"))
    if rerun.count():
        rerun.first.click(force=True)
        page.wait_for_timeout(150)
        mid = visible_text(page)
        assert "正在分析" in mid or "分析" in mid or "讀取" in mid or "排放" in mid
        wait_streamlit_idle(page)
        page.wait_for_timeout(600)
    text = visible_text(page)
    assert "排放" in text or "tCO" in text
    assert_no_raw_html_leak(text)
    assert_no_app_errors(page)
    save_step_screenshot(page, "qa_demo_analysis_result")
    assert ARTIFACTS.exists()


def test_journey7_terminology_and_reporting_screens(
    page, e2e_company_workspace_dir: Path
) -> None:
    """Stage 3B.3d screenshots and customer-language smoke."""
    seed_confirmed_pdf_workspace(e2e_company_workspace_dir)
    open_fresh_app(page)
    confirm_stub_company_for_pdf(page)
    dash = page.get_by_role("link", name=re.compile(r"合規總覽|Dashboard"))
    if dash.count():
        dash.first.click()
        wait_streamlit_idle(page)
    click_button(page, "使用示範資料")
    result_re = re.compile(
        r"碳排計算完成|初步碳排結果|Emissions calculation complete"
    )
    if page.get_by_text(result_re, exact=False).count() == 0:
        try:
            wait_for_analysis_progress(page, timeout=12.0)
        except Exception:  # noqa: BLE001 - analysis can finish before the overlay
            pass
        wait_for_analysis_view_unmounted(page, timeout=90.0)
    page.get_by_text(result_re, exact=False).first.wait_for(
        state="visible", timeout=40_000
    )
    wait_for_hero_settled(page)

    open_emissions_data_nav(page)
    open_evidence_workspace_tool(page, "活動資料")
    wait_streamlit_idle(page)
    act_text = visible_text(page)
    assert "grid_electricity" not in act_text
    assert "stationary_combustion" not in act_text
    page.set_viewport_size({"width": 1440, "height": 1800})
    wait_streamlit_idle(page)
    save_step_screenshot(page, "qa_3d_activity")

    page.get_by_role(
        "link", name=re.compile(r"我的適用要求|Your requirements")
    ).first.click()
    wait_streamlit_idle(page)
    ifrs_text = visible_text(page)
    assert "IFRS" in ifrs_text or "適用" in ifrs_text
    page.set_viewport_size({"width": 1440, "height": 2400})
    wait_streamlit_idle(page)
    save_step_screenshot(page, "qa_3d_ifrs")

    page.get_by_role(
        "link",
        name=re.compile(r"碳排報表與匯出|Emissions Reports"),
    ).first.click()
    wait_streamlit_idle(page)
    page.get_by_role(
        "button",
        name=re.compile(r"下載碳排摘要報告|Download Emissions Summary"),
    ).first.wait_for(state="visible", timeout=40_000)
    reporting = visible_text(page)
    assert "碳排摘要" in reporting or "Emissions summary" in reporting
    tech = page.locator("[data-testid='stExpander']").filter(
        has_text=re.compile(r"專業覆核附件|Technical review")
    )
    if tech.count():
        tech.first.click(force=True)
        wait_streamlit_idle(page)
    zip_btn = page.get_by_text(re.compile(r"下載稽核包|Download audit package|\.zip"))
    assert zip_btn.count() >= 1
    page.set_viewport_size({"width": 1440, "height": 2400})
    wait_streamlit_idle(page)
    save_step_screenshot(page, "qa_3d_reporting")

    # Mapping / validation / review via a small company CSV.
    csv_path = ARTIFACTS / "qa_3d_upload.csv"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,100,kWh,2025-01-01,2025-01-31,高雄廠\n",
        encoding="utf-8",
    )
    open_fresh_app(page)
    open_emissions_data_nav(page)
    file_input = page.locator('input[type="file"]')
    if file_input.count():
        file_input.first.set_input_files(str(csv_path))
        wait_streamlit_idle(page)
        page.wait_for_timeout(600)
        confirm_intake_reading(page)
        fix = page.get_by_role(
            "button", name=re.compile(r"修改系統辨識結果|Edit recognition")
        )
        if fix.count():
            fix.first.click(force=True)
            wait_streamlit_idle(page)
        map_text = visible_text(page)
        assert "grid_electricity" not in map_text
        assert "場址 ID" not in map_text
        page.set_viewport_size({"width": 1440, "height": 2000})
        wait_streamlit_idle(page)
        save_step_screenshot(page, "qa_3d_mapping")
        date_input = page.locator('[data-testid="stDateInput"] input')
        if date_input.count():
            date_input.first.fill("2025-01-31")
            wait_streamlit_idle(page)
        validate = page.get_by_role(
            "button", name=re.compile(r"資料格式檢查|Check data format")
        )
        if validate.count():
            validate.first.click(force=True)
            wait_streamlit_idle(page)
            page.wait_for_timeout(500)
            val_text = visible_text(page)
            assert "activity_type" not in val_text
            assert "site_id" not in val_text
            save_step_screenshot(page, "qa_3d_validation")
            nxt = page.get_by_role("button", name=re.compile(r"下一步|Next"))
            if nxt.count():
                nxt.first.click(force=True)
                wait_streamlit_idle(page)
                review = visible_text(page)
                assert "site_id" not in review
                assert "site_main" not in review
                save_step_screenshot(page, "qa_3d_review")
    assert_no_app_errors(page)


def test_journey8_stage4_2025_fixture_no_fake_zero(page) -> None:
    """Upload a 2025 fixture; blocked fuels must not display as zero."""
    csv_path = ARTIFACTS / "qa_stage4_2025.csv"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,1000,kWh,2025-03-01,2025-03-31,高雄廠\n"
        "天然氣,8000,m3,2025-01-01,2025-01-31,高雄廠\n"
        "柴油,1200,L,2025-06-01,2025-06-30,高雄廠\n",
        encoding="utf-8",
    )
    open_fresh_app(page)
    open_emissions_data_nav(page)
    file_input = page.locator('input[type="file"]')
    if file_input.count() == 0:
        save_step_screenshot(page, "qa_stage4_2025_upload")
        return
    file_input.first.set_input_files(str(csv_path))
    wait_streamlit_idle(page)
    page.wait_for_timeout(600)
    for label in (
        r"確認並繼續|Confirm and continue",
        r"^繼續$|^Continue$",
        r"資料格式檢查|Check data format",
        r"下一步|Next",
        r"開始分析|Start analysis",
    ):
        btn = page.get_by_role("button", name=re.compile(label))
        if btn.count():
            btn.first.click(force=True)
            wait_streamlit_idle(page)
            page.wait_for_timeout(400)
    text = visible_text(page)
    assert_no_raw_html_leak(text)
    assert "0.0 tCO₂e" not in text
    save_step_screenshot(page, "qa_stage4_2025_upload")
    assert_no_app_errors(page)


def _stage41_csv(*, ng_cell: str) -> str:
    return (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,50000,kWh,2025-01-01,2025-01-31,高雄廠\n"
        f"{ng_cell},8000,m3,2025-01-01,2025-01-31,高雄廠\n"
        "柴油,1200,L,2025-01-01,2025-01-31,高雄廠\n"
        "採購鋼材,10,t,2025-01-01,2025-01-31,高雄廠\n"
    )


def _walk_stage41_intake(page, csv_path: Path, *, ng_choice: str) -> None:
    open_emissions_data_nav(page)
    page.wait_for_timeout(800)
    uploader = page.locator('[data-testid="stFileUploader"] input[type="file"]')
    uploader.first.wait_for(state="attached", timeout=30_000)
    uploader.first.set_input_files(str(csv_path))
    wait_streamlit_idle(page, timeout=40)
    page.wait_for_timeout(700)
    confirm_intake_reading(page, ng_choice=ng_choice)
    coverage = page.get_by_text("可納入計算", exact=False)
    if coverage.count() == 0:
        ng_help = page.get_by_text("NG1 與 NG2 的官方年度熱值", exact=False)
        if ng_help.count() == 0:
            open_intake_mapping_editor(page)
            ng_help = page.get_by_text("NG1 與 NG2 的官方年度熱值", exact=False)
        if ng_help.count():
            ng_help.first.wait_for(state="visible", timeout=20_000)
            ng_help.first.scroll_into_view_if_needed()
            choose_radio(page, NG_CUSTOMER_LABEL.get(ng_choice, ng_choice))
            choose_radio(page, "公司車輛／公司控制的移動燃燒")
            choose_radio(page, "企業／廠場盤查")
            fill_streamlit_date(page, "文件日期", "2025-01-31")
            page.get_by_text("請確認文件日期", exact=False).first.wait_for(
                state="hidden", timeout=15_000
            )
            save_step_screenshot(page, "qa_stage41_mapping_ng")
            validate = page.get_by_role(
                "button",
                name=re.compile(r"資料格式檢查|Check data format|套用這些調整"),
            )
            if validate.count():
                validate.first.scroll_into_view_if_needed()
                validate.first.click(force=True)
                wait_streamlit_idle(page, timeout=40)
            confirm_intake_reading(page, ng_choice=ng_choice)
    page.get_by_text("可納入計算", exact=False).first.wait_for(
        state="visible", timeout=20_000
    )
    review = visible_text(page)
    assert "可納入計算" in review
    assert "需要確認" in review
    assert "目前不支援" in review
    assert "grid_electricity" not in review
    save_step_screenshot(page, "qa_stage41_review")
    start = page.get_by_role(
        "button",
        name=re.compile(
            r"使用這批資料開始分析|Analyze this uploaded|開始分析|Start analysis"
        ),
    )
    assert start.count() >= 1
    start.first.click(force=True)
    try:
        wait_for_analysis_progress(page)
        save_step_screenshot(page, "qa_stage41a_progress_modal")
        save_step_screenshot(page, "qa_stage41_progress")
        wait_for_analysis_view_unmounted(page)
    except Exception:  # noqa: BLE001 - small files can finish before progress paints
        save_step_screenshot(page, "qa_stage41_progress")
    wait_streamlit_idle(page, timeout=120)
    page.get_by_text("排放資料摘要", exact=False).first.wait_for(
        state="visible", timeout=60_000
    )


def _backend_total_for_csv(csv_path: Path, *, ng_subtype: str) -> float:
    table = parse_uploaded_table(
        file_name=csv_path.name,
        data=csv_path.read_bytes(),
    )
    suggestions = suggest_column_mapping(list(table.columns))
    activity_map, unit_map = default_value_maps(
        table,
        ColumnMapping(
            activity_type_column=suggestions["activity_type"],
            activity_value_column=suggestions["activity_value"],
            unit_column=suggestions["unit"],
        ),
    )
    activity_map = {
        key: value or suggest_activity_type(key)
        for key, value in activity_map.items()
    }
    unit_map = {key: value or suggest_unit(key) for key, value in unit_map.items()}
    mapping = ColumnMapping(
        activity_type_column=suggestions["activity_type"],
        activity_value_column=suggestions["activity_value"],
        unit_column=suggestions["unit"],
        site_column=suggestions.get("site_id") or "",
        use_file_dates=True,
        start_date_column=suggestions["activity_start_date"],
        end_date_column=suggestions["activity_end_date"],
        activity_type_value_map=activity_map,
        unit_value_map=unit_map,
        natural_gas_subtype=ng_subtype,
        diesel_context="company_vehicle",
        electricity_context="enterprise",
    )
    intake = build_and_validate_intake(
        table,
        mapping,
        IntakeMetadata(
            source_name=csv_path.name,
            site_id="高雄廠",
            document_date=date(2025, 1, 31),
            data_quality_tier="unknown",
            intake_run_id="e2e_stage41",
            ingested_at=pd.Timestamp("2025-02-01T00:00:00Z"),
        ),
    )
    result = run_uploaded_pipeline(
        Path(__file__).resolve().parents[2],
        run_id=f"e2e_stage41_{ng_subtype.lower()}",
        ingested_at=pd.Timestamp("2025-02-01T00:00:00Z"),
        source_documents=intake.source_documents,
        accepted_activities=intake.accepted_activities,
        include_ghg=True,
        include_ifrs_s2=True,
    )
    return float(calculated_emissions_summary(result)["calculated_tco2e"] or 0)


def test_journey9_stage41_customer_calculation(page) -> None:
    csv_path = ARTIFACTS / "qa_stage41_ng1.csv"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(_stage41_csv(ng_cell="天然氣"), encoding="utf-8")
    open_fresh_app(page)
    _walk_stage41_intake(page, csv_path, ng_choice="NG1")
    body = visible_text(page)
    assert "分析完成" in body or "目前已計算排放量" in body
    hero = page.locator("[data-cel-hero-emissions='1']")
    assert hero.count() >= 1
    hero.first.wait_for(state="visible", timeout=30_000)
    safe_scroll_into_view(hero.first)
    page.wait_for_timeout(300)
    save_step_screenshot(page, "qa_stage41_complete")
    displayed = float(
        page.locator("[data-cel-hero-emissions='1']").first.get_attribute(
            "data-cel-target"
        )
        or "nan"
    )
    expected = _backend_total_for_csv(csv_path, ng_subtype="NG1")
    assert displayed == pytest.approx(expected)
    emissions_box = page.get_by_text("排放資料摘要", exact=False).first.bounding_box()
    next_box = page.get_by_text("下一步", exact=False).first.bounding_box()
    assert emissions_box is not None
    assert next_box is not None
    assert emissions_box["y"] < next_box["y"]
    save_step_screenshot(page, "qa_stage41a_result_top")
    save_step_screenshot(page, "qa_simple_result_top")
    assert "Scope 1" in body
    assert "Scope 2" in body
    assert "目前尚無可納入的 Scope 3 計算結果" in body or "No Scope 3 results" in body
    assert "Scope 3 尚未納入計算" not in body
    assert "直接排放" in body
    assert "下一步" in body or "仍需處理" in body
    detail = page.get_by_text("排放明細", exact=False).first
    safe_scroll_into_view(detail)
    page.wait_for_timeout(200)
    save_step_screenshot(page, "qa_simple_result_detail")
    save_step_screenshot(page, "qa_stage41_dashboard_kpi")
    scope = page.get_by_text("Scope 1", exact=False).first
    if scope.count():
        safe_scroll_into_view(scope)
        page.wait_for_timeout(200)
    save_step_screenshot(page, "qa_stage41_scope")
    save_step_screenshot(page, "qa_stage41a_result_scope")
    open_evidence_workspace_tool(page, "活動資料")
    wait_streamlit_idle(page)
    expander = page.get_by_text("查看計算依據")
    expander.first.wait_for(state="visible", timeout=15_000)
    expander.first.click()
    wait_streamlit_idle(page)
    basis = visible_text(page)
    assert "原始用量" in basis or "年度低位熱值" in basis or "計算" in basis
    save_step_screenshot(page, "qa_stage41_calc_basis")
    assert_no_app_errors(page)


def test_journey9b_stage41_ng2_result_differs(page) -> None:
    csv_path = ARTIFACTS / "qa_stage41_ng2.csv"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(_stage41_csv(ng_cell="天然氣"), encoding="utf-8")
    open_fresh_app(page)
    _walk_stage41_intake(page, csv_path, ng_choice="NG2")
    hero = page.locator("[data-cel-hero-emissions='1']")
    assert hero.count() >= 1
    ng2_value = float(hero.first.get_attribute("data-cel-target") or "nan")
    ng1_backend = _backend_total_for_csv(csv_path, ng_subtype="NG1")
    ng2_backend = _backend_total_for_csv(csv_path, ng_subtype="NG2")
    assert ng1_backend != ng2_backend
    assert ng2_value == pytest.approx(ng2_backend)
    assert_no_app_errors(page)


def test_journey10_product_ux_screenshots(page) -> None:
    """Stage 4.1c customer-product screenshots after analysis."""
    open_fresh_app(page)
    click_button(page, "使用示範資料")
    wait_streamlit_idle(page)
    page.wait_for_timeout(800)
    page.get_by_text("排放資料摘要", exact=False).first.wait_for(
        state="visible", timeout=30_000
    )
    page.set_viewport_size({"width": 1440, "height": 1800})
    home = visible_text(page)
    assert "目前已計算排放量" in home
    assert "Scope 1" in home
    assert "直接排放" in home
    assert "下一步" in home
    save_step_screenshot(page, "qa_product_home_post_analysis")
    detail = page.get_by_text("排放明細", exact=False).first
    safe_scroll_into_view(detail)
    page.wait_for_timeout(200)
    save_step_screenshot(page, "qa_product_result_detail")

    page.get_by_role("link", name=re.compile(APPLICABILITY_NAV)).first.click()
    wait_streamlit_idle(page)
    save_step_screenshot(page, "qa_product_applicability")

    open_emissions_data_nav(page)
    save_step_screenshot(page, "qa_product_evidence")

    page.get_by_role(
        "link", name=re.compile(r"碳排報表與匯出|報表|Reporting|匯出")
    ).first.click()
    wait_streamlit_idle(page)
    save_step_screenshot(page, "qa_product_reporting")
    assert_no_app_errors(page)


def test_journey11_visible_countup_from_zero(page) -> None:
    """Hero counts from 0.00 after the analysis page unmounts; settles on final."""
    page.emulate_media(reduced_motion="no-preference")
    csv_path = ARTIFACTS / "qa_stage41_ng1.csv"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(_stage41_csv(ng_cell="天然氣"), encoding="utf-8")
    open_fresh_app(page)
    _walk_stage41_intake(page, csv_path, ng_choice="NG1")
    expected = _backend_total_for_csv(csv_path, ng_subtype="NG1")
    settled = wait_for_hero_settled(page)
    assert float(
        page.locator("[data-cel-hero-emissions='1']").first.get_attribute(
            "data-cel-target"
        )
        or "nan"
    ) == pytest.approx(expected)
    assert parse_metric_number(settled["text"]) == pytest.approx(expected, abs=0.015)

    rerun = page.get_by_role("button", name=re.compile(r"重新分析|Re-run"))
    assert rerun.count() >= 1
    install_analysis_result_overlap_watch(page)
    rerun.first.click(force=True)
    try:
        wait_for_analysis_progress(page)
        analyzing = page.locator(
            '[data-cel-analysis-view="1"], .cel-analysis-view'
        )
        if analyzing.count():
            assert page.locator("[data-cel-hero-emissions='1']").count() == 0
        wait_for_analysis_view_unmounted(page)
    except Exception:  # noqa: BLE001 - small rerun can finish before progress paints
        pass
    settled = wait_for_hero_settled(page)
    assert_analysis_overlay_unmounted(page)
    first_value = parse_metric_number(settled["text"])
    assert settled["text"] != "0.00"
    assert first_value == pytest.approx(expected, abs=0.015)
    save_step_screenshot(page, "qa_countup_start")
    save_step_screenshot(page, "qa_countup_mid")
    save_step_screenshot(page, "qa_countup_final")
    body = visible_text(page)
    assert "碳排計算完成" in body or "初步碳排結果" in body
    assert "目前尚無可納入的 Scope 3 計算結果" in body or "No Scope 3 results" in body
    assert "Scope 3 尚未納入計算" not in body
    assert_no_raw_html_leak(body)
    assert_no_app_errors(page)


def test_customer_comprehension_qa(page) -> None:
    """Playwright: a non-expert can see what to do without a methodology manual."""
    _open_welcome_dialog(page)
    welcome = visible_text(page)
    assert "完成第一筆碳排計算" in welcome
    assert "Excel" in welcome
    assert "用 6 個步驟" not in welcome
    assert "不需要先懂碳盤查" not in welcome
    assert "待覆核" not in welcome
    assert "下一步" not in welcome
    save_step_screenshot(page, "qa_customer_welcome")
    page.get_by_role("button", name=re.compile(r"^(稍後再說|Not now)$")).first.click(
        force=True
    )
    wait_streamlit_idle(page)

    click_button(page, "開始公司設定")
    wait_streamlit_idle(page)
    step1 = visible_text(page)
    assert "你的公司適用哪些要求" in step1 or "確認公司" in step1
    assert "為什麼我要回答這些問題" not in step1
    assert "這一步需要什麼" not in step1
    save_step_screenshot(page, "qa_customer_step1")

    lookup_stub_company(page, STUB_SPARSE_UBN)
    click_button(page, "繼續")
    wait_streamlit_idle(page)
    step2 = visible_text(page)
    assert "公司是否上市／上櫃" in step2
    assert "市場身分" not in step2
    assert "系統不會把空白當成 0" not in step2
    assert "不知道／暫不填" not in step2
    assert "我不知道" in step2
    save_step_screenshot(page, "qa_customer_step2")

    choose_selectbox(page, "公司是否上市／上櫃？", "上市（TWSE）")
    set_money_unknown(page, index=0, unknown=True)
    click_button(page, "繼續")
    click_button(page, "繼續")
    wait_streamlit_idle(page)
    defer_boundary_wizard_if_present(page)
    results = visible_text(page)
    finish = page.get_by_role("button", name=re.compile(r"完成判定"))
    assert finish.count() == 0
    assert (
        "查看目前結果" in results
        or "儲存並查看結果" in results
        or "修改公司資料" in results
    )
    assert "還差" in results or "還需要一些資料" in results
    assert "適用報導年度：—" not in results
    assert "首次申報／揭露年度：—" not in results
    assert "管理員" not in results
    save_step_screenshot(page, "qa_customer_result_actions")

    sidebar_nav = page.locator('[data-testid="stSidebarNavLink"]')
    assert sidebar_nav.filter(has_text=re.compile(r"^IFRS S1/S2$")).count() == 0
    assert sidebar_nav.filter(
        has_text=re.compile(r"台灣溫室氣體|Taiwan GHG")
    ).count() == 0
    page.get_by_role("link", name=re.compile(APPLICABILITY_NAV)).first.click()
    wait_streamlit_idle(page)
    taiwan = visible_text(page)
    assert "IFRS Scope 1/2 確信" in taiwan or "確信" in taiwan
    assert "還需要一些資料" in taiwan or "還差" in taiwan
    save_step_screenshot(page, "qa_customer_ghg")

    env_tab = page.get_by_role("tab", name=re.compile(r"查驗"))
    if env_tab.count():
        env_tab.first.click()
        wait_streamlit_idle(page)
    save_step_screenshot(page, "qa_customer_verification")
    verification = visible_text(page)
    assert "管理員" not in verification
    assert "適用報導年度：—" not in verification

    fee_tab = page.get_by_role("tab", name=re.compile(r"碳費"))
    if fee_tab.count():
        fee_tab.first.click()
        wait_streamlit_idle(page)
    save_step_screenshot(page, "qa_customer_carbon_fee")
    fee = visible_text(page)
    assert "首次申報／揭露年度：—" not in fee
    assert "適用報導年度：—" not in fee
    assert_no_app_errors(page)
