"""Framework-neutral core data-quality exception register.

Phase 7A consolidates technical core-pipeline problems into one deterministic
exception register. It does not use GHG Protocol, CBAM, or IFRS S2 outputs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

OUTPUT_COLUMNS = [
    "issue_id",
    "record_id",
    "source_document_id",
    "issue_scope",
    "pipeline_stage",
    "issue_code",
    "severity",
    "issue_status",
    "source_status",
    "source_reason",
    "blocking_dependency",
    "rule_id",
    "rule_version",
    "issue_summary",
    "recommended_action",
    "allowed_use",
    "prohibited_use",
    "requires_human_review",
]

SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}

NORMALIZATION_ISSUE_STATUSES = {
    "invalid_value": "qa_normalization_invalid_value",
    "invalid_unit": "qa_normalization_invalid_unit",
    "unsupported_activity_type": "qa_unsupported_activity_type",
    "unsupported_conversion": "qa_normalization_unsupported_conversion",
}

SUCCESSFUL_NORMALIZATION_STATUSES = frozenset(
    {"already_canonical", "normalized"}
)

EXPECTED_READINESS_CALCULATION_PAIRS = {
    "ready": "calculated",
    "blocked_missing_conversion": "blocked_missing_conversion",
    "blocked_ambiguous_conversion": "blocked_ambiguous_conversion",
    "blocked_incomplete_gas_factors": "blocked_incomplete_gas_factors",
    "blocked_conflicting_factor_group": "blocked_conflicting_factor_group",
    "blocked_natural_gas_type_required": "blocked_natural_gas_type_required",
    "no_factor_configured": "no_factor_configured",
    "not_emissions_activity": "not_emissions_activity",
    "unsupported_activity_type": "unsupported_activity_type",
}

DELEGATED_READINESS_STATUSES = frozenset(
    {
        "purchased_steel_category1",
    }
)

CALCULATION_ISSUE_RULES = {
    "blocked_missing_conversion": "qa_missing_conversion_dependency",
    "blocked_ambiguous_conversion": "qa_ambiguous_conversion",
    "blocked_incomplete_gas_factors": "qa_incomplete_gas_factors",
    "blocked_conflicting_factor_group": "qa_conflicting_factor_group",
    "blocked_missing_gwp": "qa_missing_gwp",
    "blocked_natural_gas_type_required": "qa_natural_gas_type_required",
    "no_factor_configured": "qa_no_factor_configured",
    "invalid_normalized_input": "qa_invalid_normalized_input",
    "factor_match_inconsistent": "qa_factor_match_inconsistent",
    "unsupported_activity_type": "qa_unsupported_activity_type",
}

NON_ISSUE_CALCULATION_STATUSES = frozenset(
    {"calculated", "not_emissions_activity"}
)

CALCULATION_LAYER_ERROR_STATUSES = frozenset(
    {
        "invalid_normalized_input",
        "factor_match_inconsistent",
        "blocked_missing_gwp",
        "blocked_incomplete_gas_factors",
        "blocked_conflicting_factor_group",
        "blocked_ambiguous_conversion",
        "blocked_missing_conversion",
        "blocked_natural_gas_type_required",
    }
)

REQUIRED_REJECTION_COLUMNS = (
    "record_kind",
    "row_number",
    "record_id",
    "rejection_code",
    "rejection_message",
)


def load_qa_rules(config_directory: Path) -> pd.DataFrame:
    """Load versioned core QA exception rules from a config directory."""
    path = Path(config_directory) / "qa_rules.csv"
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def _text(value: Any) -> str:
    if _is_blank(value):
        return ""
    return str(value).strip()


def _parse_bool(value: Any) -> bool:
    return _text(value).lower() == "true"


def _sanitize_id_component(value: Any) -> str:
    text = _text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _blank_to_na(value: str) -> Any:
    return value if value else pd.NA


def _rule_lookup(rules: pd.DataFrame) -> dict[str, pd.Series]:
    lookup: dict[str, pd.Series] = {}
    for _, row in rules.iterrows():
        rule_id = _text(row.get("rule_id"))
        if rule_id:
            lookup[rule_id] = row
    return lookup


def _has_column(frame: pd.DataFrame, column: str) -> bool:
    return column in frame.columns


def _frame_usable(frame: pd.DataFrame, required_columns: tuple[str, ...]) -> bool:
    return all(column in frame.columns for column in required_columns)


def _stage_frame_usable(frame: pd.DataFrame) -> bool:
    """A stage frame is usable only when it has rows and a record_id column."""
    return not frame.empty and _has_column(frame, "record_id")


def _missing_stage_reason(stage_label: str) -> str:
    if stage_label == "normalization":
        return (
            "Normalization result is missing because normalized_records is "
            "empty or does not include a usable record_id column."
        )
    if stage_label == "readiness":
        return (
            "Activity-readiness result is missing because activity_readiness "
            "is empty or does not include a usable record_id column."
        )
    return (
        "Calculation result is missing because calculation_results is empty "
        "or does not include a usable record_id column."
    )


def _issue_from_rule(
    *,
    issue_id: str,
    record_id: Any,
    source_document_id: Any,
    issue_scope: str,
    rule: pd.Series,
    source_status: str,
    source_reason: str,
    blocking_dependency: Any = pd.NA,
    pipeline_stage_override: str | None = None,
) -> dict[str, Any]:
    return {
        "issue_id": issue_id,
        "record_id": _blank_to_na(_text(record_id)),
        "source_document_id": _blank_to_na(_text(source_document_id)),
        "issue_scope": issue_scope,
        "pipeline_stage": pipeline_stage_override
        or _text(rule.get("pipeline_stage")),
        "issue_code": _text(rule.get("issue_code")),
        "severity": _text(rule.get("severity")),
        "issue_status": "open",
        "source_status": source_status,
        "source_reason": source_reason,
        "blocking_dependency": (
            blocking_dependency
            if not _is_blank(blocking_dependency)
            else pd.NA
        ),
        "rule_id": _text(rule.get("rule_id")),
        "rule_version": _text(rule.get("rule_version")),
        "issue_summary": _text(rule.get("issue_summary")),
        "recommended_action": _text(rule.get("recommended_action")),
        "allowed_use": _text(rule.get("allowed_use")),
        "prohibited_use": _text(rule.get("prohibited_use")),
        "requires_human_review": _parse_bool(rule.get("requires_human_review")),
    }


def _activity_issue_id(record_id: str, issue_code: str) -> str:
    return (
        f"qa_{_sanitize_id_component(record_id)}_"
        f"{_sanitize_id_component(issue_code)}"
    )


def _ingestion_issue_id(
    record_kind: str,
    row_number: Any,
    rejection_code: str,
) -> str:
    kind = _sanitize_id_component(record_kind) or "unknown"
    row = _sanitize_id_component(row_number) or "unknown"
    code = _sanitize_id_component(rejection_code) or "unknown"
    return f"qa_ingestion_{kind}_row_{row}_{code}"


def _lookup_rows(
    frame: pd.DataFrame,
    record_id: str,
) -> pd.DataFrame:
    if not _has_column(frame, "record_id"):
        return pd.DataFrame()
    return frame.loc[frame["record_id"].astype(str) == record_id]


def _build_ingestion_issues(
    ingestion_rejections: pd.DataFrame,
    rules_by_id: dict[str, pd.Series],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    rule = rules_by_id["qa_ingestion_rejection"]
    consistency_rule = rules_by_id["qa_pipeline_result_inconsistent"]

    if ingestion_rejections.empty:
        return issues

    if not _frame_usable(ingestion_rejections, REQUIRED_REJECTION_COLUMNS):
        issues.append(
            _issue_from_rule(
                issue_id="qa_pipeline_ingestion_rejections_schema",
                record_id=pd.NA,
                source_document_id=pd.NA,
                issue_scope="pipeline_consistency",
                rule=consistency_rule,
                source_status="missing_duplicate_or_conflicting_result",
                source_reason=(
                    "ingestion_rejections is non-empty but missing required "
                    "rejection columns."
                ),
            )
        )
        return issues

    for _, row in ingestion_rejections.iterrows():
        record_kind = _text(row.get("record_kind"))
        row_number = row.get("row_number")
        rejection_code = _text(row.get("rejection_code"))
        rejection_message = _text(row.get("rejection_message"))
        record_id = _text(row.get("record_id"))
        source_document_id = ""
        if _has_column(ingestion_rejections, "source_document_id"):
            source_document_id = _text(row.get("source_document_id"))

        issues.append(
            _issue_from_rule(
                issue_id=_ingestion_issue_id(
                    record_kind,
                    row_number,
                    rejection_code,
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="ingestion_rejection",
                rule=rule,
                source_status=rejection_code or "rejected",
                source_reason=rejection_message,
            )
        )
    return issues


def _pipeline_consistency_issue(
    *,
    record_id: str,
    source_document_id: Any,
    reason: str,
    rules_by_id: dict[str, pd.Series],
    issue_id_suffix: str | None = None,
) -> dict[str, Any]:
    rule = rules_by_id["qa_pipeline_result_inconsistent"]
    suffix = issue_id_suffix or "pipeline_result_inconsistent"
    return _issue_from_rule(
        issue_id=_activity_issue_id(record_id, suffix),
        record_id=record_id,
        source_document_id=source_document_id,
        issue_scope="pipeline_consistency",
        rule=rule,
        source_status="missing_duplicate_or_conflicting_result",
        source_reason=reason,
    )


def _orphan_issue(
    *,
    record_id: str,
    stage_label: str,
    rules_by_id: dict[str, pd.Series],
) -> dict[str, Any]:
    return _pipeline_consistency_issue(
        record_id=record_id,
        source_document_id=pd.NA,
        reason=(
            f"Orphan {stage_label} result exists for record_id "
            f"{record_id!r}, which is not present in activity_records."
        ),
        rules_by_id=rules_by_id,
        issue_id_suffix=f"orphan_{_sanitize_id_component(stage_label)}",
    )


def _build_orphan_issues(
    activity_ids: set[str],
    normalized_records: pd.DataFrame,
    activity_readiness: pd.DataFrame,
    calculation_results: pd.DataFrame,
    rules_by_id: dict[str, pd.Series],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    frames = (
        (normalized_records, "normalization"),
        (activity_readiness, "readiness"),
        (calculation_results, "calculation"),
    )
    seen: set[str] = set()
    for frame, label in frames:
        if not _has_column(frame, "record_id"):
            continue
        for record_id in frame["record_id"].astype(str).tolist():
            if _is_blank(record_id):
                continue
            if record_id in activity_ids:
                continue
            key = f"{record_id}|{label}"
            if key in seen:
                continue
            seen.add(key)
            issues.append(
                _orphan_issue(
                    record_id=record_id,
                    stage_label=label,
                    rules_by_id=rules_by_id,
                )
            )
    return issues


def _evaluate_activity(
    activity: pd.Series,
    normalized_records: pd.DataFrame,
    activity_readiness: pd.DataFrame,
    calculation_results: pd.DataFrame,
    rules_by_id: dict[str, pd.Series],
    schema_flags: dict[str, bool],
) -> list[dict[str, Any]]:
    record_id = _text(activity.get("record_id")) or "<missing>"
    source_document_id = _text(activity.get("source_document_id"))
    issues: list[dict[str, Any]] = []

    # Empty or schemaless required stage frames are consistency failures.
    for flag_name, stage_label in (
        ("normalized_ok", "normalization"),
        ("readiness_ok", "readiness"),
        ("calculation_ok", "calculation"),
    ):
        if not schema_flags[flag_name]:
            issues.append(
                _pipeline_consistency_issue(
                    record_id=record_id,
                    source_document_id=source_document_id,
                    reason=_missing_stage_reason(stage_label),
                    rules_by_id=rules_by_id,
                    issue_id_suffix=f"missing_{stage_label}_frame",
                )
            )
            return issues

    norm_rows = _lookup_rows(normalized_records, record_id)
    ready_rows = _lookup_rows(activity_readiness, record_id)
    calc_rows = _lookup_rows(calculation_results, record_id)

    if len(norm_rows) != 1:
        reason = (
            f"Expected exactly one normalization result for {record_id!r}; "
            f"found {len(norm_rows)}."
        )
        issues.append(
            _pipeline_consistency_issue(
                record_id=record_id,
                source_document_id=source_document_id,
                reason=reason,
                rules_by_id=rules_by_id,
                issue_id_suffix="missing_or_duplicate_normalization",
            )
        )
        return issues

    if len(ready_rows) != 1:
        reason = (
            f"Expected exactly one readiness result for {record_id!r}; "
            f"found {len(ready_rows)}."
        )
        issues.append(
            _pipeline_consistency_issue(
                record_id=record_id,
                source_document_id=source_document_id,
                reason=reason,
                rules_by_id=rules_by_id,
                issue_id_suffix="missing_or_duplicate_readiness",
            )
        )
        return issues

    if len(calc_rows) != 1:
        reason = (
            f"Expected exactly one calculation result for {record_id!r}; "
            f"found {len(calc_rows)}."
        )
        issues.append(
            _pipeline_consistency_issue(
                record_id=record_id,
                source_document_id=source_document_id,
                reason=reason,
                rules_by_id=rules_by_id,
                issue_id_suffix="missing_or_duplicate_calculation",
            )
        )
        return issues

    norm_row = norm_rows.iloc[0]
    ready_row = ready_rows.iloc[0]
    calc_row = calc_rows.iloc[0]

    normalization_status = _text(norm_row.get("normalization_status"))
    normalization_reason = _text(norm_row.get("normalization_reason"))
    readiness_status = _text(ready_row.get("calculation_readiness"))
    calculation_status = _text(calc_row.get("calculation_status"))
    calculation_reason = _text(calc_row.get("calculation_reason"))
    blocking_dependency = ready_row.get("blocking_dependency")

    upstream_normalization_issue = False
    if normalization_status in NORMALIZATION_ISSUE_STATUSES:
        rule_id = NORMALIZATION_ISSUE_STATUSES[normalization_status]
        rule = rules_by_id[rule_id]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=normalization_status,
                source_reason=normalization_reason,
            )
        )
        upstream_normalization_issue = True

    expected_calc = EXPECTED_READINESS_CALCULATION_PAIRS.get(readiness_status)
    statuses_match = (
        expected_calc is not None and calculation_status == expected_calc
    ) or readiness_status in DELEGATED_READINESS_STATUSES
    ready_calc_layer_error = (
        readiness_status == "ready"
        and calculation_status in CALCULATION_LAYER_ERROR_STATUSES
    )

    if not statuses_match and not ready_calc_layer_error:
        # Upstream normalization already explains the failure path.
        if upstream_normalization_issue:
            return issues
        issues.append(
            _pipeline_consistency_issue(
                record_id=record_id,
                source_document_id=source_document_id,
                reason=(
                    f"Readiness status {readiness_status!r} conflicts with "
                    f"calculation status {calculation_status!r}."
                ),
                rules_by_id=rules_by_id,
                issue_id_suffix="readiness_calculation_conflict",
            )
        )
        return issues

    if upstream_normalization_issue:
        return issues

    if calculation_status in NON_ISSUE_CALCULATION_STATUSES:
        return issues

    if calculation_status == "blocked_missing_conversion":
        rule = rules_by_id["qa_missing_conversion_dependency"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
                blocking_dependency=blocking_dependency,
            )
        )
        return issues

    if calculation_status == "blocked_natural_gas_type_required":
        rule = rules_by_id["qa_natural_gas_type_required"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
                blocking_dependency=blocking_dependency,
            )
        )
        return issues

    if calculation_status == "blocked_ambiguous_conversion":
        rule = rules_by_id["qa_ambiguous_conversion"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
                blocking_dependency=blocking_dependency,
            )
        )
        return issues

    if calculation_status == "blocked_incomplete_gas_factors":
        rule = rules_by_id["qa_incomplete_gas_factors"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
            )
        )
        return issues

    if calculation_status == "blocked_conflicting_factor_group":
        rule = rules_by_id["qa_conflicting_factor_group"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
            )
        )
        return issues

    if calculation_status == "blocked_missing_gwp":
        rule = rules_by_id["qa_missing_gwp"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
            )
        )
        return issues

    if calculation_status in {"no_factor_configured", "no_matching_factor"}:
        rule = rules_by_id["qa_no_factor_configured"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
            )
        )
        return issues

    if calculation_status == "invalid_normalized_input":
        if upstream_normalization_issue:
            return issues
        rule = rules_by_id["qa_invalid_normalized_input"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
            )
        )
        return issues

    if calculation_status == "factor_match_inconsistent":
        rule = rules_by_id["qa_factor_match_inconsistent"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
            )
        )
        return issues

    if calculation_status == "unsupported_activity_type":
        if upstream_normalization_issue:
            return issues
        rule = rules_by_id["qa_unsupported_activity_type"]
        issues.append(
            _issue_from_rule(
                issue_id=_activity_issue_id(
                    record_id,
                    _text(rule.get("issue_code")),
                ),
                record_id=record_id,
                source_document_id=source_document_id,
                issue_scope="activity_record",
                rule=rule,
                source_status=calculation_status,
                source_reason=calculation_reason,
                pipeline_stage_override="calculation",
            )
        )
        return issues

    return issues


def _sort_issues(issues: list[dict[str, Any]]) -> pd.DataFrame:
    if not issues:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    output = pd.DataFrame(issues, columns=OUTPUT_COLUMNS)
    # Deduplicate by issue_id, keeping first occurrence.
    output = output.drop_duplicates(subset=["issue_id"], keep="first")

    severity_rank = output["severity"].map(
        lambda value: SEVERITY_RANK.get(_text(value), 99)
    )
    record_sort = output["record_id"].map(
        lambda value: ("1", "") if _is_blank(value) else ("0", _text(value))
    )
    output = output.assign(
        _severity_rank=severity_rank,
        _record_blank=record_sort.map(lambda item: item[0]),
        _record_id_sort=record_sort.map(lambda item: item[1]),
    )
    output = output.sort_values(
        by=[
            "_severity_rank",
            "_record_blank",
            "_record_id_sort",
            "pipeline_stage",
            "issue_code",
            "issue_id",
        ],
        kind="mergesort",
    ).reset_index(drop=True)
    return output.drop(
        columns=["_severity_rank", "_record_blank", "_record_id_sort"]
    )


def build_core_qa_issues(
    activity_records: pd.DataFrame,
    ingestion_rejections: pd.DataFrame,
    normalized_records: pd.DataFrame,
    activity_readiness: pd.DataFrame,
    calculation_results: pd.DataFrame,
    rules: pd.DataFrame,
) -> pd.DataFrame:
    """Build the framework-neutral core data-quality exception register.

    Returns zero or more issue rows. Does not mutate inputs and does not create
    framework-specific conclusions.
    """
    activities = activity_records.copy(deep=True)
    rejections = ingestion_rejections.copy(deep=True)
    normalized = normalized_records.copy(deep=True)
    readiness = activity_readiness.copy(deep=True)
    calculations = calculation_results.copy(deep=True)
    rules_frame = rules.copy(deep=True)

    rules_by_id = _rule_lookup(rules_frame)
    issues: list[dict[str, Any]] = []

    issues.extend(_build_ingestion_issues(rejections, rules_by_id))

    schema_flags = {
        "normalized_ok": _stage_frame_usable(normalized),
        "readiness_ok": _stage_frame_usable(readiness),
        "calculation_ok": _stage_frame_usable(calculations),
    }

    # Empty frames and frames without record_id are treated as unusable stage
    # inputs and produce one critical consistency issue per accepted activity.
    activity_ids: set[str] = set()
    if _has_column(activities, "record_id"):
        for value in activities["record_id"].tolist():
            text = _text(value)
            if text:
                activity_ids.add(text)

    if _has_column(activities, "record_id"):
        for _, activity in activities.iterrows():
            issues.extend(
                _evaluate_activity(
                    activity,
                    normalized,
                    readiness,
                    calculations,
                    rules_by_id,
                    schema_flags,
                )
            )
    elif not activities.empty:
        # Non-empty activities without record_id: one consistency issue.
        consistency_rule = rules_by_id["qa_pipeline_result_inconsistent"]
        issues.append(
            _issue_from_rule(
                issue_id="qa_pipeline_activity_records_missing_record_id",
                record_id=pd.NA,
                source_document_id=pd.NA,
                issue_scope="pipeline_consistency",
                rule=consistency_rule,
                source_status="missing_duplicate_or_conflicting_result",
                source_reason=(
                    "activity_records is non-empty but missing a record_id "
                    "column."
                ),
            )
        )

    issues.extend(
        _build_orphan_issues(
            activity_ids,
            normalized,
            readiness,
            calculations,
            rules_by_id,
        )
    )

    return _sort_issues(issues)
