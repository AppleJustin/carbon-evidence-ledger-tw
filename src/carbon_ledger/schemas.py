"""Pandera schemas for raw source_documents and activity_records tables.

Phase 1A validates structure and cross-field rules only. It does not perform
carbon calculations or framework mappings.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema

from carbon_ledger.domain import (
    ACTIVITY_OTHER_NOTES_FIELDS,
    ACTIVITY_TYPE_UNIT_COMPATIBILITY,
    ACTIVITY_TYPES,
    ACTIVITY_UNKNOWN_REVIEW_FIELDS,
    CBAM_PROCESS_BOUNDARY_STATUSES,
    DATA_ORIGINS,
    DATA_QUALITY_TIERS,
    DOCUMENT_TYPES,
    FUEL_SUBTYPES,
    HUMAN_REVIEW_STATUSES,
    MEASUREMENT_METHODS,
    ORGANIZATIONAL_BOUNDARY_STATUSES,
    OWNERSHIP_CONTROLS,
    PROCESS_USES,
    RECORD_TYPES,
    SUPPORTED_UNITS,
    TRANSPORT_PAYERS,
)


def _non_empty_string(series: pd.Series) -> bool:
    """Return True when every non-null value is a non-empty string."""
    if series.isna().any():
        return False
    return series.astype(str).str.strip().ne("").all()


def _check_source_document_id_unique(df: pd.DataFrame) -> bool:
    return bool(df["source_document_id"].is_unique)


def _check_valid_document_dates(df: pd.DataFrame) -> bool:
    return bool(df["document_date"].notna().all())


def _check_synthetic_consistency(df: pd.DataFrame) -> bool:
    synthetic_flag = df["is_synthetic"]
    synthetic_origin = df["data_origin"] == "synthetic_generated"
    return bool((synthetic_flag == synthetic_origin).all())


def _check_document_type_other_notes(df: pd.DataFrame) -> bool:
    other_rows = df["document_type"] == "other"
    if not other_rows.any():
        return True
    notes = df.loc[other_rows, "notes"]
    return bool(notes.notna().all() and notes.astype(str).str.strip().ne("").all())


def _check_record_id_unique(df: pd.DataFrame) -> bool:
    return bool(df["record_id"].is_unique)


def _check_valid_activity_dates(df: pd.DataFrame) -> bool:
    return bool(
        df["activity_start_date"].notna().all()
        and df["activity_end_date"].notna().all()
    )


def _check_activity_date_order(df: pd.DataFrame) -> bool:
    return bool((df["activity_end_date"] >= df["activity_start_date"]).all())


def _check_unknown_requires_review(df: pd.DataFrame) -> bool:
    needs_review = df["human_review_status"] == "needs_review"
    for field in ACTIVITY_UNKNOWN_REVIEW_FIELDS:
        unknown_rows = df[field] == "unknown"
        if unknown_rows.any() and not needs_review.loc[unknown_rows].all():
            return False
    return True


def _check_activity_other_notes(df: pd.DataFrame) -> bool:
    for field in ACTIVITY_OTHER_NOTES_FIELDS:
        other_rows = df[field] == "other"
        if not other_rows.any():
            continue
        notes = df.loc[other_rows, "notes"]
        if not notes.notna().all():
            return False
        if not notes.astype(str).str.strip().ne("").all():
            return False
    return True


def _check_unit_compatibility(df: pd.DataFrame) -> bool:
    for activity_type, allowed_units in ACTIVITY_TYPE_UNIT_COMPATIBILITY.items():
        rows = df["activity_type"] == activity_type
        if not rows.any():
            continue
        units = df.loc[rows, "unit"]
        if not units.isin(allowed_units).all():
            return False
    return True


def _check_transport_payer_rules(df: pd.DataFrame) -> bool:
    transport_rows = df["record_type"] == "transport_activity"
    non_transport_rows = ~transport_rows

    if transport_rows.any():
        allowed = {"exporter", "supplier", "customer", "third_party", "unknown"}
        payers = df.loc[transport_rows, "transport_payer"]
        if payers.isna().any():
            return False
        if not payers.isin(allowed).all():
            return False

    if non_transport_rows.any():
        payers = df.loc[non_transport_rows, "transport_payer"]
        # Nullable for non-transport records; when present must be not_applicable.
        present = payers.notna()
        if present.any() and not (payers.loc[present] == "not_applicable").all():
            return False

    return True


SOURCE_DOCUMENTS_SCHEMA = DataFrameSchema(
    {
        "source_document_id": Column(
            str,
            checks=[
                Check(_non_empty_string, error="source_document_id must be non-empty"),
            ],
            nullable=False,
        ),
        "file_name": Column(
            str,
            checks=[
                Check(_non_empty_string, error="file_name must be non-empty"),
            ],
            nullable=False,
        ),
        "document_type": Column(str, checks=Check.isin(DOCUMENT_TYPES), nullable=False),
        "document_date": Column(pa.DateTime, nullable=False),
        "issuer": Column(str, nullable=True, required=False),
        "data_origin": Column(str, checks=Check.isin(DATA_ORIGINS), nullable=False),
        "is_synthetic": Column(bool, nullable=False),
        # Optional until the later ingestion / provenance phase.
        "source_path": Column(str, nullable=True, required=False),
        "sha256": Column(str, nullable=True, required=False),
        "ingested_at": Column(pa.DateTime, nullable=True, required=False),
        "ingestion_run_id": Column(str, nullable=True, required=False),
        "notes": Column(str, nullable=True, required=False),
    },
    checks=[
        Check(_check_source_document_id_unique, name="unique_source_document_id"),
        Check(_check_valid_document_dates, name="valid_document_dates"),
        Check(_check_synthetic_consistency, name="synthetic_consistency"),
        Check(_check_document_type_other_notes, name="document_type_other_notes"),
    ],
    strict=True,
    coerce=False,
)


ACTIVITY_RECORDS_SCHEMA = DataFrameSchema(
    {
        "record_id": Column(
            str,
            checks=[Check(_non_empty_string, error="record_id must be non-empty")],
            nullable=False,
        ),
        "source_document_id": Column(
            str,
            checks=[
                Check(
                    _non_empty_string,
                    error="source_document_id must be non-empty",
                ),
            ],
            nullable=False,
        ),
        "source_locator": Column(
            str,
            checks=[Check(_non_empty_string, error="source_locator must be non-empty")],
            nullable=False,
        ),
        "record_type": Column(str, checks=Check.isin(RECORD_TYPES), nullable=False),
        "activity_start_date": Column(pa.DateTime, nullable=False),
        "activity_end_date": Column(pa.DateTime, nullable=False),
        "site_id": Column(
            str,
            checks=[Check(_non_empty_string, error="site_id must be non-empty")],
            nullable=False,
        ),
        "production_process_id": Column(str, nullable=True, required=False),
        "product_id": Column(str, nullable=True, required=False),
        "activity_type": Column(str, checks=Check.isin(ACTIVITY_TYPES), nullable=False),
        "process_use": Column(
            str,
            checks=Check.isin(PROCESS_USES),
            nullable=True,
            required=False,
        ),
        "fuel_subtype": Column(
            str,
            checks=Check.isin(FUEL_SUBTYPES),
            nullable=True,
            required=False,
        ),
        "refrigerant_code": Column(str, nullable=True, required=False),
        "refill_confirmed": Column(str, nullable=True, required=False),
        "calculation_method": Column(str, nullable=True, required=False),
        "supplier_name": Column(str, nullable=True, required=False),
        "steel_product_type": Column(str, nullable=True, required=False),
        "product_identifier": Column(str, nullable=True, required=False),
        "emission_factor_value": Column(str, nullable=True, required=False),
        "emission_factor_unit": Column(str, nullable=True, required=False),
        "factor_boundary": Column(str, nullable=True, required=False),
        "factor_geography": Column(str, nullable=True, required=False),
        "factor_year": Column(str, nullable=True, required=False),
        "factor_source_id": Column(str, nullable=True, required=False),
        "evidence_reference": Column(str, nullable=True, required=False),
        "includes_pre_tier1_supply_chain_transport": Column(
            str, nullable=True, required=False
        ),
        "includes_tier1_to_reporting_company_transport": Column(
            str, nullable=True, required=False
        ),
        "factor_includes_tier1_to_reporting_company_transport": Column(
            str, nullable=True, required=False
        ),
        "tier1_to_reporting_company_transport_control": Column(
            str, nullable=True, required=False
        ),
        "activity_value": Column(float, checks=Check.gt(0), nullable=False),
        "unit": Column(str, checks=Check.isin(SUPPORTED_UNITS), nullable=False),
        "transport_payer": Column(
            str,
            checks=Check.isin(TRANSPORT_PAYERS),
            nullable=True,
            required=False,
        ),
        "ownership_control": Column(
            str,
            checks=Check.isin(OWNERSHIP_CONTROLS),
            nullable=False,
        ),
        "organizational_boundary_status": Column(
            str,
            checks=Check.isin(ORGANIZATIONAL_BOUNDARY_STATUSES),
            nullable=False,
        ),
        "cbam_process_boundary_status": Column(
            str,
            checks=Check.isin(CBAM_PROCESS_BOUNDARY_STATUSES),
            nullable=False,
        ),
        "measurement_method": Column(
            str,
            checks=Check.isin(MEASUREMENT_METHODS),
            nullable=False,
        ),
        "data_quality_tier": Column(
            str,
            checks=Check.isin(DATA_QUALITY_TIERS),
            nullable=False,
        ),
        "human_review_status": Column(
            str,
            checks=Check.isin(HUMAN_REVIEW_STATUSES),
            nullable=False,
        ),
        "notes": Column(str, nullable=True, required=False),
    },
    checks=[
        Check(_check_record_id_unique, name="unique_record_id"),
        Check(_check_valid_activity_dates, name="valid_activity_dates"),
        Check(_check_activity_date_order, name="activity_date_order"),
        Check(_check_unknown_requires_review, name="unknown_requires_review"),
        Check(_check_activity_other_notes, name="activity_other_notes"),
        Check(_check_unit_compatibility, name="unit_compatibility"),
        Check(_check_transport_payer_rules, name="transport_payer_rules"),
    ],
    strict=True,
    coerce=False,
)


def validate_source_documents(df: pd.DataFrame) -> pd.DataFrame:
    """Validate a source_documents DataFrame and return the validated result."""
    return SOURCE_DOCUMENTS_SCHEMA.validate(df)


def validate_activity_records(df: pd.DataFrame) -> pd.DataFrame:
    """Validate an activity_records DataFrame and return the validated result."""
    return ACTIVITY_RECORDS_SCHEMA.validate(df)
