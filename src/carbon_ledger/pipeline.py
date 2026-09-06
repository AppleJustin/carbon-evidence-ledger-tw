"""Reproducible end-to-end pipeline orchestration.

Phase 7C wires existing tested modules into one structured demo run. It does
not add carbon-accounting or regulatory rules.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from carbon_ledger.calculate import calculate_activity_emissions
from carbon_ledger.cbam import OUTPUT_COLUMNS as CBAM_OUTPUT_COLUMNS
from carbon_ledger.cbam import (
    evaluate_cbam,
    load_cbam_product_scenario,
    load_cbam_references,
    load_cbam_rules,
)
from carbon_ledger.factors import validate_factor_registry
from carbon_ledger.ifrs_s2 import OUTPUT_COLUMNS as IFRS_S2_OUTPUT_COLUMNS
from carbon_ledger.ifrs_s2 import (
    evaluate_ifrs_s2_readiness,
    load_ifrs_s2_references,
    load_ifrs_s2_reporting_context,
    load_ifrs_s2_rules,
)
from carbon_ledger.ingest import REJECTION_COLUMNS, ingest_evidence
from carbon_ledger.match_factors import match_activity_factors
from carbon_ledger.normalize import normalize_activity_records
from carbon_ledger.qa import build_core_qa_issues, load_qa_rules
from carbon_ledger.rules import OUTPUT_COLUMNS as GHG_OUTPUT_COLUMNS
from carbon_ledger.rules import (
    evaluate_ghg_protocol,
    load_ghg_protocol_references,
    load_ghg_protocol_rules,
)

ProgressCallback = Callable[[str, int, int, str], None]
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@dataclass
class PipelineRunResult:
    """Complete structured result of one demo pipeline run."""

    run_id: str
    ingested_at: pd.Timestamp
    include_ghg: bool
    include_cbam: bool
    include_ifrs_s2: bool
    source_documents_accepted: pd.DataFrame
    source_documents_rejected: pd.DataFrame
    activity_records_accepted: pd.DataFrame
    activity_records_rejected: pd.DataFrame
    normalized_records: pd.DataFrame
    candidate_matches: pd.DataFrame
    activity_readiness: pd.DataFrame
    calculation_results: pd.DataFrame
    core_qa_issues: pd.DataFrame
    ghg_evaluations: pd.DataFrame
    cbam_evaluations: pd.DataFrame
    ifrs_s2_evaluations: pd.DataFrame


def validate_run_id(run_id: str) -> str:
    """Validate and return a safe run_id or raise ValueError."""
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be a non-empty string.")
    cleaned = run_id.strip()
    if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
        raise ValueError(
            "run_id must not contain path separators or path traversal."
        )
    if not RUN_ID_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "run_id must be 1-64 characters using only letters, numbers, "
            "underscore, hyphen, or period."
        )
    return cleaned


def _empty_rejection_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=REJECTION_COLUMNS)


def _emit_progress(
    callback: ProgressCallback | None,
    stage: str,
    completed: int,
    total: int,
    message: str,
) -> None:
    if callback is None:
        return
    callback(stage, completed, total, message)


def _run_validated_activity_pipeline(
    *,
    repo_root: Path,
    run_id: str,
    ingested_at: pd.Timestamp,
    accepted_documents: pd.DataFrame,
    rejected_documents: pd.DataFrame,
    accepted_activities: pd.DataFrame,
    rejected_activities: pd.DataFrame,
    include_ghg: bool,
    include_cbam: bool,
    include_ifrs_s2: bool,
    progress_callback: ProgressCallback | None = None,
) -> PipelineRunResult:
    """Run normalize → match → calculate → QA → optional adapters."""
    validated_run_id = validate_run_id(run_id)
    if not isinstance(ingested_at, pd.Timestamp):
        raise ValueError("ingested_at must be a pandas.Timestamp.")
    if accepted_activities is None or accepted_activities.empty:
        raise ValueError("accepted_activities must contain at least one row.")

    root = Path(repo_root)
    reference_directory = root / "data" / "reference"
    config_directory = root / "config"

    run_ghg = bool(include_ghg or include_ifrs_s2)
    run_cbam = bool(include_cbam)
    run_ifrs = bool(include_ifrs_s2)
    total_stages = 6

    _emit_progress(
        progress_callback, "ingest", 1, total_stages, "reading activity data"
    )

    _emit_progress(
        progress_callback, "normalize", 2, total_stages, "normalizing units"
    )
    normalized = normalize_activity_records(accepted_activities)

    registry = validate_factor_registry(reference_directory)
    from carbon_ledger.steel_factor_catalog import merge_steel_factors

    emission_factors = merge_steel_factors(
        registry.emission_factors, reference_directory
    )
    activities_for_matching = accepted_activities.merge(
        normalized[["record_id", "normalized_unit", "normalization_status"]],
        on="record_id",
        how="left",
    )
    _emit_progress(
        progress_callback, "factors", 3, total_stages, "matching emission factors"
    )
    matching = match_activity_factors(
        activities_for_matching,
        emission_factors,
        registry.calculation_dependencies,
        heating_values=registry.fuel_heating_values,
    )
    _emit_progress(
        progress_callback, "calculate", 4, total_stages, "calculating emissions"
    )
    calculations = calculate_activity_emissions(
        normalized,
        matching.candidate_matches,
        matching.activity_readiness,
        emission_factors,
        heating_values=registry.fuel_heating_values,
        gwp_values=registry.gwp_values,
        engineering_conversions=registry.engineering_conversions,
        activity_records=accepted_activities,
    )

    ingestion_rejections = pd.concat(
        [rejected_documents, rejected_activities],
        ignore_index=True,
    )
    _emit_progress(
        progress_callback, "qa", 5, total_stages, "building quality issues"
    )
    core_qa_issues = build_core_qa_issues(
        accepted_activities,
        ingestion_rejections,
        normalized,
        matching.activity_readiness,
        calculations,
        load_qa_rules(config_directory),
    )

    _emit_progress(
        progress_callback, "rules", 6, total_stages, "evaluating framework rules"
    )
    if run_ghg:
        ghg_evaluations = evaluate_ghg_protocol(
            accepted_activities,
            load_ghg_protocol_rules(config_directory),
            load_ghg_protocol_references(reference_directory),
        )
    else:
        ghg_evaluations = pd.DataFrame(columns=GHG_OUTPUT_COLUMNS)

    if run_cbam:
        cbam_evaluations = evaluate_cbam(
            accepted_activities,
            load_cbam_rules(config_directory),
            load_cbam_references(reference_directory),
            load_cbam_product_scenario(config_directory),
        )
    else:
        cbam_evaluations = pd.DataFrame(columns=CBAM_OUTPUT_COLUMNS)

    if run_ifrs:
        ifrs_s2_evaluations = evaluate_ifrs_s2_readiness(
            accepted_activities,
            calculations,
            ghg_evaluations,
            load_ifrs_s2_rules(config_directory),
            load_ifrs_s2_references(reference_directory),
            load_ifrs_s2_reporting_context(config_directory),
        )
    else:
        ifrs_s2_evaluations = pd.DataFrame(columns=IFRS_S2_OUTPUT_COLUMNS)

    return PipelineRunResult(
        run_id=validated_run_id,
        ingested_at=pd.Timestamp(ingested_at),
        include_ghg=run_ghg,
        include_cbam=run_cbam,
        include_ifrs_s2=run_ifrs,
        source_documents_accepted=accepted_documents.copy(),
        source_documents_rejected=rejected_documents.copy(),
        activity_records_accepted=accepted_activities.copy(),
        activity_records_rejected=rejected_activities.copy(),
        normalized_records=normalized,
        candidate_matches=matching.candidate_matches,
        activity_readiness=matching.activity_readiness,
        calculation_results=calculations,
        core_qa_issues=core_qa_issues,
        ghg_evaluations=ghg_evaluations,
        cbam_evaluations=cbam_evaluations,
        ifrs_s2_evaluations=ifrs_s2_evaluations,
    )


def run_demo_pipeline(
    repo_root: Path,
    *,
    run_id: str,
    ingested_at: pd.Timestamp,
    include_ghg: bool = False,
    include_cbam: bool = False,
    include_ifrs_s2: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> PipelineRunResult:
    """Run the reproducible demo pipeline without writing files.

    Optional adapters never alter the framework-neutral core outputs.
    """
    validated_run_id = validate_run_id(run_id)
    if not isinstance(ingested_at, pd.Timestamp):
        raise ValueError("ingested_at must be a pandas.Timestamp.")

    root = Path(repo_root)
    raw_directory = root / "data" / "raw"

    if progress_callback is not None:
        progress_callback("ingest", 0, 6, "reading source evidence")
    ingestion = ingest_evidence(
        raw_directory=raw_directory,
        ingestion_run_id=f"ingestion_{validated_run_id}",
        ingested_at=pd.Timestamp(ingested_at),
    )
    return _run_validated_activity_pipeline(
        repo_root=root,
        run_id=validated_run_id,
        ingested_at=pd.Timestamp(ingested_at),
        accepted_documents=ingestion.source_documents.accepted,
        rejected_documents=ingestion.source_documents.rejected,
        accepted_activities=ingestion.activity_records.accepted,
        rejected_activities=ingestion.activity_records.rejected,
        include_ghg=include_ghg,
        include_cbam=include_cbam,
        include_ifrs_s2=include_ifrs_s2,
        progress_callback=progress_callback,
    )


def run_uploaded_pipeline(
    repo_root: Path,
    *,
    run_id: str,
    ingested_at: pd.Timestamp,
    source_documents: pd.DataFrame,
    accepted_activities: pd.DataFrame,
    include_ghg: bool = False,
    include_cbam: bool = False,
    include_ifrs_s2: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> PipelineRunResult:
    """Run the validated analysis pipeline on confirmed uploaded activities.

    Uses the live factor registry under data/reference. Does not load
    bundled synthetic demo rows from data/raw.
    """
    if source_documents is None or source_documents.empty:
        raise ValueError("source_documents must contain at least one row.")
    return _run_validated_activity_pipeline(
        repo_root=Path(repo_root),
        run_id=run_id,
        ingested_at=ingested_at,
        accepted_documents=source_documents,
        rejected_documents=_empty_rejection_frame(),
        accepted_activities=accepted_activities,
        rejected_activities=_empty_rejection_frame(),
        include_ghg=include_ghg,
        include_cbam=include_cbam,
        include_ifrs_s2=include_ifrs_s2,
        progress_callback=progress_callback,
    )
