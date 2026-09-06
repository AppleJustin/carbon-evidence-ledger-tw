"""Purchased-steel average-data catalog: taxonomy, candidates, and active factors.

Three stages stay separate:

1. Official CFP_P_02 raw fields (candidate)
2. Internal review / applicability metadata (still candidate until approved)
3. Active factor used for Category 1 calculation

Official updates never overwrite an active row. Activation requires explicit
review fields and is never performed by the scheduled workflow.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from carbon_ledger.cfp_p_02 import (
    GENERIC_STEEL_LABELS,
    STEEL_OFFICIAL_PRODUCT_NAMES,
    is_generic_steel_label,
    is_steel_official_product,
    redact_api_key_from_url,
)

ACTIVITY_TYPE = "purchased_steel"
FACTOR_BOUNDARY_CRADLE_TO_GATE = "cradle_to_gate"
READY_FACTOR_STATUS = "ready"

UNDECIDED_PRODUCT_TYPE = "其他／尚不確定"
TAXONOMY_COLUMNS = [
    "taxonomy_id",
    "official_name",
    "ui_group",
    "sort_order",
    "notes",
]
STEEL_CANDIDATE_COLUMNS = [
    "candidate_id",
    "snapshot_id",
    "source_id",
    "source_record_id",
    "official_name",
    "official_coe",
    "official_unit",
    "official_departmentname",
    "official_announcementyear",
    "steel_product_type",
    "factor_value",
    "numerator_unit",
    "denominator_unit",
    "lifecycle_boundary",
    "geography",
    "technology",
    "factor_year",
    "approved_for_reporting_from",
    "approved_for_reporting_to",
    "source_url",
    "snapshot_hash",
    "source_dataset",
    "retrieved_at",
    "official_valid_from",
    "official_valid_to",
    "publisher",
    "approval_status",
    "reviewer",
    "approved_at",
    "factor_version",
    "is_secondary_or_proxy",
    "lifecycle_status",
    "reason",
    "created_at",
]
ACTIVE_STEEL_FACTOR_COLUMNS = [
    "factor_id",
    "activity_type",
    "steel_product_type",
    "product_type",
    "official_name",
    "technology",
    "factor_value",
    "numerator_unit",
    "denominator_unit",
    "factor_unit",
    "factor_boundary",
    "lifecycle_boundary",
    "geography",
    "factor_year",
    "announcement_year",
    "publisher",
    "source_dataset",
    "official_valid_from",
    "official_valid_to",
    "approved_for_reporting_from",
    "approved_for_reporting_to",
    "source_reference_id",
    "source_record_id",
    "source_url",
    "snapshot_hash",
    "source_snapshot_sha256",
    "retrieved_at",
    "factor_status",
    "review_status",
    "factor_version",
    "approval_status",
    "reviewer",
    "approved_at",
    "rationale",
    "is_secondary_or_proxy",
    "includes_pre_tier1_supply_chain_transport",
    "notes",
]
REQUIRED_ACTIVATION_FIELDS = (
    "steel_product_type",
    "factor_value",
    "numerator_unit",
    "denominator_unit",
    "lifecycle_boundary",
    "geography",
    "factor_year",
    "approved_for_reporting_from",
    "source_record_id",
    "source_url",
    "snapshot_hash",
    "approval_status",
    "reviewer",
    "approved_at",
    "factor_version",
)
DEFAULT_REFERENCE_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "reference"
)


class SteelFactorActivationError(Exception):
    """Candidate is not ready to become an active steel factor."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _display_year(value: Any) -> str:
    """Format a year for display only. Source catalog values are not mutated."""
    text = _text(value)
    if not text:
        return ""
    try:
        number = float(text)
    except (TypeError, ValueError):
        return text
    if number.is_integer():
        year = int(number)
        if 1000 <= abs(year) <= 9999:
            return str(year)
    return text


def _read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    extra = [column for column in frame.columns if column not in columns]
    return frame.loc[:, columns + extra].copy()


def _write_csv(path: Path, frame: pd.DataFrame, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = ""
    extra = [column for column in out.columns if column not in columns]
    out.loc[:, columns + extra].to_csv(path, index=False)


def taxonomy_path(reference_dir: Path | None = None) -> Path:
    root = Path(reference_dir) if reference_dir is not None else DEFAULT_REFERENCE_DIR
    return root / "steel_product_taxonomy.csv"


def steel_candidates_path(reference_dir: Path | None = None) -> Path:
    root = Path(reference_dir) if reference_dir is not None else DEFAULT_REFERENCE_DIR
    return root / "purchased_steel_factor_candidates.csv"


def active_steel_factors_path(reference_dir: Path | None = None) -> Path:
    root = Path(reference_dir) if reference_dir is not None else DEFAULT_REFERENCE_DIR
    return root / "purchased_steel_factors.csv"


def load_steel_product_taxonomy(reference_dir: Path | None = None) -> pd.DataFrame:
    path = taxonomy_path(reference_dir)
    frame = _read_csv(path, TAXONOMY_COLUMNS)
    if frame.empty:
        return pd.DataFrame(
            [
                {
                    "taxonomy_id": f"tax_{index:02d}",
                    "official_name": name,
                    "ui_group": name,
                    "sort_order": str(index),
                    "notes": "",
                }
                for index, name in enumerate(STEEL_OFFICIAL_PRODUCT_NAMES, start=1)
            ]
        )
    return frame


def official_taxonomy_names(reference_dir: Path | None = None) -> tuple[str, ...]:
    frame = load_steel_product_taxonomy(reference_dir)
    names = [
        _text(row.get("official_name"))
        for row in frame.to_dict(orient="records")
        if _text(row.get("official_name"))
    ]
    return tuple(names) or STEEL_OFFICIAL_PRODUCT_NAMES


def load_steel_factor_candidates(reference_dir: Path | None = None) -> pd.DataFrame:
    return _read_csv(steel_candidates_path(reference_dir), STEEL_CANDIDATE_COLUMNS)


def load_active_steel_factors(reference_dir: Path | None = None) -> pd.DataFrame:
    frame = _read_csv(
        active_steel_factors_path(reference_dir),
        ACTIVE_STEEL_FACTOR_COLUMNS,
    )
    if frame.empty:
        return frame
    return frame.loc[frame["factor_status"].astype(str) == READY_FACTOR_STATUS].copy()


def merge_steel_factors(
    emission_factors: pd.DataFrame | None,
    reference_dir: Path | None = None,
) -> pd.DataFrame:
    """Append active steel catalog rows without mutating electricity/fuel rows."""
    base = (
        emission_factors.copy(deep=True)
        if emission_factors is not None
        else pd.DataFrame()
    )
    steel = load_active_steel_factors(reference_dir)
    if steel.empty:
        return base
    return pd.concat([base, steel], ignore_index=True, sort=False)


def steel_product_type_choices(
    *,
    reference_dir: Path | None = None,
    active_factors: pd.DataFrame | None = None,
) -> tuple[str, ...]:
    """Select options from taxonomy + active catalog. Not a Streamlit hardcode."""
    names: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        cleaned = _text(value)
        if not cleaned or cleaned in seen or is_generic_steel_label(cleaned):
            return
        seen.add(cleaned)
        names.append(cleaned)

    taxonomy = load_steel_product_taxonomy(reference_dir)
    for row in taxonomy.to_dict(orient="records"):
        add(row.get("official_name"))
    catalog = (
        active_factors
        if active_factors is not None
        else load_active_steel_factors(reference_dir)
    )
    if catalog is not None and not catalog.empty:
        column = (
            "steel_product_type"
            if "steel_product_type" in catalog.columns
            else ""
        )
        if column:
            for value in catalog[column].tolist():
                add(value)
    names.append(UNDECIDED_PRODUCT_TYPE)
    return tuple(names)


def pending_steel_candidates_for_product(
    steel_product_type: str,
    *,
    reference_dir: Path | None = None,
) -> pd.DataFrame:
    product = _text(steel_product_type)
    if not product or is_generic_steel_label(product):
        return pd.DataFrame(columns=STEEL_CANDIDATE_COLUMNS)
    candidates = load_steel_factor_candidates(reference_dir)
    if candidates.empty:
        return candidates
    status = candidates["approval_status"].astype(str)
    pending = candidates.loc[
        (candidates["steel_product_type"].astype(str) == product)
        & ~status.isin({"approved", "active", "rejected"})
    ]
    return pending.copy()


def matchable_average_factor_rows(
    *,
    steel_product_type: str,
    reporting_year: int | None,
    geography: str = "",
    technology: str = "",
    reference_dir: Path | None = None,
    active_factors: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Active factors that could match. Does not pick newest or first."""
    product = _text(steel_product_type)
    if not product or is_generic_steel_label(product):
        return pd.DataFrame()
    catalog = (
        active_factors.copy()
        if active_factors is not None
        else load_active_steel_factors(reference_dir)
    )
    if catalog is None or catalog.empty:
        return pd.DataFrame()
    if "steel_product_type" not in catalog.columns:
        return pd.DataFrame()
    matched = catalog.loc[catalog["steel_product_type"].astype(str) == product]
    if geography:
        geo_col = "geography" if "geography" in matched.columns else "factor_geography"
        if geo_col in matched.columns:
            matched = matched.loc[matched[geo_col].astype(str) == geography]
    if technology and "technology" in matched.columns:
        matched = matched.loc[
            (matched["technology"].astype(str) == "")
            | (matched["technology"].astype(str) == technology)
        ]
    if reporting_year is not None:
        keep: list[bool] = []
        for row in matched.to_dict(orient="records"):
            keep.append(_covers_reporting_year(row, reporting_year))
        matched = matched.loc[keep]
    return matched.copy()


def display_factor_rows(frame: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if frame is None or frame.empty:
        return rows
    for raw in frame.to_dict(orient="records"):
        numerator = _text(raw.get("numerator_unit"))
        denominator = _text(raw.get("denominator_unit"))
        unit = (
            f"{numerator}/{denominator}"
            if numerator and denominator
            else _text(raw.get("factor_unit"))
        )
        start = _text(raw.get("approved_for_reporting_from") or raw.get("valid_from"))
        end = _text(raw.get("approved_for_reporting_to") or raw.get("valid_to"))
        period = start
        if end:
            period = f"{start} → {end}"
        elif start:
            period = f"{start} → (open-ended, internally approved)"
        publisher = _text(
            raw.get("publisher") or raw.get("official_departmentname")
        )
        rows.append(
            {
                "steel_product_type": _text(
                    raw.get("official_name") or raw.get("steel_product_type")
                ),
                "official_name": _text(
                    raw.get("official_name") or raw.get("steel_product_type")
                ),
                "factor_value": _text(raw.get("factor_value")),
                "factor_unit": unit,
                "declared_unit": publisher,
                "publisher": publisher,
                "announcement_year": _display_year(raw.get("announcement_year")),
                "factor_year": _display_year(raw.get("factor_year")),
                "factor_version": _text(raw.get("factor_version")),
                "factor_boundary": _text(
                    raw.get("factor_boundary") or raw.get("lifecycle_boundary")
                ),
                "geography": _text(raw.get("geography") or raw.get("factor_geography")),
                "source_url": redact_api_key_from_url(
                    _text(raw.get("source_url") or raw.get("source_locator"))
                ),
                "applicability_period": period,
                "is_secondary_or_proxy": _text(
                    raw.get("is_secondary_or_proxy") or "true"
                ),
                "technology": _text(raw.get("technology")),
                "factor_id": _text(raw.get("factor_id")),
            }
        )
    return rows


def upsert_steel_candidates(
    records: Sequence[Mapping[str, Any]],
    *,
    snapshot_id: str,
    source_id: str,
    retrieved_at: str,
    reference_dir: Path | None = None,
) -> list[dict[str, str]]:
    """Insert new official steel candidates. Never updates active factors."""
    path = steel_candidates_path(reference_dir)
    existing = _read_csv(path, STEEL_CANDIDATE_COLUMNS)
    known = set()
    if not existing.empty:
        known = set(
            zip(
                existing["source_record_id"].astype(str),
                existing["snapshot_hash"].astype(str),
                strict=False,
            )
        )
    created: list[dict[str, str]] = []
    rows = [dict(item) for item in existing.to_dict(orient="records")]
    for record in records:
        source_record_id = _text(record.get("source_record_id"))
        snapshot_hash = _text(record.get("snapshot_hash"))
        if not source_record_id:
            continue
        key = (source_record_id, snapshot_hash)
        if key in known:
            continue
        row = {column: "" for column in STEEL_CANDIDATE_COLUMNS}
        row.update(
            {
                "candidate_id": f"cand_steel_{source_record_id[:12]}",
                "snapshot_id": snapshot_id,
                "source_id": source_id,
                "source_record_id": source_record_id,
                "official_name": _text(record.get("official_name")),
                "official_coe": _text(record.get("official_coe")),
                "official_unit": _text(record.get("official_unit")),
                "official_departmentname": _text(
                    record.get("official_departmentname")
                ),
                "official_announcementyear": _text(
                    record.get("official_announcementyear")
                ),
                "steel_product_type": _text(record.get("steel_product_type")),
                "factor_value": _text(record.get("factor_value")),
                "numerator_unit": _text(record.get("numerator_unit")),
                "denominator_unit": _text(record.get("denominator_unit")),
                "lifecycle_boundary": "",
                "geography": "",
                "technology": _text(record.get("technology")),
                "factor_year": _text(record.get("factor_year")),
                "approved_for_reporting_from": "",
                "approved_for_reporting_to": "",
                "source_url": redact_api_key_from_url(
                    _text(record.get("source_url"))
                ),
                "snapshot_hash": snapshot_hash,
                "source_dataset": _text(record.get("source_dataset")) or "CFP_P_02",
                "retrieved_at": retrieved_at,
                "official_valid_from": "",
                "official_valid_to": "",
                "publisher": _text(
                    record.get("publisher")
                    or record.get("official_departmentname")
                ),
                "approval_status": "pending_review",
                "reviewer": "",
                "approved_at": "",
                "factor_version": "",
                "is_secondary_or_proxy": "true",
                "lifecycle_status": "candidate",
                "reason": _text(record.get("applicability_notes")),
                "created_at": retrieved_at,
            }
        )
        rows.append(row)
        created.append(row)
        known.add(key)
    _write_csv(path, pd.DataFrame(rows), STEEL_CANDIDATE_COLUMNS)
    return created


def activate_reviewed_steel_factor(
    candidate: Mapping[str, Any],
    *,
    reference_dir: Path | None = None,
    factor_id: str = "",
) -> dict[str, str]:
    """Copy a fully reviewed candidate into the active catalog. Never silent."""
    missing = [
        field
        for field in REQUIRED_ACTIVATION_FIELDS
        if not _text(candidate.get(field))
        and not (
            field == "approved_for_reporting_to"
        )
    ]
    if missing:
        raise SteelFactorActivationError(
            "Steel factor cannot be activated until review fields are "
            f"complete: {', '.join(missing)}."
        )
    if _text(candidate.get("lifecycle_boundary")) != FACTOR_BOUNDARY_CRADLE_TO_GATE:
        raise SteelFactorActivationError(
            "Active steel factors require an internally reviewed "
            "cradle-to-gate lifecycle boundary. The official API does not "
            "state this boundary."
        )
    if _text(candidate.get("approval_status")) not in {"approved", "active"}:
        raise SteelFactorActivationError(
            "Only an approved steel candidate can become an active factor."
        )
    if is_generic_steel_label(_text(candidate.get("steel_product_type"))):
        raise SteelFactorActivationError(
            "Generic labels such as 採購鋼材 cannot be activated as a product."
        )
    try:
        value = Decimal(_text(candidate.get("factor_value")).replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise SteelFactorActivationError("factor_value is not numeric.") from exc
    if not value.is_finite() or value <= 0:
        raise SteelFactorActivationError("factor_value must be greater than zero.")

    path = active_steel_factors_path(reference_dir)
    existing = _read_csv(path, ACTIVE_STEEL_FACTOR_COLUMNS)
    source_record_id = _text(candidate.get("source_record_id"))
    version = _text(candidate.get("factor_version"))
    if not existing.empty:
        same = existing.loc[
            (existing["source_record_id"].astype(str) == source_record_id)
            & (existing["factor_version"].astype(str) == version)
        ]
        if not same.empty:
            return {
                column: _text(same.iloc[0].get(column))
                for column in ACTIVE_STEEL_FACTOR_COLUMNS
            }

    product_name = _text(
        candidate.get("official_name") or candidate.get("steel_product_type")
    )
    numerator = _text(candidate.get("numerator_unit"))
    denominator = _text(candidate.get("denominator_unit"))
    snapshot_hash = _text(candidate.get("snapshot_hash"))
    rationale = _text(
        candidate.get("rationale") or candidate.get("reason") or candidate.get("notes")
    )
    new_id = factor_id or (
        "ef_steel_"
        f"{_slug(_text(candidate.get('steel_product_type')))}_"
        f"{_text(candidate.get('factor_year'))}_"
        f"{version}"
    )
    row = {column: "" for column in ACTIVE_STEEL_FACTOR_COLUMNS}
    row.update(
        {
            "factor_id": new_id,
            "activity_type": ACTIVITY_TYPE,
            "steel_product_type": _text(candidate.get("steel_product_type")),
            "product_type": product_name,
            "official_name": product_name,
            "technology": _text(candidate.get("technology")),
            "factor_value": _text(candidate.get("factor_value")),
            "numerator_unit": numerator,
            "denominator_unit": denominator,
            "factor_unit": (
                _text(candidate.get("factor_unit"))
                or (f"{numerator}/{denominator}" if numerator and denominator else "")
            ),
            "factor_boundary": FACTOR_BOUNDARY_CRADLE_TO_GATE,
            "lifecycle_boundary": FACTOR_BOUNDARY_CRADLE_TO_GATE,
            "geography": _text(candidate.get("geography")),
            "factor_year": _text(candidate.get("factor_year")),
            "announcement_year": _text(
                candidate.get("official_announcementyear")
                or candidate.get("factor_year")
            ),
            "publisher": _text(
                candidate.get("publisher")
                or candidate.get("official_departmentname")
            ),
            "source_dataset": _text(candidate.get("source_dataset")) or "CFP_P_02",
            "official_valid_from": "",
            "official_valid_to": "",
            "approved_for_reporting_from": _text(
                candidate.get("approved_for_reporting_from")
            ),
            "approved_for_reporting_to": _text(
                candidate.get("approved_for_reporting_to")
            ),
            "source_reference_id": _text(
                candidate.get("source_reference_id") or candidate.get("source_id")
            ),
            "source_record_id": source_record_id,
            "source_url": redact_api_key_from_url(
                _text(candidate.get("source_url"))
            ),
            "snapshot_hash": snapshot_hash,
            "source_snapshot_sha256": snapshot_hash,
            "retrieved_at": _text(
                candidate.get("retrieved_at") or candidate.get("created_at")
            ),
            "factor_status": READY_FACTOR_STATUS,
            "review_status": "active",
            "factor_version": version,
            "approval_status": "approved",
            "reviewer": _text(candidate.get("reviewer")),
            "approved_at": _text(candidate.get("approved_at")),
            "rationale": rationale,
            "is_secondary_or_proxy": _text(
                candidate.get("is_secondary_or_proxy") or "true"
            ),
            "includes_pre_tier1_supply_chain_transport": _text(
                candidate.get("includes_pre_tier1_supply_chain_transport")
            ),
            "notes": (
                rationale
                or (
                    "Internally reviewed average-data factor. "
                    "approved_for_reporting_from/to are project governance "
                    "dates, not government valid_from/valid_to. "
                    "official_valid_from/to stay blank because CFP_P_02 "
                    "does not publish those fields."
                )
            ),
        }
    )
    out = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    _write_csv(path, out, ACTIVE_STEEL_FACTOR_COLUMNS)
    return row


def _covers_reporting_year(row: Mapping[str, Any], reporting_year: int) -> bool:
    year_start = date(reporting_year, 1, 1)
    year_end = date(reporting_year, 12, 31)
    start_text = _text(
        row.get("approved_for_reporting_from") or row.get("valid_from")
    )
    end_text = _text(row.get("approved_for_reporting_to") or row.get("valid_to"))
    start = _parse_date(start_text)
    if start is None or start > year_start:
        return False
    if not end_text:
        return True
    end = _parse_date(end_text)
    if end is None:
        return False
    return end >= year_end


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    stamp = pd.Timestamp(parsed)
    return date(int(stamp.year), int(stamp.month), int(stamp.day))


def _slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value)
    return cleaned.strip("_") or "product"


# Re-export for callers that only import this module.
__all__ = [
    "GENERIC_STEEL_LABELS",
    "UNDECIDED_PRODUCT_TYPE",
    "SteelFactorActivationError",
    "activate_reviewed_steel_factor",
    "display_factor_rows",
    "is_generic_steel_label",
    "is_steel_official_product",
    "load_active_steel_factors",
    "load_steel_factor_candidates",
    "load_steel_product_taxonomy",
    "matchable_average_factor_rows",
    "merge_steel_factors",
    "official_taxonomy_names",
    "pending_steel_candidates_for_product",
    "steel_product_type_choices",
    "upsert_steel_candidates",
]
