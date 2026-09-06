"""Session-scoped purchased-steel confirmation overlays.

Confirmations supplement the current upload's accepted activities. They never
overwrite the original Excel bytes, never infer a method from the activity
name, and never apply across a different file, reporting year, or period.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

import pandas as pd

from carbon_ledger.activity_boundary_decisions import (
    period_id_for_decision,
    reporting_year_from_activity,
)
from carbon_ledger.intake import (
    READINESS_NEEDS_CONFIRM,
    READINESS_NO_MATCHING_FACTOR,
    classify_activity_ui_readiness,
    normalize_steel_calculation_method,
    normalize_steel_factor_boundary,
    normalize_uploaded_boolean,
)
from carbon_ledger.purchased_steel import (
    CONTROL_NOT_APPLICABLE,
    CONTROL_REPORTING_COMPANY,
    CONTROL_THIRD_PARTY,
    CONTROL_UNKNOWN,
    FACTOR_BOUNDARY_CRADLE_TO_GATE,
    METHOD_AVERAGE_DATA,
    METHOD_SUPPLIER_SPECIFIC,
    parse_emission_factor_unit,
    parse_factor_includes_tier1_transport,
    parse_tier1_transport_control,
    serialize_tri_state_bool,
)

METHOD_UNDECIDED = "undecided"
ALLOWED_METHODS = frozenset({METHOD_SUPPLIER_SPECIFIC, METHOD_AVERAGE_DATA})
STEEL_OVERLAY_FIELDS = (
    "calculation_method",
    "supplier_name",
    "steel_product_type",
    "product_identifier",
    "emission_factor_value",
    "emission_factor_unit",
    "factor_boundary",
    "factor_geography",
    "factor_year",
    "factor_source_id",
    "evidence_reference",
    "source_document_id",
    "technology",
    "includes_pre_tier1_supply_chain_transport",
    "includes_tier1_to_reporting_company_transport",
    "factor_includes_tier1_to_reporting_company_transport",
    "tier1_to_reporting_company_transport_control",
)

ERROR_METHOD_REQUIRED = "method_required"
ERROR_IDENTITY_INCOMPLETE = "identity_incomplete"
ERROR_FILE_HASH_REQUIRED = "file_hash_required"
ERROR_INBOUND_UNANSWERED = "inbound_transport_unanswered"
ERROR_TRANSPORT_CONTROL_UNANSWERED = "transport_control_unanswered"
ERROR_SUPPLIER_REQUIRED = "supplier_name_required"
ERROR_PRODUCT_REQUIRED = "product_required"
ERROR_FACTOR_VALUE_REQUIRED = "emission_factor_value_required"
ERROR_FACTOR_UNIT_REQUIRED = "emission_factor_unit_required"
ERROR_BOUNDARY_REQUIRED = "factor_boundary_required"
ERROR_FACTOR_YEAR_REQUIRED = "factor_year_required"
ERROR_EVIDENCE_REQUIRED = "evidence_required"
ERROR_GEOGRAPHY_REQUIRED = "factor_geography_required"
ERROR_REPORTING_YEAR_REQUIRED = "reporting_year_required"


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text.lower() in {"nan", "<na>", "none"}:
        return ""
    return text


def _canonical_method(value: Any) -> str:
    token = _text(value)
    if token == METHOD_UNDECIDED:
        return METHOD_UNDECIDED
    return normalize_steel_calculation_method(token)


def inclusion_from_mapping(raw: Mapping[str, Any]) -> str:
    """Prefer the factor-inclusion field; read the legacy flag conservatively."""
    parsed = parse_factor_includes_tier1_transport(raw)
    return serialize_tri_state_bool(parsed)


def _control_token(value: Any, *, inclusion: str) -> str:
    if inclusion == "false":
        return CONTROL_NOT_APPLICABLE
    control = parse_tier1_transport_control(value)
    if inclusion == "true" and control == CONTROL_NOT_APPLICABLE:
        return CONTROL_UNKNOWN
    if inclusion != "true" and control == CONTROL_NOT_APPLICABLE:
        return CONTROL_NOT_APPLICABLE
    return control


def is_blocked_transport_split(inclusion: str, control: str) -> bool:
    if inclusion != "true":
        return False
    return control in {CONTROL_THIRD_PARTY, CONTROL_REPORTING_COMPANY}


def confirmation_identity(
    file_hash: str,
    record_id: str,
    reporting_year: int,
    reporting_period_id: str,
) -> tuple[str, str, int, str]:
    """Bind one confirmation to one upload row and reporting period."""
    return (
        _text(file_hash),
        _text(record_id),
        int(reporting_year),
        _text(reporting_period_id),
    )


def activity_reporting_period_id(activity: Mapping[str, Any] | pd.Series) -> str:
    year = reporting_year_from_activity(activity)
    if year is None:
        return _text(activity.get("reporting_period_id"))
    return period_id_for_decision(
        reporting_period_id=_text(activity.get("reporting_period_id")),
        reporting_year=year,
    )


@dataclass(frozen=True)
class PurchasedSteelConfirmation:
    """Customer-supplied steel fields for one current-upload activity row."""

    file_hash: str
    record_id: str
    reporting_year: int
    reporting_period_id: str
    calculation_method: str = METHOD_UNDECIDED
    supplier_name: str = ""
    steel_product_type: str = ""
    product_identifier: str = ""
    emission_factor_value: str = ""
    emission_factor_unit: str = ""
    factor_boundary: str = ""
    factor_geography: str = ""
    factor_year: str = ""
    factor_source_id: str = ""
    evidence_reference: str = ""
    source_document_id: str = ""
    technology: str = ""
    includes_pre_tier1_supply_chain_transport: str = ""
    includes_tier1_to_reporting_company_transport: str = ""
    factor_includes_tier1_to_reporting_company_transport: str = ""
    tier1_to_reporting_company_transport_control: str = CONTROL_UNKNOWN

    def identity(self) -> tuple[str, str, int, str]:
        return confirmation_identity(
            self.file_hash,
            self.record_id,
            self.reporting_year,
            self.reporting_period_id,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reporting_year"] = int(self.reporting_year)
        payload["calculation_method"] = _canonical_method(self.calculation_method)
        payload["factor_boundary"] = normalize_steel_factor_boundary(
            self.factor_boundary
        )
        inclusion = inclusion_from_mapping(payload)
        control = _control_token(
            payload.get("tier1_to_reporting_company_transport_control"),
            inclusion=inclusion,
        )
        payload["factor_includes_tier1_to_reporting_company_transport"] = inclusion
        payload["includes_tier1_to_reporting_company_transport"] = inclusion
        payload["tier1_to_reporting_company_transport_control"] = control
        payload["includes_pre_tier1_supply_chain_transport"] = (
            normalize_uploaded_boolean(
                self.includes_pre_tier1_supply_chain_transport
            )
        )
        return payload

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> PurchasedSteelConfirmation:
        year = reporting_year_from_activity(
            {"reporting_year": raw.get("reporting_year")}
        )
        if year is None:
            raise ValueError("reporting_year is required")
        names = {item.name for item in fields(cls)}
        payload = {key: raw.get(key, "") for key in names}
        payload["file_hash"] = _text(raw.get("file_hash"))
        payload["record_id"] = _text(raw.get("record_id"))
        payload["reporting_year"] = year
        payload["reporting_period_id"] = _text(raw.get("reporting_period_id"))
        payload["calculation_method"] = _canonical_method(
            raw.get("calculation_method")
        )
        payload["factor_boundary"] = normalize_steel_factor_boundary(
            raw.get("factor_boundary")
        )
        inclusion = inclusion_from_mapping(raw)
        payload["factor_includes_tier1_to_reporting_company_transport"] = inclusion
        payload["includes_tier1_to_reporting_company_transport"] = inclusion
        payload["tier1_to_reporting_company_transport_control"] = _control_token(
            raw.get("tier1_to_reporting_company_transport_control"),
            inclusion=inclusion,
        )
        payload["includes_pre_tier1_supply_chain_transport"] = (
            normalize_uploaded_boolean(
                raw.get("includes_pre_tier1_supply_chain_transport")
            )
        )
        for key in names:
            if key in {
                "reporting_year",
                "calculation_method",
                "factor_boundary",
                "includes_pre_tier1_supply_chain_transport",
                "includes_tier1_to_reporting_company_transport",
                "factor_includes_tier1_to_reporting_company_transport",
                "tier1_to_reporting_company_transport_control",
            }:
                continue
            payload[key] = _text(payload.get(key))
        return cls(**payload)


def build_confirmation(
    *,
    file_hash: str,
    record_id: str,
    reporting_year: int,
    reporting_period_id: str = "",
    calculation_method: str = METHOD_UNDECIDED,
    supplier_name: str = "",
    steel_product_type: str = "",
    product_identifier: str = "",
    emission_factor_value: Any = "",
    emission_factor_unit: str = "",
    factor_boundary: str = "",
    factor_geography: str = "",
    factor_year: Any = "",
    factor_source_id: str = "",
    evidence_reference: str = "",
    source_document_id: str = "",
    technology: str = "",
    includes_pre_tier1_supply_chain_transport: Any = "",
    includes_tier1_to_reporting_company_transport: Any = "",
    factor_includes_tier1_to_reporting_company_transport: Any = "",
    tier1_to_reporting_company_transport_control: Any = "",
) -> PurchasedSteelConfirmation:
    period = period_id_for_decision(
        reporting_period_id=reporting_period_id,
        reporting_year=int(reporting_year),
    )
    return PurchasedSteelConfirmation.from_dict(
        {
            "file_hash": file_hash,
            "record_id": record_id,
            "reporting_year": reporting_year,
            "reporting_period_id": period,
            "calculation_method": calculation_method,
            "supplier_name": supplier_name,
            "steel_product_type": steel_product_type,
            "product_identifier": product_identifier,
            "emission_factor_value": emission_factor_value,
            "emission_factor_unit": emission_factor_unit,
            "factor_boundary": factor_boundary,
            "factor_geography": factor_geography,
            "factor_year": factor_year,
            "factor_source_id": factor_source_id,
            "evidence_reference": evidence_reference,
            "source_document_id": source_document_id,
            "technology": technology,
            "includes_pre_tier1_supply_chain_transport": (
                includes_pre_tier1_supply_chain_transport
            ),
            "includes_tier1_to_reporting_company_transport": (
                includes_tier1_to_reporting_company_transport
            ),
            "factor_includes_tier1_to_reporting_company_transport": (
                factor_includes_tier1_to_reporting_company_transport
                if _text(factor_includes_tier1_to_reporting_company_transport)
                or factor_includes_tier1_to_reporting_company_transport is False
                or factor_includes_tier1_to_reporting_company_transport is True
                else includes_tier1_to_reporting_company_transport
            ),
            "tier1_to_reporting_company_transport_control": (
                tier1_to_reporting_company_transport_control
            ),
        }
    )


def load_confirmations(
    raw: Iterable[Any] | None,
) -> list[PurchasedSteelConfirmation]:
    loaded: list[PurchasedSteelConfirmation] = []
    for item in raw or []:
        if isinstance(item, PurchasedSteelConfirmation):
            loaded.append(item)
            continue
        if isinstance(item, Mapping):
            try:
                loaded.append(PurchasedSteelConfirmation.from_dict(item))
            except (TypeError, ValueError):
                continue
    return latest_confirmations(loaded)


def latest_confirmations(
    confirmations: Iterable[PurchasedSteelConfirmation],
) -> list[PurchasedSteelConfirmation]:
    newest: dict[tuple[str, str, int, str], PurchasedSteelConfirmation] = {}
    for item in confirmations:
        newest[item.identity()] = item
    return list(newest.values())


def validate_confirmation(
    confirmation: PurchasedSteelConfirmation,
    *,
    current_file_hash: str,
) -> tuple[str, ...]:
    """Return blocking codes. Empty means the overlay may be saved."""
    errors: list[str] = []
    if not _text(confirmation.file_hash) or not _text(current_file_hash):
        errors.append(ERROR_FILE_HASH_REQUIRED)
    elif _text(confirmation.file_hash) != _text(current_file_hash):
        errors.append(ERROR_FILE_HASH_REQUIRED)
    if not _text(confirmation.record_id) or confirmation.reporting_year <= 0:
        errors.append(ERROR_IDENTITY_INCOMPLETE)
    if not _text(confirmation.reporting_period_id):
        errors.append(ERROR_IDENTITY_INCOMPLETE)
    method = _canonical_method(confirmation.calculation_method)
    if method not in ALLOWED_METHODS:
        errors.append(ERROR_METHOD_REQUIRED)
        return tuple(dict.fromkeys(errors))
    inclusion = inclusion_from_mapping(
        {
            "factor_includes_tier1_to_reporting_company_transport": (
                confirmation.factor_includes_tier1_to_reporting_company_transport
            ),
            "includes_tier1_to_reporting_company_transport": (
                confirmation.includes_tier1_to_reporting_company_transport
            ),
        }
    )
    if not inclusion:
        errors.append(ERROR_INBOUND_UNANSWERED)
    control = _control_token(
        confirmation.tier1_to_reporting_company_transport_control,
        inclusion=inclusion,
    )
    if inclusion == "true":
        if control in {CONTROL_UNKNOWN, CONTROL_NOT_APPLICABLE, ""}:
            errors.append(ERROR_TRANSPORT_CONTROL_UNANSWERED)
    if method == METHOD_AVERAGE_DATA:
        from carbon_ledger.cfp_p_02 import is_generic_steel_label

        if not _text(confirmation.steel_product_type) or is_generic_steel_label(
            confirmation.steel_product_type
        ):
            errors.append(ERROR_PRODUCT_REQUIRED)
        if reporting_year_from_activity(
            {"reporting_year": confirmation.reporting_year}
        ) is None:
            errors.append(ERROR_REPORTING_YEAR_REQUIRED)
        return tuple(dict.fromkeys(errors))
    from carbon_ledger.cfp_p_02 import is_generic_steel_label

    if not _text(confirmation.supplier_name):
        errors.append(ERROR_SUPPLIER_REQUIRED)
    product = _text(confirmation.steel_product_type)
    product_id = _text(confirmation.product_identifier)
    if (not product or is_generic_steel_label(product)) and not product_id:
        errors.append(ERROR_PRODUCT_REQUIRED)
    if normalize_steel_factor_boundary(confirmation.factor_boundary) != (
        FACTOR_BOUNDARY_CRADLE_TO_GATE
    ):
        errors.append(ERROR_BOUNDARY_REQUIRED)
    factor_value = _text(confirmation.emission_factor_value)
    try:
        parsed_factor = Decimal(factor_value)
    except (InvalidOperation, ValueError):
        parsed_factor = None
    if (
        parsed_factor is None
        or not parsed_factor.is_finite()
        or parsed_factor <= 0
    ):
        errors.append(ERROR_FACTOR_VALUE_REQUIRED)
    if parse_emission_factor_unit(confirmation.emission_factor_unit) is None:
        errors.append(ERROR_FACTOR_UNIT_REQUIRED)
    if reporting_year_from_activity(
        {"reporting_year": confirmation.factor_year}
    ) is None:
        errors.append(ERROR_FACTOR_YEAR_REQUIRED)
    if not (
        _text(confirmation.factor_source_id)
        or _text(confirmation.evidence_reference)
        or _text(confirmation.source_document_id)
    ):
        errors.append(ERROR_EVIDENCE_REQUIRED)
    return tuple(dict.fromkeys(errors))


def confirmation_matches_activity(
    confirmation: PurchasedSteelConfirmation,
    activity: Mapping[str, Any] | pd.Series,
    *,
    current_file_hash: str,
) -> bool:
    if _text(confirmation.file_hash) != _text(current_file_hash):
        return False
    if _text(confirmation.record_id) != _text(activity.get("record_id")):
        return False
    year = reporting_year_from_activity(activity)
    if year is None or year != int(confirmation.reporting_year):
        return False
    period = activity_reporting_period_id(activity)
    if period != _text(confirmation.reporting_period_id):
        return False
    return True


def _overlay_values(confirmation: PurchasedSteelConfirmation) -> dict[str, str]:
    method = _canonical_method(confirmation.calculation_method)
    inclusion = inclusion_from_mapping(
        {
            "factor_includes_tier1_to_reporting_company_transport": (
                confirmation.factor_includes_tier1_to_reporting_company_transport
            ),
            "includes_tier1_to_reporting_company_transport": (
                confirmation.includes_tier1_to_reporting_company_transport
            ),
        }
    )
    control = _control_token(
        confirmation.tier1_to_reporting_company_transport_control,
        inclusion=inclusion,
    )
    values = {
        "calculation_method": method if method in ALLOWED_METHODS else "",
        "factor_includes_tier1_to_reporting_company_transport": inclusion,
        "includes_tier1_to_reporting_company_transport": inclusion,
        "tier1_to_reporting_company_transport_control": control,
    }
    pre_tier1 = normalize_uploaded_boolean(
        confirmation.includes_pre_tier1_supply_chain_transport
    )
    if method == METHOD_AVERAGE_DATA:
        values.update(
            {
                "steel_product_type": _text(confirmation.steel_product_type),
                "product_identifier": _text(
                    confirmation.product_identifier
                    or confirmation.steel_product_type
                ),
                "factor_geography": _text(confirmation.factor_geography),
                "technology": _text(confirmation.technology),
                "emission_factor_value": "",
                "emission_factor_unit": "",
            }
        )
        return values
    values.update(
        {
            "supplier_name": _text(confirmation.supplier_name),
            "steel_product_type": _text(confirmation.steel_product_type),
            "product_identifier": _text(confirmation.product_identifier),
            "emission_factor_value": _text(confirmation.emission_factor_value),
            "emission_factor_unit": _text(confirmation.emission_factor_unit),
            "factor_boundary": normalize_steel_factor_boundary(
                confirmation.factor_boundary
            ),
            "factor_year": _text(confirmation.factor_year),
            "factor_source_id": _text(confirmation.factor_source_id),
            "evidence_reference": _text(confirmation.evidence_reference),
            "source_document_id": _text(confirmation.source_document_id),
            "factor_geography": _text(confirmation.factor_geography),
            "technology": _text(confirmation.technology),
            "includes_pre_tier1_supply_chain_transport": pre_tier1,
        }
    )
    return values


def apply_purchased_steel_confirmations(
    activities: pd.DataFrame,
    confirmations: Iterable[PurchasedSteelConfirmation],
    *,
    current_file_hash: str,
) -> pd.DataFrame:
    """Return a copy with matching current-upload steel overlays applied."""
    frame = activities.copy(deep=True)
    if frame.empty:
        return frame
    current = [
        item
        for item in latest_confirmations(confirmations)
        if not validate_confirmation(item, current_file_hash=current_file_hash)
        and _canonical_method(item.calculation_method) in ALLOWED_METHODS
    ]
    if not current:
        return frame
    for field_name in STEEL_OVERLAY_FIELDS:
        if field_name not in frame.columns:
            frame[field_name] = ""
    for index, row in frame.iterrows():
        if _text(row.get("activity_type")) != "purchased_steel":
            continue
        matched = next(
            (
                item
                for item in current
                if confirmation_matches_activity(
                    item, row, current_file_hash=current_file_hash
                )
            ),
            None,
        )
        if matched is None:
            continue
        for field_name, value in _overlay_values(matched).items():
            frame.at[index, field_name] = value
    return frame


def steel_confirmation_candidates(
    activities: pd.DataFrame,
    *,
    calculation_status_by_record: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Format-valid purchased-steel rows that still need a confirmation form.

    Includes incomplete rows and confirmed average-data / supplier-specific
    rows that have not calculated yet (including ``no_factor_configured``),
    so the user can switch method on the same identity.
    """
    if activities is None or getattr(activities, "empty", True):
        return pd.DataFrame()
    status_map = {
        str(key): str(value)
        for key, value in dict(calculation_status_by_record or {}).items()
    }
    rows = []
    for _, row in activities.iterrows():
        if _text(row.get("activity_type")) != "purchased_steel":
            continue
        record_id = _text(row.get("record_id"))
        calc_status = status_map.get(
            record_id, _text(row.get("calculation_status"))
        )
        readiness = classify_activity_ui_readiness(
            activity_type="purchased_steel",
            fuel_subtype=_text(row.get("fuel_subtype")),
            process_use=_text(row.get("process_use")),
            activity_start=row.get("activity_start_date"),
            activity_end=row.get("activity_end_date"),
            calculation_method=_text(row.get("calculation_method")),
            supplier_name=_text(row.get("supplier_name")),
            steel_product_type=_text(row.get("steel_product_type")),
            product_identifier=_text(row.get("product_identifier")),
            emission_factor_value=row.get("emission_factor_value"),
            emission_factor_unit=_text(row.get("emission_factor_unit")),
            factor_boundary=_text(row.get("factor_boundary")),
            factor_year=row.get("factor_year"),
            factor_source_id=_text(row.get("factor_source_id")),
            evidence_reference=_text(row.get("evidence_reference")),
            source_document_id=_text(row.get("source_document_id")),
            factor_includes_tier1_to_reporting_company_transport=row.get(
                "factor_includes_tier1_to_reporting_company_transport"
            ),
            includes_tier1_to_reporting_company_transport=row.get(
                "includes_tier1_to_reporting_company_transport"
            ),
            tier1_to_reporting_company_transport_control=row.get(
                "tier1_to_reporting_company_transport_control"
            ),
            factor_geography=_text(row.get("factor_geography")),
            calculation_status=calc_status,
        )
        method = _canonical_method(row.get("calculation_method"))
        keep = readiness in {
            READINESS_NEEDS_CONFIRM,
            READINESS_NO_MATCHING_FACTOR,
        }
        if method in ALLOWED_METHODS and calc_status != "calculated":
            keep = True
        if keep:
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=activities.columns)
    return pd.DataFrame(rows).reset_index(drop=True)
