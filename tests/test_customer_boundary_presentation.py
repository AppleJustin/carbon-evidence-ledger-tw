"""Customer-facing boundary / Scope 3 presentation closure."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from carbon_ledger.applicability import (
    STATUS_APPLICABLE,
    STATUS_NEEDS_INFORMATION,
    STATUS_NOT_APPLICABLE,
    ApplicabilityAssessment,
    ObligationResult,
)
from carbon_ledger.company_master import (
    SOURCE_OFFICIAL_FACTORY,
    CompanyMaster,
    FacilityMaster,
    FacilityMasterRecord,
)
from carbon_ledger.company_workspace import CompanyWorkspace
from carbon_ledger.inventory_boundary import (
    CATEGORY_EXPECTED,
    CONSOLIDATION_CONSOLIDATED,
    CONSOLIDATION_STANDALONE,
    CONSOLIDATION_UNRESOLVED,
    EVIDENCE_CONFIRMED_COMPANY_DOCUMENT,
    EVIDENCE_CUSTOMER_PENDING,
    PURPOSE_IFRS_REPORTING_ENTITY,
    PURPOSE_LISTED_CONSOLIDATED,
    PURPOSE_MOENV_FACILITY,
    REQUIREMENT_NEEDS_FACT,
    SOURCE_CATEGORIES,
    ExpectedSourceCategory,
    FinancialStatementReportingEntityEvidence,
    InventoryBoundary,
    RegistrationLink,
    ReportingPeriod,
    boundaries_from_reviews,
    initial_boundary_semantics_state,
    purpose_reviews_from_assessment,
)
from carbon_ledger.legal_entity import LegalEntity
from carbon_ledger.ui.boundary_wizard import (
    BoundaryWizardContext,
    _customer_purpose_status_key,
    _ifrs_step_required,
    _known_legal_entities,
    _purpose_label,
    _reporting_entity_reviews,
    _step_after_purposes,
    _step_before_registrations,
    draft_reporting_entity_evidence,
    included_legal_entity_ids_for_basis,
)
from carbon_ledger.ui.i18n import MESSAGES, t
from carbon_ledger.ui.state import activate_demo_mode
from carbon_ledger.ui.view_models import labeled_scope_hero_caption

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "streamlit_app.py"
WIZARD = ROOT / "src/carbon_ledger/ui/boundary_wizard.py"
ZH = "zh-TW"
EN = "en"

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

CUSTOMER_MESSAGE_PREFIXES = (
    "boundary.wizard.",
    "boundary.purpose.",
    "dash.hero.scope3_version",
    "dash.scope3_unsupported",
    "dash.scope3_short",
    "dash.scope3.empty",
    "dash.scope3.partial",
    "dash.scope_help_body",
)
ADMIN_KEY_MARKERS = (".admin_",)


def _period() -> ReportingPeriod:
    return ReportingPeriod.confirmed(
        reporting_year_suggested=2026,
        reporting_year_confirmed=2026,
        period_start_confirmed="2026-01-01",
        period_end_confirmed="2026-12-31",
    )


def _assessment(obligations: dict[str, ObligationResult]) -> ApplicabilityAssessment:
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


def _company() -> CompanyMaster:
    return CompanyMaster(
        company_id="co_12345675",
        company_name="長興材料工業股份有限公司",
        unified_business_number="12345675",
        listing_status="TWSE",
    )


def _entity() -> LegalEntity:
    return LegalEntity(
        entity_id="co_12345675",
        legal_name="長興材料工業股份有限公司",
        jurisdiction="TW",
        taiwan_ubn="12345675",
    )


def _subsidiary() -> LegalEntity:
    return LegalEntity(
        entity_id="sub_001",
        legal_name="長興材料工業（蘇州）有限公司",
        jurisdiction="CN",
        parent_entity_id="co_12345675",
    )


def _reporting_basis_button_label(evidence: object) -> str:
    key = (
        "boundary.wizard.reporting_entities.confirm"
        if getattr(evidence, "confirms_reporting_entity", False)
        else "boundary.wizard.reporting_entities.save_basis"
    )
    return t(key, ZH)


def _ifrs_state() -> object:
    assessment = _assessment(
        {
            "ifrs_s1_s2": ObligationResult(
                obligation_id="ifrs_s1_s2",
                obligation_name="IFRS S1/S2",
                status=STATUS_APPLICABLE,
                applied_rule_ids=["tw_order_51756_phase1_ge_10bn"],
            ),
            "verification_assurance": ObligationResult(
                obligation_id="verification_assurance",
                obligation_name="Verification",
                status=STATUS_APPLICABLE,
                applied_rule_ids=[
                    "tw_order_51756_scope12_consolidated_assurance"
                ],
            ),
        }
    )
    return initial_boundary_semantics_state(
        assessment=assessment,
        company=_company(),
        facilities=[],
        workspace_id="tw-ubn-12345675",
        reporting_period=_period(),
    )


def _assert_no_customer_internal_codes(text: str) -> None:
    for token in CUSTOMER_INTERNAL_LEAK_TOKENS:
        assert token not in text, f"customer copy leaked {token!r}"


def _customer_message_keys() -> list[str]:
    keys: list[str] = []
    for key in MESSAGES:
        if any(key.startswith(prefix) for prefix in CUSTOMER_MESSAGE_PREFIXES):
            if any(marker in key for marker in ADMIN_KEY_MARKERS):
                continue
            keys.append(key)
    return keys


def test_customer_i18n_hides_internal_rule_and_migration_codes() -> None:
    samples = {
        "year": 2026,
        "company": "測試公司",
        "current": 1,
        "total": 2,
        "name": "IFRS S1／S2",
        "names": "IFRS S1／S2、上市櫃合併申報範圍",
        "boundaries": 1,
        "registrations": 2,
        "categories": 3,
        "obligation": "hidden",
        "status": "hidden",
        "rules": "hidden",
    }
    for key in _customer_message_keys():
        for lang in (ZH, EN):
            _assert_no_customer_internal_codes(t(key, lang, **samples))


def test_purpose_status_copy_is_customer_language() -> None:
    class _Review:
        assessment_status = "NEEDS_REVIEW"
        outcome = "unresolved"
        purpose = PURPOSE_MOENV_FACILITY
        effective_year = 2026
        obligation_id = "ghg_inventory"
        applied_rule_ids = ("tw_order_51756_phase1_ge_10bn",)

    key = _customer_purpose_status_key(_Review())
    for lang in (ZH, EN):
        label = t(key, lang)
        _assert_no_customer_internal_codes(label)
        assert label
    assert t(key, ZH) == "可能適用，仍需確認"


def test_customer_wizard_source_keeps_diagnostics_behind_admin() -> None:
    source = WIZARD.read_text(encoding="utf-8")
    purpose = source.split("def _purpose_step", maxsplit=1)[1].split(
        "\ndef ", maxsplit=1
    )[0]
    assert "admin_provenance" in purpose
    before_admin, after_admin = purpose.split("is_admin_mode", maxsplit=1)
    assert "obligation_id" not in before_admin
    assert "assessment_status" not in before_admin
    assert "applied_rule_ids" not in before_admin
    assert "obligation_id" in after_admin

    migration = source.split("def _render_migration_action", maxsplit=1)[1].split(
        "\ndef ", maxsplit=1
    )[0]
    assert "if run_clicked:" in migration
    before_click, after_click = migration.split("if run_clicked:", maxsplit=1)
    assert "migrate_boundary_semantics_v2" not in before_click
    assert "migrate_boundary_semantics_v2" in after_click
    assert "dry_run_boundary_semantics_migration" in migration
    admin_block = migration.split("is_admin_mode", maxsplit=1)[1]
    assert "dry_run_boundary_semantics_migration" in admin_block
    assert "dry_run_boundary_semantics_migration" not in before_click.split(
        "is_admin_mode", maxsplit=1
    )[0]


def test_ifrs_page_is_skipped_when_not_applicable() -> None:
    assessment = _assessment(
        {
            "ghg_inventory": ObligationResult(
                obligation_id="ghg_inventory",
                obligation_name="GHG Inventory",
                status=STATUS_NEEDS_INFORMATION,
            ),
            "ifrs_s1_s2": ObligationResult(
                obligation_id="ifrs_s1_s2",
                obligation_name="IFRS S1/S2",
                status=STATUS_NOT_APPLICABLE,
                applied_rule_ids=["tw_order_51756_phase1_ge_10bn"],
            ),
        }
    )
    reviews = purpose_reviews_from_assessment(
        assessment=assessment,
        workspace_id="tw-ubn-12345675",
        reporting_period_id=_period().reporting_period_id,
    )
    state = initial_boundary_semantics_state(
        assessment=assessment,
        company=_company(),
        facilities=[],
        workspace_id="tw-ubn-12345675",
        reporting_period=_period(),
    )
    assert PURPOSE_IFRS_REPORTING_ENTITY not in {
        item.purpose for item in reviews
    }
    assert [item.purpose for item in reviews] == [PURPOSE_MOENV_FACILITY]
    assert _reporting_entity_reviews(state) == []
    assert _ifrs_step_required(state) is False
    assert _step_after_purposes(state) == 4
    assert _step_before_registrations(state) == 2


def test_ifrs_guided_flow_does_not_auto_choose_statements() -> None:
    state = _ifrs_state()
    reviews = _reporting_entity_reviews(state)
    assert {item.purpose for item in reviews} == {
        PURPOSE_IFRS_REPORTING_ENTITY,
        PURPOSE_LISTED_CONSOLIDATED,
    }
    source = WIZARD.read_text(encoding="utf-8")
    step = source.split("def _reporting_entity_step", maxsplit=1)[1].split(
        "\ndef ", maxsplit=1
    )[0]
    assert "else CONSOLIDATION_UNRESOLVED" in step
    assert "expanded=False" in step
    assert "boundary.wizard.reporting_entities.evidence_expander" in step
    assert "disabled=basis == CONSOLIDATION_UNRESOLVED" in step
    assert "facilities.records" not in step
    assert "context.facilities" not in step
    assert "STATE_BOUNDARY_COMPANY_INDEX" not in step
    assert "boundary.wizard.reporting_entities.progress" not in step
    assert step.count("st.radio(") == 1
    assert "save_basis" in step
    assert "draft.confirms_reporting_entity" in step
    assert "need_subsidiaries" in step
    assert t("boundary.wizard.reporting_entities.save_basis", ZH) == "儲存報導基礎"
    assert t("boundary.wizard.reporting_entities.confirm", ZH) == "確認此報導範圍"
    assert t("boundary.wizard.reporting_entities.title", ZH) == "確認永續揭露報導個體"
    assert "boundary.wizard.reporting_entities.limit" in step
    assert t("boundary.wizard.reporting_entities.need_subsidiaries", ZH) == (
        "補齊子公司法律實體範圍後，才能確認合併報導範圍。"
    )


def test_known_legal_entities_exclude_facility_records() -> None:
    context = BoundaryWizardContext(
        assessment=_assessment({}),
        company=_company(),
        facilities=FacilityMaster(
            records=[
                FacilityMasterRecord(
                    facility_id="fac_kaohsiung",
                    display_name="高雄一廠",
                    address="高雄市前鎮區",
                    source_type=SOURCE_OFFICIAL_FACTORY,
                )
            ]
        ),
        workspace=None,  # type: ignore[arg-type]
        assessment_year=2026,
        active_period_key="boundary_active_period_test",
    )
    names = [
        item.legal_name
        for item in _known_legal_entities(context, _ifrs_state())
    ]
    ids = [
        item.entity_id
        for item in _known_legal_entities(context, _ifrs_state())
    ]
    assert names == ["長興材料工業股份有限公司"]
    assert "高雄一廠" not in names
    assert "fac_kaohsiung" not in ids


def test_basis_without_document_stays_pending_and_creates_no_boundary() -> None:
    period = _period()
    pending = draft_reporting_entity_evidence(
        existing=None,
        reporting_period_id=period.reporting_period_id,
        entity=_entity(),
        basis=CONSOLIDATION_STANDALONE,
        reporting_entity_name="長興材料工業股份有限公司",
        financial_statement_title="2026 個別財務報表",
        provenance_reference="",
        included_legal_entity_ids=("co_12345675",),
    )
    assert pending.verification_state == EVIDENCE_CUSTOMER_PENDING
    assert pending.confirms_reporting_entity is False
    assert pending.included_legal_entity_ids == ()
    assert _reporting_basis_button_label(pending) == "儲存報導基礎"
    state = _ifrs_state()
    built = boundaries_from_reviews(
        reviews=state.purpose_reviews,
        reporting_period=period,
        legal_entities=(_entity(),),
        financial_statement_evidence=(pending,),
    )
    purposes = {item.purpose for item in built}
    assert PURPOSE_IFRS_REPORTING_ENTITY not in purposes
    assert PURPOSE_LISTED_CONSOLIDATED not in purposes


def test_document_reference_can_confirm_standalone_without_listed_boundary() -> None:
    period = _period()
    confirmed = draft_reporting_entity_evidence(
        existing=None,
        reporting_period_id=period.reporting_period_id,
        entity=_entity(),
        basis=CONSOLIDATION_STANDALONE,
        reporting_entity_name="長興材料工業股份有限公司",
        provenance_reference="board/2026-fs.pdf",
        included_legal_entity_ids=("co_12345675", "sub_001"),
        known_legal_entity_ids=("co_12345675", "sub_001"),
    )
    assert confirmed.verification_state == EVIDENCE_CONFIRMED_COMPANY_DOCUMENT
    assert confirmed.confirms_reporting_entity is True
    assert confirmed.included_legal_entity_ids == ("co_12345675",)
    assert _reporting_basis_button_label(confirmed) == "確認此報導範圍"
    state = _ifrs_state()
    built = boundaries_from_reviews(
        reviews=state.purpose_reviews,
        reporting_period=period,
        legal_entities=(_entity(), _subsidiary()),
        financial_statement_evidence=(confirmed,),
    )
    purposes = {item.purpose for item in built}
    assert PURPOSE_IFRS_REPORTING_ENTITY in purposes
    assert PURPOSE_LISTED_CONSOLIDATED not in purposes


def test_standalone_includes_only_the_current_company() -> None:
    included = included_legal_entity_ids_for_basis(
        basis=CONSOLIDATION_STANDALONE,
        company_entity_id="co_12345675",
        candidate_ids=("co_12345675", "sub_001", "fac_kaohsiung"),
        known_legal_entity_ids=("co_12345675", "sub_001"),
    )
    assert included == ("co_12345675",)
    pending = draft_reporting_entity_evidence(
        existing=None,
        reporting_period_id=_period().reporting_period_id,
        entity=_entity(),
        basis=CONSOLIDATION_STANDALONE,
        reporting_entity_name="長興材料工業股份有限公司",
        provenance_reference="",
        included_legal_entity_ids=("co_12345675", "sub_001"),
        known_legal_entity_ids=("co_12345675", "sub_001"),
    )
    assert pending.confirms_reporting_entity is False
    assert _reporting_basis_button_label(pending) == "儲存報導基礎"


def test_consolidated_with_only_parent_and_document_stays_pending() -> None:
    period = _period()
    pending = draft_reporting_entity_evidence(
        existing=None,
        reporting_period_id=period.reporting_period_id,
        entity=_entity(),
        basis=CONSOLIDATION_CONSOLIDATED,
        reporting_entity_name="長興集團",
        provenance_reference="group/2026-cfs.pdf",
        included_legal_entity_ids=("co_12345675",),
        known_legal_entity_ids=("co_12345675",),
    )
    assert pending.verification_state == EVIDENCE_CUSTOMER_PENDING
    assert pending.confirms_reporting_entity is False
    assert pending.included_legal_entity_ids == ()
    assert _reporting_basis_button_label(pending) == "儲存報導基礎"
    state = _ifrs_state()
    built = boundaries_from_reviews(
        reviews=state.purpose_reviews,
        reporting_period=period,
        legal_entities=(_entity(),),
        financial_statement_evidence=(pending,),
    )
    purposes = {item.purpose for item in built}
    assert PURPOSE_IFRS_REPORTING_ENTITY not in purposes
    assert PURPOSE_LISTED_CONSOLIDATED not in purposes
    assert (
        t("boundary.wizard.reporting_entities.no_subsidiaries", ZH)
        == "目前系統僅有本公司資料；合併報導個體與子公司範圍仍待補充。"
    )
    assert t("boundary.wizard.reporting_entities.need_subsidiaries", ZH) == (
        "補齊子公司法律實體範圍後，才能確認合併報導範圍。"
    )


def test_consolidated_confirms_with_parent_subsidiary_and_complete_evidence() -> None:
    period = _period()
    confirmed = draft_reporting_entity_evidence(
        existing=None,
        reporting_period_id=period.reporting_period_id,
        entity=_entity(),
        basis=CONSOLIDATION_CONSOLIDATED,
        reporting_entity_name="長興集團",
        provenance_reference="group/2026-cfs.pdf",
        included_legal_entity_ids=("co_12345675", "sub_001"),
        known_legal_entity_ids=("co_12345675", "sub_001"),
    )
    assert confirmed.verification_state == EVIDENCE_CONFIRMED_COMPANY_DOCUMENT
    assert confirmed.confirms_reporting_entity is True
    assert confirmed.included_legal_entity_ids == ("co_12345675", "sub_001")
    assert _reporting_basis_button_label(confirmed) == "確認此報導範圍"
    state = _ifrs_state()
    built = boundaries_from_reviews(
        reviews=state.purpose_reviews,
        reporting_period=period,
        legal_entities=(_entity(), _subsidiary()),
        financial_statement_evidence=(confirmed,),
    )
    purposes = {item.purpose for item in built}
    assert PURPOSE_IFRS_REPORTING_ENTITY in purposes
    assert PURPOSE_LISTED_CONSOLIDATED in purposes


def test_facilities_never_enter_included_legal_entity_ids() -> None:
    standalone = draft_reporting_entity_evidence(
        existing=None,
        reporting_period_id=_period().reporting_period_id,
        entity=_entity(),
        basis=CONSOLIDATION_STANDALONE,
        reporting_entity_name="長興材料工業股份有限公司",
        provenance_reference="board/2026-fs.pdf",
        included_legal_entity_ids=("co_12345675", "fac_kaohsiung"),
        known_legal_entity_ids=("co_12345675",),
    )
    consolidated = draft_reporting_entity_evidence(
        existing=None,
        reporting_period_id=_period().reporting_period_id,
        entity=_entity(),
        basis=CONSOLIDATION_CONSOLIDATED,
        reporting_entity_name="長興集團",
        provenance_reference="group/2026-cfs.pdf",
        included_legal_entity_ids=("co_12345675", "sub_001", "fac_kaohsiung"),
        known_legal_entity_ids=("co_12345675", "sub_001"),
    )
    assert "fac_kaohsiung" not in standalone.included_legal_entity_ids
    assert "fac_kaohsiung" not in consolidated.included_legal_entity_ids
    assert standalone.included_legal_entity_ids == ("co_12345675",)
    assert consolidated.included_legal_entity_ids == ("co_12345675", "sub_001")


def test_ifrs_step_is_skipped_when_not_required() -> None:
    empty = initial_boundary_semantics_state(
        assessment=_assessment(
            {
                "ghg_inventory": ObligationResult(
                    obligation_id="ghg_inventory",
                    obligation_name="GHG Inventory",
                    status=STATUS_NEEDS_INFORMATION,
                )
            }
        ),
        company=_company(),
        facilities=[],
        workspace_id="tw-ubn-12345675",
        reporting_period=_period(),
    )
    assert _ifrs_step_required(empty) is False
    assert _step_after_purposes(empty) == 4
    assert _step_before_registrations(empty) == 2
    ifrs_state = _ifrs_state()
    assert _ifrs_step_required(ifrs_state) is True
    assert _step_after_purposes(ifrs_state) == 3
    assert _step_before_registrations(ifrs_state) == 3


def test_review_and_purpose_labels_hide_internal_purpose_codes() -> None:
    for purpose in (
        PURPOSE_IFRS_REPORTING_ENTITY,
        PURPOSE_LISTED_CONSOLIDATED,
        PURPOSE_MOENV_FACILITY,
    ):
        for lang in (ZH, EN):
            label = _purpose_label(purpose, lang)
            assert purpose not in label
            _assert_no_customer_internal_codes(label)
    source = WIZARD.read_text(encoding="utf-8")
    assert "({boundary.purpose})" not in source
    assert "_purpose_label(boundary.purpose" in source


def test_optional_ifrs_evidence_does_not_change_engine_confirmation() -> None:
    evidence = FinancialStatementReportingEntityEvidence(
        evidence_id="financial_evidence",
        reporting_period_id=_period().reporting_period_id,
        financial_statement_title="",
        financial_statement_type="",
        issuer_or_source="",
        reporting_entity_identifier="co_12345675",
        reporting_entity_name="長興材料工業股份有限公司",
        consolidation_basis=CONSOLIDATION_STANDALONE,
        included_legal_entity_ids=("co_12345675",),
        provenance_reference="",
        verification_state=EVIDENCE_CONFIRMED_COMPANY_DOCUMENT,
    )
    assert evidence.consolidation_basis != CONSOLIDATION_UNRESOLVED
    assert evidence.confirms_reporting_entity is False


def test_later_copy_does_not_mark_ifrs_complete_or_block_calculations() -> None:
    for lang in (ZH, EN):
        later = t("boundary.wizard.later_not_confirmed", lang)
        help_text = t("boundary.wizard.reporting_entities.unresolved_help", lang)
        _assert_no_customer_internal_codes(later)
        _assert_no_customer_internal_codes(help_text)
    assert "不會把任何項目標示為已確認" in t(
        "boundary.wizard.later_not_confirmed", ZH
    )
    assert "不會阻擋 Scope 1／Scope 2" in t(
        "boundary.wizard.reporting_entities.unresolved_help", ZH
    )
    wizard = WIZARD.read_text(encoding="utf-8")
    assert "carbon_ledger.calculate" not in wizard
    assert "match_factors" not in wizard
    assert "heating.py" not in wizard


def test_legacy_status_hides_notice_when_no_old_data(tmp_path: Path) -> None:
    workspace = CompanyWorkspace.for_company(
        root=tmp_path, taiwan_ubn="12345675"
    )
    assert (
        workspace.boundary_semantics_migration_status(
            reporting_period_id=_period().reporting_period_id
        )
        == "not_required"
    )


def test_legacy_migration_stays_inert_until_explicit_confirm(tmp_path: Path) -> None:
    workspace = CompanyWorkspace.for_company(
        root=tmp_path, taiwan_ubn="12345675"
    )
    period = _period()
    legacy = InventoryBoundary(
        boundary_id="legacy_boundary",
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
    assert (
        workspace.boundary_semantics_migration_status(
            reporting_period_id=period.reporting_period_id
        )
        == "v1_detected"
    )
    assert workspace.load_semantics_current(
        reporting_period_id=period.reporting_period_id
    ) is None
    prepared = workspace.prepare_boundary_semantics_v2_migration(
        initial_boundary_semantics_state(
            assessment=_assessment(
                {
                    "ghg_inventory": ObligationResult(
                        obligation_id="ghg_inventory",
                        obligation_name="GHG Inventory",
                        status=STATUS_NEEDS_INFORMATION,
                    )
                }
            ),
            company=_company(),
            facilities=[
                FacilityMasterRecord(
                    facility_id="raw_one",
                    display_name="政府工廠一",
                    address="高雄市一號",
                    official_factory_registration_number="REG-001",
                    company_unified_business_number="12345675",
                    discovered_from=(SOURCE_OFFICIAL_FACTORY,),
                )
            ],
            workspace_id="tw-ubn-12345675",
            reporting_period=period,
        )
    )
    assert prepared.canonical_sites == ()
    assert prepared.operating_facts == ()
    assert prepared.boundaries == ()
    migrated = workspace.migrate_boundary_semantics_v2(
        state=prepared,
        dry_run_reviewed=True,
    )
    assert legacy_path.read_bytes() == before
    assert migrated.canonical_sites == ()
    assert workspace.boundary_semantics_migration_status(
        reporting_period_id=period.reporting_period_id
    ) == "v2_current"


def test_scope3_copy_is_complete_in_zh_and_en_and_not_zero() -> None:
    zh = t("dash.scope3.empty", ZH)
    en = t("dash.scope3.empty", EN)
    assert zh == "目前尚無可納入的 Scope 3 計算結果。"
    assert "No Scope 3 results can be included yet." in en
    assert "尚未納入計算" not in zh
    assert "不支援" not in zh
    for text in (zh, en):
        assert "0 tCO" not in text
        assert "0.00" not in text
        _assert_no_customer_internal_codes(text)
    partial = t(
        "dash.scope3.partial",
        ZH,
        value="24.15",
        categories="Category 1－採購商品與服務",
    )
    assert "目前已計算 24.15 tCO2e" in partial
    assert "Category 1－採購商品與服務" in partial
    assert "尚不代表完整 Scope 3 總量" in partial
    caption = labeled_scope_hero_caption(
        {
            "scope_1": {"state": "calculated", "value": 10.0},
            "scope_2": {"state": "calculated", "value": 5.0},
            "scope_3": {"state": "empty", "value": None},
        },
        ZH,
    )
    assert "Scope 3" not in caption
    assert "0.00" not in caption or "10.00" in caption


def test_demo_dashboard_scope3_is_not_rendered_as_zero() -> None:
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    activate_demo_mode(at.session_state)
    at.run()
    chunks: list[str] = []
    for collection_name in (
        "markdown",
        "caption",
        "text",
        "info",
        "success",
        "warning",
        "title",
    ):
        collection = getattr(at, collection_name, None)
        if collection is None:
            continue
        for item in collection:
            value = getattr(item, "value", None)
            if value:
                chunks.append(str(value))
    text = "\n".join(chunks)
    assert t("dash.scope3.empty", ZH) in text
    assert "Scope 3 尚未納入計算" not in text
    assert re.search(r"Scope 3[^\n]{0,120}0(?:\.00)?\s*tCO", text) is None
    _assert_no_customer_internal_codes(t("dash.scope3.empty", ZH))


def test_analysis_countup_assets_were_not_rewritten() -> None:
    hero = ROOT / "src/carbon_ledger/ui/hero_emissions_countup.js"
    digest = hashlib.sha256(hero.read_bytes()).hexdigest()
    assert digest == (
        "70cd43b7f1fa2bedf4485bc7846278b736e1c183961c6c7117d6cc8b5f5828c0"
    )
    progress = (ROOT / "app_pages/analysis_progress.py").read_text(encoding="utf-8")
    assert "render_analysis_transition_view" in progress
