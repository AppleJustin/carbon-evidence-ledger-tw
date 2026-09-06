"""Customer-facing boundary / Scope 3 presentation E2E and screenshots."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest
from playwright.sync_api import expect

E2E_DIR = Path(__file__).resolve().parent
if str(E2E_DIR) not in sys.path:
    sys.path.insert(0, str(E2E_DIR))

from helpers import (  # noqa: E402
    STUB_ALIGNED_UBN,
    STUB_SPARSE_UBN,
    assert_no_app_errors,
    choose_radio,
    choose_selectbox,
    click_button,
    fill_streamlit_date,
    lookup_stub_company,
    open_fresh_app,
    save_step_screenshot,
    visible_text,
    wait_streamlit_idle,
)

from carbon_ledger.applicability import (  # noqa: E402
    STATUS_APPLICABLE,
    STATUS_NEEDS_INFORMATION,
    ApplicabilityAssessment,
    ObligationResult,
)
from carbon_ledger.company_lookup import stub_company  # noqa: E402
from carbon_ledger.company_master import SOURCE_OFFICIAL_FACTORY  # noqa: E402
from carbon_ledger.company_workspace import CompanyWorkspace  # noqa: E402
from carbon_ledger.inventory_boundary import (  # noqa: E402
    CATEGORY_EXPECTED,
    PURPOSE_IFRS_REPORTING_ENTITY,
    REQUIREMENT_NEEDS_FACT,
    SOURCE_CATEGORIES,
    ExpectedSourceCategory,
    InventoryBoundary,
    RegistrationLink,
    ReportingPeriod,
    initial_boundary_semantics_state,
)
from carbon_ledger.ui.i18n import t  # noqa: E402

pytestmark = pytest.mark.e2e

CUSTOMER_INTERNAL_LEAK_TOKENS = (
    "dry-run",
    "boundary-semantics-v2",
    "rollback",
    "NEEDS_REVIEW",
    "APPLICABLE",
    "ghg_inventory",
    "ifrs_s1_s2",
    "tw_order_",
    "ifrs_reporting_entity",
    "listed_consolidated",
    "moenv_facility",
)
ZH = "zh-TW"
EN = "en"


def _assert_no_customer_internal_codes(text: str) -> None:
    for token in CUSTOMER_INTERNAL_LEAK_TOKENS:
        assert token not in text, f"customer DOM leaked {token!r}"


def _wizard(page):
    return page.locator(".st-key-cel_boundary_wizard_root")


def _footer(page):
    return _wizard(page).locator(".st-key-cel_boundary_footer")


def _capture_1440(page, name: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    wait_streamlit_idle(page)
    path = save_step_screenshot(page, name, required=True, full_page=False)
    assert path.is_file() and path.stat().st_size > 0


def _lookup_company(page, ubn: str, *, force_listed: bool) -> None:
    if force_listed:
        lookup_stub_company(page, ubn)
        return
    field = page.get_by_label("統一編號")
    if field.count():
        field.first.fill(ubn)
    else:
        page.locator('input[type="text"]').first.fill(ubn)
    wait_streamlit_idle(page)
    lookup = page.get_by_role("button", name="查詢公司")
    lookup.first.click(force=True)
    wait_streamlit_idle(page)
    confirm = page.get_by_role("button", name="這是我的公司")
    if confirm.count():
        confirm.first.click(force=True)
        wait_streamlit_idle(page)
    if page.get_by_text("公司是否上市／上櫃").count():
        choose_selectbox(page, "公司是否上市／上櫃？", "未上市／未上櫃")


def _goto_boundary_wizard(
    page, *, reporting_year: int, ubn: str = STUB_ALIGNED_UBN
) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    open_fresh_app(page)
    click_button(page, "開始公司設定")
    _lookup_company(page, ubn, force_listed=ubn == STUB_ALIGNED_UBN)
    year = page.locator('input[aria-label="要評估哪一年度？"]')
    year.fill(str(reporting_year))
    year.press("Tab")
    wait_streamlit_idle(page)
    click_button(page, "繼續")
    click_button(page, "繼續")
    facilities_confirm = page.get_by_role(
        "button", name="是，3 個都正確", exact=True
    )
    if facilities_confirm.count() and facilities_confirm.first.is_visible():
        facilities_confirm.first.click()
        wait_streamlit_idle(page)
    click_button(page, "繼續")
    expect(page.get_by_text("確認報導期間", exact=True)).to_be_visible()
    year_field = page.locator('input[aria-label="報導年度"]')
    if year_field.count():
        year_field.first.fill(str(reporting_year))
        year_field.first.press("Tab")
        wait_streamlit_idle(page)
    fill_streamlit_date(page, "期間開始日", f"{reporting_year}-01-01")
    fill_streamlit_date(page, "期間結束日", f"{reporting_year}-12-31")


def _confirm_period(page) -> None:
    page.get_by_text("我已確認報導年度、開始日與結束日", exact=True).click()
    button = _footer(page).get_by_role("button", name="儲存並繼續", exact=True)
    button.scroll_into_view_if_needed()
    button.click()
    wait_streamlit_idle(page)


def _period(year: int) -> ReportingPeriod:
    return ReportingPeriod.confirmed(
        reporting_year_suggested=year,
        reporting_year_confirmed=year,
        period_start_confirmed=f"{year}-01-01",
        period_end_confirmed=f"{year}-12-31",
    )


def _assessment(*, ifrs: bool) -> ApplicabilityAssessment:
    obligations: dict[str, ObligationResult] = {
        "ghg_inventory": ObligationResult(
            obligation_id="ghg_inventory",
            obligation_name="GHG Inventory",
            status=STATUS_NEEDS_INFORMATION,
        )
    }
    if ifrs:
        obligations["ifrs_s1_s2"] = ObligationResult(
            obligation_id="ifrs_s1_s2",
            obligation_name="IFRS S1/S2",
            status=STATUS_APPLICABLE,
            applied_rule_ids=["tw_order_51756_phase1_ge_10bn"],
        )
        obligations["verification_assurance"] = ObligationResult(
            obligation_id="verification_assurance",
            obligation_name="Verification",
            status=STATUS_APPLICABLE,
            applied_rule_ids=["tw_order_51756_scope12_consolidated_assurance"],
        )
    return ApplicabilityAssessment(
        assessment_timestamp="2026-08-24T00:00:00Z",
        reporting_year=2026,
        company_profile_snapshot={},
        obligations=obligations,
        rule_ids_used=[],
        rule_versions_used={},
        regulatory_freshness_snapshot={},
        result_statuses={},
    )


def test_customer_boundary_review_hides_internal_codes(page) -> None:
    _goto_boundary_wizard(page, reporting_year=2026)
    _confirm_period(page)
    expect(
        page.get_by_text("為何這些申報目的需要覆核", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_text("偵測到先前版本的盤查設定", exact=True)
    ).to_have_count(0)
    wizard = _wizard(page)
    body = wizard.inner_text() + "\n" + wizard.inner_html()
    _assert_no_customer_internal_codes(body)
    assert "可能適用，仍需確認" in wizard.inner_text()
    assert "政府登記候選不是已確認的政府登記結果" in wizard.inner_text()
    _capture_1440(page, "qa_customer_boundary_review_no_internal_codes")
    assert_no_app_errors(page)


def test_legacy_settings_customer_notice(
    page, e2e_company_workspace_dir: Path
) -> None:
    year = 2028
    period = _period(year)
    workspace = CompanyWorkspace.for_company(
        root=e2e_company_workspace_dir, taiwan_ubn=STUB_ALIGNED_UBN
    )
    legacy = InventoryBoundary(
        boundary_id="legacy_boundary_customer",
        purpose=PURPOSE_IFRS_REPORTING_ENTITY,
        requirement_status=REQUIREMENT_NEEDS_FACT,
        display_name="舊版範圍提示",
        reporting_period=period,
        registration_links=(
            RegistrationLink(
                registration_link_id="registration_link_one",
                registration_identity="REG-001",
                facility_id="raw_one",
                official_source=SOURCE_OFFICIAL_FACTORY,
                location="高雄市一號",
            ),
        ),
        expected_categories=tuple(
            ExpectedSourceCategory(category=item, state=CATEGORY_EXPECTED)
            for item in SOURCE_CATEGORIES
        ),
        schema_version="inventory-boundary-v1",
    )
    legacy_path = workspace.write_draft(legacy)
    before = legacy_path.read_bytes()
    period_dir = (
        workspace.path / "periods" / period.reporting_period_id
    )
    try:
        _goto_boundary_wizard(page, reporting_year=year)
        _confirm_period(page)
        expect(
            page.get_by_text("偵測到先前版本的盤查設定", exact=True)
        ).to_be_visible()
        notice = page.locator(".st-key-cel_boundary_migration_notice")
        expect(notice).to_be_visible()
        notice_dom = notice.inner_text() + "\n" + notice.inner_html()
        _assert_no_customer_internal_codes(notice_dom)
        assert "舊版邊界紀錄" not in notice.inner_text()
        assert "政府登記候選數" not in notice.inner_text()
        assert workspace.load_semantics_current(
            reporting_period_id=period.reporting_period_id
        ) is None
        _capture_1440(page, "qa_legacy_settings_customer_notice")
        click_button(page, "查看更新摘要")
        expect(page.get_by_text("更新摘要", exact=True)).to_be_visible()
        assert workspace.load_semantics_current(
            reporting_period_id=period.reporting_period_id
        ) is None
        assert legacy_path.read_bytes() == before
        click_button(page, "更新盤查設定")
        expect(
            page.get_by_text("盤查設定已更新", exact=False)
        ).to_be_visible()
        assert workspace.boundary_semantics_migration_status(
            reporting_period_id=period.reporting_period_id
        ) == "v2_current"
        assert legacy_path.read_bytes() == before
        expect(
            page.get_by_text("偵測到先前版本的盤查設定", exact=True)
        ).to_have_count(0)
        assert_no_app_errors(page)
    finally:
        shutil.rmtree(period_dir, ignore_errors=True)


def test_ifrs_reporting_entity_guided_flow(
    page, e2e_company_workspace_dir: Path
) -> None:
    year = 2027
    period = _period(year)
    workspace = CompanyWorkspace.for_company(
        root=e2e_company_workspace_dir, taiwan_ubn=STUB_ALIGNED_UBN
    )
    company = stub_company(STUB_ALIGNED_UBN)
    state = initial_boundary_semantics_state(
        assessment=_assessment(ifrs=True),
        company=company,
        facilities=[],
        workspace_id=workspace.workspace_id,
        reporting_period=period,
    )
    workspace.write_semantics_draft(state)
    period_dir = workspace.path / "periods" / period.reporting_period_id
    try:
        _goto_boundary_wizard(page, reporting_year=year)
        _confirm_period(page)
        expect(
            page.get_by_text("為何這些申報目的需要覆核", exact=True)
        ).to_be_visible()
        _assert_no_customer_internal_codes(_wizard(page).inner_text())
        button = _footer(page).get_by_role("button", name="儲存並繼續", exact=True)
        button.click()
        wait_streamlit_idle(page)
        expect(
            page.get_by_text("確認 IFRS 永續揭露涵蓋範圍", exact=True)
        ).to_be_visible()
        expect(page.get_by_text("本次確認會影響：", exact=False)).to_be_visible()
        expect(page.get_by_text("報導範圍 1／2", exact=False)).to_have_count(0)
        expect(page.get_by_text("另一項：", exact=False)).to_have_count(0)
        expect(page.get_by_text("個別財務報表", exact=True)).to_be_visible()
        expect(page.get_by_text("合併財務報表", exact=True)).to_be_visible()
        expect(page.get_by_text("尚未確認", exact=True)).to_be_visible()
        expect(
            page.get_by_text("補充財務報表資料（選填）", exact=True)
        ).to_be_visible()
        wizard = _wizard(page)
        assert "財務報表類型" not in wizard.inner_text()
        assert "高雄一廠" not in wizard.inner_text()
        radio = page.get_by_role("radio", name="尚未確認")
        if radio.count():
            expect(radio.first).to_be_checked()
        _assert_no_customer_internal_codes(wizard.inner_text() + wizard.inner_html())
        _capture_1440(page, "qa_ifrs_reporting_entity_guided_flow")

        choose_radio(page, "個別財務報表")
        expect(
            page.get_by_text("上市櫃合併申報範圍會維持待確認", exact=False)
        ).to_be_visible()
        save_basis = _footer(page).get_by_role(
            "button", name="儲存報導基礎", exact=True
        )
        expect(save_basis).to_be_visible()
        expect(
            _footer(page).get_by_role("button", name="確認此報導範圍", exact=True)
        ).to_have_count(0)
        save_basis.click(force=True)
        wait_streamlit_idle(page)
        saved = workspace.load_semantics_draft(
            reporting_period_id=period.reporting_period_id
        )
        assert saved is not None
        evidence = saved.financial_reporting_entity_evidence
        assert evidence
        assert evidence[0].consolidation_basis == "standalone"
        assert evidence[0].confirms_reporting_entity is False
        assert not any(
            item.purpose == "listed_consolidated" for item in saved.boundaries
        )
        assert not any(
            item.purpose == "ifrs_reporting_entity" for item in saved.boundaries
        )

        back = _footer(page).get_by_role("button", name="上一步", exact=True)
        back.click(force=True)
        wait_streamlit_idle(page)
        expect(
            page.get_by_text("確認 IFRS 永續揭露涵蓋範圍", exact=True)
        ).to_be_visible()
        page.get_by_text("補充財務報表資料（選填）", exact=True).click(
            force=True
        )
        wait_streamlit_idle(page)
        page.get_by_label("文件位置或證據參考").first.fill("board/2027-fs.pdf")
        page.get_by_label("文件位置或證據參考").first.press("Tab")
        wait_streamlit_idle(page)
        confirm = _footer(page).get_by_role(
            "button", name="確認此報導範圍", exact=True
        )
        expect(confirm).to_be_visible()
        confirm.click(force=True)
        wait_streamlit_idle(page)
        saved = workspace.load_semantics_draft(
            reporting_period_id=period.reporting_period_id
        )
        assert saved is not None
        assert saved.financial_reporting_entity_evidence[0].confirms_reporting_entity
        assert any(
            item.purpose == "ifrs_reporting_entity" for item in saved.boundaries
        )
        assert not any(
            item.purpose == "listed_consolidated" for item in saved.boundaries
        )
        later = _footer(page).get_by_role("button", name="稍後處理", exact=True)
        later.click()
        wait_streamlit_idle(page)
        body = visible_text(page)
        assert "稍後處理" in body or "適用" in body or "排放" in body
        assert_no_app_errors(page)
    finally:
        shutil.rmtree(period_dir, ignore_errors=True)


def test_scope3_not_included_disclosure(page) -> None:
    open_fresh_app(page)
    click_button(page, "使用示範資料")
    wait_streamlit_idle(page)
    page.set_viewport_size({"width": 1440, "height": 900})
    zh_copy = t("dash.scope3.empty", ZH)
    scope3 = page.locator("[data-testid='stColumn']").filter(
        has_text="Scope 3"
    ).filter(has=page.get_by_text("其他價值鏈排放", exact=True))
    expect(scope3).to_have_count(1)
    scope3.first.scroll_into_view_if_needed()
    expect(scope3.get_by_text(zh_copy, exact=False)).to_be_visible()
    text = scope3.inner_text()
    assert "目前尚無可納入的 Scope 3 計算結果" in text
    assert "Scope 3 尚未納入計算" not in text
    assert zh_copy in text
    assert "0 tCO₂e" not in text
    assert "0.00 tCO₂e" not in text
    assert "0 tCO2e" not in text
    assert "0.00 tCO2e" not in text
    assert re.search(r"\d+(?:[.,]\d+)?\s*tCO", text) is None
    _capture_1440(page, "qa_scope3_not_included_disclosure")
    lang = page.get_by_role("radio", name="EN")
    if lang.count() == 0:
        lang = page.get_by_text("EN", exact=True)
    if lang.count():
        lang.first.click(force=True)
        wait_streamlit_idle(page)
        en_copy = t("dash.scope3.empty", EN)
        scope3_en = page.locator("[data-testid='stColumn']").filter(
            has_text="Scope 3"
        ).filter(
            has=page.get_by_text("Other value-chain emissions", exact=True)
        )
        expect(scope3_en).to_have_count(1)
        en_text = scope3_en.inner_text()
        assert en_copy in en_text
        assert "0 tCO₂e" not in en_text
        assert "0.00 tCO₂e" not in en_text
        assert re.search(r"\d+(?:[.,]\d+)?\s*tCO", en_text) is None
    assert_no_app_errors(page)


def test_ifrs_not_applicable_skips_guided_page(page) -> None:
    _goto_boundary_wizard(
        page, reporting_year=2026, ubn=STUB_SPARSE_UBN
    )
    _confirm_period(page)
    button = _footer(page).get_by_role("button", name="儲存並繼續", exact=True)
    button.click()
    wait_streamlit_idle(page)
    expect(page.locator("[data-cel-ifrs-guided-flow='1']")).to_have_count(0)
    expect(
        page.get_by_text("確認 IFRS 永續揭露涵蓋範圍", exact=True)
    ).to_have_count(0)
    expect(
        page.get_by_text("把政府紀錄核對到實際公司據點", exact=True)
    ).to_be_visible()
    _assert_no_customer_internal_codes(_wizard(page).inner_text())
    back = _footer(page).get_by_role("button", name="上一步", exact=True)
    back.click(force=True)
    wait_streamlit_idle(page)
    expect(
        page.get_by_text("為何這些申報目的需要覆核", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_text("確認 IFRS 永續揭露涵蓋範圍", exact=True)
    ).to_have_count(0)
    assert_no_app_errors(page)


def test_wizard_steps_one_to_six_hide_internal_purpose_codes(page) -> None:
    _goto_boundary_wizard(page, reporting_year=2029)
    _confirm_period(page)
    reached_review = False
    for _ in range(14):
        wizard = _wizard(page)
        _assert_no_customer_internal_codes(
            wizard.inner_text() + "\n" + wizard.inner_html()
        )
        review_confirm = _footer(page).get_by_role(
            "button", name="在本機工作區確認此範圍", exact=True
        )
        if review_confirm.count():
            reached_review = True
            break
        if page.locator("[data-cel-ifrs-guided-flow='1']").count():
            expect(page.get_by_text("報導範圍 1／2", exact=False)).to_have_count(
                0
            )
            choose_radio(page, "個別財務報表")
            save_basis = _footer(page).get_by_role(
                "button", name="儲存報導基礎", exact=True
            )
            expect(save_basis).to_be_visible()
            expect(
                _footer(page).get_by_role(
                    "button", name="確認此報導範圍", exact=True
                )
            ).to_have_count(0)
            save_basis.click(force=True)
            wait_streamlit_idle(page)
            continue
        progressed = False
        for name in ("儲存並繼續", "繼續"):
            button = _footer(page).get_by_role("button", name=name, exact=True)
            if button.count() and button.first.is_enabled():
                button.first.click(force=True)
                wait_streamlit_idle(page)
                progressed = True
                break
        if not progressed:
            break
    assert reached_review
    expect(page.get_by_text("檢查並確認", exact=True).first).to_be_visible()
    assert_no_app_errors(page)
