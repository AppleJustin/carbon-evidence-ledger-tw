"""Stage 3B.3d — customer terminology and reporting IA."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest
from test_emissions_report_closure import prepare_session_for_pdf_export

from carbon_ledger.domain import ACTIVITY_TYPES
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
from carbon_ledger.ui.i18n import t
from carbon_ledger.ui.purchased_steel_confirmation import accepted_review_preview
from carbon_ledger.ui.state import (
    STATE_INTAKE_FILE_NAME,
    STATE_INTAKE_METADATA,
    STATE_INTAKE_RESULT,
    STATE_INTAKE_SHOW_MAPPING_EDITOR,
    STATE_INTAKE_STEP,
    STATE_INTAKE_TABLE,
    activate_demo_mode,
    initialize_ui_state,
)
from carbon_ledger.ui.view_models import (
    activity_display_name,
    build_activity_overview,
    customer_schema_label,
    customer_site_display,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "streamlit_app.py"
ZH = "zh-TW"
EN = "en"

RAW_CODES = (
    "grid_electricity",
    "stationary_combustion",
    "mobile_combustion",
    "natural_gas",
    "site_id",
    "record_id",
    "factor_id",
    "source_id",
    "rule_id",
    "evaluation_id",
    "MONITORING_PARTIAL",
    "NEEDS_INFORMATION",
    "MANUAL_VERIFICATION_REQUIRED",
    "NOT_ACTIVATED",
    "site_main",
    "activity_type",
    "activity_value",
)


def _run(page: str | None = None, *, demo: bool = False) -> AppTest:
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    initialize_ui_state(at.session_state)
    if demo:
        activate_demo_mode(at.session_state)
        at.run()
    if page:
        at.switch_page(page)
        at.run()
    assert not at.exception
    return at


def _surface(at: AppTest) -> str:
    chunks: list[str] = []
    for name in ("title", "header", "subheader", "markdown", "text", "info"):
        collection = getattr(at, name, None)
        if collection is None:
            continue
        for item in collection:
            value = getattr(item, "value", None) or getattr(item, "body", None)
            if value:
                chunks.append(str(value))
    for button in at.button:
        if getattr(button, "label", None):
            chunks.append(str(button.label))
    for item in getattr(at, "download_button", []):
        if getattr(item, "label", None):
            chunks.append(str(item.label))
    for item in getattr(at, "selectbox", []):
        if getattr(item, "label", None):
            chunks.append(str(item.label))
        for option in getattr(item, "options", []) or []:
            chunks.append(str(option))
    return "\n".join(chunks)


def _customer_csv() -> bytes:
    return (
        "活動類型,用量,單位,開始日期,結束日期,廠場\n"
        "外購電力,100,kWh,2025-01-01,2025-01-31,高雄廠\n"
        "天然氣,80,m3,2025-01-01,2025-01-31,高雄廠\n"
    ).encode("utf-8")


def _validated_intake(*, site: str = "高雄廠"):
    table = parse_uploaded_table(
        file_name="company.csv",
        data=_customer_csv(),
    )
    suggestions = suggest_column_mapping(list(table.columns))
    activity_map, unit_map = default_value_maps(
        table,
        ColumnMapping(
            activity_type_column=suggestions["activity_type"],
            activity_value_column=suggestions["activity_value"],
            unit_column=suggestions["unit"],
            site_column=suggestions.get("site_id", ""),
        ),
    )
    activity_map = {
        key: value or suggest_activity_type(key) for key, value in activity_map.items()
    }
    unit_map = {key: value or suggest_unit(key) for key, value in unit_map.items()}
    mapping = ColumnMapping(
        activity_type_column=suggestions["activity_type"],
        activity_value_column=suggestions["activity_value"],
        unit_column=suggestions["unit"],
        site_column=suggestions.get("site_id", ""),
        use_file_dates=True,
        start_date_column=suggestions["activity_start_date"],
        end_date_column=suggestions["activity_end_date"],
        activity_type_value_map=activity_map,
        unit_value_map=unit_map,
    )
    metadata = IntakeMetadata(
        source_name="company.csv",
        site_id=site,
        document_date=date(2025, 1, 31),
        data_quality_tier="unknown",
        intake_run_id="ui_intake_3d",
        ingested_at=__import__("pandas").Timestamp("2025-02-01T00:00:00Z"),
    )
    return build_and_validate_intake(table, mapping, metadata), table, metadata


def test_mapping_dropdown_shows_human_labels_not_backend_codes() -> None:
    table = parse_uploaded_table(file_name="company.csv", data=_customer_csv())
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    initialize_ui_state(at.session_state)
    at.session_state[STATE_INTAKE_TABLE] = table
    at.session_state[STATE_INTAKE_FILE_NAME] = "company.csv"
    at.session_state[STATE_INTAKE_STEP] = 3
    at.session_state[STATE_INTAKE_SHOW_MAPPING_EDITOR] = True
    at.switch_page("app_pages/data_intake.py")
    at.run()
    assert not at.exception
    options: list[str] = []
    for box in at.selectbox:
        for option in getattr(box, "options", []) or []:
            options.append(str(option))
    blob = "\n".join(options)
    assert "外購電力" in blob
    assert "grid_electricity" not in blob
    assert "natural_gas" not in blob
    assert "stationary_combustion" not in blob
    for code in ACTIVITY_TYPES:
        assert f"/ {code}" not in blob


def test_validation_preview_headers_are_human_readable() -> None:
    intake, table, metadata = _validated_intake()
    accepted = intake.accepted_activities
    assert not accepted.empty

    zh_preview = accepted_review_preview(
        accepted,
        lang=ZH,
        status=t("intake.result_accepted", ZH),
        issue="—",
    )
    en_preview = accepted_review_preview(
        accepted,
        lang=EN,
        status=t("intake.result_accepted", EN),
        issue="—",
    )
    zh_columns = [str(col) for col in zh_preview.columns]
    en_columns = [str(col) for col in en_preview.columns]
    internal = {
        "activity_type",
        "activity_value",
        "activity_start_date",
        "site_id",
    }
    assert internal.isdisjoint(zh_columns)
    assert internal.isdisjoint(en_columns)
    assert t("intake.field.activity_type", ZH) in zh_columns
    assert t("intake.field.activity_value", ZH) in zh_columns
    assert t("intake.field.site_id", ZH) in zh_columns
    assert "活動類型" in zh_columns
    assert "用量" in zh_columns
    assert "廠場／營運據點" in zh_columns
    assert t("intake.field.activity_type", EN) in en_columns
    assert t("intake.field.activity_value", EN) in en_columns
    assert t("intake.field.site_id", EN) in en_columns

    helper = (
        REPO_ROOT / "src/carbon_ledger/ui/purchased_steel_confirmation.py"
    ).read_text(encoding="utf-8")
    assert "def accepted_review_preview(" in helper
    assert 't("intake.field.activity_type"' in helper
    assert "preview.rename" in helper
    page = (REPO_ROOT / "app_pages/data_intake.py").read_text(encoding="utf-8")
    assert "accepted_review_preview(" in page

    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    initialize_ui_state(at.session_state)
    at.session_state[STATE_INTAKE_TABLE] = table
    at.session_state[STATE_INTAKE_FILE_NAME] = "company.csv"
    at.session_state[STATE_INTAKE_RESULT] = intake
    at.session_state[STATE_INTAKE_METADATA] = metadata
    at.session_state[STATE_INTAKE_STEP] = 4
    at.switch_page("app_pages/data_intake.py")
    at.run()
    assert not at.exception
    columns: list[str] = []
    for item in getattr(at, "dataframe", []):
        value = getattr(item, "value", None)
        if value is None:
            value = getattr(item, "data", None)
        if value is None:
            continue
        columns.extend(str(col) for col in getattr(value, "columns", []))
    joined = " ".join(columns)
    assert joined
    assert "activity_type" not in joined
    assert "activity_value" not in joined
    assert "activity_start_date" not in joined
    assert "site_id" not in joined
    assert "活動類型" in joined
    assert "用量" in joined
    assert "廠場／營運據點" in joined


def test_customer_never_sees_site_id_as_normal_field() -> None:
    assert customer_schema_label("site_id", ZH) == "廠場／營運據點"
    assert "Site ID" not in customer_schema_label("site_id", EN)
    assert "場址 ID" not in t("intake.site_name", ZH)
    page = (REPO_ROOT / "app_pages/data_intake.py").read_text(encoding="utf-8")
    assert "intake.site_name" in page
    assert 't("intake.site_id"' not in page


def test_no_site_main_production_default() -> None:
    assert customer_site_display("site_main", ZH) == t("intake.site_unconfirmed", ZH)
    assert customer_site_display("UNKNOWN", ZH) == t("intake.site_unconfirmed", ZH)
    assert customer_site_display("高雄廠", ZH) == "高雄廠"
    page = (REPO_ROOT / "app_pages/data_intake.py").read_text(encoding="utf-8")
    assert "site_main" not in page
    assert 'site_id.strip() or "UNKNOWN"' in page


def test_activity_filter_uses_translated_labels() -> None:
    at = _run("app_pages/activity_explorer.py", demo=True)
    options: list[str] = []
    for box in at.selectbox:
        options.extend(str(option) for option in getattr(box, "options", []) or [])
    blob = "\n".join(options)
    assert "grid_electricity" not in blob
    assert "stationary_combustion" not in blob
    assert "mobile_combustion" not in blob
    assert "外購電力" in blob
    explorer = (REPO_ROOT / "app_pages/activity_explorer.py").read_text(
        encoding="utf-8"
    )
    assert 'overview["activity_name"]' in explorer
    from carbon_ledger.ui.state import get_current_result

    overview = build_activity_overview(get_current_result(at.session_state), ZH)
    names = set(overview["activity_name"].astype(str))
    assert "外購電力" in names
    assert "grid_electricity" not in names


def test_audit_zip_under_technical_files_not_primary(monkeypatch, tmp_path) -> None:
    page = (REPO_ROOT / "app_pages/audit_export.py").read_text(encoding="utf-8")
    pdf = page.index("aud_pdf_dl")
    tech = page.index("report.technical_files")
    zip_key = page.index("aud_zip_dl")
    assert pdf < tech < zip_key
    at = _run(demo=True)
    prepare_session_for_pdf_export(at.session_state, monkeypatch, tmp_path)
    at.switch_page("app_pages/audit_export.py")
    at.run()
    text = _surface(at)
    assert "碳排摘要報告" in text or "Emissions Summary" in text
    labels = [str(item.label) for item in at.download_button]
    assert any("PDF" in label or "碳排摘要" in label for label in labels)
    assert any(
        "稽核包" in label or "audit package" in label.lower() for label in labels
    )


def test_run_id_hidden_by_default(monkeypatch, tmp_path) -> None:
    page = (REPO_ROOT / "app_pages/audit_export.py").read_text(encoding="utf-8")
    assert page.index("aud.audit_trace") < page.index("aud.tech_ids")
    assert page.index("aud.tech_ids") < page.index('t("aud.run_id"')
    at = _run(demo=True)
    prepare_session_for_pdf_export(at.session_state, monkeypatch, tmp_path)
    at.switch_page("app_pages/audit_export.py")
    at.run()
    labels = [
        str(getattr(item, "label", "") or "")
        for item in getattr(at, "expander", [])
    ]
    assert any("稽核追溯" in label for label in labels)
    assert any("技術識別" in label for label in labels)


def test_ifrs_readiness_labeled_climate_metrics_not_compliance(monkeypatch) -> None:
    monkeypatch.setenv("CEL_APP_MODE", "admin")
    at = _run("app_pages/frameworks.py", demo=True)
    text = _surface(at)
    assert "氣候指標資料準備度" in text
    assert "Climate Metrics Data Readiness" in t("fw.metrics_readiness_title", EN)
    assert "不代表 IFRS S1/S2 整體符合程度" in text
    assert "合規百分比" not in text
    assert "readiness 84" not in text.lower()


def test_pre_analysis_review_shows_site_name_not_site_id() -> None:
    intake, table, metadata = _validated_intake(site="高雄廠")
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    initialize_ui_state(at.session_state)
    at.session_state[STATE_INTAKE_TABLE] = table
    at.session_state[STATE_INTAKE_FILE_NAME] = "company.csv"
    at.session_state[STATE_INTAKE_RESULT] = intake
    at.session_state[STATE_INTAKE_METADATA] = metadata
    at.session_state[STATE_INTAKE_STEP] = 5
    at.switch_page("app_pages/data_intake.py")
    at.run()
    assert not at.exception
    text = _surface(at)
    assert "廠場／營運據點" in text
    assert "高雄廠" in text
    assert "site_id" not in text
    assert "site_main" not in text
    assert "場址 ID" not in text
    assert "資料筆數" in text


def test_raw_backend_enums_absent_from_default_customer_pages() -> None:
    pages = (
        "app_pages/dashboard.py",
        "app_pages/applicability.py",
        "app_pages/frameworks.py",
        "app_pages/taiwan_ghg.py",
        "app_pages/data_intake.py",
        "app_pages/audit_export.py",
    )
    for page in pages:
        at = _run(page)
        text = _surface(at)
        for token in RAW_CODES:
            assert token not in text, f"{token} leaked on {page}"


def test_activity_display_names_cover_enums() -> None:
    for code in ACTIVITY_TYPES:
        label_zh = activity_display_name(code, ZH)
        label_en = activity_display_name(code, EN)
        assert label_zh != code
        assert label_en != code
        assert "_" not in label_zh
        if "_" in code:
            assert code not in label_zh
            assert code not in label_en
