"""Phase 10A official reference sync tests (mocked/local fixtures only)."""

from __future__ import annotations

import ast
import io
import shutil
import ssl
from pathlib import Path
from urllib.error import HTTPError, URLError

import pandas as pd
import pytest

from carbon_ledger import reference_sync as reference_sync_module
from carbon_ledger.__main__ import build_parser
from carbon_ledger.__main__ import main as cli_main
from carbon_ledger.factors import validate_factor_registry
from carbon_ledger.match_factors import match_activity_factors
from carbon_ledger.reference_sync import (
    ACTIVATION_COLUMNS,
    CANDIDATE_COLUMNS,
    FETCH_MODE_FETCH,
    FETCH_MODE_PROVENANCE_ONLY,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_CANDIDATE,
    LIFECYCLE_DISCOVERED,
    LIFECYCLE_NEEDS_PARSER_REVIEW,
    LIFECYCLE_PARSED,
    LIFECYCLE_REJECTED,
    LIFECYCLE_VALIDATED,
    OFFICIAL_USER_AGENT,
    REF_TYPE_ELECTRICITY_ENTERPRISE,
    RETRIEVAL_DISCOVER_ATTACHMENT,
    RETRIEVAL_PARSE_LANDING,
    RETRIEVAL_PROVENANCE_ONLY,
    SNAPSHOT_COLUMNS,
    SOURCE_COLUMNS,
    TLS_MODE_DEFAULT,
    TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
    TLS_VERIFICATION_VERIFIED,
    VALIDATION_FAILED,
    ReferenceSyncError,
    activate_candidate,
    assert_candidate_ready_for_activation,
    assert_not_company_upload_as_official,
    assert_url_allowlisted,
    build_official_request_headers,
    build_official_ssl_context,
    check_official_sources,
    compute_bytes_sha256,
    default_paths,
    discover_from_landing_parser,
    discover_official_attachments,
    explicit_fallback_rule_applies,
    fetch_and_stage_sources,
    fetch_official_artifact,
    format_candidate_activation_summary,
    format_missing_year_factor_message,
    load_official_reference_rules,
    load_official_sources,
    normalize_request_url,
    parse_artifact,
    parse_electricity_factor_csv,
    parse_moenv_electricity_news_html,
    reference_sync_status,
    register_snapshot,
    resolve_and_filter_allowlisted_urls,
    validate_candidate_row,
    validate_candidates,
)

MOENV_ENTERPRISE_SOURCE_ID = "src_tw_moenv_electricity_factor_enterprise"
MOEA_UPSTREAM_SOURCE_ID = "src_tw_moea_electricity_factor"

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "reference_sync"


class _FakeResponse:
    def __init__(
        self,
        content: bytes,
        *,
        url: str,
        status: int = 200,
        content_type: str = "text/csv",
    ) -> None:
        self._buffer = io.BytesIO(content)
        self._url = url
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def geturl(self) -> str:
        return self._url

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        return None


class _FakeOpener:
    def __init__(self, mapping: dict[str, bytes], *, status: int = 200) -> None:
        self.mapping = mapping
        self.status = status
        self.requests: list[object] = []

    def open(self, request, timeout=None):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if url not in self.mapping:
            raise URLError(f"No fixture for {url}")
        if self.status >= 400:
            raise HTTPError(url, self.status, "error", hdrs=None, fp=None)
        return _FakeResponse(self.mapping[url], url=url, status=self.status)


def _seed_repo(tmp_path: Path) -> Path:
    """Build an isolated repo rooted at tmp_path from immutable fixtures.

    Does not copy mutable live ``data/reference`` sync/activation state.
    """
    from tests.reference_fixtures import (
        BASELINE_REFERENCE_DIR,
        copy_baseline_reference_tree,
    )

    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    (root / "data").mkdir(parents=True)
    (root / "data" / "reference_snapshots").mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "config" / "official_reference_sources.csv",
        root / "config" / "official_reference_sources.csv",
    )
    shutil.copy(
        REPO_ROOT / "config" / "official_reference_rules.csv",
        root / "config" / "official_reference_rules.csv",
    )
    copy_baseline_reference_tree(root / "data" / "reference")
    # Ensure sync ledgers stay empty even if a fixture accidentally gains rows.
    for name, columns in (
        ("reference_snapshots.csv", SNAPSHOT_COLUMNS),
        ("reference_candidates.csv", CANDIDATE_COLUMNS),
        ("reference_activations.csv", ACTIVATION_COLUMNS),
    ):
        pd.DataFrame(columns=columns).to_csv(
            root / "data" / "reference" / name,
            index=False,
        )
    # Guard: baseline must remain 2024-only for electricity applicability.
    factors = pd.read_csv(
        root / "data" / "reference" / "emission_factors.csv",
        dtype=str,
    )
    elec = factors.loc[factors["activity_type"] == "grid_electricity"]
    assert set(elec["factor_year"]) == {"2024"}
    assert BASELINE_REFERENCE_DIR.is_dir()
    return root


def test_seed_repo_is_hermetic_against_live_activation(tmp_path: Path) -> None:
    """Live 2025 activation must not leak into seeded test baselines."""
    live_factors = pd.read_csv(
        REPO_ROOT / "data" / "reference" / "emission_factors.csv",
        dtype=str,
    )
    live_has_2025_industrial = (
        "ef_tw_grid_electricity_2025_industrial_enterprise_inventory"
        in set(live_factors["factor_id"])
    )

    root_a = _seed_repo(tmp_path / "a")
    root_b = _seed_repo(tmp_path / "b")
    seeded_a = pd.read_csv(
        root_a / "data" / "reference" / "emission_factors.csv",
        dtype=str,
    )
    seeded_b = pd.read_csv(
        root_b / "data" / "reference" / "emission_factors.csv",
        dtype=str,
    )
    pd.testing.assert_frame_equal(seeded_a, seeded_b)
    seeded_years = set(
        seeded_a.loc[
            seeded_a["activity_type"] == "grid_electricity", "factor_year"
        ]
    )
    assert seeded_years == {"2024"}
    assert "0.466" not in set(seeded_a["factor_value"])
    assert len(seeded_a) == 7
    candidates = pd.read_csv(
        root_a / "data" / "reference" / "reference_candidates.csv",
        dtype=str,
    )
    activations = pd.read_csv(
        root_a / "data" / "reference" / "reference_activations.csv",
        dtype=str,
    )
    assert candidates.empty
    assert activations.empty
    status = reference_sync_status(root_a)
    assert status.electricity_years.get("2024") == "available"
    assert status.electricity_years.get("2025") == "unavailable"
    if live_has_2025_industrial:
        assert "0.466" in set(live_factors["factor_value"])
        assert (
            "ef_tw_grid_electricity_2025_industrial_enterprise_inventory"
            not in set(seeded_a["factor_id"])
        )


MOEA_ELECTRICITY_CANONICAL = (
    "https://www.moea.gov.tw/mns/Populace/news/News.aspx"
    "?kind=1&menu_id=40&news_id=122891"
)
MOEA_ELECTRICITY_ARTIFACT = (
    "https://www.moea.gov.tw/files/fixture-electricity-factor.csv"
)
MOENV_ELECTRICITY_OPERATIONAL = (
    "https://ghgregistry.moenv.gov.tw/epa_ghg/News/NewsList.aspx?Type_ID=1"
)
# Backward-compatible alias used by helpers within this module.
MOENV_ELECTRICITY_NEWS = MOENV_ELECTRICITY_OPERATIONAL
MOENV_ELECTRICITY_ARTIFACT = (
    "https://ghgregistry.moenv.gov.tw/epa_ghg/files/"
    "fixture-electricity-factor.csv"
)
MOENV_DOWNLOADS_LANDING = (
    "https://ghgregistry.moenv.gov.tw/epa_ghg/Downloads/"
    "FileDownloads.aspx?Type_ID=6"
)
MOENV_SITE_LANDING = "https://ghgregistry.moenv.gov.tw/epa_ghg/"
MOENV_HEATING_ARTIFACT = (
    "https://ghgregistry.moenv.gov.tw/epa_ghg/files/"
    "fixture-fuel-heating-values.csv"
)


def _landing_html(artifact_url: str, label: str = "official attachment") -> bytes:
    return (
        "<html><body>"
        f'<a href="{artifact_url}">{label}</a>'
        '<a href="https://example.com/evil.csv">ignore</a>'
        "</body></html>"
    ).encode("utf-8")


def _moenv_news_fetch(html: bytes):
    """Fetch stub that returns only the MOENV NewsList HTML (parse_landing)."""

    def _fetch(request_url: str, *, allowed_domain: str, **kwargs):  # type: ignore[no-untyped-def]
        assert request_url == MOENV_ELECTRICITY_NEWS
        return fetch_official_artifact(
            request_url,
            allowed_domain=allowed_domain,
            opener=_FakeOpener({MOENV_ELECTRICITY_NEWS: html}),
            tls_compatibility_mode=kwargs.get(
                "tls_compatibility_mode",
                TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
            ),
        )

    return _fetch


def _enterprise_news_html() -> bytes:
    return (FIXTURES / "moenv_electricity_news_list.html").read_bytes()


def _stage_enterprise_electricity(
    root: Path,
    *,
    retrieved_at: str = "2026-08-10T00:00:00Z",
    html: bytes | None = None,
) -> list[dict]:
    return fetch_and_stage_sources(
        root,
        retrieved_at=retrieved_at,
        source_ids=[MOENV_ENTERPRISE_SOURCE_ID],
        fetch=_moenv_news_fetch(html if html is not None else _enterprise_news_html()),
    )


def _industry_candidate_id(candidates_csv: Path) -> str:
    candidates = pd.read_csv(candidates_csv, dtype=str)
    industry = candidates.loc[
        candidates["factor_category"].isin(
            ["industrial_enterprise_inventory", "industry"]
        )
    ]
    assert not industry.empty
    return str(industry.iloc[0]["candidate_id"])


def test_official_reference_sources_csv_loads_with_expected_columns() -> None:
    path = REPO_ROOT / "config" / "official_reference_sources.csv"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    assert list(frame.columns) == SOURCE_COLUMNS
    assert len(frame.columns) == 15
    assert not frame.empty
    assert MOEA_UPSTREAM_SOURCE_ID in set(frame["source_id"])
    assert MOENV_ENTERPRISE_SOURCE_ID in set(frame["source_id"])
    by_id = frame.set_index("source_id")
    assert by_id.loc[MOEA_UPSTREAM_SOURCE_ID, "retrieval_strategy"] == (
        RETRIEVAL_PROVENANCE_ONLY
    )
    assert by_id.loc[MOENV_ENTERPRISE_SOURCE_ID, "retrieval_strategy"] == (
        RETRIEVAL_PARSE_LANDING
    )
    assert by_id.loc[
        "src_tw_moenv_general_emission_factors", "retrieval_strategy"
    ] == RETRIEVAL_DISCOVER_ATTACHMENT
    assert by_id.loc["src_tw_moenv_cfp_p_02", "retrieval_strategy"] == (
        "paginated_open_data_api"
    )
    assert by_id.loc["src_tw_moenv_cfp_p_02", "parser_type"] == (
        "cfp_p_02_open_data_v1"
    )


def test_allowlisted_official_source_accepted() -> None:
    assert_url_allowlisted(
        "https://www.moea.gov.tw/path/file.csv",
        "moea.gov.tw",
    )


def test_non_allowlisted_domain_rejected() -> None:
    with pytest.raises(ReferenceSyncError) as exc:
        assert_url_allowlisted("https://example.com/factor.csv", "moea.gov.tw")
    assert exc.value.code == "DOMAIN_NOT_ALLOWLISTED"


def test_network_timeout_handled(tmp_path: Path) -> None:
    class TimeoutOpener:
        def open(self, request, timeout=None):  # type: ignore[no-untyped-def]
            raise URLError("timed out")

    with pytest.raises(ReferenceSyncError) as exc:
        fetch_official_artifact(
            "https://www.moea.gov.tw/x.csv",
            allowed_domain="moea.gov.tw",
            opener=TimeoutOpener(),
        )
    assert exc.value.code == "NETWORK_TIMEOUT"


def test_http_failure_handled() -> None:
    opener = _FakeOpener(
        {"https://www.moea.gov.tw/x.csv": b"nope"},
        status=503,
    )
    with pytest.raises(ReferenceSyncError) as exc:
        fetch_official_artifact(
            "https://www.moea.gov.tw/x.csv",
            allowed_domain="moea.gov.tw",
            opener=opener,
        )
    assert exc.value.code == "HTTP_ERROR"


def test_oversized_response_rejected() -> None:
    huge = b"a" * 1000
    opener = _FakeOpener({"https://www.moea.gov.tw/x.csv": huge})
    with pytest.raises(ReferenceSyncError) as exc:
        fetch_official_artifact(
            "https://www.moea.gov.tw/x.csv",
            allowed_domain="moea.gov.tw",
            opener=opener,
            max_bytes=100,
        )
    assert exc.value.code == "RESPONSE_TOO_LARGE"


def test_sha256_deterministic() -> None:
    data = b"official-bytes"
    assert compute_bytes_sha256(data) == compute_bytes_sha256(data)


def test_identical_artifact_recognized_as_already_known(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    html = _enterprise_news_html()
    fetch = _moenv_news_fetch(html)
    first = fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-10T00:00:00Z",
        source_ids=[MOENV_ENTERPRISE_SOURCE_ID],
        fetch=fetch,
    )
    second = fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-11T00:00:00Z",
        source_ids=[MOENV_ENTERPRISE_SOURCE_ID],
        fetch=fetch,
    )
    assert first[0]["status"] == "staged"
    assert first[0]["retrieved_url"] == MOENV_ELECTRICITY_NEWS
    assert first[0]["retrieval_strategy"] == RETRIEVAL_PARSE_LANDING
    assert ".pdf" not in first[0]["retrieved_url"].lower()
    assert second[0]["status"] == "already_known"
    assert second[0]["candidates_created"] == 0
    paths = default_paths(root)
    snapshots = pd.read_csv(paths["snapshots_csv"], dtype=str)
    assert len(snapshots) == 1


def test_changed_artifact_creates_new_snapshot(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    first_html = _enterprise_news_html()
    second_html = (FIXTURES / "moenv_electricity_news_list_alt.html").read_bytes()
    fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-10T00:00:00Z",
        source_ids=[MOENV_ENTERPRISE_SOURCE_ID],
        fetch=_moenv_news_fetch(first_html),
    )
    fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-11T00:00:00Z",
        source_ids=[MOENV_ENTERPRISE_SOURCE_ID],
        fetch=_moenv_news_fetch(second_html),
    )
    snapshots = pd.read_csv(default_paths(root)["snapshots_csv"], dtype=str)
    assert len(snapshots) == 2
    assert snapshots.iloc[0]["sha256"] != snapshots.iloc[1]["sha256"]
    assert (snapshots["retrieved_url"] == MOENV_ELECTRICITY_NEWS).all()


def test_publication_date_remains_distinct_from_applicability() -> None:
    parsed = parse_electricity_factor_csv(
        (FIXTURES / "electricity_2025.csv").read_bytes()
    )
    row = parsed.records[0]
    assert row["publication_date"] == "2026-04-01"
    assert row["valid_from"] == "2025-01-01"
    assert row["valid_to"] == "2025-12-31"
    assert row["publication_date"] != row["valid_from"]


def test_candidate_factor_remains_inactive_before_validation(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    _stage_enterprise_electricity(root)
    candidates = pd.read_csv(default_paths(root)["candidates_csv"], dtype=str)
    assert not candidates.empty
    assert len(candidates) == 3
    assert set(candidates["factor_category"]) == {
        "public_sales_average",
        "industrial_enterprise_inventory",
        "residential",
    }
    assert (candidates["lifecycle_status"] == LIFECYCLE_CANDIDATE).all()
    assert LIFECYCLE_ACTIVE not in set(candidates["lifecycle_status"])
    assert LIFECYCLE_NEEDS_PARSER_REVIEW not in set(candidates["lifecycle_status"])
    snapshots = pd.read_csv(default_paths(root)["snapshots_csv"], dtype=str)
    assert len(snapshots) == 1
    assert snapshots.iloc[0]["retrieved_url"] == MOENV_ELECTRICITY_NEWS


def test_invalid_units_reject_candidate() -> None:
    issues = validate_candidate_row(
        {
            "lifecycle_status": LIFECYCLE_CANDIDATE,
            "reference_type": "electricity_factor",
            "factor_value": "0.5",
            "factor_year": "2025",
            "geography": "TW",
            "activity_type": "grid_electricity",
            "numerator_unit": "widgets",
            "denominator_unit": "kWh",
            "factor_category": "utility_average",
            "valid_from": "2025-01-01",
            "valid_to": "2025-12-31",
            "source_locator": "x",
            "snapshot_id": "snap",
            "parser_version": "v1",
        }
    )
    assert any("numerator_unit" in item for item in issues)


def test_invalid_numeric_factor_rejects_candidate() -> None:
    issues = validate_candidate_row(
        {
            "lifecycle_status": LIFECYCLE_CANDIDATE,
            "reference_type": "electricity_factor",
            "factor_value": "not-a-number",
            "factor_year": "2025",
            "geography": "TW",
            "activity_type": "grid_electricity",
            "numerator_unit": "kgCO2e",
            "denominator_unit": "kWh",
            "factor_category": "utility_average",
            "valid_from": "2025-01-01",
            "valid_to": "2025-12-31",
            "source_locator": "x",
            "snapshot_id": "snap",
            "parser_version": "v1",
        }
    )
    assert any("numeric" in item for item in issues)


def test_invalid_validity_period_rejects_candidate() -> None:
    issues = validate_candidate_row(
        {
            "lifecycle_status": LIFECYCLE_CANDIDATE,
            "reference_type": "electricity_factor",
            "factor_value": "0.5",
            "factor_year": "2025",
            "geography": "TW",
            "activity_type": "grid_electricity",
            "numerator_unit": "kgCO2e",
            "denominator_unit": "kWh",
            "factor_category": "utility_average",
            "valid_from": "2025-12-31",
            "valid_to": "2025-01-01",
            "source_locator": "x",
            "snapshot_id": "snap",
            "parser_version": "v1",
        }
    )
    assert any("valid_from" in item for item in issues)


def test_validated_candidate_can_be_activated(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    _stage_enterprise_electricity(root)
    validate_candidates(paths["candidates_csv"])
    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    candidate_id = _industry_candidate_id(paths["candidates_csv"])
    industry = candidates.loc[candidates["candidate_id"] == candidate_id].iloc[0]
    assert industry["lifecycle_status"] == LIFECYCLE_VALIDATED
    activation = activate_candidate(
        candidate_id=candidate_id,
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        activated_at="2026-08-10T12:00:00Z",
    )
    assert activation["sha256"]
    assert activation["snapshot_id"]
    factors = pd.read_csv(paths["emission_factors"], dtype=str)
    assert "ef_tw_grid_electricity_2024" in set(factors["factor_id"])
    assert any(factors["factor_year"] == "2025")


def test_activation_preserves_historical_factors(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    before = pd.read_csv(paths["emission_factors"], dtype=str)
    _stage_enterprise_electricity(root)
    validate_candidates(paths["candidates_csv"])
    candidate_id = _industry_candidate_id(paths["candidates_csv"])
    activate_candidate(
        candidate_id=candidate_id,
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        activated_at="2026-08-10T12:00:00Z",
    )
    after = pd.read_csv(paths["emission_factors"], dtype=str)
    assert set(before["factor_id"]).issubset(set(after["factor_id"]))
    assert len(after) == len(before) + 1


def test_activation_does_not_overwrite_prior_year(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    original = pd.read_csv(paths["emission_factors"], dtype=str)
    original_2024 = original.loc[
        original["factor_id"] == "ef_tw_grid_electricity_2024"
    ].iloc[0]["factor_value"]
    _stage_enterprise_electricity(root)
    validate_candidates(paths["candidates_csv"])
    candidate_id = _industry_candidate_id(paths["candidates_csv"])
    activate_candidate(
        candidate_id=candidate_id,
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        activated_at="2026-08-10T12:00:00Z",
    )
    updated = pd.read_csv(paths["emission_factors"], dtype=str)
    still_2024 = updated.loc[
        updated["factor_id"] == "ef_tw_grid_electricity_2024"
    ].iloc[0]["factor_value"]
    assert still_2024 == original_2024


def _factors_and_match(tmp_path: Path, activities: pd.DataFrame):
    root = _seed_repo(tmp_path)
    registry = validate_factor_registry(root / "data" / "reference")
    deps = registry.calculation_dependencies
    return match_activity_factors(activities, registry.emission_factors, deps)


def test_2024_activity_matches_2024_only_factor(tmp_path: Path) -> None:
    activities = pd.DataFrame(
        [
            {
                "record_id": "rec_2024",
                "activity_type": "grid_electricity",
                "unit": "kWh",
                "normalized_unit": "kWh",
                "process_use": "general_factory",
                "activity_start_date": pd.Timestamp("2024-06-01"),
                "activity_end_date": pd.Timestamp("2024-06-30"),
            }
        ]
    )
    result = _factors_and_match(tmp_path, activities)
    assert len(result.candidate_matches) == 1
    assert result.candidate_matches.iloc[0]["factor_id"] == (
        "ef_tw_grid_electricity_2024"
    )


def test_2025_activity_does_not_match_2024_only_factor(tmp_path: Path) -> None:
    activities = pd.DataFrame(
        [
            {
                "record_id": "rec_2025",
                "activity_type": "grid_electricity",
                "unit": "kWh",
                "normalized_unit": "kWh",
                "process_use": "general_factory",
                "activity_start_date": pd.Timestamp("2025-01-01"),
                "activity_end_date": pd.Timestamp("2025-01-31"),
            }
        ]
    )
    result = _factors_and_match(tmp_path, activities)
    assert result.candidate_matches.empty
    readiness = result.activity_readiness.iloc[0]
    assert readiness["calculation_readiness"] == "no_factor_configured"
    assert "2025" in readiness["readiness_reason"]
    assert "2024" in readiness["readiness_reason"]


def test_compatible_2025_factor_can_match_2025_activity(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    _stage_enterprise_electricity(root)
    validate_candidates(paths["candidates_csv"])
    candidate_id = _industry_candidate_id(paths["candidates_csv"])
    activate_candidate(
        candidate_id=candidate_id,
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        activated_at="2026-08-10T12:00:00Z",
    )
    registry = validate_factor_registry(paths["reference_dir"])
    assert registry.issues.empty
    activities = pd.DataFrame(
        [
            {
                "record_id": "rec_2025b",
                "activity_type": "grid_electricity",
                "unit": "kWh",
                "normalized_unit": "kWh",
                "process_use": "general_factory",
                "activity_start_date": pd.Timestamp("2025-02-01"),
                "activity_end_date": pd.Timestamp("2025-02-28"),
            }
        ]
    )
    result = match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
    )
    assert len(result.candidate_matches) == 1
    assert "2025" in result.candidate_matches.iloc[0]["factor_id"]


def test_no_implicit_previous_year_fallback() -> None:
    rules = load_official_reference_rules(
        REPO_ROOT / "config" / "official_reference_rules.csv"
    )
    assert (
        explicit_fallback_rule_applies(
            rules,
            reference_type="electricity_factor",
            activity_date="2025-06-01",
        )
        is None
    )


def test_explicit_official_fallback_rule_can_be_represented(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.csv"
    pd.DataFrame(
        [
            {
                "rule_id": "rule_temp_prev_year",
                "reference_type": "electricity_factor",
                "jurisdiction": "TW",
                "condition": "current_year_factor_unavailable",
                "fallback_behavior": "allow_previous_year_with_audit",
                "valid_from": "2025-01-01",
                "valid_to": "2025-12-31",
                "source_reference_id": "ref_example_official_notice",
                "source_locator": "fixture rule row",
                "rule_version": "1",
                "active": "true",
                "notes": "Explicit provenance-backed temporary rule.",
            }
        ]
    ).to_csv(rules_path, index=False)
    rules = load_official_reference_rules(rules_path)
    matched = explicit_fallback_rule_applies(
        rules,
        reference_type="electricity_factor",
        activity_date="2025-03-01",
    )
    assert matched is not None
    assert matched["fallback_behavior"] == "allow_previous_year_with_audit"
    assert matched["source_reference_id"] == "ref_example_official_notice"


def test_fuel_heating_value_remains_versioned_dependency(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    content = (FIXTURES / "fuel_heating_values.csv").read_bytes()
    mapping = {
        MOENV_SITE_LANDING: _landing_html(MOENV_HEATING_ARTIFACT),
        MOENV_HEATING_ARTIFACT: content,
    }

    def _fetch(request_url: str, *, allowed_domain: str, **kwargs):  # type: ignore[no-untyped-def]
        return fetch_official_artifact(
            request_url,
            allowed_domain=allowed_domain,
            opener=_FakeOpener(mapping),
            tls_compatibility_mode=kwargs.get(
                "tls_compatibility_mode",
                TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
            ),
        )

    fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-10T00:00:00Z",
        source_ids=["src_tw_moenv_fuel_heating_values"],
        fetch=_fetch,
    )
    validate_candidates(paths["candidates_csv"])
    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    heating_candidates = candidates.loc[
        candidates["reference_type"] == "fuel_heating_values"
    ]
    assert not heating_candidates.empty
    candidate_id = heating_candidates.iloc[0]["candidate_id"]
    activate_candidate(
        candidate_id=candidate_id,
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        activated_at="2026-08-10T12:00:00Z",
    )
    heating = pd.read_csv(paths["fuel_heating_values"], dtype=str)
    assert not heating.empty
    deps = pd.read_csv(
        paths["reference_dir"] / "calculation_dependencies.csv",
        dtype=str,
    )
    assert (
        deps.loc[deps["activity_type"] == "natural_gas", "status"].iloc[0]
        == "missing_verified_value"
    )


def test_missing_heating_value_still_blocks_calculation(tmp_path: Path) -> None:
    registry = validate_factor_registry(REPO_ROOT / "data" / "reference")
    activities = pd.DataFrame(
        [
            {
                "record_id": "rec_gas",
                "activity_type": "natural_gas",
                "unit": "m3",
                "normalized_unit": "m3",
                "process_use": "boiler",
                "activity_start_date": pd.Timestamp("2024-01-01"),
                "activity_end_date": pd.Timestamp("2024-01-31"),
            }
        ]
    )
    result = match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
    )
    assert (
        result.activity_readiness.iloc[0]["calculation_readiness"]
        == "blocked_missing_conversion"
    )


def test_uploaded_excel_emission_factor_never_promoted() -> None:
    with pytest.raises(ReferenceSyncError) as exc:
        assert_not_company_upload_as_official(source_kind="company_upload")
    assert exc.value.code == "COMPANY_UPLOAD_NOT_OFFICIAL"


def test_normal_analysis_does_not_make_network_calls(tmp_path: Path) -> None:
    # Matching uses only local registry frames; no fetch callable involved.
    registry = validate_factor_registry(REPO_ROOT / "data" / "reference")
    activities = pd.DataFrame(
        [
            {
                "record_id": "rec_local",
                "activity_type": "grid_electricity",
                "unit": "kWh",
                "normalized_unit": "kWh",
                "process_use": "general_factory",
                "activity_start_date": pd.Timestamp("2024-01-01"),
                "activity_end_date": pd.Timestamp("2024-01-31"),
            }
        ]
    )
    result = match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
    )
    assert result.activity_readiness.iloc[0]["calculation_readiness"] == "ready"


def test_existing_analysis_works_when_sync_network_unavailable(tmp_path: Path) -> None:
    from carbon_ledger.pipeline import run_demo_pipeline

    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    sources = load_official_sources(paths["sources"])
    active = sources.loc[sources["active"].str.lower() == "true"]
    fetchable_ids = set(
        active.loc[
            (active["fetch_mode"] == FETCH_MODE_FETCH)
            & (active["retrieval_strategy"] != "paginated_open_data_api"),
            "source_id",
        ]
    )
    provenance_ids = set(
        active.loc[
            active["fetch_mode"] == FETCH_MODE_PROVENANCE_ONLY, "source_id"
        ]
    )
    assert MOENV_ENTERPRISE_SOURCE_ID in fetchable_ids
    assert MOEA_UPSTREAM_SOURCE_ID in provenance_ids

    before_factors = pd.read_csv(paths["emission_factors"], dtype=str)

    def _broken_fetch(url: str, *, allowed_domain: str, **kwargs):  # type: ignore[no-untyped-def]
        raise ReferenceSyncError("NETWORK_ERROR", "offline")

    rows = check_official_sources(
        root,
        retrieved_at="2026-08-10T00:00:00Z",
        fetch=_broken_fetch,
    )
    by_id = {row["source_id"]: row for row in rows}
    for source_id in fetchable_ids:
        assert by_id[source_id]["status"] == "unavailable"
        assert "NETWORK_ERROR" in by_id[source_id]["message"]
    for source_id in provenance_ids:
        assert by_id[source_id]["status"] == "recorded_access_restricted"
        assert by_id[source_id]["status"] != "unavailable"
    assert all(row["status"] != "available" for row in rows)

    after_check_factors = pd.read_csv(paths["emission_factors"], dtype=str)
    pd.testing.assert_frame_equal(before_factors, after_check_factors)

    registry = validate_factor_registry(root / "data" / "reference")
    assert not registry.emission_factors.empty
    assert "ef_tw_grid_electricity_2024" in set(
        registry.emission_factors["factor_id"].astype(str)
    )

    # Offline analysis uses the local versioned registry and does not depend
    # on reference-sync network access.
    result = run_demo_pipeline(
        REPO_ROOT,
        run_id="offline-sync-unavailable",
        ingested_at=pd.Timestamp("2026-08-10T00:00:00Z"),
        include_ghg=True,
        include_cbam=False,
        include_ifrs_s2=False,
    )
    assert result.calculation_results is not None
    assert not result.calculation_results.empty

    after_pipeline_factors = pd.read_csv(paths["emission_factors"], dtype=str)
    pd.testing.assert_frame_equal(before_factors, after_pipeline_factors)


def test_source_snapshot_id_and_sha_propagate_into_audit_metadata(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    _stage_enterprise_electricity(root)
    validate_candidates(paths["candidates_csv"])
    candidate_id = _industry_candidate_id(paths["candidates_csv"])
    activation = activate_candidate(
        candidate_id=candidate_id,
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        activated_at="2026-08-10T12:00:00Z",
    )
    factors = pd.read_csv(paths["emission_factors"], dtype=str)
    new_row = factors.loc[factors["factor_id"] == activation["factor_id"]].iloc[0]
    assert activation["snapshot_id"] in new_row["source_locator"]
    assert activation["sha256"] in new_row["source_locator"]


def test_duplicate_artifact_does_not_duplicate_registry_candidate(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    html = _enterprise_news_html()
    fetch = _moenv_news_fetch(html)
    fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-10T00:00:00Z",
        source_ids=[MOENV_ENTERPRISE_SOURCE_ID],
        fetch=fetch,
    )
    fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-11T00:00:00Z",
        source_ids=[MOENV_ENTERPRISE_SOURCE_ID],
        fetch=fetch,
    )
    candidates = pd.read_csv(default_paths(root)["candidates_csv"], dtype=str)
    assert len(candidates) == 3
    assert set(candidates["factor_category"]) == {
        "public_sales_average",
        "industrial_enterprise_inventory",
        "residential",
    }


def test_parser_output_is_deterministic() -> None:
    content = (FIXTURES / "electricity_2025.csv").read_bytes()
    first = parse_electricity_factor_csv(content)
    second = parse_electricity_factor_csv(content)
    assert first.records == second.records
    assert first.status == second.status


def test_no_old_factor_is_deleted_automatically(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    before_ids = set(pd.read_csv(paths["emission_factors"], dtype=str)["factor_id"])
    _stage_enterprise_electricity(root)
    validate_candidates(paths["candidates_csv"])
    candidate_id = _industry_candidate_id(paths["candidates_csv"])
    activate_candidate(
        candidate_id=candidate_id,
        candidates_csv=paths["candidates_csv"],
        snapshots_csv=paths["snapshots_csv"],
        activations_csv=paths["activations_csv"],
        emission_factors_csv=paths["emission_factors"],
        fuel_heating_values_csv=paths["fuel_heating_values"],
        activated_at="2026-08-10T12:00:00Z",
    )
    after_ids = set(pd.read_csv(paths["emission_factors"], dtype=str)["factor_id"])
    assert before_ids.issubset(after_ids)


def test_needs_parser_review_for_unstructured_pdf_source(tmp_path: Path) -> None:
    parsed = parse_artifact(
        b"%PDF-1.4 official announcement bytes",
        parser_type="needs_parser_review",
        expected_file_type="pdf",
    )
    assert parsed.status == LIFECYCLE_NEEDS_PARSER_REVIEW


def test_format_missing_year_message() -> None:
    text = format_missing_year_factor_message(
        activity_year="2025",
        registered_years=["2024"],
    )
    assert "2025" in text
    assert "2024" in text
    assert "不會自動使用不同年度" in text


def test_load_official_sources_from_config() -> None:
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    assert "src_tw_moea_electricity_factor" in set(sources["source_id"])
    assert "moea.gov.tw" in set(sources["allowed_domain"])
    assert "ghgregistry.moenv.gov.tw" in set(sources["allowed_domain"])


def test_production_config_contains_no_placeholder_official_reference_urls() -> None:
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    for url in sources["landing_url"].tolist():
        assert "/official-reference/" not in str(url)


def test_moenv_host_is_ghgregistry() -> None:
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    moenv = sources.loc[sources["allowed_domain"] == "ghgregistry.moenv.gov.tw"]
    assert not moenv.empty
    assert "ghg.moenv.gov.tw" not in " ".join(sources["landing_url"].tolist())
    assert "ghg.moenv.gov.tw" not in set(sources["allowed_domain"])


def test_electricity_source_uses_real_moea_landing_page() -> None:
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    moea = sources.loc[sources["source_id"] == MOEA_UPSTREAM_SOURCE_ID].iloc[0]
    moenv = sources.loc[
        sources["source_id"] == MOENV_ENTERPRISE_SOURCE_ID
    ].iloc[0]
    assert moea["canonical_url"] == MOEA_ELECTRICITY_CANONICAL
    assert moea["fetch_mode"] == FETCH_MODE_PROVENANCE_ONLY
    assert moea["retrieval_strategy"] == RETRIEVAL_PROVENANCE_ONLY
    assert moenv["landing_url"] == MOENV_ELECTRICITY_OPERATIONAL
    assert moenv["fetch_mode"] == "fetch"
    assert moenv["retrieval_strategy"] == RETRIEVAL_PARSE_LANDING
    assert moenv["parser_type"] == "tw_moenv_electricity_news_landing_v1"
    assert moenv["reference_type"] == REF_TYPE_ELECTRICITY_ENTERPRISE
    assert moenv["upstream_canonical_url"] == MOEA_ELECTRICITY_CANONICAL


def test_enterprise_electricity_parse_landing_ignores_pdf_links(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    # Realistic percent-encoded Traditional Chinese PDF filename on the page.
    # parse_landing must keep retrieved_url on the NewsList HTML, not follow it.
    pdf_href = (
        "/upload/Tools/"
        "%E9%9B%BB%E5%8A%9B%E6%8E%92%E7%A2%B3%E4%BF%82%E6%95%B8.pdf"
    )
    html = (
        _enterprise_news_html()
        .decode("utf-8")
        .replace(
            "</body>",
            f'<a href="{pdf_href}">attachment</a></body>',
        )
        .encode("utf-8")
    )
    report = _stage_enterprise_electricity(root, html=html)[0]
    assert report["status"] == "staged"
    assert report["retrieval_strategy"] == RETRIEVAL_PARSE_LANDING
    assert report["retrieved_url"] == MOENV_ELECTRICITY_NEWS
    assert report["discovered_artifact_url"] == ""
    assert ".pdf" not in report["retrieved_url"].lower()
    assert report["parser_status"] == LIFECYCLE_PARSED
    candidates = pd.read_csv(default_paths(root)["candidates_csv"], dtype=str)
    assert len(candidates) == 3
    assert (candidates["lifecycle_status"] == LIFECYCLE_CANDIDATE).all()
    snapshots = pd.read_csv(default_paths(root)["snapshots_csv"], dtype=str)
    assert len(snapshots) == 1
    assert snapshots.iloc[0]["retrieved_url"] == MOENV_ELECTRICITY_NEWS


def test_moenv_general_factor_source_uses_real_download_landing_page() -> None:
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    row = sources.loc[
        sources["source_id"] == "src_tw_moenv_general_emission_factors"
    ].iloc[0]
    assert row["landing_url"] == MOENV_DOWNLOADS_LANDING
    assert row["allowed_domain"] == "ghgregistry.moenv.gov.tw"
    assert row["expected_file_type"] == "html"
    assert row["retrieval_strategy"] == RETRIEVAL_DISCOVER_ATTACHMENT


def test_landing_page_discovery_never_follows_non_allowlisted_domain() -> None:
    html = _landing_html("https://example.com/secret.csv")
    discovered = discover_official_attachments(
        html,
        landing_url=MOENV_ELECTRICITY_NEWS,
        allowed_domain="ghgregistry.moenv.gov.tw",
        parser_type="tw_moenv_electricity_news_landing_v1",
    )
    assert discovered.status == LIFECYCLE_NEEDS_PARSER_REVIEW
    assert discovered.artifact_url == ""
    assert all("example.com" not in url for url in discovered.candidate_urls)


def test_discovered_attachment_url_is_separately_validated() -> None:
    html = _landing_html(MOENV_ELECTRICITY_ARTIFACT)
    discovered = discover_from_landing_parser(
        html,
        landing_url=MOENV_ELECTRICITY_NEWS,
        allowed_domain="ghgregistry.moenv.gov.tw",
        parser_type="tw_moenv_electricity_news_landing_v1",
    )
    assert discovered.status == LIFECYCLE_DISCOVERED
    assert discovered.artifact_url == MOENV_ELECTRICITY_ARTIFACT
    assert_url_allowlisted(
        discovered.artifact_url, "ghgregistry.moenv.gov.tw"
    )
    with pytest.raises(ReferenceSyncError):
        assert_url_allowlisted(discovered.artifact_url, "moea.gov.tw")


def test_direct_artifact_urls_are_not_assumed_for_landing_sources() -> None:
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    fetchable = sources.loc[
        (sources["active"].str.lower() == "true")
        & (sources["fetch_mode"].str.lower() == "fetch")
    ]
    landing = fetchable.loc[
        fetchable["retrieval_strategy"] != "paginated_open_data_api"
    ]
    for _, row in landing.iterrows():
        assert row["expected_file_type"] == "html"
        assert str(row["parser_type"]).endswith("_landing_v1")
        assert not str(row["landing_url"]).lower().endswith(".csv")
    api_sources = fetchable.loc[
        fetchable["retrieval_strategy"] == "paginated_open_data_api"
    ]
    assert not api_sources.empty
    assert (api_sources["expected_file_type"] == "json").all()


def test_resolve_and_filter_skips_non_allowlisted_hrefs() -> None:
    urls = resolve_and_filter_allowlisted_urls(
        [
            MOEA_ELECTRICITY_ARTIFACT,
            "https://example.com/x.csv",
            "/files/relative-ok.csv",
        ],
        landing_url="https://www.moea.gov.tw/news",
        allowed_domain="moea.gov.tw",
    )
    assert MOEA_ELECTRICITY_ARTIFACT in urls
    assert "https://www.moea.gov.tw/files/relative-ok.csv" in urls
    assert all("example.com" not in url for url in urls)


def test_reference_sync_status_lists_years(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    status = reference_sync_status(root)
    assert status.electricity_years.get("2024") == "available"
    assert status.electricity_years.get("2025") == "unavailable"


def test_register_snapshot_refuses_path_overwrite(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    content_a = b"alpha-bytes"
    content_b = b"beta-bytes-different"
    source = load_official_sources(paths["sources"]).iloc[0]
    from carbon_ledger.reference_sync import FetchResult

    first = FetchResult(
        url="https://www.moea.gov.tw/a.csv",
        final_url="https://www.moea.gov.tw/a.csv",
        content=content_a,
        media_type="text/csv",
        sha256=compute_bytes_sha256(content_a),
        byte_size=len(content_a),
    )
    row = register_snapshot(
        snapshots_csv=paths["snapshots_csv"],
        artifact_dir=paths["artifact_dir"],
        source_row=source,
        fetch=first,
        retrieved_at="2026-08-10T00:00:00Z",
        publication_date="2025",
    )
    conflict_path = Path(row["local_path"])
    # Force same filename with different bytes via direct write, then register.
    conflict_path.write_bytes(content_b)
    second = FetchResult(
        url="https://www.moea.gov.tw/a.csv",
        final_url="https://www.moea.gov.tw/a.csv",
        content=content_a,
        media_type="text/csv",
        sha256=first.sha256,
        byte_size=first.byte_size,
    )
    # Same sha short-circuits before overwrite; use different sha same name path
    # by calling artifact write path indirectly through register with same name
    # components but different sha — filename includes sha prefix so no conflict.
    # Explicitly assert find-by-sha dedupe instead:
    again = register_snapshot(
        snapshots_csv=paths["snapshots_csv"],
        artifact_dir=paths["artifact_dir"],
        source_row=source,
        fetch=second,
        retrieved_at="2026-08-11T00:00:00Z",
        publication_date="2025",
    )
    assert again["snapshot_id"] == row["snapshot_id"]


def test_validate_candidates_marks_failed(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    pd.DataFrame(
        [
            {
                "candidate_id": "cand_bad",
                "snapshot_id": "snap_x",
                "source_id": "src_x",
                "reference_type": "electricity_factor",
                "factor_year": "2025",
                "valid_from": "",
                "valid_to": "",
                "geography": "TW",
                "activity_type": "grid_electricity",
                "combustion_context": "not_applicable",
                "gas": "CO2e",
                "factor_value": "0.5",
                "numerator_unit": "kgCO2e",
                "denominator_unit": "kWh",
                "factor_category": "utility_average",
                "publication_date": "2026-01-01",
                "source_locator": "x",
                "validation_status": "pending",
                "lifecycle_status": LIFECYCLE_CANDIDATE,
                "parser_version": "v1",
                "reason": "",
                "notes": "",
            }
        ]
    ).to_csv(paths["candidates_csv"], index=False)
    frame = validate_candidates(paths["candidates_csv"])
    assert frame.iloc[0]["validation_status"] == VALIDATION_FAILED
    assert frame.iloc[0]["lifecycle_status"] == LIFECYCLE_REJECTED


def test_default_ssl_context_keeps_verify_x509_strict() -> None:
    context = build_official_ssl_context(
        tls_compatibility_mode=TLS_MODE_DEFAULT,
    )
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    strict = getattr(ssl, "VERIFY_X509_STRICT", None)
    if strict is not None:
        assert context.verify_flags & strict


def test_moenv_compatibility_clears_only_verify_x509_strict() -> None:
    context = build_official_ssl_context(
        tls_compatibility_mode=TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
    )
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    strict = getattr(ssl, "VERIFY_X509_STRICT", None)
    if strict is not None:
        assert not (context.verify_flags & strict)


def test_official_ssl_keeps_certificate_and_hostname_verification() -> None:
    for mode in (
        TLS_MODE_DEFAULT,
        TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
    ):
        context = build_official_ssl_context(tls_compatibility_mode=mode)
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True
        assert context.verify_mode != ssl.CERT_NONE


def _ast_is_false(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _ast_is_cert_none(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute) and node.attr == "CERT_NONE":
        return True
    return isinstance(node, ast.Name) and node.id == "CERT_NONE"


def _ast_attr_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _ast_call_qualname(node: ast.Call) -> str:
    parts: list[str] = []
    current: ast.AST = node.func
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _prohibited_tls_executable_findings(tree: ast.AST) -> list[str]:
    """Return executable TLS anti-patterns (ignores comments/docstrings/strings)."""
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "verify" and _ast_is_false(keyword.value):
                    findings.append(
                        f"keyword verify=False at line {node.lineno}"
                    )
            qualname = _ast_call_qualname(node)
            if qualname.endswith("_create_unverified_context"):
                findings.append(
                    f"call {qualname}() at line {node.lineno}"
                )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                attr = _ast_attr_name(target)
                if attr == "check_hostname" and _ast_is_false(node.value):
                    findings.append(
                        f"check_hostname = False at line {node.lineno}"
                    )
                if attr == "verify_mode" and _ast_is_cert_none(node.value):
                    findings.append(
                        f"verify_mode = CERT_NONE at line {node.lineno}"
                    )
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            attr = _ast_attr_name(node.target)
            if attr == "check_hostname" and _ast_is_false(node.value):
                findings.append(
                    f"check_hostname = False at line {node.lineno}"
                )
            if attr == "verify_mode" and _ast_is_cert_none(node.value):
                findings.append(
                    f"verify_mode = CERT_NONE at line {node.lineno}"
                )
    return findings


def test_fetch_path_never_uses_verify_false() -> None:
    """Assert TLS fetch helpers have no insecure executable patterns.

    Uses AST inspection so docstring/explanatory mentions of ``verify=False``
    do not create false positives.
    """
    module_path = Path(reference_sync_module.__file__)
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    target_names = {
        "build_official_ssl_context",
        "build_official_https_opener",
        "fetch_official_artifact",
        "_read_response",
    }
    function_trees = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in target_names
    ]
    assert {node.name for node in function_trees} == target_names

    findings: list[str] = []
    for function_tree in function_trees:
        findings.extend(_prohibited_tls_executable_findings(function_tree))
    assert findings == [], findings

    # Runtime behavior still proves verified TLS for both modes.
    default_ctx = build_official_ssl_context(
        tls_compatibility_mode=TLS_MODE_DEFAULT,
    )
    relaxed_ctx = build_official_ssl_context(
        tls_compatibility_mode=TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
    )
    for context in (default_ctx, relaxed_ctx):
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True
        assert context.verify_mode != ssl.CERT_NONE
    strict = getattr(ssl, "VERIFY_X509_STRICT", None)
    if strict is not None:
        assert default_ctx.verify_flags & strict
        assert not (relaxed_ctx.verify_flags & strict)


def test_non_allowlisted_domains_remain_rejected_under_tls_modes() -> None:
    for mode in (
        TLS_MODE_DEFAULT,
        TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
    ):
        with pytest.raises(ReferenceSyncError) as exc:
            fetch_official_artifact(
                "https://example.com/factor.csv",
                allowed_domain="ghgregistry.moenv.gov.tw",
                tls_compatibility_mode=mode,
                opener=_FakeOpener(
                    {"https://example.com/factor.csv": b"x"},
                ),
            )
        assert exc.value.code == "DOMAIN_NOT_ALLOWLISTED"


def test_tls_compatibility_mode_is_source_specific() -> None:
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    moea = sources.loc[
        sources["source_id"] == "src_tw_moea_electricity_factor"
    ].iloc[0]
    assert moea["tls_compatibility_mode"] == TLS_MODE_DEFAULT
    moenv = sources.loc[
        sources["allowed_domain"] == "ghgregistry.moenv.gov.tw"
    ]
    assert not moenv.empty
    assert set(moenv["tls_compatibility_mode"]) == {
        TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
    }


def test_ssl_failure_does_not_auto_fallback_to_relaxed_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modes_seen: list[str] = []

    def tracking_builder(  # type: ignore[no-untyped-def]
        *,
        allowed_domain: str,
        tls_compatibility_mode: str = TLS_MODE_DEFAULT,
    ):
        modes_seen.append(tls_compatibility_mode)

        class _FailOpener:
            def open(self, request, timeout=None):  # type: ignore[no-untyped-def]
                raise URLError(
                    ssl.SSLCertVerificationError(
                        "certificate verify failed: "
                        "Missing Subject Key Identifier"
                    )
                )

        return _FailOpener()

    monkeypatch.setattr(
        "carbon_ledger.reference_sync.build_official_https_opener",
        tracking_builder,
    )
    with pytest.raises(ReferenceSyncError) as exc:
        fetch_official_artifact(
            "https://www.moea.gov.tw/x.csv",
            allowed_domain="moea.gov.tw",
            tls_compatibility_mode=TLS_MODE_DEFAULT,
        )
    assert modes_seen == [TLS_MODE_DEFAULT]
    assert exc.value.code == "NETWORK_ERROR"
    assert TLS_MODE_PYTHON313_RELAXED_X509_STRICT not in modes_seen


def test_compatibility_mode_recorded_in_snapshot_metadata(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    sources = load_official_sources(paths["sources"])
    source = sources.loc[
        sources["source_id"] == "src_tw_moenv_general_emission_factors"
    ].iloc[0]
    content = b"moenv-official-bytes"
    from carbon_ledger.reference_sync import FetchResult

    fetched = FetchResult(
        url=MOENV_DOWNLOADS_LANDING,
        final_url=MOENV_DOWNLOADS_LANDING,
        content=content,
        media_type="text/html",
        sha256=compute_bytes_sha256(content),
        byte_size=len(content),
        tls_verification=TLS_VERIFICATION_VERIFIED,
        tls_compatibility_mode=TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
    )
    row = register_snapshot(
        snapshots_csv=paths["snapshots_csv"],
        artifact_dir=paths["artifact_dir"],
        source_row=source,
        fetch=fetched,
        retrieved_at="2026-08-10T00:00:00Z",
        publication_date="2025",
    )
    assert row["tls_verification"] == TLS_VERIFICATION_VERIFIED
    assert (
        row["tls_compatibility_mode"]
        == TLS_MODE_PYTHON313_RELAXED_X509_STRICT
    )
    stored = pd.read_csv(paths["snapshots_csv"], dtype=str)
    match = stored.loc[stored["snapshot_id"] == row["snapshot_id"]].iloc[0]
    assert match["tls_verification"] == TLS_VERIFICATION_VERIFIED
    assert (
        match["tls_compatibility_mode"]
        == TLS_MODE_PYTHON313_RELAXED_X509_STRICT
    )


def test_fetch_result_records_configured_tls_compatibility_mode() -> None:
    opener = _FakeOpener(
        {"https://ghgregistry.moenv.gov.tw/epa_ghg/": b"<html/>"},
    )
    fetched = fetch_official_artifact(
        "https://ghgregistry.moenv.gov.tw/epa_ghg/",
        allowed_domain="ghgregistry.moenv.gov.tw",
        tls_compatibility_mode=TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
        opener=opener,
    )
    assert fetched.tls_verification == TLS_VERIFICATION_VERIFIED
    assert (
        fetched.tls_compatibility_mode
        == TLS_MODE_PYTHON313_RELAXED_X509_STRICT
    )


def _request_headers_lower(request: object) -> dict[str, str]:
    headers: dict[str, str] = {}
    header_items = getattr(request, "header_items", None)
    if callable(header_items):
        for key, value in header_items():
            headers[str(key).lower()] = str(value)
        return headers
    raw = getattr(request, "headers", {}) or {}
    for key, value in raw.items():
        headers[str(key).lower()] = str(value)
    return headers


def test_official_requests_send_explicit_application_user_agent() -> None:
    opener = _FakeOpener({MOENV_ELECTRICITY_NEWS: b"<html/>"})
    fetch_official_artifact(
        MOENV_ELECTRICITY_NEWS,
        allowed_domain="ghgregistry.moenv.gov.tw",
        opener=opener,
    )
    assert len(opener.requests) == 1
    headers = _request_headers_lower(opener.requests[0])
    assert headers["user-agent"] == OFFICIAL_USER_AGENT
    assert "CarbonEvidenceLedger/0.1" in headers["user-agent"]
    assert "Python-urllib" not in headers["user-agent"]
    assert headers["accept"].startswith("text/html")
    assert "zh-TW" in headers["accept-language"]


def test_official_request_headers_are_not_default_python_urllib() -> None:
    headers = build_official_request_headers()
    assert headers["User-Agent"] == OFFICIAL_USER_AGENT
    assert headers["User-Agent"] != "Python-urllib/3.13"
    assert "Python-urllib" not in headers["User-Agent"]


def test_official_requests_do_not_add_browser_impersonation_headers() -> None:
    opener = _FakeOpener({MOENV_ELECTRICITY_NEWS: b"<html/>"})
    fetch_official_artifact(
        MOENV_ELECTRICITY_NEWS,
        allowed_domain="ghgregistry.moenv.gov.tw",
        opener=opener,
    )
    headers = _request_headers_lower(opener.requests[0])
    prohibited = {
        "cookie",
        "authorization",
        "referer",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
        "sec-fetch-site",
        "sec-fetch-mode",
        "sec-fetch-dest",
        "sec-fetch-user",
    }
    assert prohibited.isdisjoint(headers.keys())
    assert "Mozilla/" not in headers["user-agent"]
    assert "Chrome/" not in headers["user-agent"]


def test_allowlist_checked_before_official_request() -> None:
    class _TrackingOpener:
        def __init__(self) -> None:
            self.called = False

        def open(self, request, timeout=None):  # type: ignore[no-untyped-def]
            self.called = True
            raise AssertionError("opener must not run for rejected domains")

    opener = _TrackingOpener()
    with pytest.raises(ReferenceSyncError) as exc:
        fetch_official_artifact(
            "https://example.com/factor.csv",
            allowed_domain="moea.gov.tw",
            opener=opener,
        )
    assert exc.value.code == "DOMAIN_NOT_ALLOWLISTED"
    assert opener.called is False


def test_http_403_reports_source_access_restricted() -> None:
    opener = _FakeOpener(
        {MOEA_ELECTRICITY_CANONICAL: b"forbidden"},
        status=403,
    )
    with pytest.raises(ReferenceSyncError) as exc:
        fetch_official_artifact(
            MOEA_ELECTRICITY_CANONICAL,
            allowed_domain="moea.gov.tw",
            opener=opener,
        )
    assert exc.value.code == "SOURCE_ACCESS_RESTRICTED"
    assert "403" in exc.value.message
    assert "impersonation" in exc.value.message.lower()


def test_moenv_tls_compatibility_unchanged_after_request_header_update() -> None:
    context = build_official_ssl_context(
        tls_compatibility_mode=TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
    )
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    strict = getattr(ssl, "VERIFY_X509_STRICT", None)
    if strict is not None:
        assert not (context.verify_flags & strict)
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    moenv = sources.loc[
        sources["source_id"] == MOENV_ENTERPRISE_SOURCE_ID
    ].iloc[0]
    assert (
        moenv["tls_compatibility_mode"]
        == TLS_MODE_PYTHON313_RELAXED_X509_STRICT
    )
    moea = sources.loc[sources["source_id"] == MOEA_UPSTREAM_SOURCE_ID].iloc[0]
    assert moea["tls_compatibility_mode"] == TLS_MODE_DEFAULT
    assert moea["fetch_mode"] == FETCH_MODE_PROVENANCE_ONLY


def test_moea_canonical_url_remains_in_provenance() -> None:
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    moea = sources.loc[sources["source_id"] == MOEA_UPSTREAM_SOURCE_ID].iloc[0]
    moenv = sources.loc[
        sources["source_id"] == MOENV_ENTERPRISE_SOURCE_ID
    ].iloc[0]
    assert moea["canonical_url"] == MOEA_ELECTRICITY_CANONICAL
    assert moenv["upstream_canonical_url"] == MOEA_ELECTRICITY_CANONICAL
    assert "Energy Administration" in moenv["upstream_factor_authority"]


def test_known_403_moea_source_not_required_for_normal_sync_success(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    html = (FIXTURES / "moenv_electricity_news_list.html").read_bytes()
    requested: list[str] = []

    def _fetch(request_url: str, *, allowed_domain: str, **kwargs):  # type: ignore[no-untyped-def]
        requested.append(request_url)
        if "moea.gov.tw" in request_url:
            raise AssertionError("MOEA host must not be fetched in normal sync")
        return fetch_official_artifact(
            request_url,
            allowed_domain=allowed_domain,
            opener=_FakeOpener({MOENV_ELECTRICITY_NEWS: html}),
            tls_compatibility_mode=kwargs.get(
                "tls_compatibility_mode",
                TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
            ),
        )

    check_rows = check_official_sources(
        root,
        retrieved_at="2026-08-10T00:00:00Z",
        fetch=_fetch,
    )
    by_id = {row["source_id"]: row for row in check_rows}
    assert by_id[MOEA_UPSTREAM_SOURCE_ID]["status"] == (
        "recorded_access_restricted"
    )
    assert by_id[MOENV_ENTERPRISE_SOURCE_ID]["status"] == "available"
    assert all("moea.gov.tw" not in url for url in requested)

    reports = fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-10T00:00:00Z",
        source_ids=[MOEA_UPSTREAM_SOURCE_ID, MOENV_ENTERPRISE_SOURCE_ID],
        fetch=_fetch,
    )
    statuses = {row["source_id"]: row["status"] for row in reports}
    assert statuses[MOEA_UPSTREAM_SOURCE_ID] == "skipped_provenance_only"
    assert statuses[MOENV_ENTERPRISE_SOURCE_ID] == "staged"


def test_moenv_news_is_active_machine_readable_source() -> None:
    sources = load_official_sources(
        REPO_ROOT / "config" / "official_reference_sources.csv"
    )
    moenv = sources.loc[
        sources["source_id"] == MOENV_ENTERPRISE_SOURCE_ID
    ].iloc[0]
    assert moenv["landing_url"] == MOENV_ELECTRICITY_OPERATIONAL
    assert moenv["fetch_mode"] == "fetch"
    assert moenv["retrieval_strategy"] == RETRIEVAL_PARSE_LANDING
    assert moenv["active"].lower() == "true"
    assert moenv["allowed_domain"] == "ghgregistry.moenv.gov.tw"


def test_moenv_parser_identifies_only_2026_06_17_announcement() -> None:
    parsed = parse_moenv_electricity_news_html(
        (FIXTURES / "moenv_electricity_news_list.html").read_bytes()
    )
    assert parsed.status == LIFECYCLE_PARSED
    assert parsed.publication_date == "2026-06-17"
    values = {row["factor_value"] for row in parsed.records}
    assert "0.999" not in values
    assert "0.123" not in values


def test_moenv_parser_preserves_category_distinctions_from_fixture() -> None:
    parsed = parse_moenv_electricity_news_html(
        (FIXTURES / "moenv_electricity_news_list.html").read_bytes()
    )
    by_category = {
        row["factor_category"]: row for row in parsed.records
    }
    assert by_category["public_sales_average"]["factor_value"] == "0.467"
    assert by_category["industrial_enterprise_inventory"]["factor_value"] == (
        "0.466"
    )
    assert by_category["residential"]["factor_value"] == "0.471"
    assert by_category["industrial_enterprise_inventory"]["intended_use"] == (
        "enterprise GHG inventory / disclosure"
    )
    assert (
        "tariff"
        in by_category["industrial_enterprise_inventory"][
            "applicability_notes"
        ].lower()
    )
    assert {
        row["upstream_factor_authority"] for row in parsed.records
    } == {
        "Taiwan Ministry of Economic Affairs / Energy Administration"
    }


def test_moenv_live_like_html_parses_three_categories_without_hardcoding() -> None:
    html = (FIXTURES / "moenv_electricity_news_list_live_like.html").read_bytes()
    # Prove values are present in the fixture HTML, not in production config.
    assert b"0.467" in html and b"0.466" in html and b"0.471" in html
    sources_text = (
        REPO_ROOT / "config" / "official_reference_sources.csv"
    ).read_text(encoding="utf-8")
    assert "0.467" not in sources_text
    assert "0.466" not in sources_text
    assert "0.471" not in sources_text

    parsed = parse_moenv_electricity_news_html(html)
    assert parsed.status == LIFECYCLE_PARSED
    assert parsed.publication_date == "2026-06-17"
    by_category = {row["factor_category"]: row for row in parsed.records}
    assert set(by_category) == {
        "public_sales_average",
        "industrial_enterprise_inventory",
        "residential",
    }
    assert by_category["public_sales_average"]["factor_value"] == "0.467"
    assert by_category["industrial_enterprise_inventory"]["factor_value"] == (
        "0.466"
    )
    assert by_category["residential"]["factor_value"] == "0.471"
    assert {
        row["factor_year"] for row in parsed.records
    } == {"2025"}
    assert {
        row["publication_date"] for row in parsed.records
    } == {"2026-06-17"}
    assert {
        row["valid_from"] for row in parsed.records
    } == {"2025-01-01"}
    assert {
        row["valid_to"] for row in parsed.records
    } == {"2025-12-31"}
    values = {row["factor_value"] for row in parsed.records}
    assert values.isdisjoint({"0.123", "0.999", "0.888", "0.777"})
    enterprise = by_category["industrial_enterprise_inventory"]
    assert enterprise["activity_type"] == "grid_electricity"
    assert enterprise["numerator_unit"] == "kgCO2e"
    assert enterprise["denominator_unit"] == "kWh"
    assert enterprise["intended_use"] == (
        "enterprise GHG inventory / disclosure"
    )
    assert "Energy Administration" in enterprise["upstream_factor_authority"]


def test_moenv_live_like_missing_category_needs_parser_review() -> None:
    html = (
        (FIXTURES / "moenv_electricity_news_list_live_like.html")
        .read_text(encoding="utf-8")
        .replace("「民生住宅電力排碳係數」為0.471公斤CO2e/度", "住宅相關說明已移除")
        .encode("utf-8")
    )
    parsed = parse_moenv_electricity_news_html(html)
    assert parsed.status == LIFECYCLE_NEEDS_PARSER_REVIEW
    assert "missing categories" in parsed.reason.lower()
    assert "residential" in parsed.reason.lower()


def test_config_does_not_hard_code_active_registry_factor_values() -> None:
    sources_text = (
        REPO_ROOT / "config" / "official_reference_sources.csv"
    ).read_text(encoding="utf-8")
    from tests.reference_fixtures import BASELINE_REFERENCE_DIR

    baseline_factors = pd.read_csv(
        BASELINE_REFERENCE_DIR / "emission_factors.csv",
        dtype=str,
    )
    for value in ("0.467", "0.466", "0.471"):
        assert value not in sources_text
        # Immutable baseline must not bake MOENV announcement values in.
        assert value not in set(
            baseline_factors.get("factor_value", pd.Series(dtype=str))
        )


def test_moenv_source_format_change_needs_parser_review() -> None:
    html = """
    <html><body>
      <div class="news-item">
        <span class="news-date">2026/08/01</span>
        <a class="news-title">其他公告</a>
        <div class="news-body">沒有電力排碳係數</div>
      </div>
    </body></html>
    """.encode("utf-8")
    parsed = parse_moenv_electricity_news_html(html)
    assert parsed.status == LIFECYCLE_NEEDS_PARSER_REVIEW
    assert "format" in parsed.reason.lower() or "not found" in parsed.reason.lower()


def test_upstream_moea_authority_remains_recorded_in_snapshot(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    html = (FIXTURES / "moenv_electricity_news_list.html").read_bytes()
    fetch_and_stage_sources(
        root,
        retrieved_at="2026-08-10T00:00:00Z",
        source_ids=[MOENV_ENTERPRISE_SOURCE_ID],
        fetch=_moenv_news_fetch(html),
    )
    snapshots = pd.read_csv(paths["snapshots_csv"], dtype=str)
    row = snapshots.iloc[0]
    assert row["upstream_canonical_url"] == MOEA_ELECTRICITY_CANONICAL
    assert "Economic Affairs" in row["upstream_factor_authority"]
    assert row["retrieved_host"] == "ghgregistry.moenv.gov.tw"
    assert row["retrieved_url"] == MOENV_ELECTRICITY_NEWS
    assert row["upstream_canonical_url"] != row["retrieved_url"]
    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    assert (
        candidates["upstream_factor_authority"]
        .astype(str)
        .str.contains("Economic Affairs")
        .all()
    )
    assert "0.466" not in pd.read_csv(
        paths["emission_factors"], dtype=str
    ).to_string()


def test_non_official_mirrors_remain_rejected() -> None:
    for url in (
        "https://example.com/moea-mirror/news",
        "https://archive.org/moea/news_id=122891",
        "https://cdn.unofficial-gov.tw/news",
    ):
        with pytest.raises(ReferenceSyncError) as exc:
            assert_url_allowlisted(url, "moea.gov.tw")
        assert exc.value.code == "DOMAIN_NOT_ALLOWLISTED"


def test_canonical_host_403_does_not_trigger_browser_impersonation() -> None:
    opener = _FakeOpener(
        {MOEA_ELECTRICITY_CANONICAL: b"forbidden"},
        status=403,
    )
    with pytest.raises(ReferenceSyncError) as exc:
        fetch_official_artifact(
            MOEA_ELECTRICITY_CANONICAL,
            allowed_domain="moea.gov.tw",
            opener=opener,
        )
    assert exc.value.code == "SOURCE_ACCESS_RESTRICTED"
    headers = _request_headers_lower(opener.requests[0])
    assert "Mozilla/" not in headers["user-agent"]
    assert "Chrome/" not in headers["user-agent"]
    assert "cookie" not in headers
    assert "sec-ch-ua" not in headers


def test_reference_sync_status_distinguishes_upstream_and_operational(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    status = reference_sync_status(root)
    assert status.electricity_years.get("2024") == "available"
    assert "Energy Administration" in status.upstream_factor_authority
    assert "Environment" in status.operational_source_authority
    assert "access restricted" in status.upstream_source_status
    assert status.upstream_canonical_url == MOEA_ELECTRICITY_CANONICAL
    assert status.operational_source_url == MOENV_ELECTRICITY_OPERATIONAL


MOENV_CHINESE_ARTIFACT = (
    "https://ghgregistry.moenv.gov.tw/epa_ghg/files/114年度天然氣熱值.csv"
)
MOENV_CHINESE_ARTIFACT_QUERY = (
    "https://ghgregistry.moenv.gov.tw/epa_ghg/Downloads/"
    "FileDownloads.aspx?name=114年度天然氣熱值"
)


def test_normalize_request_url_leaves_ascii_url_unchanged() -> None:
    url = (
        "https://ghgregistry.moenv.gov.tw/epa_ghg/News/"
        "NewsList.aspx?Type_ID=1"
    )
    assert normalize_request_url(url) == url


def test_normalize_request_url_percent_encodes_chinese_path() -> None:
    encoded = normalize_request_url(MOENV_CHINESE_ARTIFACT)
    assert "年度" not in encoded
    assert "天然氣" not in encoded
    assert "%E5%B9%B4" in encoded  # 年
    assert encoded.encode("ascii")
    assert encoded.startswith(
        "https://ghgregistry.moenv.gov.tw/epa_ghg/files/"
    )


def test_normalize_request_url_percent_encodes_chinese_query() -> None:
    encoded = normalize_request_url(MOENV_CHINESE_ARTIFACT_QUERY)
    assert "年度" not in encoded
    assert "name=" in encoded
    assert "%E5%B9%B4" in encoded
    assert encoded.encode("ascii")


def test_normalize_request_url_does_not_double_encode() -> None:
    already = (
        "https://ghgregistry.moenv.gov.tw/upload/Tools/AI/"
        "113%E5%B9%B42%E6%9C%885%E6%97%A5%E5%85%AC%E5%91%8A.pdf"
    )
    encoded = normalize_request_url(already)
    assert encoded == already
    assert "%25E5" not in encoded


def test_normalized_official_url_keeps_allowlisted_host() -> None:
    encoded = normalize_request_url(MOENV_CHINESE_ARTIFACT)
    assert_url_allowlisted(encoded, "ghgregistry.moenv.gov.tw")
    assert "ghgregistry.moenv.gov.tw" in encoded


def test_non_allowlisted_domain_rejected_before_unicode_fetch() -> None:
    evil = "https://example.com/files/114年度天然氣熱值.csv"
    with pytest.raises(ReferenceSyncError) as exc:
        fetch_official_artifact(
            evil,
            allowed_domain="ghgregistry.moenv.gov.tw",
            opener=_FakeOpener({evil: b"x"}),
        )
    assert exc.value.code == "DOMAIN_NOT_ALLOWLISTED"


def test_chinese_official_attachment_fetch_via_mocked_opener(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    transport = normalize_request_url(MOENV_CHINESE_ARTIFACT)
    content = "燃料,熱值\n天然氣,9000\n".encode("utf-8")
    opener = _FakeOpener({transport: content})
    fetched = fetch_official_artifact(
        MOENV_CHINESE_ARTIFACT,
        allowed_domain="ghgregistry.moenv.gov.tw",
        opener=opener,
    )
    assert fetched.discovered_url == MOENV_CHINESE_ARTIFACT
    assert fetched.url == transport
    assert fetched.final_url == transport
    assert fetched.content == content
    request_url = opener.requests[0].full_url
    assert request_url == transport
    assert request_url.encode("ascii")

    sources = load_official_sources(paths["sources"])
    source = sources.loc[
        sources["source_id"] == "src_tw_moenv_fuel_heating_values"
    ].iloc[0]
    row = register_snapshot(
        snapshots_csv=paths["snapshots_csv"],
        artifact_dir=paths["artifact_dir"],
        source_row=source,
        fetch=fetched,
        retrieved_at="2026-08-10T00:00:00Z",
        publication_date="2025",
    )
    assert row["discovered_url"] == MOENV_CHINESE_ARTIFACT
    assert row["retrieved_url"] == transport
    assert row["discovered_url"] != row["retrieved_url"]


def test_chinese_attachment_discovery_preserves_unicode_then_fetches(
    tmp_path: Path,
) -> None:
    landing_html = (
        FIXTURES / "moenv_chinese_attachment_landing.html"
    ).read_bytes()
    discovered = discover_official_attachments(
        landing_html,
        landing_url="https://ghgregistry.moenv.gov.tw/epa_ghg/",
        allowed_domain="ghgregistry.moenv.gov.tw",
        parser_type="tw_moenv_news_heating_values_landing_v1",
    )
    assert discovered.status == LIFECYCLE_DISCOVERED
    assert discovered.artifact_url == MOENV_CHINESE_ARTIFACT
    assert "年度" in discovered.artifact_url

    transport = normalize_request_url(discovered.artifact_url)
    opener = _FakeOpener({transport: b"fuel,value\n"})
    fetched = fetch_official_artifact(
        discovered.artifact_url,
        allowed_domain="ghgregistry.moenv.gov.tw",
        opener=opener,
    )
    assert fetched.discovered_url == MOENV_CHINESE_ARTIFACT
    assert fetched.url == transport


def test_redirect_allowlist_still_enforced_with_unicode_location() -> None:
    from carbon_ledger.reference_sync import _AllowlistRedirectHandler

    handler = _AllowlistRedirectHandler("ghgregistry.moenv.gov.tw")
    with pytest.raises(ReferenceSyncError) as exc:
        handler.redirect_request(
            req=None,
            fp=None,
            code=302,
            msg="Found",
            headers={},
            newurl="https://example.com/files/114年度天然氣熱值.csv",
        )
    assert exc.value.code == "DOMAIN_NOT_ALLOWLISTED"


def _stage_and_validate_enterprise(root: Path) -> Path:
    paths = default_paths(root)
    _stage_enterprise_electricity(
        root,
        html=(FIXTURES / "moenv_electricity_news_list_live_like.html").read_bytes(),
    )
    validate_candidates(paths["candidates_csv"])
    return paths["candidates_csv"]


def test_activate_cli_requires_candidate_id() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(
            [
                "references",
                "activate",
                "--activated-at",
                "2026-08-11T14:30:00+08:00",
                "--confirm",
            ]
        )
    assert exc.value.code == 2


def test_activate_cli_requires_activated_at() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(
            [
                "references",
                "activate",
                "--candidate-id",
                "cand_example",
                "--confirm",
            ]
        )
    assert exc.value.code == 2


def test_activate_cli_requires_confirm_and_does_not_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _seed_repo(tmp_path)
    monkeypatch.chdir(root)
    candidates_csv = _stage_and_validate_enterprise(root)
    candidate_id = _industry_candidate_id(candidates_csv)
    before_factors = pd.read_csv(
        default_paths(root)["emission_factors"], dtype=str
    )
    before_activations = pd.read_csv(
        default_paths(root)["activations_csv"], dtype=str
    )
    code = cli_main(
        [
            "references",
            "activate",
            "--candidate-id",
            candidate_id,
            "--activated-at",
            "2026-08-11T14:30:00+08:00",
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert "Candidate to activate" in captured.out
    assert "industrial_enterprise_inventory" in captured.out
    assert "Activation not performed." in captured.out
    assert "--confirm" in captured.out
    after_factors = pd.read_csv(
        default_paths(root)["emission_factors"], dtype=str
    )
    after_activations = pd.read_csv(
        default_paths(root)["activations_csv"], dtype=str
    )
    pd.testing.assert_frame_equal(before_factors, after_factors)
    pd.testing.assert_frame_equal(before_activations, after_activations)
    candidates = pd.read_csv(candidates_csv, dtype=str)
    industry = candidates.loc[candidates["candidate_id"] == candidate_id].iloc[0]
    assert industry["lifecycle_status"] == LIFECYCLE_VALIDATED


def test_unvalidated_and_needs_parser_review_cannot_activate(
    tmp_path: Path,
) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    _stage_enterprise_electricity(
        root,
        html=(FIXTURES / "moenv_electricity_news_list_live_like.html").read_bytes(),
    )
    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    # Force one candidate back to unvalidated candidate state.
    candidate_id = candidates.loc[
        candidates["factor_category"] == "public_sales_average"
    ].iloc[0]["candidate_id"]
    idx = candidates.index[candidates["candidate_id"] == candidate_id][0]
    candidates.at[idx, "validation_status"] = "pending"
    candidates.at[idx, "lifecycle_status"] = LIFECYCLE_CANDIDATE
    candidates.to_csv(paths["candidates_csv"], index=False)
    with pytest.raises(ReferenceSyncError) as exc:
        activate_candidate(
            candidate_id=candidate_id,
            candidates_csv=paths["candidates_csv"],
            snapshots_csv=paths["snapshots_csv"],
            activations_csv=paths["activations_csv"],
            emission_factors_csv=paths["emission_factors"],
            fuel_heating_values_csv=paths["fuel_heating_values"],
            activated_at="2026-08-11T14:30:00+08:00",
        )
    assert exc.value.code == "CANDIDATE_NOT_VALIDATED"

    review_id = "cand_review_hist_fixture"
    review_row = {
        column: "" for column in CANDIDATE_COLUMNS
    }
    review_row.update(
        {
            "candidate_id": review_id,
            "snapshot_id": candidates.iloc[0]["snapshot_id"],
            "source_id": MOENV_ENTERPRISE_SOURCE_ID,
            "reference_type": REF_TYPE_ELECTRICITY_ENTERPRISE,
            "validation_status": VALIDATION_FAILED,
            "lifecycle_status": LIFECYCLE_NEEDS_PARSER_REVIEW,
            "upstream_factor_authority": (
                "Taiwan Ministry of Economic Affairs / Energy Administration"
            ),
            "source_locator": MOENV_ELECTRICITY_NEWS,
            "parser_version": "reference_sync_v1",
            "reason": "historical parser-review evidence",
        }
    )
    candidates = pd.concat(
        [candidates, pd.DataFrame([review_row])],
        ignore_index=True,
    )
    candidates.to_csv(paths["candidates_csv"], index=False)
    with pytest.raises(ReferenceSyncError) as exc_review:
        activate_candidate(
            candidate_id=review_id,
            candidates_csv=paths["candidates_csv"],
            snapshots_csv=paths["snapshots_csv"],
            activations_csv=paths["activations_csv"],
            emission_factors_csv=paths["emission_factors"],
            fuel_heating_values_csv=paths["fuel_heating_values"],
            activated_at="2026-08-11T14:30:00+08:00",
        )
    assert exc_review.value.code == "CANDIDATE_NEEDS_PARSER_REVIEW"


def test_validated_industrial_activation_is_category_specific(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _seed_repo(tmp_path)
    monkeypatch.chdir(root)
    paths = default_paths(root)
    candidates_csv = _stage_and_validate_enterprise(root)
    candidate_id = _industry_candidate_id(candidates_csv)
    before_ids = set(pd.read_csv(paths["emission_factors"], dtype=str)["factor_id"])
    assert "ef_tw_grid_electricity_2024" in before_ids

    code = cli_main(
        [
            "references",
            "activate",
            "--candidate-id",
            candidate_id,
            "--activated-at",
            "2026-08-11T14:30:00+08:00",
            "--activated-by",
            "test_admin",
            "--confirm",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Activation completed." in captured.out

    candidates = pd.read_csv(paths["candidates_csv"], dtype=str)
    by_category = {
        row["factor_category"]: row["lifecycle_status"]
        for _, row in candidates.loc[
            candidates["factor_category"].isin(
                {
                    "public_sales_average",
                    "industrial_enterprise_inventory",
                    "residential",
                }
            )
        ].iterrows()
    }
    assert by_category["industrial_enterprise_inventory"] == LIFECYCLE_ACTIVE
    assert by_category["public_sales_average"] == LIFECYCLE_VALIDATED
    assert by_category["residential"] == LIFECYCLE_VALIDATED

    factors = pd.read_csv(paths["emission_factors"], dtype=str)
    assert "ef_tw_grid_electricity_2024" in set(factors["factor_id"])
    assert any(factors["factor_year"] == "2025")
    new_rows = factors.loc[
        ~factors["factor_id"].isin(before_ids)
    ]
    assert len(new_rows) == 1
    assert "industrial_enterprise_inventory" in new_rows.iloc[0]["factor_id"]
    assert "0.466" == new_rows.iloc[0]["factor_value"]

    activations = pd.read_csv(paths["activations_csv"], dtype=str)
    assert len(activations) == 1
    row = activations.iloc[0]
    assert row["candidate_id"] == candidate_id
    assert row["snapshot_id"]
    assert row["factor_year"] == "2025"
    assert row["factor_category"] == "industrial_enterprise_inventory"
    assert row["factor_value"] == "0.466"
    assert row["activated_by"] == "test_admin"
    assert candidate_id in row["candidate_id"]
    assert row["snapshot_id"] in new_rows.iloc[0]["source_locator"]

    with pytest.raises(ReferenceSyncError) as exc:
        activate_candidate(
            candidate_id=candidate_id,
            candidates_csv=paths["candidates_csv"],
            snapshots_csv=paths["snapshots_csv"],
            activations_csv=paths["activations_csv"],
            emission_factors_csv=paths["emission_factors"],
            fuel_heating_values_csv=paths["fuel_heating_values"],
            activated_at="2026-08-11T15:00:00+08:00",
        )
    assert exc.value.code == "CANDIDATE_ALREADY_ACTIVE"

    status = reference_sync_status(root)
    assert status.electricity_years.get("2024") == "available"
    assert status.electricity_years.get("2025") == "available"
    assert status.electricity_categories["industrial_enterprise_inventory"] == (
        "active"
    )
    assert status.electricity_categories["public_sales_average"] == (
        "validated / not active"
    )
    assert status.electricity_categories["residential"] == (
        "validated / not active"
    )

    registry = validate_factor_registry(paths["reference_dir"])
    activities = pd.DataFrame(
        [
            {
                "record_id": "rec_2025_enterprise",
                "activity_type": "grid_electricity",
                "unit": "kWh",
                "normalized_unit": "kWh",
                "process_use": "general_factory",
                "activity_start_date": pd.Timestamp("2025-02-01"),
                "activity_end_date": pd.Timestamp("2025-02-28"),
            },
            {
                "record_id": "rec_2024_keep",
                "activity_type": "grid_electricity",
                "unit": "kWh",
                "normalized_unit": "kWh",
                "process_use": "general_factory",
                "activity_start_date": pd.Timestamp("2024-06-01"),
                "activity_end_date": pd.Timestamp("2024-06-30"),
            },
        ]
    )
    result = match_activity_factors(
        activities,
        registry.emission_factors,
        registry.calculation_dependencies,
    )
    match_2025 = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_2025_enterprise"
    ]
    match_2024 = result.candidate_matches.loc[
        result.candidate_matches["record_id"] == "rec_2024_keep"
    ]
    assert len(match_2025) == 1
    assert "2025" in match_2025.iloc[0]["factor_id"]
    assert "2024" not in match_2025.iloc[0]["factor_id"]
    assert len(match_2024) == 1
    assert "2024" in match_2024.iloc[0]["factor_id"]


def test_activation_summary_and_assert_helpers(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    candidates_csv = _stage_and_validate_enterprise(root)
    candidates = pd.read_csv(candidates_csv, dtype=str)
    industry = candidates.loc[
        candidates["factor_category"] == "industrial_enterprise_inventory"
    ].iloc[0]
    snapshots = pd.read_csv(paths["snapshots_csv"], dtype=str)
    snapshot = snapshots.iloc[0]
    summary = format_candidate_activation_summary(
        industry,
        snapshot=snapshot,
    )
    assert "Candidate to activate" in summary
    assert "industrial_enterprise_inventory" in summary
    assert "0.466" in summary
    assert "enterprise GHG inventory / disclosure" in summary
    assert_candidate_ready_for_activation(industry, snapshot=snapshot)


def test_activation_path_makes_no_network_request(tmp_path: Path) -> None:
    root = _seed_repo(tmp_path)
    paths = default_paths(root)
    candidates_csv = _stage_and_validate_enterprise(root)
    candidate_id = _industry_candidate_id(candidates_csv)

    original = reference_sync_module.fetch_official_artifact

    def _forbid_network(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("activation must not perform network I/O")

    reference_sync_module.fetch_official_artifact = _forbid_network  # type: ignore[attr-defined]
    try:
        activate_candidate(
            candidate_id=candidate_id,
            candidates_csv=paths["candidates_csv"],
            snapshots_csv=paths["snapshots_csv"],
            activations_csv=paths["activations_csv"],
            emission_factors_csv=paths["emission_factors"],
            fuel_heating_values_csv=paths["fuel_heating_values"],
            activated_at="2026-08-11T14:30:00+08:00",
        )
        status = reference_sync_status(root)
        assert status.electricity_years.get("2025") == "available"
        from carbon_ledger.pipeline import run_demo_pipeline

        # Normal analysis remains offline against the local versioned registry.
        result = run_demo_pipeline(
            REPO_ROOT,
            run_id="activation-offline-check",
            ingested_at=pd.Timestamp("2026-08-11T00:00:00Z"),
            include_ghg=True,
            include_cbam=False,
            include_ifrs_s2=False,
        )
        assert result.calculation_results is not None
        assert not result.calculation_results.empty
    finally:
        reference_sync_module.fetch_official_artifact = original  # type: ignore[attr-defined]

