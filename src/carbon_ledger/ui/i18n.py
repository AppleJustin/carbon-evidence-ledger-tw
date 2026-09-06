"""Centralized Traditional Chinese / English UI strings for Phase 8B.

Default language is Traditional Chinese (zh-TW). Identifiers such as record_id
are never translated. Official standard names may stay in English.
"""

from __future__ import annotations

from typing import Any

LANG_ZH = "zh-TW"
LANG_EN = "en"
DEFAULT_LANG = LANG_ZH
LANG_OPTIONS = ("繁中", "EN")
LANG_OPTION_TO_CODE = {"繁中": LANG_ZH, "EN": LANG_EN}
LANG_CODE_TO_OPTION = {LANG_ZH: "繁中", LANG_EN: "EN"}

STATE_LANGUAGE = "ui_language"

MESSAGES: dict[str, dict[str, str]] = {
    # Navigation — four customer destinations; IFRS / Taiwan remain admin-only
    "nav.dashboard": {"zh-TW": "合規總覽", "en": "Compliance Overview"},
    "nav.applicability": {"zh-TW": "我的適用要求", "en": "Your requirements"},
    "nav.ifrs": {"zh-TW": "IFRS S1/S2", "en": "IFRS S1/S2"},
    "nav.taiwan": {
        "zh-TW": "台灣溫室氣體與碳費",
        "en": "Taiwan GHG / Carbon Fee",
    },
    "nav.evidence": {
        "zh-TW": "排放資料與計算",
        "en": "Emissions Data & Calculations",
    },
    "nav.audit": {"zh-TW": "碳排報表與匯出", "en": "Emissions Reports & Exports"},
    # Hidden Evidence deep-link page titles (not primary sidebar items)
    "nav.intake": {"zh-TW": "資料匯入", "en": "Data Intake"},
    "nav.activity": {"zh-TW": "活動資料", "en": "Activity Data"},
    "nav.issues": {"zh-TW": "待處理問題", "en": "Issues & Actions"},
    "nav.frameworks": {"zh-TW": "IFRS S1/S2", "en": "IFRS S1/S2"},
    # Brand / header
    "brand.name": {
        "zh-TW": "Carbon Evidence Ledger",
        "en": "Carbon Evidence Ledger",
    },
    "brand.descriptor": {
        "zh-TW": "台灣出口企業碳資料準備與證據追蹤",
        "en": "Carbon data readiness for Taiwanese exporters",
    },
    "header.tutorial": {"zh-TW": "? 操作教學", "en": "? Tutorial"},
    "header.language_aria": {"zh-TW": "語言", "en": "Language"},
    # Sidebar
    "sidebar.current_analysis": {"zh-TW": "目前分析", "en": "Current analysis"},
    "sidebar.current_source": {"zh-TW": "目前資料來源", "en": "Current data source"},
    "sidebar.workspace_name": {
        "zh-TW": "虛構台灣扣件公司",
        "en": "Synthetic Taiwan Fastener Co.",
    },
    "sidebar.reporting_context": {
        "zh-TW": "2024 示範資料",
        "en": "2024 synthetic demonstration",
    },
    "sidebar.source_demo": {"zh-TW": "示範資料", "en": "Demo data"},
    "sidebar.source_uploaded": {
        "zh-TW": "你上傳的公司資料",
        "en": "Your uploaded company data",
    },
    "sidebar.analysis_contents": {"zh-TW": "分析內容", "en": "Analysis modules"},
    "sidebar.ghg_title": {"zh-TW": "公司碳盤查", "en": "Corporate GHG inventory"},
    "sidebar.ghg_help": {
        "zh-TW": "判斷公司活動屬於 Scope 1、2 或 3。",
        "en": "Classify activities as Scope 1, 2, or 3.",
    },
    "sidebar.cbam_title": {"zh-TW": "歐盟出口", "en": "EU export"},
    "sidebar.cbam_help": {
        "zh-TW": "判斷出口產品需要哪些碳資料，以及目前缺什麼。",
        "en": "See which carbon data an EU export product needs, and what is missing.",
    },
    "sidebar.ifrs_title": {"zh-TW": "氣候揭露", "en": "Climate disclosure"},
    "sidebar.ifrs_help": {
        "zh-TW": "判斷現有碳資料是否足以支援氣候資訊揭露準備。",
        "en": "See whether current carbon data can support climate disclosure prep.",
    },
    "sidebar.ifrs_note": {
        "zh-TW": "IFRS S2 會自動使用 GHG Protocol 分類結果作為來源證據。",
        "en": (
            "IFRS S2 automatically uses GHG Protocol classifications "
            "as source evidence."
        ),
    },
    "sidebar.run": {"zh-TW": "開始分析", "en": "Start analysis"},
    "sidebar.run_demo": {"zh-TW": "執行示範分析", "en": "Run demo analysis"},
    "sidebar.run_uploaded": {
        "zh-TW": "使用這批資料開始分析",
        "en": "Analyze this uploaded dataset",
    },
    "sidebar.rerun": {"zh-TW": "重新分析", "en": "Re-run analysis"},
    "sidebar.settings": {"zh-TW": "分析設定", "en": "Analysis settings"},
    "sidebar.settings_help": {
        "zh-TW": "選擇要一併執行的準則分析模組。預設全部開啟。",
        "en": "Choose framework modules to include. All are on by default.",
    },
    "sidebar.need_help": {"zh-TW": "需要協助？", "en": "Need help?"},
    "sidebar.tutorial_link": {
        "zh-TW": "操作教學 →",
        "en": "Tutorial →",
    },
    "sidebar.running": {"zh-TW": "正在分析…", "en": "Running analysis…"},
    "sidebar.loading": {
        "zh-TW": "正在整理資料並計算…",
        "en": "Preparing data and calculating…",
    },
    "sidebar.loading_demo": {
        "zh-TW": "正在整理內建示範資料…",
        "en": "Loading bundled synthetic evidence…",
    },
    "sidebar.loading_uploaded": {
        "zh-TW": "正在使用你上傳的資料進行分析…",
        "en": "Analyzing your uploaded company data…",
    },
    "sidebar.complete": {"zh-TW": "分析完成", "en": "Analysis complete"},
    "sidebar.pipeline_done": {
        "zh-TW": "管線已完成。",
        "en": "Pipeline complete.",
    },
    "analysis.stage.reading": {
        "zh-TW": "讀取資料",
        "en": "Reading data",
    },
    "analysis.stage.normalize": {
        "zh-TW": "標準化欄位與單位",
        "en": "Normalizing fields and units",
    },
    "analysis.stage.quality": {
        "zh-TW": "檢查資料品質",
        "en": "Checking data quality",
    },
    "analysis.stage.factors": {
        "zh-TW": "配對排放係數與熱值",
        "en": "Matching emission factors and heating values",
    },
    "analysis.stage.calculate": {
        "zh-TW": "正在計算排放量",
        "en": "Calculating emissions",
    },
    "analysis.stage.issues": {
        "zh-TW": "整理規則與待處理問題",
        "en": "Organizing rules and unresolved issues",
    },
    "analysis.running_title": {
        "zh-TW": "正在分析你的資料",
        "en": "Analyzing your data",
    },
    "analysis.processing_count": {
        "zh-TW": "正在處理 {count} 筆活動資料",
        "en": "Processing {count} activity records",
    },
    "analysis.failed_reason": {"zh-TW": "原因：", "en": "Reason:"},
    "analysis.failed_next": {"zh-TW": "下一步：", "en": "Next step:"},
    "analysis.failed_next_body": {
        "zh-TW": "請回到排放資料與計算，確認欄位與活動類型後再分析。",
        "en": (
            "Return to Emissions Data & Calculations, confirm fields and "
            "activity types, then analyze again."
        ),
    },
    "analysis.return_to_data": {
        "zh-TW": "返回修改資料",
        "en": "Return to edit data",
    },
    "analysis.percent_label": {
        "zh-TW": "{percent}%",
        "en": "{percent}%",
    },
    "analysis.stage.classify": {
        "zh-TW": "正在建立分類與準則檢查…",
        "en": "Building classifications…",
    },
    "analysis.complete_banner": {
        "zh-TW": "分析完成 ✓",
        "en": "Analysis complete ✓",
    },
    "error.analysis_incomplete": {
        "zh-TW": "分析未完成",
        "en": "Analysis incomplete",
    },
    "error.analysis_failed_safe": {
        "zh-TW": "分析未完成。請檢查上傳資料後再試。",
        "en": "Analysis did not finish. Review your upload and try again.",
    },
    "error.analysis_missing_fields": {
        "zh-TW": "必要欄位缺失或尚未完成資料驗證。",
        "en": "Required fields are missing or data is not yet validated.",
    },
    "error.analysis_unit": {
        "zh-TW": "單位無法辨識或資料編碼有問題。",
        "en": "A unit could not be recognized or the file encoding is invalid.",
    },
    "error.analysis_file_format": {
        "zh-TW": "檔案格式錯誤或不受支援。",
        "en": "The file format is invalid or unsupported.",
    },
    "onboard.welcome_title": {
        "zh-TW": "歡迎使用 Carbon Evidence Ledger",
        "en": "Welcome to Carbon Evidence Ledger",
    },
    "onboard.welcome_body": {
        "zh-TW": (
            "先完成公司設定，我們會依已驗證法規整理"
            "公司可能需要準備的 IFRS、溫室氣體與碳費要求。"
        ),
        "en": (
            "Start with company setup. We will organize IFRS, GHG, and "
            "carbon-fee requirements based on verified regulations."
        ),
    },
    "onboard.step1": {"zh-TW": "公司設定", "en": "Company setup"},
    "onboard.step2": {"zh-TW": "適用性判定", "en": "Applicability"},
    "onboard.step3": {"zh-TW": "上傳資料", "en": "Upload data"},
    "onboard.step4": {"zh-TW": "分析與檢查", "en": "Analyze & review"},
    "onboard.step5": {"zh-TW": "準備報告", "en": "Prepare reports"},
    "onboard.cta_setup": {
        "zh-TW": "開始公司設定",
        "en": "Start company setup",
    },
    "onboard.cta_demo": {
        "zh-TW": "使用示範資料",
        "en": "Try demo data",
    },
    "onboard.demo_note": {
        "zh-TW": "示範資料僅供體驗，不會與真實公司資料混淆。",
        "en": "Demo data is for exploration only and is clearly labeled.",
    },
    "empty.no_analysis_title": {
        "zh-TW": "完成分析後即可查看結果",
        "en": "Results appear after analysis",
    },
    "empty.no_analysis_body": {
        "zh-TW": "完成分析後即可建立報告。",
        "en": "Reports become available after analysis.",
    },
    "empty.no_upload_title": {
        "zh-TW": "尚未上傳公司資料",
        "en": "No company data uploaded yet",
    },
    "empty.no_upload_body": {
        "zh-TW": "請先上傳 CSV 或 Excel，再完成欄位對應與驗證。",
        "en": "Upload a CSV or Excel file, then map columns and validate.",
    },
    "intake.nav.back": {"zh-TW": "← 上一步", "en": "← Back"},
    "intake.nav.next": {"zh-TW": "下一步 →", "en": "Next →"},
    "intake.nav.edit": {"zh-TW": "修改", "en": "Edit"},
    "intake.nav.replace_file": {"zh-TW": "更換檔案", "en": "Replace file"},
    "intake.uploaded_summary": {
        "zh-TW": "已上傳",
        "en": "Uploaded",
    },
    "intake.step5": {"zh-TW": "開始分析", "en": "Start analysis"},
    "intake.step.results": {
        "zh-TW": "04 查看排放結果",
        "en": "04 View emissions results",
    },
    "intake.site_unknown_help": {
        "zh-TW": (
            "若檔案沒有據點欄位，請填寫廠場或營運據點名稱；"
            "留空將標示為待確認。"
        ),
        "en": (
            "If the file has no location column, enter a site / operating "
            "location name. Leave blank to mark as needing confirmation."
        ),
    },
    "intake.period_required": {
        "zh-TW": "請指定報導期間（系統不會自動填入示範年份）。",
        "en": "Specify the reporting period (demo years are not auto-filled).",
    },
    "coverage.calc_status": {
        "zh-TW": "資料計算狀態",
        "en": "Calculation coverage",
    },
    "coverage.calc_ratio": {
        "zh-TW": "{done} / {total} 已完成",
        "en": "{done} / {total} complete",
    },
    "coverage.calc_needs": {
        "zh-TW": "{count} 筆需要補充資料或排放係數",
        "en": "{count} records need data or factors",
    },
    "analysis.complete_detail": {
        "zh-TW": "{total} 筆活動資料已完成檢查。{done} 筆目前可計算。",
        "en": "{total} activity records checked. {done} are currently calculable.",
    },
    "analysis.toast": {
        "zh-TW": "分析完成：{done}/{total} 筆可計算",
        "en": "Analysis complete: {done}/{total} calculable",
    },
    "error.analysis_failed": {
        "zh-TW": "分析暫時無法完成。",
        "en": "Analysis could not be completed.",
    },
    "error.export_failed": {
        "zh-TW": "下載檔案建立失敗。",
        "en": "Export bundle could not be generated.",
    },
    # Common
    "common.demo_badge": {"zh-TW": "示範資料", "en": "Demo data"},
    "common.uploaded_badge": {
        "zh-TW": "你上傳的公司資料",
        "en": "Your uploaded company data",
    },
    "common.partial_result": {"zh-TW": "部分結果", "en": "Partial result"},
    "common.not_run": {"zh-TW": "尚未執行", "en": "Not run"},
    "common.how_to_use": {"zh-TW": "這頁怎麼用？", "en": "How to use this page"},
    "common.view_missing": {
        "zh-TW": "查看資料 →",
        "en": "View data →",
    },
    "common.high_priority": {"zh-TW": "高優先", "en": "High priority"},
    "common.critical": {"zh-TW": "重大", "en": "Critical"},
    "common.glossary": {"zh-TW": "名詞小幫手 →", "en": "Glossary →"},
    "common.advanced": {"zh-TW": "進階技術資訊", "en": "Advanced technical details"},
    "common.view_details": {"zh-TW": "查看詳細資料", "en": "View details"},
    # Status labels
    "status.calculated": {"zh-TW": "已完成計算", "en": "Calculated"},
    "status.blocked_missing_conversion": {
        "zh-TW": "無法計算－缺少轉換資料",
        "en": "Blocked — missing conversion",
    },
    "status.blocked_natural_gas_type_required": {
        "zh-TW": "請確認天然氣類型（NG1 或 NG2），才能套用正確熱值。",
        "en": (
            "Confirm natural-gas type (NG1 or NG2) before applying "
            "the heating value."
        ),
    },
    "status.no_factor_configured": {
        "zh-TW": "缺少排放係數",
        "en": "Emission factor needed",
    },
    "status.no_matching_factor": {
        "zh-TW": "無符合係數",
        "en": "No matching factor",
    },
    "status.blocked_missing_supplier_or_product": {
        "zh-TW": "尚缺供應商名稱",
        "en": "Supplier name required",
    },
    "status.blocked_missing_factor_year": {
        "zh-TW": "尚缺係數年份",
        "en": "Factor year required",
    },
    "status.blocked_missing_product_type": {
        "zh-TW": "尚缺鋼材產品類型",
        "en": "Steel product type required",
    },
    "status.blocked_missing_evidence": {
        "zh-TW": "尚缺係數來源或證據",
        "en": "Factor source or evidence required",
    },
    "status.blocked_missing_source": {
        "zh-TW": "尚缺係數來源",
        "en": "Factor source required",
    },
    "status.blocked_incompatible_factor_boundary": {
        "zh-TW": "係數邊界必須為搖籃到大門",
        "en": "Factor boundary must be cradle-to-gate",
    },
    "status.blocked_transport_not_category_1": {
        "zh-TW": "獨立運輸紀錄不屬於 Category 1",
        "en": "A standalone transport record is not Category 1",
    },
    "status.blocked_factor_inclusion_unconfirmed": {
        "zh-TW": "尚未確認係數是否包含入廠運輸",
        "en": "Factor inbound-transport inclusion is not confirmed",
    },
    "status.blocked_transport_control_unconfirmed": {
        "zh-TW": "尚未確認入廠運輸控制方式",
        "en": "Inbound-transport control is not confirmed",
    },
    "status.blocked_tier1_inbound_transport_requires_category4_split": {
        "zh-TW": "需先拆分 Scope 3 Category 4 運輸",
        "en": "Category 4 transport split required",
    },
    "status.blocked_company_controlled_transport_requires_scope1_or2_split": {
        "zh-TW": "需先拆分 Scope 1 或 Scope 2 運輸",
        "en": "Scope 1 or 2 transport split required",
    },
    "status.blocked_ambiguous_factor": {
        "zh-TW": "符合的平均係數超過一筆",
        "en": "More than one matching average factor",
    },
    "status.blocked_unsupported_calculation_method": {
        "zh-TW": "計算方法目前僅支援供應商特定或平均數據",
        "en": "Only supplier-specific or average-data methods are supported",
    },
    "status.blocked_missing_factor_geography": {
        "zh-TW": "尚缺係數地理範圍",
        "en": "Factor geography required",
    },
    "status.purchased_steel_category1": {
        "zh-TW": "採購鋼材 Category 1",
        "en": "Purchased steel Category 1",
    },
    "status.not_emissions_activity": {
        "zh-TW": "輔助資料",
        "en": "Supporting data",
    },
    "status.unsupported_activity_type": {
        "zh-TW": "尚不支援的活動類型",
        "en": "Unsupported activity",
    },
    "status.invalid_normalized_input": {
        "zh-TW": "標準化輸入無效",
        "en": "Invalid normalized input",
    },
    "status.factor_match_inconsistent": {
        "zh-TW": "係數比對不一致",
        "en": "Factor match inconsistent",
    },
    "status.blocked_ambiguous_conversion": {
        "zh-TW": "無法計算－熱值資料衝突",
        "en": "Blocked — conflicting heating value",
    },
    "status.blocked_incomplete_gas_factors": {
        "zh-TW": "無法計算－排放係數資料不完整",
        "en": "Blocked — incomplete gas factors",
    },
    "status.blocked_conflicting_factor_group": {
        "zh-TW": "無法計算－係數版本不一致",
        "en": "Blocked — conflicting factor group",
    },
    "status.blocked_missing_gwp": {
        "zh-TW": "無法計算－GWP 版本無法確認",
        "en": "Blocked — GWP not confirmed",
    },
    "status.blocked_unknown_refrigerant": {
        "zh-TW": "無法計算－冷媒種類無法識別",
        "en": "Blocked — unknown refrigerant",
    },
    "status.blocked_missing_refill_quantity": {
        "zh-TW": "無法計算－補充量尚未確認",
        "en": "Blocked — refill not confirmed",
    },
    "status.blocked_invalid_reporting_period": {
        "zh-TW": "無法計算－報導年度無法唯一判定",
        "en": "Blocked — reporting year is not unique",
    },
    "status.ready": {"zh-TW": "資料完整", "en": "Ready"},
    "status.partial_evidence": {
        "zh-TW": "部分資料可用",
        "en": "Partial evidence",
    },
    "status.data_gap": {"zh-TW": "資料不足", "en": "Data gap"},
    "status.supporting_only": {"zh-TW": "僅作輔助", "en": "Supporting only"},
    "status.excluded": {"zh-TW": "不納入", "en": "Excluded"},
    "status.needs_review": {"zh-TW": "需要確認", "en": "Needs review"},
    "status.outside_boundary": {
        "zh-TW": "組織邊界外，不納入",
        "en": "Outside the organizational boundary",
    },
    "status.not_applicable": {"zh-TW": "不適用", "en": "Not applicable"},
    "status.mapped": {"zh-TW": "已對應", "en": "Mapped"},
    "status.unknown": {"zh-TW": "未知", "en": "Unknown"},
    "status.no_open_issue": {
        "zh-TW": "無待處理問題",
        "en": "No open issue",
    },
    "status.attention_blocked": {
        "zh-TW": "缺少熱值轉換資料",
        "en": "Missing heating-value conversion",
    },
    "status.attention_factor": {
        "zh-TW": "缺少適用排放係數",
        "en": "Missing applicable emission factor",
    },
    # Activity names
    "activity.grid_electricity": {
        "zh-TW": "外購電力",
        "en": "Purchased electricity",
    },
    "activity.natural_gas": {
        "zh-TW": "天然氣",
        "en": "Natural gas",
    },
    "activity.diesel": {
        "zh-TW": "柴油",
        "en": "Diesel",
    },
    "activity.refrigerant_refill": {
        "zh-TW": "冷媒實際補充",
        "en": "Actual refrigerant refill",
    },
    "activity.purchased_steel": {
        "zh-TW": "採購鋼材",
        "en": "Purchased steel wire rod",
    },
    "activity.finished_goods_output": {
        "zh-TW": "成品產出",
        "en": "Finished-goods output",
    },
    "activity.third_party_transport": {
        "zh-TW": "第三方運輸",
        "en": "Third-party transport",
    },
    "activity.scrap_output": {"zh-TW": "廢料產出", "en": "Scrap output"},
    "activity.other": {"zh-TW": "其他", "en": "Other"},
    "activity.unknown": {"zh-TW": "未知", "en": "Unknown"},
    # GHG / CBAM roles
    "ghg.scope_1": {"zh-TW": "Scope 1", "en": "Scope 1"},
    "ghg.scope_2": {"zh-TW": "Scope 2", "en": "Scope 2"},
    "ghg.scope_3": {"zh-TW": "Scope 3", "en": "Scope 3"},
    "ghg.scope_3_cat1": {
        "zh-TW": "Scope 3 Category 1",
        "en": "Scope 3 Category 1",
    },
    "cbam.role.supporting_energy": {
        "zh-TW": "佐證用能源資料／不納入直接排放",
        "en": "Supporting evidence / excluded from direct emissions",
    },
    "cbam.role.direct_candidate": {
        "zh-TW": "直接排放活動候選",
        "en": "Direct-emissions activity candidate",
    },
    "cbam.role.outside": {
        "zh-TW": "製程邊界外",
        "en": "Outside process boundary",
    },
    "cbam.role.precursor": {
        "zh-TW": "可能的前驅物資料缺口",
        "en": "Possible precursor data gap",
    },
    "cbam.role.product_qty": {
        "zh-TW": "產品數量證據",
        "en": "Product quantity evidence",
    },
    # Compliance Overview (formerly analysis results)
    "dash.page_title": {"zh-TW": "合規總覽", "en": "Compliance Overview"},
    "dash.page_subtitle": {
        "zh-TW": "先處理優先事項與缺少的資料，再查看排放與證據細節。",
        "en": (
            "See what needs attention, what information is missing, "
            "and then review emissions and evidence details."
        ),
    },
    "dash.section_attention": {
        "zh-TW": "目前需要注意",
        "en": "What requires attention",
    },
    "dash.section_attention_help": {
        "zh-TW": "優先處理會阻擋計算或揭露準備的資料缺口。",
        "en": "Prioritize gaps that block calculation or disclosure prep.",
    },
    "dash.section_missing": {
        "zh-TW": "缺少的資料",
        "en": "Missing information",
    },
    "dash.section_review": {
        "zh-TW": "需要複核",
        "en": "Needs review",
    },
    "dash.section_emissions_summary": {
        "zh-TW": "排放資料摘要",
        "en": "Emissions summary",
    },
    "dash.section_emissions_summary_help": {
        "zh-TW": "既有計算結果摘要，僅供佐證參考，不是合規分數。",
        "en": (
            "Summary of existing calculation results for evidence review — "
            "not a compliance score."
        ),
    },
    "dash.cta.view_ifrs": {
        "zh-TW": "查看 IFRS S1/S2",
        "en": "View IFRS S1/S2",
    },
    "dash.cta.view_taiwan": {
        "zh-TW": "查看台灣法規要求",
        "en": "View Taiwan requirements",
    },
    "dash.cta.view_evidence": {
        "zh-TW": "查看佐證文件與稽核紀錄",
        "en": "View supporting documents & audit trail",
    },
    "dash.no_fake_score_note": {
        "zh-TW": "",
        "en": "",
    },
    "dash.cta.view_calc_basis": {
        "zh-TW": "查看計算依據",
        "en": "View calculation basis",
    },
    "dash.complete_title": {"zh-TW": "分析完成 ✓", "en": "Analysis complete ✓"},
    "dash.source_section": {"zh-TW": "資料來源", "en": "Data source"},
    "dash.period_section": {"zh-TW": "資料期間", "en": "Data period"},
    "dash.activities_kpi": {"zh-TW": "活動資料", "en": "Activity records"},
    "dash.calculated_kpi": {"zh-TW": "已成功計算", "en": "Successfully calculated"},
    "dash.needs_work_kpi": {"zh-TW": "仍需處理", "en": "Still needs attention"},
    "dash.kpi.scope1": {"zh-TW": "Scope 1", "en": "Scope 1"},
    "dash.kpi.scope2": {"zh-TW": "Scope 2", "en": "Scope 2"},
    "dash.kpi.scope3": {"zh-TW": "Scope 3", "en": "Scope 3"},
    "dash.kpi.scope1_plain": {"zh-TW": "直接排放", "en": "Direct emissions"},
    "dash.kpi.scope2_plain": {"zh-TW": "外購能源", "en": "Purchased energy"},
    "dash.kpi.scope3_plain": {
        "zh-TW": "其他價值鏈排放",
        "en": "Other value-chain emissions",
    },
    "dash.scope3_unsupported": {
        "zh-TW": "尚未納入總排放量",
        "en": "Not included in the current total",
    },
    "dash.scope_pending": {
        "zh-TW": "尚未完成計算",
        "en": "Not yet calculated",
    },
    "dash.emissions_coverage": {
        "zh-TW": "目前已計算 {done} / {total} 筆活動資料",
        "en": "Currently calculated {done} / {total} activity records",
    },
    "dash.partial_banner": {
        "zh-TW": "尚有 {count} 筆活動未納入目前結果",
        "en": "{count} activities are not yet included in the current result",
    },
    "dash.section_scope": {
        "zh-TW": "範疇分解",
        "en": "Scope breakdown",
    },
    "dash.partial_excluded": {
        "zh-TW": "{count} 筆活動目前尚未納入計算結果。",
        "en": "{count} activities are not yet included in calculated results.",
    },
    "act.basis.quantity": {"zh-TW": "原始用量", "en": "Original quantity"},
    "act.basis.ng_type": {"zh-TW": "天然氣類型", "en": "Natural-gas type"},
    "act.basis.heating_value": {
        "zh-TW": "年度低位熱值",
        "en": "Annual lower heating value",
    },
    "act.basis.energy": {"zh-TW": "換算後能源量", "en": "Converted energy"},
    "act.basis.gas_factors": {
        "zh-TW": "CO2 / CH4 / N2O 排放係數",
        "en": "CO2 / CH4 / N2O emission factors",
    },
    "act.basis.gwp": {"zh-TW": "GWP", "en": "GWP"},
    "act.basis.result": {"zh-TW": "計算結果", "en": "Calculation result"},
    "act.basis.source": {"zh-TW": "官方來源", "en": "Official source"},
    "act.basis.diesel_use": {"zh-TW": "柴油用途", "en": "Diesel use"},
    "act.basis.refrigerant_code": {
        "zh-TW": "冷媒種類",
        "en": "Refrigerant type",
    },
    "act.basis.refill_quantity": {
        "zh-TW": "實際補充量",
        "en": "Actual refill quantity",
    },
    "dash.kpi.emissions": {
        "zh-TW": "目前已計算排放量",
        "en": "Currently calculated emissions",
    },
    "dash.kpi.inventory": {
        "zh-TW": "目前已納入公司盤查排放量",
        "en": "Currently included company inventory emissions",
    },
    "dash.kpi.completion": {"zh-TW": "計算完成", "en": "Calculation complete"},
    "dash.kpi.unresolved": {"zh-TW": "仍需處理", "en": "Still unresolved"},
    "dash.kpi.unresolved_hint": {
        "zh-TW": "尚未完成計算的活動",
        "en": "Activities still blocked",
    },
    "dash.kpi.source": {"zh-TW": "資料來源", "en": "Data sources"},
    "dash.kpi.source_hint": {
        "zh-TW": "來源文件 · 官方係數已連結",
        "en": "Source documents · official factors linked",
    },
    "dash.section_emissions": {"zh-TW": "排放結果", "en": "Emissions results"},
    "dash.section_trend": {"zh-TW": "排放趨勢", "en": "Emissions trend"},
    "dash.section_trend_help": {
        "zh-TW": "依活動期間彙總目前已計算的排放量。",
        "en": "Monthly totals from currently calculated activities.",
    },
    "dash.section_sources": {"zh-TW": "排放來源", "en": "Emissions sources"},
    "dash.section_sources_help": {
        "zh-TW": "結果只包含目前已完成計算的活動。",
        "en": "Results include only activities that have been calculated.",
    },
    "dash.section_completeness": {"zh-TW": "本次資料狀態", "en": "Dataset status"},
    "dash.section_completeness_help": {
        "zh-TW": "依活動檢視目前已能計算與仍缺資料的分布（輔助圖表）。",
        "en": (
            "Supporting chart of which activities can be calculated "
            "and which still lack data."
        ),
    },
    "dash.completeness_note": {
        "zh-TW": "本次資料狀態用來提醒還有哪些筆數尚未納入結果。",
        "en": "This status shows which records are not yet included in the result.",
    },
    "dash.section_priority": {"zh-TW": "優先處理", "en": "Priority actions"},
    "dash.section_priority_help": {
        "zh-TW": "先處理這些缺口，才能擴大可計算範圍。",
        "en": "Resolve these gaps to expand what can be calculated.",
    },
    "dash.priority.missing_conversion": {
        "zh-TW": "缺少熱值轉換資料",
        "en": "Missing heating-value conversion data",
    },
    "dash.priority.missing_factor": {
        "zh-TW": "缺少適用排放係數",
        "en": "Missing applicable emission factor",
    },
    "dash.priority.affected": {
        "zh-TW": "影響 {count} 筆活動",
        "en": "Affects {count} activities",
    },
    "dash.section_calc_table": {"zh-TW": "計算明細", "en": "Calculation table"},
    "dash.section_calc_table_help": {
        "zh-TW": "點選一列可查看計算驗算。",
        "en": "Select a row to open the calculation check.",
    },
    "dash.col.factor": {"zh-TW": "係數", "en": "Factor"},
    "dash.col.factor_year": {"zh-TW": "係數年度", "en": "Factor year"},
    "dash.col.emissions": {"zh-TW": "排放量", "en": "Emissions"},
    "dash.cta.view_issues": {
        "zh-TW": "查看待處理問題",
        "en": "View open issues",
    },
    "dash.cta.how_to_fix": {"zh-TW": "查看如何處理", "en": "See how to fix"},
    "dash.cta.view_frameworks": {"zh-TW": "查看準則分析", "en": "Open frameworks"},
    "dash.cta.update_data": {"zh-TW": "更新資料", "en": "Update data"},
    "dash.cta.edit_emissions_data": {
        "zh-TW": "返回排放資料與計算修改",
        "en": "Return to edit emissions data and calculations",
    },
    "dash.frameworks_card": {
        "zh-TW": "準則分析 · {count} 個分析模組可查看",
        "en": "Framework analysis · {count} modules available",
    },
    "dash.trace_evidence": {
        "zh-TW": "查看完整證據鏈",
        "en": "View full evidence chain",
    },
    "dash.section_uncalculable": {
        "zh-TW": "哪些資料還不能算",
        "en": "What still cannot be calculated",
    },
    "dash.section_activity_status": {
        "zh-TW": "各活動的計算狀態",
        "en": "Calculation status by activity",
    },
    "dash.section_trace": {"zh-TW": "計算驗算", "en": "Calculation check"},
    "dash.section_frameworks": {"zh-TW": "準則分析", "en": "Framework analysis"},
    "dash.section_advanced": {
        "zh-TW": "進階技術資料",
        "en": "Advanced technical details",
    },
    "dash.uncalculable_title": {
        "zh-TW": "目前無法計算",
        "en": "Currently not calculable",
    },
    "dash.uncalculable_missing": {"zh-TW": "缺少：", "en": "Missing:"},
    "dash.uncalculable_next": {"zh-TW": "下一步：", "en": "Next step:"},
    "dash.period_unknown": {"zh-TW": "期間未標示", "en": "Period not labeled"},
    "dash.current_analysis": {"zh-TW": "目前分析", "en": "Current analysis"},
    "dash.file_label": {"zh-TW": "檔案：", "en": "File:"},
    "dash.legal_year_label": {
        "zh-TW": "法規適用年度：{year}",
        "en": "Legal applicability year: {year}",
    },
    "dash.period_label": {
        "zh-TW": "資料期間：",
        "en": "Data period: ",
    },
    "ghg.rationale.refrigerant_third_party": {
        "zh-TW": (
            "第三方所有的冷媒設備不會自動列入 Scope 1；系統也不會自行推定為 "
            "Scope 3，請確認實際營運控制與盤查邊界。"
        ),
        "en": (
            "Third-party refrigerant equipment is not automatically mapped "
            "to Scope 1; Scope 3 is not guessed."
        ),
    },
    "dash.activity_count_label": {
        "zh-TW": "{count} 筆活動資料",
        "en": "{count} activity records",
    },
    "chart.trend.empty": {
        "zh-TW": "目前尚無可繪製的月度排放趨勢。",
        "en": "No monthly emissions trend is available yet.",
    },
    "chart.source.not_calculated": {
        "zh-TW": "尚未計算",
        "en": "Not yet calculated",
    },
    "dash.tutorial_hint": {
        "zh-TW": "第一次使用？查看 3 分鐘操作教學 →",
        "en": "First time here? Open the 3-minute tutorial →",
    },
    "dash.hero_kicker": {
        "zh-TW": "Carbon Evidence Ledger",
        "en": "Carbon Evidence Ledger",
    },
    "dash.hero_title": {
        "zh-TW": "讓碳資料變得\n可計算、可追溯、可行動",
        "en": "Make carbon data\ncalculable, traceable, and actionable",
    },
    "dash.hero_support": {
        "zh-TW": (
            "從原始活動資料到 Scope 1 / 2 / 3 與 IFRS S1/S2 準備，"
            "清楚知道目前能算什麼、缺什麼，以及下一步該做什麼。"
        ),
        "en": (
            "From source activity data to Scope 1 / 2 / 3 and IFRS S1/S2 prep — "
            "see what can be calculated, what is missing, and what to do next."
        ),
    },
    "dash.hero_cta": {"zh-TW": "開始分析", "en": "Start analysis"},
    "dash.hero_help_link": {
        "zh-TW": "不知道怎麼開始？請使用左側的「開始分析」。",
        "en": "Not sure how to start? Use Start analysis in the sidebar.",
    },
    "dash.hero_help_cta": {
        "zh-TW": "查看操作教學",
        "en": "Open tutorial",
    },
    "dash.flow_evidence": {"zh-TW": "來源證據", "en": "Source evidence"},
    "dash.flow_activity": {"zh-TW": "活動資料", "en": "Activity data"},
    "dash.flow_calc": {"zh-TW": "排放計算", "en": "Emissions calculation"},
    "dash.flow_framework": {"zh-TW": "準則分析", "en": "Framework analysis"},
    "dash.flow_frameworks_short": {
        "zh-TW": "準則對應",
        "en": "Frameworks",
    },
    "dash.flow_action": {"zh-TW": "下一步行動", "en": "Next action"},
    "dash.how_title": {"zh-TW": "如何使用", "en": "How it works"},
    "dash.how_1": {"zh-TW": "選擇分析項目", "en": "Choose modules"},
    "dash.how_2": {"zh-TW": "開始分析", "en": "Run analysis"},
    "dash.how_3": {"zh-TW": "處理缺少資料", "en": "Resolve data gaps"},
    "dash.how_4": {"zh-TW": "查看準則結果", "en": "Review frameworks"},
    "dash.how_5": {"zh-TW": "下載成果", "en": "Export results"},
    "dash.kpi_activities": {"zh-TW": "活動資料", "en": "Activities"},
    "dash.kpi_calculated": {"zh-TW": "已完成計算", "en": "Calculated"},
    "dash.kpi_issues": {"zh-TW": "待處理問題", "en": "Open issues"},
    "dash.kpi_docs": {"zh-TW": "來源文件", "en": "Source documents"},
    "dash.emissions_title": {
        "zh-TW": "目前已能計算的排放量",
        "en": "Currently calculable emissions",
    },
    "dash.emissions_label": {
        "zh-TW": "目前已能計算",
        "en": "Currently calculable",
    },
    "dash.emissions_ratio": {
        "zh-TW": "{done} / {total} 筆活動已完成計算",
        "en": "{done} / {total} activities calculated",
    },
    "dash.emissions_ratio_short": {
        "zh-TW": "{done} / {total} 筆活動",
        "en": "{done} / {total} activities",
    },
    "dash.emissions_notice": {
        "zh-TW": (
            "這不是公司的總排放量。"
            "缺少資料的活動不會被當成 0。"
        ),
        "en": (
            "This is not total company emissions. "
            "Missing activities are not treated as zero."
        ),
    },
    "dash.attention_title": {
        "zh-TW": "你現在需要處理",
        "en": "Needs your attention",
    },
    "dash.attention_sub": {
        "zh-TW": "以下資料缺口會阻止完整計算。",
        "en": "These data gaps currently prevent complete calculation.",
    },
    "dash.attention_empty": {
        "zh-TW": "目前沒有待處理的核心資料問題。",
        "en": "No open core data-quality issues right now.",
    },
    "dash.attention_gas_action": {
        "zh-TW": "取得適用的低位熱值後，即可繼續排放計算。",
        "en": "Register an applicable lower heating value to continue calculation.",
    },
    "dash.attention_diesel_action": {
        "zh-TW": "取得適用的低位熱值後，即可繼續排放計算。",
        "en": "Register an applicable lower heating value to continue calculation.",
    },
    "dash.attention_steel_action": {
        "zh-TW": "選定並登錄適用排放係數後，即可繼續計算。",
        "en": "Select and document an applicable emission factor to continue.",
    },
    "dash.activities_title": {
        "zh-TW": "所有活動資料",
        "en": "All activity data",
    },
    "dash.activities_sub": {
        "zh-TW": "快速查看每筆資料目前的計算與準則狀態。",
        "en": "Quickly review calculation and framework status for each record.",
    },
    "dash.activities_explore": {
        "zh-TW": "查看完整活動資料 →",
        "en": "Open full activity explorer →",
    },
    "dash.col.activity": {"zh-TW": "活動", "en": "Activity"},
    "dash.col.amount": {"zh-TW": "數量", "en": "Amount"},
    "dash.col.calc": {"zh-TW": "計算", "en": "Calculation"},
    "dash.col.ghg": {"zh-TW": "GHG Protocol", "en": "GHG Protocol"},
    "dash.col.cbam": {"zh-TW": "EU CBAM", "en": "EU CBAM"},
    "dash.col.ifrs": {"zh-TW": "IFRS S2", "en": "IFRS S2"},
    "dash.col.qa": {"zh-TW": "資料檢查", "en": "Data check"},
    "dash.framework_title": {
        "zh-TW": "準則涵蓋範圍",
        "en": "Framework coverage",
    },
    "dash.enabled": {"zh-TW": "已啟用", "en": "Enabled"},
    "dash.disabled": {"zh-TW": "未啟用", "en": "Not enabled"},
    "dash.rows": {"zh-TW": "{n} 筆評估", "en": "{n} evaluation rows"},
    # Activity page
    "act.title": {"zh-TW": "活動資料", "en": "Activity Data"},
    "act.subtitle": {
        "zh-TW": "從來源證據一路追蹤到排放計算與準則用途。",
        "en": "Trace each activity from evidence to calculation and framework use.",
    },
    "act.help": {
        "zh-TW": (
            "1. 先選一筆活動。\n"
            "2. 查看它目前能不能計算。\n"
            "3. 如果不能算，系統會告訴你缺什麼。\n"
            "4. 再查看來源證據及各準則如何使用它。"
        ),
        "en": (
            "1. Select an activity.\n"
            "2. See whether it can be calculated.\n"
            "3. If not, the app explains what is missing.\n"
            "4. Then review evidence and framework use."
        ),
    },
    "act.select_hint": {
        "zh-TW": "請先點選一筆活動，下方會顯示完整資料。",
        "en": "Select an activity row to see full details below.",
    },
    "act.filter_search": {"zh-TW": "搜尋", "en": "Search"},
    "act.filter_type": {"zh-TW": "活動類型", "en": "Activity type"},
    "act.filter_status": {"zh-TW": "計算狀態", "en": "Calculation status"},
    "act.filter_attention": {"zh-TW": "需要處理", "en": "Attention required"},
    "act.filter_all": {"zh-TW": "全部", "en": "All"},
    "act.filter_yes": {"zh-TW": "是", "en": "Yes"},
    "act.filter_no": {"zh-TW": "否", "en": "No"},
    "act.tab.summary": {"zh-TW": "總覽", "en": "Summary"},
    "act.tab.calc": {"zh-TW": "計算", "en": "Calculation"},
    "act.tab.evidence": {"zh-TW": "來源證據", "en": "Evidence"},
    "act.tab.frameworks": {"zh-TW": "準則分析", "en": "Frameworks"},
    "act.tab.tech": {"zh-TW": "進階技術資料", "en": "Technical details"},
    "act.can_calculate": {"zh-TW": "可以計算", "en": "Can calculate"},
    "act.cannot_calculate": {"zh-TW": "目前無法計算", "en": "Cannot calculate yet"},
    "act.why_blocked": {
        "zh-TW": "為什麼現在不能算？",
        "en": "Why this cannot be calculated yet",
    },
    "act.what_next": {
        "zh-TW": "下一步需要什麼？",
        "en": "What is needed next",
    },
    "act.no_zero": {
        "zh-TW": "排放量：未回報（缺少資料不會顯示為 0）",
        "en": "Emissions: not reported (gaps are not shown as zero)",
    },
    # Issues
    "iss.title": {"zh-TW": "待處理問題", "en": "Issues & Actions"},
    "iss.subtitle": {
        "zh-TW": "系統不會猜測缺少的資料；這裡告訴你下一步該補什麼。",
        "en": (
            "The system does not guess missing data; this list tells you "
            "what to collect next."
        ),
    },
    "iss.help": {
        "zh-TW": "這裡就是你的待辦清單。先處理高優先問題，再重新執行分析。",
        "en": (
            "This is your task list. Resolve high-priority issues, "
            "then run analysis again."
        ),
    },
    "iss.metric_open": {"zh-TW": "待處理", "en": "Open issues"},
    "iss.metric_critical": {"zh-TW": "重大", "en": "Critical"},
    "iss.metric_high": {"zh-TW": "高優先", "en": "High priority"},
    "iss.metric_affected": {"zh-TW": "受影響活動", "en": "Affected activities"},
    "iss.todo_title": {"zh-TW": "待辦清單", "en": "To-do list"},
    "iss.todo_help": {
        "zh-TW": "每個問題都對應下一步行動，不會把缺資料當成 0。",
        "en": (
            "Each issue maps to a next action; "
            "missing data is never treated as zero."
        ),
    },
    "iss.gap_title": {"zh-TW": "缺少資料類型", "en": "Missing data types"},
    "iss.filter_severity": {"zh-TW": "優先程度", "en": "Severity"},
    "iss.filter_type": {"zh-TW": "問題類型", "en": "Issue type"},
    "iss.filter_activity": {"zh-TW": "活動", "en": "Activity"},
    "iss.col.priority": {"zh-TW": "優先程度", "en": "Priority"},
    "iss.col.activity": {"zh-TW": "活動", "en": "Activity"},
    "iss.col.issue": {"zh-TW": "問題", "en": "Issue"},
    "iss.col.why": {"zh-TW": "原因", "en": "Why it matters"},
    "iss.col.next": {"zh-TW": "下一步", "en": "Recommended action"},
    "iss.detail.problem": {"zh-TW": "問題", "en": "Problem"},
    "iss.detail.why": {"zh-TW": "為什麼重要", "en": "Why it matters"},
    "iss.detail.next": {"zh-TW": "下一步怎麼做", "en": "What to do next"},
    "iss.detail.allowed": {
        "zh-TW": "目前仍可以怎麼使用",
        "en": "Allowed use",
    },
    "iss.detail.prohibited": {
        "zh-TW": "目前不可怎麼使用",
        "en": "Do not use for",
    },
    "iss.detail.related": {"zh-TW": "相關資料", "en": "Related evidence"},
    "iss.empty": {
        "zh-TW": "目前沒有待處理的核心資料問題。",
        "en": "No open core data-quality issues.",
    },
    # Frameworks
    "fw.title": {"zh-TW": "IFRS S1/S2", "en": "IFRS S1/S2"},
    "fw.ifrs_what_title": {
        "zh-TW": "? IFRS S1/S2 是什麼？",
        "en": "? What are IFRS S1/S2?",
    },
    "fw.subtitle": {
        "zh-TW": "先了解要準備什麼，再依治理、策略、風險管理、指標與目標整理。",
        "en": (
            "First understand what to prepare, then organize by governance, "
            "strategy, risk management, and metrics & targets."
        ),
    },
    "fw.help": {
        "zh-TW": (
            "IFRS S1 提供一般揭露架構；IFRS S2 提供氣候相關要求。"
            "本頁不做合規判定。"
        ),
        "en": (
            "IFRS S1 provides the general disclosure architecture; "
            "IFRS S2 adds climate requirements. "
            "This page does not determine compliance."
        ),
    },
    "fw.pillar.governance": {"zh-TW": "治理", "en": "Governance"},
    "fw.pillar.strategy": {"zh-TW": "策略", "en": "Strategy"},
    "fw.pillar.risk": {"zh-TW": "風險管理", "en": "Risk Management"},
    "fw.pillar.metrics": {"zh-TW": "指標與目標", "en": "Metrics & Targets"},
    "fw.pillar.shell_status": {
        "zh-TW": "規則集尚未實作",
        "en": "Rule set not yet implemented",
    },
    "fw.pillar.shell_help": {
        "zh-TW": (
            "此區塊將於後續階段接上風險／機會紀錄與規則登錄。"
            "目前不臆測適用或合規結論。"
        ),
        "en": (
            "This pillar will connect to risk/opportunity records and the "
            "rule registry in a later stage. No applicability or compliance "
            "conclusions are invented here."
        ),
    },
    "fw.pillars_title": {"zh-TW": "四大支柱", "en": "Four pillars"},
    "fw.pillars_help": {
        "zh-TW": "先理解每個支柱要回答什麼，再準備對應資訊與證據。",
        "en": "Learn what each pillar asks before gathering evidence.",
    },
    "fw.pillar.contains": {"zh-TW": "此處資訊：", "en": "Information here:"},
    "fw.pillar.governance_help": {
        "zh-TW": "董事會與管理階層如何監督氣候與永續相關風險與機會。",
        "en": (
            "How the board and management oversee climate-related "
            "risks and opportunities."
        ),
    },
    "fw.pillar.governance_need": {
        "zh-TW": "治理架構、職責、開會與監督紀錄。",
        "en": "Governance structure, roles, meeting and oversight records.",
    },
    "fw.pillar.strategy_help": {
        "zh-TW": "氣候相關風險／機會如何影響商業模式與策略韌性。",
        "en": (
            "How climate risks/opportunities affect business model "
            "and strategy resilience."
        ),
    },
    "fw.pillar.strategy_need": {
        "zh-TW": "風險機會說明、轉型計畫、情境分析摘要。",
        "en": "Risk/opportunity narrative, transition plans, scenario summaries.",
    },
    "fw.pillar.risk_help": {
        "zh-TW": "如何辨識、評估、排序與管理氣候相關風險。",
        "en": (
            "How climate-related risks are identified, assessed, "
            "prioritized, and managed."
        ),
    },
    "fw.pillar.risk_need": {
        "zh-TW": "風險流程說明、評估結果、與既有風險管理整合方式。",
        "en": "Risk process notes, assessment outcomes, integration with ERM.",
    },
    "fw.pillar.metrics_help": {
        "zh-TW": "用來衡量與管理氣候相關風險／機會的指標與目標。",
        "en": (
            "Metrics and targets used to measure and manage "
            "climate-related risks/opportunities."
        ),
    },
    "fw.pillar.metrics_need": {
        "zh-TW": "Scope 1/2（及相關）指標、目標、計算依據與證據。",
        "en": "Scope 1/2 (and related) metrics, targets, methods, and evidence.",
    },
    "fw.learning_path_title": {
        "zh-TW": "建議學習路徑",
        "en": "Suggested learning path",
    },
    "fw.learning_path_body": {
        "zh-TW": "了解 → 準備 → 提供證據 → 完成揭露（工作流程，不是合規分數）。",
        "en": (
            "Learn → Prepare → Provide evidence → Disclose "
            "(workflow, not a compliance score)."
        ),
    },
    "fw.metrics_help": {
        "zh-TW": "目前已實作的 IFRS S2 氣候指標就緒度檢視（資料準備，非合規分數）。",
        "en": (
            "Currently implemented IFRS S2 climate-metrics readiness view "
            "(data prep, not a compliance score)."
        ),
    },
    "fw.data_readiness_section": {
        "zh-TW": "資料準備度",
        "en": "Data readiness",
    },
    "fw.metrics_readiness_title": {
        "zh-TW": "氣候指標資料準備度",
        "en": "Climate Metrics Data Readiness",
    },
    "fw.metrics_readiness_disclaimer": {
        "zh-TW": (
            "此區僅反映目前排放／氣候資料的可用程度，"
            "不代表 IFRS S1/S2 整體符合程度。"
        ),
        "en": (
            "This section reflects only how complete current emissions / climate "
            "data is. It does not represent overall IFRS S1/S2 compliance."
        ),
    },
    "fw.needs_information": {
        "zh-TW": "需要更多資訊",
        "en": "Needs information",
    },
    "fw.ghg_card_title": {"zh-TW": "公司碳盤查", "en": "Corporate GHG inventory"},
    "fw.ghg_question": {
        "zh-TW": "「這筆排放在公司盤查裡屬於哪個 Scope？」",
        "en": "“Which Scope does this belong to in the corporate inventory?”",
    },
    "fw.ghg_examples": {
        "zh-TW": (
            "天然氣 → Scope 1｜公司車柴油 → Scope 1｜"
            "外購電力 → Scope 2｜採購鋼材 → Scope 3"
        ),
        "en": (
            "Natural gas → Scope 1 · Fleet diesel → Scope 1 · "
            "Electricity → Scope 2 · Steel → Scope 3"
        ),
    },
    "fw.cbam_card_title": {
        "zh-TW": "歐盟出口產品碳資料",
        "en": "EU export product carbon data",
    },
    "fw.cbam_question": {
        "zh-TW": "「這筆資料跟出口歐盟的產品有什麼關係？」",
        "en": "“How does this record relate to an EU-exported product?”",
    },
    "fw.cbam_note": {
        "zh-TW": "不是把 Scope 1、2、3 直接搬過來使用。",
        "en": "This is not a direct copy of Scope 1 / 2 / 3.",
    },
    "fw.ifrs_card_title": {
        "zh-TW": "氣候資訊揭露準備",
        "en": "Climate disclosure readiness",
    },
    "fw.ifrs_question": {
        "zh-TW": "「目前的碳資料是否足以支援氣候相關揭露？」",
        "en": "“Is current carbon evidence enough to support climate disclosure prep?”",
    },
    "fw.ifrs_note": {
        "zh-TW": "不是重新計算一次排放。",
        "en": "This does not recalculate emissions.",
    },
    "fw.cbam_warning": {
        "zh-TW": "CN 7318 為示範假設，不是正式海關分類判定。",
        "en": "CN 7318 is a demo assumption — not a formal customs classification.",
    },
    "fw.ifrs_warning": {
        "zh-TW": "這是資料準備度判斷，不是 IFRS S2 合規判定。",
        "en": (
            "This is a data-readiness assessment, not an IFRS S2 "
            "compliance judgment."
        ),
    },
    "fw.disabled": {
        "zh-TW": "尚未執行這項分析。請在左側勾選此項目後，重新按「開始分析」。",
        "en": (
            "Not run for this analysis. Enable it in the sidebar and "
            "run analysis again."
        ),
    },
    "fw.disabled_title": {
        "zh-TW": "尚未執行此分析",
        "en": "Not run for this analysis",
    },
    "fw.col.activity": {"zh-TW": "活動", "en": "Activity"},
    "fw.col.scope": {"zh-TW": "Scope", "en": "Scope"},
    "fw.col.type": {"zh-TW": "類型", "en": "Category / type"},
    "fw.col.status": {"zh-TW": "狀態", "en": "Status"},
    "fw.col.reason": {"zh-TW": "說明", "en": "Reason"},
    "fw.col.role": {"zh-TW": "CBAM 用途", "en": "CBAM role"},
    "fw.col.relevance": {"zh-TW": "相關性", "en": "Relevance"},
    "fw.col.missing": {"zh-TW": "缺少資料", "en": "What is missing"},
    "fw.col.evidence_role": {"zh-TW": "資料角色", "en": "Evidence role"},
    "fw.col.readiness": {
        "zh-TW": "資料準備狀態",
        "en": "Data readiness",
    },
    # Audit
    "aud.title": {
        "zh-TW": "碳排報表與匯出",
        "en": "Emissions Reports & Exports",
    },
    "aud.subtitle": {
        "zh-TW": "下載主管可交付的碳排摘要報告，並保留專業覆核附件。",
        "en": (
            "Download the management-ready emissions summary report, "
            "with technical review files kept for specialists."
        ),
    },
    "aud.help": {
        "zh-TW": "輸出為佐證包／就緒度工作底稿。系統不宣稱產出完整正式申報。",
        "en": (
            "Outputs are supporting packages / readiness workpapers. "
            "The system does not claim to produce a complete official filing."
        ),
    },
    "aud.workpaper_note": {
        "zh-TW": "請以工作底稿／佐證包理解下載內容，而非正式法規申報檔。",
        "en": (
            "Treat downloads as workpapers / supporting packages, "
            "not official regulatory filings."
        ),
    },
    "aud.hero": {
        "zh-TW": "下載你的分析成果",
        "en": "Download your analysis results",
    },
    "aud.group.management": {"zh-TW": "管理摘要", "en": "Management summary"},
    "aud.group.compliance": {
        "zh-TW": "合規準備",
        "en": "Compliance preparation",
    },
    "aud.group.evidence": {
        "zh-TW": "GHG / 證據工作底稿",
        "en": "GHG & evidence workpapers",
    },
    "aud.group.data": {"zh-TW": "資料匯出", "en": "Data export"},
    "aud.group.ready": {"zh-TW": "可下載", "en": "Ready"},
    "aud.group.partial": {"zh-TW": "部分就緒", "en": "Partially ready"},
    "aud.zip_title": {
        "zh-TW": "工作底稿／佐證包",
        "en": "Workpaper / supporting package",
    },
    "aud.zip_desc": {
        "zh-TW": (
            "包含活動資料、排放計算、待處理問題、IFRS 就緒度與證據追蹤"
            "（工作底稿用途）。"
        ),
        "en": (
            "Includes activities, calculations, open issues, IFRS readiness, "
            "and evidence trail files (workpaper use)."
        ),
    },
    "aud.zip_button": {
        "zh-TW": "下載稽核包 (.zip)",
        "en": "Download audit package (.zip)",
    },
    "aud.csv_title": {"zh-TW": "待處理問題", "en": "Open issues"},
    "aud.csv_desc": {
        "zh-TW": "可直接使用 Excel 開啟，方便整理需要補充的資料。",
        "en": "Open in Excel to track the data you still need to collect.",
    },
    "aud.csv_button": {
        "zh-TW": "下載待處理問題 (.csv)",
        "en": "Download open issues (.csv)",
    },
    "aud.info_title": {"zh-TW": "分析資訊", "en": "Analysis information"},
    "aud.evidence_title": {"zh-TW": "來源證據", "en": "Source evidence"},
    "aud.advanced": {"zh-TW": "進階技術資訊", "en": "Advanced technical details"},
    "aud.run_id": {"zh-TW": "Run ID", "en": "Run ID"},
    "aud.activities": {"zh-TW": "活動資料", "en": "Activities"},
    "aud.calculations": {"zh-TW": "排放計算", "en": "Calculations"},
    "aud.issues": {"zh-TW": "待處理問題", "en": "Open issues"},
    "aud.enabled": {"zh-TW": "已啟用分析", "en": "Enabled adapters"},
    "aud.ref_title": {"zh-TW": "官方參考資料", "en": "Official reference data"},
    "aud.ref_help": {
        "zh-TW": (
            "此區塊供資料維護檢視。一般碳分析不會連網抓取係數，"
            "也不會自動啟用新下載的官方數值。"
        ),
        "en": (
            "Maintenance view only. Normal analysis does not crawl the web "
            "and never auto-activates newly downloaded official values."
        ),
    },
    "aud.ref_electricity": {
        "zh-TW": "電力排放係數（企業盤查）",
        "en": "Electricity factor — enterprise inventory",
    },
    "aud.ref_upstream_authority": {
        "zh-TW": "上游係數權責機關",
        "en": "Upstream factor authority",
    },
    "aud.ref_operational_source": {
        "zh-TW": "運作中的官方來源",
        "en": "Operational official source",
    },
    "aud.ref_heating": {
        "zh-TW": "燃料熱值",
        "en": "Fuel heating values",
    },
    "aud.ref_last_checked": {
        "zh-TW": "上次檢查",
        "en": "Last checked",
    },
    "aud.ref_year_available": {"zh-TW": "已登錄", "en": "available"},
    "aud.ref_year_candidate": {"zh-TW": "候選", "en": "candidate"},
    "aud.ref_year_unavailable": {"zh-TW": "尚未登錄", "en": "unavailable"},
    "aud.ref_unregistered": {"zh-TW": "尚未登錄", "en": "unregistered"},
    # Action-driven first-run onboarding.
    # One short welcome, then five coachmarks on the real product UI.
    # No legal conclusions, internal states, or technical data semantics.
    "onb.welcome.title": {
        "zh-TW": "完成第一筆碳排計算",
        "en": "Complete your first emissions calculation",
    },
    "onb.welcome.body": {
        "zh-TW": (
            "準備一份公司現有的 Excel 或 CSV，"
            "我們會帶你完成設定、確認與計算。"
        ),
        "en": (
            "Have an Excel or CSV ready. We’ll guide you through setup, "
            "review, and calculation."
        ),
    },
    "onb.welcome.start": {"zh-TW": "開始", "en": "Start"},
    "onb.welcome.later": {"zh-TW": "稍後再說", "en": "Not now"},
    "onb.finish": {"zh-TW": "完成", "en": "Finish"},
    "onb.progress": {
        "zh-TW": "第 {current}／{total} 步",
        "en": "Step {current} of {total}",
    },
    "onb.s1.title": {
        "zh-TW": "完成公司設定",
        "en": "Complete company setup",
    },
    "onb.s1.body": {
        "zh-TW": "先確認公司與本次計算範圍。",
        "en": "First, confirm the company and calculation scope.",
    },
    "onb.s1a.title": {
        "zh-TW": "開始公司設定",
        "en": "Start company setup",
    },
    "onb.s1a.body": {
        "zh-TW": "先確認公司與本次計算範圍。",
        "en": "First, confirm the company and calculation scope.",
    },
    "onb.s1b.title": {
        "zh-TW": "查詢公司",
        "en": "Find your company",
    },
    "onb.s1b.body": {
        "zh-TW": "輸入公司的 8 位統一編號，再點「查詢公司」。",
        "en": "Enter the 8-digit business number, then select “Look up company”.",
    },
    "onb.s1c.title": {
        "zh-TW": "核對公司資料",
        "en": "Confirm the company",
    },
    "onb.s1c.body": {
        "zh-TW": "確認公司名稱與地址後，點「這是我的公司」。",
        "en": (
            "Check the company name and address, then confirm that it is "
            "your company."
        ),
    },
    "onb.s1d.title": {
        "zh-TW": "補充公司資料",
        "en": "Complete company details",
    },
    "onb.s1d.body": {
        "zh-TW": "確認報導年度與公司類型，再點「繼續」。",
        "en": "Confirm the reporting year and company type, then continue.",
    },
    "onb.s1e.title": {
        "zh-TW": "補充必要資訊",
        "en": "Add required details",
    },
    "onb.s1e.body": {
        "zh-TW": "確認市場別與其他必要欄位，再點「繼續」。",
        "en": "Confirm listing and other required fields, then continue.",
    },
    "onb.s1f.title": {
        "zh-TW": "確認台灣廠場",
        "en": "Confirm Taiwan sites",
    },
    "onb.s1f.body": {
        "zh-TW": "確認目前仍由公司營運的廠場。",
        "en": "Confirm the sites the company still operates.",
    },
    "onb.s1g.title": {
        "zh-TW": "繼續公司設定",
        "en": "Continue company setup",
    },
    "onb.s1g.body": {
        "zh-TW": "廠場已確認，點「繼續」進入下一畫面。",
        "en": "Sites are confirmed. Select “Continue” for the next step.",
    },
    "onb.s1h.title": {
        "zh-TW": "確認報導期間",
        "en": "Confirm the reporting period",
    },
    "onb.s1h.body": {
        "zh-TW": "確認年度與起迄日期後繼續。",
        "en": "Confirm the year and dates, then continue.",
    },
    "onb.s1i.title": {
        "zh-TW": "查看申報目的",
        "en": "Review reporting purposes",
    },
    "onb.s1i.body": {
        "zh-TW": "查看本次申報目的後繼續。",
        "en": "Review the reporting purposes, then continue.",
    },
    "onb.s1j.title": {
        "zh-TW": "確認永續揭露報導個體",
        "en": "Confirm the sustainability disclosure reporting entity",
    },
    "onb.s1j.body": {
        "zh-TW": "確認永續揭露報導個體後繼續。",
        "en": "Confirm the sustainability disclosure reporting entity, then continue.",
    },
    "onb.s1k.title": {
        "zh-TW": "核對政府紀錄",
        "en": "Match government records",
    },
    "onb.s1k.body": {
        "zh-TW": "核對政府紀錄與公司實際據點後繼續。",
        "en": "Match government records with company sites, then continue.",
    },
    "onb.s1l.title": {
        "zh-TW": "確認營運範圍",
        "en": "Confirm operating scope",
    },
    "onb.s1l.body": {
        "zh-TW": "確認本期間營運範圍後繼續。",
        "en": "Confirm operations for this period, then continue.",
    },
    "onb.s1m.title": {
        "zh-TW": "確認計算範圍",
        "en": "Confirm calculation scope",
    },
    "onb.s1m.body": {
        "zh-TW": "確認計算範圍以完成公司設定。",
        "en": "Confirm the calculation scope to finish company setup.",
    },
    "onb.s2.title": {
        "zh-TW": "上傳活動資料",
        "en": "Upload activity data",
    },
    "onb.s2.body": {
        "zh-TW": "選擇公司現有的 Excel 或 CSV。",
        "en": "Choose an existing Excel or CSV file.",
    },
    "onb.s3.title": {
        "zh-TW": "確認資料內容",
        "en": "Review your data",
    },
    "onb.s3.body": {
        "zh-TW": "選擇正確答案後完成確認。",
        "en": "Choose the correct answer, then confirm it.",
    },
    "onb.s4.title": {
        "zh-TW": "開始計算",
        "en": "Start calculation",
    },
    "onb.s4.body": {
        "zh-TW": "確認本次資料筆數後，開始分析。",
        "en": "Review the record count, then start analysis.",
    },
    "onb.s4a.title": {
        "zh-TW": "檢查計算範圍",
        "en": "Review calculation coverage",
    },
    "onb.s4a.body": {
        "zh-TW": "確認本次會處理的資料筆數。",
        "en": "Review the number of records included in this calculation.",
    },
    "onb.s4b.title": {
        "zh-TW": "開始計算",
        "en": "Start calculation",
    },
    "onb.s4b.body": {
        "zh-TW": "確認無誤後，開始分析。",
        "en": "When everything looks right, start the analysis.",
    },
    "onb.s5.title": {
        "zh-TW": "查看計算結果",
        "en": "View your results",
    },
    "onb.s5.body": {
        "zh-TW": "排放總量、計算依據與 PDF 報告都在這裡。",
        "en": (
            "Your emissions total, calculation details, and PDF report "
            "are here."
        ),
    },
    # In-page hint on the applicable-requirements page. Not an onboarding step.
    "onb.applicability_hint": {
        "zh-TW": "查看目前可能適用的要求與重要時程。",
        "en": "Review requirements and key dates that may apply to your company.",
    },
    # Explanations used in view models
    "explain.calculated": {
        "zh-TW": "已用已驗證輸入與對應排放係數完成計算。",
        "en": "Emissions were calculated from verified inputs and a matched factor.",
    },
    "explain.blocked_missing_conversion": {
        "zh-TW": "缺少已驗證的轉換資料，因此目前無法計算。",
        "en": (
            "Calculation is blocked until verified conversion evidence "
            "is registered."
        ),
    },
    "explain.blocked_natural_gas_type_required": {
        "zh-TW": "請確認天然氣類型（NG1 或 NG2），才能套用正確熱值。",
        "en": (
            "Confirm whether this activity uses NG1 or NG2 before the "
            "official heating value can be applied."
        ),
    },
    "explain.no_factor_configured": {
        "zh-TW": (
            "尚未找到適用於這筆活動期間的官方排放係數。"
            "系統不會自動使用不同年度的係數。"
        ),
        "en": (
            "No official emission factor applies to this activity period. "
            "The system will not silently use a different year's factor."
        ),
    },
    "explain.no_matching_factor": {
        "zh-TW": "目前無符合係數。",
        "en": "No matching factor.",
    },
    "explain.no_factor_configured_year": {
        "zh-TW": (
            "尚未找到適用於這筆活動期間的官方排放係數。\n"
            "活動期間：\n{activity_year}\n"
            "目前已登錄：\n{registered_years}\n"
            "系統不會自動使用不同年度的係數。"
        ),
        "en": (
            "No official emission factor applies to this activity period.\n"
            "Activity period:\n{activity_year}\n"
            "Currently registered:\n{registered_years}\n"
            "The system will not silently use a different year's factor."
        ),
    },
    "explain.not_emissions_activity": {
        "zh-TW": "這筆是輔助營運資料，不是排放來源本身。",
        "en": "This record is supporting operational data, not an emissions source.",
    },
    "next.blocked_missing_conversion": {
        "zh-TW": "取得並登錄所需的已驗證轉換證據。",
        "en": "Obtain and register the required verified conversion evidence.",
    },
    "next.blocked_natural_gas_type_required": {
        "zh-TW": "請確認天然氣類型為 NG1 或 NG2。系統不會自行推測。",
        "en": "Confirm NG1 or NG2. The type is not inferred.",
    },
    "next.no_factor_configured": {
        "zh-TW": "選定並文件化適用的排放係數後再計算。",
        "en": "Select and document an appropriate emission factor before calculation.",
    },
    "next.no_matching_factor": {
        "zh-TW": "補齊產品類型與已核准係數後再計算。",
        "en": "Confirm the product type and an approved factor before calculation.",
    },
    "next.calculated": {
        "zh-TW": "此筆計算無需額外動作。",
        "en": "No calculation action required for this record.",
    },
    "next.not_emissions_activity": {
        "zh-TW": "保留作為輔助或分母證據即可。",
        "en": "Keep as supporting operational or denominator evidence.",
    },
    "explain.steel.calculated": {
        "zh-TW": (
            "已依採購質量乘上搖籃到大門係數完成估算。"
            "供應商以前的供應鏈運輸涵蓋情形由係數來源與系統邊界判定；"
            "本列 Category 1 不含需另行分類的供應商到本公司運輸盤查。"
        ),
        "en": (
            "Estimated as purchased mass times a cradle-to-gate factor. "
            "Pre-Tier-1 supply-chain transport coverage is taken from the "
            "factor source and system boundary. This Category 1 result does "
            "not inventory a separate Tier 1 to reporting-company transport leg."
        ),
    },
    "explain.steel.no_factor_configured": {
        "zh-TW": "目前尚未設定符合條件的平均數據係數，因此本列暫不計算。",
        "en": (
            "No matching average-data factor is configured yet, "
            "so this row is not calculated."
        ),
    },
    "explain.steel.no_matching_factor": {
        "zh-TW": "沒有唯一且已核准的平均數據係數可精確匹配，因此本列暫不計算。",
        "en": (
            "No unique approved average-data factor matches this row, "
            "so emissions are not calculated."
        ),
    },
    "explain.steel.blocked_missing_supplier_or_product": {
        "zh-TW": "供應商特定法需要供應商名稱；僅有產品類型不足以計算。",
        "en": (
            "The supplier-specific method requires a supplier name; "
            "a product type alone is not enough."
        ),
    },
    "explain.steel.blocked_missing_factor_year": {
        "zh-TW": "供應商特定法需要係數年份。系統不會用盤查年度自動補上。",
        "en": (
            "The supplier-specific method requires factor year. "
            "Reporting year is not substituted."
        ),
    },
    "explain.steel.blocked_missing_product_type": {
        "zh-TW": "需要鋼材產品類型或明確產品識別。",
        "en": "A steel product type or explicit product identifier is required.",
    },
    "explain.steel.blocked_missing_evidence": {
        "zh-TW": "需要係數來源編號、證據參照或來源文件，才能追溯供應商文件。",
        "en": (
            "A factor source id, evidence reference, or source document is "
            "required so the supplier document can be traced."
        ),
    },
    "explain.steel.blocked_transport_not_category_1": {
        "zh-TW": (
            "獨立的第三方運輸紀錄不屬於 Category 1 採購鋼材。"
        ),
        "en": (
            "A standalone third-party transport record is not Scope 3 "
            "Category 1 purchased steel."
        ),
    },
    "explain.steel.blocked_factor_inclusion_unconfirmed": {
        "zh-TW": (
            "尚未確認此筆鋼材使用的排放係數是否包含 Tier 1 供應商到本公司的運輸。"
            "空白不會被當成「不包含」，因此本列暫不計算。"
        ),
        "en": (
            "Confirm whether the steel emission factor includes Tier 1 "
            "supplier to this-company transport. Blank is not treated as "
            "excluded, so this row is not calculated."
        ),
    },
    "explain.steel.blocked_transport_control_unconfirmed": {
        "zh-TW": (
            "此係數包含 Tier 1 供應商到本公司運輸，但尚未確認運輸工具由誰擁有或控制。"
            "在確認前本列不計算，也不會推測為 Category 4。"
        ),
        "en": (
            "The factor includes Tier 1 supplier to this-company transport, "
            "but vehicle ownership/control is not confirmed. The row is not "
            "calculated and Category 4 is not inferred."
        ),
    },
    "explain.steel.blocked_tier1_inbound_transport_requires_category4_split": {
        "zh-TW": (
            "此係數包含由第三方承運的 Tier 1 供應商到本公司運輸。"
            "該段應另列 Scope 3 Category 4；在取得不含該段運輸的鋼材係數"
            "或完成拆分前，本列不計入 Category 1。"
        ),
        "en": (
            "This factor includes third-party carriage from the Tier 1 "
            "supplier to this company. That leg belongs in Scope 3 "
            "Category 4. Until a steel factor without that leg, or a split, "
            "is available, this row is not counted in Category 1."
        ),
    },
    "explain.steel.blocked_company_controlled_transport_requires_scope1_or2_split": {
        "zh-TW": (
            "此係數包含由本公司擁有或控制之運輸排放。"
            "該段應依能源來源分別列入 Scope 1 或 Scope 2；"
            "在取得不含該段運輸的鋼材係數或完成拆分前，本列不計入 Category 1。"
        ),
        "en": (
            "This factor includes transport owned or controlled by this "
            "company. That leg belongs in Scope 1 or Scope 2 by energy "
            "source. Until a steel factor without that leg, or a split, is "
            "available, this row is not counted in Category 1."
        ),
    },
    "explain.steel.blocked_ambiguous_factor": {
        "zh-TW": "同時有多筆符合的平均係數。系統不會自動選最新版。",
        "en": (
            "More than one matching average factor covers this year. "
            "The newest version is not selected automatically."
        ),
    },
    "explain.steel.blocked_unsupported_calculation_method": {
        "zh-TW": "目前只支援供應商特定與平均數據法，尚未支援混合法或支出法。",
        "en": (
            "Only supplier-specific and average-data methods are supported. "
            "Hybrid and spend-based methods are not available."
        ),
    },
    "explain.steel.blocked_incompatible_factor_boundary": {
        "zh-TW": "係數邊界必須明確為搖籃到大門（cradle-to-gate）。",
        "en": "The factor boundary must be explicitly cradle-to-gate.",
    },
    "explain.steel.blocked_missing_factor_geography": {
        "zh-TW": "平均數據法需要精確的係數地理範圍，系統不會跨地區推測。",
        "en": (
            "The average-data method needs an exact factor geography. "
            "Geography is not inferred."
        ),
    },
    "severity.critical": {"zh-TW": "重大", "en": "Critical"},
    "severity.high": {"zh-TW": "高優先", "en": "High"},
    "severity.medium": {"zh-TW": "中", "en": "Medium"},
    "severity.low": {"zh-TW": "低", "en": "Low"},
    "severity.info": {"zh-TW": "資訊", "en": "Info"},
    # Charts (Phase 8E)
    "chart.calc_status.title": {
        "zh-TW": "活動計算狀態",
        "en": "Calculation status",
    },
    "chart.calc_status.help": {
        "zh-TW": "顯示目前 {n} 筆活動資料中，哪些已能計算、哪些仍缺資料。",
        "en": (
            "Shows which of the {n} activities can be calculated "
            "and which still have gaps."
        ),
    },
    "chart.activity_status.title": {
        "zh-TW": "各活動目前狀態",
        "en": "Activity status breakdown",
    },
    "chart.activity_status.help": {
        "zh-TW": "快速看出哪一筆活動已完成計算，哪一筆需要處理。",
        "en": "See at a glance which activities are calculated and which need action.",
    },
    "chart.emissions_contrib.help": {
        "zh-TW": "目前已納入公司盤查排放量的來源活動（缺少資料的活動不會以 0 呈現）。",
        "en": (
            "Activities contributing to company inventory emissions "
            "(gaps are not shown as zero)."
        ),
    },
    "chart.emissions_contrib.empty": {
        "zh-TW": "目前尚無已納入公司盤查的活動排放量。",
        "en": "No company inventory activity emissions yet.",
    },
    "chart.ghg_scope.title": {
        "zh-TW": "活動分類筆數",
        "en": "Activity classification count",
    },
    "chart.ghg_scope.help": {
        "zh-TW": "此圖顯示活動分類筆數，不代表各 Scope 的排放量占比。",
        "en": (
            "This chart shows activity classification counts, "
            "not emissions share by Scope."
        ),
    },
    "chart.cbam_roles.title": {
        "zh-TW": "CBAM 資料角色筆數",
        "en": "CBAM data-role counts",
    },
    "chart.cbam_roles.help": {
        "zh-TW": "依目前評估結果統計各 CBAM 資料角色出現次數。",
        "en": "Counts of CBAM data roles from the current evaluation.",
    },
    "chart.ifrs_ready.title": {
        "zh-TW": "氣候指標資料準備度筆數",
        "en": "Climate metrics data readiness counts",
    },
    "chart.ifrs_ready.help": {
        "zh-TW": "依目前評估結果統計準備狀態筆數，不是合規分數。",
        "en": (
            "Counts of readiness statuses from the current evaluation "
            "— not a compliance score."
        ),
    },
    "chart.issue_gaps.title": {
        "zh-TW": "缺少資料類型",
        "en": "Missing-data types",
    },
    "chart.issue_gaps.help": {
        "zh-TW": "目前待處理問題主要屬於哪些資料缺口類型。",
        "en": "Which kinds of data gaps appear in the open issues list.",
    },
    "chart.issue.missing_conversion": {
        "zh-TW": "缺少熱值 / 轉換資料",
        "en": "Missing heating-value / conversion data",
    },
    "chart.issue.missing_factor": {
        "zh-TW": "缺少排放係數",
        "en": "Missing emission factor",
    },
    "act.status_strip": {
        "zh-TW": "目前狀態",
        "en": "Current status",
    },
    # Phase 9A Data Intake
    "intake.title": {
        "zh-TW": "上傳能源與營運資料",
        "en": "Upload energy and operating data",
    },
    "intake.subtitle": {
        "zh-TW": (
            "上傳活動資料後，系統會協助確認欄位、單位與資料完整性，"
            "完成後再進行排放分析。"
        ),
        "en": (
            "After you upload activity data, the system helps confirm "
            "columns, units, and completeness before emissions analysis."
        ),
    },
    "intake.page_lead": {
        "zh-TW": (
            "請直接使用公司目前的 Excel 或 CSV，不必重新整理格式。"
            "系統會辨識欄位、單位、日期與廠場，只詢問不確定的項目。"
        ),
        "en": (
            "Use the Excel or CSV your company already maintains. "
            "The system will identify columns, units, dates, and facilities, "
            "and will only ask about uncertain items."
        ),
    },
    "intake.upload_existing_title": {
        "zh-TW": "上傳公司現有資料",
        "en": "Upload your company’s existing data",
    },
    "intake.processing_title": {
        "zh-TW": "正在讀取檔案…",
        "en": "Reading the file…",
    },
    "intake.processing_body": {
        "zh-TW": "我們正在辨識工作表、欄位與資料格式。",
        "en": "We are identifying worksheets, columns, and the data layout.",
    },
    "intake.read_title": {
        "zh-TW": "資料已讀取",
        "en": "File read successfully",
    },
    "intake.read_found": {
        "zh-TW": "找到 {n} 筆資料",
        "en": "{n} records found",
    },
    "intake.read_mapped": {
        "zh-TW": "系統已提出 {mapped} 個欄位對應",
        "en": "{mapped} column matches proposed",
    },
    "intake.read_confirm_count": {
        "zh-TW": "{confirm} 個項目需要確認",
        "en": "{confirm} questions still need answers",
    },
    "intake.read_recognized": {
        "zh-TW": "系統已自動辨識 {n} 個欄位",
        "en": "{n} fields recognized automatically",
    },
    "intake.read_rows": {
        "zh-TW": "可繼續 {ready} 筆；{held} 筆暫緩處理",
        "en": "{ready} rows can continue; {held} rows are deferred",
    },
    "intake.status.ready": {
        "zh-TW": "資料已可繼續",
        "en": "This file is ready to continue",
    },
    "intake.status.deferred": {
        "zh-TW": "已完成目前確認；另有 {n} 筆暫緩處理，不納入本次計算",
        "en": (
            "All current questions are complete; {n} rows are deferred "
            "and will not be calculated this time"
        ),
    },
    "intake.memory.found": {
        "zh-TW": "找到上次確認的欄位設定",
        "en": "Previous confirmed column settings were found",
    },
    "intake.memory.explain": {
        "zh-TW": "這份檔案的格式與上次相同，可以沿用已確認的設定。",
        "en": (
            "This file has the same format as last time. "
            "You can reuse the confirmed settings."
        ),
    },
    "intake.memory.use": {
        "zh-TW": "使用上次設定",
        "en": "Use previous settings",
    },
    "intake.memory.recheck": {
        "zh-TW": "重新檢查",
        "en": "Check again",
    },
    "intake.memory.history": {
        "zh-TW": "查看欄位處理紀錄",
        "en": "View column processing history",
    },
    "intake.memory.history_action": {
        "zh-TW": "處理",
        "en": "Action",
    },
    "intake.memory.history_field": {
        "zh-TW": "項目",
        "en": "Item",
    },
    "intake.memory.history_detail": {
        "zh-TW": "內容",
        "en": "Detail",
    },
    "intake.memory.history_when": {
        "zh-TW": "時間",
        "en": "Time",
    },
    "intake.history.emission_activity": {
        "zh-TW": "排放活動",
        "en": "Emissions activity",
    },
    "intake.ex.progress": {
        "zh-TW": "需要確認 {current}／{total}",
        "en": "Needs confirmation {current}/{total}",
    },
    "intake.sheet_ask": {
        "zh-TW": "哪一個工作表包含能源或營運資料？",
        "en": "Which worksheet contains energy or operating data?",
    },
    "intake.ex.usage_q_blank": {
        "zh-TW": "哪一欄是實際用量？",
        "en": "Which column is the actual quantity?",
    },
    "intake.ex.date_era_q": {
        "zh-TW": "這一欄的日期是民國年還是西元年？",
        "en": "Are the dates in this column Minguo or Gregorian years?",
    },
    "intake.upload_no_pdf": {
        "zh-TW": "本版接受 Excel 或 CSV。掃描件與 PDF 請先轉成試算表後再上傳。",
        "en": (
            "This version accepts Excel or CSV. "
            "Convert scans and PDFs to a spreadsheet first."
        ),
    },
    "intake.err_pdf": {
        "zh-TW": "本版接受 Excel 或 CSV。請改上傳試算表，範本僅供參考。",
        "en": (
            "This version accepts Excel or CSV. "
            "Please upload a spreadsheet instead. The example is optional."
        ),
    },
    "intake.ex.queue_title": {
        "zh-TW": "需要你確認的項目",
        "en": "Items that need your answer",
    },
    "intake.ex.none": {
        "zh-TW": "資料已可繼續",
        "en": "This file is ready to continue",
    },
    "intake.ex.apply": {
        "zh-TW": "確認並前往下一題",
        "en": "Confirm and go to the next question",
    },
    "intake.ex.apply_last": {
        "zh-TW": "完成確認並檢查資料",
        "en": "Finish confirmation and review data",
    },
    "intake.ex.previous": {"zh-TW": "上一題", "en": "Previous"},
    "intake.ex.editor_apply": {
        "zh-TW": "套用這些調整",
        "en": "Apply these adjustments",
    },
    "intake.ex.column_q": {
        "zh-TW": "請確認「{column}」欄位",
        "en": "Please confirm the “{column}” column",
    },
    "intake.ex.column_q_blank": {
        "zh-TW": "請選擇哪一欄是{label}。",
        "en": "Please choose which column is {label}.",
    },
    "intake.ex.column_why": {
        "zh-TW": "沒有這個對應，系統無法正確讀取這份檔案。",
        "en": "Without this match, the file cannot be read correctly.",
    },
    "intake.ex.column_why_medium": {
        "zh-TW": "系統建議使用這一欄作為排放計算的{label}。",
        "en": (
            "The system suggests using this column as the {label} "
            "for emission calculation."
        ),
    },
    "intake.ex.column_control": {
        "zh-TW": "要使用哪一欄？",
        "en": "Which column should be used?",
    },
    "intake.ex.proposed": {
        "zh-TW": "系統建議：{value}",
        "en": "Suggested answer: {value}",
    },
    "intake.ex.ym_q": {
        "zh-TW": "請確認系統將「{column}」讀成資料期間。",
        "en": "Please confirm that “{column}” is the reporting period.",
    },
    "intake.ex.dates_q": {
        "zh-TW": "請告訴系統這份資料的日期或期間。",
        "en": "Please tell the system the dates or period for this file.",
    },
    "intake.ex.ng_q": {
        "zh-TW": "確認天然氣種類",
        "en": "Confirm the natural-gas type",
    },
    "intake.ex.ng_why": {
        "zh-TW": (
            "天然氣種類會影響熱值與排放量。系統目前無法從這份資料判斷，"
            "請查看天然氣帳單或供氣契約。"
        ),
        "en": (
            "Natural-gas type affects heating value and emissions. "
            "The system cannot determine it from this file; "
            "please check a natural-gas bill or supply contract."
        ),
    },
    "intake.ex.ng_group": {
        "zh-TW": "適用據點：{site}（{n} 筆）",
        "en": "Applies to site {site} ({n} rows)",
    },
    "intake.ex.ng_single": {
        "zh-TW": "本檔單一來源",
        "en": "This file’s single source",
    },
    "intake.ex.ng_hint": {
        "zh-TW": "僅供參考：先前在本工作階段曾確認為 {value}。新檔仍須確認。",
        "en": (
            "For reference only: this session previously confirmed {value}. "
            "A new file still needs confirmation."
        ),
    },
    "intake.ex.diesel_q": {
        "zh-TW": "這些柴油列是公司車輛使用嗎？",
        "en": "Are these diesel rows for company vehicles?",
    },
    "intake.ex.diesel_why": {
        "zh-TW": "無法確認用途時，這些列會暫不計算，不會被刪除。",
        "en": (
            "If the use cannot be confirmed, those rows are held out of "
            "calculation; they are not deleted."
        ),
    },
    "intake.ex.elec_q": {
        "zh-TW": "請確認這是公司營運使用的外購電力。",
        "en": (
            "Please confirm this is purchased electricity used for company "
            "operations."
        ),
    },
    "intake.ex.elec_why": {
        "zh-TW": (
            "原始資料只有「外購電力」，系統不會只因為單位是 kWh 就當成 Scope 2。"
            "確認為公司營運使用後才會納入企業盤查並計算；未確認的列會暫不計算。"
        ),
        "en": (
            "The source only says purchased electricity; kWh alone is not "
            "treated as Scope 2. Confirm company-operations use before the "
            "enterprise inventory calculation. Unconfirmed rows are held out."
        ),
    },
    "intake.ex.activity_q": {
        "zh-TW": "「{value}」是哪一種活動？",
        "en": "What activity is “{value}”?",
    },
    "intake.ex.unit_q": {
        "zh-TW": "「{value}」的單位是？",
        "en": "What unit is “{value}”?",
    },
    "intake.ex.unknown_rows": {
        "zh-TW": "還不確定（相關列暫不計算）",
        "en": "Not sure yet (those rows will not be calculated for now)",
    },
    "intake.ex.why_activity": {
        "zh-TW": "無法判斷活動類型時，這一列會暫不計算，不會被刪除。",
        "en": (
            "If the activity cannot be identified, the row is held out of "
            "calculation; it is not deleted."
        ),
    },
    "intake.draft_unapplied": {
        "zh-TW": "你有尚未套用的選擇。請先套用，才能繼續。",
        "en": "You have unapplied choices. Apply them before continuing.",
    },
    "intake.btn.continue_ready": {
        "zh-TW": "完成確認並檢查資料",
        "en": "Finish confirmation and review data",
    },
    "intake.validate.unexpected_error": {
        "zh-TW": "資料檢查未完成。請再試一次。",
        "en": "Data review did not finish. Please try again.",
    },
    "intake.validate.running_title": {
        "zh-TW": "正在檢查你的資料",
        "en": "Checking your data",
    },
    "intake.validate.processing_count": {
        "zh-TW": "正在處理 {count} 筆活動資料",
        "en": "Processing {count} activity records",
    },
    "intake.validate.percent": {
        "zh-TW": "{percent}%",
        "en": "{percent}%",
    },
    "intake.validate.stage.prepare": {
        "zh-TW": "準備欄位與來源文件",
        "en": "Preparing fields and source documents",
    },
    "intake.validate.stage.rows": {
        "zh-TW": "驗證資料列",
        "en": "Validating activity rows",
    },
    "intake.validate.stage.dispositions": {
        "zh-TW": "建立可納入／暫緩／無法納入結果",
        "en": "Building included, held, and excluded results",
    },
    "intake.validate.stage.duplicates": {
        "zh-TW": "重複資料檢查",
        "en": "Checking for duplicate records",
    },
    "intake.validate.stage.complete": {
        "zh-TW": "完成",
        "en": "Complete",
    },
    "intake.btn.continue_blocked": {
        "zh-TW": "完成剩餘 {n} 項確認後，即可檢查資料。",
        "en": "Complete the remaining {n} confirmations to review the data.",
    },
    "intake.rej.held_activity": {
        "zh-TW": "這一列的活動類型還無法判斷，因此暫不計算。",
        "en": "This row’s activity is still unclear, so it is not calculated yet.",
    },
    "intake.rej.held_unit": {
        "zh-TW": "這一列的單位還無法判斷，因此暫不計算。",
        "en": "This row’s unit is still unclear, so it is not calculated yet.",
    },
    "intake.rej.held_ng": {
        "zh-TW": "天然氣用途尚未確定，因此這一列暫不計算。",
        "en": (
            "Natural-gas context is still unknown, "
            "so this row is not calculated yet."
        ),
    },
    "intake.rej.held_pending_hv": {
        "zh-TW": "實際熱值待專業審核，因此這一列暫不計算，也不會當成零排放。",
        "en": (
            "The actual heating value is pending professional review, "
            "so this row is not calculated yet and is not treated as zero."
        ),
    },
    "intake.rej.held_diesel": {
        "zh-TW": "柴油用途尚未確定，因此這一列暫不計算。",
        "en": "Diesel context is still unknown, so this row is not calculated yet.",
    },
    "intake.rej.held_elec": {
        "zh-TW": "電力盤查用途尚未確定，因此這一列暫不計算。",
        "en": (
            "Electricity inventory context is still unknown, "
            "so this row is not calculated yet."
        ),
    },
    "intake.read_sheet": {
        "zh-TW": "工作表：{sheet}",
        "en": "Worksheet: {sheet}",
    },
    "intake.read_ask": {
        "zh-TW": "請確認系統對這份檔案的理解",
        "en": "Please confirm how the system read this file",
    },
    "intake.editor.required": {
        "zh-TW": "必須確認",
        "en": "Required",
    },
    "intake.editor.optional": {
        "zh-TW": "可選調整",
        "en": "Optional adjustments",
    },
    "intake.editor.dates": {
        "zh-TW": "日期與期間",
        "en": "Dates and period",
    },
    "intake.editor.values": {
        "zh-TW": "檔案內容對應",
        "en": "File value matching",
    },
    "intake.ng_option_1": {
        "zh-TW": "NG1——帳單或契約標示為 NG1",
        "en": "NG1 — the bill or contract is labelled NG1",
    },
    "intake.ng_option_2": {
        "zh-TW": "NG2——帳單或契約標示為 NG2",
        "en": "NG2 — the bill or contract is labelled NG2",
    },
    "intake.ng_option_actual_hv": {
        "zh-TW": "帳單提供實際熱值",
        "en": "An actual heating value is provided on the bill",
    },
    "intake.ng_option_cannot_confirm": {
        "zh-TW": "我現在無法確認，暫不納入計算",
        "en": "I cannot confirm now; hold out of calculation",
    },
    "intake.ng_pending_hv_title": {
        "zh-TW": "實際熱值待專業審核",
        "en": "Actual heating value pending professional review",
    },
    "intake.ng_pending_hv_help": {
        "zh-TW": (
            "請提供熱值、單位、適用期間與來源文件。此值必須經過驗證後才能用於計算，"
            "目前相關列暫不納入，也不會當成零排放。"
        ),
        "en": (
            "Provide the value, unit, applicable period, and source. "
            "It must be verified before it can be used. "
            "Affected rows are held out of calculation and are not treated as zero."
        ),
    },
    "intake.ng_pending_hv_value": {"zh-TW": "熱值", "en": "Heating value"},
    "intake.ng_pending_hv_unit": {"zh-TW": "單位", "en": "Unit"},
    "intake.ng_pending_hv_period": {
        "zh-TW": "適用期間",
        "en": "Applicable period",
    },
    "intake.ng_pending_hv_source": {
        "zh-TW": "來源文件或參考",
        "en": "Source document or reference",
    },
    "intake.upload_limit": {
        "zh-TW": "支援 CSV、XLSX。單一檔案最大 10 MB。",
        "en": "CSV and XLSX. Maximum 10 MB per file.",
    },
    "intake.need_help_prepare": {
        "zh-TW": "不知道怎麼準備資料？",
        "en": "Not sure how to prepare the file?",
    },
    "intake.needed_fields_title": {
        "zh-TW": "需要準備的資料",
        "en": "What to prepare",
    },
    "intake.needed_fields_list": {
        "zh-TW": (
            "- 活動類型\n"
            "- 用量\n"
            "- 單位\n"
            "- 開始日期\n"
            "- 結束日期"
        ),
        "en": (
            "- Activity type\n"
            "- Quantity\n"
            "- Unit\n"
            "- Start date\n"
            "- End date"
        ),
    },
    "intake.advanced_schema": {
        "zh-TW": "進階：查看系統欄位格式",
        "en": "Advanced: system field format",
    },
    "intake.example_expand": {
        "zh-TW": "查看填寫範例",
        "en": "View a fill-in example",
    },
    "intake.example_disclaimer": {
        "zh-TW": "以下僅為格式範例，不會自動匯入或參與分析。",
        "en": (
            "This is a format example only. "
            "It is not imported and is not used in analysis."
        ),
    },
    "intake.intro": {
        "zh-TW": (
            "不需要先修改原本 Excel 欄位名稱。\n"
            "系統會先嘗試辨識你的欄位，再請你確認是否正確。\n\n"
            "第一次使用？\n\n"
            "你只需要準備一份表格，每一列代表一筆活動資料，例如：\n"
            "- 外購電力\n"
            "- 天然氣\n"
            "- 柴油\n"
            "- 採購鋼材\n"
            "- 生產數量"
        ),
        "en": (
            "You do not need to rename your Excel columns first.\n"
            "The system will try to recognize your columns, "
            "then ask you to confirm.\n\n"
            "First time here?\n\n"
            "Prepare one table where each row is an activity, for example:\n"
            "- Purchased electricity\n"
            "- Natural gas\n"
            "- Diesel\n"
            "- Purchased steel\n"
            "- Production quantity"
        ),
    },
    "intake.no_rename": {
        "zh-TW": (
            "不需要先修改原本 Excel 欄位名稱。\n"
            "系統會先嘗試辨識你的欄位，再請你確認是否正確。"
        ),
        "en": (
            "You do not need to rename your Excel columns first.\n"
            "The system will try to recognize your columns, then ask you to confirm."
        ),
    },
    "intake.suggest_sheet_title": {
        "zh-TW": "建議使用工作表",
        "en": "Suggested worksheet",
    },
    "intake.detect_result": {"zh-TW": "偵測結果：", "en": "Detection result:"},
    "intake.use_suggested_sheet": {
        "zh-TW": "使用建議工作表",
        "en": "Use suggested worksheet",
    },
    "intake.choose_other_sheet": {
        "zh-TW": "選擇其他工作表",
        "en": "Choose another worksheet",
    },
    "intake.header_ask": {
        "zh-TW": "哪一列是欄位名稱？",
        "en": "Which row contains the column names?",
    },
    "intake.header_confirm": {
        "zh-TW": "確認欄位名稱列",
        "en": "Confirm header row",
    },
    "intake.header_row_label": {
        "zh-TW": "第 {row} 列",
        "en": "Row {row}",
    },
    "intake.confidence_high": {
        "zh-TW": "系統已辨識",
        "en": "Recognized by the system",
    },
    "intake.confidence_medium": {
        "zh-TW": "請確認",
        "en": "Please confirm",
    },
    "intake.confidence_low": {
        "zh-TW": "需要你選擇",
        "en": "Needs your choice",
    },
    "intake.mapping_unknown": {
        "zh-TW": "我們無法確定這一欄代表什麼。請從下方選擇它的用途。",
        "en": (
            "We could not determine what this column means. "
            "Please choose its purpose below."
        ),
    },
    "intake.map_site": {
        "zh-TW": "廠場／營運據點欄位",
        "en": "Site / operating location column",
    },
    "intake.field.activity_type": {"zh-TW": "活動類型", "en": "Activity type"},
    "intake.field.activity_value": {"zh-TW": "用量", "en": "Quantity"},
    "intake.field.unit": {"zh-TW": "單位", "en": "Unit"},
    "intake.field.site_id": {
        "zh-TW": "廠場／營運據點",
        "en": "Site / operating location",
    },
    "intake.field.start": {"zh-TW": "開始日期", "en": "Start date"},
    "intake.field.end": {"zh-TW": "結束日期", "en": "End date"},
    "intake.field.refrigerant_code": {
        "zh-TW": "冷媒種類",
        "en": "Refrigerant type",
    },
    "intake.field.refill_confirmed": {
        "zh-TW": "補充量已確認",
        "en": "Refill confirmed",
    },
    "intake.field.ownership_control": {
        "zh-TW": "設備控制方式",
        "en": "Equipment control",
    },
    "intake.field.organizational_boundary_status": {
        "zh-TW": "組織盤查邊界",
        "en": "Organizational inventory boundary",
    },
    "intake.field.calculation_method": {
        "zh-TW": "計算方法",
        "en": "Calculation method",
    },
    "intake.field.supplier_name": {
        "zh-TW": "供應商名稱",
        "en": "Supplier name",
    },
    "intake.field.steel_product_type": {
        "zh-TW": "鋼材產品類型",
        "en": "Steel product type",
    },
    "intake.field.product_identifier": {
        "zh-TW": "產品識別",
        "en": "Product identifier",
    },
    "intake.field.emission_factor_value": {
        "zh-TW": "供應商排放係數",
        "en": "Supplier emission factor",
    },
    "intake.field.emission_factor_unit": {
        "zh-TW": "係數單位",
        "en": "Emission factor unit",
    },
    "intake.field.factor_boundary": {
        "zh-TW": "係數邊界",
        "en": "Factor boundary",
    },
    "intake.field.factor_geography": {
        "zh-TW": "係數地理範圍",
        "en": "Factor geography",
    },
    "intake.field.factor_year": {
        "zh-TW": "係數年份",
        "en": "Factor year",
    },
    "intake.field.factor_source_id": {
        "zh-TW": "係數來源",
        "en": "Factor source",
    },
    "intake.field.evidence_reference": {
        "zh-TW": "證據參照",
        "en": "Evidence reference",
    },
    "intake.field.includes_pre_tier1_transport": {
        "zh-TW": "供應鏈上游（pre-Tier-1）運輸涵蓋（來源文件／係數邊界）",
        "en": "Pre-Tier-1 supply-chain transport coverage (source/boundary)",
    },
    "intake.field.includes_inbound_transport": {
        "zh-TW": "含供應商到申報公司入廠運輸（舊欄位）",
        "en": "Includes Tier 1 to reporting-company transport (legacy field)",
    },
    "intake.field.factor_includes_inbound_transport": {
        "zh-TW": (
            "此筆鋼材使用的排放係數，是否包含 Tier 1 供應商到本公司的運輸排放？"
        ),
        "en": (
            "Does the emission factor used for this steel purchase include "
            "transport emissions from the Tier 1 supplier to this company?"
        ),
    },
    "intake.field.transport_control": {
        "zh-TW": "該段運輸工具由誰擁有或控制？",
        "en": "Who owns or controls the vehicle used for that transport?",
    },
    "intake.issue.steel_missing": {
        "zh-TW": "尚缺：{fields}",
        "en": "Still missing: {fields}",
    },
    "intake.issue.steel_no_method": {
        "zh-TW": "請選擇計算方法（供應商特定或平均數據），系統不會依活動名稱推測。",
        "en": (
            "Choose a calculation method (supplier-specific or average-data). "
            "The activity name is not used to infer the method."
        ),
    },
    "intake.issue.steel_inbound": {
        "zh-TW": (
            "此係數包含由第三方承運的 Tier 1 供應商到本公司運輸。"
            "該段應另列 Scope 3 Category 4；在取得不含該段運輸的鋼材係數"
            "或完成拆分前，本列不計入 Category 1。"
        ),
        "en": (
            "This factor includes third-party carriage from the Tier 1 "
            "supplier to this company. That leg belongs in Scope 3 "
            "Category 4. Until a steel factor without that leg, or a split, "
            "is available, this row is not counted in Category 1."
        ),
    },
    "intake.issue.steel_factor_inclusion": {
        "zh-TW": (
            "請確認排放係數是否包含 Tier 1 供應商到本公司的運輸。"
            "此題問的是係數邊界，不是貨物有沒有送到公司。"
        ),
        "en": (
            "Confirm whether the emission factor includes Tier 1 supplier "
            "to this-company transport. This asks about the factor boundary, "
            "not whether the goods were delivered."
        ),
    },
    "intake.issue.steel_transport_control": {
        "zh-TW": (
            "係數已包含該段運輸時，必須確認運輸工具由本公司或第三方擁有或控制。"
            "在確認前不會計算，也不會推測為 Category 4。"
        ),
        "en": (
            "When the factor includes that transport leg, confirm whether "
            "this company or a third party owns or controls the vehicle. "
            "Until then the row is not calculated and Category 4 is not inferred."
        ),
    },
    "intake.issue.steel_average_no_factor": {
        "zh-TW": (
            "目前無符合係數。登錄檔沒有可精確匹配的已核准平均數據係數，"
            "因此本列暫不計算。"
        ),
        "en": (
            "No matching factor. The registry has no unique approved "
            "average-data coefficient for this row, so it is not calculated."
        ),
    },
    "intake.issue.steel_candidate_pending_review": {
        "zh-TW": (
            "已偵測到官方候選係數，但尚未完成適用邊界與版本審查，"
            "因此本列暫不計算。"
        ),
        "en": (
            "Official candidate factors were detected, but applicability "
            "boundary and version review is not complete, so this row "
            "is not calculated yet."
        ),
    },
    "intake.field.source_document_id": {
        "zh-TW": "來源文件編號",
        "en": "Source document id",
    },
    "intake.legend.format_ok": {
        "zh-TW": "格式檢查通過只代表欄位與資料格式可讀，不代表可以開始計算。",
        "en": (
            "Passing the format check only means the columns and values are "
            "readable. It does not mean the row can be calculated yet."
        ),
    },
    "intake.legend.needs_confirm": {
        "zh-TW": "需要確認代表計算所需的業務資料尚未完整，請用下方表單補齊。",
        "en": (
            "Needs confirmation means the business data required for "
            "calculation is still incomplete. Use the form below."
        ),
    },
    "intake.legend.no_factor": {
        "zh-TW": (
            "目前無符合係數代表資料已確認，但登錄檔沒有可用係數，本列暫不計算。"
        ),
        "en": (
            "No matching factor means the row is confirmed, but the registry "
            "has no usable factor, so this row is not calculated."
        ),
    },
    "intake.steel.form.title": {
        "zh-TW": "採購鋼材確認",
        "en": "Purchased steel confirmation",
    },
    "intake.steel.form.help": {
        "zh-TW": (
            "請選擇計算方法並補齊資料。系統不會依「採購鋼材」名稱自動選擇方法，"
            "也不會讓使用者直接選擇 Scope。Scope 3 Category 1 仍由既有規則判定。"
        ),
        "en": (
            "Choose a calculation method and complete the required fields. "
            "The activity name does not select a method, and you cannot "
            "choose Scope here. Scope 3 Category 1 is still decided by "
            "existing rules."
        ),
    },
    "intake.steel.form.record": {
        "zh-TW": "資料列編號",
        "en": "Record id",
    },
    "intake.steel.form.quantity": {
        "zh-TW": "採購量：{quantity} {unit}",
        "en": "Purchased quantity: {quantity} {unit}",
    },
    "intake.steel.form.year": {
        "zh-TW": "盤查年度 {year}／期間 {period}",
        "en": "Reporting year {year} / period {period}",
    },
    "intake.steel.form.no_scope": {
        "zh-TW": "此表單不能選擇 Scope；Category 1 由系統規則判定。",
        "en": "This form does not let you choose Scope; Category 1 is rule-based.",
    },
    "intake.steel.form.transport_help": {
        "zh-TW": (
            "這裡確認的是『排放係數包含哪些排放』，不是確認鋼材是否有送到公司。"
            "供應商以前的上游運輸可包含在 Category 1；"
            "供應商到本公司的運輸需依實際控制方式另外分類。"
        ),
        "en": (
            "This confirms which emissions are inside the emission factor, "
            "not whether the steel was delivered to the company. Upstream "
            "transport before the supplier may already sit in Category 1. "
            "Transport from the supplier to this company is classified by "
            "who owns or controls the vehicle."
        ),
    },
    "intake.steel.form.pre_tier1_help": {
        "zh-TW": (
            "Category 1 使用 cradle-to-gate 係數；其中供應商以前的供應鏈運輸"
            "涵蓋情形由係數來源與系統邊界判定。"
        ),
        "en": (
            "Category 1 uses a cradle-to-gate factor. Whether transport "
            "before the supplier is covered is determined by the factor "
            "source and system boundary."
        ),
    },
    "intake.steel.method.undecided": {
        "zh-TW": "尚不確定",
        "en": "Not sure yet",
    },
    "intake.steel.method.undecided_help": {
        "zh-TW": "尚未選擇計算方法前，本列不能繼續計算。",
        "en": "This row cannot be calculated until a method is chosen.",
    },
    "intake.steel.method.supplier_specific": {
        "zh-TW": "供應商特定資料",
        "en": "Supplier-specific data",
    },
    "intake.steel.method.average_data": {
        "zh-TW": "平均數據",
        "en": "Average data",
    },
    "intake.steel.answer.unconfirmed": {
        "zh-TW": "尚未確認",
        "en": "Not yet confirmed",
    },
    "intake.steel.answer.yes": {"zh-TW": "是", "en": "Yes"},
    "intake.steel.answer.no": {"zh-TW": "否", "en": "No"},
    "intake.steel.answer.included": {"zh-TW": "包含", "en": "Included"},
    "intake.steel.answer.excluded": {"zh-TW": "不包含", "en": "Not included"},
    "intake.steel.control.reporting_company": {
        "zh-TW": "本公司擁有或控制",
        "en": "Owned or controlled by this company",
    },
    "intake.steel.control.third_party": {
        "zh-TW": "第三方擁有或控制",
        "en": "Owned or controlled by a third party",
    },
    "intake.steel.boundary.cradle_to_gate": {
        "zh-TW": "確認為搖籃到大門（cradle_to_gate）",
        "en": "Confirm cradle-to-gate",
    },
    "intake.steel.average.help": {
        "zh-TW": (
            "平均數據只能使用登錄檔中產品、地理範圍、cradle-to-gate 邊界"
            "及有效期間完全符合的係數，不會使用上傳列中的任意係數，"
            "也不會自動挑選最新版本。"
        ),
        "en": (
            "Average data uses only a registry factor that matches product, "
            "geography, cradle-to-gate boundary, and validity period. "
            "Uploaded factor values are not used, and the newest version "
            "is not selected automatically."
        ),
    },
    "intake.steel.field.reporting_year": {
        "zh-TW": "盤查年度",
        "en": "Reporting year",
    },
    "intake.steel.field.factor_year": {
        "zh-TW": "係數年份",
        "en": "Factor year",
    },
    "intake.steel.field.technology": {
        "zh-TW": "製程／技術",
        "en": "Process / technology",
    },
    "intake.steel.catalog.factors": {
        "zh-TW": "目前可匹配的已核准平均數據係數",
        "en": "Approved average-data factors that can match",
    },
    "intake.steel.catalog.product": {
        "zh-TW": "產品名稱",
        "en": "Product name",
    },
    "intake.steel.catalog.value": {
        "zh-TW": "係數值與單位",
        "en": "Factor value and unit",
    },
    "intake.steel.catalog.declared_unit": {
        "zh-TW": "提供／登錄單位",
        "en": "Declared / registry unit",
    },
    "intake.steel.catalog.version": {
        "zh-TW": "版本",
        "en": "Version",
    },
    "intake.steel.catalog.boundary": {
        "zh-TW": "邊界",
        "en": "Boundary",
    },
    "intake.steel.catalog.geography": {
        "zh-TW": "地理範圍",
        "en": "Geography",
    },
    "intake.steel.catalog.source": {
        "zh-TW": "來源連結",
        "en": "Source URL",
    },
    "intake.steel.catalog.period": {
        "zh-TW": "適用期間（內部核准）",
        "en": "Applicability period (internally approved)",
    },
    "intake.steel.catalog.secondary": {
        "zh-TW": "是否為二次／代理數據",
        "en": "Secondary / proxy data",
    },
    "intake.steel.save": {
        "zh-TW": "儲存並重新分析",
        "en": "Save and re-analyse",
    },
    "intake.steel.edit": {
        "zh-TW": "修改鋼材計算資料",
        "en": "Edit steel calculation data",
    },
    "intake.steel.edit.help": {
        "zh-TW": (
            "同一筆資料仍可改選供應商特定資料或其他平均數據條件。"
            "不會新增列，也不會套用到其他檔案、年度或期間。"
        ),
        "en": (
            "You can still switch this same row to supplier-specific data "
            "or different average-data fields. This does not create a new "
            "record or reuse the confirmation on another file, year, or period."
        ),
    },
    "intake.steel.error.incomplete": {
        "zh-TW": "必要資料尚未完整，本列維持需要確認，不會開始計算。",
        "en": (
            "Required data is still incomplete. This row stays in needs "
            "confirmation and is not calculated."
        ),
    },
    "intake.steel.error.method": {
        "zh-TW": "請先選擇計算方法。尚未選擇前不能繼續計算。",
        "en": "Choose a calculation method before this row can be calculated.",
    },
    "intake.steel.error.identity": {
        "zh-TW": "缺少目前檔案、資料列或盤查期間資訊，無法儲存確認。",
        "en": (
            "The current file, record, or reporting period is missing, "
            "so this confirmation cannot be saved."
        ),
    },
    "intake.steel.error.file": {
        "zh-TW": "確認資料必須綁定目前上傳檔案，不能套用到其他檔案。",
        "en": (
            "Confirmation data must be bound to the current upload "
            "and cannot be applied to another file."
        ),
    },
    "intake.steel.error.inbound": {
        "zh-TW": (
            "請確認排放係數是否包含 Tier 1 供應商到本公司的運輸。"
            "尚未確認前不能開始計算。"
        ),
        "en": (
            "Confirm whether the emission factor includes Tier 1 supplier "
            "to this-company transport before this row can be calculated."
        ),
    },
    "intake.steel.error.control": {
        "zh-TW": (
            "係數已包含該段運輸時，請確認運輸工具由本公司或第三方擁有或控制。"
        ),
        "en": (
            "When the factor includes that transport, confirm whether this "
            "company or a third party owns or controls the vehicle."
        ),
    },
    "intake.steel.error.supplier": {
        "zh-TW": "供應商特定法需要供應商名稱。",
        "en": "The supplier-specific method requires a supplier name.",
    },
    "intake.steel.error.product": {
        "zh-TW": "需要鋼材產品類型或產品識別。",
        "en": "A steel product type or product identifier is required.",
    },
    "intake.steel.error.factor_value": {
        "zh-TW": "需要供應商排放係數。缺值不會當成 0。",
        "en": "A supplier emission factor is required. Missing values are not 0.",
    },
    "intake.steel.error.factor_unit": {
        "zh-TW": "需要明確的係數單位，例如 tCO2e/t。",
        "en": "An explicit factor unit such as tCO2e/t is required.",
    },
    "intake.steel.error.boundary": {
        "zh-TW": "請確認係數邊界為搖籃到大門（cradle_to_gate）。",
        "en": "Confirm that the factor boundary is cradle-to-gate.",
    },
    "intake.steel.error.factor_year": {
        "zh-TW": "供應商特定法需要係數年份，系統不會用盤查年度補上。",
        "en": (
            "The supplier-specific method requires factor year. "
            "Reporting year is not substituted."
        ),
    },
    "intake.steel.error.evidence": {
        "zh-TW": "請提供係數來源、證據參照或來源文件編號至少一項。",
        "en": (
            "Provide at least one of factor source, evidence reference, "
            "or source document id."
        ),
    },
    "intake.steel.error.geography": {
        "zh-TW": "平均數據法需要係數地理範圍。",
        "en": "Average data requires factor geography.",
    },
    "intake.steel.error.reporting_year": {
        "zh-TW": "平均數據法需要可確認的盤查年度。",
        "en": "Average data requires a confirmed reporting year.",
    },
    "intake.field.year_month": {
        "zh-TW": "年月（月報期間）",
        "en": "Year-month (monthly period)",
    },
    "intake.dates_year_month": {
        "zh-TW": "使用檔案中的年月欄位",
        "en": "Use a year-month column in the file",
    },
    "intake.map_year_month": {
        "zh-TW": "年月欄位",
        "en": "Year-month column",
    },
    "intake.year_month_preview_title": {
        "zh-TW": "系統將轉換為：",
        "en": "The system will convert this to:",
    },
    "intake.year_month_confirm": {
        "zh-TW": "確認此年月轉換",
        "en": "Confirm this year-month conversion",
    },
    "intake.reference_only_note": {
        "zh-TW": (
            "檔案中的「排放係數／排放量／計算結果」欄位僅供參考，"
            "不會當作本系統的計算依據。"
        ),
        "en": (
            "Uploaded emission-factor / emission-result columns are reference only "
            "and are not used as this system's calculation truth."
        ),
    },
    "intake.mapping_preview": {
        "zh-TW": "欄位對應建議",
        "en": "Suggested column mappings",
    },
    "intake.interpret.title": {
        "zh-TW": "資料已讀取",
        "en": "File read successfully",
    },
    "intake.interpret.intro": {
        "zh-TW": "我們會這樣讀取你的資料：",
        "en": "Here is how we will read your data:",
    },
    "intake.interpret.activity_type": {
        "zh-TW": (
            "用來判斷每筆資料是外購電力、天然氣、柴油或其他活動。"
        ),
        "en": (
            "Used to tell whether each row is purchased electricity, "
            "natural gas, diesel, or another activity."
        ),
    },
    "intake.interpret.activity_value": {
        "zh-TW": "作為每筆活動的實際數量。",
        "en": "Used as the actual quantity for each activity.",
    },
    "intake.interpret.unit": {
        "zh-TW": "作為 kWh、m³、L、kg、t 等計量單位。",
        "en": "Used as the unit of measure, such as kWh, m³, L, kg, or t.",
    },
    "intake.interpret.site_id": {
        "zh-TW": "用來區分資料所屬的廠場或營運據點。",
        "en": "Used to tell which site / operating location each row belongs to.",
    },
    "intake.interpret.year_month": {
        "zh-TW": (
            "用來建立每筆活動的資料期間。\n"
            "例如 {example} 會轉成 {start} ～ {end}。"
        ),
        "en": (
            "Used to build the reporting period for each activity.\n"
            "For example, {example} becomes {start} – {end}."
        ),
    },
    "intake.interpret.start": {
        "zh-TW": "作為每筆活動的開始日期。",
        "en": "Used as the start date for each activity.",
    },
    "intake.interpret.end": {
        "zh-TW": "作為每筆活動的結束日期。",
        "en": "Used as the end date for each activity.",
    },
    "intake.interpret.ask": {
        "zh-TW": "請確認系統對這份檔案的理解",
        "en": "Please confirm how the system read this file",
    },
    "intake.interpret.need_help": {
        "zh-TW": (
            "有些欄位我們還不確定，需要你幫忙確認後才能繼續。"
        ),
        "en": (
            "Some columns are still unclear. "
            "Please adjust them before continuing."
        ),
    },
    "intake.btn.accept": {
        "zh-TW": "確認並繼續",
        "en": "Confirm and continue",
    },
    "intake.btn.accept_help": {
        "zh-TW": "確認目前的讀取結果，繼續檢查資料。",
        "en": "Confirm the current reading and continue to data checks.",
    },
    "intake.btn.fix": {
        "zh-TW": "修改系統辨識結果",
        "en": "Edit recognition results",
    },
    "intake.btn.fix_help": {
        "zh-TW": "調整系統對檔案欄位的理解。",
        "en": "Adjust how the system reads your file columns.",
    },
    "intake.btn.validate_help": {
        "zh-TW": "只檢查資料能否轉成系統格式，不會開始計算碳排。",
        "en": (
            "Only checks whether the data can become the system format. "
            "It will not start carbon calculation."
        ),
    },
    "intake.btn.continue_help": {
        "zh-TW": "查看系統如何讀取你的 Excel 欄位。",
        "en": "See how the system will read your Excel columns.",
    },
    "intake.btn.use_sheet_help": {
        "zh-TW": "使用建議的工作表繼續讀取資料。",
        "en": "Continue using the suggested worksheet.",
    },
    "intake.btn.other_sheet_help": {
        "zh-TW": "改選其他工作表。",
        "en": "Pick a different worksheet instead.",
    },
    "intake.btn.header_help": {
        "zh-TW": "確認哪一列是欄位名稱，然後繼續。",
        "en": "Confirm which row has the column names, then continue.",
    },
    "intake.btn.show_advanced": {
        "zh-TW": "顯示進階設定",
        "en": "Show advanced settings",
    },
    "intake.btn.show_advanced_help": {
        "zh-TW": "查看系統欄位格式與其他進階選項。",
        "en": "View system field format and other advanced options.",
    },
    "intake.advanced_canonical": {
        "zh-TW": "進階：查看系統欄位格式",
        "en": "Advanced: system field format",
    },
    "intake.step1": {
        "zh-TW": "01 上傳活動資料",
        "en": "01 Upload activity data",
    },
    "intake.step2": {
        "zh-TW": "02 確認資料辨識",
        "en": "02 Confirm data recognition",
    },
    "intake.step3": {
        "zh-TW": "03 檢查計算範圍",
        "en": "03 Review calculation coverage",
    },
    "intake.step4": {
        "zh-TW": "04 查看排放結果",
        "en": "04 View emissions results",
    },
    "intake.journey.upload": {"zh-TW": "上傳資料", "en": "Upload data"},
    "intake.journey.confirm": {
        "zh-TW": "確認資料辨識",
        "en": "Confirm data recognition",
    },
    "intake.journey.results": {"zh-TW": "查看分析結果", "en": "View analysis results"},
    "intake.upload_priority": {
        "zh-TW": "上傳公司現有資料",
        "en": "Upload your company’s existing data",
    },
    "intake.understood": {
        "zh-TW": "資料已讀取",
        "en": "File read successfully",
    },
    "intake.upload_label": {
        "zh-TW": "選擇公司檔案",
        "en": "Choose a company file",
    },
    "intake.upload_help": {
        "zh-TW": "支援 CSV、XLSX。單一檔案最大 10 MB。",
        "en": "CSV and XLSX. Maximum 10 MB per file.",
    },
    "intake.template_button": {
        "zh-TW": "還沒有資料檔？下載範例",
        "en": "Don’t have a data file yet? Download an example.",
    },
    "intake.template_fallback": {
        "zh-TW": "還沒有資料檔？下載範例",
        "en": "Don’t have a data file yet? Download an example.",
    },
    "intake.example_button": {
        "zh-TW": "下載範例檔 (.csv)",
        "en": "Download example file (.csv)",
    },
    "intake.example_label": {
        "zh-TW": "範例資料，不會自動匯入",
        "en": "Example data only; it is not imported automatically.",
    },
    "intake.col_help_activity_type": {
        "zh-TW": "activity_type：活動類型，例如外購電力、天然氣、柴油、採購鋼材",
        "en": (
            "activity_type: activity type, e.g. purchased electricity, "
            "natural gas, diesel, purchased steel"
        ),
    },
    "intake.col_help_activity_value": {
        "zh-TW": "activity_value：實際數量或用量",
        "en": "activity_value: the actual quantity or usage amount",
    },
    "intake.col_help_unit": {
        "zh-TW": "unit：單位，例如 kWh、m3、L、t",
        "en": "unit: unit of measure, e.g. kWh, m3, L, t",
    },
    "intake.col_help_start": {
        "zh-TW": "activity_start_date：資料期間開始日",
        "en": "activity_start_date: reporting period start date",
    },
    "intake.col_help_end": {
        "zh-TW": "activity_end_date：資料期間結束日",
        "en": "activity_end_date: reporting period end date",
    },
    "intake.preview_title": {"zh-TW": "檔案預覽", "en": "File preview"},
    "intake.file_name": {"zh-TW": "檔名", "en": "File name"},
    "intake.file_type": {"zh-TW": "檔案類型", "en": "File type"},
    "intake.row_count": {"zh-TW": "列數", "en": "Rows"},
    "intake.col_count": {"zh-TW": "欄數", "en": "Columns"},
    "intake.sheet_label": {"zh-TW": "選擇工作表", "en": "Choose worksheet"},
    "intake.sheet_name": {"zh-TW": "工作表", "en": "Worksheet"},
    "intake.err_too_large": {
        "zh-TW": "檔案太大。\n目前單一檔案上限為 10 MB。",
        "en": "The file is too large.\nThe current limit is 10 MB per file.",
    },
    "intake.err_encoding": {
        "zh-TW": "請將 CSV 另存為 UTF-8 編碼後再上傳。",
        "en": "Please re-save the CSV as UTF-8 and upload again.",
    },
    "intake.err_unsupported": {
        "zh-TW": "目前僅支援 CSV 與 XLSX 檔案。",
        "en": "Only CSV and XLSX files are supported right now.",
    },
    "intake.map_activity_type": {
        "zh-TW": "活動類型欄位",
        "en": "Activity type column",
    },
    "intake.map_activity_value": {
        "zh-TW": "用量欄位",
        "en": "Quantity column",
    },
    "intake.map_unit": {"zh-TW": "單位欄位", "en": "Unit column"},
    "intake.dates_in_file": {
        "zh-TW": "日期在檔案欄位中",
        "en": "Dates are in file columns",
    },
    "intake.dates_period": {
        "zh-TW": "使用同一資料期間",
        "en": "Use one reporting period",
    },
    "intake.map_start": {"zh-TW": "開始日期欄位", "en": "Start date column"},
    "intake.map_end": {"zh-TW": "結束日期欄位", "en": "End date column"},
    "intake.period_start": {"zh-TW": "開始日期", "en": "Start date"},
    "intake.period_end": {"zh-TW": "結束日期", "en": "End date"},
    "intake.value_map_activity": {
        "zh-TW": "活動類型對應",
        "en": "Activity type mapping",
    },
    "intake.ng_type": {"zh-TW": "天然氣類型", "en": "Natural-gas type"},
    "intake.ng_type_help": {
        "zh-TW": (
            "NG1 與 NG2 的官方年度熱值不同，因此需要確認類型後才能完成計算。"
        ),
        "en": (
            "NG1 and NG2 have different official annual heating values, "
            "so the type must be confirmed before calculation can finish."
        ),
    },
    "intake.ng_type_unknown": {
        "zh-TW": "還不確定（此列暫不計算）",
        "en": "Not sure yet (this row will not be calculated for now)",
    },
    "intake.ng_learn_title": {
        "zh-TW": "什麼是 NG1 / NG2？",
        "en": "What are NG1 and NG2?",
    },
    "intake.ng_learn_body": {
        "zh-TW": (
            "環境部公布的年度天然氣熱值分為 NG1 與 NG2，"
            "兩者熱值不同，因此盤查時需要確認公司使用的類型。"
        ),
        "en": (
            "MOENV publishes annual natural-gas heating values as NG1 and NG2. "
            "The values differ, so inventory work needs the company type."
        ),
    },
    "intake.ng_type_from_file": {
        "zh-TW": "檔案中已標示 NG1／NG2 的列會優先保留原值。",
        "en": "Rows that already name NG1/NG2 keep that source value.",
    },
    "intake.map_ng_type_column": {
        "zh-TW": "天然氣類型欄位（選填）",
        "en": "Natural-gas type column (optional)",
    },
    "intake.interpret.fuel_subtype": {
        "zh-TW": "這欄看起來是天然氣類型。",
        "en": "This column looks like the natural-gas type.",
    },
    "intake.diesel_context": {
        "zh-TW": "柴油用途",
        "en": "Diesel context",
    },
    "intake.diesel_company_vehicle": {
        "zh-TW": "公司車輛／公司控制的移動燃燒",
        "en": "Company vehicle / company-controlled mobile combustion",
    },
    "intake.diesel_context_help": {
        "zh-TW": (
            "目前僅在公司車輛移動燃燒路徑計算柴油。"
            "若無法確認，此筆活動將暫不納入計算。"
        ),
        "en": (
            "Diesel is currently calculated only for company-vehicle "
            "mobile combustion. Unconfirmed rows stay out of the total."
        ),
    },
    "intake.electricity_context": {
        "zh-TW": "電力盤查類型",
        "en": "Electricity inventory type",
    },
    "intake.electricity_enterprise": {
        "zh-TW": "這是公司營運使用的外購電力",
        "en": "This is purchased electricity used for company operations",
    },
    "intake.electricity_context_help": {
        "zh-TW": (
            "請確認這是公司營運使用的外購電力。"
            "系統不會只因為單位是 kWh 就當成 Scope 2。"
            "確認後才會納入企業盤查並計算。"
        ),
        "en": (
            "Confirm this is purchased electricity used for company operations. "
            "kWh alone is not treated as Scope 2. Calculation starts only after "
            "this confirmation."
        ),
    },
    "intake.review.ready": {
        "zh-TW": "可納入計算",
        "en": "Included in calculation",
    },
    "intake.review.needs_confirm": {
        "zh-TW": "需要確認",
        "en": "Needs confirmation",
    },
    "intake.review.unsupported": {
        "zh-TW": "目前不支援",
        "en": "Currently unsupported",
    },
    "intake.review.no_factor": {
        "zh-TW": "目前無符合係數",
        "en": "No matching factor",
    },
    "intake.value_map_unit": {"zh-TW": "單位對應", "en": "Unit mapping"},
    "intake.choose": {"zh-TW": "請選擇", "en": "Please choose"},
    "intake.source_name": {"zh-TW": "資料來源名稱", "en": "Source name"},
    "intake.site_name": {"zh-TW": "廠場／營運據點", "en": "Site / operating location"},
    "intake.site_id": {"zh-TW": "廠場／營運據點", "en": "Site / operating location"},
    "intake.site_placeholder": {
        "zh-TW": "例如：高雄廠、台中辦公室、第一倉庫",
        "en": "e.g. Kaohsiung plant, Taichung office, Warehouse 1",
    },
    "intake.site_unconfirmed": {
        "zh-TW": "待確認",
        "en": "Needs confirmation",
    },
    "intake.document_date": {"zh-TW": "文件日期", "en": "Document date"},
    "intake.data_quality": {"zh-TW": "資料品質", "en": "Data quality"},
    "intake.quality.primary": {
        "zh-TW": "公司原始紀錄",
        "en": "Primary company record",
    },
    "intake.quality.secondary": {"zh-TW": "二級資料", "en": "Secondary data"},
    "intake.quality.estimated": {"zh-TW": "估算資料", "en": "Estimated data"},
    "intake.quality.unknown": {"zh-TW": "不確定", "en": "Unknown"},
    "intake.confirm_title": {
        "zh-TW": "確認匯入資料",
        "en": "Confirm imported data",
    },
    "intake.advanced": {"zh-TW": "進階欄位", "en": "Advanced fields"},
    "intake.col.activity": {"zh-TW": "活動", "en": "Activity"},
    "intake.col.amount": {"zh-TW": "用量", "en": "Quantity"},
    "intake.col.unit": {"zh-TW": "單位", "en": "Unit"},
    "intake.col.start": {"zh-TW": "開始日期", "en": "Start date"},
    "intake.col.end": {"zh-TW": "結束日期", "en": "End date"},
    "intake.col.status": {"zh-TW": "狀態", "en": "Status"},
    "intake.col.issue": {"zh-TW": "問題", "en": "Issue"},
    "intake.col.quality": {"zh-TW": "資料品質", "en": "Data quality"},
    "intake.col.review": {
        "zh-TW": "需要人工確認",
        "en": "Needs human review",
    },
    "intake.result_accepted": {
        "zh-TW": "可納入計算",
        "en": "Included in calculation",
    },
    "intake.result_rejected": {
        "zh-TW": "無法納入",
        "en": "Excluded from calculation",
    },
    "intake.result_needs_confirm": {
        "zh-TW": "需要確認",
        "en": "Needs confirmation",
    },
    "intake.result_unsupported": {
        "zh-TW": "目前不支援",
        "en": "Currently unsupported",
    },
    "intake.result_no_factor": {
        "zh-TW": "目前無符合係數",
        "en": "No matching factor",
    },
    "intake.result_invalid": {
        "zh-TW": "格式錯誤",
        "en": "Invalid data",
    },
    "intake.issue.context_required": {
        "zh-TW": "需要補充活動內容或盤查情境後才能計算。",
        "en": "Activity context or inventory treatment must be confirmed.",
    },
    "intake.issue.unsupported_activity": {
        "zh-TW": "此活動類型目前尚未提供排放計算；原始資料仍會保留。",
        "en": (
            "Calculation is not yet available for this activity type; "
            "the source row is retained."
        ),
    },
    "intake.unsupported.summary": {
        "zh-TW": "目前不支援的活動：{names}。資料會保留，但不會計入排放量。",
        "en": (
            "Currently unsupported activities: {names}. Source rows are "
            "retained but excluded from emissions totals."
        ),
    },
    "intake.empty.ready": {
        "zh-TW": "目前沒有可直接計算的資料。",
        "en": "No rows are ready for calculation.",
    },
    "intake.empty.needs_confirm": {
        "zh-TW": "目前沒有需要確認的資料。",
        "en": "No rows need confirmation.",
    },
    "intake.empty.unsupported": {
        "zh-TW": "目前沒有產品尚未支援的活動類型。",
        "en": "No rows use currently unsupported activity types.",
    },
    "intake.empty.no_factor": {
        "zh-TW": "目前沒有已確認但缺少符合係數的資料。",
        "en": "No confirmed rows are waiting on a matching factor.",
    },
    "intake.empty.invalid": {
        "zh-TW": "目前沒有格式錯誤的資料。",
        "en": "No rows have data-format errors.",
    },
    "intake.result_total": {"zh-TW": "總筆數", "en": "Total rows"},
    "intake.success": {
        "zh-TW": "資料格式檢查完成。",
        "en": "Data-format checks completed.",
    },
    "intake.dup.title": {
        "zh-TW": "發現可能重複的資料",
        "en": "Possible duplicate records found",
    },
    "intake.dup.body": {
        "zh-TW": (
            "發現 {count} 組可能重複的活動資料。\n"
            "重複資料可能造成排放量重複計算，請先確認。"
        ),
        "en": (
            "Found {count} possible duplicate activity group(s).\n"
            "Duplicates can double-count emissions. Please confirm first."
        ),
    },
    "intake.dup.review": {
        "zh-TW": "查看並確認",
        "en": "Review and confirm",
    },
    "intake.dup.keep_all": {
        "zh-TW": "這是不同的真實紀錄 → 保留全部",
        "en": "These are different real records — keep all",
    },
    "intake.dup.exclude": {
        "zh-TW": "這是重複匯入 → 排除重複列",
        "en": "This is a duplicate import — exclude duplicate rows",
    },
    "intake.dup.group": {
        "zh-TW": "第 {n} 組",
        "en": "Group {n}",
    },
    "intake.dup.file_row": {
        "zh-TW": "檔案列次",
        "en": "File row",
    },
    "intake.dup.context": {
        "zh-TW": "燃料／活動內容",
        "en": "Fuel / activity context",
    },
    "intake.dup.blocked": {
        "zh-TW": "請先確認可能重複的資料，才能開始分析。",
        "en": "Confirm possible duplicates before starting analysis.",
    },
    "intake.dup.exclude_note": {
        "zh-TW": "將保留檔案中的第一筆，排除其餘重複列。原始資料仍會保存。",
        "en": (
            "The first file row is kept and later lookalike rows are "
            "excluded. Original imported rows are preserved."
        ),
    },
    "intake.dup.keep_note": {
        "zh-TW": "這些列都會納入計算。",
        "en": "All of these rows will be included in the calculation.",
    },
    "intake.dup.confirmed": {
        "zh-TW": "可能重複的資料已確認。",
        "en": "Possible duplicates have been confirmed.",
    },
    "intake.partial": {
        "zh-TW": "有部分資料需要修正。",
        "en": "Some rows need correction.",
    },
    "intake.rejected_title": {
        "zh-TW": "需要修正的資料",
        "en": "Rows that need correction",
    },
    "intake.rej.row": {"zh-TW": "原始列", "en": "Source row"},
    "intake.rej.field": {"zh-TW": "欄位", "en": "Field"},
    "intake.rej.issue": {"zh-TW": "問題", "en": "Issue"},
    "intake.rej.value": {"zh-TW": "目前值", "en": "Current value"},
    "intake.next_phase": {
        "zh-TW": (
            "資料已準備完成。下一步可使用這批資料開始排放計算與準則分析。"
        ),
        "en": (
            "Data is ready. Next, analyze this batch for emissions "
            "calculation and framework checks."
        ),
    },
    "intake.ready_title": {
        "zh-TW": "資料已準備完成 ✓",
        "en": "Data is ready ✓",
    },
    "intake.ready_body": {
        "zh-TW": "{count} 筆資料已通過格式檢查。",
        "en": "{count} records passed format checks.",
    },
    "intake.ready_next": {
        "zh-TW": (
            "下一步，系統會使用這批資料進行排放計算、資料缺口檢查與準則分析。"
        ),
        "en": (
            "Next, the system will use this batch for emissions calculation, "
            "gap checks, and framework analysis."
        ),
    },
    "intake.review.rows": {"zh-TW": "資料筆數", "en": "Record count"},
    "intake.review.period": {"zh-TW": "報導期間", "en": "Reporting period"},
    "intake.review.period_to": {"zh-TW": "至", "en": "to"},
    "intake.review.activity_types": {"zh-TW": "活動類型", "en": "Activity types"},
    "intake.review.pending": {"zh-TW": "待確認資料", "en": "Rows needing review"},
    "intake.start_analysis": {
        "zh-TW": "使用這批資料開始分析",
        "en": "Analyze this uploaded dataset",
    },
    "intake.back_edit": {"zh-TW": "返回修改資料", "en": "Back to edit data"},
    "intake.demo_notice": {
        "zh-TW": "上傳並完成資料確認後，即可使用公司資料進行分析。",
        "en": (
            "After upload and data confirmation, you can analyze "
            "using your company data."
        ),
    },
    "intake.upload_notice": {
        "zh-TW": "上傳並完成資料確認後，即可使用公司資料進行分析。",
        "en": (
            "After upload and data confirmation, you can analyze "
            "using your company data."
        ),
    },
    "intake.document_date_required": {
        "zh-TW": "請確認文件日期。系統不會把「不知道」自動填成今天。",
        "en": (
            "Please confirm the document date. "
            "Unknown must not become today's date."
        ),
    },
    "act.trace_activity": {"zh-TW": "活動量", "en": "Activity amount"},
    "act.trace_factor": {"zh-TW": "使用排放係數", "en": "Emission factor used"},
    "act.trace_factor_year": {"zh-TW": "係數年度", "en": "Factor year"},
    "act.trace_calc": {"zh-TW": "計算", "en": "Calculation"},
    "act.trace_source": {"zh-TW": "來源", "en": "Source"},
    "act.trace_source_official": {
        "zh-TW": "官方同步參考資料",
        "en": "Official synced reference",
    },
    "act.trace_source_demo": {
        "zh-TW": "示範參考資料",
        "en": "Demo reference data",
    },
    "intake.run_validation": {
        "zh-TW": "資料格式檢查",
        "en": "Check data format",
    },
    "intake.continue_mapping": {
        "zh-TW": "繼續",
        "en": "Continue",
    },
    "fw.purpose_ghg": {
        "zh-TW": "把公司活動分類到 Scope 1、2、3 或不適用。",
        "en": "Classifies corporate activities into Scope 1, 2, 3, or not applicable.",
    },
    "fw.purpose_cbam": {
        "zh-TW": "對合成 CN 7318 情境對應資料角色與缺口。",
        "en": "Maps activities to data roles for the synthetic CN 7318 scenario.",
    },
    "fw.purpose_ifrs": {
        "zh-TW": "只評估氣候指標相關證據的技術準備度。",
        "en": "Assesses technical climate-metrics evidence readiness only.",
    },
    # Stage 2 IA shells
    "app.needs_information": {
        "zh-TW": "需要更多資訊",
        "en": "Needs information",
    },
    "app.rule_not_implemented": {
        "zh-TW": "規則集尚未實作",
        "en": "Rule set not yet implemented",
    },
    "app.coming_next_stage": {
        "zh-TW": "將於下一實作階段補齊",
        "en": "Coming in the next implementation stage",
    },
    "app.applicable": {"zh-TW": "適用", "en": "Applicable"},
    "app.not_applicable": {"zh-TW": "不適用", "en": "Not applicable"},
    "app.future_requirement": {
        "zh-TW": "未來要求",
        "en": "Future requirement",
    },
    "apl.title": {
        "zh-TW": "你的公司適用哪些要求？",
        "en": "Which requirements apply to your company?",
    },
    "apl.subtitle": {
        "zh-TW": (
            "輸入統一編號，我們會從目前的官方公司資料中尋找，"
            "再整理與公司相關的 IFRS 與台灣溫室氣體要求。"
        ),
        "en": (
            "Enter the unified business number. We search the current official "
            "company data, then list related IFRS and Taiwan GHG requirements."
        ),
    },
    "apl.help": {
        "zh-TW": (
            "公司資料不足時會顯示「需要更多資料」，不會臆測適用結論。"
            "此判定僅供合規準備，必要時應再經專業判斷。"
        ),
        "en": (
            "When company data is incomplete, the status is Needs "
            "information — never guessed. This assessment supports preparation "
            "and should be reviewed where professional judgement is required."
        ),
    },
    "apl.company_profile": {
        "zh-TW": "公司基本資料",
        "en": "Company basics",
    },
    "apl.company_profile_help": {
        "zh-TW": "先填寫公司是誰與報導年度；其餘欄位依公司類型逐步顯示。",
        "en": (
            "Start with who the company is and the reporting year; other fields "
            "appear based on entity type."
        ),
    },
    "apl.section.entity": {
        "zh-TW": "公司類型與上市狀態",
        "en": "Entity type and market status",
    },
    "apl.section.finance": {"zh-TW": "財務資料", "en": "Financial facts"},
    "apl.section.group": {
        "zh-TW": "集團與報導邊界",
        "en": "Group and reporting boundary",
    },
    "apl.section.industry": {"zh-TW": "產業", "en": "Industry"},
    "apl.section.facilities": {
        "zh-TW": "台灣廠場與環境資訊",
        "en": "Taiwan facilities and environmental context",
    },
    "apl.section.results": {"zh-TW": "判定結果", "en": "Assessment results"},
    "apl.save_profile": {
        "zh-TW": "儲存公司資料",
        "en": "Save company details",
    },
    "apl.edit_profile": {
        "zh-TW": "修改公司資料",
        "en": "Edit company details",
    },
    "apl.run_assessment": {
        "zh-TW": "進行適用性判定",
        "en": "Run applicability assessment",
    },
    "apl.saved_ok": {
        "zh-TW": "公司資料已儲存於本次工作階段。",
        "en": "Company details saved for this session.",
    },
    "apl.why": {"zh-TW": "為什麼？", "en": "Why?"},
    "apl.when": {"zh-TW": "何時開始？", "en": "When does it start?"},
    "apl.missing": {"zh-TW": "缺少哪些資料？", "en": "What is missing?"},
    "apl.next": {"zh-TW": "下一步", "en": "Next action"},
    "apl.view_basis": {
        "zh-TW": "查看法規依據",
        "en": "View regulatory basis",
    },
    "apl.effective_year": {
        "zh-TW": "適用報導年度",
        "en": "Effective reporting year",
    },
    "apl.first_filing_year": {
        "zh-TW": "首次申報／揭露年度",
        "en": "First filing year",
    },
    "apl.disclaimer": {
        "zh-TW": (
            "依目前公司資料與已驗證法規規則判定，僅供合規準備參考；"
            "需要專業判斷處請再人工檢視。"
        ),
        "en": (
            "Based on the current company details and verified regulatory rules. "
            "This supports compliance preparation and should be reviewed where "
            "professional judgement is required."
        ),
    },
    "apl.field.company_name": {"zh-TW": "公司名稱", "en": "Company name"},
    "apl.field.reporting_year": {
        "zh-TW": "要評估哪一年度？",
        "en": "Which year should we assess?",
    },
    "apl.field.reporting_year_help": {
        "zh-TW": "例如：評估 2026 年公司需要準備哪些要求。",
        "en": "Example: which requirements the company should prepare for in 2026.",
    },
    "apl.field.reporting_year_professional": {
        "zh-TW": "專業上稱為報導年度。",
        "en": "Professionally this is the reporting year.",
    },
    "apl.field.entity_type": {"zh-TW": "公司類型", "en": "Entity type"},
    "apl.field.listing_status": {
        "zh-TW": "公司是否上市／上櫃？",
        "en": "Is the company listed / OTC?",
    },
    "apl.field.paid_in_capital_twd": {
        "zh-TW": "實收資本額（新台幣）",
        "en": "Paid-in capital (TWD)",
    },
    "apl.field.net_worth_twd": {"zh-TW": "淨值（新台幣）", "en": "Net worth (TWD)"},
    "apl.field.is_fhc_subsidiary": {
        "zh-TW": "是否為金融控股公司子公司",
        "en": "Is a financial-holding-company subsidiary?",
    },
    "apl.field.has_taiwan_facilities": {
        "zh-TW": "是否有台灣廠場／營運據點",
        "en": "Has Taiwan facilities / operations?",
    },
    "apl.field.received_environmental_authority_inventory_notice": {
        "zh-TW": "是否曾收到環境主管機關要求盤查或登錄溫室氣體的通知",
        "en": (
            "Has the company received an environmental-authority GHG inventory "
            "or registration notice?"
        ),
    },
    "apl.field.received_authority_notice": {
        "zh-TW": "公司是否曾收到主管機關要求盤查、登錄或查驗溫室氣體的通知？",
        "en": (
            "Has the company received an authority notice requiring GHG "
            "inventory, registration, or verification?"
        ),
    },
    "apl.field.received_verification_requirement": {
        "zh-TW": "是否曾收到查驗／確信要求",
        "en": "Has the company received a verification requirement?",
    },
    "apl.field.known_regulated_facility": {
        "zh-TW": "是否已知有列管廠場",
        "en": "Known regulated facility?",
    },
    "apl.field.reporting_entities_known": {
        "zh-TW": "這次報告包含哪些公司？",
        "en": "Which companies does this report include?",
    },
    "apl.field.reporting_entities_known_help": {
        "zh-TW": "這會用來建立本次報告涵蓋的公司範圍。專業上稱為報導邊界。",
        "en": (
            "This sets the company scope. "
            "Professionally this is the reporting boundary."
        ),
    },
    "apl.field.industry": {"zh-TW": "產業", "en": "Industry"},
    "apl.field.sasb_industry": {
        "zh-TW": "SASB 產業（可選）",
        "en": "SASB industry (optional)",
    },
    "apl.field.share_par_value_twd": {
        "zh-TW": "股票面額（新台幣）",
        "en": "Share par value (TWD)",
    },
    "apl.field.has_no_par_value_shares": {
        "zh-TW": "是否有無面額股份",
        "en": "Has no-par-value shares?",
    },
    "apl.field.uses_consolidated_financial_statements": {
        "zh-TW": "是否使用合併財務報表",
        "en": "Uses consolidated financial statements?",
    },
    "apl.field.number_of_taiwan_facilities": {
        "zh-TW": "台灣廠場數量",
        "en": "Number of Taiwan facilities",
    },
    "apl.entity.general_listed_company": {
        "zh-TW": "一般上市公司",
        "en": "General listed company (TWSE)",
    },
    "apl.entity.general_otc_company": {
        "zh-TW": "一般上櫃公司",
        "en": "General OTC company (TPEx)",
    },
    "apl.entity.financial_holding_company": {
        "zh-TW": "金融控股公司",
        "en": "Financial holding company",
    },
    "apl.entity.bank": {"zh-TW": "銀行", "en": "Bank"},
    "apl.entity.bills_finance_company": {
        "zh-TW": "票券金融公司",
        "en": "Bills finance company",
    },
    "apl.entity.securities_firm": {"zh-TW": "證券商", "en": "Securities firm"},
    "apl.entity.futures_commission_merchant": {
        "zh-TW": "期貨商",
        "en": "Futures commission merchant",
    },
    "apl.entity.other": {"zh-TW": "其他", "en": "Other"},
    "apl.entity.unresolved": {
        "zh-TW": "不知道／不確定",
        "en": "I don't know / not sure",
    },
    "apl.listing.TWSE": {"zh-TW": "上市（TWSE）", "en": "TWSE listed"},
    "apl.listing.TPEX": {"zh-TW": "上櫃（TPEx）", "en": "TPEx OTC"},
    "apl.listing.EMERGING": {"zh-TW": "興櫃", "en": "Emerging stock"},
    "apl.listing.PRIVATE": {
        "zh-TW": "未上市／未上櫃",
        "en": "Not listed / not OTC",
    },
    "apl.listing.NOT_APPLICABLE": {"zh-TW": "不適用", "en": "Not applicable"},
    "apl.listing.UNKNOWN": {"zh-TW": "不知道／不確定", "en": "Not sure"},
    "apl.choice.YES": {"zh-TW": "是", "en": "Yes"},
    "apl.choice.NO": {"zh-TW": "否", "en": "No"},
    "apl.choice.NOT_SURE": {"zh-TW": "不知道／不確定", "en": "Not sure"},
    "apl.choice.TRUE": {"zh-TW": "是", "en": "Yes"},
    "apl.choice.FALSE": {"zh-TW": "否", "en": "No"},
    "apl.choice.UNKNOWN": {"zh-TW": "不知道／不確定", "en": "Not sure"},
    "apl.status.APPLICABLE": {"zh-TW": "適用", "en": "Applicable"},
    "apl.status.NOT_APPLICABLE": {
        "zh-TW": "目前不適用",
        "en": "Does not apply now",
    },
    "apl.status.FUTURE_REQUIREMENT": {
        "zh-TW": "未來將適用",
        "en": "Will apply later",
    },
    "apl.status.NEEDS_INFORMATION": {
        "zh-TW": "還需要一些資料",
        "en": "Needs a few more details",
    },
    "apl.status.NEEDS_REVIEW": {
        "zh-TW": "正在確認中",
        "en": "Being confirmed",
    },
    "apl.status.NOT_YET_ASSESSED": {
        "zh-TW": "尚未開始",
        "en": "Not started",
    },
    "apl.status.MANUAL_VERIFICATION_REQUIRED": {
        "zh-TW": "正在確認中",
        "en": "Being confirmed",
    },
    "apl.status.REGULATORY_DATA_STALE": {
        "zh-TW": "法規資料需要更新",
        "en": "Regulatory data update required",
    },
    "apl.status.OUT_OF_V1_SCOPE": {
        "zh-TW": "目前版本暫不支援",
        "en": "Not supported in this version",
    },
    "apl.basis.authority": {"zh-TW": "官方主管機關", "en": "Official authority"},
    "apl.basis.document": {"zh-TW": "官方文件", "en": "Official document"},
    "apl.basis.citation": {"zh-TW": "條文／段落", "en": "Citation"},
    "apl.basis.rule_id": {"zh-TW": "規則編號", "en": "Rule ID"},
    "apl.basis.effective": {"zh-TW": "生效日", "en": "Effective date"},
    "apl.basis.version": {"zh-TW": "規則版本", "en": "Rule version"},
    "apl.basis.verified": {"zh-TW": "最後驗證日期", "en": "Last verified date"},
    "apl.basis.source": {"zh-TW": "官方來源編號", "en": "Official source"},
    "apl.obligation_ifrs": {
        "zh-TW": "IFRS永續揭露準則適用時程（S1＋S2）",
        "en": (
            "IFRS Sustainability Disclosure Standards applicability "
            "timeline (S1 and S2)"
        ),
    },
    "apl.obligation_inventory": {
        "zh-TW": "台灣溫室氣體盤查",
        "en": "Taiwan GHG inventory",
    },
    "apl.obligation_verification": {
        "zh-TW": "查驗／確信",
        "en": "Verification / assurance",
    },
    "apl.obligation_carbon_fee": {"zh-TW": "碳費", "en": "Carbon fee"},
    "reg.status_title": {"zh-TW": "法規資料", "en": "Regulatory data"},
    "reg.status_verified": {"zh-TW": "已驗證", "en": "Verified"},
    "reg.status_pending_verification": {
        "zh-TW": "法規更新確認中",
        "en": "Regulatory update under verification",
    },
    "reg.last_success_check": {
        "zh-TW": "最後成功檢查",
        "en": "Last successful check",
    },
    "reg.last_verified": {
        "zh-TW": "最後法規確認",
        "en": "Last regulatory verification",
    },
    "reg.pending_reviews": {
        "zh-TW": "待審法規變更",
        "en": "Pending regulatory reviews",
    },
    "reg.pending_major_updates": {
        "zh-TW": "待人工確認之重大更新",
        "en": "Major updates pending admin verification",
    },
    "reg.auto_sources_label": {
        "zh-TW": "核心法規監控",
        "en": "Core regulatory monitoring",
    },
    "reg.auto_sources_ok": {"zh-TW": "正常", "en": "Healthy"},
    "reg.auto_sources_attention": {
        "zh-TW": "需系統維護關注",
        "en": "Needs system maintenance attention",
    },
    "reg.supporting_config_required": {
        "zh-TW": "輔助資料來源：{n} 個尚未設定",
        "en": "Supporting data sources: {n} not configured",
    },
    "reg.pending_signal_note": {
        "zh-TW": "目前評估仍依最近已驗證規則集；無需自行查法規網站。",
        "en": "Uses last verified rules; no need to research laws yourself.",
    },
    "reg.admin_expander": {
        "zh-TW": "系統維護／技術狀態（管理員）",
        "en": "System maintenance / technical status (admin)",
    },
    "reg.freshness.CURRENT": {"zh-TW": "最新", "en": "Current"},
    "reg.freshness.CHECK_DUE": {"zh-TW": "建議更新", "en": "Check due"},
    "reg.freshness.UPDATE_REQUIRED": {
        "zh-TW": "建議更新",
        "en": "Update recommended",
    },
    "reg.freshness.STALE": {"zh-TW": "需要更新", "en": "Stale"},
    "reg.freshness.REGULATORY_DATA_STALE": {
        "zh-TW": "需要更新",
        "en": "Regulatory data stale",
    },
    "reg.freshness.MANUAL_VERIFICATION_REQUIRED": {
        "zh-TW": "需要人工確認官方版本",
        "en": "Manual verification required",
    },
    "reg.freshness.MANUAL_ACCESS_REQUIRED": {
        "zh-TW": "需要人工確認官方版本",
        "en": "Manual access required",
    },
    "reg.freshness.SOURCE_CHECK_FAILED": {
        "zh-TW": "來源檢查失敗",
        "en": "Source check failed",
    },
    "reg.freshness.FRESHNESS_STATE_UNAVAILABLE": {
        "zh-TW": "新鮮度狀態不可用",
        "en": "Freshness state unavailable",
    },
    "reg.freshness.PARTIAL": {
        "zh-TW": "核心監控正常／部分輔助來源尚未設定",
        "en": "Core monitoring OK; some supporting sources unset",
    },
    "reg.freshness.MONITORING_PARTIAL": {
        "zh-TW": "核心監控正常／部分輔助來源尚未設定",
        "en": "Core monitoring OK; some supporting sources unset",
    },
    "reg.freshness.MONITORING_CURRENT": {
        "zh-TW": "法規資料：已驗證",
        "en": "Regulations verified",
    },
    "reg.freshness.BASELINE_CAPTURED": {
        "zh-TW": "已建立基準",
        "en": "Baseline established",
    },
    "reg.freshness.SOURCE_UNAVAILABLE": {
        "zh-TW": "來源目前無法檢查",
        "en": "Source currently unavailable",
    },
    "reg.freshness.NOT_ACTIVATED": {
        "zh-TW": "尚未啟用",
        "en": "Not activated",
    },
    "reg.freshness.NEEDS_INFORMATION": {
        "zh-TW": "還需要一些資料",
        "en": "More information needed",
    },
    "reg.freshness.OUT_OF_V1_SCOPE": {
        "zh-TW": "目前版本暫不支援",
        "en": "Not supported in this version",
    },
    "dash.section_requirements": {
        "zh-TW": "適用要求",
        "en": "Your Requirements",
    },
    "dash.section_requirements_help": {
        "zh-TW": "與適用性判定使用同一份評估結果。",
        "en": "Uses the same assessment object as Applicability.",
    },
    "dash.section_attention_reg": {
        "zh-TW": "目前需要注意",
        "en": "Current Attention",
    },
    "dash.section_missing_profile": {
        "zh-TW": "缺少的資料（公司檔）",
        "en": "Missing Information (company profile)",
    },
    "dash.section_missing_emissions": {
        "zh-TW": "缺少的資料（排放資料）",
        "en": "Missing Information (emissions data)",
    },
    "dash.attention.need_profile": {
        "zh-TW": "尚未完成適用性判定",
        "en": "Applicability assessment not completed",
    },
    "dash.attention.need_profile_action": {
        "zh-TW": "前往「適用性判定」填寫公司資料。",
        "en": "Go to Applicability and complete the company profile.",
    },
    "dash.attention.freshness": {
        "zh-TW": "法規資料需要更新或人工確認",
        "en": "Regulatory data needs update or manual verification",
    },
    "dash.attention.freshness_action": {
        "zh-TW": "系統正在確認法規更新；目前結論仍依已驗證規則。",
        "en": "Verifying a regulatory update; last verified rules still apply.",
    },
    "dash.attention.review_action": {
        "zh-TW": "查看相關要求與法規依據。",
        "en": "Review the related requirements and legal basis.",
    },
    "dash.attention.future": {
        "zh-TW": "{obligation}：未來適用（{year}）",
        "en": "{obligation}: future requirement ({year})",
    },
    "dash.attention.future_action": {
        "zh-TW": "開始準備首個適用報導年度所需資料。",
        "en": "Begin readiness work before the first reporting year.",
    },
    "dash.attention.missing_profile": {
        "zh-TW": "{obligation}：公司檔資料不足",
        "en": "{obligation}: company-profile information missing",
    },
    "dash.attention.missing_profile_action": {
        "zh-TW": "回到適用性判定補齊缺少欄位。",
        "en": "Return to Applicability and complete the missing fields.",
    },
    "dash.no_assessment_yet": {
        "zh-TW": "尚未產生適用性判定。請先到「適用性判定」頁面。",
        "en": "No applicability assessment yet. Open the Applicability page first.",
    },
    "fw.applicability_summary": {
        "zh-TW": "適用性摘要（IFRS）",
        "en": "Applicability summary (IFRS)",
    },
    "tw.applicability_summary": {
        "zh-TW": "適用性摘要（台灣義務）",
        "en": "Applicability summary (Taiwan obligations)",
    },
    "tw.title": {
        "zh-TW": "台灣溫室氣體與碳費",
        "en": "Taiwan GHG / Carbon Fee",
    },
    "tw.subtitle": {
        "zh-TW": "先分清楚盤查、查驗、確信與碳費，再看你目前的狀態。",
        "en": (
            "First tell inventory, verification, assurance, and carbon fee apart, "
            "then review your status."
        ),
    },
    "tw.help": {
        "zh-TW": (
            "此頁顯示適用性判定摘要；完整盤查／碳費表單與計算屬於後續階段。"
        ),
        "en": (
            "This page shows applicability summaries; full inventory / carbon-fee "
            "forms belong to a later stage."
        ),
    },
    "tw.inventory": {"zh-TW": "溫室氣體盤查", "en": "GHG Inventory"},
    "tw.verification": {
        "zh-TW": "查驗／確信",
        "en": "Verification / Assurance",
    },
    "tw.carbon_fee": {"zh-TW": "碳費", "en": "Carbon Fee"},
    "tw.track.inventory": {"zh-TW": "溫室氣體盤查", "en": "GHG Inventory"},
    "tw.track.env_verification": {
        "zh-TW": "環境部溫室氣體查驗",
        "en": "MOENV GHG verification",
    },
    "tw.track.carbon_fee": {"zh-TW": "碳費", "en": "Carbon Fee"},
    "tw.track.ifrs_assurance": {
        "zh-TW": "臺灣規範：合併個體Scope 1／2溫室氣體排放確信",
        "en": (
            "Taiwan requirement: Assurance of consolidated Scope 1 and "
            "Scope 2 GHG emissions"
        ),
    },
    "tw.ifrs_assurance_note": {
        "zh-TW": (
            "此結果反映臺灣主管機關對適用公司之合併個體Scope 1／2溫室氣體排放"
            "確信要求，並非IFRS S1或S2本身的完整確信結論，也不同於環境部列管"
            "事業的盤查查驗。"
        ),
        "en": (
            "This result reflects the Taiwan authority's requirement for "
            "applicable companies to obtain assurance over consolidated-entity "
            "Scope 1 and Scope 2 GHG emissions. It is not a complete IFRS S1 "
            "or S2 assurance conclusion, and it is distinct from inventory "
            "verification for MOENV-regulated entities."
        ),
    },
    "tw.track.empty": {
        "zh-TW": "此軌道尚無判定結果；請先完成公司設定。",
        "en": "No result for this track yet — finish company setup first.",
    },
    "tw.section_help": {
        "zh-TW": "詳細工作底稿與申報表單尚未開放；請先完成適用性判定。",
        "en": (
            "Detailed workpapers and filing forms are not open yet; complete "
            "Applicability first."
        ),
    },
    "ev.title": {
        "zh-TW": "佐證文件與稽核紀錄",
        "en": "Supporting Documents & Audit Trail",
    },
    "ev.landing.title": {
        "zh-TW": "上傳能源與營運資料",
        "en": "Upload energy and operating data",
    },
    "ev.landing.body": {
        "zh-TW": (
            "上傳公司既有的電力、燃料、車輛或採購資料。"
            "系統會先整理，並標出需要你確認的項目。"
        ),
        "en": (
            "Upload the electricity, fuel, vehicle, or purchasing files "
            "your company already keeps. We will organize them and flag "
            "anything that needs confirmation."
        ),
    },
    "ev.landing.primary": {
        "zh-TW": "上傳資料檔",
        "en": "Upload a data file",
    },
    "ev.subtitle": {
        "zh-TW": "把資料給系統，系統幫你整理和計算。",
        "en": "Give the system your data; it organizes and calculates it for you.",
    },
    "ev.help": {
        "zh-TW": "同一來源文件可支援多項義務；此頁整理入口，不重寫計算管線。",
        "en": (
            "One source document can support multiple obligations. This page "
            "organizes entry points without rewriting the calculation pipeline."
        ),
    },
    "ev.workspace_nav": {
        "zh-TW": "其他資料功能",
        "en": "More data tools",
    },
    "ev.flow_title": {
        "zh-TW": "資料與證據工作流程",
        "en": "Data and evidence workflow",
    },
    "ev.flow_help": {
        "zh-TW": "請從上方分頁進入既有功能；這些不是獨立的主選單項目。",
        "en": (
            "Use the tabs above to open existing tools; "
            "they are not separate primary navigation items."
        ),
    },
    "ev.tab.overview": {"zh-TW": "流程總覽", "en": "Overview"},
    "ev.tab.intake": {"zh-TW": "資料匯入", "en": "Data Upload"},
    "ev.tab.intake_help": {
        "zh-TW": "上傳公司既有檔案；其他資料功能可從上方選單開啟。",
        "en": (
            "Upload a file your company already keeps; "
            "other data tools are in the menu above."
        ),
    },
    "ev.tab.activity": {"zh-TW": "活動資料", "en": "Activity Data"},
    "ev.tab.issues": {"zh-TW": "待處理問題", "en": "Issues & Review"},
    "ev.tab.records": {
        "zh-TW": "佐證文件與稽核紀錄",
        "en": "Supporting Documents & Audit Trail",
    },
    "ev.tab.records_help": {
        "zh-TW": "目前分析已接受的來源文件與證據雜湊。",
        "en": "Accepted source documents and evidence hashes for this analysis.",
    },
    "ev.records_help": {
        "zh-TW": "此處列出佐證文件清單，不會改寫計算結果。",
        "en": "Lists supporting documents; it does not change calculation results.",
    },
    "ev.step_upload": {"zh-TW": "1. 資料匯入", "en": "1. Data Upload"},
    "ev.step_upload_help": {
        "zh-TW": "上傳並檢查活動資料格式。",
        "en": "Upload and validate activity data format.",
    },
    "ev.step_activity": {
        "zh-TW": "2. 活動與計算",
        "en": "2. Activities & calculations",
    },
    "ev.step_activity_help": {
        "zh-TW": "查看每筆活動的計算狀態與證據連結。",
        "en": "Inspect calculation status and evidence links per activity.",
    },
    "ev.step_issues": {"zh-TW": "3. 待處理問題", "en": "3. Issues & Review"},
    "ev.step_issues_help": {
        "zh-TW": "處理資料品質與缺口複核事項。",
        "en": "Resolve data-quality and gap-review items.",
    },
    "ev.open_intake": {"zh-TW": "開啟資料匯入", "en": "Open data upload"},
    "ev.open_activity": {"zh-TW": "開啟活動資料", "en": "Open activity data"},
    "ev.open_issues": {"zh-TW": "開啟待處理問題", "en": "Open issues"},
    # --- Stage 3B.2 enterprise UX ---
    "header.help": {"zh-TW": "? 說明", "en": "? Help"},
    "header.glossary": {"zh-TW": "名詞解釋", "en": "Glossary"},
    "glossary.title": {"zh-TW": "名詞解釋", "en": "Glossary"},
    "glossary.intro": {
        "zh-TW": "工作時可隨時查閱的簡短說明。",
        "en": "Short definitions available while you work.",
    },
    "dash.greeting": {"zh-TW": "早安，{company}", "en": "Good morning, {company}"},
    "dash.greeting_company_fallback": {
        "zh-TW": "貴公司",
        "en": "your company",
    },
    "dash.greeting_year_suffix": {
        "zh-TW": "報導年度",
        "en": "reporting year",
    },
    "dash.greeting_attention_count": {
        "zh-TW": "{n} 件事項需要處理",
        "en": "{n} items need attention",
    },
    "dash.reporting_context": {
        "zh-TW": "報導區間與資料",
        "en": "Reporting period & data",
    },
    "dash.section_attention_unified": {
        "zh-TW": "目前需要注意",
        "en": "Current Attention",
    },
    "dash.section_attention_unified_help": {
        "zh-TW": "先處理最重要的事項，再進入細節。",
        "en": "Handle the highest-priority items first.",
    },
    "dash.priority.high": {"zh-TW": "高優先", "en": "High"},
    "dash.priority.medium": {"zh-TW": "中優先", "en": "Medium"},
    "dash.cta.complete_now": {"zh-TW": "現在完成", "en": "Complete now"},
    "dash.cta.review_reg": {"zh-TW": "查看法規狀態", "en": "Review regulatory status"},
    "dash.journey_title": {"zh-TW": "工作進度", "en": "Workflow journey"},
    "dash.journey_help": {
        "zh-TW": "顯示目前已完成的工作步驟。",
        "en": "Shows which work steps are already done.",
    },
    "dash.journey.company": {"zh-TW": "公司設定", "en": "Company setup"},
    "dash.journey.applicability": {
        "zh-TW": "我的適用要求",
        "en": "Your requirements",
    },
    "dash.journey.data": {"zh-TW": "資料與證據", "en": "Data & evidence"},
    "dash.journey.prepare": {
        "zh-TW": "IFRS / 台灣準備",
        "en": "IFRS / Taiwan preparation",
    },
    "dash.journey.reporting": {"zh-TW": "報表", "en": "Reporting"},
    "dash.emissions_section": {"zh-TW": "排放資料摘要", "en": "Emissions summary"},
    "dash.coverage_complete": {
        "zh-TW": "碳排計算完成",
        "en": "Emissions calculation complete",
    },
    "dash.coverage_complete_demo": {
        "zh-TW": "碳排計算完成",
        "en": "Emissions calculation complete",
    },
    "dash.result_preliminary": {
        "zh-TW": "初步碳排結果",
        "en": "Preliminary emissions result",
    },
    "dash.result_preliminary_body": {
        "zh-TW": (
            "技術上已計算：{calculated} 筆；已納入公司盤查：{included} 筆；"
            "待使用者確認：{needs_review} 筆；目前產品尚未支援：{unsupported} 筆；"
            "邊界外：{outside} 筆。"
        ),
        "en": (
            "Technically calculated: {calculated} rows; included in the "
            "company inventory: {included} rows; awaiting confirmation: "
            "{needs_review} rows; not supported yet: {unsupported} rows; "
            "outside the boundary: {outside} rows."
        ),
    },
    "dash.result_incomplete_sources": {
        "zh-TW": "目前結果尚未涵蓋全部待確認來源，不代表完整盤查總量。",
        "en": (
            "The current result does not yet cover every source that still "
            "needs confirmation, and is not the complete inventory total."
        ),
    },
    "dash.result_no_factor": {
        "zh-TW": "已支援但目前無符合係數：{n} 筆。",
        "en": "Supported but no matching factor: {n} rows.",
    },
    "boundary.confirm.title": {
        "zh-TW": "待確認冷媒的組織邊界",
        "en": "Refrigerant organizational boundary confirmation",
    },
    "boundary.confirm.help": {
        "zh-TW": (
            "請確認法律所有權、實際營運控制與盤查邊界。系統不會讓您直接選擇 "
            "Scope；確認後會依既有規則重新分析。"
        ),
        "en": (
            "Confirm legal ownership, operational control, and inventory "
            "boundary. You do not choose Scope directly; existing mapping "
            "rules re-run after you save."
        ),
    },
    "boundary.confirm.record_id": {"zh-TW": "紀錄編號", "en": "Record ID"},
    "boundary.confirm.refrigerant": {"zh-TW": "冷媒種類", "en": "Refrigerant"},
    "boundary.confirm.quantity": {
        "zh-TW": "實際補充量",
        "en": "Actual refill quantity",
    },
    "boundary.confirm.tco2e": {
        "zh-TW": "已計算 tCO₂e",
        "en": "Calculated tCO₂e",
    },
    "boundary.confirm.current_mapping": {
        "zh-TW": "目前判定與未納入原因",
        "en": "Current classification and exclusion reason",
    },
    "boundary.confirm.legal_owner": {
        "zh-TW": "法律所有人",
        "en": "Legal owner",
    },
    "boundary.confirm.controller": {
        "zh-TW": "實際營運控制者",
        "en": "Operational controller",
    },
    "boundary.confirm.boundary_status": {
        "zh-TW": "是否位於盤查邊界",
        "en": "Organizational boundary status",
    },
    "boundary.confirm.boundary_basis": {
        "zh-TW": "本次邊界依據",
        "en": "Boundary basis for this confirmation",
    },
    "boundary.confirm.evidence": {
        "zh-TW": "佐證文件／紀錄編號",
        "en": "Supporting document or record ID",
    },
    "boundary.confirm.rationale": {"zh-TW": "判定理由", "en": "Rationale"},
    "boundary.confirm.save": {
        "zh-TW": "儲存判定並重新分析",
        "en": "Save decision and re-analyze",
    },
    "boundary.confirm.withdraw": {
        "zh-TW": "撤銷判定並重新分析",
        "en": "Withdraw decision and re-analyze",
    },
    "boundary.confirm.evidence_required": {
        "zh-TW": "佐證文件／紀錄編號為必填，空白時無法完成確認。",
        "en": (
            "A supporting document or record ID is required; confirmation "
            "cannot be completed while it is blank."
        ),
    },
    "boundary.confirm.incomplete": {
        "zh-TW": "請完整填寫所有判定欄位後再儲存。",
        "en": "Complete every confirmation field before saving.",
    },
    "boundary.confirm.no_upload": {
        "zh-TW": "請先完成上傳分析，才能儲存判定並重新分析。",
        "en": "Upload and analyze data before saving a decision.",
    },
    "boundary.outcome.included_scope_1": {
        "zh-TW": "已納入 Scope 1",
        "en": "Included in Scope 1",
    },
    "boundary.outcome.excluded_outside": {
        "zh-TW": "已排除於盤查邊界外",
        "en": "Excluded as outside the inventory boundary",
    },
    "boundary.outcome.still_needs_review": {
        "zh-TW": "仍需補充資料",
        "en": "Still needs more information",
    },
    "boundary.owner.company": {"zh-TW": "本公司", "en": "The company"},
    "boundary.owner.third_party": {"zh-TW": "第三方", "en": "Third party"},
    "boundary.owner.unknown": {"zh-TW": "不確定", "en": "Unknown"},
    "boundary.controller.company": {"zh-TW": "本公司", "en": "The company"},
    "boundary.controller.third_party": {"zh-TW": "第三方", "en": "Third party"},
    "boundary.controller.shared": {"zh-TW": "共同控制", "en": "Shared"},
    "boundary.controller.unknown": {"zh-TW": "不確定", "en": "Unknown"},
    "boundary.status.inside": {"zh-TW": "位於盤查邊界內", "en": "Inside"},
    "boundary.status.outside": {
        "zh-TW": "位於盤查邊界外",
        "en": "Outside",
    },
    "boundary.status.unknown": {"zh-TW": "不確定", "en": "Unknown"},
    "boundary.basis.taiwan_statutory_facility": {
        "zh-TW": "台灣法定廠場",
        "en": "Taiwan statutory facility",
    },
    "boundary.basis.operational_control": {
        "zh-TW": "營運控制",
        "en": "Operational control",
    },
    "boundary.basis.financial_control": {
        "zh-TW": "財務控制",
        "en": "Financial control",
    },
    "boundary.basis.equity_share": {
        "zh-TW": "權益比例",
        "en": "Equity share",
    },
    "boundary.basis.unknown": {"zh-TW": "尚不確定", "en": "Unknown"},
    "dash.cta.resolve_remaining": {
        "zh-TW": "處理待確認的 {remaining} 筆",
        "en": "Resolve {remaining} rows awaiting confirmation",
    },
    "dash.hero.excluded": {
        "zh-TW": "已排除 {n} 筆",
        "en": "{n} rows excluded",
    },
    "dash.hero.included": {
        "zh-TW": "納入 {included}／{total} 筆",
        "en": "{included} of {total} rows included",
    },
    "dash.hero.scope2_location": {
        "zh-TW": "Scope 2（地區基準）",
        "en": "Scope 2 (location-based)",
    },
    "dash.hero.scope_value": {
        "zh-TW": "{label}：{value} tCO₂e",
        "en": "{label}: {value} tCO₂e",
    },
    "dash.hero.scope3_version": {
        "zh-TW": (
            "Scope 3 尚未納入計算。本版本總排放量僅包含 Scope 1 與 Scope 2；"
            "採購、委外運輸等價值鏈排放不包含在目前總量中。"
        ),
        "en": (
            "Scope 3 is not included in this calculation. The current total "
            "covers Scope 1 and Scope 2 only; purchased goods, outsourced "
            "transport, and other value-chain emissions are excluded."
        ),
    },
    "dash.hero.meta": {
        "zh-TW": "{company} · {period} · {sources} 份來源文件",
        "en": "{company} · {period} · {sources} source documents",
    },
    "dash.hero.factor_details": {
        "zh-TW": "係數與版本",
        "en": "Factors and version",
    },
    "dash.coverage_partial": {
        "zh-TW": "目前已計算 {done} / {total} 筆；其餘資料尚未納入結果。",
        "en": (
            "Currently calculated {done} / {total} records; "
            "the rest are not yet included."
        ),
    },
    "dash.coverage_all_done": {
        "zh-TW": "本次資料皆已完成計算",
        "en": "All records in this run are calculated",
    },
    "dash.section_scope_main": {
        "zh-TW": "主要排放範疇",
        "en": "Main emission scopes",
    },
    "dash.scope3.empty": {
        "zh-TW": "目前尚無可納入的 Scope 3 計算結果。",
        "en": "No Scope 3 results can be included yet.",
    },
    "dash.scope3.partial": {
        "zh-TW": (
            "目前已計算 {value} tCO2e，現階段僅涵蓋 {categories}，"
            "尚不代表完整 Scope 3 總量。"
        ),
        "en": (
            "Currently calculated {value} tCO2e, covering {categories} "
            "only at this stage; this is not a complete Scope 3 total."
        ),
    },
    "dash.scope3.category.category_1": {
        "zh-TW": "Category 1－採購商品與服務",
        "en": "Category 1 — purchased goods and services",
    },
    "dash.scope3_cat1.title": {
        "zh-TW": "Scope 3 Category 1－採購商品與服務",
        "en": "Scope 3 Category 1 — purchased goods and services",
    },
    "dash.scope3_cat1.not_in_inventory": {
        "zh-TW": (
            "此為已計算的估算排放量，未納入上方 Scope 1＋Scope 2 公司盤查總量。"
        ),
        "en": (
            "This is a calculated estimate and is not included in the "
            "Scope 1 + Scope 2 company inventory total above."
        ),
    },
    "dash.scope3_cat1.estimated": {
        "zh-TW": "估算排放量",
        "en": "Estimated emissions",
    },
    "dash.scope3_cat1.empty": {
        "zh-TW": "本次尚未計算 Scope 3 Category 1 採購鋼材排放。",
        "en": "No Scope 3 Category 1 purchased-steel emissions were calculated.",
    },
    "dash.scope3_cat1.method": {
        "zh-TW": "方法",
        "en": "Method",
    },
    "dash.scope3_cat1.method.supplier_specific": {
        "zh-TW": "供應商特定",
        "en": "Supplier-specific",
    },
    "dash.scope3_cat1.method.average_data": {
        "zh-TW": "平均數據",
        "en": "Average data",
    },
    "dash.scope3_cat1.supplier": {
        "zh-TW": "供應商",
        "en": "Supplier",
    },
    "dash.scope3_cat1.product": {
        "zh-TW": "產品類型",
        "en": "Product type",
    },
    "dash.scope3_cat1.factor_year": {
        "zh-TW": "係數年份",
        "en": "Factor year",
    },
    "dash.scope3_cat1.factor_id": {
        "zh-TW": "係數編號",
        "en": "Factor id",
    },
    "dash.scope3_cat1.factor_version": {
        "zh-TW": "係數版本",
        "en": "Factor version",
    },
    "dash.scope3_cat1.factor_source": {
        "zh-TW": "係數來源",
        "en": "Factor source",
    },
    "dash.scope3_cat1.official_name": {
        "zh-TW": "官方產品名稱",
        "en": "Official product name",
    },
    "dash.scope3_cat1.factor_value": {
        "zh-TW": "係數值",
        "en": "Factor value",
    },
    "dash.scope3_cat1.publisher": {
        "zh-TW": "發布單位",
        "en": "Publisher",
    },
    "dash.scope3_cat1.announcement_year": {
        "zh-TW": "公告年份",
        "en": "Announcement year",
    },
    "dash.scope3_cat1.source_url": {
        "zh-TW": "來源網址",
        "en": "Source URL",
    },
    "dash.scope3_cat1.snapshot": {
        "zh-TW": "Snapshot SHA-256",
        "en": "Snapshot SHA-256",
    },
    "dash.scope3_cat1.boundary": {
        "zh-TW": "係數邊界",
        "en": "Factor boundary",
    },
    "dash.scope3_cat1.limit": {
        "zh-TW": "資料限制",
        "en": "Data limits",
    },
    "dash.scope3_cat1.temporal": {
        "zh-TW": (
            "係數年份為 {factor_year}，與盤查年度 {reporting_year} 不同。"
            "此為有來源的估算資料，請確認時間代表性；不得視為盤查年度最新係數。"
        ),
        "en": (
            "The factor year is {factor_year}, which differs from reporting "
            "year {reporting_year}. Treat this as sourced estimate data and "
            "confirm temporal representativeness; it is not the latest "
            "reporting-year factor."
        ),
    },
    "dash.scope3_cat1.boundary_note": {
        "zh-TW": (
            "cradle-to-gate 可包含 Tier 1 以前的供應鏈運輸；"
            "供應商到申報公司的入廠運輸不列入 Category 1。"
        ),
        "en": (
            "Cradle-to-gate may include pre-Tier-1 supply-chain transport; "
            "Tier 1 to reporting-company inbound transport is not Category 1."
        ),
    },
    "dash.scope_help_title": {
        "zh-TW": "? Scope 是什麼？",
        "en": "? What is Scope?",
    },
    "dash.scope_help_body": {
        "zh-TW": (
            "**Scope 1**：公司直接產生的排放，例如燃料燃燒。\n\n"
            "**Scope 2**：外購能源的間接排放，例如外購電力。\n\n"
            "**Scope 3**：價值鏈其他間接排放。已計算的部分會另外顯示，"
            "不加入目前的 Scope 1＋Scope 2 公司盤查總量；"
            "目前可能僅部分涵蓋，不代表完整 Scope 3。"
        ),
        "en": (
            "**Scope 1**: Direct emissions, such as fuel combustion.\n\n"
            "**Scope 2**: Indirect emissions from purchased energy, "
            "such as electricity.\n\n"
            "**Scope 3**: Other value-chain emissions. Calculated Scope 3 "
            "is shown separately and is not added to the current "
            "Scope 1 + Scope 2 company inventory total; coverage may be "
            "partial and is not a complete Scope 3 inventory."
        ),
    },
    "dash.insight.top_scope": {
        "zh-TW": "目前排放主要來自 {scope}，約占已納入公司盤查排放量的 {percent}%。",
        "en": (
            "Emissions currently come mainly from {scope}, "
            "about {percent}% of company inventory emissions."
        ),
    },
    "dash.insight.top_source": {
        "zh-TW": "{name}是目前最大的單一排放來源。",
        "en": "{name} is currently the largest single emissions source.",
    },
    "dash.insight.top_source_share": {
        "zh-TW": "{name}是目前最大的排放來源，占已納入公司盤查排放量 {percent}%。",
        "en": (
            "{name} is currently the largest emissions source, "
            "{percent}% of company inventory emissions."
        ),
    },
    "dash.section_detail": {"zh-TW": "排放明細", "en": "Emissions detail"},
    "dash.section_detail_help": {
        "zh-TW": "排放來源與排放趨勢，一次只顯示一張圖。",
        "en": "Source and trend views; one chart at a time.",
    },
    "dash.detail.source": {"zh-TW": "依來源", "en": "By source"},
    "dash.detail.trend": {"zh-TW": "依月份", "en": "By month"},
    "dash.detail.trend_title": {
        "zh-TW": "每月已納入公司盤查排放量",
        "en": "Monthly company inventory emissions",
    },
    "dash.cta.view_detail": {"zh-TW": "查看排放明細", "en": "View emissions detail"},
    "dash.cta.view_all_attention": {"zh-TW": "查看全部", "en": "View all"},
    "dash.cta.calc_help": {"zh-TW": "查看計算說明", "en": "View calculation notes"},
    "dash.evidence_line": {
        "zh-TW": "資料來源：{count} 個上傳檔案",
        "en": "Data source: {count} uploaded file(s)",
    },
    "dash.evidence_line_demo": {
        "zh-TW": "資料來源：{count} 個示範檔案",
        "en": "Data source: {count} demo file(s)",
    },
    "dash.scope3_short": {
        "zh-TW": "尚未納入計算",
        "en": "Not included in the total",
    },
    "dash.coverage_learn": {
        "zh-TW": "了解結果涵蓋範圍",
        "en": "What this result includes",
    },
    "dash.coverage_learn_body": {
        "zh-TW": (
            "結果涵蓋目前已完成計算的活動。"
            "未完成計算的活動不會被當成 0。"
            "這不是公司的總排放量。"
        ),
        "en": (
            "Results cover activities that have been calculated. "
            "Activities not yet calculated are not treated as zero. "
            "This is not total company emissions."
        ),
    },
    "dash.issues_banner": {
        "zh-TW": "{count} 筆資料仍需處理",
        "en": "{count} records still need attention",
    },
    "dash.cta.view_problems": {"zh-TW": "查看問題", "en": "View issues"},
    "dash.no_data_issues": {
        "zh-TW": "沒有待處理的資料問題",
        "en": "No outstanding data issues",
    },
    "dash.section_next": {"zh-TW": "下一步", "en": "Next step"},
    "dash.next.applicability": {
        "zh-TW": "完成公司適用性判定",
        "en": "Complete company applicability",
    },
    "dash.next.applicability_body": {
        "zh-TW": "了解 IFRS / 台灣相關要求",
        "en": "See IFRS / Taiwan requirements that may apply",
    },
    "dash.next.need_more": {
        "zh-TW": "還需要一些公司資訊才能完成判定",
        "en": "A few more company details are needed to finish the assessment",
    },
    "dash.req.headline": {"zh-TW": "你的主要要求", "en": "Your main requirements"},
    "dash.req.applies": {"zh-TW": "適用", "en": "Applies"},
    "dash.req.year_applies": {
        "zh-TW": "{year} 年開始適用",
        "en": "Applies from {year}",
    },
    "dash.cta.view_requirements": {
        "zh-TW": "查看全部要求",
        "en": "View all requirements",
    },
    "dash.reg_details": {"zh-TW": "查看詳細資訊", "en": "View details"},
    "dash.period_line": {
        "zh-TW": "資料期間 {start} ～ {end}",
        "en": "Reporting period {start} – {end}",
    },
    "dash.source_files_line": {
        "zh-TW": "來源：{count} 個資料檔案",
        "en": "Source: {count} data file(s)",
    },
    "apl.why_title": {
        "zh-TW": "為什麼我要回答這些問題？",
        "en": "Why am I answering these questions?",
    },
    "apl.why_body": {
        "zh-TW": (
            "這些資料用來判斷哪些法規要求跟你的公司有關。"
            "你不必先懂碳盤查。"
        ),
        "en": (
            "These answers help identify which requirements apply to your company. "
            "You do not need carbon-inventory expertise first."
        ),
    },
    "apl.result_heading": {
        "zh-TW": "你的公司目前：",
        "en": "Your company today:",
    },
    "apl.result.year_applies": {
        "zh-TW": "{year} 年開始適用",
        "en": "Applies from {year}",
    },
    "apl.result.need_info": {
        "zh-TW": "還需要更多公司資訊",
        "en": "More company information is needed",
    },
    "apl.cta.view_basis": {"zh-TW": "查看法規依據", "en": "View regulatory basis"},
    "fw.prepare_what": {
        "zh-TW": "IFRS S1/S2 要公司準備什麼？",
        "en": "What do IFRS S1/S2 ask companies to prepare?",
    },
    "fw.prepare_body": {
        "zh-TW": (
            "公司需要說明如何治理永續議題、策略如何受影響、"
            "如何管理風險，以及追蹤哪些指標與目標。"
        ),
        "en": (
            "Companies explain who oversees sustainability, how it affects strategy, "
            "how risks are managed, and which metrics and targets are tracked."
        ),
    },
    "fw.not_compliance": {
        "zh-TW": "這是揭露準備，不代表已經符合 IFRS。",
        "en": "This is disclosure preparation; it does not represent IFRS compliance.",
    },
    "fw.pillar.governance_q": {
        "zh-TW": "誰負責永續議題？",
        "en": "Who is accountable for sustainability?",
    },
    "fw.pillar.strategy_q": {
        "zh-TW": "永續議題如何影響公司？",
        "en": "How do sustainability issues affect the company?",
    },
    "fw.pillar.risk_q": {
        "zh-TW": "公司如何辨識與管理風險？",
        "en": "How does the company identify and manage risk?",
    },
    "fw.pillar.metrics_q": {
        "zh-TW": "公司追蹤哪些數據與目標？",
        "en": "Which metrics and targets does the company track?",
    },
    "fw.readiness_detail": {
        "zh-TW": "了解資料準備細節",
        "en": "Data-readiness detail",
    },
    "tw.explain_title": {
        "zh-TW": "這四件事有什麼不同？",
        "en": "How do these four tracks differ?",
    },
    "tw.explain.inventory.title": {
        "zh-TW": "溫室氣體盤查",
        "en": "GHG inventory",
    },
    "tw.explain.inventory.body": {
        "zh-TW": "算清楚排放量。",
        "en": "Calculate emissions clearly.",
    },
    "tw.explain.verification.title": {
        "zh-TW": "環境部溫室氣體查驗",
        "en": "MOENV GHG verification",
    },
    "tw.explain.verification.body": {
        "zh-TW": "特定企業可能需要第三方查驗。",
        "en": "Some companies may need third-party verification.",
    },
    "tw.explain.assurance.title": {
        "zh-TW": "臺灣規範：合併個體Scope 1／2溫室氣體排放確信",
        "en": (
            "Taiwan requirement: Assurance of consolidated Scope 1 and "
            "Scope 2 GHG emissions"
        ),
    },
    "tw.explain.assurance.body": {
        "zh-TW": (
            "臺灣主管機關對適用公司合併個體Scope 1／2溫室氣體排放的確信要求，"
            "與環境部列管事業盤查查驗不同。"
        ),
        "en": (
            "A Taiwan-authority assurance requirement over consolidated-entity "
            "Scope 1 and Scope 2 GHG emissions, distinct from inventory "
            "verification for MOENV-regulated entities."
        ),
    },
    "tw.explain.fee.title": {"zh-TW": "碳費", "en": "Carbon fee"},
    "tw.explain.fee.body": {
        "zh-TW": "符合條件的排放來源可能涉及碳費。",
        "en": "Qualifying emission sources may involve a carbon fee.",
    },
    "tw.status_title": {"zh-TW": "你目前的狀態", "en": "Your current status"},
    "ev.status_title": {"zh-TW": "資料狀態", "en": "Data status"},
    "ev.status_done": {
        "zh-TW": "{done} 筆已完成",
        "en": "{done} records calculated",
    },
    "ev.cta.view_activities": {"zh-TW": "查看活動資料", "en": "View activities"},
    "ev.cta.view_files": {"zh-TW": "查看文件", "en": "View files"},
    "aud.ask.management": {"zh-TW": "給主管看", "en": "For leadership"},
    "aud.ask.ifrs": {"zh-TW": "準備 IFRS", "en": "Prepare IFRS"},
    "aud.ask.ghg": {"zh-TW": "盤查 / 查驗", "en": "Inventory / verification"},
    "aud.ask.audit": {"zh-TW": "給稽核", "en": "For auditors"},
    "aud.ask.data": {"zh-TW": "自己分析", "en": "Analyze yourself"},
    "apl.wizard.step_of": {
        "zh-TW": "步驟 {current} / {total}",
        "en": "Step {current} / {total}",
    },
    "apl.wizard.step1": {"zh-TW": "確認公司", "en": "Confirm company"},
    "apl.wizard.step2": {"zh-TW": "補充必要資訊", "en": "Add missing facts"},
    "apl.wizard.step3": {"zh-TW": "確認台灣廠場", "en": "Confirm Taiwan sites"},
    "apl.wizard.step4": {"zh-TW": "你的結果", "en": "Your results"},
    "apl.wizard.step5": {"zh-TW": "你的結果", "en": "Your results"},
    "apl.wizard.back": {"zh-TW": "上一步", "en": "Back"},
    "apl.wizard.continue": {"zh-TW": "繼續", "en": "Continue"},
    "apl.wizard.save": {"zh-TW": "儲存", "en": "Save"},
    "apl.wizard.finish": {"zh-TW": "查看目前結果", "en": "View current results"},
    "apl.wizard.view_current": {
        "zh-TW": "查看目前結果",
        "en": "View current results",
    },
    "apl.wizard.save_view": {
        "zh-TW": "儲存並查看結果",
        "en": "Save and view results",
    },
    "apl.money.unknown": {"zh-TW": "我不知道", "en": "I don't know"},
    "apl.money.unknown_help": {
        "zh-TW": "可以稍後補上；部分判定可能暫時無法完成。",
        "en": "You can add this later; some results may stay incomplete for now.",
    },
    "apl.money.amount_placeholder": {
        "zh-TW": "請輸入金額",
        "en": "Enter amount",
    },
    "apl.money.blank_is_unknown": {
        "zh-TW": "",
        "en": "",
    },
    "apl.step2.wait_for_type": {
        "zh-TW": "請先選擇公司類型，我們再問需要的財務或上市資料。",
        "en": "Choose a company type first; then we will ask only the needed details.",
    },
    "apl.money.invalid_number": {
        "zh-TW": "請輸入有效數字。",
        "en": "Please enter a valid number.",
    },
    "apl.money.unit_label": {"zh-TW": "單位", "en": "Unit"},
    "apl.money.unit.yuan": {"zh-TW": "元", "en": "TWD"},
    "apl.money.unit.wan": {"zh-TW": "萬元", "en": "10k TWD"},
    "apl.money.unit.yi": {"zh-TW": "億元", "en": "100m TWD"},
    "apl.obligation_ifrs_assurance": {
        "zh-TW": "臺灣規範：合併個體Scope 1／2溫室氣體排放確信",
        "en": (
            "Taiwan requirement: Assurance of consolidated Scope 1 and "
            "Scope 2 GHG emissions"
        ),
    },
    "apl.obligation_env_verification": {
        "zh-TW": "環境部溫室氣體查驗",
        "en": "MOENV GHG verification",
    },
    "apl.kind.ifrs_assurance": {
        "zh-TW": (
            "類型：臺灣規範之合併個體Scope 1／2溫室氣體排放確信（與環境部盤查查驗不同）"
        ),
        "en": (
            "Type: Taiwan requirement for assurance of consolidated Scope 1 "
            "and Scope 2 GHG emissions (distinct from MOENV inventory "
            "verification)"
        ),
    },
    "apl.kind.env_verification": {
        "zh-TW": "類型：台灣環境主管機關查驗",
        "en": "Type: Taiwan environmental authority verification",
    },
    "apl.basis.empty": {
        "zh-TW": "目前尚未提供自動判定。",
        "en": "An automatic determination is not available yet.",
    },
    "apl.basis.technical": {"zh-TW": "技術資訊", "en": "Technical details"},
    "apl.cta.start_prepare": {"zh-TW": "開始準備", "en": "Start preparing"},
    "apl.cta.start_prepare_ifrs": {
        "zh-TW": "開始準備 IFRS 資料",
        "en": "Start preparing IFRS data",
    },
    "apl.cta.prepare_taiwan": {
        "zh-TW": "查看台灣要求",
        "en": "View Taiwan requirements",
    },
    "apl.cta.provide_info": {"zh-TW": "補充資料", "en": "Provide information"},
    "apl.text_needs_review_fallback": {
        "zh-TW": "目前仍需補充或確認資料後才能完成判定。",
        "en": "More information is needed before this determination can be completed.",
    },
    "apl.notes_secondary": {
        "zh-TW": "部分官方版本細節仍在確認中；不影響已驗證的適用年度結論。",
        "en": "Some recognised-version details are still being confirmed.",
    },
    "apl.reason_generic.APPLICABLE": {
        "zh-TW": "依目前公司資料與已驗證規則，此要求適用。開始年度 {year}，首次申報 {filing}。",  # noqa: E501
        "en": "Applicable under the current profile and verified rules. Start year {year}; first filing {filing}.",  # noqa: E501
    },
    "apl.reason_generic.FUTURE_REQUIREMENT": {
        "zh-TW": "此要求將於未來年度適用（{year}）。",
        "en": "This requirement applies in a future year ({year}).",
    },
    "apl.reason_generic.NEEDS_INFORMATION": {
        "zh-TW": "我們還無法確認是否適用，請先補充下方資料。",
        "en": "We cannot confirm applicability yet — please provide the missing information.",  # noqa: E501
    },
    "apl.reason_generic.NEEDS_REVIEW": {
        "zh-TW": "需要進一步人工確認後才能完成判定。",
        "en": "Additional human review is required before concluding.",
    },
    "apl.reason_generic.NOT_APPLICABLE": {
        "zh-TW": "依目前資料，此要求目前不適用。",
        "en": "Not applicable based on the current profile.",
    },
    "apl.reason_generic.OUT_OF_V1_SCOPE": {
        "zh-TW": "此類型目前不在本產品第一版自動化範圍。",
        "en": "This entity type is outside V1 automated support.",
    },
    "apl.reason_generic.MANUAL_VERIFICATION_REQUIRED": {
        "zh-TW": "法規更新確認中，請稍後再判定。",
        "en": "A regulatory update is under verification.",
    },
    "apl.reason_generic.REGULATORY_DATA_STALE": {
        "zh-TW": "法規資料需要更新後才能完成判定。",
        "en": "Regulatory data must be refreshed before concluding.",
    },
    "apl.reason_generic.NOT_YET_ASSESSED": {
        "zh-TW": "尚未完成判定。",
        "en": "Not yet assessed.",
    },
    "apl.next_generic.APPLICABLE": {
        "zh-TW": "開始準備相關揭露與證據資料。",
        "en": "Start preparing the related disclosures and evidence.",
    },
    "apl.next_generic.FUTURE_REQUIREMENT": {
        "zh-TW": "可先了解時程並預作資料盤點。",
        "en": "Review the timeline and begin readiness planning.",
    },
    "apl.next_generic.NEEDS_INFORMATION": {
        "zh-TW": "補充公司資料後重新判定。",
        "en": "Provide the missing company information and reassess.",
    },
    "apl.next_generic.NEEDS_REVIEW": {
        "zh-TW": "此項目前正在確認中，你現在不需要操作。",
        "en": "This item is being confirmed. You do not need to act now.",
    },
    "apl.next_generic.NOT_APPLICABLE": {
        "zh-TW": "目前無需為此要求準備申報。",
        "en": "No filing preparation is required for this item now.",
    },
    "apl.next_generic.OUT_OF_V1_SCOPE": {
        "zh-TW": "請另循專責流程追蹤。",
        "en": "Track this obligation outside the V1 workflow.",
    },
    "apl.next_generic.MANUAL_VERIFICATION_REQUIRED": {
        "zh-TW": "等待法規確認完成後再評估。",
        "en": "Wait for regulatory verification to finish.",
    },
    "apl.next_generic.REGULATORY_DATA_STALE": {
        "zh-TW": "先更新法規監控狀態。",
        "en": "Refresh regulatory monitoring state first.",
    },
    "apl.next_generic.NOT_YET_ASSESSED": {
        "zh-TW": "完成公司設定以開始判定。",
        "en": "Complete company setup to begin assessment.",
    },
    "apl.reason.ifrs_s1_s2.APPLICABLE": {
        "zh-TW": "你的公司屬上市公司，且符合目前第一階段適用條件。",
        "en": "Your company is a listed company meeting the current first-phase conditions.",  # noqa: E501
    },
    "apl.next.ifrs_s1_s2.APPLICABLE": {
        "zh-TW": "開始準備 IFRS S1/S2 揭露資料。",
        "en": "Start preparing IFRS S1/S2 disclosure materials.",
    },
    "apl.reason.ghg_inventory.NEEDS_INFORMATION": {
        "zh-TW": "我們還無法確認是否適用溫室氣體盤查。",
        "en": "We cannot yet confirm whether GHG inventory applies.",
    },
    "apl.next.ghg_inventory.NEEDS_INFORMATION": {
        "zh-TW": "請補充台灣廠場與主管機關通知相關資料。",
        "en": "Provide Taiwan facility and authority-notice information.",
    },
    "apl.reason.carbon_fee.NEEDS_INFORMATION": {
        "zh-TW": "碳費適用性仍待補充公司與廠場資料後判定。",
        "en": "Carbon-fee applicability still needs facility information.",
    },
    "apl.next.carbon_fee.NEEDS_INFORMATION": {
        "zh-TW": "請補充台灣廠場與報導邊界相關資料。",
        "en": "Clarify Taiwan facilities and reporting boundary.",
    },
    "apl.reason.verification_assurance.APPLICABLE": {
        "zh-TW": (
            "此結果反映臺灣主管機關對適用公司之合併個體Scope 1／2溫室氣體排放"
            "確信要求，並非IFRS S1或S2本身的完整確信結論，也不同於環境部列管"
            "事業的盤查查驗。"
        ),
        "en": (
            "This result reflects the Taiwan authority's requirement for "
            "applicable companies to obtain assurance over consolidated-entity "
            "Scope 1 and Scope 2 GHG emissions. It is not a complete IFRS S1 "
            "or S2 assurance conclusion, and it is distinct from inventory "
            "verification for MOENV-regulated entities."
        ),
    },
    "apl.reason.verification_assurance.NEEDS_INFORMATION": {
        "zh-TW": (
            "臺灣規範的合併個體Scope 1／2確信時程，仍取決於IFRS適用性與公司資料。"
        ),
        "en": (
            "Timing of the Taiwan consolidated Scope 1 and Scope 2 assurance "
            "requirement still depends on the IFRS applicability assessment."
        ),
    },
    "apl.reason.verification_assurance.FUTURE_REQUIREMENT": {
        "zh-TW": (
            "臺灣規範的合併個體Scope 1／2溫室氣體排放確信，將依適用時程於未來年度發生。"
        ),
        "en": (
            "The Taiwan requirement for assurance of consolidated Scope 1 and "
            "Scope 2 GHG emissions will apply in a future year."
        ),
    },
    "apl.reason.env_verification.NEEDS_INFORMATION": {
        "zh-TW": (
            "台灣溫室氣體查驗與臺灣規範的合併個體Scope 1／2確信不同；目前還需要"
            "確認是否收到查驗要求。"
        ),
        "en": (
            "Taiwan environmental verification is distinct from the Taiwan "
            "consolidated Scope 1 and Scope 2 assurance requirement; confirm "
            "any notice received."
        ),
    },
    "apl.reason.env_verification.NEEDS_REVIEW": {
        "zh-TW": "你已表示收到查驗要求。",
        "en": "You indicated that a verification requirement was received.",
    },
    "apl.next.env_verification.NEEDS_INFORMATION": {
        "zh-TW": "補充是否曾收到環境主管機關查驗要求。",
        "en": "Confirm whether an environmental authority required verification.",
    },
    "apl.next.env_verification.NEEDS_REVIEW": {
        "zh-TW": "補充／核對主管機關通知。",
        "en": "Add or check the official notice.",
    },
    "learn.why_label": {
        "zh-TW": "為什麼需要這項資料？",
        "en": "Why is this information needed?",
    },
    "learn.where_label": {"zh-TW": "去哪裡找資料？", "en": "Where to find it?"},
    "learn.wizard.step1.title": {
        "zh-TW": "這一步需要什麼？",
        "en": "What this step needs",
    },
    "learn.wizard.step1.body": {
        "zh-TW": "輸入統一編號後，先確認帶入的公司資料是否正確。",
        "en": "After entering the business number, confirm the company we found.",
    },
    "learn.wizard.step1.where": {
        "zh-TW": "公司登記資料、最新年報或公開資訊觀測站。",
        "en": "Company registration, annual report, or market disclosure sites.",
    },
    "learn.wizard.step1.why": {
        "zh-TW": "不同公司類型的適用時程與義務不同。",
        "en": "Different entity types follow different obligation timelines.",
    },
    "learn.wizard.step2.title": {
        "zh-TW": "上市與財務資料",
        "en": "Listing & financials",
    },
    "learn.wizard.step2.body": {
        "zh-TW": "只補官方資料沒有、但判定真正需要的項目；不知道請勿填 0。",
        "en": (
            "Add only facts official data could not supply and the rules need; "
            "never enter 0 if unknown."
        ),
    },
    "learn.wizard.step2.where": {
        "zh-TW": "資產負債表「權益總額」、公司登記資本額、公開資訊觀測站。",
        "en": "Balance-sheet equity, registered capital, or disclosure filings.",
    },
    "learn.wizard.step2.why": {
        "zh-TW": "部分上市櫃適用時程依資本額分階段；淨值僅在特定情形輔助判定。",
        "en": (
            "Some listed phases depend on capital; "
            "net worth is only used in specific cases."
        ),
    },
    "learn.wizard.step3.title": {
        "zh-TW": "確認台灣廠場",
        "en": "Confirm Taiwan sites",
    },
    "learn.wizard.step3.body": {
        "zh-TW": (
            "政府名錄與上傳資料找出的據點，請確認這次是否納入。"
            "登記工廠不自動等於盤查範圍。"
        ),
        "en": (
            "Confirm whether discovered sites belong in this year's data. "
            "A registered factory is not automatically in scope."
        ),
    },
    "learn.wizard.step3.where": {
        "zh-TW": "合併財務報表附註、組織圖、永續報告書邊界說明。",
        "en": (
            "Consolidated-statement notes, org charts, "
            "sustainability boundary notes."
        ),
    },
    "learn.wizard.step3.why": {
        "zh-TW": "邊界不清會影響後續證據與揭露準備。",
        "en": "Unclear boundaries create evidence and disclosure gaps later.",
    },
    "learn.wizard.step4.title": {
        "zh-TW": "台灣廠場與通知",
        "en": "Taiwan facilities & notices",
    },
    "learn.wizard.step4.body": {
        "zh-TW": (
            "台灣盤查、環境查驗與碳費取決於廠場與主管機關通知，"
            "不是只看上傳排放量。"
        ),
        "en": (
            "Taiwan inventory, verification, and carbon fee depend on "
            "facilities and notices — not upload totals alone."
        ),
    },
    "learn.wizard.step4.where": {
        "zh-TW": "廠場清冊、環境主管機關公文／通知、既有環保許可資料。",
        "en": "Facility lists, environmental authority notices, existing permits.",
    },
    "learn.wizard.step4.why": {
        "zh-TW": "缺少這些資訊時系統會標示「還需要資料」，而不是當成違法。",
        "en": (
            "Missing facts show as “needs information”, "
            "not as a legal failure."
        ),
    },
    "learn.wizard.step5.title": {
        "zh-TW": "判定結果怎麼讀",
        "en": "How to read results",
    },
    "learn.wizard.step5.body": {
        "zh-TW": (
            "每張結果卡會說明是否適用、何時開始，以及建議下一步；"
            "官方依據預設收合。"
        ),
        "en": (
            "Each card shows applicability, timing, and next action; "
            "official basis stays collapsed."
        ),
    },
    "learn.wizard.step5.where": {
        "zh-TW": "展開「查看官方依據」可看到主管機關與文件編號。",
        "en": "Expand “View official basis” for authority and document IDs.",
    },
    "learn.wizard.step5.why": {
        "zh-TW": "先理解決策，再深入法條細節，可減少閱讀負擔。",
        "en": (
            "Understand the decision first, then dive into "
            "legal detail when needed."
        ),
    },
    "learn.hint.entity_type": {
        "zh-TW": "會影響部分要求的開始年度。",
        "en": "This can affect when some requirements start.",
    },
    "learn.why.entity_type": {
        "zh-TW": "不同公司類型的適用時程與義務不同。",
        "en": "Different company types follow different timelines.",
    },
    "learn.hint.paid_in_capital_twd": {
        "zh-TW": "通常可在公司登記資料找到。",
        "en": "Usually found in company registration records.",
    },
    "learn.hint.net_worth_twd": {
        "zh-TW": "通常可在資產負債表「權益總額」找到。",
        "en": "Usually found as total equity on the balance sheet.",
    },
    "learn.example.paid_in_capital_twd": {
        "zh-TW": "例如：實收資本額 120 億元。",
        "en": "Example: paid-in capital NT$12 billion.",
    },
    "learn.example.net_worth_twd": {
        "zh-TW": "例如：權益總額 95 億元。",
        "en": "Example: total equity NT$9.5 billion.",
    },
    "learn.why.paid_in_capital_twd": {
        "zh-TW": "部分上市櫃適用時程會依實收資本額分階段。",
        "en": "Some listed-company phases depend on paid-in capital.",
    },
    "learn.why.net_worth_twd": {
        "zh-TW": "在特定情況下，部分適用時程會使用淨值輔助判定。",
        "en": "In some cases, timing rules may also use net worth.",
    },
    "learn.why_detail.paid_in_capital_twd": {
        "zh-TW": "系統只會在相關規則需要時使用此資料，不會改寫你的財務報表。",
        "en": "Used only when a relevant rule needs it.",
    },
    "learn.why_detail.net_worth_twd": {
        "zh-TW": "若你暫時不知道，可先勾選「不知道」，不要填 0。",
        "en": "If unknown, choose “I don't know” — do not enter 0.",
    },
    "learn.panel_title": {"zh-TW": "了解這項要求", "en": "Learn this requirement"},
    "learn.req.label.what": {"zh-TW": "這是什麼？", "en": "What is it?"},
    "learn.req.label.why": {"zh-TW": "為什麼可能適用？", "en": "Why may it apply?"},
    "learn.req.label.need": {"zh-TW": "之後需要哪些資料？", "en": "What will I need?"},
    "learn.req.label.first": {"zh-TW": "建議先做什麼？", "en": "What to prepare first?"},  # noqa: E501
    "learn.req.ifrs.what": {
        "zh-TW": "IFRS S1/S2 是永續與氣候相關財務揭露準則。",
        "en": "IFRS S1/S2 are sustainability and climate disclosure standards.",
    },
    "learn.req.ifrs.why": {
        "zh-TW": "台灣已對特定上市櫃公司訂定適用時程。",
        "en": "Taiwan has set adoption timing for certain listed companies.",
    },
    "learn.req.ifrs.need": {
        "zh-TW": "治理、策略、風險與指標相關說明，以及可追溯證據。",
        "en": "Governance, strategy, risk, metrics narrative, and traceable evidence.",
    },
    "learn.req.ifrs.first": {
        "zh-TW": "先完成適用性判定，再整理 Scope 1/2 排放與相關證據。",
        "en": "Finish applicability, then organise Scope 1/2 emissions and evidence.",
    },
    "learn.req.taiwan.what": {
        "zh-TW": "台灣溫室氣體盤查、查驗與碳費是不同制度軌道。",
        "en": "Taiwan GHG inventory, verification, and carbon fee are distinct tracks.",
    },
    "learn.req.taiwan.why": {
        "zh-TW": "是否適用取決於廠場、通知與官方條件，不能只看上傳排放量。",
        "en": "Applicability depends on facilities and official criteria — not upload totals alone.",  # noqa: E501
    },
    "learn.req.taiwan.need": {
        "zh-TW": "廠場資訊、官方通知，以及後續盤查工作底稿。",
        "en": "Facility facts, official notices, and later inventory workpapers.",
    },
    "learn.req.taiwan.first": {
        "zh-TW": "先回答台灣廠場與通知問題。",
        "en": "Answer the Taiwan facility and notice questions first.",
    },
    "reg.admin.expected": {"zh-TW": "預期自動化來源", "en": "Automated sources expected"},  # noqa: E501
    "reg.admin.successful": {"zh-TW": "成功檢查", "en": "Successful checks"},
    "reg.admin.failed": {"zh-TW": "失敗檢查", "en": "Failed checks"},
    "reg.admin.config_required": {
        "zh-TW": "待設定來源",
        "en": "Configuration required",
    },
    "reg.admin.manual_access": {
        "zh-TW": "本輪需人工處理",
        "en": "Manual access this run",
    },
    "reg.admin.manual_reference": {
        "zh-TW": "人工／參考來源總數",
        "en": "Manual/reference sources",
    },
    "reg.admin.restricted": {
        "zh-TW": "限制自動化來源",
        "en": "Restricted automation sources",
    },
    "reg.admin.pending_signals": {
        "zh-TW": "待審變更訊號",
        "en": "Pending change signals",
    },
    "reg.admin.last_verified": {"zh-TW": "最後確認", "en": "Last verified"},
    "reg.admin.monitoring_health": {"zh-TW": "監控健康狀態", "en": "Monitoring health"},
    "reg.admin.supporting_note": {"zh-TW": "輔助來源說明", "en": "Supporting note"},
    "ev.reuse_title": {
        "zh-TW": "上傳一次，多處重用",
        "en": "Upload once, reuse across requirements",
    },
    "ev.reuse_help": {
        "zh-TW": "同一證據可同時支持排放計算、IFRS 指標與盤查工作底稿。",
        "en": "The same evidence can support calculations, IFRS metrics, and inventory workpapers.",  # noqa: E501
    },
    "empty.no_assessment_title": {
        "zh-TW": "先完成公司設定",
        "en": "Complete company setup first",
    },
    "empty.no_assessment_body": {
        "zh-TW": "提供幾項公司基本資料後，即可查看此處要求。",
        "en": "Share a few company basics to see the related requirements here.",
    },
    "empty.no_evidence_title": {
        "zh-TW": "尚未加入證據資料",
        "en": "No evidence uploaded yet",
    },
    "empty.no_evidence_body": {
        "zh-TW": "上傳電費單、燃料紀錄或其他活動資料後，系統會在這裡建立可追溯的證據紀錄。",  # noqa: E501
        "en": "Upload utility bills or activity data to create traceable evidence records.",  # noqa: E501
    },
    "sidebar.company_unset": {
        "zh-TW": "尚未設定公司",
        "en": "Company not set",
    },
    "sidebar.company_ubn": {
        "zh-TW": "統一編號 {ubn}",
        "en": "UBN {ubn}",
    },
    "sidebar.source_empty_detail": {
        "zh-TW": "尚未上傳公司資料",
        "en": "No company data uploaded yet",
    },
    "aud.group.ifrs": {"zh-TW": "IFRS 準備資料", "en": "IFRS preparation"},
    "aud.group.ifrs_help": {
        "zh-TW": "前往 IFRS 工作區整理揭露準備資料。",
        "en": "Open the IFRS workspace to prepare disclosure materials.",
    },
    "aud.group.ifrs_body": {
        "zh-TW": "適用性判定完成後，可在此繼續準備 IFRS S1/S2 相關資料。",
        "en": "After applicability, continue preparing IFRS S1/S2 materials.",
    },
    "aud.group.management_help": {
        "zh-TW": "給經營層閱讀的分析摘要，不是技術稽核檔。",
        "en": "An executive-readable summary — not a technical audit file.",
    },
    "aud.group.management_unavailable": {
        "zh-TW": "管理摘要匯出尚未建立。目前僅顯示畫面上的分析摘要。",
        "en": (
            "A downloadable management-summary export is not available yet. "
            "The on-screen summary is shown instead."
        ),
    },
    "aud.group.audit_pkg": {"zh-TW": "稽核包", "en": "Audit package"},
    "aud.group.audit_pkg_help": {
        "zh-TW": "下載完整技術稽核包供外部查核使用。",
        "en": "Download the full technical audit package for external review.",
    },
    "aud.group.audit_pkg_body": {
        "zh-TW": (
            "包含活動資料、排放計算、待處理問題、IFRS 資料準備度與證據追蹤"
            "（工作底稿用途，非正式申報檔）。"
        ),
        "en": (
            "Includes activities, calculations, open issues, IFRS data readiness, "
            "and evidence trail files (workpaper use, not an official filing)."
        ),
    },
    "aud.audit_trace": {"zh-TW": "稽核追溯資訊", "en": "Audit trace information"},
    "aud.tech_ids": {"zh-TW": "技術識別資訊", "en": "Technical identifiers"},
    "aud.evidence_desc": {
        "zh-TW": "已接受的來源文件與使用情形。",
        "en": "Accepted source documents and how they are used.",
    },
    "aud.advanced_audit": {
        "zh-TW": "稽核追溯資訊",
        "en": "Audit trace information",
    },
    "aud.advanced_customer_note": {
        "zh-TW": "此區提供稽核追蹤用的技術資訊，日常作業通常不需開啟。",
        "en": "Technical audit metadata — usually not needed for daily work.",
    },
    "aud.advanced_admin_only": {
        "zh-TW": "登錄庫維護與系統架構細節僅在管理模式下顯示。",
        "en": "Registry maintenance details appear in admin mode only.",
    },
    "aud.run_id_hidden": {"zh-TW": "執行識別", "en": "Run identity"},
    "aud.ingested_at": {"zh-TW": "匯入時間", "en": "Ingested at"},
    "act.col.unit": {"zh-TW": "單位", "en": "Unit"},
    "act.col.period": {"zh-TW": "活動日期／期間", "en": "Activity period"},
    "act.col.source_doc": {"zh-TW": "來源文件", "en": "Source document"},
    "act.layer.operational": {
        "zh-TW": "活動摘要",
        "en": "Activity summary",
    },
    "act.layer.basis": {"zh-TW": "查看計算依據", "en": "View calculation basis"},
    "act.layer.audit": {"zh-TW": "稽核追溯資訊", "en": "Audit trace information"},
    "act.trace_normalized": {
        "zh-TW": "正規化用量",
        "en": "Normalized quantity",
    },
    "act.trace_authority": {
        "zh-TW": "官方來源／機關",
        "en": "Official authority / source",
    },
    "iss.related.activity": {"zh-TW": "相關活動", "en": "Related activity"},
    "iss.related.document": {"zh-TW": "來源文件", "en": "Source document"},
    "iss.related.period": {"zh-TW": "期間", "en": "Period"},
    "iss.related.view_source": {
        "zh-TW": "查看來源資料",
        "en": "View source data",
    },
    "iss.audit_trace": {"zh-TW": "稽核追溯資訊", "en": "Audit trace information"},
    "ev.col.name": {"zh-TW": "文件名稱", "en": "Document name"},
    "ev.col.type": {"zh-TW": "文件類型", "en": "Document type"},
    "ev.col.period": {"zh-TW": "期間", "en": "Period"},
    "ev.col.source": {"zh-TW": "來源", "en": "Source"},
    "ev.col.used_for": {"zh-TW": "使用於", "en": "Used for"},
    "ev.col.status": {"zh-TW": "狀態", "en": "Status"},
    "ev.col.data_origin": {"zh-TW": "資料來源類型", "en": "Data origin"},
    "ev.status.demo": {"zh-TW": "示範資料", "en": "Demo data"},
    "ev.status.imported": {"zh-TW": "已匯入", "en": "Imported"},
    "ev.status.pending": {"zh-TW": "待確認", "en": "Pending review"},
    "ev.status.needs_action": {"zh-TW": "需要處理", "en": "Needs attention"},
    "ev.status.verified": {"zh-TW": "已驗證", "en": "Verified"},
    "ev.origin.company": {"zh-TW": "公司提供", "en": "Company provided"},
    "ev.reuse.none": {"zh-TW": "尚未連結使用", "en": "No linked uses yet"},
    "ev.reuse.scope1": {
        "zh-TW": "Scope 1 計算",
        "en": "Scope 1 calculation",
    },
    "ev.reuse.scope2": {
        "zh-TW": "Scope 2 計算",
        "en": "Scope 2 calculation",
    },
    "ev.reuse.calculation": {
        "zh-TW": "排放計算",
        "en": "Emissions calculation",
    },
    "ev.reuse.ifrs": {
        "zh-TW": "IFRS S2 指標證據",
        "en": "IFRS S2 metrics evidence",
    },
    "ev.reuse.ghg": {
        "zh-TW": "GHG 盤查工作底稿",
        "en": "GHG inventory workpaper",
    },
    "ev.drill.title": {"zh-TW": "文件詳情", "en": "Document detail"},
    "ev.drill.usage": {"zh-TW": "計算與使用情形", "en": "Calculation & usage"},
    "ev.drill.source": {"zh-TW": "官方／資料來源", "en": "Source details"},
    "ev.drill.audit": {"zh-TW": "稽核追溯資訊", "en": "Audit trace information"},
    "ev.doc_type.other": {"zh-TW": "其他文件", "en": "Other document"},
    "ev.doc_type.utility_bill": {"zh-TW": "電費帳單", "en": "Utility bill"},
    "ev.doc_type.invoice": {"zh-TW": "發票", "en": "Invoice"},
    "ev.doc_type.receipt": {"zh-TW": "收據", "en": "Receipt"},
    "fw.sasb_title": {
        "zh-TW": "系統建議的 SASB 產業分類",
        "en": "Suggested SASB industry classification",
    },
    "fw.sasb_help": {
        "zh-TW": "此分類屬 IFRS 準備細節，可稍後再確認，不必在公司設定時完成。",
        "en": "SASB classification belongs to IFRS prep and can be set later.",
    },
    "fw.sasb_unset": {
        "zh-TW": "尚未設定。可在準備 IFRS 揭露時再確認或修改。",
        "en": "Not set yet. Confirm or edit later during IFRS preparation.",
    },
    "fw.sasb_current": {"zh-TW": "目前分類", "en": "Current classification"},
    "fw.sasb_edit": {"zh-TW": "確認／修改", "en": "Confirm / edit"},
    "fw.sasb_save": {"zh-TW": "儲存 SASB 分類", "en": "Save SASB classification"},
    "cust.status.applicable": {"zh-TW": "適用", "en": "Applies"},
    "cust.status.not_applicable": {
        "zh-TW": "目前不適用",
        "en": "Does not apply now",
    },
    "cust.status.future_applicable": {
        "zh-TW": "未來將適用",
        "en": "Will apply later",
    },
    "cust.status.needs_company_data": {
        "zh-TW": "還需要一些資料",
        "en": "A few details still needed",
    },
    "cust.status.system_review": {
        "zh-TW": "正在確認中",
        "en": "Being confirmed",
    },
    "cust.status.no_automatic_result": {
        "zh-TW": "目前尚未提供自動判定",
        "en": "Automatic result not available yet",
    },
    "cust.status.not_started": {"zh-TW": "尚未開始", "en": "Not started"},
    "cust.status.unsupported": {
        "zh-TW": "目前版本暫不支援",
        "en": "Not supported in this version",
    },
    "cust.fact.taiwan_facility": {
        "zh-TW": "台灣廠場／營運據點",
        "en": "Taiwan sites / operations",
    },
    "cust.fact.authority_notice": {
        "zh-TW": "是否收到主管機關盤查或查驗通知",
        "en": "Whether an authority inventory or verification notice was received",
    },
    "cust.fact.reporting_scope": {
        "zh-TW": "這次報告包含哪些公司",
        "en": "Which companies this report includes",
    },
    "cust.fact.paid_in_capital": {"zh-TW": "實收資本額", "en": "Paid-in capital"},
    "cust.fact.net_worth": {"zh-TW": "公司淨值", "en": "Net worth"},
    "cust.fact.listing": {
        "zh-TW": "公司是否上市／上櫃",
        "en": "Whether the company is listed / OTC",
    },
    "cust.fact.entity_type": {"zh-TW": "公司類型", "en": "Company type"},
    "cust.timing.start_year": {
        "zh-TW": "{year} 年開始適用",
        "en": "Applies from {year}",
    },
    "cust.timing.first_filing": {
        "zh-TW": "{year} 年首次申報",
        "en": "First filing in {year}",
    },
    "cust.explain.applicable": {
        "zh-TW": "此要求適用於你的公司。",
        "en": "This requirement applies to your company.",
    },
    "cust.explain.not_applicable": {
        "zh-TW": "依目前資料，此要求目前不適用。",
        "en": "Based on current information, this does not apply now.",
    },
    "cust.explain.future_applicable": {
        "zh-TW": "此要求將於未來年度適用。",
        "en": "This requirement will apply in a later year.",
    },
    "cust.explain.needs_company_data": {
        "zh-TW": "還需要一些公司資料才能完成這項判定。",
        "en": "A few company details are still needed to finish this result.",
    },
    "cust.explain.system_review": {
        "zh-TW": "此項目前正在確認中，你現在不需要操作。",
        "en": "This item is being confirmed. You do not need to act now.",
    },
    "cust.explain.no_automatic_result": {
        "zh-TW": "目前尚未提供自動判定。",
        "en": "An automatic determination is not available yet.",
    },
    "cust.explain.not_started": {
        "zh-TW": "相關設定尚未完成。",
        "en": "This workflow has not been completed yet.",
    },
    "cust.explain.unsupported": {
        "zh-TW": "目前版本暫不支援此項。",
        "en": "This version does not support this item yet.",
    },
    "cust.explain.ifrs.needs_company_data": {
        "zh-TW": "還需要一些公司資料，才能確認適用時程。",
        "en": "A few company details are still needed to confirm the timeline.",
    },
    "cust.explain.ifrs.applicable": {
        "zh-TW": "你的公司屬於目前第一階段適用範圍。",
        "en": "Your company is in the current first-phase scope.",
    },
    "cust.explain.ifrs_assurance.needs_company_data": {
        "zh-TW": (
            "IFRS適用時程確認後，才能判斷臺灣規範的合併個體Scope 1／2確信準備時點。"
        ),
        "en": (
            "Timing of the Taiwan consolidated Scope 1 and Scope 2 assurance "
            "requirement follows the IFRS applicability timeline."
        ),
    },
    "cust.explain.ifrs_assurance.applicable": {
        "zh-TW": (
            "此結果反映臺灣主管機關對適用公司之合併個體Scope 1／2溫室氣體排放"
            "確信要求，並非IFRS S1或S2本身的完整確信結論，也不同於環境部列管"
            "事業的盤查查驗。"
        ),
        "en": (
            "This result reflects the Taiwan authority's requirement for "
            "applicable companies to obtain assurance over consolidated-entity "
            "Scope 1 and Scope 2 GHG emissions. It is not a complete IFRS S1 "
            "or S2 assurance conclusion, and it is distinct from inventory "
            "verification for MOENV-regulated entities."
        ),
    },
    "cust.explain.ghg_inventory.needs_company_data": {
        "zh-TW": (
            "我們還需要確認公司是否有台灣廠場，以及是否曾收到主管機關"
            "要求盤查或登錄溫室氣體的通知。"
        ),
        "en": (
            "We still need to confirm Taiwan sites and whether an authority "
            "asked the company to inventory or register GHG."
        ),
    },
    "cust.explain.env_verification.needs_company_data": {
        "zh-TW": "特定受管制企業可能需要由第三方查驗排放資料。",
        "en": "Some regulated companies may need third-party emission verification.",
    },
    "cust.explain.env_verification.received": {
        "zh-TW": "你已表示收到查驗要求。",
        "en": "You indicated that a verification requirement was received.",
    },
    "cust.explain.carbon_fee.needs_company_data": {
        "zh-TW": "目前還無法確認是否涉及碳費。",
        "en": "We cannot yet confirm whether a carbon fee applies.",
    },
    "cust.q.ghg_inventory": {
        "zh-TW": "公司需要向環境部盤查／登錄溫室氣體嗎？",
        "en": "Does the company need to inventory / register GHG with MOENV?",
    },
    "cust.q.env_verification": {
        "zh-TW": "公司需要第三方查驗溫室氣體資料嗎？",
        "en": "Does the company need third-party GHG verification?",
    },
    "cust.q.carbon_fee": {
        "zh-TW": "公司可能需要繳碳費嗎？",
        "en": "Might the company need to pay a carbon fee?",
    },
    "cust.meaning.ghg_inventory": {
        "zh-TW": "如果適用，公司需要整理年度排放資料並依規定完成登錄。",
        "en": (
            "If this applies, the company must compile annual emissions "
            "and complete registration."
        ),
    },
    "cust.meaning.env_verification": {
        "zh-TW": "如果適用，需要由合格第三方檢查公司的排放資料。",
        "en": (
            "If this applies, a qualified third party must check "
            "the emissions data."
        ),
    },
    "cust.meaning.carbon_fee": {
        "zh-TW": "符合相關法規條件的排放來源，可能成為碳費徵收對象。",
        "en": (
            "Emissions that meet the legal conditions may be subject "
            "to the carbon fee."
        ),
    },
    "cust.answer.need": {"zh-TW": "需要", "en": "Yes, it is needed"},
    "cust.answer.not_need": {"zh-TW": "目前不需要", "en": "Not needed now"},
    "cust.answer.future": {"zh-TW": "未來年度再確認", "en": "Confirm in a later year"},
    "cust.results.heading": {
        "zh-TW": "你的公司目前需要做什麼？",
        "en": "What does your company need to do now?",
    },
    "cust.results.outcomes": {"zh-TW": "判定結果", "en": "Results"},
    "cust.action.missing_count": {
        "zh-TW": "還差 {n} 項資料",
        "en": "{n} more detail(s) needed",
    },
    "cust.action.after_answer": {
        "zh-TW": "完成後，我們會更新下方的台灣要求判定。",
        "en": "After this, we will update the Taiwan results below.",
    },
    "cust.q.missing_notice": {
        "zh-TW": "公司是否曾收到主管機關要求盤查、登錄或查驗溫室氣體的通知？",
        "en": (
            "Has the company received an authority notice requiring GHG "
            "inventory, registration, or verification?"
        ),
    },
    "cust.q.missing_facilities": {
        "zh-TW": "請先確認政府找到的台灣工廠今年是否仍由公司營運。",
        "en": (
            "Please confirm whether the found Taiwan factories "
            "still operate this year."
        ),
    },
    "cust.cta.confirm_notice": {
        "zh-TW": "確認主管機關通知",
        "en": "Confirm the authority notice",
    },
    "cust.cta.notice_yes": {"zh-TW": "有", "en": "Yes"},
    "cust.cta.notice_no": {"zh-TW": "沒有", "en": "No"},
    "cust.cta.notice_unsure": {"zh-TW": "不確定", "en": "Not sure"},
    "cust.cta.provide_company_facts": {
        "zh-TW": "補上公司資料",
        "en": "Add company details",
    },
    "cust.cta.prepare_emissions": {
        "zh-TW": "補上完整年度排放資料",
        "en": "Prepare the full-year emissions data",
    },
    "cust.cta.confirm_facilities": {
        "zh-TW": "確認台灣廠場",
        "en": "Confirm Taiwan sites",
    },
    "cust.action.taiwan_missing": {
        "zh-TW": "還差 {n} 項資料，就能完成 {m} 個台灣要求的判定",
        "en": "{n} more detail(s) would complete {m} Taiwan requirement(s)",
    },
    "cust.action.missing": {
        "zh-TW": "還差 {n} 項資料就能完成判定",
        "en": "{n} more detail(s) would complete the results",
    },
    "cust.action.need_profile": {
        "zh-TW": "先完成公司基本資料，才能整理適用要求。",
        "en": "Complete company basics first so we can list related requirements.",
    },
    "setup.ubn.label": {"zh-TW": "統一編號", "en": "Unified business number"},
    "setup.ubn.help": {
        "zh-TW": "輸入統一編號，我們會從目前的官方公司資料中尋找。",
        "en": (
            "Enter the unified business number to search "
            "the current official company data."
        ),
    },
    "setup.lookup": {"zh-TW": "查詢公司", "en": "Look up company"},
    "setup.found": {"zh-TW": "我們找到：", "en": "We found:"},
    "setup.status": {"zh-TW": "公司狀態", "en": "Company status"},
    "setup.address": {"zh-TW": "公司地址", "en": "Company address"},
    "setup.capital": {"zh-TW": "實收資本額", "en": "Paid-in capital"},
    "setup.listing": {"zh-TW": "公司類型 / 市場資訊", "en": "Market status"},
    "setup.listing.TWSE": {"zh-TW": "上市", "en": "TWSE listed"},
    "setup.listing.TPEX": {"zh-TW": "上櫃", "en": "TPEx listed"},
    "setup.listing.PUBLIC": {"zh-TW": "公開發行", "en": "Public company"},
    "setup.business_items": {
        "zh-TW": "主要營業項目",
        "en": "Registered business items",
    },
    "setup.source": {"zh-TW": "資料來源", "en": "Source"},
    "setup.source.open_data": {
        "zh-TW": "政府公開資料",
        "en": "Government open data",
    },
    "setup.source.gcis": {
        "zh-TW": "政府公開資料",
        "en": "Government open data",
    },
    "setup.data_as_of": {"zh-TW": "資料更新至", "en": "Data current as of"},
    "setup.last_lookup": {"zh-TW": "資料更新至", "en": "Data current as of"},
    "setup.confirm_company": {"zh-TW": "這是我的公司", "en": "This is my company"},
    "setup.confirm_company_ok": {
        "zh-TW": "已確認公司資料。",
        "en": "Company confirmed.",
    },
    "setup.data_wrong": {"zh-TW": "資料不正確", "en": "Some details are incorrect"},
    "setup.data_wrong.help": {
        "zh-TW": "你可以修正公司名稱或地址。官方登記資料仍會保留。",
        "en": (
            "You can correct the company name or address. "
            "The official registered values are kept."
        ),
    },
    "setup.retry": {"zh-TW": "稍後重試", "en": "Try again later"},
    "setup.manual": {"zh-TW": "手動填寫公司資料", "en": "Enter company details"},
    "setup.not_found": {
        "zh-TW": "目前的官方公司資料庫沒有找到這個統編。",
        "en": (
            "This unified business number is not in the current "
            "official company database."
        ),
    },
    "setup.not_found.hint": {
        "zh-TW": "目前資料庫以公開發行／上市櫃等官方公開公司資料為主。",
        "en": (
            "Coverage currently focuses on official public / listed "
            "company open data."
        ),
    },
    "setup.stale": {
        "zh-TW": "目前的官方公司資料庫沒有找到這個統編。",
        "en": (
            "This unified business number is not in the current "
            "official company database."
        ),
    },
    "setup.capital_source": {
        "zh-TW": "來源：政府公開資料",
        "en": "Source: government open data",
    },
    "setup.capital_edit": {"zh-TW": "修改", "en": "Edit"},
    "setup.listing_source": {
        "zh-TW": "依證交所／櫃買中心公開資料建議。",
        "en": "Suggested from TWSE / TPEx open data.",
    },
    "setup.net_worth_help": {
        "zh-TW": "公司淨值通常可在最新資產負債表的「權益總額」找到。",
        "en": "Net worth is usually total equity on the latest balance sheet.",
    },
    "setup.group.label": {
        "zh-TW": "這次報告包含哪些公司？",
        "en": "Which companies does this report include?",
    },
    "setup.group.SELF_ONLY": {"zh-TW": "僅本公司", "en": "This company only"},
    "setup.group.WITH_SUBSIDIARIES": {
        "zh-TW": "還包含子公司",
        "en": "Includes subsidiaries",
    },
    "setup.group.UNKNOWN": {"zh-TW": "還不確定", "en": "Not sure yet"},
    "setup.group.help": {
        "zh-TW": "這與廠場不同：這裡問的是公司／子公司，不是工廠地址。",
        "en": "This is about companies, not physical sites.",
    },
    "setup.facilities.aligned": {
        "zh-TW": "我們找到 {n} 個據點，資料一致。",
        "en": "We found {n} sites, and the sources agree.",
    },
    "setup.facilities.review": {
        "zh-TW": "我們找到 {n} 個可能的台灣廠場，請確認。",
        "en": "We found {n} possible Taiwan sites. Please confirm.",
    },
    "setup.facilities.confirm_include": {
        "zh-TW": (
            "我們找到以下可能的廠場，請確認這次是否需要納入。"
            "這會用來確認這次排放資料要包含哪些據點。"
        ),
        "en": (
            "Please confirm which discovered sites belong in this year's data. "
            "This decides which sites the emissions data should cover."
        ),
    },
    "setup.facilities.title": {"zh-TW": "確認台灣廠場", "en": "Confirm Taiwan sites"},
    "setup.facilities.found_official": {
        "zh-TW": "根據政府公開資料，我們找到 {n} 個登記工廠。",
        "en": "Official public records show {n} registered factories.",
    },
    "setup.facilities.still_operating": {
        "zh-TW": "這些工廠在 {year} 年是否都仍由公司營運？",
        "en": "Are these factories still operated by the company in {year}?",
    },
    "setup.facilities.confirm_all": {
        "zh-TW": "是，{n} 個都正確",
        "en": "Yes, all {n} are correct",
    },
    "setup.facilities.exceptions": {
        "zh-TW": "有廠場已停用、出售或資料不正確",
        "en": "Some sites are closed, sold, or incorrect",
    },
    "setup.facilities.view_list": {
        "zh-TW": "查看找到的 {n} 個廠場",
        "en": "View the {n} found sites",
    },
    "setup.facilities.source_once": {
        "zh-TW": "資料來源：政府登記工廠公開資料",
        "en": "Source: official registered-factory public data",
    },
    "setup.facilities.as_of": {
        "zh-TW": "資料更新至：{date}",
        "en": "Data as of: {date}",
    },
    "setup.facilities.discrepancy_n": {
        "zh-TW": "有 {n} 個據點需要確認",
        "en": "{n} site(s) need confirmation",
    },
    "setup.facilities.diff.official_only": {
        "zh-TW": "政府資料有此工廠，但這次上傳資料沒有出現。",
        "en": "In government data, but not in this upload.",
    },
    "setup.facilities.diff.upload_only": {
        "zh-TW": "上傳資料有此據點，但政府工廠名錄沒有。",
        "en": "In the upload, but not in the official factory list.",
    },
    "setup.facilities.none_found": {
        "zh-TW": "目前政府公開資料沒有找到登記工廠。",
        "en": "No registered factories were found in the official public data.",
    },
    "setup.facilities.confirm_none": {
        "zh-TW": "確認公司沒有台灣廠場",
        "en": "Confirm the company has no Taiwan sites",
    },
    "setup.facilities.confirm_statuses": {
        "zh-TW": "確認這些廠場狀態",
        "en": "Confirm these site statuses",
    },
    "setup.facilities.exception_need_confirm_title": {
        "zh-TW": "請先確認廠場狀態",
        "en": "Please confirm site statuses first",
    },
    "setup.facilities.exception_need_confirm_body": {
        "zh-TW": "請確認每個廠場的最新狀態，再按『確認這些廠場狀態』。",
        "en": (
            "Confirm each site's latest status, then select "
            "‘Confirm these site statuses’."
        ),
    },
    "ifrs.timeline.heading": {
        "zh-TW": "IFRS永續揭露法規時程（非公司完成度）",
        "en": (
            "IFRS sustainability disclosure regulatory timeline "
            "(not company completion)"
        ),
    },
    "ifrs.timeline.rows_heading": {
        "zh-TW": "適用結果",
        "en": "Applicability results",
    },
    "ifrs.result.product_scope": {
        "zh-TW": (
            "目前系統支援：\n"
            "✓ 適用年度與首次申報年度判定\n"
            "✓ 永續揭露報導個體確認\n"
            "尚未支援：\n"
            "— IFRS S1／S2完整揭露內容編製\n"
            "— 合規聲明或第三方確信結論"
        ),
        "en": (
            "Currently supported:\n"
            "✓ Determination of the applicable reporting year and first "
            "filing year\n"
            "✓ Confirmation of the sustainability disclosure reporting entity\n"
            "Not currently supported:\n"
            "— Preparation of complete IFRS S1/S2 disclosures\n"
            "— Compliance statements or third-party assurance conclusions"
        ),
    },
    "ifrs.readiness.title": {
        "zh-TW": "IFRS S1／S2 揭露準備清單",
        "en": "IFRS S1/S2 disclosure readiness checklist",
    },
    "ifrs.readiness.note": {
        "zh-TW": (
            "以下僅整理目前系統中可取得的資料，不代表已符合 IFRS S1／S2，"
            "也不是公司實際完成率。"
        ),
        "en": (
            "This list only summarises data currently available in the system. "
            "It does not mean the company meets IFRS S1/S2 and is not a "
            "company completion rate."
        ),
    },
    "ifrs.readiness.status.available": {
        "zh-TW": "系統已有資料",
        "en": "Data available in the system",
    },
    "ifrs.readiness.status.missing": {
        "zh-TW": "尚未提供資料",
        "en": "Information not yet provided",
    },
    "ifrs.readiness.status.unsupported": {
        "zh-TW": "目前產品尚未支援",
        "en": "Not supported by the current product",
    },
    "ifrs.readiness.section.s1": {
        "zh-TW": "S1 共通編製基礎",
        "en": "S1 general preparation foundations",
    },
    "ifrs.readiness.section.s2": {
        "zh-TW": "S2 氣候相關揭露資料",
        "en": "S2 climate-related disclosure information",
    },
    "ifrs.readiness.item.reporting_period.name": {
        "zh-TW": "報導期間",
        "en": "Reporting period",
    },
    "ifrs.readiness.item.reporting_period.why.available": {
        "zh-TW": "系統已有本期報導年度或期間資料。",
        "en": "A reporting year or period is already recorded in the system.",
    },
    "ifrs.readiness.item.reporting_period.next.available": {
        "zh-TW": "建議下一步：請確認期間起迄與相關財務報表期間一致。",
        "en": (
            "Suggested next step: Confirm that the period matches the related "
            "financial statements."
        ),
    },
    "ifrs.readiness.item.reporting_period.why.missing": {
        "zh-TW": "系統尚未取得有效的報導年度或期間。",
        "en": "No valid reporting year or period is available in the system yet.",
    },
    "ifrs.readiness.item.reporting_period.next.missing": {
        "zh-TW": "建議下一步：請在公司設定中確認報導年度。",
        "en": "Suggested next step: Confirm the reporting year in company setup.",
    },
    "ifrs.readiness.item.reporting_entity.name": {
        "zh-TW": "永續揭露報導個體",
        "en": "Sustainability disclosure reporting entity",
    },
    "ifrs.readiness.item.reporting_entity.why.available": {
        "zh-TW": "系統已有已確認的永續揭露報導個體資料。",
        "en": (
            "A confirmed sustainability disclosure reporting entity is already "
            "recorded in the system."
        ),
    },
    "ifrs.readiness.item.reporting_entity.next.available": {
        "zh-TW": "建議下一步：請核對法律實體範圍是否與實際使用的財務報表一致。",
        "en": (
            "Suggested next step: Check that the legal-entity coverage matches "
            "the financial statements actually used."
        ),
    },
    "ifrs.readiness.item.reporting_entity.why.missing": {
        "zh-TW": "系統尚未確認本期永續揭露報導個體。",
        "en": (
            "The sustainability disclosure reporting entity for this period "
            "has not yet been confirmed."
        ),
    },
    "ifrs.readiness.item.reporting_entity.next.missing": {
        "zh-TW": "建議下一步：請依實際使用的個別或合併財務報表確認報導個體。",
        "en": (
            "Suggested next step: Confirm the reporting entity from the "
            "standalone or consolidated financial statements actually used."
        ),
    },
    "ifrs.readiness.item.materiality.name": {
        "zh-TW": "重大永續風險與機會辨認",
        "en": "Identification of material sustainability risks and opportunities",
    },
    "ifrs.readiness.item.materiality.why.unsupported": {
        "zh-TW": "系統目前未蒐集重大永續風險與機會辨認資料。",
        "en": (
            "The system does not currently collect identification of material "
            "sustainability risks and opportunities."
        ),
    },
    "ifrs.readiness.item.materiality.next.unsupported": {
        "zh-TW": (
            "建議下一步：由永續與財務部門辨認可能影響現金流、融資或資本成本的"
            "重大議題。"
        ),
        "en": (
            "Suggested next step: Have sustainability and finance teams identify "
            "topics that may affect cash flows, financing or cost of capital."
        ),
    },
    "ifrs.readiness.item.governance.name": {
        "zh-TW": "治理",
        "en": "Governance",
    },
    "ifrs.readiness.item.governance.why.unsupported": {
        "zh-TW": "系統目前未蒐集永續治理職權與監督資料。",
        "en": (
            "The system does not currently collect sustainability governance "
            "and oversight information."
        ),
    },
    "ifrs.readiness.item.governance.next.unsupported": {
        "zh-TW": "建議下一步：請整理董事會或管理階層如何監督永續相關風險與機會。",
        "en": (
            "Suggested next step: Document how the board or management oversees "
            "sustainability-related risks and opportunities."
        ),
    },
    "ifrs.readiness.item.strategy.name": {
        "zh-TW": "策略",
        "en": "Strategy",
    },
    "ifrs.readiness.item.strategy.why.unsupported": {
        "zh-TW": "系統目前未蒐集永續策略與商業模式影響資料。",
        "en": (
            "The system does not currently collect sustainability strategy or "
            "business-model impact information."
        ),
    },
    "ifrs.readiness.item.strategy.next.unsupported": {
        "zh-TW": "建議下一步：請說明重大永續議題如何影響策略、商業模式與財務規劃。",
        "en": (
            "Suggested next step: Explain how material sustainability topics "
            "affect strategy, the business model and financial planning."
        ),
    },
    "ifrs.readiness.item.risk_management.name": {
        "zh-TW": "風險管理",
        "en": "Risk management",
    },
    "ifrs.readiness.item.risk_management.why.unsupported": {
        "zh-TW": "系統目前未蒐集永續風險管理流程資料。",
        "en": (
            "The system does not currently collect sustainability risk-management "
            "process information."
        ),
    },
    "ifrs.readiness.item.risk_management.next.unsupported": {
        "zh-TW": "建議下一步：請說明如何辨認、評估、優先排序及監控永續相關風險。",
        "en": (
            "Suggested next step: Describe how sustainability-related risks are "
            "identified, assessed, prioritised and monitored."
        ),
    },
    "ifrs.readiness.item.metrics_targets.name": {
        "zh-TW": "指標與目標",
        "en": "Metrics and targets",
    },
    "ifrs.readiness.item.metrics_targets.why.unsupported": {
        "zh-TW": "系統目前未蒐集永續指標與目標的正式揭露資料。",
        "en": (
            "The system does not currently collect formal sustainability metrics "
            "and targets for disclosure."
        ),
    },
    "ifrs.readiness.item.metrics_targets.next.unsupported": {
        "zh-TW": "建議下一步：請整理用以監督重大永續風險與機會的指標及目標。",
        "en": (
            "Suggested next step: Compile the metrics and targets used to "
            "monitor material sustainability risks and opportunities."
        ),
    },
    "ifrs.readiness.item.financial_connectivity.name": {
        "zh-TW": "與財務報表及其他一般用途財務報告的連結",
        "en": (
            "Connectivity with financial statements and other general-purpose "
            "financial reports"
        ),
    },
    "ifrs.readiness.item.financial_connectivity.why.unsupported": {
        "zh-TW": "系統目前未蒐集永續資訊與財務報表的連結說明。",
        "en": (
            "The system does not currently collect explanations linking "
            "sustainability information to the financial statements."
        ),
    },
    "ifrs.readiness.item.financial_connectivity.next.unsupported": {
        "zh-TW": (
            "建議下一步：請核對永續揭露與相關財務報表及其他一般用途財務報告的"
            "連結。"
        ),
        "en": (
            "Suggested next step: Check the links between sustainability "
            "disclosures and the related financial statements and other "
            "general-purpose financial reports."
        ),
    },
    "ifrs.readiness.item.physical_risk.name": {
        "zh-TW": "氣候相關實體風險",
        "en": "Climate-related physical risks",
    },
    "ifrs.readiness.item.physical_risk.why.unsupported": {
        "zh-TW": "系統目前未蒐集氣候相關實體風險。",
        "en": "The system does not currently collect climate-related physical risks.",
    },
    "ifrs.readiness.item.physical_risk.next.unsupported": {
        "zh-TW": (
            "建議下一步：由永續、營運及風險管理部門辨認可能影響資產或營運的"
            "實體風險。"
        ),
        "en": (
            "Suggested next step: Have sustainability, operations and risk teams "
            "identify physical risks that may affect assets or operations."
        ),
    },
    "ifrs.readiness.item.transition_risk.name": {
        "zh-TW": "氣候相關轉型風險",
        "en": "Climate-related transition risks",
    },
    "ifrs.readiness.item.transition_risk.why.unsupported": {
        "zh-TW": "系統目前未蒐集政策、技術、市場及法規轉型風險。",
        "en": (
            "The system does not currently collect policy, technology, market "
            "or regulatory transition risks."
        ),
    },
    "ifrs.readiness.item.transition_risk.next.unsupported": {
        "zh-TW": (
            "建議下一步：由永續、財務及風險管理部門共同辨認可能影響現金流、"
            "融資或資本成本的轉型風險。"
        ),
        "en": (
            "Suggested next step: Have sustainability, finance and risk teams "
            "jointly identify transition risks that may affect cash flows, "
            "financing or cost of capital."
        ),
    },
    "ifrs.readiness.item.climate_opportunity.name": {
        "zh-TW": "氣候相關機會",
        "en": "Climate-related opportunities",
    },
    "ifrs.readiness.item.climate_opportunity.why.unsupported": {
        "zh-TW": "系統目前未蒐集氣候相關機會資料。",
        "en": (
            "The system does not currently collect climate-related opportunity "
            "information."
        ),
    },
    "ifrs.readiness.item.climate_opportunity.next.unsupported": {
        "zh-TW": "建議下一步：請辨認可能影響策略或財務績效的氣候相關機會。",
        "en": (
            "Suggested next step: Identify climate-related opportunities that "
            "may affect strategy or financial performance."
        ),
    },
    "ifrs.readiness.item.scope_1.name": {
        "zh-TW": "Scope 1 排放資料",
        "en": "Scope 1 emissions data",
    },
    "ifrs.readiness.item.scope_2.name": {
        "zh-TW": "Scope 2 排放資料",
        "en": "Scope 2 emissions data",
    },
    "ifrs.readiness.item.scope_1.why.available": {
        "zh-TW": (
            "系統已有排放計算資料；仍需確認報導邊界、衡量方法、假設及揭露所需佐證。"
        ),
        "en": (
            "Calculated emissions data is available in the system; reporting "
            "boundary, measurement methods, assumptions, and supporting evidence "
            "for disclosure still need to be confirmed."
        ),
    },
    "ifrs.readiness.item.scope_2.why.available": {
        "zh-TW": (
            "系統已有排放計算資料；仍需確認報導邊界、衡量方法、假設及揭露所需佐證。"
        ),
        "en": (
            "Calculated emissions data is available in the system; reporting "
            "boundary, measurement methods, assumptions, and supporting evidence "
            "for disclosure still need to be confirmed."
        ),
    },
    "ifrs.readiness.item.scope_1.next.available": {
        "zh-TW": "建議下一步：請核對組織邊界、方法與佐證是否足以支持揭露。",
        "en": (
            "Suggested next step: Check whether the organisational boundary, "
            "methods and evidence are sufficient to support disclosure."
        ),
    },
    "ifrs.readiness.item.scope_2.next.available": {
        "zh-TW": "建議下一步：請核對組織邊界、方法與佐證是否足以支持揭露。",
        "en": (
            "Suggested next step: Check whether the organisational boundary, "
            "methods and evidence are sufficient to support disclosure."
        ),
    },
    "ifrs.readiness.item.scope_1.why.missing": {
        "zh-TW": "系統尚未有此 Scope 的排放計算結果。",
        "en": "No calculated emissions result for this scope is in the system yet.",
    },
    "ifrs.readiness.item.scope_2.why.missing": {
        "zh-TW": "系統尚未有此 Scope 的排放計算結果。",
        "en": "No calculated emissions result for this scope is in the system yet.",
    },
    "ifrs.readiness.item.scope_1.next.missing": {
        "zh-TW": "建議下一步：請上傳活動資料並完成計算後再回到此清單。",
        "en": (
            "Suggested next step: Upload activity data, complete the calculation, "
            "then return to this checklist."
        ),
    },
    "ifrs.readiness.item.scope_2.next.missing": {
        "zh-TW": "建議下一步：請上傳活動資料並完成計算後再回到此清單。",
        "en": (
            "Suggested next step: Upload activity data, complete the calculation, "
            "then return to this checklist."
        ),
    },
    "ifrs.readiness.item.scope_3.name": {
        "zh-TW": "Scope 3 排放資料",
        "en": "Scope 3 emissions data",
    },
    "ifrs.readiness.item.scope_3.why.unsupported": {
        "zh-TW": "目前產品尚未支援 Scope 3 排放資料蒐集與計算。",
        "en": (
            "The current product does not support Scope 3 emissions collection "
            "or calculation."
        ),
    },
    "ifrs.readiness.item.scope_3.next.unsupported": {
        "zh-TW": (
            "建議下一步：請另以公司既有流程整理重大 Scope 3 類別，"
            "勿將本系統結果視為 Scope 3 揭露。"
        ),
        "en": (
            "Suggested next step: Compile material Scope 3 categories through "
            "existing company processes. Do not treat this system's result as "
            "a Scope 3 disclosure."
        ),
    },
    "ifrs.readiness.item.measurement_methods.name": {
        "zh-TW": "排放衡量方法、係數、估計與假設",
        "en": "Measurement methods, factors, estimates and assumptions",
    },
    "ifrs.readiness.item.measurement_methods.why.available": {
        "zh-TW": (
            "系統計算結果中已有係數、來源或方法紀錄；揭露時仍須檢視估計與假設。"
        ),
        "en": (
            "Factor, source or method records are present in the calculation "
            "results; estimates and assumptions still need review for disclosure."
        ),
    },
    "ifrs.readiness.item.measurement_methods.next.available": {
        "zh-TW": "建議下一步：請核對係數版本、來源與重大估計是否足以支持揭露。",
        "en": (
            "Suggested next step: Check whether factor versions, sources and "
            "significant estimates are sufficient to support disclosure."
        ),
    },
    "ifrs.readiness.item.measurement_methods.why.missing": {
        "zh-TW": "系統尚未有可用的排放衡量方法、係數或來源紀錄。",
        "en": (
            "No usable measurement-method, factor or source records are in the "
            "system yet."
        ),
    },
    "ifrs.readiness.item.measurement_methods.next.missing": {
        "zh-TW": "建議下一步：請完成排放計算，使結果包含係數與方法資訊。",
        "en": (
            "Suggested next step: Complete the emissions calculation so the "
            "result includes factor and method information."
        ),
    },
    "ifrs.readiness.item.climate_metrics_targets.name": {
        "zh-TW": "氣候相關指標與目標",
        "en": "Climate-related metrics and targets",
    },
    "ifrs.readiness.item.climate_metrics_targets.why.unsupported": {
        "zh-TW": "系統目前未蒐集氣候相關指標與目標。",
        "en": (
            "The system does not currently collect climate-related metrics and "
            "targets."
        ),
    },
    "ifrs.readiness.item.climate_metrics_targets.next.unsupported": {
        "zh-TW": "建議下一步：請整理用以監督氣候風險與機會的指標、目標及進度。",
        "en": (
            "Suggested next step: Compile the metrics, targets and progress used "
            "to monitor climate risks and opportunities."
        ),
    },
    "ifrs.readiness.item.scenario_analysis.name": {
        "zh-TW": "氣候情境分析與韌性評估",
        "en": "Climate scenario analysis and resilience assessment",
    },
    "ifrs.readiness.item.scenario_analysis.why.unsupported": {
        "zh-TW": "系統目前未蒐集氣候情境分析與韌性評估。",
        "en": (
            "The system does not currently collect climate scenario analysis or "
            "resilience assessment."
        ),
    },
    "ifrs.readiness.item.scenario_analysis.next.unsupported": {
        "zh-TW": "建議下一步：請由永續與風險管理部門評估策略在不同氣候情境下的韌性。",
        "en": (
            "Suggested next step: Have sustainability and risk teams assess "
            "strategy resilience under different climate scenarios."
        ),
    },
    "ifrs.readiness.item.transition_plan.name": {
        "zh-TW": "轉型計畫資訊",
        "en": "Transition-plan information",
    },
    "ifrs.readiness.item.transition_plan.why.unsupported": {
        "zh-TW": "系統目前未蒐集轉型計畫資訊。",
        "en": "The system does not currently collect transition-plan information.",
    },
    "ifrs.readiness.item.transition_plan.next.unsupported": {
        "zh-TW": "建議下一步：請整理減碳路徑、資本配置或轉型行動等公司既有資料。",
        "en": (
            "Suggested next step: Compile existing company information such as "
            "decarbonisation pathways, capital allocation or transition actions."
        ),
    },
    "ifrs.readiness.item.assurance_evidence.name": {
        "zh-TW": "確信／查核佐證資料",
        "en": "Assurance / verification supporting evidence",
    },
    "ifrs.readiness.item.assurance_evidence.why.unsupported": {
        "zh-TW": (
            "系統目前未蒐集確信或查核佐證資料；適用確信要求不代表已有證據。"
        ),
        "en": (
            "The system does not currently collect assurance or verification "
            "evidence. An applicable assurance requirement does not mean "
            "evidence is on hand."
        ),
    },
    "ifrs.readiness.item.assurance_evidence.next.unsupported": {
        "zh-TW": (
            "建議下一步：請依主管機關時程另行準備合併個體 Scope 1／2 排放確信"
            "所需佐證。"
        ),
        "en": (
            "Suggested next step: Separately prepare supporting evidence for "
            "consolidated Scope 1 and Scope 2 emissions assurance according "
            "to the authority timeline."
        ),
    },
    "ifrs.timeline.evidence": {
        "zh-TW": "查看官方時程依據",
        "en": "View official timeline sources",
    },
    "ifrs.timeline.past": {
        "zh-TW": "官方時程已經過",
        "en": "The official timeline window has passed",
    },
    "ifrs.timeline.conditional": {
        "zh-TW": "條件期限",
        "en": "Conditional deadline",
    },
    "ifrs.timeline.derived": {
        "zh-TW": "推導時程",
        "en": "Derived timeline",
    },
    "ifrs.timeline.source.authority": {
        "zh-TW": "主管機關",
        "en": "Authority",
    },
    "ifrs.timeline.source.document": {
        "zh-TW": "文件名稱",
        "en": "Document title",
    },
    "ifrs.timeline.source.url": {
        "zh-TW": "官方網址",
        "en": "Official URL",
    },
    "ifrs.timeline.source.published": {
        "zh-TW": "發布／生效日",
        "en": "Publication / effective date",
    },
    "ifrs.timeline.source.retrieved": {
        "zh-TW": "擷取日期",
        "en": "Retrieved date",
    },
    "ifrs.timeline.source.phase_rule": {
        "zh-TW": "公司階段判定依據",
        "en": "How this company phase was selected",
    },
    "ifrs.timeline.source.october": {
        "zh-TW": "10 月確信條件期限說明",
        "en": "October assurance conditional deadline",
    },
    "ifrs.timeline.source.scope3": {
        "zh-TW": "2029 Scope 3 時點如何推導",
        "en": "How the 2029 Scope 3 year is derived",
    },
    "ifrs.timeline.now": {
        "zh-TW": "依官方時程，目前建議階段：{task}",
        "en": (
            "Based on the official timeline, the current recommended stage is: {task}"
        ),
    },
    "ifrs.timeline.next": {
        "zh-TW": "下一官方時程：{period} — {task}",
        "en": "Next official window: {period} — {task}",
    },
    "ifrs.timeline.after": {
        "zh-TW": "官方建議時程窗口均已結束。最後一項為：{task}",
        "en": (
            "The official recommended windows have ended. "
            "The last item was: {task}"
        ),
    },
    "ifrs.timeline.note": {
        "zh-TW": (
            "此時程依主管機關導入時程與今天日期顯示目前位置，不代表公司已完成"
            "前述工作，也不是公司實際完成率。"
        ),
        "en": (
            "This timeline shows the current position based on the regulatory "
            "implementation schedule and today's date. It does not indicate "
            "that the company has completed the preceding work and is not a "
            "company completion rate."
        ),
    },
    "ifrs.timeline.phase_first": {
        "zh-TW": "第一階段適用",
        "en": "First-stage companies",
    },
    "ifrs.timeline.capital_100": {
        "zh-TW": "實收資本額達 100 億元以上",
        "en": "Paid-in capital of NT$10 billion or more",
    },
    "ifrs.timeline.start_2026": {
        "zh-TW": "2026 年度開始適用",
        "en": "Applies from reporting year 2026",
    },
    "ifrs.timeline.file_2027": {
        "zh-TW": "2027 年首次申報",
        "en": "First filing in 2027",
    },
    "ifrs.timeline.phase_rule": {
        "zh-TW": (
            "依金管證審字第11403851756號令第二點第（一）款，"
            "上市上櫃且實收資本額達新臺幣 100 億元以上之公司，"
            "應自 115 會計年度（2026）起適用永續揭露準則，並自 116 年（2027）起申報。"
        ),
        "en": (
            "Under FSC Order Chin-Kuan-Cheng-Shen-Tzu No. 11403851756, "
            "point 2(1), listed and TPEx companies with paid-in capital of "
            "NT$10 billion or more must apply the sustainability disclosure "
            "standards from accounting year 115 (2026) and file from 116 "
            "(2027)."
        ),
    },
    "ifrs.timeline.october": {
        "zh-TW": (
            "令第四點要求合併個體 Scope 1/2 溫室氣體排放取得獨立第三方確信。"
            "若年報申報時尚未取得確信，應於年報註明，並於同年 10 月底前"
            "於公開資訊觀測站補充經確信資訊並上傳確信報告。"
            "這是條件式最晚期限，不是自動產生的第二次申報義務。"
        ),
        "en": (
            "Point 4 of the order requires independent third-party assurance "
            "of consolidated Scope 1/2 greenhouse-gas emissions. If assurance "
            "is not ready when the annual report is filed, note that in the "
            "report and, by the end of October in the same year, publish the "
            "assured information on the Market Observation Post System and "
            "upload the assurance report. This is a conditional latest "
            "deadline, not an automatic second filing obligation."
        ),
    },
    "ifrs.timeline.scope3": {
        "zh-TW": (
            "令第六點規定應自首次適用後第四個會計年度起適用 Scope 3。"
            "第一階段公司首次適用年度為 2026，因此第四個會計年度為 2029。"
            "此 2029 時點由該公式推導，不是另一次獨立法令生效日。"
        ),
        "en": (
            "Point 6 of the order applies Scope 3 from the fourth accounting "
            "year after first application. First-stage companies first apply "
            "in 2026, so the fourth accounting year is 2029. That 2029 date "
            "is derived from the formula; it is not a separate statutory "
            "effective date."
        ),
    },
    "ifrs.timeline.source.official_title": {
        "zh-TW": "官方文件名稱（原文）",
        "en": "Official title (original language)",
    },
    "ifrs.timeline.source.fsc.authority": {
        "zh-TW": "金融監督管理委員會",
        "en": "Financial Supervisory Commission",
    },
    "ifrs.timeline.source.twse.authority": {
        "zh-TW": "臺灣證券交易所",
        "en": "Taiwan Stock Exchange",
    },
    "ifrs.timeline.source.cgc.authority": {
        "zh-TW": "臺灣證券交易所公司治理中心",
        "en": "TWSE Corporate Governance Center",
    },
    "ifrs.timeline.m.analysis_planning.period": {
        "zh-TW": "2024 Q4–2025 Q1",
        "en": "2024 Q4–2025 Q1",
    },
    "ifrs.timeline.m.analysis_planning.label": {
        "zh-TW": "分析與規劃",
        "en": "Analyse and plan",
    },
    "ifrs.timeline.m.analysis_planning.short": {
        "zh-TW": "成立專案小組、完成初步盤點",
        "en": "Form a project team and finish the initial review",
    },
    "ifrs.timeline.m.analysis_planning.detail": {
        "zh-TW": "成立專案小組、盤點準則差距、確認報導個體並擬定導入計畫",
        "en": (
            "Form a project team, review standard gaps, confirm the "
            "reporting entity, and draft the adoption plan"
        ),
    },
    "ifrs.timeline.m.design_execute.period": {
        "zh-TW": "2025 Q2–2026 Q2",
        "en": "2025 Q2–2026 Q2",
    },
    "ifrs.timeline.m.design_execute.label": {
        "zh-TW": "設計與執行",
        "en": "Design and execute",
    },
    "ifrs.timeline.m.design_execute.short": {
        "zh-TW": "盤點資料並調整流程",
        "en": "Map data needs and adjust processes",
    },
    "ifrs.timeline.m.design_execute.detail": {
        "zh-TW": "辨認重大風險與機會、盤點資料需求，並調整流程與系統",
        "en": (
            "Identify material risks and opportunities, map data needs, "
            "and adjust processes and systems"
        ),
    },
    "ifrs.timeline.m.trial_prepare.period": {
        "zh-TW": "2026 Q3–Q4",
        "en": "2026 Q3–Q4",
    },
    "ifrs.timeline.m.trial_prepare.label": {
        "zh-TW": "試行編製",
        "en": "Trial preparation",
    },
    "ifrs.timeline.m.trial_prepare.short": {
        "zh-TW": "試編永續資訊專章",
        "en": "Draft the sustainability information chapter",
    },
    "ifrs.timeline.m.trial_prepare.detail": {
        "zh-TW": "試編 2026 年年報永續資訊專章，檢查資料與內控制度",
        "en": (
            "Draft the 2026 annual-report sustainability chapter and "
            "check data and internal controls"
        ),
    },
    "ifrs.timeline.m.first_filing.period": {
        "zh-TW": "2027 Q1 · 3/16 前",
        "en": "2027 Q1 · before 16 Mar",
    },
    "ifrs.timeline.m.first_filing.label": {
        "zh-TW": "首次申報",
        "en": "First filing",
    },
    "ifrs.timeline.m.first_filing.short": {
        "zh-TW": "完成首次申報",
        "en": "Complete the first filing",
    },
    "ifrs.timeline.m.first_filing.detail": {
        "zh-TW": "完成 2026 年度永續資訊專章並依規定申報",
        "en": (
            "Complete the 2026 sustainability information chapter and "
            "file it as required"
        ),
    },
    "ifrs.timeline.m.scope12_assurance.period": {
        "zh-TW": "2027 Q4 · 10/31 前",
        "en": "2027 Q4 · before 31 Oct",
    },
    "ifrs.timeline.m.scope12_assurance.label": {
        "zh-TW": "完成 Scope 1/2 確信",
        "en": "Complete Scope 1/2 assurance",
    },
    "ifrs.timeline.m.scope12_assurance.short": {
        "zh-TW": "視情況補交確信報告",
        "en": "File the assurance report if still outstanding",
    },
    "ifrs.timeline.m.scope12_assurance.detail": {
        "zh-TW": (
            "若年報申報時尚未取得確信，最晚於 10 月底前補充"
            "經確信資訊及確信報告"
        ),
        "en": (
            "If assurance is not ready when the annual report is filed, "
            "supplement the assured information and assurance report by "
            "the end of October"
        ),
    },
    "ifrs.timeline.m.scope3_start.period": {
        "zh-TW": "2029 年度",
        "en": "2029 reporting year",
    },
    "ifrs.timeline.m.scope3_start.label": {
        "zh-TW": "開始納入 Scope 3",
        "en": "Begin including Scope 3",
    },
    "ifrs.timeline.m.scope3_start.short": {
        "zh-TW": "納入 Scope 3 揭露",
        "en": "Include Scope 3 disclosures",
    },
    "ifrs.timeline.m.scope3_start.detail": {
        "zh-TW": "第一階段公司自首次適用後第四個會計年度起適用 Scope 3 規定",
        "en": (
            "First-stage companies apply the Scope 3 requirements from "
            "the fourth accounting year after first application"
        ),
    },
    "ifrs.timeline.m.scope3_start.derived_note": {
        "zh-TW": (
            "依金管會令第 6 點「自首次適用後第四個會計年度起」推導："
            "第一階段公司首次適用年度為 2026，第四個會計年度為 2029。"
            "此為時程推導，不是另一次獨立法令公布日期。"
        ),
        "en": (
            "Derived from point 6 of the FSC order, which applies from "
            "the fourth accounting year after first application: "
            "first-stage companies first apply in 2026, so the fourth "
            "accounting year is 2029. This is a derived schedule date, "
            "not a separate statutory publication date."
        ),
    },
    "setup.identity.operating": {"zh-TW": "營運中", "en": "Operating"},
    "setup.identity.inactive": {"zh-TW": "已停用", "en": "Closed"},
    "setup.identity.sold": {"zh-TW": "已出售", "en": "Sold"},
    "setup.identity.not_ours": {"zh-TW": "不是本公司據點", "en": "Not our site"},
    "setup.identity.incorrect": {"zh-TW": "資料不正確", "en": "Data is incorrect"},
    "setup.identity.status": {
        "zh-TW": "這個據點目前的狀態",
        "en": "Status of this site",
    },
    "setup.coverage.question": {
        "zh-TW": "這次上傳的排放資料有包含所有營運中的台灣廠場嗎？",
        "en": "Does this upload include every operating Taiwan site?",
    },
    "setup.coverage.all": {"zh-TW": "全部都有", "en": "Yes, all of them"},
    "setup.coverage.some": {"zh-TW": "有些還沒包含", "en": "Some are missing"},
    "setup.coverage.unsure": {"zh-TW": "不確定", "en": "Not sure"},
    "setup.facilities.empty": {
        "zh-TW": "目前還沒找到廠場。你可以新增據點，或先上傳營運資料。",
        "en": "No sites found yet. Add one, or upload activity data first.",
    },
    "setup.all_correct": {"zh-TW": "全部正確", "en": "All correct"},
    "setup.need_adjust": {"zh-TW": "需要調整", "en": "Need to adjust"},
    "setup.include_all": {
        "zh-TW": "全部納入本次資料",
        "en": "Include all in this year's data",
    },
    "setup.include_this": {
        "zh-TW": "納入本次資料",
        "en": "Include in this year's data",
    },
    "setup.add_site": {"zh-TW": "＋ 新增據點", "en": "+ Add a site"},
    "setup.add_site_confirm": {"zh-TW": "新增", "en": "Add"},
    "setup.site_name": {"zh-TW": "據點名稱", "en": "Site name"},
    "setup.site_address": {"zh-TW": "地址（若方便）", "en": "Address (optional)"},
    "setup.site_kind": {"zh-TW": "類型", "en": "Type"},
    "setup.kind.factory": {"zh-TW": "工廠", "en": "Factory"},
    "setup.kind.office": {"zh-TW": "辦公室", "en": "Office"},
    "setup.kind.warehouse": {"zh-TW": "倉庫", "en": "Warehouse"},
    "setup.kind.other": {"zh-TW": "其他", "en": "Other"},
    "setup.deactivate": {"zh-TW": "這次如何處理？", "en": "What should we do?"},
    "setup.inactive.keep": {"zh-TW": "維持使用", "en": "Keep active"},
    "setup.inactive.year_out": {
        "zh-TW": "本年度不納入",
        "en": "Exclude this year",
    },
    "setup.inactive.sold": {"zh-TW": "已出售", "en": "Sold"},
    "setup.inactive.inactive": {"zh-TW": "已停用", "en": "Inactive"},
    "setup.historical": {
        "zh-TW": "已停用或本年度不納入的據點",
        "en": "Inactive or excluded sites",
    },
    "setup.year_reuse": {
        "zh-TW": "與去年相比，公司廠場有變動嗎？",
        "en": "Have the company's sites changed since last year?",
    },
    "setup.year_reuse.reuse": {
        "zh-TW": "沒有，沿用去年資料",
        "en": "No change — reuse last year",
    },
    "setup.year_reuse.changed": {
        "zh-TW": "有新增／停用廠場",
        "en": "Yes — sites were added or closed",
    },
    "setup.full_year_all": {
        "zh-TW": "所有台灣廠場都包含在本次完整年度資料中",
        "en": "All Taiwan sites are covered by this full-year dataset",
    },
    "setup.match.aligned": {"zh-TW": "資料一致", "en": "Sources agree"},
    "setup.match.official_only": {
        "zh-TW": "僅在政府資料找到",
        "en": "Found only in government data",
    },
    "setup.match.upload_only": {
        "zh-TW": "僅在上傳資料找到",
        "en": "Found only in the uploaded file",
    },
    "setup.match.previous_only": {
        "zh-TW": "僅在去年已確認資料找到",
        "en": "Found only in last year's confirmed list",
    },
    "setup.match.needs_review": {"zh-TW": "需要確認", "en": "Needs confirmation"},
    "setup.source.official": {"zh-TW": "政府資料", "en": "Government data"},
    "setup.source.upload": {"zh-TW": "上傳資料", "en": "Uploaded data"},
    "setup.source.previous": {"zh-TW": "去年已確認", "en": "Confirmed last year"},
    "boundary.wizard.step.period": {
        "zh-TW": "報導期間",
        "en": "Reporting period",
    },
    "boundary.wizard.step.purposes": {
        "zh-TW": "申報目的覆核",
        "en": "Purpose review",
    },
    "boundary.wizard.step.reporting_entities": {
        "zh-TW": "永續揭露報導個體",
        "en": "Sustainability disclosure reporting entity",
    },
    "boundary.wizard.step.registrations": {
        "zh-TW": "政府紀錄與據點",
        "en": "Government records & sites",
    },
    "boundary.wizard.step.operations": {
        "zh-TW": "營運與主管機關邊界",
        "en": "Operations & authority units",
    },
    "boundary.wizard.step.review": {
        "zh-TW": "檢查並確認",
        "en": "Review & confirm",
    },
    "boundary.wizard.continue": {"zh-TW": "繼續", "en": "Continue"},
    "boundary.wizard.counter": {
        "zh-TW": "第 {current} 項，共 {total} 項",
        "en": "Item {current} of {total}",
    },
    "boundary.wizard.purposes.title": {
        "zh-TW": "為何這些申報目的需要覆核",
        "en": "Why these reporting purposes need review",
    },
    "boundary.wizard.purposes.intro": {
        "zh-TW": (
            "系統根據目前公司資料找出可能適用的申報目的，"
            "但仍需由貴公司確認實際登記、財務報表與組織範圍。"
        ),
        "en": (
            "The system found reporting purposes that may apply based on "
            "current company information. Your company still needs to confirm "
            "actual registrations, financial statements, and organisational scope."
        ),
    },
    "boundary.wizard.purposes.non_approval": {
        "zh-TW": (
            "本步不核可、取消或改寫法律要求。"
            "政府登記候選不是已確認的政府登記結果。"
            "選擇「稍後處理」不會被當成已確認。"
        ),
        "en": (
            "This step does not approve, cancel, or rewrite legal requirements. "
            "A government-registration candidate is not a confirmed registration. "
            "Choosing “Do this later” is not a confirmation."
        ),
    },
    "boundary.wizard.purposes.none": {
        "zh-TW": "既有評估目前沒有映射出本階段的申報目的。",
        "en": "The assessment currently maps to no purpose in this stage.",
    },
    "boundary.wizard.purposes.effective_year": {
        "zh-TW": "生效年度：{year}",
        "en": "Effective year: {year}",
    },
    "boundary.wizard.purposes.status.needs_confirm": {
        "zh-TW": "可能適用，仍需確認",
        "en": "May apply; still needs confirmation",
    },
    "boundary.wizard.purposes.status.applicable_confirm": {
        "zh-TW": "評估顯示適用，仍需確認實際範圍",
        "en": "Assessment indicates it applies; actual scope still needs confirmation",
    },
    "boundary.wizard.purposes.status.future": {
        "zh-TW": "未來才需要準備，本期不建立邊界",
        "en": "Preparation only for a future period; no current boundary",
    },
    "boundary.wizard.purposes.why_label": {
        "zh-TW": "為什麼需要確認",
        "en": "Why confirmation is needed",
    },
    "boundary.wizard.purposes.impact_label": {
        "zh-TW": "會影響什麼",
        "en": "What this affects",
    },
    "boundary.wizard.purposes.status_label": {
        "zh-TW": "目前狀態",
        "en": "Current status",
    },
    "boundary.wizard.purposes.why.moenv_facility": {
        "zh-TW": (
            "公司資料顯示可能與環境部登記或營運邊界有關，"
            "仍需核對實際據點與官方文件。"
        ),
        "en": (
            "Company information suggests a possible MOENV registration or "
            "operating boundary. Actual sites and official documents still "
            "need to be checked."
        ),
    },
    "boundary.wizard.purposes.why.ifrs_reporting_entity": {
        "zh-TW": (
            "公司資料顯示 IFRS S1／S2 可能適用，"
            "永續揭露範圍需與實際使用的財務報表一致。"
        ),
        "en": (
            "Company information suggests IFRS S1/S2 may apply. The sustainability "
            "disclosure scope must match the financial statements you actually use."
        ),
    },
    "boundary.wizard.purposes.why.listed_consolidated": {
        "zh-TW": (
            "公司資料顯示可能涉及上市櫃合併申報範圍，"
            "仍需確認實際納入的公司與報表。"
        ),
        "en": (
            "Company information suggests a listed-company consolidated "
            "reporting scope may apply. Included companies and statements "
            "still need confirmation."
        ),
    },
    "boundary.wizard.purposes.impact.moenv_facility": {
        "zh-TW": "影響本期環境部盤查納入哪些實際據點，不會把候選登記當成已確認結果。",
        "en": (
            "This affects which actual sites are included in this period's MOENV "
            "inventory. A candidate record is not treated as a confirmed registration."
        ),
    },
    "boundary.wizard.purposes.impact.ifrs_reporting_entity": {
        "zh-TW": "影響 IFRS 永續揭露涵蓋哪一個報導個體；確認前不會假裝範圍已完成。",
        "en": (
            "This affects which reporting entity IFRS sustainability disclosures "
            "cover. The scope is not treated as complete before confirmation."
        ),
    },
    "boundary.wizard.purposes.impact.listed_consolidated": {
        "zh-TW": "影響合併申報可能涵蓋哪些公司；未確認前維持待處理。",
        "en": (
            "This affects which companies a consolidated filing may cover. "
            "It stays pending until confirmed."
        ),
    },
    "boundary.wizard.purposes.admin_provenance": {
        "zh-TW": "評估來源：{obligation}；狀態：{status}；規則：{rules}",
        "en": "Assessment source: {obligation}; status: {status}; rules: {rules}",
    },
    "boundary.wizard.purpose_outcome.current": {
        "zh-TW": "本期目的",
        "en": "Current-period purpose",
    },
    "boundary.wizard.purpose_outcome.future_preparation_only": {
        "zh-TW": "僅供未來準備，本期不建立邊界",
        "en": "Future preparation only; no current boundary",
    },
    "boundary.wizard.purpose_outcome.unresolved": {
        "zh-TW": "仍待法律或官方資料覆核",
        "en": "Legal or official review remains unresolved",
    },
    "boundary.wizard.reporting_entities.title": {
        "zh-TW": "確認永續揭露報導個體",
        "en": "Confirm the sustainability disclosure reporting entity",
    },
    "boundary.wizard.reporting_entities.none": {
        "zh-TW": "本期不需確認永續揭露報導個體。",
        "en": (
            "This period does not require confirmation of the sustainability "
            "disclosure reporting entity."
        ),
    },
    "boundary.wizard.reporting_entities.ifrs_notice": {
        "zh-TW": (
            "永續相關財務揭露原則上應與相關財務報表使用相同的報導個體。"
            "請依公司實際使用的個別或合併財務報表確認；系統不會自行決定報導個體。"
        ),
        "en": (
            "Sustainability-related financial disclosures should, in principle, "
            "use the same reporting entity as the related financial statements. "
            "Please confirm based on the standalone or consolidated financial "
            "statements the company actually uses; the system will not "
            "determine the reporting entity."
        ),
    },
    "boundary.wizard.reporting_entities.limit": {
        "zh-TW": (
            "本步驟只確認本報導期間應納入哪些法律實體，不代表已完成IFRS S1／S2"
            "揭露，也不會取代溫室氣體盤查的組織邊界判斷。"
        ),
        "en": (
            "This step only confirms which legal entities should be included "
            "for this reporting period. It does not mean IFRS S1/S2 disclosures "
            "are complete, and it does not replace organisational-boundary "
            "determination for the GHG inventory."
        ),
    },
    "boundary.wizard.reporting_entities.question": {
        "zh-TW": "本次永續揭露依據哪一類財務報表？",
        "en": "Which financial statements does this sustainability disclosure follow?",
    },
    "boundary.wizard.reporting_entities.standalone_confirm": {
        "zh-TW": "目前公司名稱為「{company}」。請確認這是本次永續揭露的報導個體。",
        "en": (
            "The current company name is “{company}”. Confirm this is the "
            "reporting entity for this sustainability disclosure."
        ),
    },
    "boundary.wizard.reporting_entities.consolidated_confirm": {
        "zh-TW": "請確認集團／母公司名稱，以及應納入合併報導的法律實體。",
        "en": (
            "Confirm the group or parent company name and the legal entities "
            "that belong in the consolidated reporting entity."
        ),
    },
    "boundary.wizard.reporting_entities.group_name": {
        "zh-TW": "集團／母公司名稱",
        "en": "Group or parent company name",
    },
    "boundary.wizard.reporting_entities.covered_companies": {
        "zh-TW": "系統中的法律實體（尚未視為已確認）",
        "en": "Legal entities in the system (not treated as confirmed)",
    },
    "boundary.wizard.reporting_entities.no_subsidiaries": {
        "zh-TW": (
            "目前系統僅有本公司資料；合併報導個體與子公司範圍仍待補充。"
        ),
        "en": (
            "Only this company is in the system so far. The consolidated "
            "reporting entity and subsidiary scope still need to be added."
        ),
    },
    "boundary.wizard.reporting_entities.need_subsidiaries": {
        "zh-TW": "補齊子公司法律實體範圍後，才能確認合併報導範圍。",
        "en": (
            "Add subsidiary legal-entity coverage before confirming the "
            "consolidated reporting scope."
        ),
    },
    "boundary.wizard.reporting_entities.affects": {
        "zh-TW": "本次確認會影響：{names}",
        "en": "This confirmation affects: {names}",
    },
    "boundary.wizard.reporting_entities.standalone_keeps_listed_pending": {
        "zh-TW": "選擇個別財務報表時，上市櫃合併申報範圍會維持待確認。",
        "en": (
            "Choosing standalone statements keeps listed-company consolidated "
            "reporting pending."
        ),
    },
    "boundary.wizard.reporting_entities.need_document": {
        "zh-TW": "要確認報導範圍，請提供文件位置或證據參考。",
        "en": (
            "To confirm this reporting scope, provide a document location or "
            "evidence reference."
        ),
    },
    "boundary.wizard.reporting_entities.save_basis": {
        "zh-TW": "儲存報導基礎",
        "en": "Save reporting basis",
    },
    "boundary.wizard.reporting_entities.unresolved_help": {
        "zh-TW": (
            "可以稍後再確認。IFRS 揭露邊界會維持待確認，"
            "不會假裝已完成，也不會阻擋 Scope 1／Scope 2 碳排計算。"
        ),
        "en": (
            "You can confirm this later. The IFRS disclosure boundary stays "
            "pending, is not treated as complete, and does not block Scope 1 / "
            "Scope 2 calculations."
        ),
    },
    "boundary.wizard.reporting_entities.progress": {
        "zh-TW": "報導範圍 {current}／{total}：{name}",
        "en": "Reporting scope {current}/{total}: {name}",
    },
    "boundary.wizard.reporting_entities.also": {
        "zh-TW": "另一項：{name}",
        "en": "Also in this step: {name}",
    },
    "boundary.wizard.reporting_entities.evidence_expander": {
        "zh-TW": "補充財務報表資料（選填）",
        "en": "Additional financial-statement details (optional)",
    },
    "boundary.wizard.reporting_entities.confirm": {
        "zh-TW": "確認此報導範圍",
        "en": "Confirm this reporting scope",
    },
    "boundary.wizard.reporting_entities.name.ifrs_reporting_entity": {
        "zh-TW": "IFRS S1／S2",
        "en": "IFRS S1/S2",
    },
    "boundary.wizard.reporting_entities.name.listed_consolidated": {
        "zh-TW": "上市櫃合併申報範圍",
        "en": "Listed-company consolidated reporting",
    },
    "boundary.wizard.reporting_entities.basis": {
        "zh-TW": "相關財務報表的報導基礎",
        "en": "Reporting basis of the relevant financial statements",
    },
    "boundary.wizard.reporting_entities.statement": {
        "zh-TW": "財務報表名稱",
        "en": "Financial statement title",
    },
    "boundary.wizard.reporting_entities.statement_type": {
        "zh-TW": "財務報表類型",
        "en": "Financial statement type",
    },
    "boundary.wizard.reporting_entities.issuer": {
        "zh-TW": "出具者或資料來源",
        "en": "Issuer or source",
    },
    "boundary.wizard.reporting_entities.entity_name": {
        "zh-TW": "報導個體名稱",
        "en": "Reporting entity name",
    },
    "boundary.wizard.reporting_entities.provenance": {
        "zh-TW": "文件位置或證據參考",
        "en": "Document location or evidence reference",
    },
    "boundary.wizard.consolidation.unresolved": {
        "zh-TW": "尚未確認",
        "en": "Not yet confirmed",
    },
    "boundary.wizard.consolidation.standalone": {
        "zh-TW": "個別財務報表",
        "en": "Standalone financial statements",
    },
    "boundary.wizard.consolidation.consolidated": {
        "zh-TW": "合併財務報表",
        "en": "Consolidated financial statements",
    },
    "boundary.wizard.registrations.title": {
        "zh-TW": "把政府紀錄核對到實際公司據點",
        "en": "Reconcile government records to actual company sites",
    },
    "boundary.wizard.registrations.none": {
        "zh-TW": "目前沒有政府工廠登記資料需要核對。",
        "en": "There are no government factory-registration records to reconcile.",
    },
    "boundary.wizard.registrations.official_record": {
        "zh-TW": "政府工廠登記資料",
        "en": "Government factory-registration record",
    },
    "boundary.wizard.registrations.limit": {
        "zh-TW": (
            "這筆資料可協助辨識可能的地點，但不能單獨證明這是本公司的實際"
            "營運據點、環境部盤查邊界或獨立申報單位。"
        ),
        "en": (
            "This record can help identify a possible location, but it cannot by "
            "itself prove an actual company site, MOENV boundary, or separate "
            "reporting unit."
        ),
    },
    "boundary.wizard.registrations.why": {
        "zh-TW": "政府紀錄與公司實際營運據點是不同事實，必須先核對身分。",
        "en": "A government record and an actual company site are different facts.",
    },
    "boundary.wizard.registrations.role": {
        "zh-TW": "廠務、總務或據點營運主管。",
        "en": "Facilities, administration, or the site operations manager.",
    },
    "boundary.wizard.registrations.evidence": {
        "zh-TW": "工廠登記、租約、內部據點清冊、停工或移轉文件。",
        "en": "Factory registrations, leases, site lists, closure or transfer records.",
    },
    "boundary.wizard.registrations.uncertain": {
        "zh-TW": (
            "保留為目前無法確認；不會變成排除、不適用、已確認據點或 0 排放。"
        ),
        "en": (
            "It remains unresolved, not excluded, inapplicable, a confirmed "
            "site, or zero emissions."
        ),
    },
    "boundary.wizard.registrations.question": {
        "zh-TW": "這筆政府紀錄與本公司實際據點的關係為何？",
        "en": "How does this government record relate to an actual company site?",
    },
    "boundary.wizard.registrations.site": {
        "zh-TW": "選擇既有公司據點",
        "en": "Select an existing company site",
    },
    "boundary.wizard.registrations.new_site": {
        "zh-TW": "建立新公司據點",
        "en": "Create a new company site",
    },
    "boundary.wizard.registrations.site_name": {
        "zh-TW": "實際公司據點名稱",
        "en": "Actual company site name",
    },
    "boundary.wizard.registrations.site_address": {
        "zh-TW": "實際公司據點地址",
        "en": "Actual company site address",
    },
    "boundary.wizard.registrations.basis": {
        "zh-TW": "核對依據或失效原因",
        "en": "Reconciliation basis or invalidity reason",
    },
    "boundary.wizard.registrations.evidence_reference": {
        "zh-TW": "支持文件或資料參考",
        "en": "Supporting document or record reference",
    },
    "boundary.wizard.registrations.gov_prefill": {
        "zh-TW": "以下資料來自政府紀錄，請確認或修改。",
        "en": (
            "The following details come from a government record. "
            "Review or edit them."
        ),
    },
    "boundary.wizard.registrations.confirm_site": {
        "zh-TW": "我確認以上名稱與地址是本公司的實際據點。",
        "en": (
            "I confirm that the name and address above are an actual site "
            "of this company."
        ),
    },
    "boundary.wizard.registrations.no_sites_for_duplicate": {
        "zh-TW": (
            "目前沒有可對應的公司據點。請先將第一筆登記核對到本公司據點，"
            "再處理這筆紀錄。"
        ),
        "en": (
            "There is no company site to match yet. Reconcile the first "
            "record to a company site before handling this one."
        ),
    },
    "boundary.wizard.registrations.other_basis": {
        "zh-TW": "判定依據",
        "en": "Basis for this determination",
    },
    "boundary.wizard.registrations.invalid_basis": {
        "zh-TW": "註銷或失效依據",
        "en": "Basis for cancellation or period inapplicability",
    },
    "boundary.wizard.registrations.notes": {
        "zh-TW": "待確認備註（選填）",
        "en": "Notes pending confirmation (optional)",
    },
    "boundary.wizard.reconciliation.matched_to_confirmed_site": {
        "zh-TW": "這筆登記對應本公司的實際據點",
        "en": "This registration matches an actual site of this company",
    },
    "boundary.wizard.reconciliation.duplicate_or_additional_record_for_same_site": {
        "zh-TW": "這是同一公司據點的另一筆登記",
        "en": "This is another registration for the same company site",
    },
    "boundary.wizard.reconciliation.belongs_to_another_company": {
        "zh-TW": "這筆登記不屬於本公司",
        "en": "This registration does not belong to this company",
    },
    "boundary.wizard.reconciliation.no_longer_valid": {
        "zh-TW": "這筆登記已註銷或不適用於本期",
        "en": (
            "This registration is cancelled or not applicable in this period"
        ),
    },
    "boundary.wizard.reconciliation.unresolved": {
        "zh-TW": "目前無法確認",
        "en": "Cannot be confirmed yet",
    },
    "boundary.wizard.operations.title": {
        "zh-TW": "確認營運事實與主管機關邊界",
        "en": "Confirm operating facts and authority-defined boundaries",
    },
    "boundary.wizard.authority.title": {
        "zh-TW": "主管機關邊界依據",
        "en": "Competent-authority boundary evidence",
    },
    "boundary.wizard.authority.official_only": {
        "zh-TW": (
            "只有主管機關文件已明確描述同一申報或營運單位，而且官方核發機關、"
            "文件身分、適用範圍及有效期間都已由官方來源驗證，系統才會建立環境部邊界。"
        ),
        "en": (
            "A MOENV boundary is created only when an authority document describes "
            "the unit and its issuer, identity, scope, and period are verified "
            "against an official source."
        ),
    },
    "boundary.wizard.authority.professional_review": {
        "zh-TW": (
            "專業人員的解讀或覆核只能作為參考，"
            "不能取代主管機關文件或官方來源驗證。"
        ),
        "en": (
            "Professional interpretation is reference metadata only and cannot "
            "replace authority provenance or official-source verification."
        ),
    },
    "boundary.wizard.authority.action": {
        "zh-TW": "本次要提供什麼資料？",
        "en": "What evidence will you provide now?",
    },
    "boundary.wizard.authority.action.no_evidence": {
        "zh-TW": "目前沒有主管機關邊界文件",
        "en": "No authority-boundary document is available",
    },
    "boundary.wizard.authority.action.add_pending": {
        "zh-TW": "新增一筆待官方來源驗證的文件",
        "en": "Add a document pending official-source verification",
    },
    "boundary.wizard.authority.authority": {"zh-TW": "主管機關", "en": "Authority"},
    "boundary.wizard.authority.source_id": {"zh-TW": "來源 ID", "en": "Source ID"},
    "boundary.wizard.authority.document_type": {
        "zh-TW": "文件類型",
        "en": "Document type",
    },
    "boundary.wizard.authority.identifier": {
        "zh-TW": "文件或登記識別碼",
        "en": "Document or registration identifier",
    },
    "boundary.wizard.authority.unit": {
        "zh-TW": "文件描述的申報或營運單位",
        "en": "Reporting or operating unit described",
    },
    "boundary.wizard.authority.effective_start": {
        "zh-TW": "有效期間起日",
        "en": "Effective start",
    },
    "boundary.wizard.authority.effective_end": {
        "zh-TW": "有效期間迄日",
        "en": "Effective end",
    },
    "boundary.wizard.authority.provenance": {
        "zh-TW": "官方來源參考",
        "en": "Official provenance reference",
    },
    "boundary.wizard.authority.note": {
        "zh-TW": "公司補充說明（不是主管機關證明）",
        "en": "Company note (not authority evidence)",
    },
    "boundary.wizard.operating_counter": {
        "zh-TW": "實際公司據點營運事實 {current} / {total}",
        "en": "Canonical-site operating fact {current} / {total}",
    },
    "boundary.wizard.membership_counter": {
        "zh-TW": "有主管機關依據的據點歸屬 {current} / {total}",
        "en": "Evidence-linked site membership {current} / {total}",
    },
    "boundary.wizard.operations.separate_facts": {
        "zh-TW": "營運期間與申報邊界是不同事實；本題只記錄這個實際公司據點的營運期間。",
        "en": "Operating timing and boundary membership are separate facts.",
    },
    "boundary.wizard.operations.operating_question": {
        "zh-TW": "這個實際公司據點在本報導期間的營運情況為何？",
        "en": "How did this actual company site operate during this period?",
    },
    "boundary.wizard.operations.effective_date": {
        "zh-TW": "開始、停止、出售或移轉日期",
        "en": "Start, closure, sale, or transfer date",
    },
    "boundary.wizard.operations.basis": {
        "zh-TW": "支持依據",
        "en": "Supporting basis",
    },
    "boundary.wizard.operations.authority_membership": {
        "zh-TW": "本題只會出現在已驗證主管機關證據明確連結的實際公司據點。",
        "en": (
            "This question appears only for sites linked by verified "
            "authority evidence."
        ),
    },
    "boundary.wizard.operations.membership_question": {
        "zh-TW": "這個實際公司據點是否屬於該主管機關定義的申報單位？",
        "en": "Is this actual company site in the authority-defined reporting unit?",
    },
    "boundary.wizard.operations.membership_reason": {
        "zh-TW": "排除或本期不適用的原因",
        "en": "Reason for exclusion or period inapplicability",
    },
    "boundary.wizard.operations.complete": {
        "zh-TW": "本步目前沒有其他問題。",
        "en": "There are no more questions in this step.",
    },
    "boundary.wizard.operations.counts": {
        "zh-TW": "實際據點營運事實：{sites}；有證據連結的邊界歸屬：{memberships}",
        "en": (
            "Site operating facts: {sites}; evidence-linked memberships: "
            "{memberships}"
        ),
    },
    "boundary.wizard.review.summary": {
        "zh-TW": (
            "申報目的 {purposes}；已證據定義的邊界 {boundaries}；"
            "政府紀錄 {candidates}；實際據點 {sites}"
        ),
        "en": (
            "Purposes {purposes}; evidence-defined boundaries {boundaries}; "
            "government records {candidates}; actual sites {sites}"
        ),
    },
    "boundary.wizard.review.unresolved_counts": {
        "zh-TW": "法律或官方資料待覆核：{legal}；公司可處理事實待確認：{company}",
        "en": (
            "Legal/official review unresolved: {legal}; "
            "company facts unresolved: {company}"
        ),
    },
    "boundary.wizard.review.not_legal_conclusion": {
        "zh-TW": (
            "本機確認只保存公司提供的資料與決定，"
            "不代表法律結論或官方來源驗證已完成。"
        ),
        "en": (
            "Local confirmation records company-provided facts and decisions. "
            "It is not a legal conclusion or official-source verification."
        ),
    },
    "boundary.wizard.migration.title": {
        "zh-TW": "偵測到先前版本的盤查設定",
        "en": "Earlier inventory settings were found",
    },
    "boundary.wizard.migration.explicit": {
        "zh-TW": (
            "更新不會改變法律要求，也不會自動確認任何公司資料。"
            "原始設定將保留，以便需要時復原。"
        ),
        "en": (
            "Updating does not change legal requirements and does not "
            "automatically confirm any company information. The original "
            "settings are kept so they can be restored if needed."
        ),
    },
    "boundary.wizard.migration.summary_title": {
        "zh-TW": "更新摘要",
        "en": "Update summary",
    },
    "boundary.wizard.migration.summary": {
        "zh-TW": (
            "系統找到先前儲存的盤查草稿。更新後會改用目前的盤查設定格式；"
            "原始草稿會保留，且不會自動確認據點、證據或申報邊界。"
        ),
        "en": (
            "Earlier inventory drafts were found. Updating switches to the "
            "current settings format. The original draft is kept, and sites, "
            "evidence, and reporting boundaries are not auto-confirmed."
        ),
    },
    "boundary.wizard.migration.view_summary": {
        "zh-TW": "查看更新摘要",
        "en": "View update summary",
    },
    "boundary.wizard.migration.run": {
        "zh-TW": "更新盤查設定",
        "en": "Update inventory settings",
    },
    "boundary.wizard.migration.done": {
        "zh-TW": "盤查設定已更新。原始設定仍保留，需要時可以復原。",
        "en": (
            "Inventory settings were updated. The original settings are still "
            "kept and can be restored if needed."
        ),
    },
    "boundary.wizard.migration.admin_summary": {
        "zh-TW": (
            "舊版邊界紀錄：{boundaries}；政府登記候選：{registrations}；"
            "只保留於舊版歷史的來源類別紀錄：{categories}"
        ),
        "en": (
            "Legacy boundary records: {boundaries}; registration candidates: "
            "{registrations}; source-category rows retained only in legacy history: "
            "{categories}"
        ),
    },
    "boundary.wizard.later_not_confirmed": {
        "zh-TW": "「稍後處理」只會暫停此步驟，不會把任何項目標示為已確認。",
        "en": (
            "“Do this later” only pauses this step. It does not mark anything "
            "as confirmed."
        ),
    },
    "boundary.error.reporting_entity_evidence": {
        "zh-TW": "選擇單獨或合併報導基礎時，請完整填寫相關財務報表與證據資料。",
        "en": "Complete the financial-statement evidence before confirming a basis.",
    },
    "boundary.error.canonical_site": {
        "zh-TW": "請填寫實際公司據點名稱。",
        "en": "Enter the actual company site name.",
    },
    "boundary.error.site_confirm": {
        "zh-TW": "請確認名稱與地址是本公司的實際據點。",
        "en": "Confirm that the name and address are an actual site of this company.",
    },
    "boundary.error.duplicate_site": {
        "zh-TW": "重複或附加紀錄必須選擇一個既有實際公司據點。",
        "en": "A duplicate or additional record must select an existing site.",
    },
    "boundary.error.duplicate_primary": {
        "zh-TW": "所選據點尚無主要政府紀錄可供連結。",
        "en": "The selected site has no primary government record to reference.",
    },
    "boundary.error.other_company_basis": {
        "zh-TW": "判定不屬於本公司時必須提供依據。",
        "en": "Provide a basis when this registration does not belong to the company.",
    },
    "boundary.error.registration_basis": {
        "zh-TW": "標記政府紀錄已註銷或不適用於本期時必須提供依據。",
        "en": (
            "Provide a basis when marking a government record cancelled or "
            "not applicable in this period."
        ),
    },
    "boundary.error.authority_identifier": {
        "zh-TW": "請至少填寫文件或登記識別碼；新資料會保持待官方來源驗證。",
        "en": (
            "Provide a document identifier; new evidence remains pending "
            "verification."
        ),
    },
    "boundary.error.operating_fact": {
        "zh-TW": "部分期間或整期未營運需要日期及／或支持依據。",
        "en": "Partial-period or non-operating facts require dates and/or support.",
    },
    "boundary.error.membership_reason": {
        "zh-TW": "排除或本期不適用時必須提供原因。",
        "en": "Provide a reason for exclusion or period inapplicability.",
    },
    "boundary.wizard.step_of": {
        "zh-TW": "邊界確認步驟 {current} / 6",
        "en": "Boundary confirmation step {current} / 6",
    },
    "boundary.wizard.current_task": {
        "zh-TW": "目前申報範圍：{task}",
        "en": "Current reporting scope: {task}",
    },
    "boundary.wizard.support.why": {
        "zh-TW": "為什麼需要確認",
        "en": "Why this needs confirmation",
    },
    "boundary.wizard.support.role": {
        "zh-TW": "公司內通常由誰確認",
        "en": "Who usually knows",
    },
    "boundary.wizard.support.evidence": {
        "zh-TW": "可以查看什麼資料或文件",
        "en": "Records or documents to check",
    },
    "boundary.wizard.support.uncertain": {
        "zh-TW": "回答「尚不確定」之後會發生什麼",
        "en": "What happens after “Not sure”",
    },
    "boundary.wizard.back": {"zh-TW": "上一步", "en": "Back"},
    "boundary.wizard.later": {"zh-TW": "稍後處理", "en": "Do this later"},
    "boundary.wizard.save_continue": {
        "zh-TW": "儲存並繼續",
        "en": "Save & continue",
    },
    "boundary.wizard.resume": {
        "zh-TW": "繼續範圍確認",
        "en": "Resume boundary confirmation",
    },
    "boundary.wizard.deferred": {
        "zh-TW": "範圍草稿已保留。您可以稍後從相同公司與報導期間繼續。",
        "en": (
            "Your boundary draft is saved. You can resume later for the same "
            "company and reporting period."
        ),
    },
    "boundary.wizard.answer": {"zh-TW": "您的回答", "en": "Your answer"},
    "boundary.wizard.choose": {"zh-TW": "請選擇", "en": "Select an answer"},
    "boundary.wizard.answer_required": {
        "zh-TW": "請先選擇一個回答。",
        "en": "Select an answer before continuing.",
    },
    "boundary.wizard.period.title": {
        "zh-TW": "確認報導期間",
        "en": "Confirm reporting period",
    },
    "boundary.wizard.period.why": {
        "zh-TW": (
            "報導期間決定這次範圍確認適用的年度與日期，也避免把前期答案"
            "當成本期答案。"
        ),
        "en": (
            "The reporting period determines which year and dates these boundary "
            "decisions apply to and prevents prior-period answers from becoming "
            "current-period answers."
        ),
    },
    "boundary.wizard.period.role": {
        "zh-TW": "永續、財會，或負責對外申報的窗口。",
        "en": "Sustainability, finance, or the external reporting contact.",
    },
    "boundary.wizard.period.evidence": {
        "zh-TW": "年度盤查計畫、永續報告書、主管機關通知，或公司的會計年度資料。",
        "en": (
            "The annual inventory plan, sustainability report, regulator notice, "
            "or company fiscal-year records."
        ),
    },
    "boundary.wizard.period.uncertain": {
        "zh-TW": "本步不提供猜測值；請先確認年度與日期，系統才會建立本期草稿。",
        "en": (
            "This step does not guess a period. Confirm the year and dates before "
            "a current-period draft is created."
        ),
    },
    "boundary.wizard.tasks.title": {
        "zh-TW": "了解本次申報範圍",
        "en": "Understand reporting scopes",
    },
    "boundary.wizard.tasks.intro": {
        "zh-TW": (
            "系統已依目前的公司資料與適用性評估整理本次需要確認的申報範圍。"
            "這裡不是法規清單，您不需要自行挑選適用法律。"
        ),
        "en": (
            "The system identified these reporting-scope tasks from your company "
            "data and applicability assessment. This is not a checklist of laws "
            "for you to choose."
        ),
    },
    "boundary.wizard.tasks.non_approval": {
        "zh-TW": (
            "這些申報範圍由既有適用性評估產生。您在這裡不會核可、取消或"
            "改寫法律要求。"
        ),
        "en": (
            "These scopes come from the existing applicability assessment. You "
            "are not approving, cancelling, or overriding a legal requirement."
        ),
    },
    "boundary.wizard.tasks.why": {
        "zh-TW": "不同政府登記或申報目的可能有不同的公司、據點與證據，必須分開核對。",
        "en": (
            "Different registrations or reporting purposes can involve different "
            "companies, sites, and evidence."
        ),
    },
    "boundary.wizard.tasks.role": {
        "zh-TW": "永續或法遵窗口；工廠登記事項可請廠務或總務協助。",
        "en": (
            "The sustainability or compliance contact, with facilities or "
            "administration for factory registrations."
        ),
    },
    "boundary.wizard.tasks.evidence": {
        "zh-TW": "主管機關通知、工廠或商工登記、許可、營運協議、申報政策。",
        "en": (
            "Regulator notices, factory or business registrations, permits, "
            "operating agreements, or reporting policies."
        ),
    },
    "boundary.wizard.tasks.uncertain": {
        "zh-TW": "資料不完整時，此項保留為需要公司確認，不會自動視為不適用。",
        "en": (
            "If information is incomplete, the task remains unresolved and is "
            "not treated as not applicable."
        ),
    },
    "boundary.wizard.tasks.start": {
        "zh-TW": "開始確認這些範圍",
        "en": "Start confirming these scopes",
    },
    "boundary.wizard.task_counter": {
        "zh-TW": "範圍確認 {current} / {total}",
        "en": "Scope review {current} / {total}",
    },
    "boundary.wizard.company_counter": {
        "zh-TW": "申報範圍 {scope_current} / {scope_total} · 公司：{company}",
        "en": (
            "Reporting scope {scope_current} / {scope_total} · "
            "Company: {company}"
        ),
    },
    "boundary.wizard.site_counter": {
        "zh-TW": "工廠或營運據點 {current} / {total}",
        "en": "Factory or operating site {current} / {total}",
    },
    "boundary.wizard.category_counter": {
        "zh-TW": (
            "申報範圍 {scope_current} / {scope_total} · "
            "排放來源 {category_current} / {category_total}"
        ),
        "en": (
            "Reporting scope {scope_current} / {scope_total} · "
            "Emission source {category_current} / {category_total}"
        ),
    },
    "boundary.wizard.task_name.moenv_facility": {
        "zh-TW": "環境部盤查範圍",
        "en": "MOENV inventory scope",
    },
    "boundary.wizard.task_name.ifrs_reporting_entity": {
        "zh-TW": "IFRS 財務報表報導個體",
        "en": "IFRS financial-statement reporting entity",
    },
    "boundary.wizard.task_name.listed_consolidated": {
        "zh-TW": "上市櫃公司合併申報範圍",
        "en": "Listed-company consolidated reporting scope",
    },
    "boundary.wizard.task_name.with_site": {
        "zh-TW": "{purpose} — {site}",
        "en": "{purpose} — {site}",
    },
    "boundary.wizard.task_status.needs_fact": {
        "zh-TW": "仍需公司提供事實或由法規人員覆核",
        "en": "Company facts or legal review are still needed",
    },
    "boundary.wizard.task_status.with_year": {
        "zh-TW": "系統已辨識：{status}（{year} 年起）",
        "en": "System identified: {status} (from {year})",
    },
    "boundary.wizard.task_status.identified": {
        "zh-TW": "系統已辨識：{status}",
        "en": "System identified: {status}",
    },
    "boundary.wizard.operating_company": {
        "zh-TW": "營運公司：{company}",
        "en": "Operating company: {company}",
    },
    "boundary.wizard.task.why_label": {
        "zh-TW": "為什麼有這項任務",
        "en": "Why this task exists",
    },
    "boundary.wizard.task.status_label": {
        "zh-TW": "目前判斷",
        "en": "Current determination",
    },
    "boundary.wizard.task.next_label": {
        "zh-TW": "下一步",
        "en": "Next action",
    },
    "boundary.wizard.task.next": {
        "zh-TW": "確認本期間包含的公司、工廠或營運據點及預期排放來源。",
        "en": (
            "Confirm the companies, factories or operating sites, and expected "
            "emission sources for this period."
        ),
    },
    "boundary.wizard.task.why.moenv_facility": {
        "zh-TW": "系統找到一筆政府工廠登記，因此保留為獨立的盤查範圍任務。",
        "en": (
            "The system found a government factory registration, so it remains "
            "a separate inventory-scope task."
        ),
    },
    "boundary.wizard.task.why.ifrs_reporting_entity": {
        "zh-TW": "適用性評估依精確 IFRS 採用規則辨識到報導目的。",
        "en": (
            "The applicability assessment identified a reporting purpose from "
            "an exact IFRS adoption rule."
        ),
    },
    "boundary.wizard.task.why.listed_consolidated": {
        "zh-TW": "適用性評估辨識到上市櫃公司合併申報目的。",
        "en": (
            "The applicability assessment identified a listed-company consolidated "
            "reporting purpose."
        ),
    },
    "boundary.wizard.combination.review": {
        "zh-TW": "有文件顯示這些登記屬於同一核准或營運邊界",
        "en": (
            "Documents show that registrations share an approved or operating "
            "boundary"
        ),
    },
    "boundary.wizard.companies.title": {
        "zh-TW": "確認本次包含的公司",
        "en": "Confirm companies included",
    },
    "boundary.wizard.companies.question": {
        "zh-TW": "請確認這家公司是否包含在「{task}」的本次申報範圍。",
        "en": (
            "Should this company be included in the current reporting scope for "
            "“{task}”?"
        ),
    },
    "boundary.wizard.companies.why": {
        "zh-TW": "公司範圍決定哪些母公司或子公司的活動要納入後續盤查。",
        "en": (
            "The company scope determines which parent or subsidiary activities "
            "enter the inventory."
        ),
    },
    "boundary.wizard.companies.role": {
        "zh-TW": "財會合併報表窗口、公司治理／法務，或永續團隊。",
        "en": (
            "The consolidation reporting contact, corporate governance or legal, "
            "or the sustainability team."
        ),
    },
    "boundary.wizard.companies.evidence": {
        "zh-TW": "集團組織圖、合併報表範圍、公司登記、董事會或內部申報政策。",
        "en": (
            "Group charts, consolidation scope, company registrations, board "
            "records, or internal reporting policy."
        ),
    },
    "boundary.wizard.companies.uncertain": {
        "zh-TW": "此公司保留為待公司確認，無法在最後一步建立新的本機確認版本。",
        "en": (
            "The company remains unresolved and a new local confirmation version "
            "cannot be created."
        ),
    },
    "boundary.wizard.companies.uncertain_detail": {
        "zh-TW": "請向財會、法務或公司治理窗口確認，並查看合併報表範圍或組織圖。",
        "en": (
            "Ask finance, legal, or corporate governance and check the consolidation "
            "scope or group chart."
        ),
    },
    "boundary.wizard.companies.add_subsidiary": {
        "zh-TW": "新增合併範圍內的子公司",
        "en": "Add a subsidiary in the consolidated scope",
    },
    "boundary.wizard.companies.add": {
        "zh-TW": "新增這家公司",
        "en": "Add this company",
    },
    "boundary.wizard.companies.identity_error": {
        "zh-TW": "請填寫子公司名稱與設立國家／地區。",
        "en": "Enter the subsidiary name and jurisdiction.",
    },
    "boundary.wizard.membership.included": {
        "zh-TW": "包含",
        "en": "Include",
    },
    "boundary.wizard.membership.excluded": {
        "zh-TW": "排除",
        "en": "Exclude",
    },
    "boundary.wizard.membership.not_applicable_to_period": {
        "zh-TW": "本期間不適用",
        "en": "Not applicable to this period",
    },
    "boundary.wizard.membership.uncertain": {
        "zh-TW": "尚不確定",
        "en": "Not sure",
    },
    "boundary.wizard.membership.pending_confirmation": {
        "zh-TW": "尚待回答",
        "en": "Awaiting an answer",
    },
    "boundary.wizard.membership.reason": {
        "zh-TW": "請說明原因",
        "en": "Explain the reason",
    },
    "boundary.wizard.membership.evidence": {
        "zh-TW": "可以支持這個判斷的文件或資料",
        "en": "Document or record supporting this decision",
    },
    "boundary.wizard.sites.title": {
        "zh-TW": "確認工廠與營運據點",
        "en": "Confirm factories and operating sites",
    },
    "boundary.wizard.sites.empty": {
        "zh-TW": "這個申報範圍目前沒有需要逐筆確認的工廠或營運據點。",
        "en": (
            "There are currently no factories or operating sites to review for "
            "this reporting scope."
        ),
    },
    "boundary.wizard.sites.operating_question": {
        "zh-TW": "這個工廠或營運據點在整個報導期間內的營運情況為何？",
        "en": (
            "How was this factory or operating site operated during the complete "
            "reporting period?"
        ),
    },
    "boundary.wizard.sites.why": {
        "zh-TW": (
            "據點可能只在報導期間的一部分時間由公司營運；開始、停止、出售"
            "或移轉日期會影響後續需要蒐集哪一段期間的活動資料。"
        ),
        "en": (
            "A site might be operated for only part of the period. Start, closure, "
            "sale, or transfer dates affect which activity-data period may be needed."
        ),
    },
    "boundary.wizard.sites.role": {
        "zh-TW": "廠務、總務、資產管理、法務或負責該據點的營運主管。",
        "en": (
            "Facilities, administration, asset management, legal, or the site "
            "operations manager."
        ),
    },
    "boundary.wizard.sites.evidence": {
        "zh-TW": "工廠登記、租約、許可、營運協議、處分或移轉文件、內部據點清冊。",
        "en": (
            "Factory registrations, leases, permits, operating agreements, disposal "
            "or transfer records, or the internal site list."
        ),
    },
    "boundary.wizard.sites.uncertain": {
        "zh-TW": "此據點保留為待公司確認，不會被視為整期排除。",
        "en": (
            "The site remains unresolved and is not treated as excluded for the "
            "whole period."
        ),
    },
    "boundary.wizard.sites.uncertain_detail": {
        "zh-TW": (
            "請向廠務或總務確認 {site} 在 {year} 年的實際營運起訖日。可查看"
            "工廠登記、租約、停工、處分或移轉文件及內部據點清冊。"
        ),
        "en": (
            "Ask facilities or administration for the actual operating dates of "
            "{site} in {year}. Check registrations, leases, closure, disposal, "
            "transfer, or internal site records."
        ),
    },
    "boundary.wizard.sites.effective_date": {
        "zh-TW": "生效日期",
        "en": "Effective date",
    },
    "boundary.wizard.sites.operating_basis": {
        "zh-TW": "原因或支持資料",
        "en": "Reason or supporting source",
    },
    "boundary.wizard.sites.partial_notice": {
        "zh-TW": (
            "這個據點在報導期間內有營運變動，後續可能仍需蒐集部分期間的活動"
            "資料。本步只保存營運事實，不進行資料涵蓋或排放量計算。"
        ),
        "en": (
            "The site's operation changed during the reporting period. Activity "
            "data may still be needed for part of the period. This step records "
            "the operating fact only; it does not assess coverage or calculate "
            "emissions."
        ),
    },
    "boundary.wizard.sites.basis_required": {
        "zh-TW": "請填寫這項營運情況的原因或支持資料。",
        "en": "Enter a reason or supporting source for this operating status.",
    },
    "boundary.wizard.sites.date_error": {
        "zh-TW": "生效日期必須在目前報導期間內。",
        "en": "The effective date must be within the current reporting period.",
    },
    "boundary.wizard.sites.membership_question": {
        "zh-TW": "這個據點是否包含在「{task}」？",
        "en": "Is this site included in “{task}”?",
    },
    "boundary.wizard.sites.membership_why": {
        "zh-TW": "營運時間與申報範圍是不同事實；此處只確認是否納入本次範圍。",
        "en": (
            "Operating time and reporting-scope inclusion are separate facts. "
            "This decision addresses inclusion only."
        ),
    },
    "boundary.wizard.sites.moenv_restriction": {
        "zh-TW": (
            "這是本政府登記對應的據點，不能因營運變動而從申報範圍靜默消失。"
            "如主張排除，請提供登記變更、停工或移轉依據；系統仍會進行完整性檢查。"
        ),
        "en": (
            "This site corresponds to the government registration and cannot "
            "silently disappear after an operating change. Provide registration, "
            "closure, or transfer evidence if exclusion is claimed; completeness "
            "validation still applies."
        ),
    },
    "boundary.wizard.sites.uncertain_membership": {
        "zh-TW": "此據點的申報範圍仍待確認，不會自動變成排除。",
        "en": (
            "This site's reporting-scope decision remains unresolved and is not "
            "automatically excluded."
        ),
    },
    "boundary.wizard.sites.unresolved_error": {
        "zh-TW": "請先確認所有據點的期間營運事實與申報範圍。",
        "en": (
            "Confirm every site's period operating fact and reporting-scope "
            "decision first."
        ),
    },
    "boundary.wizard.operating.full_period": {
        "zh-TW": "整個報導期間都由公司營運",
        "en": "Operated by the company for the full reporting period",
    },
    "boundary.wizard.operating.started_during_period": {
        "zh-TW": "在報導期間內開始營運",
        "en": "Started operating during the reporting period",
    },
    "boundary.wizard.operating.stopped_during_period": {
        "zh-TW": "在報導期間內停止營運",
        "en": "Stopped operating during the reporting period",
    },
    "boundary.wizard.operating.transferred_during_period": {
        "zh-TW": "在報導期間內出售或移轉",
        "en": "Sold or transferred during the reporting period",
    },
    "boundary.wizard.operating.no_operation_full_period": {
        "zh-TW": "整個報導期間都沒有由公司營運",
        "en": "Not operated by the company at any time in the reporting period",
    },
    "boundary.wizard.operating.not_company": {
        "zh-TW": "不是本公司的工廠或營運據點",
        "en": "Not the company's factory or operating site",
    },
    "boundary.wizard.operating.uncertain": {
        "zh-TW": "尚不確定",
        "en": "Not sure",
    },
    "boundary.wizard.categories.title": {
        "zh-TW": "確認預期的排放來源",
        "en": "Confirm expected emission sources",
    },
    "boundary.wizard.categories.question": {
        "zh-TW": "本範圍是否有這類排放來源？",
        "en": "Does this reporting scope have this type of emission source?",
    },
    "boundary.wizard.categories.why": {
        "zh-TW": "先辨識可能存在的來源，後續蒐集資料時才不會漏掉設備、燃料或外購能源。",
        "en": (
            "Identifying expected sources helps prevent equipment, fuel, or "
            "purchased energy from being missed later."
        ),
    },
    "boundary.wizard.categories.uncertain": {
        "zh-TW": "此類別保留為未解決，不會自動變成「沒有」，最後一步也不會建立新版本。",
        "en": (
            "The category remains unresolved, is not changed to “No,” and blocks "
            "a new version at the final step."
        ),
    },
    "boundary.wizard.categories.uncertain_detail": {
        "zh-TW": (
            "請依下方建議詢問負責同仁並查看相關紀錄；"
            "系統不會把此回答改成「沒有」。"
        ),
        "en": (
            "Ask the suggested colleague and check the listed records. The system "
            "will not change this answer to “No.”"
        ),
    },
    "boundary.wizard.categories.review": {
        "zh-TW": "查看六個排放來源類別",
        "en": "Review all six emission-source categories",
    },
    "boundary.wizard.category_state.pending": {
        "zh-TW": "尚待回答",
        "en": "Awaiting an answer",
    },
    "boundary.wizard.category_state.expected": {"zh-TW": "有", "en": "Yes"},
    "boundary.wizard.category_state.not_expected": {
        "zh-TW": "沒有",
        "en": "No",
    },
    "boundary.wizard.category_state.uncertain": {
        "zh-TW": "尚不確定",
        "en": "Not sure",
    },
    "boundary.wizard.category_examples.stationary_combustion": {
        "zh-TW": "例如：鍋爐、加熱爐、緊急發電機。",
        "en": "Examples: boilers, furnaces, and emergency generators.",
    },
    "boundary.wizard.category_examples.mobile_combustion": {
        "zh-TW": "例如：公務車、堆高機、公司車輛。",
        "en": "Examples: business vehicles, forklifts, and company vehicles.",
    },
    "boundary.wizard.category_examples.process_emissions": {
        "zh-TW": "例如：化學反應、物理反應、製程原料轉化。",
        "en": (
            "Examples: chemical reactions, physical reactions, and process "
            "material conversion."
        ),
    },
    "boundary.wizard.category_examples.fugitive_emissions": {
        "zh-TW": "例如：冷媒、滅火器、氣體洩漏。",
        "en": "Examples: refrigerants, fire extinguishers, and gas leakage.",
    },
    "boundary.wizard.category_examples.purchased_electricity": {
        "zh-TW": "例如：台電電力、其他供電來源、共用電表分攤。",
        "en": (
            "Examples: grid electricity, other electricity suppliers, and shared "
            "meter allocations."
        ),
    },
    "boundary.wizard.category_examples.purchased_steam": {
        "zh-TW": "例如：外購蒸汽、外購熱能、園區供汽。",
        "en": "Examples: purchased steam, purchased heat, and industrial-park steam.",
    },
    "boundary.wizard.category_role.stationary_combustion": {
        "zh-TW": "廠務或環安衛。",
        "en": "Facilities or EHS.",
    },
    "boundary.wizard.category_role.mobile_combustion": {
        "zh-TW": "總務或車隊管理。",
        "en": "Administration or fleet management.",
    },
    "boundary.wizard.category_role.process_emissions": {
        "zh-TW": "生產、製程工程或環安衛。",
        "en": "Production, process engineering, or EHS.",
    },
    "boundary.wizard.category_role.fugitive_emissions": {
        "zh-TW": "廠務、冷凍空調或環安衛。",
        "en": "Facilities, refrigeration and air conditioning, or EHS.",
    },
    "boundary.wizard.category_role.purchased_electricity": {
        "zh-TW": "總務、財會或採購。",
        "en": "Administration, finance, or procurement.",
    },
    "boundary.wizard.category_role.purchased_steam": {
        "zh-TW": "廠務、採購或財會。",
        "en": "Facilities, procurement, or finance.",
    },
    "boundary.wizard.category_evidence.stationary_combustion": {
        "zh-TW": "設備清冊、燃料採購或操作許可。",
        "en": "Equipment lists, fuel purchases, or operating permits.",
    },
    "boundary.wizard.category_evidence.mobile_combustion": {
        "zh-TW": "車輛與堆高機清冊、油卡或燃料紀錄。",
        "en": "Vehicle and forklift lists, fuel cards, or fuel records.",
    },
    "boundary.wizard.category_evidence.process_emissions": {
        "zh-TW": "製程圖、物料平衡或操作許可。",
        "en": "Process diagrams, material balances, or operating permits.",
    },
    "boundary.wizard.category_evidence.fugitive_emissions": {
        "zh-TW": "冷媒補充、保養、滅火器或氣體盤點紀錄。",
        "en": (
            "Refrigerant top-up, maintenance, fire extinguisher, or gas inventory "
            "records."
        ),
    },
    "boundary.wizard.category_evidence.purchased_electricity": {
        "zh-TW": "電費單、電號、供電契約或分攤資料。",
        "en": (
            "Electricity bills, meter numbers, supply contracts, or allocation "
            "records."
        ),
    },
    "boundary.wizard.category_evidence.purchased_steam": {
        "zh-TW": "蒸汽帳單、流量紀錄或供汽契約。",
        "en": "Steam bills, flow records, or steam supply contracts.",
    },
    "boundary.wizard.review.title": {
        "zh-TW": "檢查並確認",
        "en": "Review and confirm",
    },
    "boundary.wizard.review.unresolved": {
        "zh-TW": "仍有尚待回答或尚不確定的項目。請回到對應步驟處理後再建立新版本。",
        "en": (
            "Some items are unanswered or uncertain. Return to the relevant step "
            "before creating a new version."
        ),
    },
    "boundary.wizard.review.return_step3": {
        "zh-TW": "回到公司",
        "en": "Return to companies",
    },
    "boundary.wizard.review.return_step4": {
        "zh-TW": "回到工廠與營運據點",
        "en": "Return to sites",
    },
    "boundary.wizard.review.return_step5": {
        "zh-TW": "回到排放來源",
        "en": "Return to emission sources",
    },
    "boundary.wizard.review.period": {
        "zh-TW": "報導期間",
        "en": "Reporting period",
    },
    "boundary.wizard.review.companies": {
        "zh-TW": "本次包含的公司",
        "en": "Companies in this scope",
    },
    "boundary.wizard.review.sites": {
        "zh-TW": "工廠或營運據點",
        "en": "Factories or operating sites",
    },
    "boundary.wizard.review.categories": {
        "zh-TW": "預期排放來源",
        "en": "Expected emission sources",
    },
    "boundary.wizard.review.partial_period": {
        "zh-TW": (
            "後續可能需要 {start} 至 {end} 的活動資料；"
            "本階段尚未執行資料涵蓋或計算。"
        ),
        "en": (
            "Activity data may be needed from {start} to {end}. Coverage and "
            "calculation are not performed at this stage."
        ),
    },
    "boundary.wizard.review.view_results": {
        "zh-TW": "查看目前結果",
        "en": "View current results",
    },
    "boundary.heading": {
        "zh-TW": "確認盤查與申報範圍",
        "en": "Confirm inventory and reporting boundaries",
    },
    "boundary.intro": {
        "zh-TW": (
            "以下範圍依目前的公司資料與適用性結果整理。"
            "法定要求不能由使用者取消；資料不足時，請確認事實，不會臆測法律結論。"
        ),
        "en": (
            "These boundaries are based on current company facts and "
            "applicability results. A legal requirement cannot be dismissed "
            "by the user; where facts are missing, confirm them rather than "
            "inferring a legal conclusion."
        ),
    },
    "boundary.requirement.engine_applicable": {
        "zh-TW": "目前要求",
        "en": "Current requirement",
    },
    "boundary.requirement.engine_future_requirement": {
        "zh-TW": "未來要求",
        "en": "Future requirement",
    },
    "boundary.requirement.needs_customer_fact": {
        "zh-TW": "需要公司事實或覆核",
        "en": "Company fact or review needed",
    },
    "boundary.requirement.customer_requested_voluntary": {
        "zh-TW": "公司自願要求",
        "en": "Company-requested voluntary boundary",
    },
    "boundary.status.locally_confirmed": {
        "zh-TW": "已在本機確認",
        "en": "Locally confirmed",
    },
    "boundary.confirmation.pending": {
        "zh-TW": "確認狀態：待確認",
        "en": "Confirmation status: Pending confirmation",
    },
    "boundary.confirmation.locally_confirmed": {
        "zh-TW": "確認狀態：已在本機確認",
        "en": "Confirmation status: Locally confirmed",
    },
    "boundary.confirmation.not_saved": {
        "zh-TW": "尚未建立新的本機確認版本；確認狀態仍為待確認。",
        "en": (
            "No new locally confirmed version was created; confirmation remains "
            "pending."
        ),
    },
    "boundary.legal_status": {
        "zh-TW": "法律要求：{status}",
        "en": "Legal requirement: {status}",
    },
    "boundary.progress": {
        "zh-TW": "已在本機確認 {confirmed} / {total}",
        "en": "Locally confirmed {confirmed} / {total}",
    },
    "boundary.next_task": {
        "zh-TW": "下一項：{boundary}",
        "en": "Next task: {boundary}",
    },
    "boundary.overview": {
        "zh-TW": "查看全部範圍與狀態",
        "en": "View all boundaries and statuses",
    },
    "boundary.completed_summary.unresolved": {
        "zh-TW": (
            "本機範圍確認已完成；仍有 {unresolved} 個範圍需要公司事實或覆核，"
            "不能視為已取得法律結論。"
        ),
        "en": (
            "Local boundary confirmation is complete; {unresolved} boundaries "
            "still require company facts or review and cannot be treated as "
            "legally resolved."
        ),
    },
    "boundary.completed_summary.resolved": {
        "zh-TW": (
            "已在本機確認全部 {total} 個範圍；這表示邊界資料已確認。"
            "目前沒有尚待完成的法律事實或覆核。"
        ),
        "en": (
            "All {total} boundaries are locally confirmed. This confirms the "
            "boundary information. No legal facts or reviews remain unresolved."
        ),
    },
    "boundary.completed_item": {
        "zh-TW": "✓ {boundary}",
        "en": "✓ {boundary}",
    },
    "boundary.missing_fact": {
        "zh-TW": "尚缺的明確事實：{fact}",
        "en": "Exact missing fact: {fact}",
    },
    "boundary.provide_fact": {
        "zh-TW": "公司可這樣提供：{resolution}",
        "en": "How the company can provide it: {resolution}",
    },
    "boundary.missing.has_taiwan_facilities": {
        "zh-TW": "公司在本報導期間是否有台灣廠場",
        "en": "whether the company had Taiwan facilities in this reporting period",
    },
    "boundary.missing.received_environmental_authority_inventory_notice": {
        "zh-TW": "公司是否收到環境主管機關的盤查通知",
        "en": "whether the company received an environmental inventory notice",
    },
    "boundary.missing.boundary_specific_moenv_inventory_notice_or_rule": {
        "zh-TW": "適用於這筆廠場登記的環境部指定、登記或盤查通知",
        "en": (
            "the MOENV designation, registration, or inventory notice that "
            "applies to this facility registration"
        ),
    },
    "boundary.missing.standalone_ghg_reporting_effective_timing": {
        "zh-TW": "個體溫室氣體申報範圍的官方生效年度或公司申報通知",
        "en": (
            "the official effective year or company filing notice for the "
            "standalone GHG reporting boundary"
        ),
    },
    "boundary.missing.consolidated_ghg_reporting_effective_timing": {
        "zh-TW": "合併溫室氣體申報範圍的官方生效年度或公司申報通知",
        "en": (
            "the official effective year or company filing notice for the "
            "consolidated GHG reporting boundary"
        ),
    },
    "boundary.resolve.has_taiwan_facilities": {
        "zh-TW": "確認本期間是否營運任何台灣廠場，並逐筆核對下方廠場。",
        "en": (
            "Confirm whether any Taiwan facility operated during the period "
            "and review each facility below."
        ),
    },
    "boundary.resolve.received_environmental_authority_inventory_notice": {
        "zh-TW": "確認是否收到主管機關通知；如有，填入通知或公文參考。",
        "en": (
            "Confirm whether a notice was received and provide its reference "
            "if available."
        ),
    },
    "boundary.resolve.boundary_specific_moenv_inventory_notice_or_rule": {
        "zh-TW": "提供適用的環境部指定、登記或盤查通知，供逐筆邊界覆核。",
        "en": (
            "Provide the applicable MOENV designation, registration, or "
            "inventory notice for boundary-specific review."
        ),
    },
    "boundary.resolve.standalone_ghg_reporting_effective_timing": {
        "zh-TW": "提供個體溫室氣體申報通知或邊界專屬規則資料，供覆核。",
        "en": (
            "Provide the standalone GHG filing notice or boundary-specific "
            "rule reference for review."
        ),
    },
    "boundary.resolve.consolidated_ghg_reporting_effective_timing": {
        "zh-TW": "提供合併溫室氣體申報通知或邊界專屬規則資料，供覆核。",
        "en": (
            "Provide the consolidated GHG filing notice or boundary-specific "
            "rule reference for review."
        ),
    },
    "boundary.evidence.effective_year": {
        "zh-TW": "規則生效年度：{year}",
        "en": "Rule effective year: {year}",
    },
    "boundary.evidence.authority": {
        "zh-TW": "主管機關：{authority}",
        "en": "Authority: {authority}",
    },
    "boundary.evidence.document": {
        "zh-TW": "法規來源：{document}",
        "en": "Legal source: {document}",
    },
    "boundary.purpose.moenv_facility": {
        "zh-TW": "環境部登記／營運邊界",
        "en": "MOENV registered or operating boundary",
    },
    "boundary.purpose.ifrs_reporting_entity": {
        "zh-TW": "IFRS 財務報表報導個體",
        "en": "IFRS financial-statement reporting entity",
    },
    "boundary.purpose.listed_consolidated": {
        "zh-TW": "上市櫃合併申報範圍",
        "en": "Listed-company consolidated reporting boundary",
    },
    "boundary.registration": {
        "zh-TW": "政府登記編號：{registration}",
        "en": "Government registration: {registration}",
    },
    "boundary.registration_separate": {
        "zh-TW": "每筆政府登記各自列為候選，不會因統一編號相同而自動合併。",
        "en": (
            "Each government registration remains a separate candidate. "
            "Registrations are not combined merely because they share a UBN."
        ),
    },
    "boundary.combination.heading": {
        "zh-TW": "選填：連結已核准或同一營運邊界的登記",
        "en": "Optional: link registrations in one approved or operating boundary",
    },
    "boundary.combination.help": {
        "zh-TW": (
            "政府登記預設各自分開。只有在公司有正式核准或可說明的營運盤查"
            "邊界時，才連結所選登記。每筆原始登記與政府來源都會保留。"
        ),
        "en": (
            "Government registrations remain separate by default. Link selected "
            "registrations only when an official approval or documented operating "
            "inventory boundary supports it. Every original identity and source "
            "is retained."
        ),
    },
    "boundary.combination.unverified": {
        "zh-TW": "此連結決定由使用者在本機輸入，未經帳號驗證。",
        "en": (
            "This linking decision is user-entered locally and is not "
            "account-verified."
        ),
    },
    "boundary.combination.enable": {
        "zh-TW": "這筆登記與其他登記屬於同一盤查邊界",
        "en": "This registration shares one inventory boundary with others",
    },
    "boundary.combination.targets": {
        "zh-TW": "選擇要連結的其他政府登記",
        "en": "Select the other government registrations to link",
    },
    "boundary.combination.basis": {
        "zh-TW": "用白話說明正式核准或營運合併依據",
        "en": "Plain-language official or operating combination basis",
    },
    "boundary.combination.evidence": {
        "zh-TW": "支持文件、通知或參考資料",
        "en": "Supporting document, notice, or reference",
    },
    "boundary.select": {
        "zh-TW": "選擇要確認的範圍",
        "en": "Choose a boundary to confirm",
    },
    "boundary.period.heading": {
        "zh-TW": "報導期間",
        "en": "Reporting period",
    },
    "boundary.period.suggestion": {
        "zh-TW": "系統建議年度：{year}。這只是建議，仍須由公司明確確認。",
        "en": (
            "Suggested year: {year}. This is a suggestion only and still "
            "requires explicit company confirmation."
        ),
    },
    "boundary.period.no_suggestion": {
        "zh-TW": "目前沒有可靠的年度建議，請由公司輸入並確認。",
        "en": "No reliable year is available. Enter and confirm the period.",
    },
    "boundary.period.year": {"zh-TW": "報導年度", "en": "Reporting year"},
    "boundary.period.start": {"zh-TW": "期間開始日", "en": "Period start date"},
    "boundary.period.end": {"zh-TW": "期間結束日", "en": "Period end date"},
    "boundary.period.confirm": {
        "zh-TW": "我已確認報導年度、開始日與結束日",
        "en": "I have confirmed the reporting year, start date, and end date",
    },
    "boundary.entities.heading": {
        "zh-TW": "法律實體",
        "en": "Legal entities",
    },
    "boundary.entities.help": {
        "zh-TW": "法律實體是法律上的公司，不是工廠地址。海外子公司可以沒有台灣統編。",
        "en": (
            "A legal entity is a company in law, not a factory address. "
            "An overseas subsidiary may have no Taiwan UBN."
        ),
    },
    "boundary.entity.add_count": {
        "zh-TW": "要新增幾個合併範圍內的子公司？",
        "en": "How many subsidiaries should be added to this consolidated boundary?",
    },
    "boundary.entity.name": {"zh-TW": "子公司法律名稱", "en": "Subsidiary legal name"},
    "boundary.entity.jurisdiction": {
        "zh-TW": "設立國家／地區",
        "en": "Jurisdiction",
    },
    "boundary.entity.registration": {
        "zh-TW": "當地登記識別碼（可選）",
        "en": "Local registration identifier (optional)",
    },
    "boundary.entity.ubn": {
        "zh-TW": "台灣統一編號（如適用）",
        "en": "Taiwan UBN (if applicable)",
    },
    "boundary.facilities.heading": {
        "zh-TW": "廠場範圍",
        "en": "Included facilities",
    },
    "boundary.facilities.help": {
        "zh-TW": "請逐一確認這份盤查或申報要包含哪些工廠與營業地址。",
        "en": (
            "Confirm each factory or operating location included in this "
            "inventory or filing boundary."
        ),
    },
    "boundary.membership.pending_confirmation": {
        "zh-TW": "尚未確認",
        "en": "Not yet confirmed",
    },
    "boundary.membership.included": {"zh-TW": "包含", "en": "Included"},
    "boundary.membership.excluded": {"zh-TW": "排除", "en": "Excluded"},
    "boundary.membership.not_applicable_to_period": {
        "zh-TW": "本期間不適用",
        "en": "Not applicable to this period",
    },
    "boundary.membership.reason": {
        "zh-TW": "包含／排除理由",
        "en": "Reason for inclusion or exclusion",
    },
    "boundary.membership.evidence": {
        "zh-TW": "依據或來源",
        "en": "Basis or source",
    },
    "boundary.categories.heading": {
        "zh-TW": "預期的排放來源類別",
        "en": "Expected emission-source categories",
    },
    "boundary.categories.help": {
        "zh-TW": "這一步只確認類別，不建立設備清冊。",
        "en": (
            "This step confirms categories only; it does not create "
            "an equipment register."
        ),
    },
    "boundary.category.stationary_combustion": {
        "zh-TW": "固定燃燒",
        "en": "Stationary combustion",
    },
    "boundary.category.mobile_combustion": {
        "zh-TW": "移動燃燒",
        "en": "Mobile combustion",
    },
    "boundary.category.process_emissions": {
        "zh-TW": "製程排放",
        "en": "Process emissions",
    },
    "boundary.category.fugitive_emissions": {
        "zh-TW": "逸散排放",
        "en": "Fugitive emissions",
    },
    "boundary.category.purchased_electricity": {
        "zh-TW": "外購電力",
        "en": "Purchased electricity",
    },
    "boundary.category.purchased_steam": {
        "zh-TW": "外購蒸汽",
        "en": "Purchased steam",
    },
    "boundary.category.pending": {"zh-TW": "尚未確認", "en": "Not yet confirmed"},
    "boundary.category.expected": {"zh-TW": "預期有此類別", "en": "Expected"},
    "boundary.category.not_expected": {
        "zh-TW": "預期沒有此類別",
        "en": "Not expected",
    },
    "boundary.category.not_expected_reason": {
        "zh-TW": "公司確認本期間沒有此活動的理由",
        "en": "Company reason confirming no such activity occurred this period",
    },
    "boundary.contact.heading": {
        "zh-TW": "確認人資料",
        "en": "Confirmer details",
    },
    "boundary.contact.name": {
        "zh-TW": "確認人姓名（必填，自行填寫）",
        "en": "Confirmer name (required, self-entered)",
    },
    "boundary.contact.title": {
        "zh-TW": "職稱（必填，自行填寫）",
        "en": "Job title (required, self-entered)",
    },
    "boundary.contact.unverified": {
        "zh-TW": "確認人資料由使用者自行填寫，未經帳號驗證",
        "en": "Contact details are self-entered and not account-verified",
    },
    "boundary.contact.reconfirm_legacy": {
        "zh-TW": "此歷史版本缺少必要確認人資料，須補齊姓名與職稱並重新確認。",
        "en": (
            "This historical version lacks required confirmer details. Enter "
            "the name and job title and reconfirm it."
        ),
    },
    "boundary.confirm": {
        "zh-TW": "在本機工作區確認此範圍",
        "en": "Confirm this boundary in the local workspace",
    },
    "boundary.confirmed": {
        "zh-TW": "公司已在此本機工作區確認",
        "en": "Confirmed by the company in this local workspace",
    },
    "boundary.confirm_error": {
        "zh-TW": "請先確認報導期間、所有實體、廠場與六個來源類別。",
        "en": (
            "Confirm the reporting period, every entity and facility, "
            "and all six source categories first."
        ),
    },
    "boundary.error.included_entity": {
        "zh-TW": "至少須包含一個法律實體；全數排除不能確認為有效範圍。",
        "en": (
            "Include at least one legal entity; an all-excluded boundary cannot "
            "be confirmed."
        ),
    },
    "boundary.error.included_registration": {
        "zh-TW": "環境部登記邊界須包含對應的已登記廠場，不能只排除該廠場。",
        "en": (
            "An MOENV registration boundary must include its registered facility; "
            "excluding that facility cannot create an empty confirmed boundary."
        ),
    },
    "boundary.error.exclusion_support": {
        "zh-TW": "每筆排除或本期間不適用的項目，都須填寫白話理由與支持依據。",
        "en": (
            "Every excluded or not-applicable item requires a plain-language "
            "reason and supporting basis."
        ),
    },
    "boundary.error.not_expected_reason": {
        "zh-TW": "選擇「預期沒有此類別」時，須記錄公司確認本期間沒有該活動的理由。",
        "en": (
            "A category marked not expected requires the company's reason "
            "confirming no such activity occurred during the period."
        ),
    },
    "boundary.error.period": {
        "zh-TW": "請確認一個有效的年度或會計年度期間；不能使用不合理的跨多年期間。",
        "en": (
            "Confirm a valid annual or fiscal-year period; implausible multi-year "
            "periods are not accepted."
        ),
    },
    "boundary.error.pending": {
        "zh-TW": "尚未確認與排除不同；請逐一完成所有實體、廠場與來源類別。",
        "en": (
            "Pending confirmation is different from exclusion. Complete every "
            "entity, facility, and source category."
        ),
    },
    "boundary.error.combination": {
        "zh-TW": "登記連結須選擇有效的其他登記，填寫依據與證據，且不能形成循環連結。",
        "en": (
            "Registration links need valid other registrations, a basis and "
            "evidence, and cannot form a circular link."
        ),
    },
    "boundary.error.combination_target_required": {
        "zh-TW": "請至少選擇一筆要合併的政府登記。",
        "en": "Select at least one other government registration.",
    },
    "boundary.error.combination_basis_required": {
        "zh-TW": "請說明這些登記屬於同一盤查邊界的依據。",
        "en": (
            "Explain why these registrations belong to the same inventory "
            "boundary."
        ),
    },
    "boundary.error.combination_evidence_required": {
        "zh-TW": "請填寫支持文件、通知或參考資料。",
        "en": "Provide the supporting document, notice, or reference.",
    },
    "boundary.error.responsible_contact_name": {
        "zh-TW": "請填寫確認人姓名。",
        "en": "Enter the confirmer name.",
    },
    "boundary.error.responsible_job_title": {
        "zh-TW": "請填寫確認人職稱。",
        "en": "Enter the confirmer job title.",
    },
    "boundary.prior.heading": {
        "zh-TW": "前期已確認資料（僅供參考）",
        "en": "Prior-period confirmations (reference only)",
    },
    "boundary.prior.item": {
        "zh-TW": (
            "{year}：{start} 至 {end}；不計入目前 {current_year} 年進度"
        ),
        "en": (
            "FY{year}: {start} to {end}; not counted in FY{current_year} progress"
        ),
    },
    "boundary.period.choose_active": {
        "zh-TW": "選擇本次要使用的已確認報導期間",
        "en": "Select the confirmed reporting period to use",
    },
    "boundary.period.choose_placeholder": {
        "zh-TW": "請明確選擇期間",
        "en": "Select a period",
    },
    "boundary.period.option": {
        "zh-TW": "{year}：{start} 至 {end}",
        "en": "FY{year}: {start} to {end}",
    },
    "boundary.period.active": {
        "zh-TW": "目前報導期間：{period}",
        "en": "Active reporting period: {period}",
    },
    "boundary.legacy.title": {
        "zh-TW": "待確認的既有範圍",
        "en": "Existing scope to review",
    },
    "boundary.local.heading": {
        "zh-TW": "本機原型工作區限制",
        "en": "Local prototype workspace limitations",
    },
    "boundary.local.summary": {
        "zh-TW": (
            "這是本機原型工作區，不是企業授權系統，也不是合規等級紀錄庫。"
        ),
        "en": (
            "This is a local prototype workspace, not an enterprise authorization "
            "system or compliance-grade record store."
        ),
    },
    "boundary.local.details": {
        "zh-TW": (
            "沒有帳號身分驗證、角色權限或職責分離；沒有伺服器端存取控制、"
            "多人並行控制或雲端備份；資料以本機明文保存，除非作業系統另行保護。"
            "原子寫入與版本歷程不代表查核等級的確認。"
        ),
        "en": (
            "There is no authenticated identity, RBAC, separation of duties, "
            "server-side access control, multi-user concurrency control, or cloud "
            "backup. Data is stored as local plaintext unless the operating system "
            "protects it. Atomic writes and version history do not make this an "
            "audit-grade confirmation system."
        ),
    },
    "report.title": {
        "zh-TW": "溫室氣體排放計算與適用性摘要報告",
        "en": "GHG Emissions Calculation and Applicability Summary",
    },
    "report.pdf_button": {
        "zh-TW": "下載碳排摘要報告（PDF）",
        "en": "Download Emissions Summary Report (PDF)",
    },
    "report.generating": {
        "zh-TW": "正在產生碳排摘要報告…",
        "en": "Generating the emissions summary report…",
    },
    "report.ready": {
        "zh-TW": "報告已就緒，可下載。",
        "en": "The report is ready to download.",
    },
    "report.card_title": {
        "zh-TW": "碳排摘要報告（PDF）",
        "en": "Emissions summary report (PDF)",
    },
    "report.card_help": {
        "zh-TW": (
            "給公司主管、客戶與永續人員的主要成果文件。"
            "內容依目前已計算結果彙整，不是環境部正式申報檔或第三方查驗報告。"
        ),
        "en": (
            "The primary deliverable for management, customers, and sustainability "
            "teams. It summarises currently calculated results and is not an official "
            "MOENV filing or third-party verification report."
        ),
    },
    "report.technical_files": {
        "zh-TW": "專業覆核附件",
        "en": "Technical review files",
    },
    "report.technical_help": {
        "zh-TW": "給內部覆核與專業人員的列級資料與稽核包，預設收合。",
        "en": "Row-level files and the audit package for specialist review.",
    },
    "report.empty.no_company_title": {
        "zh-TW": "尚未完成公司與報導期間設定",
        "en": "Company and reporting period are not set",
    },
    "report.empty.no_company_body": {
        "zh-TW": "請先完成公司與報導期間設定，才能產生可匯出的碳排報告。",
        "en": (
            "Complete company and reporting-period setup before an emissions "
            "report can be exported."
        ),
    },
    "report.empty.cta_company": {
        "zh-TW": "完成公司與報導期間設定",
        "en": "Complete company and reporting period setup",
    },
    "report.empty.no_period_title": {
        "zh-TW": "請確認本次報導期間",
        "en": "Confirm this reporting period",
    },
    "report.empty.no_period_body": {
        "zh-TW": "請先確認本次要匯出的報導期間，才能產生可匯出的碳排報告。",
        "en": (
            "Confirm the reporting period for this export before an emissions "
            "report can be generated."
        ),
    },
    "report.empty.cta_period": {
        "zh-TW": "確認本次報導期間",
        "en": "Confirm this reporting period",
    },
    "report.empty.no_result_title": {
        "zh-TW": "尚無可匯出的碳排結果",
        "en": "No emissions results to export yet",
    },
    "report.empty.no_result_body": {
        "zh-TW": "尚無可匯出的碳排結果。請先上傳活動資料並完成計算。",
        "en": (
            "There are no emissions results to export yet. "
            "Upload activity data and complete the calculation first."
        ),
    },
    "report.empty.cta_intake": {
        "zh-TW": "前往排放資料與計算",
        "en": "Go to Emissions Data & Calculations",
    },
    "report.not_provided": {"zh-TW": "尚未提供", "en": "Not yet provided"},
    "report.none": {"zh-TW": "無", "en": "None"},
    "report.applicability.not_completed": {
        "zh-TW": "適用性評估尚未完成",
        "en": "Applicability assessment not yet completed",
    },
    "report.still_pending": {"zh-TW": "仍待確認", "en": "Still to be confirmed"},
    "report.value_unavailable": {"zh-TW": "—", "en": "—"},
    "report.unnamed_file": {"zh-TW": "來源文件", "en": "Source file"},
    "report.cover.kicker": {
        "zh-TW": "CARBON EVIDENCE LEDGER",
        "en": "CARBON EVIDENCE LEDGER",
    },
    "report.cover.company": {"zh-TW": "公司名稱", "en": "Company"},
    "report.cover.period": {"zh-TW": "報導期間", "en": "Reporting period"},
    "report.cover.year": {
        "zh-TW": "法規適用年度",
        "en": "Legal applicability year",
    },
    "report.cover.status": {
        "zh-TW": "碳排結果狀態",
        "en": "Emissions result status",
    },
    "report.cover.coverage": {
        "zh-TW": "上傳資料／排放分析期間",
        "en": "Uploaded data / emissions analysis period",
    },
    "report.cover.generated": {"zh-TW": "產生日期", "en": "Generated"},
    "report.cover.version": {"zh-TW": "系統版本", "en": "System version"},
    "report.cover.positioning": {
        "zh-TW": (
            "本文件為系統依使用者提供資料產生的溫室氣體排放計算與適用性摘要，"
            "供內部管理、客戶溝通與作品集展示使用。"
            "不是環境部正式盤查報告書、正式申報檔、第三方查驗報告、"
            "IFRS 正式揭露文件，也不表示已符合或已取得 ISO 或 GHG Protocol 認證。"
        ),
        "en": (
            "This document summarises GHG emissions calculated from user-provided "
            "data for management, customer communication, and portfolio use. "
            "It is not an official MOENV inventory report, a statutory filing, "
            "a third-party verification opinion, an IFRS disclosure, or evidence "
            "of ISO or GHG Protocol certification."
        ),
    },
    "report.section.summary": {"zh-TW": "管理摘要", "en": "Management summary"},
    "report.section.applicability": {
        "zh-TW": "適用性判定摘要",
        "en": "Applicability summary",
    },
    "report.section.boundary": {
        "zh-TW": "報導與盤查範圍",
        "en": "Reporting and inventory boundary",
    },
    "report.section.results": {"zh-TW": "排放結果", "en": "Emissions results"},
    "report.section.sites": {"zh-TW": "廠場別摘要", "en": "Site summary"},
    "report.section.methods": {
        "zh-TW": "計算方法與排放係數",
        "en": "Calculation methods and emission factors",
    },
    "report.section.assumptions": {
        "zh-TW": "重要計算假設",
        "en": "Key calculation assumptions",
    },
    "report.section.quality": {
        "zh-TW": "資料品質與對帳",
        "en": "Data quality and reconciliation",
    },
    "report.section.limits": {
        "zh-TW": "限制、未涵蓋項目與聲明",
        "en": "Limitations, exclusions and statements",
    },
    "report.section.appendix": {"zh-TW": "附錄", "en": "Appendix"},
    "report.section.factor_list": {
        "zh-TW": "排放係數清單",
        "en": "Emission-factor list",
    },
    "report.section.pending_items": {
        "zh-TW": "重要待確認項目",
        "en": "Open confirmation items",
    },
    "report.kpi.total": {"zh-TW": "目前計算總排放量", "en": "Calculated total"},
    "report.kpi.included": {"zh-TW": "納入資料筆數", "en": "Included rows"},
    "report.kpi.included_value": {
        "zh-TW": "{included}／{total}",
        "en": "{included} / {total}",
    },
    "report.kpi.pending": {"zh-TW": "待確認項目", "en": "Pending items"},
    "report.kpi.excluded": {"zh-TW": "排除資料", "en": "Excluded rows"},
    "report.kpi.documents": {"zh-TW": "來源文件", "en": "Source files"},
    "report.kpi.status": {"zh-TW": "結果狀態", "en": "Result status"},
    "report.chart.scope": {
        "zh-TW": "Scope 1／Scope 2 結果",
        "en": "Scope 1 / Scope 2 results",
    },
    "report.chart.sources": {
        "zh-TW": "排放來源占比",
        "en": "Share by emissions source",
    },
    "report.col.item": {"zh-TW": "項目", "en": "Item"},
    "report.col.status": {"zh-TW": "客戶狀態", "en": "Status"},
    "report.col.timing": {"zh-TW": "生效／申報年度", "en": "Effective / filing year"},
    "report.col.reason": {"zh-TW": "判定摘要", "en": "Rationale"},
    "report.col.field": {"zh-TW": "欄位", "en": "Field"},
    "report.col.value": {"zh-TW": "內容", "en": "Value"},
    "report.col.source": {"zh-TW": "排放來源", "en": "Source"},
    "report.col.tco2e": {"zh-TW": "排放量（tCO₂e）", "en": "Emissions (tCO₂e)"},
    "report.col.usage_count": {"zh-TW": "使用筆數", "en": "Rows used"},
    "report.col.share": {"zh-TW": "占比", "en": "Share"},
    "report.col.site": {"zh-TW": "廠場", "en": "Site"},
    "report.col.method": {"zh-TW": "計算方法", "en": "Method"},
    "report.col.factor": {"zh-TW": "排放係數", "en": "Emission factor"},
    "report.col.unit": {"zh-TW": "係數單位", "en": "Factor unit"},
    "report.col.factor_source": {"zh-TW": "係數來源", "en": "Factor source"},
    "report.col.year": {"zh-TW": "係數年份", "en": "Factor year"},
    "report.col.disposition": {"zh-TW": "資料狀態", "en": "Data status"},
    "report.col.count": {"zh-TW": "筆數", "en": "Rows"},
    "report.col.file": {"zh-TW": "來源文件", "en": "Source file"},
    "report.col.sheet": {"zh-TW": "工作表", "en": "Worksheet"},
    "report.col.rows": {"zh-TW": "資料筆數", "en": "Row count"},
    "report.disp.calculated": {"zh-TW": "已計算", "en": "Calculated"},
    "report.disp.needs_confirmation": {"zh-TW": "待確認", "en": "Needs confirmation"},
    "report.disp.no_matching_factor": {
        "zh-TW": "目前無符合係數",
        "en": "No matching factor",
    },
    "report.disp.excluded_duplicate": {
        "zh-TW": "排除重複",
        "en": "Excluded as duplicate",
    },
    "report.disp.excluded_out_of_scope": {
        "zh-TW": "超出範圍",
        "en": "Out of scope",
    },
    "report.disp.unsupported": {"zh-TW": "不支援", "en": "Not supported"},
    "report.disp.invalid": {"zh-TW": "無效", "en": "Invalid"},
    "report.method.activity_times_factor": {
        "zh-TW": "活動數據 × 排放係數，必要時先做單位轉換",
        "en": "Activity data × emission factor, with unit conversion where required",
    },
    "report.heating_used": {
        "zh-TW": "本次計算使用熱值 {value} {unit}",
        "en": "Heating value used in this calculation: {value} {unit}",
    },
    "report.activity_with_subtype": {
        "zh-TW": "{activity}（{subtype}）",
        "en": "{activity} ({subtype})",
    },
    "report.coverage.partial": {
        "zh-TW": (
            "本次上傳資料只涵蓋報導期間的一部分；資料涵蓋期間與已確認報導期間不同。"
        ),
        "en": (
            "Uploaded activity data covers only part of the confirmed reporting "
            "period. The two periods are shown separately."
        ),
    },
    "report.factor_source.ref_tw_moea_2024_electricity_factor": {
        "zh-TW": "經濟部公告電力排放係數",
        "en": "MOEA published electricity emission factor",
    },
    "report.factor_source.ref_tw_moenv_2024_emission_factors": {
        "zh-TW": "環境部公告排放係數",
        "en": "MOENV published emission factors",
    },
    "report.factor_source.ref_sync_src_tw_moenv_electricity_factor_enterprise_2025": {
        "zh-TW": "環境部／經濟部企業盤查用電力排放係數",
        "en": "MOENV / MOEA enterprise-inventory electricity factor",
    },
    "report.factor_source.official": {
        "zh-TW": "官方排放係數",
        "en": "Official emission factor",
    },
    "report.scope3_note": {
        "zh-TW": (
            "本版本尚未納入 Scope 3 計算；目前總量只包含系統已支援並納入的 "
            "Scope 1 與 Scope 2 資料。"
        ),
        "en": (
            "This version does not yet include Scope 3. The current total covers "
            "only Scope 1 and Scope 2 data that the system supports and has included."
        ),
    },
    "report.applicability_disclaimer": {
        "zh-TW": (
            "本適用性摘要為系統依使用者提供資料產生的初步評估，"
            "不構成法律意見、主管機關認定或第三方確信結論。"
        ),
        "en": (
            "This applicability summary is a preliminary assessment from "
            "user-provided data. It is not legal advice, a regulator determination, "
            "or a third-party assurance conclusion."
        ),
    },
    "report.boundary.entity": {
        "zh-TW": "公司／法律實體",
        "en": "Company / legal entity",
    },
    "report.boundary.entities": {
        "zh-TW": "已確認納入的法律實體",
        "en": "Confirmed included legal entities",
    },
    "report.boundary.entities_pending": {
        "zh-TW": "仍待確認的法律實體",
        "en": "Legal entities still to confirm",
    },
    "report.boundary.confirmed_purpose": {
        "zh-TW": "已確認盤查目的：{purpose}",
        "en": "Confirmed inventory purpose: {purpose}",
    },
    "report.boundary.draft_purpose": {
        "zh-TW": "仍待確認的盤查目的：{purpose}",
        "en": "Inventory purpose still to confirm: {purpose}",
    },
    "report.boundary.summary": {
        "zh-TW": "組織邊界摘要",
        "en": "Organizational boundary summary",
    },
    "report.boundary.sites": {"zh-TW": "納入廠場", "en": "Included sites"},
    "report.boundary.pending": {
        "zh-TW": "尚待確認的邊界事項",
        "en": "Boundary items still to confirm",
    },
    "report.boundary.exclusions": {
        "zh-TW": "重要排除項目及原因",
        "en": "Material exclusions and reasons",
    },
    "report.boundary.sites_pending": {
        "zh-TW": "納入廠場仍待確認",
        "en": "Included sites are still to be confirmed",
    },
    "report.boundary.confirmed_company": {
        "zh-TW": "目前以使用者確認的公司資料呈現：{company}",
        "en": "Presented from customer-confirmed company data: {company}",
    },
    "report.status.complete_body": {
        "zh-TW": "系統已支援並納入的資料均已完成計算；排除項目未計入總量。",
        "en": (
            "All supported in-scope data currently included has been calculated. "
            "Excluded rows are not in the total."
        ),
    },
    "report.status.preliminary_body": {
        "zh-TW": "仍有待確認、不支援或無效資料，本結果為初步碳排結果。",
        "en": (
            "Pending, unsupported or invalid rows remain, so this is a "
            "preliminary emissions result."
        ),
    },
    "report.assume.ghg_protocol": {
        "zh-TW": "計算及呈現方式參考 GHG Protocol 企業盤查與報導原則。",
        "en": (
            "Calculation and presentation follow the GHG Protocol Corporate "
            "Standard as a reference."
        ),
    },
    "report.assume.location_based": {
        "zh-TW": "Scope 2 目前以地區基準方法呈現。",
        "en": "Scope 2 is currently presented on a location-based basis.",
    },
    "report.assume.calculated_only": {
        "zh-TW": "總量只加總系統已計算完成的列，排除列不視為零排放。",
        "en": (
            "The total sums calculated rows only. Excluded rows are not treated "
            "as zero emissions."
        ),
    },
    "report.quality.reconciled": {
        "zh-TW": "對帳一致：原始在範圍內非空列均已歸入互斥狀態。",
        "en": "Reconciled: every in-scope source row has one exclusive status.",
    },
    "report.quality.unreconciled": {
        "zh-TW": "對帳仍待核對：列數與互斥狀態加總不一致。",
        "en": "Reconciliation still needs review: row counts do not yet match.",
    },
    "report.quality.exclusion_note": {
        "zh-TW": "排除的重複或超出範圍資料不計入排放總量，也不單獨讓完整結果改為初步。",
        "en": (
            "Duplicate or out-of-scope exclusions are not counted as emissions "
            "and do not by themselves make a complete result preliminary."
        ),
    },
    "report.limit.supported_only": {
        "zh-TW": "總量只涵蓋已上傳、在範圍內且系統支援的資料。",
        "en": "The total covers uploaded, in-scope, system-supported data only.",
    },
    "report.limit.scope3": {
        "zh-TW": "Scope 3 尚未納入本版本計算。",
        "en": "Scope 3 is not included in this version.",
    },
    "report.limit.refrigerant": {
        "zh-TW": "冷媒僅計算已確認的實際補充量；設備逸散率估算法尚未納入。",
        "en": (
            "Refrigerant totals include confirmed actual refill only; "
            "equipment leak-rate estimation is not included."
        ),
    },
    "report.limit.no_assurance": {
        "zh-TW": "本報告未經第三方查驗。",
        "en": "This report has not been third-party verified.",
    },
    "report.limit.not_filing": {
        "zh-TW": "本報告不是環境部正式申報檔。",
        "en": "This report is not an official MOENV filing.",
    },
    "report.limit.not_legal": {
        "zh-TW": "不構成法律意見或 IFRS 確信結論。",
        "en": "This is not legal advice or an IFRS assurance conclusion.",
    },
    "report.limit.preliminary_items": {
        "zh-TW": "初步結果仍有 {n} 筆待確認、不支援或無效資料尚未納入計算。",
        "en": (
            "This preliminary result still has {n} pending, unsupported or "
            "invalid rows not included in the calculation."
        ),
    },
    "report.limit.complete_not_all_sources": {
        "zh-TW": (
            "「碳排計算完成」僅表示目前已上傳且系統支援的資料已計算完成，"
            "不表示整家公司所有排放源已完整盤查。"
        ),
        "en": (
            "“Emissions calculation complete” means currently uploaded, "
            "system-supported data has been calculated. It does not mean every "
            "company emissions source has been inventoried."
        ),
    },
    "report.limit.preliminary_banner": {
        "zh-TW": "本文件為初步結果，請勿以正式、完成盤查或可申報理解。",
        "en": (
            "This document is a preliminary result. Do not treat it as a formal, "
            "complete inventory or a filing-ready statement."
        ),
    },
    "report.pending.generic": {
        "zh-TW": "另有 {n} 筆資料仍待確認後才能納入計算。",
        "en": "{n} additional rows still need confirmation before calculation.",
    },
    "report.pending.none": {
        "zh-TW": "目前沒有列出的待確認排放來源。",
        "en": "No listed emissions sources are waiting for confirmation.",
    },
    "report.appendix.generated": {
        "zh-TW": "報告產生時間：{when}",
        "en": "Report generated at: {when}",
    },
}


def normalize_lang(lang: str | None) -> str:
    """Return a supported language code."""
    if lang in (LANG_ZH, LANG_EN):
        return lang
    if lang in LANG_OPTION_TO_CODE:
        return LANG_OPTION_TO_CODE[lang]
    return DEFAULT_LANG


def t(key: str, lang: str | None = None, **kwargs: Any) -> str:
    """Translate a UI key for the active language."""
    code = normalize_lang(lang)
    entry = MESSAGES.get(key)
    if entry is None:
        return key
    text = entry.get(code) or entry.get(LANG_EN) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def status_label(code: str, lang: str | None = None) -> str:
    """Map an internal status code to a beginner-facing label."""
    key = f"status.{code}"
    if key in MESSAGES:
        return t(key, lang)
    cleaned = str(code or "").strip()
    if not cleaned:
        return t("status.unknown", lang)
    return cleaned.replace("_", " ")
