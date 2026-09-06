"""Official factor-update v1: parse, candidate, activate, year selection."""

from __future__ import annotations

import io
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from carbon_ledger.calculate import calculate_activity_emissions
from carbon_ledger.match_factors import match_activity_factors
from carbon_ledger.official_table_parse import (
    parse_moenv_ods_fuel_emission_factors,
    parse_moenv_ods_gwp,
    steel_average_data_not_configured_result,
)
from carbon_ledger.reference_sync import (
    CANDIDATE_COLUMNS,
    LIFECYCLE_CANDIDATE,
    LIFECYCLE_NEEDS_PARSER_REVIEW,
    LIFECYCLE_PARSED,
    LIFECYCLE_VALIDATED,
    REF_TYPE_FUEL_EF,
    REF_TYPE_GWP,
    REF_TYPE_STEEL,
    SNAPSHOT_COLUMNS,
    VALIDATION_FAILED,
    VALIDATION_PASSED,
    FetchResult,
    ReferenceSyncError,
    activate_candidate,
    compute_bytes_sha256,
    default_paths,
    fetch_and_stage_sources,
    parse_artifact,
    propose_official_factor_update,
    upsert_candidates_from_parse,
    validate_candidate_row,
    validate_candidates,
)
from tests.test_reference_sync import _seed_repo

REPO_ROOT = Path(__file__).resolve().parents[1]
ODS_PATH = (
    REPO_ROOT
    / "data"
    / "reference_snapshots"
    / "src_tw_moenv_general_emission_factors__unknown-pub__085fe962e158.ods"
)
MOENV_ODS_URL = (
    "https://ghgregistry.moenv.gov.tw/upload/Tools/AI/"
    "113-emission-factors.ods"
)
WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "official-factor-update.yml"
)


def _ods_bytes() -> bytes:
    assert ODS_PATH.is_file()
    return ODS_PATH.read_bytes()


def _fetch_result(url: str, content: bytes, media_type: str) -> FetchResult:
    return FetchResult(
        url=url,
        final_url=url,
        content=content,
        media_type=media_type,
        sha256=compute_bytes_sha256(content),
        byte_size=len(content),
    )


def _ods_landing_fetch(ods: bytes):
    html = (
        "<html><body>"
        f'<a href="{MOENV_ODS_URL}">113年排放係數 ODS</a>'
        "</body></html>"
    ).encode("utf-8")

    def _fetch(url: str, *, allowed_domain: str, **kwargs):  # type: ignore[no-untyped-def]
        if "FileDownloads" in url:
            return _fetch_result(url, html, "text/html")
        return _fetch_result(
            url,
            ods,
            "application/vnd.oasis.opendocument.spreadsheet",
        )

    return _fetch


def _assign_reviewer_applicability(
    candidates_csv: Path,
    candidate_id: str,
    *,
    valid_from: str,
    valid_to: str = "",
) -> None:
    """Supply an official period that is not the announcement date."""
    frame = pd.read_csv(candidates_csv, dtype=str)
    mask = frame["candidate_id"] == candidate_id
    frame.loc[mask, "valid_from"] = valid_from
    frame.loc[mask, "valid_to"] = valid_to
    frame.loc[mask, "lifecycle_status"] = LIFECYCLE_CANDIDATE
    frame.to_csv(candidates_csv, index=False)


def _blank(value: object) -> bool:
    return value is None or pd.isna(value) or str(value).strip() in {"", "nan", "NaN"}


def _write_snapshot(paths: dict[str, Path], *, sha256: str) -> dict[str, str]:
    row = {column: "" for column in SNAPSHOT_COLUMNS}
    row.update(
        {
            "snapshot_id": f"snap_test_{sha256[:12]}",
            "source_id": "src_tw_moenv_general_emission_factors",
            "authority": (
                "Taiwan Ministry of Environment / Climate Change Administration"
            ),
            "reference_type": "general_emission_factors",
            "retrieved_url": MOENV_ODS_URL,
            "retrieved_host": "ghgregistry.moenv.gov.tw",
            "retrieved_at": "2026-08-10T00:00:00Z",
            "publication_date": "2024-02-05",
            "file_name": "official.ods",
            "media_type": "application/vnd.oasis.opendocument.spreadsheet",
            "sha256": sha256,
            "byte_size": "1",
            "parser_version": "reference_sync_v1",
            "local_path": "data/reference_snapshots/official.ods",
            "status": "downloaded",
            "upstream_factor_authority": (
                "Taiwan Ministry of Environment / Climate Change Administration"
            ),
        }
    )
    pd.DataFrame([row]).to_csv(paths["snapshots_csv"], index=False)
    return row


def _source_row(reference_type: str) -> dict[str, str]:
    return {
        "source_id": (
            "src_tw_moenv_gwp_reference"
            if reference_type == REF_TYPE_GWP
            else "src_tw_moenv_general_emission_factors"
        ),
        "reference_type": reference_type,
        "authority": (
            "Taiwan Ministry of Environment / Climate Change Administration"
        ),
        "upstream_factor_authority": (
            "Taiwan Ministry of Environment / Climate Change Administration"
        ),
    }


def _replace_ods_text(content: bytes, old: str, new: str) -> bytes:
    archive = ZipFile(io.BytesIO(content))
    xml = archive.read("content.xml").decode("utf-8").replace(old, new)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as out:
        for info in archive.infolist():
            data = (
                xml.encode("utf-8")
                if info.filename == "content.xml"
                else archive.read(info.filename)
            )
            out.writestr(info, data)
    return buffer.getvalue()


def _electricity_factor(
    *,
    factor_id: str,
    year: str,
    value: str,
    valid_from: str,
    valid_to: str,
    notes: str = "",
) -> dict[str, str]:
    return {
        "factor_id": factor_id,
        "activity_type": "grid_electricity",
        "combustion_context": "not_applicable",
        "gas": "CO2e",
        "factor_value": value,
        "numerator_unit": "kgCO2e",
        "denominator_unit": "kWh",
        "geography": "TW",
        "factor_year": year,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "source_reference_id": f"ref_{factor_id}",
        "source_locator": f"test {factor_id}",
        "factor_status": "ready",
        "required_conversion": "not_required",
        "notes": notes,
    }


def _electricity_activity(record_id: str, start: str, end: str) -> dict[str, object]:
    return {
        "record_id": record_id,
        "activity_type": "grid_electricity",
        "unit": "kWh",
        "normalized_unit": "kWh",
        "process_use": "general_factory",
        "activity_start_date": start,
        "activity_end_date": end,
        "activity_value": "10",
    }


def test_official_ods_parses_fuel_and_gwp_deterministically() -> None:
    content = _ods_bytes()
    fuel = parse_moenv_ods_fuel_emission_factors(content)
    gwp = parse_moenv_ods_gwp(content)
    assert fuel.status == LIFECYCLE_PARSED
    assert gwp.status == LIFECYCLE_PARSED
    ng_co2 = next(
        row
        for row in fuel.records
        if row["activity_type"] == "natural_gas" and row["gas"] == "CO2"
    )
    assert ng_co2["factor_value"] == "56100"
    assert ng_co2["candidate_type"] == REF_TYPE_FUEL_EF
    diesel_co2 = next(
        row
        for row in fuel.records
        if row["activity_type"] == "diesel" and row["gas"] == "CO2"
    )
    assert diesel_co2["factor_value"] == "74100"
    ch4 = next(
        row
        for row in gwp.records
        if row["gas"] == "CH4" and row["factor_context"] == "fuel_combustion"
    )
    assert ch4["factor_value"] == "28"
    assert ch4["assessment_basis"] == "IPCC AR5 100-year GWP"
    assert gwp.publication_date == "2024-02-05"
    assert ch4["factor_year"] == "2024"
    assert ch4["reporting_year"] == ""
    assert ch4["valid_from"] == ""
    assert ch4["valid_to"] == ""
    assert ch4["publication_date"] == "2024-02-05"
    assert ng_co2["factor_year"] == "2024"
    assert ng_co2["reporting_year"] == ""
    assert ng_co2["valid_from"] == ""
    assert diesel_co2["factor_year"] == "2024"
    assert "2024_announcement" not in ng_co2["factor_year"]


def test_publication_date_is_not_copied_to_valid_from() -> None:
    parsed = parse_moenv_ods_gwp(_ods_bytes())
    assert parsed.status == LIFECYCLE_PARSED
    assert parsed.publication_date == "2024-02-05"
    assert parsed.records
    for row in parsed.records:
        assert row["publication_date"] == "2024-02-05"
        assert row["valid_from"] == ""
        assert row["valid_from"] != row["publication_date"]
        assert row["reporting_year"] == ""
        assert row["factor_year"] == "2024"


def test_missing_announcement_date_fails_closed() -> None:
    mutated = _replace_ods_text(_ods_bytes(), "中華民國113年2月5日", "公告日期未載明")
    gwp = parse_moenv_ods_gwp(mutated)
    fuel = parse_moenv_ods_fuel_emission_factors(mutated)
    assert gwp.status == LIFECYCLE_NEEDS_PARSER_REVIEW
    assert fuel.status == LIFECYCLE_NEEDS_PARSER_REVIEW
    assert gwp.records == []
    assert fuel.records == []
    assert "manual_review_required" in gwp.reason
    assert "manual_review_required" in fuel.reason
    assert gwp.publication_date == ""
    assert fuel.publication_date == ""


def test_future_announcement_does_not_hardcode_factor_year_2024() -> None:
    mutated = _replace_ods_text(
        _ods_bytes(), "中華民國113年2月5日", "中華民國114年3月1日"
    )
    gwp = parse_moenv_ods_gwp(mutated)
    fuel = parse_moenv_ods_fuel_emission_factors(mutated)
    assert gwp.status == LIFECYCLE_PARSED
    assert fuel.status == LIFECYCLE_PARSED
    assert gwp.publication_date == "2025-03-01"
    assert fuel.publication_date == "2025-03-01"
    assert {row["factor_year"] for row in gwp.records} == {"2025"}
    assert {row["factor_year"] for row in fuel.records} == {"2025"}
    assert all(row["reporting_year"] == "" for row in gwp.records)
    assert all(row["valid_from"] == "" for row in gwp.records)
    assert all(row["valid_from"] == "" for row in fuel.records)
    assert "2024" not in {row["factor_year"] for row in gwp.records}


def test_parsed_candidates_cannot_auto_activate_without_official_period(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    parsed = parse_moenv_ods_gwp(_ods_bytes())
    snapshot = _write_snapshot(paths, sha256="noperiodgwp")
    created = upsert_candidates_from_parse(
        candidates_csv=paths["candidates_csv"],
        snapshot=snapshot,
        source_row=_source_row(REF_TYPE_GWP),
        parsed=parsed,
    )
    assert created
    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    hfc_id = str(candidates.loc[candidates["gas"] == "HFC-32"].iloc[0]["candidate_id"])
    validate_candidates(
        paths["candidates_csv"],
        candidate_ids=[hfc_id],
        official_sources_csv=paths["sources"],
    )
    chosen = pd.read_csv(paths["candidates_csv"], dtype=str)
    chosen = chosen.loc[chosen["candidate_id"] == hfc_id].iloc[0]
    assert _blank(chosen["valid_from"])
    assert chosen["publication_date"] == "2024-02-05"
    assert chosen["validation_status"] == VALIDATION_FAILED
    assert "publication_date is not a substitute" in chosen["validation_messages"]
    assert "manual_review_required" in chosen["validation_messages"]
    with pytest.raises(ReferenceSyncError) as exc:
        activate_candidate(
            candidate_id=hfc_id,
            candidates_csv=paths["candidates_csv"],
            snapshots_csv=paths["snapshots_csv"],
            activations_csv=paths["activations_csv"],
            emission_factors_csv=paths["emission_factors"],
            fuel_heating_values_csv=paths["fuel_heating_values"],
            gwp_values_csv=paths["gwp_values"],
            activated_at="2026-08-12T00:00:00Z",
        )
    assert exc.value.code in {
        "CANDIDATE_NOT_VALIDATED",
        "CANDIDATE_MISSING_VALIDITY",
        "CANDIDATE_NOT_ACTIVATABLE",
    }


def test_header_change_fails_closed() -> None:
    mutated = _replace_ods_text(_ods_bytes(), "溫暖化潛勢", "其他欄位")
    parsed = parse_moenv_ods_gwp(mutated)
    assert parsed.status == LIFECYCLE_NEEDS_PARSER_REVIEW
    assert parsed.records == []
    fuel_mutated = _replace_ods_text(
        _ods_bytes(), "燃料單位熱值之排放係數", "不明表頭"
    )
    fuel = parse_moenv_ods_fuel_emission_factors(fuel_mutated)
    assert fuel.status == LIFECYCLE_NEEDS_PARSER_REVIEW
    assert fuel.records == []


def test_same_hash_is_noop(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    ods = _ods_bytes()
    fetch = _ods_landing_fetch(ods)
    first = fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-10T00:00:00Z",
        source_ids=["src_tw_moenv_general_emission_factors"],
        fetch=fetch,
    )
    second = fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-11T00:00:00Z",
        source_ids=["src_tw_moenv_general_emission_factors"],
        fetch=fetch,
    )
    assert first[0]["status"] == "staged"
    assert first[0]["candidates_created"] > 0
    assert second[0]["status"] == "already_known"
    assert second[0]["candidates_created"] == 0
    candidates = pd.read_csv(default_paths(root)["candidates_csv"], dtype=str)
    assert candidates["candidate_id"].is_unique


def test_gwp_candidate_validates_and_activates_append_only(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    parsed = parse_moenv_ods_gwp(_ods_bytes())
    snapshot = _write_snapshot(paths, sha256="abc123deadbeef")
    created = upsert_candidates_from_parse(
        candidates_csv=paths["candidates_csv"],
        snapshot=snapshot,
        source_row=_source_row(REF_TYPE_GWP),
        parsed=parsed,
    )
    assert created
    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    hfc = candidates.loc[candidates["gas"] == "HFC-32"].iloc[0]
    hfc_id = str(hfc["candidate_id"])
    gwp_before = pd.read_csv(paths["gwp_values"], dtype=str)
    gwp_before = gwp_before.loc[gwp_before["gas"] != "HFC-32"]
    gwp_before.to_csv(paths["gwp_values"], index=False)
    remaining = set(gwp_before["gwp_id"])
    validate_candidates(
        paths["candidates_csv"],
        candidate_ids=[hfc_id],
        official_sources_csv=paths["sources"],
    )
    row = pd.read_csv(paths["candidates_csv"], dtype=str)
    chosen = row.loc[row["candidate_id"] == hfc_id].iloc[0]
    assert _blank(chosen["valid_from"])
    assert chosen["publication_date"] == "2024-02-05"
    assert chosen["validation_status"] == VALIDATION_FAILED
    _assign_reviewer_applicability(
        paths["candidates_csv"],
        hfc_id,
        valid_from="2024-01-01",
        valid_to="2024-12-31",
    )
    validate_candidates(
        paths["candidates_csv"],
        candidate_ids=[hfc_id],
        official_sources_csv=paths["sources"],
    )
    row = pd.read_csv(paths["candidates_csv"], dtype=str)
    chosen = row.loc[row["candidate_id"] == hfc_id].iloc[0]
    assert chosen["validation_status"] == VALIDATION_PASSED
    assert chosen["lifecycle_status"] == LIFECYCLE_VALIDATED
    assert chosen["valid_from"] != chosen["publication_date"]
    activation = activate_candidate(
        candidate_id=hfc_id,
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        gwp_values_csv=paths["gwp_values"],
        activated_at="2026-08-12T00:00:00Z",
        activated_by="tester",
    )
    after = pd.read_csv(paths["gwp_values"], dtype=str)
    assert remaining.issubset(set(after["gwp_id"]))
    assert activation["factor_id"] in set(after["gwp_id"])
    assert remaining
    audit = pd.read_csv(paths["activations_csv"], dtype=str)
    assert activation["candidate_id"] in set(audit["candidate_id"])
    assert audit.iloc[0]["activated_by"] == "tester"
    assert audit.iloc[0]["sha256"]
    assert audit.iloc[0]["new_content"]
    assert str(audit.iloc[0]["source_snapshot_path"]).startswith(
        "data/reference_snapshots/"
    )


def test_fuel_factor_candidate_validates_and_preserves_history(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    parsed = parse_moenv_ods_fuel_emission_factors(_ods_bytes())
    snapshot = _write_snapshot(paths, sha256="feedfacecafe")
    upsert_candidates_from_parse(
        candidates_csv=paths["candidates_csv"],
        snapshot=snapshot,
        source_row=_source_row(REF_TYPE_FUEL_EF),
        parsed=parsed,
    )
    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    ng = candidates.loc[
        (candidates["activity_type"] == "natural_gas")
        & (candidates["gas"] == "CO2")
    ].iloc[0]
    candidate_id = str(ng["candidate_id"])
    factors_before = pd.read_csv(paths["emission_factors"], dtype=str)
    factors_before = factors_before.loc[
        factors_before["factor_id"] != "ef_tw_natural_gas_stationary_co2_2024"
    ]
    factors_before.to_csv(paths["emission_factors"], index=False)
    historical = set(factors_before["factor_id"])
    validate_candidates(
        paths["candidates_csv"],
        candidate_ids=[candidate_id],
        official_sources_csv=paths["sources"],
    )
    row = pd.read_csv(paths["candidates_csv"], dtype=str)
    chosen = row.loc[row["candidate_id"] == candidate_id].iloc[0]
    assert _blank(chosen["valid_from"])
    assert chosen["factor_year"] == "2024"
    assert chosen["validation_status"] == VALIDATION_FAILED
    _assign_reviewer_applicability(
        paths["candidates_csv"],
        candidate_id,
        valid_from="2024-01-01",
        valid_to="2024-12-31",
    )
    validate_candidates(
        paths["candidates_csv"],
        candidate_ids=[candidate_id],
        official_sources_csv=paths["sources"],
    )
    activate_candidate(
        candidate_id=candidate_id,
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        activated_at="2026-08-12T00:00:00Z",
        activated_by="tester",
    )
    after = pd.read_csv(paths["emission_factors"], dtype=str)
    assert historical.issubset(set(after["factor_id"]))
    assert "ef_tw_diesel_mobile_co2_2024" in set(after["factor_id"])
    audit = pd.read_csv(paths["activations_csv"], dtype=str)
    assert not audit.empty
    assert audit.iloc[0]["registry_table"] == "emission_factors"


def test_unknown_source_is_rejected(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    row = {column: "" for column in CANDIDATE_COLUMNS}
    row.update(
        {
            "candidate_id": "cand_unknown_blog",
            "snapshot_id": "snap_x",
            "source_id": "src_random_blog",
            "reference_type": "electricity_factor",
            "factor_year": "2025",
            "valid_from": "2025-01-01",
            "valid_to": "2025-12-31",
            "geography": "TW",
            "activity_type": "grid_electricity",
            "gas": "CO2e",
            "factor_value": "0.4",
            "numerator_unit": "kgCO2e",
            "denominator_unit": "kWh",
            "factor_category": "industrial_enterprise_inventory",
            "source_locator": "https://example.com/blog",
            "source_sha256": "abc",
            "lifecycle_status": LIFECYCLE_CANDIDATE,
            "parser_version": "v1",
        }
    )
    pd.DataFrame([row]).to_csv(paths["candidates_csv"], index=False)
    frame = validate_candidates(
        paths["candidates_csv"],
        official_sources_csv=paths["sources"],
    )
    assert frame.iloc[0]["validation_status"] == "failed"
    issues = validate_candidate_row({**row, "source_id": ""})
    assert any("source_id" in item for item in issues)


def test_steel_average_data_cannot_auto_activate(tmp_path: Path) -> None:
    parsed = steel_average_data_not_configured_result()
    assert parsed.status == LIFECYCLE_NEEDS_PARSER_REVIEW
    assert parsed.records == []
    issues = validate_candidate_row(
        {
            "lifecycle_status": LIFECYCLE_CANDIDATE,
            "reference_type": REF_TYPE_STEEL,
            "candidate_type": REF_TYPE_STEEL,
            "factor_value": "1.8",
            "factor_year": "2025",
            "geography": "TW",
            "activity_type": "purchased_steel",
            "source_id": "src_invented",
            "source_locator": "invented",
            "snapshot_id": "snap",
            "parser_version": "v1",
        }
    )
    assert any("steel" in item.lower() for item in issues)
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    snapshot = _write_snapshot(paths, sha256="steelhash")
    upsert_candidates_from_parse(
        candidates_csv=paths["candidates_csv"],
        snapshot=snapshot,
        source_row={
            "source_id": "src_tw_moenv_general_emission_factors",
            "reference_type": REF_TYPE_STEEL,
        },
        parsed=parsed,
    )
    with pytest.raises(ReferenceSyncError) as exc:
        activate_candidate(
            candidate_id=pd.read_csv(
                paths["candidates_csv"], dtype=str
            ).iloc[0]["candidate_id"],
            candidates_csv=paths["candidates_csv"],
            snapshots_csv=paths["snapshots_csv"],
            activations_csv=paths["activations_csv"],
            emission_factors_csv=paths["emission_factors"],
            fuel_heating_values_csv=paths["fuel_heating_values"],
            activated_at="2026-08-12T00:00:00Z",
        )
    assert exc.value.code in {
        "CANDIDATE_NEEDS_PARSER_REVIEW",
        "STEEL_FACTOR_NOT_CONFIGURED",
        "STEEL_FACTOR_NOT_AUTO_ACTIVATED",
        "CANDIDATE_NOT_VALIDATED",
    }


def test_year_selection_and_fail_closed_ambiguity() -> None:
    factors = pd.DataFrame(
        [
            _electricity_factor(
                factor_id="ef_2024",
                year="2024",
                value="0.474",
                valid_from="2024-01-01",
                valid_to="2024-12-31",
            ),
            _electricity_factor(
                factor_id="ef_2025",
                year="2025",
                value="0.466",
                valid_from="2025-01-01",
                valid_to="2025-12-31",
                notes="category=industrial_enterprise_inventory",
            ),
            _electricity_factor(
                factor_id="ef_2025_recalc_published_2026",
                year="2025",
                value="0.460",
                valid_from="2025-01-01",
                valid_to="2025-12-31",
                notes=(
                    "category=industrial_enterprise_inventory; "
                    "publication_date=2026-03-01"
                ),
            ),
        ]
    )
    deps = pd.DataFrame(columns=["dependency_id"])
    act_2024 = pd.DataFrame(
        [_electricity_activity("a2024", "2024-06-01", "2024-06-30")]
    )
    match_2024 = match_activity_factors(act_2024, factors.iloc[[0, 1]], deps)
    assert set(match_2024.candidate_matches["factor_id"]) == {"ef_2024"}
    assert match_2024.activity_readiness.iloc[0]["calculation_readiness"] == "ready"

    act_2025 = pd.DataFrame(
        [_electricity_activity("a2025", "2025-06-01", "2025-06-30")]
    )
    match_2025 = match_activity_factors(act_2025, factors.iloc[[0, 1]], deps)
    assert set(match_2025.candidate_matches["factor_id"]) == {"ef_2025"}

    published_2026 = factors.iloc[[0, 2]]
    match_recalc = match_activity_factors(act_2025, published_2026, deps)
    assert set(match_recalc.candidate_matches["factor_id"]) == {
        "ef_2025_recalc_published_2026"
    }

    match_2024_vs_2025 = match_activity_factors(
        act_2024, factors.iloc[[0, 1]], deps
    )
    assert "ef_2025" not in set(match_2024_vs_2025.candidate_matches["factor_id"])

    ambiguous = match_activity_factors(act_2025, factors.iloc[[1, 2]], deps)
    assert (
        ambiguous.activity_readiness.iloc[0]["calculation_readiness"]
        == "blocked_ambiguous_factor"
    )
    calculated = calculate_activity_emissions(
        pd.DataFrame(
            [
                {
                    "record_id": "a2025",
                    "normalized_value": "10",
                    "normalized_unit": "kWh",
                    "normalization_status": "normalized",
                }
            ]
        ),
        ambiguous.candidate_matches,
        ambiguous.activity_readiness,
        factors,
    )
    assert calculated.iloc[0]["calculation_status"] == "blocked_ambiguous_factor"

    calc_2024 = calculate_activity_emissions(
        pd.DataFrame(
            [
                {
                    "record_id": "a2024",
                    "normalized_value": "10",
                    "normalized_unit": "kWh",
                    "normalization_status": "normalized",
                }
            ]
        ),
        match_2024.candidate_matches,
        match_2024.activity_readiness,
        factors.iloc[[0, 1]],
    )
    assert calc_2024.iloc[0]["factor_id"] == "ef_2024"
    assert calc_2024.iloc[0]["calculation_status"] == "calculated"


def test_audit_trace_preserves_activated_factor_id(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    parsed = parse_artifact(
        _ods_bytes(),
        parser_type="tw_moenv_gwp_ods_v1",
        expected_file_type="ods",
    )
    snapshot = _write_snapshot(paths, sha256="auditgwp")
    upsert_candidates_from_parse(
        candidates_csv=paths["candidates_csv"],
        snapshot=snapshot,
        source_row=_source_row(REF_TYPE_GWP),
        parsed=parsed,
    )
    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    n2o = candidates.loc[
        (candidates["gas"] == "N2O")
        & (candidates["factor_context"] == "fuel_combustion")
    ].iloc[0]
    gwp = pd.read_csv(paths["gwp_values"], dtype=str)
    gwp = gwp.loc[gwp["gas"] != "N2O"]
    gwp.to_csv(paths["gwp_values"], index=False)
    validate_candidates(
        paths["candidates_csv"],
        candidate_ids=[str(n2o["candidate_id"])],
        official_sources_csv=paths["sources"],
    )
    _assign_reviewer_applicability(
        paths["candidates_csv"],
        str(n2o["candidate_id"]),
        valid_from="2024-01-01",
        valid_to="2024-12-31",
    )
    validate_candidates(
        paths["candidates_csv"],
        candidate_ids=[str(n2o["candidate_id"])],
        official_sources_csv=paths["sources"],
    )
    activation = activate_candidate(
        candidate_id=str(n2o["candidate_id"]),
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        gwp_values_csv=paths["gwp_values"],
        activated_at="2026-08-12T00:00:00Z",
        activated_by="auditor",
    )
    audit = pd.read_csv(paths["activations_csv"], dtype=str)
    assert audit.iloc[0]["factor_id"] == activation["factor_id"]
    payload = json.loads(audit.iloc[0]["new_content"])
    assert payload["gwp_id"] == activation["factor_id"]


def test_propose_update_writes_review_bundle(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    parsed = parse_moenv_ods_gwp(_ods_bytes())
    snapshot = _write_snapshot(paths, sha256="proposehash")
    upsert_candidates_from_parse(
        candidates_csv=paths["candidates_csv"],
        snapshot=snapshot,
        source_row=_source_row(REF_TYPE_GWP),
        parsed=parsed,
    )
    gwp = pd.read_csv(paths["gwp_values"], dtype=str)
    gwp = gwp.loc[gwp["gas"] != "HFC-125"]
    gwp.to_csv(paths["gwp_values"], index=False)
    proposal = propose_official_factor_update(
        root, retrieved_at="2026-08-12T00:00:00Z"
    )
    assert Path(proposal["proposal_json"]).is_file()
    assert Path(proposal["proposal_md"]).is_file()
    markdown = Path(proposal["proposal_md"]).read_text(encoding="utf-8")
    assert "SHA-256" in markdown
    assert "approval" in markdown.lower()
    body = json.loads(Path(proposal["proposal_json"]).read_text(encoding="utf-8"))
    assert "items" in body
    assert "cannot_activate" in body


def test_workflow_never_auto_merges() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "workflow_dispatch" in text
    assert "cron:" in text
    assert "3.13" in text
    assert "auto-merged" in text
    assert "gh pr merge" not in text
    assert "human approval" in text.lower()
    assert "contents: write" in text
    assert "propose-update" in text
    assert "--base \"${{ github.event.repository.default_branch }}\"" in text
    assert "github.ref_name" not in text


def test_workflow_dispatch_pr_base_is_default_branch_not_ref_name() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    create_block = text.split("gh pr create", 1)[1]
    assert "${{ github.event.repository.default_branch }}" in create_block
    assert "github.ref_name" not in create_block
    assert "--base \"${{ github.event.repository.default_branch }}\"" in create_block
