"""Purchased-steel Scope 3 Category 1 calculation input and evidence model.

V1 supports two GHG Protocol Category 1 methods only:

- supplier_specific: supplier or product cradle-to-gate factor with provenance
- average_data: a registered, versioned secondary factor matched by product,
  year, and geography

This module does not invent a generic steel factor and does not treat
missing values as zero. Category 1 is the purchased-goods cradle-to-gate
result. Pre-Tier-1 supply-chain transport may already sit inside that
factor boundary. Tier 1 → reporting-company transport is classified by
who owns or controls the vehicle: third-party carriage needs a Category 4
split; company-controlled carriage needs a Scope 1 or 2 split. Blank
factor-inclusion flags are never treated as false.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from carbon_ledger.calculate import OUTPUT_COLUMNS
from carbon_ledger.cfp_p_02 import redact_api_key_from_url

FORMULA_ID = "purchased_mass_times_cradle_to_gate_factor"
FORMULA_VERSION = "1.0"
ACTIVITY_TYPE = "purchased_steel"
GHG_SCOPE = "scope_3"
SCOPE3_CATEGORY = "category_1_purchased_goods_and_services"
METHOD_SUPPLIER_SPECIFIC = "supplier_specific"
METHOD_AVERAGE_DATA = "average_data"
ALLOWED_CALCULATION_METHODS = frozenset(
    {METHOD_SUPPLIER_SPECIFIC, METHOD_AVERAGE_DATA}
)
FACTOR_BOUNDARY_CRADLE_TO_GATE = "cradle_to_gate"
ALLOWED_MASS_UNITS = frozenset({"kg", "t"})
ALLOWED_CO2E_NUMERATORS = frozenset({"kgCO2e", "tCO2e"})
READY_FACTOR_STATUS = "ready"
CANONICAL_MASS_UNIT = "t"
KG_PER_TONNE = Decimal("1000")

STATUS_CALCULATED = "calculated"
STATUS_NO_FACTOR_CONFIGURED = "no_factor_configured"
STATUS_NO_MATCHING_FACTOR = "no_matching_factor"
STATUS_BLOCKED_MISSING_RECORD_ID = "blocked_missing_record_id"
STATUS_BLOCKED_MISSING_METHOD = "blocked_missing_calculation_method"
STATUS_BLOCKED_UNSUPPORTED_METHOD = "blocked_unsupported_calculation_method"
STATUS_BLOCKED_MISSING_QUANTITY = "blocked_missing_quantity"
STATUS_BLOCKED_INVALID_QUANTITY = "blocked_invalid_quantity"
STATUS_BLOCKED_MISSING_UNIT = "blocked_missing_unit"
STATUS_BLOCKED_INCOMPATIBLE_UNIT = "blocked_incompatible_unit"
STATUS_BLOCKED_MISSING_SOURCE = "blocked_missing_source"
STATUS_BLOCKED_MISSING_EVIDENCE = "blocked_missing_evidence"
STATUS_BLOCKED_MISSING_SUPPLIER_OR_PRODUCT = (
    "blocked_missing_supplier_or_product"
)
STATUS_BLOCKED_MISSING_PRODUCT_TYPE = "blocked_missing_product_type"
STATUS_BLOCKED_INCOMPATIBLE_BOUNDARY = "blocked_incompatible_factor_boundary"
STATUS_BLOCKED_PRODUCT_MISMATCH = "blocked_product_mismatch"
STATUS_BLOCKED_INVALID_PERIOD = "blocked_invalid_reporting_period"
STATUS_BLOCKED_MISSING_GEOGRAPHY = "blocked_missing_factor_geography"
STATUS_BLOCKED_MISSING_FACTOR_YEAR = "blocked_missing_factor_year"
STATUS_BLOCKED_AMBIGUOUS_FACTOR = "blocked_ambiguous_factor"
STATUS_BLOCKED_TRANSPORT_NOT_CATEGORY_1 = "blocked_transport_not_category_1"
STATUS_BLOCKED_FACTOR_INCLUSION_UNCONFIRMED = (
    "blocked_factor_inclusion_unconfirmed"
)
STATUS_BLOCKED_TRANSPORT_CONTROL_UNCONFIRMED = (
    "blocked_transport_control_unconfirmed"
)
STATUS_BLOCKED_TIER1_INBOUND_REQUIRES_CATEGORY4_SPLIT = (
    "blocked_tier1_inbound_transport_requires_category4_split"
)
STATUS_BLOCKED_COMPANY_CONTROLLED_TRANSPORT_REQUIRES_SCOPE1_OR2_SPLIT = (
    "blocked_company_controlled_transport_requires_scope1_or2_split"
)
CONTROL_UNKNOWN = "unknown"
CONTROL_REPORTING_COMPANY = "reporting_company"
CONTROL_THIRD_PARTY = "third_party"
CONTROL_NOT_APPLICABLE = "not_applicable"
ALLOWED_TRANSPORT_CONTROLS = frozenset(
    {
        CONTROL_UNKNOWN,
        CONTROL_REPORTING_COMPANY,
        CONTROL_THIRD_PARTY,
        CONTROL_NOT_APPLICABLE,
    }
)
_INCLUSION_TRUE = frozenset(
    {
        "true",
        "1",
        "yes",
        "y",
        "included",
        "include",
        "包含",
        "是",
    }
)
_INCLUSION_FALSE = frozenset(
    {
        "false",
        "0",
        "no",
        "n",
        "excluded",
        "exclude",
        "不包含",
        "否",
    }
)
_CONTROL_ALIASES = {
    "unknown": CONTROL_UNKNOWN,
    "unconfirmed": CONTROL_UNKNOWN,
    "尚未確認": CONTROL_UNKNOWN,
    "reporting_company": CONTROL_REPORTING_COMPANY,
    "company": CONTROL_REPORTING_COMPANY,
    "本公司擁有或控制": CONTROL_REPORTING_COMPANY,
    "third_party": CONTROL_THIRD_PARTY,
    "third-party": CONTROL_THIRD_PARTY,
    "第三方擁有或控制": CONTROL_THIRD_PARTY,
    "not_applicable": CONTROL_NOT_APPLICABLE,
    "n/a": CONTROL_NOT_APPLICABLE,
    "na": CONTROL_NOT_APPLICABLE,
}

BLOCKED_STATUSES = frozenset(
    {
        STATUS_NO_FACTOR_CONFIGURED,
        STATUS_NO_MATCHING_FACTOR,
        STATUS_BLOCKED_MISSING_RECORD_ID,
        STATUS_BLOCKED_MISSING_METHOD,
        STATUS_BLOCKED_UNSUPPORTED_METHOD,
        STATUS_BLOCKED_MISSING_QUANTITY,
        STATUS_BLOCKED_INVALID_QUANTITY,
        STATUS_BLOCKED_MISSING_UNIT,
        STATUS_BLOCKED_INCOMPATIBLE_UNIT,
        STATUS_BLOCKED_MISSING_SOURCE,
        STATUS_BLOCKED_MISSING_EVIDENCE,
        STATUS_BLOCKED_MISSING_SUPPLIER_OR_PRODUCT,
        STATUS_BLOCKED_MISSING_PRODUCT_TYPE,
        STATUS_BLOCKED_INCOMPATIBLE_BOUNDARY,
        STATUS_BLOCKED_PRODUCT_MISMATCH,
        STATUS_BLOCKED_INVALID_PERIOD,
        STATUS_BLOCKED_MISSING_GEOGRAPHY,
        STATUS_BLOCKED_MISSING_FACTOR_YEAR,
        STATUS_BLOCKED_AMBIGUOUS_FACTOR,
        STATUS_BLOCKED_TRANSPORT_NOT_CATEGORY_1,
        STATUS_BLOCKED_FACTOR_INCLUSION_UNCONFIRMED,
        STATUS_BLOCKED_TRANSPORT_CONTROL_UNCONFIRMED,
        STATUS_BLOCKED_TIER1_INBOUND_REQUIRES_CATEGORY4_SPLIT,
        STATUS_BLOCKED_COMPANY_CONTROLLED_TRANSPORT_REQUIRES_SCOPE1_OR2_SPLIT,
    }
)


@dataclass(frozen=True)
class FactorUnit:
    numerator: str
    denominator: str

    @property
    def label(self) -> str:
        return f"{self.numerator}/{self.denominator}"


@dataclass(frozen=True)
class PurchasedSteelEvidence:
    """Typed Category 1 purchased-steel calculation input and evidence."""

    record_id: str = ""
    calculation_method: str = ""
    supplier_name: str = ""
    steel_product_type: str = ""
    purchased_quantity: Any = None
    purchased_unit: str = ""
    emission_factor_value: Any = None
    emission_factor_unit: str = ""
    factor_boundary: str = ""
    factor_geography: str = ""
    factor_year: Any = None
    factor_source_id: str = ""
    evidence_reference: str = ""
    reporting_year: Any = None
    reporting_period_id: str = ""
    source_document_id: str = ""
    record_type: str = ""
    activity_type: str = ACTIVITY_TYPE
    product_identifier: str = ""
    factor_includes_tier1_to_reporting_company_transport: bool | None = None
    tier1_to_reporting_company_transport_control: str = CONTROL_UNKNOWN
    includes_tier1_to_reporting_company_transport: bool | None = None
    includes_pre_tier1_supply_chain_transport: bool | None = None
    technology: str = ""


@dataclass(frozen=True)
class RegisteredSteelFactor:
    """A versioned secondary steel factor. Never inferred from a constant."""

    factor_id: str
    steel_product_type: str
    factor_value: Decimal
    factor_unit: FactorUnit
    factor_boundary: str
    factor_geography: str
    factor_year: int
    factor_source_id: str
    factor_status: str
    factor_version: str = ""
    valid_from: str = ""
    valid_to: str = ""
    includes_pre_tier1_supply_chain_transport: bool | None = None
    technology: str = ""
    approved_for_reporting_from: str = ""
    approved_for_reporting_to: str = ""
    source_record_id: str = ""
    source_url: str = ""
    snapshot_hash: str = ""
    is_secondary_or_proxy: str = ""
    announcement_year: str = ""
    official_name: str = ""
    publisher: str = ""
    retrieved_at: str = ""


@dataclass(frozen=True)
class PurchasedSteelValidationIssue:
    code: str
    message: str
    field: str = ""


@dataclass(frozen=True)
class PurchasedSteelCalculationResult:
    """Typed result aligned with calculation OUTPUT_COLUMNS plus steel fields."""

    calculation_id: str
    record_id: str
    activity_type: str
    normalized_value: float | None
    normalized_unit: str
    calculated_kgco2e: float | None
    calculated_tco2e: float | None
    calculation_status: str
    calculation_reason: str
    formula_id: str
    formula_version: str
    factor_id: str
    factor_value: float | None
    factor_numerator_unit: str
    factor_denominator_unit: str
    source_reference_id: str
    calculation_method: str
    supplier_name: str
    steel_product_type: str
    factor_boundary: str
    factor_geography: str
    factor_year: int | None
    evidence_reference: str
    reporting_year: int | None
    reporting_period_id: str
    ghg_scope: str
    scope3_category: str
    calculation_trace: str
    product_identifier: str = ""
    purchased_quantity: Any = None
    purchased_unit: str = ""
    source_document_id: str = ""
    factor_source_id: str = ""
    factor_version: str = ""
    source_record_id: str = ""
    source_url: str = ""
    snapshot_hash: str = ""
    match_reason: str = ""
    approved_for_reporting_from: str = ""
    approved_for_reporting_to: str = ""
    technology: str = ""
    official_name: str = ""
    publisher: str = ""
    announcement_year: str = ""
    retrieved_at: str = ""

    def to_calculation_row(self) -> dict[str, Any]:
        row = {column: pd.NA for column in OUTPUT_COLUMNS}
        row.update(
            {
                "calculation_id": self.calculation_id,
                "record_id": self.record_id,
                "activity_type": self.activity_type,
                "normalized_value": _optional_number(self.normalized_value),
                "normalized_unit": self.normalized_unit or pd.NA,
                "factor_id": self.factor_id or pd.NA,
                "factor_value": _optional_number(self.factor_value),
                "factor_numerator_unit": self.factor_numerator_unit or pd.NA,
                "factor_denominator_unit": self.factor_denominator_unit or pd.NA,
                "source_reference_id": self.source_reference_id or pd.NA,
                "formula_id": self.formula_id or pd.NA,
                "formula_version": self.formula_version or pd.NA,
                "calculation_trace": self.calculation_trace or pd.NA,
                "calculated_kgco2e": _optional_number(self.calculated_kgco2e),
                "calculated_tco2e": _optional_number(self.calculated_tco2e),
                "calculation_status": self.calculation_status,
                "calculation_reason": self.calculation_reason,
                "calculation_method": self.calculation_method,
                "supplier_name": self.supplier_name,
                "steel_product_type": self.steel_product_type,
                "product_identifier": self.product_identifier,
                "purchased_quantity": self.purchased_quantity
                if self.purchased_quantity is not None
                else pd.NA,
                "purchased_unit": self.purchased_unit or pd.NA,
                "factor_boundary": self.factor_boundary,
                "factor_geography": self.factor_geography,
                "factor_year": self.factor_year
                if self.factor_year is not None
                else pd.NA,
                "factor_source_id": self.factor_source_id
                or self.source_reference_id
                or pd.NA,
                "evidence_reference": self.evidence_reference,
                "source_document_id": self.source_document_id or pd.NA,
                "reporting_year": self.reporting_year
                if self.reporting_year is not None
                else pd.NA,
                "reporting_period_id": self.reporting_period_id,
                "ghg_scope": self.ghg_scope,
                "scope3_category": self.scope3_category,
                "scope_3_category": "category_1",
                "factor_version": self.factor_version or pd.NA,
                "source_record_id": self.source_record_id or pd.NA,
                "source_url": self.source_url or pd.NA,
                "snapshot_hash": self.snapshot_hash or pd.NA,
                "match_reason": self.match_reason or pd.NA,
                "approved_for_reporting_from": (
                    self.approved_for_reporting_from or pd.NA
                ),
                "approved_for_reporting_to": (
                    self.approved_for_reporting_to or pd.NA
                ),
                "technology": self.technology or pd.NA,
                "official_name": self.official_name or self.steel_product_type or pd.NA,
                "publisher": self.publisher or pd.NA,
                "announcement_year": self.announcement_year or pd.NA,
                "retrieved_at": self.retrieved_at or pd.NA,
            }
        )
        return row


def _optional_number(value: float | None) -> Any:
    if value is None:
        return pd.NA
    return value


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


def _is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    return _text(value).lower() in {"true", "1", "yes", "是"}


def serialize_tri_state_bool(value: bool | None) -> str:
    """Canonical overlay token. Unknown stays blank, never false."""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def parse_tri_state_bool(value: Any) -> bool | None:
    """Return True/False only for explicit values. Blank stays unknown."""
    if value is True:
        return True
    if value is False:
        return False
    text = _text(value)
    if not text:
        return None
    token = text.casefold()
    if text in _INCLUSION_TRUE or token in _INCLUSION_TRUE:
        return True
    if text in _INCLUSION_FALSE or token in _INCLUSION_FALSE:
        return False
    return None


def parse_tier1_transport_control(value: Any) -> str:
    """Canonical control code. Unknown tokens stay unknown, never inferred."""
    text = _text(value)
    if not text:
        return CONTROL_UNKNOWN
    direct = _CONTROL_ALIASES.get(text)
    if direct:
        return direct
    return _CONTROL_ALIASES.get(text.casefold(), CONTROL_UNKNOWN)


def parse_factor_includes_tier1_transport(record: Mapping[str, Any]) -> bool | None:
    """Prefer the factor-inclusion field; read the legacy flag conservatively."""
    if "factor_includes_tier1_to_reporting_company_transport" in record:
        parsed = parse_tri_state_bool(
            record.get("factor_includes_tier1_to_reporting_company_transport")
        )
        if parsed is not None:
            return parsed
        if _text(record.get("factor_includes_tier1_to_reporting_company_transport")):
            return None
    if "includes_tier1_to_reporting_company_transport" in record:
        return parse_tri_state_bool(
            record.get("includes_tier1_to_reporting_company_transport")
        )
    return parse_tri_state_bool(
        record.get("factor_includes_tier1_to_reporting_company_transport")
    )


def _coerce_year(value: Any) -> int | None:
    if _is_blank(value):
        return None
    try:
        if isinstance(value, bool) or pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not number.is_finite() or number != number.to_integral_value():
        return None
    year = int(number)
    if 1900 <= year <= 2100:
        return year
    return None


def _parse_optional_date(value: Any) -> date | None | str:
    """Return a date, None if blank, or ``'invalid'`` if present but unparseable."""
    if _is_blank(value):
        return None
    parsed = pd.to_datetime(_text(value), errors="coerce")
    if pd.isna(parsed):
        return "invalid"
    stamp = pd.Timestamp(parsed)
    return date(int(stamp.year), int(stamp.month), int(stamp.day))


def _parse_positive_decimal(value: Any) -> Decimal | None | str:
    """Return Decimal, None if blank, or 'invalid' for non-positive/non-finite."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "invalid"
    if isinstance(value, float) and not math.isfinite(value):
        return "invalid"
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = _text(value)
    if not text:
        return None
    lowered = text.lower()
    if lowered in {"nan", "inf", "+inf", "-inf", "infinity", "-infinity"}:
        return "invalid"
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return "invalid"
    if not number.is_finite() or number <= 0:
        return "invalid"
    return number


def _decimal_to_float(value: Decimal) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite purchased-steel calculation output")
    return number


def parse_emission_factor_unit(raw: Any) -> FactorUnit | None:
    """Parse an explicit cradle-to-gate factor unit. Unknown units are not guessed."""
    token = _text(raw).replace(" per ", "/").replace(" ", "")
    if "/" not in token:
        return None
    numerator, denominator = token.split("/", 1)
    if numerator not in ALLOWED_CO2E_NUMERATORS:
        return None
    if denominator not in ALLOWED_MASS_UNITS:
        return None
    return FactorUnit(numerator=numerator, denominator=denominator)


def mass_to_canonical_tonnes(quantity: Decimal, unit: str) -> Decimal | None:
    if unit == "t":
        return quantity
    if unit == "kg":
        return quantity / KG_PER_TONNE
    return None


def _mass_in_denominator(
    quantity: Decimal, purchased_unit: str, denominator: str
) -> Decimal | None:
    if purchased_unit == denominator:
        return quantity
    if purchased_unit == "t" and denominator == "kg":
        return quantity * KG_PER_TONNE
    if purchased_unit == "kg" and denominator == "t":
        return quantity / KG_PER_TONNE
    return None


def _kgco2e_from_factor(
    quantity_in_denominator: Decimal, factor_value: Decimal, numerator: str
) -> Decimal | None:
    raw = quantity_in_denominator * factor_value
    if numerator == "kgCO2e":
        return raw
    if numerator == "tCO2e":
        return raw * KG_PER_TONNE
    return None


def parse_purchased_steel_evidence(
    record: Mapping[str, Any],
) -> PurchasedSteelEvidence:
    """Build typed evidence from a mapping. Missing fields stay blank."""
    quantity = record.get("purchased_quantity")
    if _is_blank(quantity):
        quantity = record.get("activity_value")
    unit = _text(record.get("purchased_unit") or record.get("unit"))
    evidence_reference = _text(
        record.get("evidence_reference")
        or record.get("source_locator")
        or record.get("source_reference")
    )
    factor_source_id = _text(
        record.get("factor_source_id") or record.get("source_reference_id")
    )
    activity_type = _text(record.get("activity_type")) or ACTIVITY_TYPE
    record_type = _text(record.get("record_type"))
    inclusion = parse_factor_includes_tier1_transport(record)
    control = parse_tier1_transport_control(
        record.get("tier1_to_reporting_company_transport_control")
    )
    if inclusion is False:
        control = CONTROL_NOT_APPLICABLE
    elif inclusion is True and control == CONTROL_NOT_APPLICABLE:
        control = CONTROL_UNKNOWN
    pre_tier1 = parse_tri_state_bool(
        record.get("includes_pre_tier1_supply_chain_transport")
    )
    if pre_tier1 is None and _is_true(record.get("includes_tier2_to_tier1_transport")):
        pre_tier1 = True
    return PurchasedSteelEvidence(
        record_id=_text(record.get("record_id")),
        calculation_method=_text(record.get("calculation_method")),
        supplier_name=_text(record.get("supplier_name")),
        steel_product_type=_text(record.get("steel_product_type")),
        purchased_quantity=quantity,
        purchased_unit=unit,
        emission_factor_value=record.get("emission_factor_value"),
        emission_factor_unit=_text(record.get("emission_factor_unit")),
        factor_boundary=_text(record.get("factor_boundary")),
        factor_geography=_text(record.get("factor_geography")),
        factor_year=record.get("factor_year"),
        factor_source_id=factor_source_id,
        evidence_reference=evidence_reference,
        reporting_year=record.get("reporting_year"),
        reporting_period_id=_text(record.get("reporting_period_id")),
        source_document_id=_text(record.get("source_document_id")),
        record_type=record_type,
        activity_type=activity_type,
        product_identifier=_text(
            record.get("product_identifier") or record.get("product_id")
        ),
        factor_includes_tier1_to_reporting_company_transport=inclusion,
        tier1_to_reporting_company_transport_control=control,
        includes_tier1_to_reporting_company_transport=inclusion,
        includes_pre_tier1_supply_chain_transport=pre_tier1,
        technology=_text(record.get("technology") or record.get("process")),
    )


def registered_steel_factors_from_frame(
    frame: pd.DataFrame | None,
) -> tuple[RegisteredSteelFactor, ...]:
    """Keep only complete, ready purchased-steel secondary factors.

    Rows missing product type, year, geography, version, source, or
    cradle-to-gate boundary are skipped rather than repaired.
    """
    if frame is None or frame.empty:
        return ()
    if "activity_type" not in frame.columns:
        return ()
    parsed: list[RegisteredSteelFactor] = []
    for row in frame.to_dict(orient="records"):
        if _text(row.get("activity_type")) != ACTIVITY_TYPE:
            continue
        if _text(row.get("factor_status")) != READY_FACTOR_STATUS:
            continue
        factor_id = _text(row.get("factor_id"))
        product_type = _text(row.get("steel_product_type"))
        geography = _text(row.get("geography") or row.get("factor_geography"))
        source_id = _text(
            row.get("source_reference_id") or row.get("factor_source_id")
        )
        boundary = _text(row.get("factor_boundary"))
        year = _coerce_year(row.get("factor_year"))
        version = _text(row.get("factor_version")) or factor_id
        factor_value = _parse_positive_decimal(row.get("factor_value"))
        unit = parse_emission_factor_unit(row.get("emission_factor_unit"))
        if unit is None:
            numerator = _text(row.get("numerator_unit"))
            denominator = _text(row.get("denominator_unit"))
            if (
                numerator in ALLOWED_CO2E_NUMERATORS
                and denominator in ALLOWED_MASS_UNITS
            ):
                unit = FactorUnit(numerator=numerator, denominator=denominator)
        if (
            not factor_id
            or not product_type
            or not geography
            or not source_id
            or not version
            or year is None
            or boundary != FACTOR_BOUNDARY_CRADLE_TO_GATE
            or not isinstance(factor_value, Decimal)
            or unit is None
        ):
            continue
        parsed.append(
            RegisteredSteelFactor(
                factor_id=factor_id,
                steel_product_type=product_type,
                factor_value=factor_value,
                factor_unit=unit,
                factor_boundary=boundary,
                factor_geography=geography,
                factor_year=year,
                factor_source_id=source_id,
                factor_status=READY_FACTOR_STATUS,
                factor_version=version,
                valid_from=_text(row.get("valid_from")),
                valid_to=_text(row.get("valid_to")),
                includes_pre_tier1_supply_chain_transport=parse_tri_state_bool(
                    row.get("includes_pre_tier1_supply_chain_transport")
                ),
                technology=_text(row.get("technology") or row.get("process")),
                approved_for_reporting_from=_text(
                    row.get("approved_for_reporting_from")
                ),
                approved_for_reporting_to=_text(
                    row.get("approved_for_reporting_to")
                ),
                source_record_id=_text(row.get("source_record_id")),
                source_url=redact_api_key_from_url(
                    _text(row.get("source_url") or row.get("source_locator"))
                ),
                snapshot_hash=_text(
                    row.get("snapshot_hash") or row.get("source_sha256")
                ),
                is_secondary_or_proxy=_text(row.get("is_secondary_or_proxy"))
                or "true",
                announcement_year=_text(
                    row.get("announcement_year") or row.get("official_announcementyear")
                ),
                official_name=_text(
                    row.get("official_name") or row.get("steel_product_type")
                ),
                publisher=_text(
                    row.get("publisher") or row.get("official_departmentname")
                ),
                retrieved_at=_text(row.get("retrieved_at")),
            )
        )
    return tuple(parsed)


def _factor_covers_reporting_year(
    factor: RegisteredSteelFactor, reporting_year: int
) -> bool:
    """Return True only when internally approved applicability covers the year.

    Official announcementyear is never used as coverage. Prefer
    ``approved_for_reporting_from`` / ``approved_for_reporting_to``. Fall back
    to registry ``valid_from`` / ``valid_to`` only for already-reviewed test
    rows that stored coverage there. A blank end date is open-ended only when
    the start date is present and internally approved.
    """
    year_start = date(reporting_year, 1, 1)
    year_end = date(reporting_year, 12, 31)
    start_text = factor.approved_for_reporting_from or factor.valid_from
    end_text = factor.approved_for_reporting_to or factor.valid_to
    valid_from = _parse_optional_date(start_text)
    if (
        valid_from is None
        or valid_from == "invalid"
        or not isinstance(valid_from, date)
        or valid_from > year_start
    ):
        return False
    valid_to = _parse_optional_date(end_text)
    if valid_to == "invalid":
        return False
    if valid_to is None:
        return True
    if not isinstance(valid_to, date):
        return False
    return valid_to >= year_end


def match_average_data_factor(
    evidence: PurchasedSteelEvidence,
    registered_factors: Sequence[RegisteredSteelFactor],
    *,
    reporting_year: int,
) -> tuple[RegisteredSteelFactor | None, str]:
    """Match one registered secondary factor. Do not pick a fallback version."""
    from carbon_ledger.cfp_p_02 import is_generic_steel_label

    product_type = evidence.steel_product_type
    if is_generic_steel_label(product_type):
        return None, STATUS_BLOCKED_MISSING_PRODUCT_TYPE
    geography = evidence.factor_geography
    technology = _text(evidence.technology)
    matches = [
        factor
        for factor in registered_factors
        if (
            factor.steel_product_type == product_type
            or factor.official_name == product_type
        )
        and factor.factor_geography == geography
        and _factor_covers_reporting_year(factor, reporting_year)
        and (
            not factor.technology
            or factor.technology == technology
        )
        and factor.factor_boundary == FACTOR_BOUNDARY_CRADLE_TO_GATE
        and factor.factor_unit.numerator in ALLOWED_CO2E_NUMERATORS
        and factor.factor_unit.denominator in ALLOWED_MASS_UNITS
    ]
    if not matches:
        return None, STATUS_NO_MATCHING_FACTOR
    if len(matches) > 1:
        return None, STATUS_BLOCKED_AMBIGUOUS_FACTOR
    return matches[0], ""


def _is_standalone_transport_record(evidence: PurchasedSteelEvidence) -> bool:
    return (
        evidence.activity_type == "third_party_transport"
        or evidence.record_type == "transport_activity"
    )


def _standalone_transport_status(
    evidence: PurchasedSteelEvidence,
) -> tuple[str, str, str] | None:
    if not _is_standalone_transport_record(evidence):
        return None
    return (
        STATUS_BLOCKED_TRANSPORT_NOT_CATEGORY_1,
        (
            "A standalone third-party transport record is not Scope 3 "
            "Category 1 purchased steel."
        ),
        "activity_type",
    )


def _factor_transport_split_status(
    evidence: PurchasedSteelEvidence,
) -> tuple[str, str, str] | None:
    """Return (status, message, field) when the factor boundary blocks Category 1."""
    inclusion = evidence.factor_includes_tier1_to_reporting_company_transport
    if inclusion is None:
        inclusion = evidence.includes_tier1_to_reporting_company_transport
    if inclusion is None:
        return (
            STATUS_BLOCKED_FACTOR_INCLUSION_UNCONFIRMED,
            (
                "Confirm whether the emission factor includes Tier 1 "
                "supplier to reporting-company transport before calculating "
                "Category 1. Blank values are not treated as excluded."
            ),
            "factor_includes_tier1_to_reporting_company_transport",
        )
    if inclusion is False:
        return None
    control = parse_tier1_transport_control(
        evidence.tier1_to_reporting_company_transport_control
    )
    if control in {CONTROL_UNKNOWN, CONTROL_NOT_APPLICABLE, ""}:
        return (
            STATUS_BLOCKED_TRANSPORT_CONTROL_UNCONFIRMED,
            (
                "The factor includes Tier 1 to reporting-company transport, "
                "but vehicle ownership/control is not confirmed. Category 1 "
                "is not calculated and Category 4 is not inferred."
            ),
            "tier1_to_reporting_company_transport_control",
        )
    if control == CONTROL_THIRD_PARTY:
        return (
            STATUS_BLOCKED_TIER1_INBOUND_REQUIRES_CATEGORY4_SPLIT,
            (
                "The factor includes third-party Tier 1 supplier to "
                "reporting-company transport. That leg belongs in Scope 3 "
                "Category 4. Category 1 is not calculated until a factor "
                "without that leg, or a split, is available."
            ),
            "tier1_to_reporting_company_transport_control",
        )
    if control == CONTROL_REPORTING_COMPANY:
        return (
            STATUS_BLOCKED_COMPANY_CONTROLLED_TRANSPORT_REQUIRES_SCOPE1_OR2_SPLIT,
            (
                "The factor includes reporting-company owned or controlled "
                "transport. That leg belongs in Scope 1 or Scope 2 by energy "
                "source. Category 1 is not calculated until a factor without "
                "that leg, or a split, is available."
            ),
            "tier1_to_reporting_company_transport_control",
        )
    return (
        STATUS_BLOCKED_TRANSPORT_CONTROL_UNCONFIRMED,
        (
            "The factor includes Tier 1 to reporting-company transport, "
            "but vehicle ownership/control is not confirmed."
        ),
        "tier1_to_reporting_company_transport_control",
    )


def validate_purchased_steel_evidence(
    evidence: PurchasedSteelEvidence,
    *,
    registered_factors: Sequence[RegisteredSteelFactor] = (),
) -> tuple[str, tuple[PurchasedSteelValidationIssue, ...]]:
    """Return the blocking status and issues. Calculated inputs return empty issues."""
    issues: list[PurchasedSteelValidationIssue] = []

    def add(code: str, message: str, field: str = "") -> None:
        issues.append(
            PurchasedSteelValidationIssue(code=code, message=message, field=field)
        )

    if not evidence.record_id:
        add(
            STATUS_BLOCKED_MISSING_RECORD_ID,
            "record_id is required before a Category 1 steel calculation.",
            "record_id",
        )
        return STATUS_BLOCKED_MISSING_RECORD_ID, tuple(issues)

    standalone = _standalone_transport_status(evidence)
    if standalone is not None:
        status, message, field = standalone
        add(status, message, field)
        return status, tuple(issues)

    method = evidence.calculation_method
    if not method:
        add(
            STATUS_NO_FACTOR_CONFIGURED,
            (
                "calculation_method is required. V1 allows supplier_specific "
                "or average_data only; no generic steel factor is applied."
            ),
            "calculation_method",
        )
        return STATUS_NO_FACTOR_CONFIGURED, tuple(issues)
    if method not in ALLOWED_CALCULATION_METHODS:
        add(
            STATUS_BLOCKED_UNSUPPORTED_METHOD,
            (
                f"calculation_method {method!r} is not allowed. V1 allows "
                "supplier_specific or average_data only."
            ),
            "calculation_method",
        )
        return STATUS_BLOCKED_UNSUPPORTED_METHOD, tuple(issues)

    split = _factor_transport_split_status(evidence)
    if split is not None:
        status, message, field = split
        add(status, message, field)
        return status, tuple(issues)

    reporting_year = _coerce_year(evidence.reporting_year)
    if reporting_year is None:
        add(
            STATUS_BLOCKED_INVALID_PERIOD,
            (
                "A valid reporting_year is required; a reporting_period_id "
                "alone is not enough."
            ),
            "reporting_year",
        )
        return STATUS_BLOCKED_INVALID_PERIOD, tuple(issues)

    quantity = _parse_positive_decimal(evidence.purchased_quantity)
    if quantity is None:
        add(
            STATUS_BLOCKED_MISSING_QUANTITY,
            "purchased_quantity is required and must be greater than zero.",
            "purchased_quantity",
        )
        return STATUS_BLOCKED_MISSING_QUANTITY, tuple(issues)
    if quantity == "invalid":
        add(
            STATUS_BLOCKED_INVALID_QUANTITY,
            "purchased_quantity is negative, zero, non-finite, or not a number.",
            "purchased_quantity",
        )
        return STATUS_BLOCKED_INVALID_QUANTITY, tuple(issues)

    unit = evidence.purchased_unit
    if not unit:
        add(
            STATUS_BLOCKED_MISSING_UNIT,
            "purchased_unit is required (kg or t).",
            "purchased_unit",
        )
        return STATUS_BLOCKED_MISSING_UNIT, tuple(issues)
    if unit not in ALLOWED_MASS_UNITS:
        add(
            STATUS_BLOCKED_INCOMPATIBLE_UNIT,
            f"purchased_unit {unit!r} is not a supported steel mass unit.",
            "purchased_unit",
        )
        return STATUS_BLOCKED_INCOMPATIBLE_UNIT, tuple(issues)

    if method == METHOD_SUPPLIER_SPECIFIC:
        return _validate_supplier_specific(evidence, issues)
    return _validate_average_data(
        evidence, registered_factors, reporting_year, issues
    )


def _validate_supplier_specific(
    evidence: PurchasedSteelEvidence,
    issues: list[PurchasedSteelValidationIssue],
) -> tuple[str, tuple[PurchasedSteelValidationIssue, ...]]:
    def add(code: str, message: str, field: str = "") -> None:
        issues.append(
            PurchasedSteelValidationIssue(code=code, message=message, field=field)
        )

    if not evidence.supplier_name:
        add(
            STATUS_BLOCKED_MISSING_SUPPLIER_OR_PRODUCT,
            (
                "supplier_specific requires supplier_name. A product type "
                "alone is not enough."
            ),
            "supplier_name",
        )
        return STATUS_BLOCKED_MISSING_SUPPLIER_OR_PRODUCT, tuple(issues)
    if not evidence.steel_product_type and not evidence.product_identifier:
        add(
            STATUS_BLOCKED_MISSING_PRODUCT_TYPE,
            (
                "supplier_specific requires steel_product_type or an explicit "
                "product identifier."
            ),
            "steel_product_type",
        )
        return STATUS_BLOCKED_MISSING_PRODUCT_TYPE, tuple(issues)

    factor_year = _coerce_year(evidence.factor_year)
    if factor_year is None:
        add(
            STATUS_BLOCKED_MISSING_FACTOR_YEAR,
            (
                "supplier_specific requires factor_year as the coefficient "
                "data year. reporting_year is not substituted."
            ),
            "factor_year",
        )
        return STATUS_BLOCKED_MISSING_FACTOR_YEAR, tuple(issues)

    if evidence.factor_boundary != FACTOR_BOUNDARY_CRADLE_TO_GATE:
        add(
            STATUS_BLOCKED_INCOMPATIBLE_BOUNDARY,
            (
                "supplier_specific requires an explicit cradle-to-gate "
                "factor_boundary. Gate-to-gate is not a Category 1 steel "
                "factor. Pre-Tier-1 supply-chain transport may already be "
                "inside a cradle-to-gate factor."
            ),
            "factor_boundary",
        )
        return STATUS_BLOCKED_INCOMPATIBLE_BOUNDARY, tuple(issues)

    factor_value = _parse_positive_decimal(evidence.emission_factor_value)
    if factor_value is None:
        add(
            STATUS_NO_FACTOR_CONFIGURED,
            (
                "supplier_specific requires a cradle-to-gate "
                "emission_factor_value. Missing factors are not treated as 0."
            ),
            "emission_factor_value",
        )
        return STATUS_NO_FACTOR_CONFIGURED, tuple(issues)
    if factor_value == "invalid":
        add(
            STATUS_NO_FACTOR_CONFIGURED,
            "emission_factor_value must be a finite number greater than zero.",
            "emission_factor_value",
        )
        return STATUS_NO_FACTOR_CONFIGURED, tuple(issues)

    factor_unit = parse_emission_factor_unit(evidence.emission_factor_unit)
    if factor_unit is None:
        add(
            STATUS_BLOCKED_MISSING_UNIT
            if not evidence.emission_factor_unit
            else STATUS_BLOCKED_INCOMPATIBLE_UNIT,
            (
                "supplier_specific requires an explicit emission_factor_unit "
                "such as kgCO2e/t."
            ),
            "emission_factor_unit",
        )
        return (
            STATUS_BLOCKED_MISSING_UNIT
            if not evidence.emission_factor_unit
            else STATUS_BLOCKED_INCOMPATIBLE_UNIT
        ), tuple(issues)

    if (
        not evidence.factor_source_id
        and not evidence.evidence_reference
        and not evidence.source_document_id
    ):
        add(
            STATUS_BLOCKED_MISSING_SOURCE,
            (
                "supplier_specific requires factor_source_id, "
                "evidence_reference, or source_document_id."
            ),
            "factor_source_id",
        )
        return STATUS_BLOCKED_MISSING_SOURCE, tuple(issues)

    return STATUS_CALCULATED, ()


def _validate_average_data(
    evidence: PurchasedSteelEvidence,
    registered_factors: Sequence[RegisteredSteelFactor],
    reporting_year: int,
    issues: list[PurchasedSteelValidationIssue],
) -> tuple[str, tuple[PurchasedSteelValidationIssue, ...]]:
    def add(code: str, message: str, field: str = "") -> None:
        issues.append(
            PurchasedSteelValidationIssue(code=code, message=message, field=field)
        )

    from carbon_ledger.cfp_p_02 import is_generic_steel_label

    if not evidence.steel_product_type or is_generic_steel_label(
        evidence.steel_product_type
    ):
        add(
            STATUS_BLOCKED_MISSING_PRODUCT_TYPE,
            "average_data requires an exact steel_product_type. "
            "Generic labels such as 採購鋼材 are not matched.",
            "steel_product_type",
        )
        return STATUS_BLOCKED_MISSING_PRODUCT_TYPE, tuple(issues)
    if not evidence.factor_geography:
        add(
            STATUS_BLOCKED_MISSING_GEOGRAPHY,
            "average_data requires factor_geography. Geography is not inferred.",
            "factor_geography",
        )
        return STATUS_BLOCKED_MISSING_GEOGRAPHY, tuple(issues)

    matched, match_status = match_average_data_factor(
        evidence, registered_factors, reporting_year=reporting_year
    )
    if matched is None:
        if match_status == STATUS_BLOCKED_PRODUCT_MISMATCH:
            add(
                STATUS_BLOCKED_PRODUCT_MISMATCH,
                (
                    "No registered secondary factor matches steel_product_type "
                    f"{evidence.steel_product_type!r}."
                ),
                "steel_product_type",
            )
            return STATUS_BLOCKED_PRODUCT_MISMATCH, tuple(issues)
        if match_status == STATUS_BLOCKED_AMBIGUOUS_FACTOR:
            add(
                STATUS_BLOCKED_AMBIGUOUS_FACTOR,
                (
                    "Multiple registered secondary factors match this product, "
                    "year, and geography. Newest is not selected."
                ),
                "factor_source_id",
            )
            return STATUS_BLOCKED_AMBIGUOUS_FACTOR, tuple(issues)
        if match_status == STATUS_BLOCKED_MISSING_PRODUCT_TYPE:
            add(
                STATUS_BLOCKED_MISSING_PRODUCT_TYPE,
                "Generic activity names such as 採購鋼材 are not a product type.",
                "steel_product_type",
            )
            return STATUS_BLOCKED_MISSING_PRODUCT_TYPE, tuple(issues)
        add(
            STATUS_NO_MATCHING_FACTOR,
            (
                "No unique approved average-data factor matches this product, "
                "process, geography, cradle-to-gate boundary, and approved "
                "reporting period. Newest announcement is not selected."
            ),
            "emission_factor_value",
        )
        return STATUS_NO_MATCHING_FACTOR, tuple(issues)
    return STATUS_CALCULATED, ()


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (pd.Timestamp, date)):
        return str(value)
    return value


def _transport_trace_fields(evidence: PurchasedSteelEvidence) -> dict[str, Any]:
    return {
        "factor_includes_tier1_to_reporting_company_transport": (
            evidence.factor_includes_tier1_to_reporting_company_transport
        ),
        "tier1_to_reporting_company_transport_control": (
            evidence.tier1_to_reporting_company_transport_control
        ),
        "includes_tier1_to_reporting_company_transport": (
            evidence.includes_tier1_to_reporting_company_transport
        ),
        "includes_pre_tier1_supply_chain_transport": (
            evidence.includes_pre_tier1_supply_chain_transport
        ),
    }


def _dump_trace(payload: Mapping[str, Any]) -> str:
    ready = {key: _json_ready(item) for key, item in payload.items()}
    return json.dumps(ready, ensure_ascii=False, sort_keys=True)


def _blocked_result(
    evidence: PurchasedSteelEvidence,
    *,
    status: str,
    reason: str,
    normalized_value: float | None = None,
    normalized_unit: str = "",
) -> PurchasedSteelCalculationResult:
    return PurchasedSteelCalculationResult(
        calculation_id=f"calc_{evidence.record_id}" if evidence.record_id else "",
        record_id=evidence.record_id,
        activity_type=ACTIVITY_TYPE,
        normalized_value=normalized_value,
        normalized_unit=normalized_unit,
        calculated_kgco2e=None,
        calculated_tco2e=None,
        calculation_status=status,
        calculation_reason=reason,
        formula_id="",
        formula_version="",
        factor_id="",
        factor_value=None,
        factor_numerator_unit="",
        factor_denominator_unit="",
        source_reference_id="",
        calculation_method=evidence.calculation_method,
        supplier_name=evidence.supplier_name,
        steel_product_type=evidence.steel_product_type,
        factor_boundary=evidence.factor_boundary,
        factor_geography=evidence.factor_geography,
        factor_year=_coerce_year(evidence.factor_year),
        evidence_reference=evidence.evidence_reference,
        reporting_year=_coerce_year(evidence.reporting_year),
        reporting_period_id=evidence.reporting_period_id,
        ghg_scope=GHG_SCOPE,
        scope3_category=SCOPE3_CATEGORY,
        calculation_trace=_dump_trace(
            {
                "activity_type": ACTIVITY_TYPE,
                "calculation_method": evidence.calculation_method,
                "ghg_scope": GHG_SCOPE,
                "scope3_category": SCOPE3_CATEGORY,
                "scope_3_category": "category_1",
                "product_identifier": evidence.product_identifier,
                "purchased_quantity": evidence.purchased_quantity,
                "purchased_unit": evidence.purchased_unit,
                "factor_year": _coerce_year(evidence.factor_year),
                "factor_source_id": evidence.factor_source_id,
                "evidence_reference": evidence.evidence_reference,
                "source_document_id": evidence.source_document_id,
                **_transport_trace_fields(evidence),
                "status": status,
            }
        ),
        product_identifier=evidence.product_identifier,
        purchased_quantity=evidence.purchased_quantity,
        purchased_unit=evidence.purchased_unit,
        source_document_id=evidence.source_document_id,
        factor_source_id=evidence.factor_source_id,
    )


def _calculated_result(
    evidence: PurchasedSteelEvidence,
    *,
    method_id: str,
    quantity_tonnes: Decimal,
    factor_value: Decimal,
    factor_unit: FactorUnit,
    factor_id: str,
    factor_source_id: str,
    factor_boundary: str,
    factor_geography: str,
    factor_year: int,
    kgco2e: Decimal,
    factor_version: str = "",
    source_record_id: str = "",
    source_url: str = "",
    snapshot_hash: str = "",
    match_reason: str = "",
    approved_for_reporting_from: str = "",
    approved_for_reporting_to: str = "",
    technology: str = "",
    official_name: str = "",
    publisher: str = "",
    announcement_year: str = "",
    retrieved_at: str = "",
) -> PurchasedSteelCalculationResult:
    tco2e = kgco2e / KG_PER_TONNE
    official_product = official_name or evidence.steel_product_type
    trace = {
        "activity_type": ACTIVITY_TYPE,
        "calculation_method": method_id,
        "factor_id": factor_id,
        "factor_source_id": factor_source_id,
        "factor_boundary": factor_boundary,
        "factor_geography": factor_geography,
        "factor_year": factor_year,
        "formula_id": FORMULA_ID,
        "formula_version": FORMULA_VERSION,
        "ghg_scope": GHG_SCOPE,
        "scope3_category": SCOPE3_CATEGORY,
        **_transport_trace_fields(evidence),
        "purchased_quantity_t": str(quantity_tonnes),
        "normalized_mass_kg": str(quantity_tonnes * KG_PER_TONNE),
        "factor_unit": factor_unit.label,
        "factor_value": str(factor_value),
        "kgco2e": str(kgco2e),
        "tco2e": str(tco2e),
        "steel_product_type": evidence.steel_product_type,
        "official_name": official_product,
        "publisher": publisher,
        "announcement_year": announcement_year,
        "retrieved_at": retrieved_at,
        "product_identifier": evidence.product_identifier,
        "purchased_quantity": evidence.purchased_quantity,
        "purchased_unit": evidence.purchased_unit,
        "source_document_id": evidence.source_document_id,
        "supplier_name": evidence.supplier_name,
        "scope_3_category": "category_1",
        "factor_version": factor_version,
        "source_record_id": source_record_id,
        "source_url": source_url,
        "snapshot_hash": snapshot_hash,
        "match_reason": match_reason,
        "approved_for_reporting_from": approved_for_reporting_from,
        "approved_for_reporting_to": approved_for_reporting_to,
        "technology": technology,
        "temporal_representativeness_warning": (
            evidence.reporting_year is not None
            and _coerce_year(evidence.reporting_year) is not None
            and factor_year < int(_coerce_year(evidence.reporting_year) or 0)
        ),
    }
    return PurchasedSteelCalculationResult(
        calculation_id=f"calc_{evidence.record_id}",
        record_id=evidence.record_id,
        activity_type=ACTIVITY_TYPE,
        normalized_value=_decimal_to_float(quantity_tonnes),
        normalized_unit=CANONICAL_MASS_UNIT,
        calculated_kgco2e=_decimal_to_float(kgco2e),
        calculated_tco2e=_decimal_to_float(tco2e),
        calculation_status=STATUS_CALCULATED,
        calculation_reason=(
            "Calculated as purchased mass times a cradle-to-gate "
            f"{method_id} Category 1 factor. Pre-Tier-1 supply-chain "
            "transport may be included in the cradle-to-gate factor; "
            "coverage comes from the factor source and system boundary, "
            "not from a user yes/no flag. This Category 1 result does "
            "not inventory a separate Tier 1 to reporting-company "
            "transport leg."
        ),
        formula_id=FORMULA_ID,
        formula_version=FORMULA_VERSION,
        factor_id=factor_id,
        factor_value=_decimal_to_float(factor_value),
        factor_numerator_unit=factor_unit.numerator,
        factor_denominator_unit=factor_unit.denominator,
        source_reference_id=factor_source_id,
        calculation_method=method_id,
        supplier_name=evidence.supplier_name,
        steel_product_type=evidence.steel_product_type,
        factor_boundary=factor_boundary,
        factor_geography=factor_geography,
        factor_year=factor_year,
        evidence_reference=evidence.evidence_reference,
        reporting_year=_coerce_year(evidence.reporting_year),
        reporting_period_id=evidence.reporting_period_id,
        ghg_scope=GHG_SCOPE,
        scope3_category=SCOPE3_CATEGORY,
        calculation_trace=_dump_trace(trace),
        product_identifier=evidence.product_identifier,
        purchased_quantity=evidence.purchased_quantity,
        purchased_unit=evidence.purchased_unit,
        source_document_id=evidence.source_document_id,
        factor_source_id=factor_source_id,
        factor_version=factor_version,
        source_record_id=source_record_id,
        source_url=source_url,
        snapshot_hash=snapshot_hash,
        match_reason=match_reason
        or (
            f"{method_id}: purchased mass × cradle-to-gate factor; "
            "exact product/geography/period match"
        ),
        approved_for_reporting_from=approved_for_reporting_from,
        approved_for_reporting_to=approved_for_reporting_to,
        technology=technology,
        official_name=official_product,
        publisher=publisher,
        announcement_year=announcement_year,
        retrieved_at=retrieved_at,
    )


def calculate_purchased_steel(
    record: Mapping[str, Any] | PurchasedSteelEvidence,
    *,
    registered_factors: pd.DataFrame
    | Sequence[RegisteredSteelFactor]
    | None = None,
) -> PurchasedSteelCalculationResult:
    """Calculate Category 1 steel emissions only when evidence is complete.

    Missing method, factor, unit, source, product match, or reporting period
    stays blocked or ``no_factor_configured``. Calculated values are never
    invented as zero.
    """
    evidence = (
        record
        if isinstance(record, PurchasedSteelEvidence)
        else parse_purchased_steel_evidence(record)
    )
    if isinstance(registered_factors, pd.DataFrame) or registered_factors is None:
        factors = registered_steel_factors_from_frame(registered_factors)
    else:
        factors = tuple(registered_factors)

    status, issues = validate_purchased_steel_evidence(
        evidence, registered_factors=factors
    )
    quantity = _parse_positive_decimal(evidence.purchased_quantity)
    normalized_tonnes = None
    if isinstance(quantity, Decimal) and evidence.purchased_unit in ALLOWED_MASS_UNITS:
        normalized_tonnes = mass_to_canonical_tonnes(
            quantity, evidence.purchased_unit
        )
    normalized_value = (
        _decimal_to_float(normalized_tonnes)
        if normalized_tonnes is not None
        else None
    )
    normalized_unit = CANONICAL_MASS_UNIT if normalized_tonnes is not None else ""

    if status != STATUS_CALCULATED:
        reason = issues[0].message if issues else status
        return _blocked_result(
            evidence,
            status=status,
            reason=reason,
            normalized_value=normalized_value,
            normalized_unit=normalized_unit,
        )

    assert isinstance(quantity, Decimal)
    assert normalized_tonnes is not None
    reporting_year = _coerce_year(evidence.reporting_year)
    assert reporting_year is not None

    if evidence.calculation_method == METHOD_SUPPLIER_SPECIFIC:
        factor_unit = parse_emission_factor_unit(evidence.emission_factor_unit)
        factor_value = _parse_positive_decimal(evidence.emission_factor_value)
        factor_year = _coerce_year(evidence.factor_year)
        if factor_year is None:
            return _blocked_result(
                evidence,
                status=STATUS_BLOCKED_MISSING_FACTOR_YEAR,
                reason=(
                    "supplier_specific requires factor_year as the coefficient "
                    "data year. reporting_year is not substituted."
                ),
                normalized_value=normalized_value,
                normalized_unit=normalized_unit,
            )
        assert factor_unit is not None
        assert isinstance(factor_value, Decimal)
        quantity_in_den = _mass_in_denominator(
            quantity, evidence.purchased_unit, factor_unit.denominator
        )
        kgco2e = (
            _kgco2e_from_factor(quantity_in_den, factor_value, factor_unit.numerator)
            if quantity_in_den is not None
            else None
        )
        if kgco2e is None:
            return _blocked_result(
                evidence,
                status=STATUS_BLOCKED_INCOMPATIBLE_UNIT,
                reason="Purchased mass unit cannot be applied to the factor unit.",
                normalized_value=normalized_value,
                normalized_unit=normalized_unit,
            )
        return _calculated_result(
            evidence,
            method_id=METHOD_SUPPLIER_SPECIFIC,
            quantity_tonnes=normalized_tonnes,
            factor_value=factor_value,
            factor_unit=factor_unit,
            factor_id="",
            factor_source_id=evidence.factor_source_id,
            factor_boundary=FACTOR_BOUNDARY_CRADLE_TO_GATE,
            factor_geography=evidence.factor_geography,
            factor_year=factor_year,
            kgco2e=kgco2e,
        )

    matched, match_status = match_average_data_factor(
        evidence, factors, reporting_year=reporting_year
    )
    if matched is None:
        return _blocked_result(
            evidence,
            status=match_status or STATUS_NO_MATCHING_FACTOR,
            reason=(
                "average_data can only use a unique registered, versioned "
                "secondary factor with product type, process, geography, "
                "cradle-to-gate boundary, and approved reporting period."
            ),
            normalized_value=normalized_value,
            normalized_unit=normalized_unit,
        )
    quantity_in_den = _mass_in_denominator(
        quantity, evidence.purchased_unit, matched.factor_unit.denominator
    )
    kgco2e = (
        _kgco2e_from_factor(
            quantity_in_den, matched.factor_value, matched.factor_unit.numerator
        )
        if quantity_in_den is not None
        else None
    )
    if kgco2e is None:
        return _blocked_result(
            evidence,
            status=STATUS_BLOCKED_INCOMPATIBLE_UNIT,
            reason="Purchased mass unit cannot be applied to the factor unit.",
            normalized_value=normalized_value,
            normalized_unit=normalized_unit,
        )
    return _calculated_result(
        replace(
            evidence,
            includes_pre_tier1_supply_chain_transport=(
                matched.includes_pre_tier1_supply_chain_transport
            ),
        ),
        method_id=METHOD_AVERAGE_DATA,
        quantity_tonnes=normalized_tonnes,
        factor_value=matched.factor_value,
        factor_unit=matched.factor_unit,
        factor_id=matched.factor_id,
        factor_source_id=matched.factor_source_id,
        factor_boundary=matched.factor_boundary,
        factor_geography=matched.factor_geography,
        factor_year=matched.factor_year,
        kgco2e=kgco2e,
        factor_version=matched.factor_version,
        source_record_id=matched.source_record_id,
        source_url=matched.source_url,
        snapshot_hash=matched.snapshot_hash,
        match_reason=(
            "average_data exact match on official product identity, "
            "factor unit, geography, cradle-to-gate boundary, and "
            "internally approved reporting period"
        ),
        approved_for_reporting_from=(
            matched.approved_for_reporting_from or matched.valid_from
        ),
        approved_for_reporting_to=(
            matched.approved_for_reporting_to or matched.valid_to
        ),
        technology=matched.technology,
        official_name=matched.official_name or matched.steel_product_type,
        publisher=matched.publisher,
        announcement_year=matched.announcement_year,
        retrieved_at=matched.retrieved_at,
    )
