"""Command-line entry point for the carbon_ledger package.

Examples:

    python -m carbon_ledger --version

    python -m carbon_ledger run-demo --run-id portfolio_demo --all-adapters
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from carbon_ledger import __version__
from carbon_ledger.export import export_run_bundle
from carbon_ledger.pipeline import run_demo_pipeline, validate_run_id

DEFAULT_INGESTED_AT = "2024-02-01T00:00:00Z"


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="carbon_ledger",
        description=(
            "Carbon Evidence Ledger for Taiwanese Exporters — "
            "reproducible evidence pipeline and export runner."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
        help="Print the package version and exit.",
    )

    subparsers = parser.add_subparsers(dest="command")
    run_demo = subparsers.add_parser(
        "run-demo",
        help="Run the reproducible synthetic demo pipeline and export a bundle.",
    )
    run_demo.add_argument(
        "--run-id",
        required=True,
        help="Safe run identifier used for ingestion and the output folder.",
    )
    run_demo.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Default: outputs/<run-id>",
    )
    run_demo.add_argument(
        "--ingested-at",
        default=DEFAULT_INGESTED_AT,
        help=(
            "Explicit ingestion timestamp for reproducibility. "
            f"Default: {DEFAULT_INGESTED_AT}"
        ),
    )
    run_demo.add_argument(
        "--include-ghg",
        action="store_true",
        help="Enable the optional GHG Protocol adapter.",
    )
    run_demo.add_argument(
        "--include-cbam",
        action="store_true",
        help="Enable the optional EU CBAM adapter.",
    )
    run_demo.add_argument(
        "--include-ifrs-s2",
        action="store_true",
        help="Enable the optional IFRS S2 readiness adapter.",
    )
    run_demo.add_argument(
        "--all-adapters",
        action="store_true",
        help="Enable GHG Protocol, EU CBAM, and IFRS S2 adapters.",
    )

    references = subparsers.add_parser(
        "references",
        help=(
            "Official reference sync maintenance "
            "(check / fetch / validate / activate / propose-update / status). "
            "Does not run carbon calculations and does not auto-activate."
        ),
    )
    ref_sub = references.add_subparsers(dest="references_command")
    ref_sub.add_parser(
        "check",
        help="Check allowlisted official sources without activating factors.",
    )
    fetch_parser = ref_sub.add_parser(
        "fetch",
        help="Download official artifacts, hash/version, and stage candidates.",
    )
    fetch_parser.add_argument(
        "--retrieved-at",
        default="2026-08-10T00:00:00Z",
        help="Explicit retrieval timestamp for reproducibility.",
    )
    validate_parser = ref_sub.add_parser(
        "validate",
        help="Validate staged reference candidates (no activation).",
    )
    validate_parser.add_argument(
        "--candidate-id",
        action="append",
        default=None,
        help="Optional candidate_id to validate (repeatable).",
    )
    activate_parser = ref_sub.add_parser(
        "activate",
        help=(
            "Explicitly activate ONE validated candidate into the local "
            "versioned registry. Never activates all candidates."
        ),
    )
    activate_parser.add_argument(
        "--candidate-id",
        required=True,
        help="Exact candidate_id to activate (required).",
    )
    activate_parser.add_argument(
        "--activated-at",
        required=True,
        help=(
            "Explicit activation timestamp for reproducibility "
            "(required; no hidden datetime.now())."
        ),
    )
    activate_parser.add_argument(
        "--activated-by",
        default="cli_admin",
        help="Actor recorded in the activation audit ledger.",
    )
    activate_parser.add_argument(
        "--confirm",
        action="store_true",
        help=(
            "Required confirmation flag. Without --confirm the command only "
            "prints the pre-activation summary and does not write."
        ),
    )
    steel_activate = ref_sub.add_parser(
        "activate-steel",
        help=(
            "Explicitly activate ONE reviewed purchased-steel candidate. "
            "Official CFP_P_02 fields stay as-is; review metadata is required. "
            "Never copies test fixtures into the active catalog."
        ),
    )
    steel_activate.add_argument("--candidate-id", required=True)
    steel_activate.add_argument("--reviewer", required=True)
    steel_activate.add_argument("--approved-at", required=True)
    steel_activate.add_argument("--factor-version", required=True)
    steel_activate.add_argument(
        "--lifecycle-boundary",
        required=True,
        help="Internally reviewed boundary. Must be cradle_to_gate.",
    )
    steel_activate.add_argument(
        "--geography",
        required=True,
        help="Internally reviewed geography. Not stated by CFP_P_02.",
    )
    steel_activate.add_argument(
        "--approved-for-reporting-from",
        required=True,
        help="Internal reporting applicability start. Not government valid_from.",
    )
    steel_activate.add_argument(
        "--approved-for-reporting-to",
        default="",
        help="Internal reporting applicability end; blank is open-ended.",
    )
    steel_activate.add_argument(
        "--rationale",
        required=True,
        help="Why this official row is applicable after review.",
    )
    steel_activate.add_argument("--confirm", action="store_true")
    propose_parser = ref_sub.add_parser(
        "propose-update",
        help=(
            "Write a machine-readable JSON and Markdown review bundle. "
            "Never activates coefficients and never merges a pull request."
        ),
    )
    propose_parser.add_argument(
        "--retrieved-at",
        default="",
        help="Optional timestamp recorded in the review bundle.",
    )
    ref_sub.add_parser(
        "status",
        help="Show local official-reference registry status.",
    )
    return parser


def _parse_ingested_at(raw_value: str) -> pd.Timestamp:
    text = str(raw_value).strip()
    if not text:
        raise ValueError("ingested-at must be a non-empty timestamp.")
    parsed = pd.to_datetime(text, utc=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid ingested-at value: {raw_value!r}")
    # Store as timezone-naive UTC wall time for stable CSV/JSON text.
    return pd.Timestamp(parsed.tz_convert(None))


def _print_success(
    *,
    run_id: str,
    accepted_activities: int,
    calculated_activities: int,
    core_qa_issues: int,
    ghg_rows: int,
    cbam_rows: int,
    ifrs_rows: int,
    bundle_dir: Path,
    manifest_path: Path,
) -> None:
    print("Carbon Evidence Ledger demo completed.")
    print()
    print(f"Run ID: {run_id}")
    print(f"Accepted activities: {accepted_activities}")
    print(f"Calculated activities: {calculated_activities}")
    print(f"Core QA issues: {core_qa_issues}")
    print(f"GHG rows: {ghg_rows}")
    print(f"CBAM rows: {cbam_rows}")
    print(f"IFRS S2 rows: {ifrs_rows}")
    print(f"Bundle: {bundle_dir}")
    print(f"Manifest: {manifest_path}")


def _run_demo_command(args: argparse.Namespace) -> int:
    try:
        run_id = validate_run_id(args.run_id)
        ingested_at = _parse_ingested_at(args.ingested_at)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    include_ghg = bool(args.include_ghg or args.all_adapters)
    include_cbam = bool(args.include_cbam or args.all_adapters)
    include_ifrs_s2 = bool(args.include_ifrs_s2 or args.all_adapters)

    repo_root = Path.cwd()
    output_dir = (
        Path(args.output_dir)
        if args.output_dir is not None
        else repo_root / "outputs" / run_id
    )

    try:
        result = run_demo_pipeline(
            repo_root,
            run_id=run_id,
            ingested_at=ingested_at,
            include_ghg=include_ghg,
            include_cbam=include_cbam,
            include_ifrs_s2=include_ifrs_s2,
        )
        manifest_path = export_run_bundle(result, output_dir)
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    calculated = 0
    if (
        not result.calculation_results.empty
        and "calculation_status" in result.calculation_results.columns
    ):
        calculated = int(
            (result.calculation_results["calculation_status"] == "calculated").sum()
        )

    _print_success(
        run_id=result.run_id,
        accepted_activities=len(result.activity_records_accepted),
        calculated_activities=calculated,
        core_qa_issues=len(result.core_qa_issues),
        ghg_rows=len(result.ghg_evaluations),
        cbam_rows=len(result.cbam_evaluations),
        ifrs_rows=len(result.ifrs_s2_evaluations),
        bundle_dir=output_dir,
        manifest_path=manifest_path,
    )
    return 0


def _run_references_command(args: argparse.Namespace) -> int:
    from carbon_ledger.reference_sync import (
        CANDIDATE_COLUMNS,
        SNAPSHOT_COLUMNS,
        ReferenceSyncError,
        activate_candidate,
        check_official_sources,
        default_paths,
        fetch_and_stage_sources,
        format_candidate_activation_summary,
        propose_official_factor_update,
        reference_sync_status,
        validate_candidates,
    )

    repo_root = Path.cwd()
    command = getattr(args, "references_command", None)
    if command == "check":
        rows = check_official_sources(
            repo_root,
            retrieved_at="2026-08-10T00:00:00Z",
        )
        for row in rows:
            print(
                f"{row['source_id']}: {row['status']} — {row['message']}"
            )
        return 0
    if command == "fetch":
        reports = fetch_and_stage_sources(
            repo_root,
            retrieved_at=str(args.retrieved_at),
        )
        failed = False
        for report in reports:
            print(
                f"{report['source_id']}: {report['status']} "
                f"(candidates={report.get('candidates_created', 0)})"
            )
            if report.get("change_report"):
                print(report["change_report"])
                print()
            if report.get("review_reason"):
                print(f"review_reason: {report['review_reason']}")
            if report.get("status") in {
                "parse_failed",
                "credential_required",
                "schema_changed",
            }:
                failed = True
        return 1 if failed else 0
    if command == "validate":
        paths = default_paths(repo_root)
        frame = validate_candidates(
            paths["candidates_csv"],
            candidate_ids=args.candidate_id,
            official_sources_csv=paths["sources"],
        )
        if frame.empty:
            print("No reference candidates found.")
            return 0
        for _, row in frame.iterrows():
            print(
                f"{row['candidate_id']}: {row['validation_status']} / "
                f"{row['lifecycle_status']} — {row['reason']}"
            )
        return 0
    if command == "activate":
        paths = default_paths(repo_root)
        candidate_id = str(args.candidate_id).strip()
        activated_at = str(args.activated_at).strip()
        if not candidate_id:
            print("Error: --candidate-id is required.", file=sys.stderr)
            return 2
        if not activated_at:
            print("Error: --activated-at is required.", file=sys.stderr)
            return 2

        candidates = pd.read_csv(
            paths["candidates_csv"],
            dtype=str,
            keep_default_na=False,
        )
        for column in CANDIDATE_COLUMNS:
            if column not in candidates.columns:
                candidates[column] = ""
        match = candidates.loc[candidates["candidate_id"] == candidate_id]
        if match.empty:
            print(
                f"Error: Unknown candidate_id {candidate_id!r}.",
                file=sys.stderr,
            )
            return 2
        candidate = match.iloc[0]
        snapshots = pd.read_csv(
            paths["snapshots_csv"],
            dtype=str,
            keep_default_na=False,
        )
        for column in SNAPSHOT_COLUMNS:
            if column not in snapshots.columns:
                snapshots[column] = ""
        snap_match = snapshots.loc[
            snapshots["snapshot_id"] == str(candidate.get("snapshot_id", ""))
        ]
        snapshot = snap_match.iloc[0] if not snap_match.empty else None
        print(
            format_candidate_activation_summary(
                candidate,
                snapshot=snapshot,
            )
        )
        print()
        if not bool(args.confirm):
            print("Activation not performed.")
            print(
                "Review the candidate above and rerun with --confirm."
            )
            return 2
        try:
            activation = activate_candidate(
                candidate_id=candidate_id,
                candidates_csv=paths["candidates_csv"],
                snapshots_csv=paths["snapshots_csv"],
                activations_csv=paths["activations_csv"],
                emission_factors_csv=paths["emission_factors"],
                fuel_heating_values_csv=paths["fuel_heating_values"],
                gwp_values_csv=paths["gwp_values"],
                activated_at=activated_at,
                activated_by=str(args.activated_by),
            )
        except ReferenceSyncError as exc:
            print(f"Error: {exc.code}: {exc.message}", file=sys.stderr)
            return 2
        print("Activation completed.")
        print(f"activation_id: {activation['activation_id']}")
        print(f"factor_id: {activation['factor_id']}")
        print(f"snapshot_id: {activation['snapshot_id']}")
        print(f"activated_at: {activation['activated_at']}")
        return 0
    if command == "activate-steel":
        from carbon_ledger.steel_factor_catalog import (
            SteelFactorActivationError,
            activate_reviewed_steel_factor,
            load_steel_factor_candidates,
            steel_candidates_path,
        )

        paths = default_paths(repo_root)
        candidate_id = str(args.candidate_id).strip()
        candidates = load_steel_factor_candidates(paths["reference_dir"])
        if candidates.empty:
            print(
                "Error: No steel candidates. Fetch CFP_P_02 from the "
                "public data.gov.tw dataset first: "
                "python -m carbon_ledger references fetch",
                file=sys.stderr,
            )
            return 2
        match = candidates.loc[candidates["candidate_id"] == candidate_id]
        if match.empty:
            print(
                f"Error: Unknown steel candidate_id {candidate_id!r}.",
                file=sys.stderr,
            )
            return 2
        row = {
            column: str(match.iloc[0].get(column) or "")
            for column in match.columns
        }
        print(f"candidate_id: {candidate_id}")
        print(f"official_name: {row.get('official_name')}")
        print(f"official_coe: {row.get('official_coe')}")
        print(f"official_unit: {row.get('official_unit')}")
        print(f"announcementyear: {row.get('official_announcementyear')}")
        print(f"source_record_id: {row.get('source_record_id')}")
        print(f"source_url: {row.get('source_url')}")
        print(f"snapshot_hash: {row.get('snapshot_hash')}")
        print(
            "Review fields are internally approved applicability, "
            "not government valid_from/valid_to."
        )
        if not bool(args.confirm):
            print("Activation not performed. Rerun with --confirm.")
            return 2
        from carbon_ledger.cfp_p_02 import parse_declared_factor_units

        if not str(row.get("factor_year") or "").strip():
            row["factor_year"] = str(row.get("official_announcementyear") or "")
        if not str(row.get("steel_product_type") or "").strip():
            row["steel_product_type"] = str(row.get("official_name") or "")
        if not str(row.get("factor_value") or "").strip():
            row["factor_value"] = str(row.get("official_coe") or "")
        if not str(row.get("numerator_unit") or "").strip() or not str(
            row.get("denominator_unit") or ""
        ).strip():
            units = parse_declared_factor_units(str(row.get("official_unit") or ""))
            if units:
                row["numerator_unit"] = units[0]
                row["denominator_unit"] = units[1]
        row.update(
            {
                "lifecycle_boundary": str(args.lifecycle_boundary).strip(),
                "geography": str(args.geography).strip(),
                "approved_for_reporting_from": str(
                    args.approved_for_reporting_from
                ).strip(),
                "approved_for_reporting_to": str(
                    args.approved_for_reporting_to
                ).strip(),
                "approval_status": "approved",
                "reviewer": str(args.reviewer).strip(),
                "approved_at": str(args.approved_at).strip(),
                "factor_version": str(args.factor_version).strip(),
                "reason": str(args.rationale).strip(),
            }
        )
        try:
            activated = activate_reviewed_steel_factor(
                row, reference_dir=paths["reference_dir"]
            )
        except SteelFactorActivationError as exc:
            print(f"Error: {exc.reason}", file=sys.stderr)
            return 2
        updated = candidates.copy()
        updated.loc[
            updated["candidate_id"] == candidate_id, "approval_status"
        ] = "approved"
        updated.loc[updated["candidate_id"] == candidate_id, "reviewer"] = (
            str(args.reviewer).strip()
        )
        updated.loc[updated["candidate_id"] == candidate_id, "approved_at"] = (
            str(args.approved_at).strip()
        )
        updated.loc[
            updated["candidate_id"] == candidate_id, "lifecycle_boundary"
        ] = str(args.lifecycle_boundary).strip()
        updated.loc[updated["candidate_id"] == candidate_id, "geography"] = (
            str(args.geography).strip()
        )
        updated.loc[
            updated["candidate_id"] == candidate_id,
            "approved_for_reporting_from",
        ] = str(args.approved_for_reporting_from).strip()
        updated.loc[
            updated["candidate_id"] == candidate_id,
            "approved_for_reporting_to",
        ] = str(args.approved_for_reporting_to).strip()
        updated.loc[
            updated["candidate_id"] == candidate_id, "factor_version"
        ] = str(args.factor_version).strip()
        updated.to_csv(steel_candidates_path(paths["reference_dir"]), index=False)
        print("Steel factor activated.")
        print(f"factor_id: {activated['factor_id']}")
        print(f"factor_version: {activated['factor_version']}")
        print(f"steel_product_type: {activated['steel_product_type']}")
        return 0
    if command == "propose-update":
        proposal = propose_official_factor_update(
            repo_root,
            retrieved_at=str(getattr(args, "retrieved_at", "") or ""),
        )
        print(proposal["proposal_json"])
        print(proposal["proposal_md"])
        print(f"open_pr: {proposal['open_pr']}")
        print(
            "activatable: "
            + ",".join(proposal["activatable_candidate_ids"])
        )
        print(f"manual_review_required: {proposal['manual_review_required']}")
        return 0
    if command == "status":
        status = reference_sync_status(repo_root)
        print("Official reference status")
        print(f"Last checked: {status.last_checked_at}")
        print("Electricity factor — enterprise inventory")
        for year, state in status.electricity_years.items():
            print(f"  {year} — {state}")
        if status.electricity_categories:
            print("Electricity factor categories:")
            for category, state in status.electricity_categories.items():
                print(f"  {category}:")
                print(f"    {state}")
        print(
            "Upstream authority: "
            f"{status.upstream_factor_authority} "
            f"({status.upstream_source_status})"
        )
        print(
            "Operational official source: "
            f"{status.operational_source_authority} "
            f"({status.operational_source_status})"
        )
        if status.upstream_canonical_url:
            print(f"Upstream canonical URL: {status.upstream_canonical_url}")
        if status.operational_source_url:
            print(f"Operational source URL: {status.operational_source_url}")
        print("Fuel heating values (latest registered year):")
        for fuel, year in status.heating_value_latest.items():
            print(f"  {fuel} — {year}")
        print(
            f"Snapshots: {status.snapshot_count}; "
            f"candidates: {status.candidate_count}; "
            f"active candidates: {status.active_candidate_count}"
        )
        return 0

    print(
        "Usage: python -m carbon_ledger references "
        "[check|fetch|validate|activate|propose-update|status]",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the requested command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-demo":
        return _run_demo_command(args)
    if args.command == "references":
        return _run_references_command(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
