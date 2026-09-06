"""Offline CFP_P_02 steel candidate, matching, and updater tests."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from carbon_ledger.cfp_p_02 import (
    API_KEY_ENV,
    DATA_GOV_DATASET_PAGE_URL,
    STEEL_OFFICIAL_PRODUCT_NAMES,
    CfpParseError,
    build_snapshot,
    candidate_records_from_snapshot,
    fetch_all_pages,
    fetch_cfp_p_02_snapshot,
    is_generic_steel_label,
    is_steel_official_product,
    official_source_record_id,
    parse_data_gov_dataset_distributions,
    redact_api_key_from_url,
    select_public_cfp_resource_url,
    steel_official_records,
)
from carbon_ledger.purchased_steel import (
    FACTOR_BOUNDARY_CRADLE_TO_GATE,
    METHOD_AVERAGE_DATA,
    STATUS_BLOCKED_AMBIGUOUS_FACTOR,
    STATUS_BLOCKED_MISSING_PRODUCT_TYPE,
    STATUS_CALCULATED,
    STATUS_NO_MATCHING_FACTOR,
    calculate_purchased_steel,
)
from carbon_ledger.reference_sync import (
    LIFECYCLE_ACTIVE,
    activate_candidate,
    default_paths,
    fetch_and_stage_sources,
    propose_official_factor_update,
)
from carbon_ledger.steel_factor_catalog import (
    UNDECIDED_PRODUCT_TYPE,
    activate_reviewed_steel_factor,
    load_active_steel_factors,
    load_steel_factor_candidates,
    steel_product_type_choices,
    upsert_steel_candidates,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "cfp_p_02"
PURCHASED_STEEL_SRC = (
    REPO_ROOT / "src" / "carbon_ledger" / "purchased_steel.py"
).read_text(encoding="utf-8")


def _page_fetcher(*, offset: int, limit: int, api_key: str = "") -> dict:
    assert API_KEY_ENV not in str(api_key)
    if offset == 0:
        return json.loads((FIXTURES / "page_offset_0.json").read_text(encoding="utf-8"))
    if offset == limit:
        return json.loads((FIXTURES / "page_offset_5.json").read_text(encoding="utf-8"))
    return {"records": []}


def _approved_plate_factor(**fields: object) -> dict[str, object]:
    row: dict[str, object] = {
        "factor_id": "ef_steel_plate_test_v1",
        "activity_type": "purchased_steel",
        "steel_product_type": "鋼板",
        "factor_value": "2.415",
        "numerator_unit": "kgCO2e",
        "denominator_unit": "kg",
        "factor_boundary": FACTOR_BOUNDARY_CRADLE_TO_GATE,
        "geography": "TW",
        "factor_year": "2023",
        "source_reference_id": "ref_test_cfp_steel_plate",
        "factor_status": "ready",
        "factor_version": "v1",
        "valid_from": "2023-01-01",
        "valid_to": "2025-12-31",
        "approved_for_reporting_from": "2023-01-01",
        "approved_for_reporting_to": "2025-12-31",
        "source_record_id": "fixture-plate",
        "source_url": "https://data.moenv.gov.tw/dataset/detail/CFP_P_02",
        "snapshot_hash": "abc123",
        "is_secondary_or_proxy": "true",
        "factor_includes_tier1_to_reporting_company_transport": "false",
    }
    row.update(fields)
    return row


def _plate_activity(**fields: object) -> dict[str, object]:
    record: dict[str, object] = {
        "record_id": "rec_plate_001",
        "calculation_method": METHOD_AVERAGE_DATA,
        "steel_product_type": "鋼板",
        "purchased_quantity": 10,
        "purchased_unit": "t",
        "factor_geography": "TW",
        "reporting_year": 2025,
        "reporting_period_id": "period-2025",
        "activity_type": "purchased_steel",
        "record_type": "material_input",
        "factor_includes_tier1_to_reporting_company_transport": False,
    }
    record.update(fields)
    return record


def test_fixture_parses_distinct_steel_products_across_pages() -> None:
    pages = fetch_all_pages(_page_fetcher, limit=5)
    assert len(pages) == 2
    snapshot = build_snapshot(pages, retrieved_at="2026-09-04T00:00:00Z")
    steel = steel_official_records(snapshot.records)
    names = [row.name for row in steel]
    assert "鋼板" in names
    assert "熱軋粗鋼捲" in names
    assert "熱軋鋼捲" in names
    assert "冷軋鋼捲" in names
    assert "碳鋼冷軋鋼捲" in names
    assert "不鏽鋼" in names
    assert names.count("鋼板") == 1
    assert "熱軋粗鋼捲" != "熱軋鋼捲"
    assert "波特蘭水泥" not in names
    assert "採購鋼材" not in names
    plate = next(row for row in steel if row.name == "鋼板")
    assert plate.coe == "2.415"
    assert plate.announcementyear == "2023"
    assert snapshot.extra["lifecycle_boundary_stated_by_api"] is False
    assert snapshot.extra["official_validity_period_stated_by_api"] is False


def test_source_record_id_is_deterministic_and_redacts_api_key() -> None:
    first = official_source_record_id(
        name="鋼板",
        coe="2.415",
        unit="kg",
        departmentname="Redacted Agency A",
        announcementyear="2023",
    )
    second = official_source_record_id(
        name="鋼板",
        coe="2.415",
        unit="kg",
        departmentname="Redacted Agency A",
        announcementyear="2023",
    )
    assert first == second
    assert "2.415" not in PURCHASED_STEEL_SRC
    url = redact_api_key_from_url(
        "https://data.moenv.gov.tw/api/v2/CFP_P_02"
        "?api_key=SHOULD_NOT_STORE&limit=5&sort=ImportDate desc&format=JSON"
    )
    assert "api_key" not in url
    assert "SHOULD_NOT_STORE" not in url
    assert "sort=" in url
    assert "ImportDate%20desc" in url or "ImportDate+desc" in url
    assert "format=JSON" in url
    assert "limit=5" in url


def test_generic_purchased_steel_label_does_not_auto_select_factor() -> None:
    assert is_generic_steel_label("採購鋼材")
    result = calculate_purchased_steel(
        _plate_activity(steel_product_type="採購鋼材"),
        registered_factors=pd.DataFrame([_approved_plate_factor()]),
    )
    assert result.calculation_status == STATUS_BLOCKED_MISSING_PRODUCT_TYPE
    assert result.calculated_kgco2e is None


def test_exact_steel_plate_with_unique_approved_factor_calculates() -> None:
    result = calculate_purchased_steel(
        _plate_activity(),
        registered_factors=pd.DataFrame([_approved_plate_factor()]),
    )
    assert result.calculation_status == STATUS_CALCULATED
    assert result.calculated_kgco2e == 24150.0
    assert result.calculated_tco2e == 24.15
    assert result.ghg_scope == "scope_3"
    assert result.scope3_category == "category_1_purchased_goods_and_services"
    row = result.to_calculation_row()
    assert row["scope_3_category"] == "category_1"
    assert row["factor_id"] == "ef_steel_plate_test_v1"
    assert row["factor_version"] == "v1"
    assert row["steel_product_type"] == "鋼板"
    assert row["source_record_id"] == "fixture-plate"
    assert "purchased mass" in str(row["match_reason"]).lower() or "exact match" in str(
        row["match_reason"]
    ).lower()


def test_zero_matches_are_no_matching_factor() -> None:
    result = calculate_purchased_steel(
        _plate_activity(steel_product_type="熱軋鋼捲"),
        registered_factors=pd.DataFrame([_approved_plate_factor()]),
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_kgco2e is None


def test_multiple_matches_are_blocked_ambiguous() -> None:
    factors = pd.DataFrame(
        [
            _approved_plate_factor(factor_id="ef_a", factor_version="v1"),
            _approved_plate_factor(
                factor_id="ef_b",
                factor_version="v2",
                factor_year="2024",
                source_reference_id="ref_other",
            ),
        ]
    )
    result = calculate_purchased_steel(
        _plate_activity(),
        registered_factors=factors,
    )
    assert result.calculation_status == STATUS_BLOCKED_AMBIGUOUS_FACTOR
    assert result.calculated_kgco2e is None


def test_unapproved_candidate_is_not_used_for_calculation(tmp_path: Path) -> None:
    upsert_steel_candidates(
        [
            {
                "source_record_id": "cand-plate",
                "snapshot_hash": "snap1",
                "official_name": "鋼板",
                "official_coe": "2.415",
                "official_unit": "kg",
                "steel_product_type": "鋼板",
                "factor_value": "2.415",
                "numerator_unit": "kgCO2e",
                "denominator_unit": "kg",
                "factor_year": "2023",
                "source_url": "https://data.moenv.gov.tw/dataset/detail/CFP_P_02",
            }
        ],
        snapshot_id="snap_test",
        source_id="src_tw_moenv_cfp_p_02",
        retrieved_at="2026-09-04T00:00:00Z",
        reference_dir=tmp_path,
    )
    candidates = load_steel_factor_candidates(tmp_path)
    assert not candidates.empty
    assert (candidates["approval_status"] == "pending_review").all()
    active = load_active_steel_factors(tmp_path)
    assert active.empty
    result = calculate_purchased_steel(
        _plate_activity(),
        registered_factors=active,
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR


def test_official_update_adds_candidates_without_overwriting_active(
    tmp_path: Path,
) -> None:
    from tests.test_reference_sync import _seed_repo

    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    (paths["reference_dir"] / "purchased_steel_factors.csv").write_text(
        "factor_id,activity_type,steel_product_type,factor_status,factor_version\n"
        "ef_keep,purchased_steel,鋼板,ready,v1\n",
        encoding="utf-8",
    )
    before = (paths["reference_dir"] / "purchased_steel_factors.csv").read_text(
        encoding="utf-8"
    )
    first = fetch_and_stage_sources(
        root,
        retrieved_at="2026-09-04T00:00:00Z",
        source_ids=["src_tw_moenv_cfp_p_02"],
        cfp_page_fetcher=lambda **kwargs: _page_fetcher(
            offset=kwargs["offset"],
            limit=kwargs["limit"],
            api_key="",
        ),
        cfp_page_limit=5,
    )
    assert first[0]["status"] == "staged"
    assert first[0]["candidates_created"] > 0
    after = (paths["reference_dir"] / "purchased_steel_factors.csv").read_text(
        encoding="utf-8"
    )
    assert after == before
    proposal_new = propose_official_factor_update(
        root, retrieved_at="2026-09-04T00:00:00Z"
    )
    assert proposal_new["open_pr"] is True
    assert proposal_new["steel_candidate_ids"]
    second = fetch_and_stage_sources(
        root,
        retrieved_at="2026-09-05T00:00:00Z",
        source_ids=["src_tw_moenv_cfp_p_02"],
        cfp_page_fetcher=lambda **kwargs: _page_fetcher(
            offset=kwargs["offset"],
            limit=kwargs["limit"],
            api_key="",
        ),
        cfp_page_limit=5,
    )
    assert second[0]["status"] == "already_known"
    assert second[0]["candidates_created"] == 0
    proposal = propose_official_factor_update(
        root, retrieved_at="2026-09-05T00:00:00Z"
    )
    assert proposal["open_pr"] is False


def test_parse_failure_fails_closed() -> None:
    with pytest.raises(CfpParseError):
        build_snapshot(
            [{"not_records": []}],
            retrieved_at="2026-09-04T00:00:00Z",
        )


def test_old_result_keeps_original_factor_version() -> None:
    first = calculate_purchased_steel(
        _plate_activity(),
        registered_factors=pd.DataFrame([_approved_plate_factor()]),
    )
    assert first.factor_version == "v1"
    later_registry = pd.DataFrame(
        [
            _approved_plate_factor(),
            _approved_plate_factor(
                factor_id="ef_steel_plate_test_v2",
                factor_version="v2",
                factor_year="2024",
                source_reference_id="ref_test_cfp_steel_plate_v2",
            ),
        ]
    )
    second = calculate_purchased_steel(
        _plate_activity(),
        registered_factors=later_registry,
    )
    assert second.calculation_status == STATUS_BLOCKED_AMBIGUOUS_FACTOR
    assert first.factor_version == "v1"
    assert first.calculated_kgco2e == 24150.0


def test_partial_year_coverage_cannot_represent_full_year() -> None:
    result = calculate_purchased_steel(
        _plate_activity(),
        registered_factors=pd.DataFrame(
            [
                _approved_plate_factor(
                    approved_for_reporting_from="2025-07-01",
                    approved_for_reporting_to="2025-12-31",
                    valid_from="2025-07-01",
                    valid_to="2025-12-31",
                )
            ]
        ),
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR


def test_expired_factor_cannot_represent_reporting_year() -> None:
    result = calculate_purchased_steel(
        _plate_activity(),
        registered_factors=pd.DataFrame(
            [
                _approved_plate_factor(
                    approved_for_reporting_from="2023-01-01",
                    approved_for_reporting_to="2024-12-31",
                    valid_from="2023-01-01",
                    valid_to="2024-12-31",
                )
            ]
        ),
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_kgco2e is None


def test_not_yet_effective_factor_cannot_represent_reporting_year() -> None:
    result = calculate_purchased_steel(
        _plate_activity(),
        registered_factors=pd.DataFrame(
            [
                _approved_plate_factor(
                    approved_for_reporting_from="2026-01-01",
                    approved_for_reporting_to="2026-12-31",
                    valid_from="2026-01-01",
                    valid_to="2026-12-31",
                )
            ]
        ),
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_kgco2e is None


def test_product_choices_come_from_taxonomy_not_streamlit() -> None:
    choices = steel_product_type_choices()
    assert "鋼板" in choices
    assert "熱軋鋼捲" in choices
    assert "冷軋鋼捲" in choices
    assert "不鏽鋼" in choices
    assert UNDECIDED_PRODUCT_TYPE in choices
    assert "採購鋼材" not in choices
    for name in STEEL_OFFICIAL_PRODUCT_NAMES:
        assert name in choices or is_steel_official_product(name)


def test_reviewed_activation_requires_internal_applicability(tmp_path: Path) -> None:
    with pytest.raises(Exception):
        activate_reviewed_steel_factor(
            {
                "steel_product_type": "鋼板",
                "factor_value": "2.415",
                "numerator_unit": "kgCO2e",
                "denominator_unit": "kg",
                "lifecycle_boundary": FACTOR_BOUNDARY_CRADLE_TO_GATE,
                "geography": "TW",
                "factor_year": "2023",
                "source_record_id": "x",
                "source_url": "https://data.moenv.gov.tw/dataset/detail/CFP_P_02",
                "snapshot_hash": "h",
                "approval_status": "pending_review",
                "reviewer": "",
                "approved_at": "",
                "factor_version": "v1",
            },
            reference_dir=tmp_path,
        )


def test_activate_candidate_still_refuses_steel(tmp_path: Path) -> None:
    from tests.test_reference_sync import _seed_repo

    root = _seed_repo(tmp_path)
    fetch_and_stage_sources(
        root,
        retrieved_at="2026-09-04T00:00:00Z",
        source_ids=["src_tw_moenv_cfp_p_02"],
        cfp_page_fetcher=lambda **kwargs: _page_fetcher(
            offset=kwargs["offset"],
            limit=kwargs["limit"],
            api_key="",
        ),
        cfp_page_limit=5,
    )
    paths = default_paths(root)
    from carbon_ledger.reference_sync import validate_candidates

    validate_candidates(
        paths["candidates_csv"],
        official_sources_csv=paths["sources"],
    )
    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    steel = candidates.loc[
        candidates["reference_type"] == "purchased_steel_average_data"
    ]
    assert not steel.empty
    with pytest.raises(Exception) as exc:
        activate_candidate(
            candidate_id=str(steel.iloc[0]["candidate_id"]),
            candidates_csv=paths["candidates_csv"],
            snapshots_csv=paths["snapshots_csv"],
            activations_csv=paths["activations_csv"],
            emission_factors_csv=paths["emission_factors"],
            fuel_heating_values_csv=paths["fuel_heating_values"],
            gwp_values_csv=paths["gwp_values"],
            activated_at="2026-09-04T00:00:00Z",
        )
    assert getattr(exc.value, "code", "") == "STEEL_FACTOR_NOT_AUTO_ACTIVATED"
    assert LIFECYCLE_ACTIVE not in set(steel["lifecycle_status"])


def test_candidate_records_do_not_invent_valid_from() -> None:
    pages = fetch_all_pages(_page_fetcher, limit=5)
    snapshot = build_snapshot(pages, retrieved_at="2026-09-04T00:00:00Z")
    rows = candidate_records_from_snapshot(snapshot)
    assert rows
    for row in rows:
        assert row["valid_from"] == ""
        assert row["valid_to"] == ""
        assert row["geography"] == ""
        assert row["lifecycle_boundary"] == ""
        assert row["factor_year"] == row["official_announcementyear"]
        assert "valid_from" not in row["applicability_notes"] or "not" in row[
            "applicability_notes"
        ]


def test_activate_steel_cli_fails_closed_without_candidates() -> None:
    from carbon_ledger.__main__ import _run_references_command, build_parser

    parser = build_parser()
    args = parser.parse_args(
        [
            "references",
            "activate-steel",
            "--candidate-id",
            "cand_missing",
            "--reviewer",
            "reviewer",
            "--approved-at",
            "2026-01-01T00:00:00Z",
            "--factor-version",
            "1",
            "--lifecycle-boundary",
            "cradle_to_gate",
            "--geography",
            "TW",
            "--approved-for-reporting-from",
            "2025-01-01",
            "--rationale",
            "internal review of official CFP_P_02 row",
            "--confirm",
        ]
    )
    assert _run_references_command(args) == 2


PAGE_PARSED_TOKEN = "PAGE_PARSED_TOKEN_NOT_IN_SOURCE"
OFFICIAL_SNAPSHOT = FIXTURES / "official_snapshot.json"
CFP_SRC = (REPO_ROOT / "src" / "carbon_ledger" / "cfp_p_02.py").read_text(
    encoding="utf-8"
)


def _public_page_html() -> str:
    return (FIXTURES / "data_gov_dataset_page.html").read_text(encoding="utf-8")


def _public_resource_fetcher(url: str) -> bytes:
    assert PAGE_PARSED_TOKEN in url
    from urllib.parse import parse_qs, urlsplit

    offset = int((parse_qs(urlsplit(url).query).get("offset") or ["0"])[0])
    if offset == 0:
        return (FIXTURES / "page_offset_0.json").read_bytes()
    if offset == 5:
        return (FIXTURES / "page_offset_5.json").read_bytes()
    return json.dumps({"records": []}).encode("utf-8")


def test_public_resource_url_is_parsed_from_dataset_page_not_hardcoded() -> None:
    distributions = parse_data_gov_dataset_distributions(_public_page_html())
    url, encoding = select_public_cfp_resource_url(distributions)
    assert encoding == "JSON"
    assert PAGE_PARSED_TOKEN in url
    assert "data.moenv.gov.tw" in url
    assert PAGE_PARSED_TOKEN not in CFP_SRC
    assert PAGE_PARSED_TOKEN not in DATA_GOV_DATASET_PAGE_URL
    assert "api_key=PAGE_PARSED" not in CFP_SRC


def test_fetch_without_moenv_api_key_uses_public_resource(monkeypatch) -> None:
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    snapshot = fetch_cfp_p_02_snapshot(
        retrieved_at="2026-09-05T00:00:00Z",
        environ={},
        dataset_page_fetcher=_public_page_html,
        public_resource_fetcher=_public_resource_fetcher,
        limit=5,
    )
    assert snapshot.record_count > 0
    assert PAGE_PARSED_TOKEN not in snapshot.source_url
    assert "api_key=" not in snapshot.source_url
    plate = next(row for row in snapshot.records if row.name == "鋼板")
    assert plate.coe == "2.415"
    assert plate.unit in {"kg", "公斤(kg)"}
    first = snapshot.response_sha256
    second = fetch_cfp_p_02_snapshot(
        retrieved_at="2026-09-06T00:00:00Z",
        environ={},
        dataset_page_fetcher=_public_page_html,
        public_resource_fetcher=_public_resource_fetcher,
        limit=5,
    )
    assert second.response_sha256 == first


def test_official_snapshot_fixture_parses_steel_plate() -> None:
    payload = json.loads(OFFICIAL_SNAPSHOT.read_text(encoding="utf-8"))
    assert payload["source_dataset"] == "CFP_P_02"
    assert payload["data_gov_dataset_page"] == DATA_GOV_DATASET_PAGE_URL
    assert payload["retrieved_at"]
    assert payload["response_sha256"]
    assert payload["source_url"]
    assert "api_key=" not in payload["source_url"]
    records = payload["records"]
    plates = [row for row in records if row["name"] == "鋼板"]
    assert len(plates) == 1
    plate = plates[0]
    assert plate["coe"] == "2.415"
    assert "公斤" in plate["unit"] or plate["unit"] == "kg"
    assert plate["departmentname"] == "中國鋼鐵股份有限公司"
    assert plate["announcementyear"] == "2013"
    rebuilt = build_snapshot(
        [{"records": records}],
        retrieved_at=payload["retrieved_at"],
        source_url=payload["source_url"],
    )
    assert rebuilt.response_sha256 == payload["response_sha256"]
    steel = steel_official_records(rebuilt.records)
    names = [row.name for row in steel]
    assert names.count("鋼板") == 1
    hot = next(row for row in steel if row.name == "熱軋鋼捲")
    cold = next(row for row in steel if row.name == "冷軋鋼捲")
    assert hot.coe != plate["coe"]
    assert cold.coe != plate["coe"]


def test_production_active_plate_is_unique_and_coils_do_not_share_it() -> None:
    from carbon_ledger.steel_factor_catalog import load_active_steel_factors

    active = load_active_steel_factors(REPO_ROOT / "data" / "reference")
    plates = active.loc[active["steel_product_type"].astype(str) == "鋼板"]
    assert len(plates) == 1
    assert str(plates.iloc[0]["factor_value"]) == "2.415"
    assert str(plates.iloc[0]["official_valid_from"]) == ""
    assert str(plates.iloc[0]["official_valid_to"]) == ""
    plate = calculate_purchased_steel(
        _plate_activity(),
        registered_factors=active,
    )
    assert plate.calculation_status == STATUS_CALCULATED
    assert plate.calculated_tco2e == 24.15
    hot = calculate_purchased_steel(
        _plate_activity(steel_product_type="熱軋鋼捲"),
        registered_factors=active,
    )
    cold = calculate_purchased_steel(
        _plate_activity(steel_product_type="冷軋鋼捲"),
        registered_factors=active,
    )
    assert hot.calculation_status != STATUS_CALCULATED
    assert cold.calculation_status != STATUS_CALCULATED
    assert hot.calculated_tco2e is None
    assert cold.calculated_tco2e is None

    result = calculate_purchased_steel(
        _plate_activity(steel_product_type="冷軋鋼捲"),
        registered_factors=pd.DataFrame([_approved_plate_factor()]),
    )
    assert result.calculation_status == STATUS_NO_MATCHING_FACTOR
    assert result.calculated_kgco2e is None
    assert result.factor_value != 2.415


def test_display_factor_rows_use_publisher_not_denominator_unit() -> None:
    from carbon_ledger.steel_factor_catalog import display_factor_rows

    rows = display_factor_rows(
        pd.DataFrame(
            [
                {
                    "official_name": "鋼板",
                    "steel_product_type": "鋼板",
                    "factor_value": "2.415",
                    "numerator_unit": "kgCO2e",
                    "denominator_unit": "kg",
                    "official_unit": "公斤(kg)",
                    "publisher": "中國鋼鐵股份有限公司",
                    "official_departmentname": "中國鋼鐵股份有限公司",
                    "factor_year": 2013.0,
                    "announcement_year": 2013.0,
                    "factor_version": "v1",
                    "factor_boundary": "cradle_to_gate",
                    "geography": "TW",
                    "source_url": "https://data.gov.tw/dataset/28176",
                    "approved_for_reporting_from": "2025-01-01",
                    "approved_for_reporting_to": "2025-12-31",
                    "is_secondary_or_proxy": "true",
                    "technology": "",
                    "factor_id": "ef_steel_鋼板_2013_v1",
                }
            ]
        )
    )
    assert len(rows) == 1
    assert rows[0]["declared_unit"] == "中國鋼鐵股份有限公司"
    assert rows[0]["publisher"] == "中國鋼鐵股份有限公司"
    assert rows[0]["declared_unit"] != "kg"
    assert rows[0]["factor_unit"] == "kgCO2e/kg"
    assert "kg" in rows[0]["factor_unit"]
    assert rows[0]["factor_year"] == "2013"
    assert rows[0]["announcement_year"] == "2013"


def test_display_factor_rows_fallback_to_official_departmentname() -> None:
    from carbon_ledger.steel_factor_catalog import display_factor_rows

    rows = display_factor_rows(
        pd.DataFrame(
            [
                {
                    "official_name": "鋼板",
                    "steel_product_type": "鋼板",
                    "factor_value": "2.415",
                    "numerator_unit": "kgCO2e",
                    "denominator_unit": "kg",
                    "publisher": "",
                    "official_departmentname": "中國鋼鐵股份有限公司",
                    "factor_year": "2013",
                }
            ]
        )
    )
    assert rows[0]["declared_unit"] == "中國鋼鐵股份有限公司"
    assert rows[0]["declared_unit"] != "kg"
