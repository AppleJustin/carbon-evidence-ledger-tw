"""Pure tests for Phase 8 / 8B UI view-model helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from carbon_ledger.pipeline import PipelineRunResult, run_demo_pipeline
from carbon_ledger.ui import view_models as vm
from carbon_ledger.ui.glossary import glossary_contains
from carbon_ledger.ui.tutorial import onboarding_step_titles

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED_INGESTED_AT = pd.Timestamp("2024-02-01T00:00:00Z")
EN = "en"
ZH = "zh-TW"


def _full_result():
    return run_demo_pipeline(
        REPO_ROOT,
        run_id="ui_view_model_test",
        ingested_at=FIXED_INGESTED_AT,
        include_ghg=True,
        include_cbam=True,
        include_ifrs_s2=True,
    )


def _core_only_result():
    return run_demo_pipeline(
        REPO_ROOT,
        run_id="ui_view_model_core",
        ingested_at=FIXED_INGESTED_AT,
        include_ghg=False,
        include_cbam=False,
        include_ifrs_s2=False,
    )


def _row(overview: pd.DataFrame, activity_type: str) -> pd.Series:
    matched = overview[overview["activity_type"] == activity_type]
    assert len(matched) == 1
    return matched.iloc[0]


def test_activity_overview_returns_five_baseline_rows() -> None:
    overview = vm.build_activity_overview(_full_result(), EN)
    assert len(overview) == 5


def test_activity_names_are_human_readable() -> None:
    overview = vm.build_activity_overview(_full_result(), EN)
    names = set(overview["activity_name"])
    assert "Purchased electricity" in names
    assert "Natural gas" in names
    assert "Diesel" in names
    assert "Purchased steel wire rod" in names
    assert "Finished-goods output" in names


def test_electricity_displays_calculated() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "grid_electricity")
    assert row["calculation_label"] == "Calculated"


def test_natural_gas_displays_blocked_missing_conversion() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "natural_gas")
    assert row["calculation_label"] == "Blocked — missing conversion"


def test_diesel_displays_blocked_missing_conversion() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "diesel")
    assert row["calculation_label"] == "Blocked — missing conversion"


def test_purchased_steel_displays_emission_factor_needed() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "purchased_steel")
    assert row["calculation_label"] == "Emission factor needed"


def test_finished_output_displays_supporting_data() -> None:
    row = _row(
        vm.build_activity_overview(_full_result(), EN),
        "finished_goods_output",
    )
    assert row["calculation_label"] == "Supporting data"


def test_electricity_ghg_label_is_scope_2() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "grid_electricity")
    assert row["ghg_label"] == "Scope 2"


def test_natural_gas_ghg_label_is_scope_1() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "natural_gas")
    assert row["ghg_label"] == "Scope 1"


def test_diesel_ghg_label_is_scope_1() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "diesel")
    assert row["ghg_label"] == "Scope 1"


def test_purchased_steel_ghg_label_scope_3_category_1() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "purchased_steel")
    assert row["ghg_label"] == "Scope 3 Category 1"


def test_finished_output_ghg_label_not_applicable() -> None:
    row = _row(
        vm.build_activity_overview(_full_result(), EN),
        "finished_goods_output",
    )
    assert row["ghg_label"] == "Not applicable"


def test_cbam_labels_separated_from_ghg_labels() -> None:
    overview = vm.build_activity_overview(_full_result(), EN)
    for _, row in overview.iterrows():
        assert row["cbam_label"] != row["ghg_label"]


def test_ifrs_labels_separated_from_ghg_labels() -> None:
    overview = vm.build_activity_overview(_full_result(), EN)
    for _, row in overview.iterrows():
        assert row["ifrs_s2_label"] != row["ghg_label"]


def test_disabled_adapter_displays_not_run() -> None:
    overview = vm.build_activity_overview(_core_only_result(), EN)
    assert (overview["ghg_label"] == "Not run").all()
    assert (overview["cbam_label"] == "Not run").all()
    assert (overview["ifrs_s2_label"] == "Not run").all()


def test_calculated_emissions_summary_includes_calculated_rows_only() -> None:
    summary = vm.calculated_emissions_summary(_full_result(), EN)
    assert summary["calculated_row_count"] == 1
    assert summary["calculated_tco2e"] is not None
    assert summary["calculated_tco2e"] > 0
    assert summary["partial"] is True
    assert summary["label"] == "Partial result"


def test_blocked_records_are_not_treated_as_zero() -> None:
    result = _full_result()
    overview = vm.build_activity_overview(result, EN)
    blocked = overview[
        overview["calculation_label"].isin(
            ["Blocked — missing conversion", "Emission factor needed"]
        )
    ]
    assert not blocked.empty
    assert blocked["calculated_tco2e"].isna().all()
    summary = vm.calculated_emissions_summary(result, EN)
    assert summary["calculated_row_count"] == 1


def test_qa_count_equals_current_core_qa_rows() -> None:
    result = _full_result()
    kpis = vm.dashboard_kpi_counts(result, EN)
    assert kpis["open_qa_issues"] == len(result.core_qa_issues)


def test_attention_flag_true_for_baseline_gas() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "natural_gas")
    assert bool(row["attention_required"]) is True


def test_attention_flag_true_for_baseline_diesel() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "diesel")
    assert bool(row["attention_required"]) is True


def test_attention_flag_true_for_baseline_steel() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "purchased_steel")
    assert bool(row["attention_required"]) is True


def test_attention_flag_false_for_electricity() -> None:
    row = _row(vm.build_activity_overview(_full_result(), EN), "grid_electricity")
    assert bool(row["attention_required"]) is False


def test_attention_flag_false_for_finished_output() -> None:
    row = _row(
        vm.build_activity_overview(_full_result(), EN),
        "finished_goods_output",
    )
    assert bool(row["attention_required"]) is False


def test_original_pipeline_result_dataframes_are_not_mutated() -> None:
    result = _full_result()
    before = {
        "activities": result.activity_records_accepted.copy(deep=True),
        "calculations": result.calculation_results.copy(deep=True),
        "ghg": result.ghg_evaluations.copy(deep=True),
        "cbam": result.cbam_evaluations.copy(deep=True),
        "ifrs": result.ifrs_s2_evaluations.copy(deep=True),
        "qa": result.core_qa_issues.copy(deep=True),
    }
    _ = vm.build_activity_overview(result, ZH)
    _ = vm.calculated_emissions_summary(result, ZH)
    _ = vm.attention_issue_cards(result, ZH)
    _ = vm.issues_table(result, ZH)
    _ = vm.ghg_framework_table(result, ZH)
    _ = vm.cbam_framework_table(result, ZH)
    _ = vm.ifrs_framework_table(result, ZH)
    assert result.activity_records_accepted.equals(before["activities"])
    assert result.calculation_results.equals(before["calculations"])
    assert result.ghg_evaluations.equals(before["ghg"])
    assert result.cbam_evaluations.equals(before["cbam"])
    assert result.ifrs_s2_evaluations.equals(before["ifrs"])
    assert result.core_qa_issues.equals(before["qa"])


def test_zh_default_status_labels() -> None:
    row = _row(vm.build_activity_overview(_full_result(), ZH), "natural_gas")
    assert "缺少轉換" in row["calculation_label"]


def test_glossary_core_terms() -> None:
    for term in (
        "Activity",
        "Emission factor",
        "tCO2e",
        "Scope 1",
        "Scope 2",
        "Scope 3",
        "IFRS S2",
    ):
        assert glossary_contains(term)
    assert not glossary_contains("CBAM")


def test_onboarding_has_five_action_steps() -> None:
    steps = onboarding_step_titles(ZH)
    assert steps == [
        "完成公司設定",
        "上傳活動資料",
        "確認資料內容",
        "開始計算",
        "查看計算結果",
    ]
    joined = "\n".join(steps)
    assert "GHG Protocol" not in joined
    assert "IFRS" not in joined


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame()


def _synthetic_result(
    *,
    calculations: pd.DataFrame | None = None,
    activities: pd.DataFrame | None = None,
    ghg: pd.DataFrame | None = None,
) -> PipelineRunResult:
    empty = _empty_frame()
    return PipelineRunResult(
        run_id="cat1-filter-test",
        ingested_at=FIXED_INGESTED_AT,
        include_ghg=True,
        include_cbam=False,
        include_ifrs_s2=False,
        source_documents_accepted=empty,
        source_documents_rejected=empty,
        activity_records_accepted=(
            empty if activities is None else activities
        ),
        activity_records_rejected=empty,
        normalized_records=empty,
        candidate_matches=empty,
        activity_readiness=empty,
        calculation_results=(
            empty if calculations is None else calculations
        ),
        core_qa_issues=empty,
        ghg_evaluations=empty if ghg is None else ghg,
        cbam_evaluations=empty,
        ifrs_s2_evaluations=empty,
    )


def _steel_calc_row(
    record_id: str,
    *,
    status: str = "calculated",
    tco2e: float | None = 18.5,
    ghg_scope: object = "scope_3",
    scope_3_category: object = "category_1",
    include_ghg_scope: bool = True,
    include_scope_3_category: bool = True,
    scope3_category: str | None = None,
    factor_year: object = 2025,
    announcement_year: object = None,
    source_url: str = "",
) -> dict[str, object]:
    row: dict[str, object] = {
        "record_id": record_id,
        "calculation_status": status,
        "calculated_tco2e": tco2e,
        "calculation_method": "supplier_specific",
        "supplier_name": "Demo Steel",
        "steel_product_type": "steel wire rod",
        "factor_year": factor_year,
        "reporting_year": 2025,
        "factor_boundary": "cradle_to_gate",
    }
    if source_url:
        row["source_url"] = source_url
    if announcement_year is not None:
        row["announcement_year"] = announcement_year
    if include_ghg_scope:
        row["ghg_scope"] = ghg_scope
    if include_scope_3_category:
        row["scope_3_category"] = scope_3_category
    if scope3_category is not None:
        row["scope3_category"] = scope3_category
    return row


def _activity_row(
    record_id: str,
    activity_type: str = "purchased_steel",
) -> dict[str, str]:
    return {"record_id": record_id, "activity_type": activity_type}


def _ghg_eval_row(
    record_id: str,
    ghg_scope: str,
    mapping_status: str = "mapped",
) -> dict[str, str]:
    return {
        "record_id": record_id,
        "ghg_scope": ghg_scope,
        "mapping_status": mapping_status,
    }


def _inventory_pair() -> tuple[
    list[dict[str, object]],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    calculations: list[dict[str, object]] = [
        {
            "record_id": "rec_s1",
            "calculation_status": "calculated",
            "calculated_tco2e": 10.0,
            "ghg_scope": "scope_1",
        },
        {
            "record_id": "rec_s2",
            "calculation_status": "calculated",
            "calculated_tco2e": 5.0,
            "ghg_scope": "scope_2",
        },
    ]
    activities = [
        _activity_row("rec_s1", "natural_gas"),
        _activity_row("rec_s2", "grid_electricity"),
    ]
    ghg = [
        _ghg_eval_row("rec_s1", "scope_1"),
        _ghg_eval_row("rec_s2", "scope_2"),
    ]
    return calculations, activities, ghg


def test_category_1_subtotal_includes_calculated_scope3_category_1_steel() -> None:
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                _steel_calc_row(
                    "rec_steel",
                    scope3_category="category_1_purchased_goods_and_services",
                )
            ]
        ),
        activities=pd.DataFrame([_activity_row("rec_steel")]),
    )
    summary = vm.scope3_category1_emissions_summary(result, ZH)
    assert summary["tco2e"] == 18.5
    assert summary["row_count"] == 1
    assert summary["rows"][0]["record_id"] == "rec_steel"


def test_category_1_subtotal_excludes_scope3_category_4_steel() -> None:
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                _steel_calc_row(
                    "rec_steel_cat4",
                    tco2e=99.0,
                    scope_3_category="category_4",
                )
            ]
        ),
        activities=pd.DataFrame([_activity_row("rec_steel_cat4")]),
    )
    summary = vm.scope3_category1_emissions_summary(result, ZH)
    assert summary["tco2e"] is None
    assert summary["row_count"] == 0
    assert summary["rows"] == []


def test_category_1_subtotal_excludes_blocked_transport_splits() -> None:
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                _steel_calc_row(
                    "rec_cat4_split",
                    status="blocked_tier1_inbound_transport_requires_category4_split",
                    tco2e=None,
                ),
                _steel_calc_row(
                    "rec_s1s2_split",
                    status="blocked_company_controlled_transport_requires_scope1_or2_split",
                    tco2e=None,
                ),
            ]
        ),
        activities=pd.DataFrame(
            [
                _activity_row("rec_cat4_split"),
                _activity_row("rec_s1s2_split"),
            ]
        ),
    )
    summary = vm.scope3_category1_emissions_summary(result, ZH)
    assert summary["tco2e"] is None
    assert summary["row_count"] == 0


def test_category_1_subtotal_excludes_steel_missing_scope_3_category() -> None:
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                _steel_calc_row(
                    "rec_steel_no_cat",
                    tco2e=50.0,
                    include_scope_3_category=False,
                )
            ]
        ),
        activities=pd.DataFrame([_activity_row("rec_steel_no_cat")]),
    )
    summary = vm.scope3_category1_emissions_summary(result, ZH)
    assert summary["tco2e"] is None
    assert summary["row_count"] == 0


def test_category_1_subtotal_excludes_blank_or_long_name_scope_3_category() -> None:
    blank = _synthetic_result(
        calculations=pd.DataFrame(
            [_steel_calc_row("rec_blank", tco2e=40.0, scope_3_category="")]
        ),
        activities=pd.DataFrame([_activity_row("rec_blank")]),
    )
    long_name = _synthetic_result(
        calculations=pd.DataFrame(
            [
                _steel_calc_row(
                    "rec_long",
                    tco2e=40.0,
                    scope_3_category="category_1_purchased_goods_and_services",
                )
            ]
        ),
        activities=pd.DataFrame([_activity_row("rec_long")]),
    )
    assert vm.scope3_category1_emissions_summary(blank, ZH)["row_count"] == 0
    assert vm.scope3_category1_emissions_summary(long_name, ZH)["row_count"] == 0


def test_category_1_subtotal_excludes_scope_1_steel() -> None:
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [_steel_calc_row("rec_scope1_steel", ghg_scope="scope_1")]
        ),
        activities=pd.DataFrame([_activity_row("rec_scope1_steel")]),
    )
    summary = vm.scope3_category1_emissions_summary(result, ZH)
    assert summary["tco2e"] is None
    assert summary["row_count"] == 0


def test_category_1_subtotal_excludes_blocked_category_1_steel() -> None:
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                _steel_calc_row(
                    "rec_blocked",
                    status="no_factor_configured",
                    tco2e=None,
                )
            ]
        ),
        activities=pd.DataFrame([_activity_row("rec_blocked")]),
    )
    summary = vm.scope3_category1_emissions_summary(result, ZH)
    assert summary["tco2e"] is None
    assert summary["row_count"] == 0


def test_category_4_or_missing_category_does_not_change_category_1_subtotal() -> None:
    baseline = _synthetic_result(
        calculations=pd.DataFrame([_steel_calc_row("rec_cat1")]),
        activities=pd.DataFrame([_activity_row("rec_cat1")]),
    )
    mixed = _synthetic_result(
        calculations=pd.DataFrame(
            [
                _steel_calc_row("rec_cat1"),
                _steel_calc_row(
                    "rec_cat4",
                    tco2e=99.0,
                    scope_3_category="category_4",
                ),
                _steel_calc_row(
                    "rec_missing",
                    tco2e=50.0,
                    include_scope_3_category=False,
                ),
                _steel_calc_row(
                    "rec_cat2",
                    tco2e=7.0,
                    scope_3_category="category_2",
                ),
            ]
        ),
        activities=pd.DataFrame(
            [
                _activity_row("rec_cat1"),
                _activity_row("rec_cat4"),
                _activity_row("rec_missing"),
                _activity_row("rec_cat2"),
            ]
        ),
    )
    base_summary = vm.scope3_category1_emissions_summary(baseline, ZH)
    mixed_summary = vm.scope3_category1_emissions_summary(mixed, ZH)
    assert base_summary["tco2e"] == 18.5
    assert mixed_summary["tco2e"] == base_summary["tco2e"]
    assert mixed_summary["row_count"] == 1
    assert mixed_summary["rows"][0]["record_id"] == "rec_cat1"


def test_scope_1_and_scope_2_inventory_unaffected_by_category_1_filter() -> None:
    calc_rows, activity_rows, ghg_rows = _inventory_pair()
    without_steel = _synthetic_result(
        calculations=pd.DataFrame(calc_rows),
        activities=pd.DataFrame(activity_rows),
        ghg=pd.DataFrame(ghg_rows),
    )
    with_steel = _synthetic_result(
        calculations=pd.DataFrame(
            [
                *calc_rows,
                _steel_calc_row("rec_cat1"),
                _steel_calc_row(
                    "rec_cat4",
                    tco2e=99.0,
                    scope_3_category="category_4",
                ),
                _steel_calc_row(
                    "rec_missing",
                    tco2e=50.0,
                    include_scope_3_category=False,
                ),
            ]
        ),
        activities=pd.DataFrame(
            [
                *activity_rows,
                _activity_row("rec_cat1"),
                _activity_row("rec_cat4"),
                _activity_row("rec_missing"),
            ]
        ),
        ghg=pd.DataFrame(
            [
                *ghg_rows,
                _ghg_eval_row("rec_cat1", "scope_3"),
                _ghg_eval_row("rec_cat4", "scope_3"),
                _ghg_eval_row("rec_missing", "scope_3"),
            ]
        ),
    )
    base_inventory = vm.company_inventory_emissions_summary(without_steel, ZH)
    steel_inventory = vm.company_inventory_emissions_summary(with_steel, ZH)
    assert base_inventory["inventory_tco2e"] == 15.0
    assert steel_inventory["inventory_tco2e"] == base_inventory["inventory_tco2e"]
    assert steel_inventory["scope_1"] == 10.0
    assert steel_inventory["scope_2"] == 5.0
    cat1 = vm.scope3_category1_emissions_summary(with_steel, ZH)
    assert cat1["tco2e"] == 18.5
    assert cat1["tco2e"] != steel_inventory["inventory_tco2e"]


def test_format_display_year_strips_trailing_float_zero() -> None:
    assert vm.format_display_year(2013.0) == "2013"
    assert vm.format_display_year("2013.0") == "2013"
    assert vm.format_display_year(2013) == "2013"
    assert vm.format_display_year("2013") == "2013"
    assert vm.format_display_year(2.415) == "2.415"


def _steel_24_15_result() -> PipelineRunResult:
    calc_rows, activity_rows, ghg_rows = _inventory_pair()
    return _synthetic_result(
        calculations=pd.DataFrame(
            [
                *calc_rows,
                _steel_calc_row(
                    "rec_steel",
                    tco2e=24.15,
                    factor_year=2013.0,
                    announcement_year=2013.0,
                ),
            ]
        ),
        activities=pd.DataFrame(
            [*activity_rows, _activity_row("rec_steel")]
        ),
        ghg=pd.DataFrame(
            [*ghg_rows, _ghg_eval_row("rec_steel", "scope_3")]
        ),
    )


def test_scope3_kpi_includes_mapped_category_1_steel_24_15() -> None:
    result = _steel_24_15_result()
    states = vm.scope_kpi_states(result, ZH)
    cat1 = vm.scope3_category1_emissions_summary(result, ZH)
    inventory = vm.company_inventory_emissions_summary(result, ZH)
    assert states["scope_3"]["state"] == "calculated"
    assert states["scope_3"]["value"] == pytest.approx(24.15)
    assert "24.15" in str(states["scope_3"]["caption"])
    assert "Category 1－採購商品與服務" in str(states["scope_3"]["caption"])
    assert "尚不代表完整 Scope 3 總量" in str(states["scope_3"]["caption"])
    assert "尚未納入計算" not in str(states["scope_3"]["caption"])
    assert cat1["tco2e"] == pytest.approx(24.15)
    assert cat1["row_count"] == 1
    assert inventory["scope_1"] == pytest.approx(10.0)
    assert inventory["scope_2"] == pytest.approx(5.0)
    assert inventory["inventory_tco2e"] == pytest.approx(15.0)
    assert inventory["inventory_tco2e"] != pytest.approx(15.0 + 24.15)
    assert cat1["tco2e"] == pytest.approx(states["scope_3"]["value"])


def test_scope3_summary_and_category1_share_calculation_results() -> None:
    result = _steel_24_15_result()
    summary = vm.scope3_emissions_summary(result, ZH)
    cat1 = vm.scope3_category1_emissions_summary(result, ZH)
    inventory = vm.company_inventory_emissions_summary(result, ZH)
    steel_ids = {
        str(row["record_id"])
        for row in result.calculation_results.to_dict(orient="records")
        if str(row.get("record_id")) == "rec_steel"
    }
    assert steel_ids == {"rec_steel"}
    assert summary["tco2e"] == pytest.approx(cat1["tco2e"])
    assert summary["row_count"] == cat1["row_count"] == 1
    assert "rec_steel" not in vm.company_inventory_record_ids(result)
    assert inventory["inventory_tco2e"] + cat1["tco2e"] != inventory[
        "inventory_tco2e"
    ]


def test_scope3_kpi_excludes_needs_review_r410a() -> None:
    calc_rows, activity_rows, ghg_rows = _inventory_pair()
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                *calc_rows,
                {
                    "record_id": "rec_r410a",
                    "calculation_status": "calculated",
                    "calculated_tco2e": 3.847,
                    "ghg_scope": "scope_3",
                    "scope_3_category": "category_1",
                },
            ]
        ),
        activities=pd.DataFrame(
            [
                *activity_rows,
                _activity_row("rec_r410a", "refrigerant_refill"),
            ]
        ),
        ghg=pd.DataFrame(
            [
                *ghg_rows,
                _ghg_eval_row(
                    "rec_r410a", "scope_3", mapping_status="needs_review"
                ),
            ]
        ),
    )
    states = vm.scope_kpi_states(result, ZH)
    assert states["scope_3"]["state"] == "empty"
    assert states["scope_3"]["value"] is None
    assert vm.scope3_emissions_summary(result, ZH)["tco2e"] is None


def test_scope3_kpi_excludes_outside_boundary() -> None:
    calc_rows, activity_rows, ghg_rows = _inventory_pair()
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                *calc_rows,
                {
                    "record_id": "rec_r32_out",
                    "calculation_status": "calculated",
                    "calculated_tco2e": 2.031,
                    "ghg_scope": "scope_3",
                    "scope_3_category": "category_1",
                },
            ]
        ),
        activities=pd.DataFrame(
            [
                *activity_rows,
                _activity_row("rec_r32_out", "refrigerant_refill"),
            ]
        ),
        ghg=pd.DataFrame(
            [
                *ghg_rows,
                _ghg_eval_row(
                    "rec_r32_out",
                    "scope_3",
                    mapping_status="outside_boundary",
                ),
            ]
        ),
    )
    states = vm.scope_kpi_states(result, ZH)
    assert states["scope_3"]["state"] == "empty"
    assert states["scope_3"]["value"] is None


def test_scope3_kpi_excludes_blocked_and_no_matching_factor() -> None:
    calc_rows, activity_rows, ghg_rows = _inventory_pair()
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                *calc_rows,
                _steel_calc_row(
                    "rec_blocked",
                    status="blocked_tier1_inbound_transport_requires_category4_split",
                    tco2e=99.0,
                ),
                _steel_calc_row(
                    "rec_nofactor",
                    status="no_matching_factor",
                    tco2e=50.0,
                ),
            ]
        ),
        activities=pd.DataFrame(
            [
                *activity_rows,
                _activity_row("rec_blocked"),
                _activity_row("rec_nofactor"),
            ]
        ),
        ghg=pd.DataFrame(
            [
                *ghg_rows,
                _ghg_eval_row("rec_blocked", "scope_3"),
                _ghg_eval_row("rec_nofactor", "scope_3"),
            ]
        ),
    )
    states = vm.scope_kpi_states(result, ZH)
    assert states["scope_3"]["state"] == "empty"
    assert states["scope_3"]["value"] is None


def test_scope3_kpi_excludes_missing_scope_3_category() -> None:
    calc_rows, activity_rows, ghg_rows = _inventory_pair()
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                *calc_rows,
                _steel_calc_row(
                    "rec_missing_cat",
                    tco2e=24.15,
                    include_scope_3_category=False,
                ),
            ]
        ),
        activities=pd.DataFrame(
            [*activity_rows, _activity_row("rec_missing_cat")]
        ),
        ghg=pd.DataFrame(
            [*ghg_rows, _ghg_eval_row("rec_missing_cat", "scope_3")]
        ),
    )
    states = vm.scope_kpi_states(result, ZH)
    assert states["scope_3"]["state"] == "empty"
    assert states["scope_3"]["value"] is None
    cat1 = vm.scope3_category1_emissions_summary(result, ZH)
    assert cat1["tco2e"] is None


def test_scope3_kpi_empty_when_no_qualifying_rows() -> None:
    calc_rows, activity_rows, ghg_rows = _inventory_pair()
    result = _synthetic_result(
        calculations=pd.DataFrame(calc_rows),
        activities=pd.DataFrame(activity_rows),
        ghg=pd.DataFrame(ghg_rows),
    )
    states = vm.scope_kpi_states(result, ZH)
    summary = vm.scope3_emissions_summary(result, ZH)
    assert states["scope_3"]["state"] == "empty"
    assert states["scope_3"]["value"] is None
    assert states["scope_3"]["caption"] == "目前尚無可納入的 Scope 3 計算結果。"
    assert summary["caption"] == states["scope_3"]["caption"]
    assert "尚未納入計算" not in states["scope_3"]["caption"]
    assert "不支援" not in states["scope_3"]["caption"]


def test_category1_factor_year_display_is_2013_not_float() -> None:
    result = _steel_24_15_result()
    cat1 = vm.scope3_category1_emissions_summary(result, ZH)
    assert cat1["rows"][0]["factor_year"] == "2013"
    assert cat1["rows"][0]["announcement_year"] == "2013"
    assert cat1["rows"][0]["factor_year"] != "2013.0"
    raw = result.calculation_results.loc[
        result.calculation_results["record_id"] == "rec_steel", "factor_year"
    ].iloc[0]
    assert float(raw) == pytest.approx(2013.0)


def test_category1_source_url_href_encodes_query_and_drops_api_key() -> None:
    raw = (
        "https://data.moenv.gov.tw/api/v2/cfp_p_02"
        "?limit=1000&sort=ImportDate desc&format=JSON&api_key=SECRET"
    )
    calc_rows, activity_rows, ghg_rows = _inventory_pair()
    result = _synthetic_result(
        calculations=pd.DataFrame(
            [
                *calc_rows,
                _steel_calc_row(
                    "rec_steel",
                    tco2e=24.15,
                    factor_year=2013,
                    source_url=raw,
                ),
            ]
        ),
        activities=pd.DataFrame(
            [*activity_rows, _activity_row("rec_steel")]
        ),
        ghg=pd.DataFrame(
            [*ghg_rows, _ghg_eval_row("rec_steel", "scope_3")]
        ),
    )
    href = vm.scope3_category1_emissions_summary(result, ZH)["rows"][0][
        "source_url"
    ]
    markdown = vm.source_url_markdown(href)
    assert "sort=" in href
    assert "ImportDate%20desc" in href or "ImportDate+desc" in href
    assert "format=JSON" in href
    assert "api_key" not in href
    assert "SECRET" not in href
    assert markdown == f"[{href}]({href})"
    assert "sort=" in markdown
    assert "ImportDate%20desc" in markdown or "ImportDate+desc" in markdown
    assert "format=JSON" in markdown
    assert "api_key" not in markdown


def test_hero_caption_omits_calculated_scope3() -> None:
    result = _steel_24_15_result()
    states = vm.scope_kpi_states(result, ZH)
    caption = vm.labeled_scope_hero_caption(states, ZH)
    assert "Scope 3" not in caption
    assert "24.15" not in caption
    assert "Scope 1" in caption
    assert "Scope 2" in caption
