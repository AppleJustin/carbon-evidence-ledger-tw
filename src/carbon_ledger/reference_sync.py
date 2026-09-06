"""Official reference synchronization for Carbon Evidence Ledger (Phase 10A).

Network-aware maintenance stays here. Calculation modules must never import
HTTP clients or require live internet access.

Flow: discover → download → hash/version → parse → candidate → validate →
activate. Newly fetched numbers never become active automatically.
"""

from __future__ import annotations

import csv
import hashlib
import html as html_module
import io
import json
import re
import ssl
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)

import pandas as pd

from carbon_ledger.factors import EMISSION_FACTOR_COLUMNS, GWP_COLUMNS

PARSER_VERSION = "reference_sync_v1"
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 30.0

# Transparent application identity for official-source GETs (not a browser UA).
OFFICIAL_USER_AGENT = (
    "CarbonEvidenceLedger/0.1 "
    "(+https://github.com/Ting-En-Chien/carbon-evidence-ledger-tw)"
)
OFFICIAL_REQUEST_HEADERS = {
    "User-Agent": OFFICIAL_USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
}

TLS_MODE_DEFAULT = "default"
TLS_MODE_PYTHON313_RELAXED_X509_STRICT = "python313_relaxed_x509_strict"
TLS_VERIFICATION_VERIFIED = "verified"
ALLOWED_TLS_COMPATIBILITY_MODES = frozenset(
    {
        TLS_MODE_DEFAULT,
        TLS_MODE_PYTHON313_RELAXED_X509_STRICT,
    }
)

FETCH_MODE_FETCH = "fetch"
FETCH_MODE_PROVENANCE_ONLY = "provenance_only"
ALLOWED_FETCH_MODES = frozenset(
    {
        FETCH_MODE_FETCH,
        FETCH_MODE_PROVENANCE_ONLY,
    }
)

RETRIEVAL_PARSE_LANDING = "parse_landing"
RETRIEVAL_DISCOVER_ATTACHMENT = "discover_attachment"
RETRIEVAL_PROVENANCE_ONLY = "provenance_only"
RETRIEVAL_PAGINATED_OPEN_DATA_API = "paginated_open_data_api"
ALLOWED_RETRIEVAL_STRATEGIES = frozenset(
    {
        RETRIEVAL_PARSE_LANDING,
        RETRIEVAL_DISCOVER_ATTACHMENT,
        RETRIEVAL_PROVENANCE_ONLY,
        RETRIEVAL_PAGINATED_OPEN_DATA_API,
    }
)

REF_TYPE_ELECTRICITY = "electricity_factor"
REF_TYPE_ELECTRICITY_ENTERPRISE = "electricity_factor_enterprise_inventory"
REF_TYPE_ELECTRICITY_UPSTREAM = "electricity_factor_upstream"
ELECTRICITY_CANDIDATE_REF_TYPES = frozenset(
    {
        REF_TYPE_ELECTRICITY,
        REF_TYPE_ELECTRICITY_ENTERPRISE,
    }
)

SOURCE_COLUMNS = [
    "source_id",
    "authority",
    "reference_type",
    "canonical_url",
    "upstream_canonical_url",
    "upstream_factor_authority",
    "landing_url",
    "expected_file_type",
    "parser_type",
    "allowed_domain",
    "tls_compatibility_mode",
    "fetch_mode",
    "retrieval_strategy",
    "active",
    "notes",
]

SNAPSHOT_COLUMNS = [
    "snapshot_id",
    "source_id",
    "authority",
    "reference_type",
    "canonical_url",
    "upstream_canonical_url",
    "upstream_factor_authority",
    "discovered_url",
    "retrieved_url",
    "retrieved_host",
    "retrieved_at",
    "publication_date",
    "file_name",
    "media_type",
    "sha256",
    "byte_size",
    "parser_version",
    "local_path",
    "status",
    "tls_verification",
    "tls_compatibility_mode",
    "notes",
]

CANDIDATE_COLUMNS = [
    "candidate_id",
    "snapshot_id",
    "source_id",
    "reference_type",
    "factor_year",
    "valid_from",
    "valid_to",
    "geography",
    "activity_type",
    "combustion_context",
    "gas",
    "factor_value",
    "numerator_unit",
    "denominator_unit",
    "factor_category",
    "intended_use",
    "applicability_notes",
    "upstream_factor_authority",
    "publication_date",
    "source_locator",
    "validation_status",
    "lifecycle_status",
    "parser_version",
    "reason",
    "notes",
    "candidate_type",
    "target_registry",
    "source_url",
    "source_snapshot_path",
    "source_sha256",
    "source_location",
    "reporting_year",
    "factor_context",
    "refrigerant",
    "assessment_basis",
    "factor_unit",
    "validation_messages",
    "created_at",
]

ACTIVATION_COLUMNS = [
    "activation_id",
    "candidate_id",
    "snapshot_id",
    "factor_id",
    "factor_year",
    "factor_category",
    "factor_value",
    "numerator_unit",
    "denominator_unit",
    "activated_at",
    "activated_by",
    "registry_table",
    "sha256",
    "source_id",
    "upstream_factor_authority",
    "retrieved_url",
    "notes",
    "source_snapshot_path",
    "previous_content",
    "new_content",
]

RULE_COLUMNS = [
    "rule_id",
    "reference_type",
    "jurisdiction",
    "condition",
    "fallback_behavior",
    "valid_from",
    "valid_to",
    "source_reference_id",
    "source_locator",
    "rule_version",
    "active",
    "notes",
]

HEATING_VALUE_COLUMNS = [
    "heating_value_id",
    "fuel_type",
    "fuel_subtype",
    "heating_value",
    "unit",
    "high_heating_value",
    "high_heating_value_unit",
    "factor_year",
    "geography",
    "authority",
    "valid_from",
    "valid_to",
    "source_reference_id",
    "source_locator",
    "snapshot_id",
    "snapshot_sha256",
    "snapshot_local_path",
    "status",
    "notes",
]

LIFECYCLE_DISCOVERED = "discovered"
LIFECYCLE_DOWNLOADED = "downloaded"
LIFECYCLE_PARSED = "parsed"
LIFECYCLE_VALIDATED = "validated"
LIFECYCLE_CANDIDATE = "candidate"
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_REJECTED = "rejected"
LIFECYCLE_SUPERSEDED = "superseded"
LIFECYCLE_NEEDS_PARSER_REVIEW = "needs_parser_review"

VALIDATION_PASSED = "passed"
VALIDATION_FAILED = "failed"
VALIDATION_PENDING = "pending"

STATUS_MANUAL_REVIEW_REQUIRED = "manual_review_required"
STATUS_ALREADY_KNOWN = "already_known"
REF_TYPE_FUEL_EF = "fuel_emission_factor"
REF_TYPE_GWP = "gwp_reference"
REF_TYPE_HEATING = "fuel_heating_values"
WRONG_DOCUMENT_FOR_SOURCE = "WRONG_DOCUMENT_FOR_SOURCE"
REF_TYPE_STEEL = "purchased_steel_average_data"
REF_TYPE_GENERAL_EF = "general_emission_factors"
GWP_ASSESSMENT_AR5 = "IPCC AR5 100-year GWP"
GWP_ASSESSMENT_AR6 = "IPCC AR6 100-year GWP"
SUPPORTED_GWP_ASSESSMENTS = frozenset({GWP_ASSESSMENT_AR5, GWP_ASSESSMENT_AR6})
MANUAL_REVIEW_ERROR_CODES = frozenset(
    {
        "SOURCE_ACCESS_RESTRICTED",
        "HTTP_UNAUTHORIZED",
        "HTTP_FORBIDDEN",
        "CAPTCHA_REQUIRED",
        "ROBOTS_DISALLOWED",
        "LOGIN_REQUIRED",
        "TERMS_RESTRICTED",
    }
)

SUPPORTED_ELECTRICITY_CATEGORIES = frozenset(
    {
        # MOENV enterprise-inventory announcement categories
        "public_sales_average",
        "industrial_enterprise_inventory",
        "residential",
        # Legacy / CSV / MOEA landing categories still accepted
        "utility_average",
        "industry",
        "inventory_specific",
        "unspecified",
    }
)

ENTERPRISE_INVENTORY_CATEGORIES = frozenset(
    {
        "industrial_enterprise_inventory",
        "industry",
    }
)
ENTERPRISE_INVENTORY_INTENDED_USES = frozenset(
    {
        "enterprise_inventory",
        "enterprise GHG inventory / disclosure",
    }
)

SUPPORTED_NUMERATOR_UNITS = frozenset({"kgCO2e", "kgCO2", "kgCH4", "kgN2O"})
SUPPORTED_DENOMINATOR_UNITS = frozenset({"kWh", "MWh", "TJ", "m3", "L"})
SUPPORTED_HEATING_UNITS = frozenset({"kcal/m3", "kcal/L", "MJ/m3", "MJ/L"})

LANDING_DISCOVERY_PARSERS = frozenset(
    {
        "tw_moea_electricity_landing_v1",
        "tw_moenv_file_downloads_landing_v1",
        "tw_moenv_news_heating_values_landing_v1",
    }
)

_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)

# Label → factor_category mappings for official electricity news HTML.
# Values are extracted from the fetched page; never hard-coded here.
_ELECTRICITY_HTML_CATEGORY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"公用售電業[^0-9]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*公斤",
            re.IGNORECASE,
        ),
        "utility_average",
    ),
    (
        re.compile(
            r"工業部門[^0-9]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*公斤",
            re.IGNORECASE,
        ),
        "industry",
    ),
    (
        re.compile(
            r"住宅部門[^0-9]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*公斤",
            re.IGNORECASE,
        ),
        "residential",
    ),
    (
        re.compile(
            r"public\s+electricity[- ]sales\s+average[^0-9]{0,80}?"
            r"([0-9]+(?:\.[0-9]+)?)",
            re.IGNORECASE,
        ),
        "utility_average",
    ),
    (
        re.compile(
            r"industrial\s+electricity[^0-9]{0,80}?([0-9]+(?:\.[0-9]+)?)",
            re.IGNORECASE,
        ),
        "industry",
    ),
    (
        re.compile(
            r"residential\s+electricity[^0-9]{0,80}?([0-9]+(?:\.[0-9]+)?)",
            re.IGNORECASE,
        ),
        "residential",
    ),
)
_MOEA_HTML_PUBLICATION_DATE_RE = re.compile(
    r"(?:發布日期|刊載日期|日期)[：:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})"
)
_MOEA_HTML_ROC_YEAR_RE = re.compile(r"(?:民國)?\s*([0-9]{2,3})\s*年度")

_MOENV_NEWS_ITEM_RE = re.compile(
    r"(?is)(<div[^>]*class=[\"'][^\"']*news-item[^\"']*[\"'][^>]*>.*?</div>\s*</div>)"
)
_MOENV_NEWS_DATE_RE = re.compile(
    r"(?is)class=[\"'][^\"']*news-date[^\"']*[\"'][^>]*>\s*"
    r"([0-9]{4})[/-]([0-9]{2})[/-]([0-9]{2})"
)
_MOENV_NEWS_TITLE_RE = re.compile(
    r"(?is)class=[\"'][^\"']*news-title[^\"']*[\"'][^>]*>(.*?)</a>"
)
# Live ASP.NET NewsList markup uses news-list-* classes, not news-item.
_MOENV_LIST_ITEM_RE = re.compile(
    r"(?is)<li>\s*<span[^>]*class=(['\"])[^'\"]*news-list-date[^'\"]*\1[^>]*>"
    r"(.*?)</span>(.*?)</li>"
)
_MOENV_DATE_TOKEN_RE = re.compile(
    r"(?<!\d)(20[0-9]{2})\s*[/-]\s*(0?[1-9]|1[0-2])\s*[/-]\s*"
    r"(0?[1-9]|[12][0-9]|3[01])(?!\d)"
)
_MOENV_ANNOUNCEMENT_TITLE_TOKEN = "114年度電力排碳係數"
_MOENV_ANNOUNCEMENT_DATE = "2026-06-17"
_MOENV_FACTOR_YEAR_RE = re.compile(
    r"([0-9]{2,3})\s*年(?:度)?\s*電力排碳係數"
)
# Label → factor_category for the MOENV enterprise electricity announcement.
# Values are extracted from the bounded announcement text only.
_MOENV_ELECTRICITY_CATEGORY_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Live NewsList: value appears before the "公用售電業整體" label.
    (
        re.compile(
            r"([0-9]+(?:\.[0-9]+)?)\s*公斤\s*CO2e\s*/\s*度"
            r"[^。\n]{0,80}?公用售電業整體"
        ),
        "public_sales_average",
    ),
    # Simplified fixture / alternate wording: label then value.
    (
        re.compile(
            r"公用售電業[^0-9]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*公斤"
        ),
        "public_sales_average",
    ),
    (
        re.compile(
            r"產業電力排碳係數[^0-9]{0,24}?([0-9]+(?:\.[0-9]+)?)\s*公斤"
        ),
        "industrial_enterprise_inventory",
    ),
    (
        re.compile(
            r"工業部門[^0-9]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*公斤"
        ),
        "industrial_enterprise_inventory",
    ),
    (
        re.compile(
            r"民生住宅電力排碳係數[^0-9]{0,24}?([0-9]+(?:\.[0-9]+)?)\s*公斤"
        ),
        "residential",
    ),
    (
        re.compile(
            r"住宅部門[^0-9]{0,80}?([0-9]+(?:\.[0-9]+)?)\s*公斤"
        ),
        "residential",
    ),
)


class ReferenceSyncError(ValueError):
    """Structured sync failure with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class FetchResult:
    """Bytes and metadata from one allowlisted fetch."""

    url: str
    final_url: str
    content: bytes
    media_type: str
    sha256: str
    byte_size: int
    tls_verification: str = TLS_VERIFICATION_VERIFIED
    tls_compatibility_mode: str = TLS_MODE_DEFAULT
    discovered_url: str = ""


@dataclass
class ParseResult:
    """Deterministic parser output or an explicit review requirement."""

    parser_type: str
    status: str
    records: list[dict[str, Any]] = field(default_factory=list)
    publication_date: str = ""
    reason: str = ""


@dataclass
class DiscoveryResult:
    """Result of discovering an official attachment from a landing page."""

    parser_type: str
    status: str
    landing_url: str
    artifact_url: str = ""
    preferred_extension: str = ""
    candidate_urls: tuple[str, ...] = ()
    reason: str = ""


@dataclass
class ChangeReport:
    """Human-readable comparison between known and new artifacts."""

    source_id: str
    reference_type: str
    previous_snapshot_id: str
    new_snapshot_id: str
    previous_years: tuple[str, ...]
    new_years: tuple[str, ...]
    changes: tuple[str, ...]
    activated: bool = False

    def to_text(self) -> str:
        lines = [
            "Official reference update detected",
            "",
            f"Source: {self.source_id}",
            f"Reference type: {self.reference_type}",
            f"Previous snapshot: {self.previous_snapshot_id or '(none)'}",
            f"New snapshot: {self.new_snapshot_id}",
            f"Previous known years: {', '.join(self.previous_years) or '(none)'}",
            f"New candidate years: {', '.join(self.new_years) or '(none)'}",
            "Changes:",
        ]
        if self.changes:
            lines.extend(f"- {item}" for item in self.changes)
        else:
            lines.append("- (no structured field differences detected)")
        lines.append("")
        lines.append("No automatic activation has occurred yet.")
        return "\n".join(lines)


@dataclass
class SyncStatus:
    """Beginner/admin facing registry status summary."""

    electricity_years: dict[str, str]
    heating_value_latest: dict[str, str]
    last_checked_at: str
    snapshot_count: int
    candidate_count: int
    active_candidate_count: int
    source_count: int
    upstream_factor_authority: str = (
        "Taiwan Ministry of Economic Affairs / Energy Administration"
    )
    operational_source_authority: str = (
        "Taiwan Ministry of Environment / Climate Change Administration"
    )
    upstream_source_status: str = "recorded / access restricted"
    operational_source_status: str = "unchecked"
    upstream_canonical_url: str = ""
    operational_source_url: str = ""
    electricity_categories: dict[str, str] = field(default_factory=dict)


FetchCallable = Callable[..., FetchResult]


def compute_bytes_sha256(data: bytes) -> str:
    """Return lowercase SHA-256 hex digest."""
    return hashlib.sha256(data).hexdigest()


def _blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def _text(value: Any) -> str:
    if _blank(value):
        return ""
    return str(value).strip()


def _decoded_locator_text(*values: Any) -> str:
    return unquote(" ".join(_text(item) for item in values if _text(item)))


def _looks_like_emission_factor_document(*values: Any) -> bool:
    return "排放係數" in _decoded_locator_text(*values)


def _is_heating_value_source(
    *,
    reference_type: str = "",
    candidate_type: str = "",
    source_id: str = "",
) -> bool:
    return (
        _text(reference_type) == REF_TYPE_HEATING
        or _text(candidate_type) == REF_TYPE_HEATING
        or "fuel_heating_values" in _text(source_id)
    )


def wrong_document_issues(
    candidate: dict[str, Any] | pd.Series | None = None,
    *,
    reference_type: str = "",
    candidate_type: str = "",
    source_id: str = "",
    locator: str = "",
    source_url: str = "",
    source_location: str = "",
    existing_text: str = "",
) -> list[str]:
    """Mark heating-value sources that retrieved an emission-factor document."""
    row = candidate if candidate is not None else {}
    ref_type = reference_type or _text(row.get("reference_type"))
    cand_type = candidate_type or _text(row.get("candidate_type"))
    src_id = source_id or _text(row.get("source_id"))
    if not _is_heating_value_source(
        reference_type=ref_type,
        candidate_type=cand_type,
        source_id=src_id,
    ):
        return []
    locators = (
        locator or _text(row.get("source_locator")),
        source_url or _text(row.get("source_url")),
        source_location or _text(row.get("source_location")),
    )
    blob = existing_text or " ".join(
        [
            _text(row.get("reason")),
            _text(row.get("notes")),
            _text(row.get("validation_messages")),
        ]
    )
    if _looks_like_emission_factor_document(*locators) or (
        WRONG_DOCUMENT_FOR_SOURCE in blob
    ):
        return [WRONG_DOCUMENT_FOR_SOURCE]
    return []


def wrong_document_for_source_note(
    *,
    reference_type: str,
    source_id: str = "",
    retrieved_url: str = "",
    discovered_url: str = "",
) -> str:
    """Snapshot note when a heating-value source retrieved an EF document."""
    issues = wrong_document_issues(
        reference_type=reference_type,
        source_id=source_id,
        locator=retrieved_url,
        source_url=discovered_url,
        source_location=retrieved_url,
    )
    if not issues:
        return ""
    filename = _decoded_locator_text(retrieved_url or discovered_url).rsplit(
        "/", 1
    )[-1]
    return (
        f"{WRONG_DOCUMENT_FOR_SOURCE}: filename/source_id say "
        f"fuel_heating_values but retrieved_url is {filename}. "
        "Do not use as heating-value evidence. File retained."
    )


def _truthy(value: Any) -> bool:
    return _text(value).lower() in {"1", "true", "yes", "y", "active"}


def _read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame.loc[:, columns].copy()


def _write_csv(path: Path, frame: pd.DataFrame, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = ""
    out.loc[:, columns].to_csv(path, index=False)


def default_paths(repo_root: Path) -> dict[str, Path]:
    """Return canonical Phase 10A path layout under a repository root."""
    root = Path(repo_root)
    return {
        "sources": root / "config" / "official_reference_sources.csv",
        "rules": root / "config" / "official_reference_rules.csv",
        "reference_dir": root / "data" / "reference",
        "snapshots_csv": root / "data" / "reference" / "reference_snapshots.csv",
        "candidates_csv": root / "data" / "reference" / "reference_candidates.csv",
        "activations_csv": root / "data" / "reference" / "reference_activations.csv",
        "emission_factors": root / "data" / "reference" / "emission_factors.csv",
        "fuel_heating_values": root / "data" / "reference" / "fuel_heating_values.csv",
        "gwp_values": root / "data" / "reference" / "gwp_values.csv",
        "artifact_dir": root / "data" / "reference_snapshots",
        "steel_factors": root / "data" / "reference" / "purchased_steel_factors.csv",
        "steel_candidates": root
        / "data"
        / "reference"
        / "purchased_steel_factor_candidates.csv",
        "steel_taxonomy": root / "data" / "reference" / "steel_product_taxonomy.csv",
        "proposal_json": root
        / "data"
        / "reference"
        / "official_factor_update_proposal.json",
        "proposal_md": root
        / "data"
        / "reference"
        / "official_factor_update_review.md",
    }


def load_official_sources(path: Path | str) -> pd.DataFrame:
    """Load the allowlisted official source registry."""
    frame = _read_csv(Path(path), SOURCE_COLUMNS)
    if frame.empty:
        return frame
    required = ("source_id", "allowed_domain", "landing_url")
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ReferenceSyncError(
            "INVALID_SOURCE_REGISTRY",
            f"Source registry missing columns: {missing}",
        )
    return frame


def load_official_reference_rules(path: Path | str) -> pd.DataFrame:
    """Load explicit official fallback/applicability rules."""
    return _read_csv(Path(path), RULE_COLUMNS)


def active_sources(sources: pd.DataFrame) -> pd.DataFrame:
    """Return rows marked active."""
    if sources.empty:
        return sources.copy()
    mask = sources["active"].map(_truthy)
    return sources.loc[mask].copy()


def normalize_fetch_mode(value: Any) -> str:
    """Return a supported fetch mode (default fetch when blank)."""
    text = _text(value) or FETCH_MODE_FETCH
    if text not in ALLOWED_FETCH_MODES:
        raise ReferenceSyncError(
            "INVALID_FETCH_MODE",
            f"Unsupported fetch_mode {text!r}.",
        )
    return text


def normalize_retrieval_strategy(value: Any) -> str:
    """Return a supported retrieval strategy for an official source."""
    text = _text(value)
    if not text:
        raise ReferenceSyncError(
            "MISSING_RETRIEVAL_STRATEGY",
            "Official source is missing retrieval_strategy.",
        )
    if text not in ALLOWED_RETRIEVAL_STRATEGIES:
        raise ReferenceSyncError(
            "INVALID_RETRIEVAL_STRATEGY",
            f"Unsupported retrieval_strategy {text!r}.",
        )
    return text


def fetchable_sources(sources: pd.DataFrame) -> pd.DataFrame:
    """Return active sources that are eligible for network fetch/check."""
    active = active_sources(sources)
    if active.empty:
        return active
    if "fetch_mode" not in active.columns:
        return active.copy()
    modes = active["fetch_mode"].map(normalize_fetch_mode)
    return active.loc[modes == FETCH_MODE_FETCH].copy()


def extract_hostname(url: str) -> str:
    """Return lowercase hostname from a URL."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        raise ReferenceSyncError("INVALID_URL", f"URL has no hostname: {url!r}")
    return host


def assert_url_allowlisted(url: str, allowed_domain: str) -> None:
    """Reject URLs outside the configured official domain."""
    host = extract_hostname(url)
    allowed = _text(allowed_domain).lower().lstrip(".")
    if not allowed:
        raise ReferenceSyncError(
            "MISSING_ALLOWLIST",
            "Official source is missing allowed_domain.",
        )
    if host != allowed and not host.endswith("." + allowed):
        raise ReferenceSyncError(
            "DOMAIN_NOT_ALLOWLISTED",
            f"Domain {host!r} is not allowlisted for official sync "
            f"(allowed: {allowed!r}).",
        )


def normalize_request_url(url: str) -> str:
    """Convert an official IRI/URL into an ASCII-safe URI for urllib.

    Encodes non-ASCII characters in path/query/fragment separately so scheme
    separators and already-valid percent escapes are preserved. Does not alter
    hostname validation semantics; call after allowlist checks.
    """
    text = _text(url)
    if not text:
        return text
    parts = urlsplit(text)
    hostname = parts.hostname
    if hostname:
        try:
            ascii_host = hostname.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ReferenceSyncError(
                "INVALID_URL_HOST",
                f"Official URL host cannot be encoded for HTTP: {hostname!r}.",
            ) from exc
        userinfo = ""
        if parts.username is not None:
            password = "" if parts.password is None else f":{parts.password}"
            userinfo = f"{parts.username}{password}@"
        port = f":{parts.port}" if parts.port is not None else ""
        netloc = f"{userinfo}{ascii_host}{port}"
    else:
        netloc = parts.netloc

    # Keep already-encoded % sequences intact; encode only unsafe octets.
    path = quote(parts.path, safe="/%:@-._~!$&'()*+,;=")
    query = quote(parts.query, safe="%&=+!$'()*,;:@/?")
    fragment = quote(parts.fragment, safe="%:@-._~!$&'()*+,;=/?")
    return urlunsplit((parts.scheme, netloc, path, query, fragment))


# Backward-compatible alias for the IRI→URI helper.
iri_to_uri = normalize_request_url


def assert_not_company_upload_as_official(
    *,
    source_kind: str,
    column_names: list[str] | tuple[str, ...] | None = None,
) -> None:
    """Guard: company Excel factor columns never become official registry truth."""
    kind = _text(source_kind).lower()
    if kind in {"company_upload", "user_upload", "intake_upload", "excel_upload"}:
        raise ReferenceSyncError(
            "COMPANY_UPLOAD_NOT_OFFICIAL",
            "Uploaded company spreadsheets cannot update the official "
            "reference registry.",
        )
    if column_names:
        joined = " ".join(str(item) for item in column_names)
        if any(token in joined for token in ("排放係數", "排放量", "CO2e", "計算結果")):
            # Presence in a company file is fine; promoting them is not.
            pass


class _AllowlistRedirectHandler(HTTPRedirectHandler):
    """Follow redirects only while the target remains allowlisted."""

    def __init__(self, allowed_domain: str) -> None:
        super().__init__()
        self.allowed_domain = allowed_domain

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        assert_url_allowlisted(newurl, self.allowed_domain)
        normalized = normalize_request_url(newurl)
        return super().redirect_request(
            req, fp, code, msg, headers, normalized
        )


def normalize_tls_compatibility_mode(value: Any) -> str:
    """Return a supported TLS compatibility mode (default when blank)."""
    text = _text(value) or TLS_MODE_DEFAULT
    if text not in ALLOWED_TLS_COMPATIBILITY_MODES:
        raise ReferenceSyncError(
            "INVALID_TLS_COMPATIBILITY_MODE",
            f"Unsupported tls_compatibility_mode {text!r}.",
        )
    return text


def build_official_ssl_context(
    *,
    tls_compatibility_mode: str = TLS_MODE_DEFAULT,
) -> ssl.SSLContext:
    """Build a verified SSL context for allowlisted official-source fetches.

    Always keeps CA validation and hostname checking enabled. Never uses
    ``verify=False`` or an unverified context.

    ``python313_relaxed_x509_strict`` clears only ``VERIFY_X509_STRICT`` for
    explicitly configured official sources that need Python 3.13 certificate
    chain compatibility. It does not disable certificate verification.
    """
    mode = normalize_tls_compatibility_mode(tls_compatibility_mode)
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    if mode == TLS_MODE_PYTHON313_RELAXED_X509_STRICT:
        strict_flag = getattr(ssl, "VERIFY_X509_STRICT", None)
        if strict_flag is not None:
            context.verify_flags &= ~strict_flag
    return context


def build_official_https_opener(
    *,
    allowed_domain: str,
    tls_compatibility_mode: str = TLS_MODE_DEFAULT,
) -> Any:
    """Build an opener with verified HTTPS + allowlisted redirects."""
    context = build_official_ssl_context(
        tls_compatibility_mode=tls_compatibility_mode,
    )
    return build_opener(
        HTTPSHandler(context=context),
        _AllowlistRedirectHandler(allowed_domain),
    )


def build_official_request_headers() -> dict[str, str]:
    """Return conservative headers for official-source GET requests.

    Uses a transparent application User-Agent. Does not impersonate a browser,
    and does not add cookies, authentication, or Sec-* client hints.
    """
    return dict(OFFICIAL_REQUEST_HEADERS)


def _http_status_error(status: int, url: str) -> ReferenceSyncError:
    """Map HTTP status codes to structured sync errors."""
    code = int(status)
    if code == 401:
        return ReferenceSyncError(
            "HTTP_UNAUTHORIZED",
            (
                f"Official source requires login (HTTP 401) for {url}. "
                "Credentials are not used; result is manual_review_required."
            ),
        )
    if code == 403:
        return ReferenceSyncError(
            "SOURCE_ACCESS_RESTRICTED",
            (
                f"Official source restricted access (HTTP 403) for {url}. "
                "Transparent application identity was used; no browser "
                "impersonation retry is attempted."
            ),
        )
    if code == 429:
        return ReferenceSyncError(
            "SOURCE_ACCESS_RESTRICTED",
            f"Official source rate-limited (HTTP 429) for {url}.",
        )
    return ReferenceSyncError(
        "HTTP_ERROR",
        f"Official source returned HTTP {status} for {url}.",
    )


def _fetch_failure_status(exc: ReferenceSyncError) -> str:
    if exc.code in MANUAL_REVIEW_ERROR_CODES:
        return STATUS_MANUAL_REVIEW_REQUIRED
    return "unavailable"


def _blocked_content_error(content: bytes, url: str) -> ReferenceSyncError | None:
    """Detect login walls / CAPTCHA pages that must not be treated as data."""
    sample = content[:12000].decode("utf-8", errors="ignore")
    lowered = sample.lower()
    if any(token in lowered for token in ("recaptcha", "hcaptcha", "g-recaptcha")):
        return ReferenceSyncError(
            "CAPTCHA_REQUIRED",
            f"Official source presented a CAPTCHA at {url}. "
            "Automated bypass is not attempted; manual_review_required.",
        )
    if "robots.txt" in url.lower() and "disallow:" in lowered:
        return ReferenceSyncError(
            "ROBOTS_DISALLOWED",
            f"robots.txt at {url} is not used as factor data.",
        )
    if (
        ('type="password"' in lowered or "type='password'" in lowered)
        and any(token in lowered for token in ("login", "sign in", "登入"))
        and b"<table" not in content[:4000].lower()
    ):
        return ReferenceSyncError(
            "LOGIN_REQUIRED",
            f"Official source requires login at {url}. "
            "Credentials are not used; result is manual_review_required.",
        )
    return None


def fetch_official_artifact(
    url: str,
    *,
    allowed_domain: str,
    tls_compatibility_mode: str = TLS_MODE_DEFAULT,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
    opener: Any | None = None,
) -> FetchResult:
    """Fetch bytes from an allowlisted official URL with safety bounds.

    TLS failures are not automatically retried with a relaxed context.
    Compatibility mode must be configured explicitly on the source.
    HTTP 403 is reported as SOURCE_ACCESS_RESTRICTED without browser
    impersonation retries.

    Flow: allowlist hostname → normalize Unicode IRI to ASCII URI → HTTPS GET.
    """
    discovered_url = _text(url)
    assert_url_allowlisted(discovered_url, allowed_domain)
    if urlparse(discovered_url).scheme.lower() != "https":
        raise ReferenceSyncError(
            "HTTPS_REQUIRED",
            f"Official sync requires HTTPS URLs; got {discovered_url!r}.",
        )
    request_url = normalize_request_url(discovered_url)
    mode = normalize_tls_compatibility_mode(tls_compatibility_mode)
    request = Request(
        request_url,
        headers=build_official_request_headers(),
        method="GET",
    )
    try:
        if opener is None:
            opener = build_official_https_opener(
                allowed_domain=allowed_domain,
                tls_compatibility_mode=mode,
            )
        with opener.open(request, timeout=timeout_seconds) as response:
            return _read_response(
                response,
                url=request_url,
                discovered_url=discovered_url,
                max_bytes=max_bytes,
                tls_compatibility_mode=mode,
            )
    except ReferenceSyncError:
        raise
    except HTTPError as exc:
        raise _http_status_error(exc.code, request_url) from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        message = str(reason)
        code = (
            "NETWORK_TIMEOUT"
            if "timed out" in message.lower()
            else "NETWORK_ERROR"
        )
        # Intentionally no automatic retry with relaxed TLS settings.
        raise ReferenceSyncError(
            code,
            f"Network error fetching {request_url}: {reason}",
        ) from exc


def _read_response(
    response: Any,
    *,
    url: str,
    max_bytes: int,
    tls_compatibility_mode: str = TLS_MODE_DEFAULT,
    discovered_url: str = "",
) -> FetchResult:
    raw_final = _text(getattr(response, "geturl", lambda: url)()) or url
    final_url = normalize_request_url(raw_final)
    status = getattr(response, "status", None)
    if status is None and hasattr(response, "getcode"):
        status = response.getcode()
    if status is not None and int(status) >= 400:
        raise _http_status_error(int(status), final_url)
    headers = getattr(response, "headers", {}) or {}
    media_type = _text(headers.get("Content-Type", "")).split(";")[0]
    chunks: list[bytes] = []
    total = 0
    while True:
        piece = response.read(64 * 1024)
        if not piece:
            break
        total += len(piece)
        if total > max_bytes:
            raise ReferenceSyncError(
                "RESPONSE_TOO_LARGE",
                f"Official artifact exceeds {max_bytes} byte limit.",
            )
        chunks.append(piece)
    content = b"".join(chunks)
    blocked = _blocked_content_error(content, final_url)
    if blocked is not None:
        raise blocked
    digest = compute_bytes_sha256(content)
    return FetchResult(
        url=url,
        final_url=final_url,
        content=content,
        media_type=media_type or "application/octet-stream",
        sha256=digest,
        byte_size=len(content),
        tls_verification=TLS_VERIFICATION_VERIFIED,
        tls_compatibility_mode=normalize_tls_compatibility_mode(
            tls_compatibility_mode
        ),
        discovered_url=_text(discovered_url) or url,
    )


def artifact_filename(
    *,
    source_id: str,
    sha256: str,
    expected_file_type: str,
    publication_date: str = "",
) -> str:
    """Deterministic artifact filename (never overwrites differing bytes)."""
    safe_source = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_id).strip("_") or "source"
    pub = re.sub(r"[^0-9A-Za-z_-]+", "", publication_date) or "unknown-pub"
    ext = _text(expected_file_type).lower().lstrip(".") or "bin"
    return f"{safe_source}__{pub}__{sha256[:12]}.{ext}"


def find_snapshot_by_sha(
    snapshots: pd.DataFrame,
    sha256: str,
) -> dict[str, str] | None:
    """Return an existing snapshot row dict when SHA-256 already known."""
    if snapshots.empty:
        return None
    matches = snapshots.loc[snapshots["sha256"] == sha256]
    if matches.empty:
        return None
    return {col: _text(matches.iloc[0][col]) for col in SNAPSHOT_COLUMNS}


def register_snapshot(
    *,
    snapshots_csv: Path,
    artifact_dir: Path,
    source_row: pd.Series | dict[str, Any],
    fetch: FetchResult,
    retrieved_at: str,
    publication_date: str = "",
    status: str = LIFECYCLE_DOWNLOADED,
    notes: str = "",
) -> dict[str, str]:
    """Persist artifact bytes and snapshot metadata; dedupe by SHA-256."""
    snapshots = _read_csv(snapshots_csv, SNAPSHOT_COLUMNS)
    existing = find_snapshot_by_sha(snapshots, fetch.sha256)
    if existing is not None:
        return existing

    source_id = _text(source_row.get("source_id"))
    file_name = artifact_filename(
        source_id=source_id,
        sha256=fetch.sha256,
        expected_file_type=_text(source_row.get("expected_file_type")),
        publication_date=publication_date,
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    local_path = artifact_dir / file_name
    if local_path.exists():
        prior = compute_bytes_sha256(local_path.read_bytes())
        if prior != fetch.sha256:
            raise ReferenceSyncError(
                "ARTIFACT_PATH_CONFLICT",
                f"Refusing to overwrite {local_path} with different bytes.",
            )
    else:
        local_path.write_bytes(fetch.content)

    retrieved_url = fetch.final_url
    discovered_url = _text(fetch.discovered_url) or retrieved_url
    retrieved_host = extract_hostname(retrieved_url)
    canonical_url = _text(source_row.get("canonical_url"))
    upstream_canonical_url = _text(
        source_row.get("upstream_canonical_url")
    ) or canonical_url
    upstream_factor_authority = _text(
        source_row.get("upstream_factor_authority")
    )
    provenance_notes = _text(notes)
    if discovered_url != retrieved_url:
        encode_note = (
            "Discovered official URL retained separately from the "
            "percent-encoded transport URI used for HTTPS retrieval."
        )
        if encode_note not in provenance_notes:
            provenance_notes = (
                f"{provenance_notes}; {encode_note}"
                if provenance_notes
                else encode_note
            )
    if retrieved_host == "ghgregistry.moenv.gov.tw" and upstream_canonical_url:
        moenv_note = (
            "Retrieved from operational MOENV GHG Registry source; "
            "upstream MOEA canonical URL retained separately and was not "
            "required for this fetch."
        )
        if moenv_note not in provenance_notes:
            provenance_notes = (
                f"{provenance_notes}; {moenv_note}"
                if provenance_notes
                else moenv_note
            )
    mismatch_note = wrong_document_for_source_note(
        reference_type=_text(source_row.get("reference_type")),
        source_id=source_id,
        retrieved_url=retrieved_url,
        discovered_url=discovered_url,
    )
    if mismatch_note and WRONG_DOCUMENT_FOR_SOURCE not in provenance_notes:
        provenance_notes = (
            f"{provenance_notes} {mismatch_note}"
            if provenance_notes
            else mismatch_note
        )

    snapshot_id = f"snap_{source_id}_{fetch.sha256[:12]}"
    row = {
        "snapshot_id": snapshot_id,
        "source_id": source_id,
        "authority": _text(source_row.get("authority")),
        "reference_type": _text(source_row.get("reference_type")),
        "canonical_url": canonical_url or upstream_canonical_url,
        "upstream_canonical_url": upstream_canonical_url,
        "upstream_factor_authority": upstream_factor_authority,
        "discovered_url": discovered_url,
        "retrieved_url": retrieved_url,
        "retrieved_host": retrieved_host,
        "retrieved_at": retrieved_at,
        "publication_date": publication_date,
        "file_name": file_name,
        "media_type": fetch.media_type,
        "sha256": fetch.sha256,
        "byte_size": str(fetch.byte_size),
        "parser_version": PARSER_VERSION,
        "local_path": str(local_path),
        "status": status,
        "tls_verification": (
            _text(fetch.tls_verification) or TLS_VERIFICATION_VERIFIED
        ),
        "tls_compatibility_mode": normalize_tls_compatibility_mode(
            fetch.tls_compatibility_mode
        ),
        "notes": provenance_notes,
    }
    snapshots = pd.concat([snapshots, pd.DataFrame([row])], ignore_index=True)
    _write_csv(snapshots_csv, snapshots, SNAPSHOT_COLUMNS)
    return row


def parse_electricity_factor_csv(content: bytes) -> ParseResult:
    """Parse the supported Taiwan electricity-factor CSV fixture format."""
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return ParseResult(
            parser_type="tw_electricity_factor_csv_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason="CSV has no header row.",
        )
    required = {
        "factor_year",
        "factor_value",
        "numerator_unit",
        "denominator_unit",
        "geography",
    }
    present = {name.strip() for name in reader.fieldnames if name}
    if not required.issubset(present):
        return ParseResult(
            parser_type="tw_electricity_factor_csv_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason=(
                "CSV headers are not the supported electricity-factor format."
            ),
        )

    records: list[dict[str, Any]] = []
    publication_dates: list[str] = []
    for raw in reader:
        category = _text(raw.get("factor_category") or raw.get("category")) or (
            "unspecified"
        )
        publication_date = _text(raw.get("publication_date"))
        if publication_date:
            publication_dates.append(publication_date)
        records.append(
            {
                "reference_type": "electricity_factor",
                "factor_year": _text(raw.get("factor_year")),
                "factor_value": _text(raw.get("factor_value")),
                "numerator_unit": _text(raw.get("numerator_unit")),
                "denominator_unit": _text(raw.get("denominator_unit")),
                "geography": _text(raw.get("geography")) or "TW",
                "activity_type": "grid_electricity",
                "combustion_context": "not_applicable",
                "gas": _text(raw.get("gas")) or "CO2e",
                "factor_category": category,
                "valid_from": _text(raw.get("valid_from")),
                "valid_to": _text(raw.get("valid_to")),
                "publication_date": publication_date,
                "source_locator": _text(raw.get("source_locator"))
                or f"electricity_factor_year={_text(raw.get('factor_year'))}",
            }
        )

    if not records:
        return ParseResult(
            parser_type="tw_electricity_factor_csv_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason="CSV contained no electricity-factor rows.",
        )

    pub = sorted(set(publication_dates))[0] if publication_dates else ""
    return ParseResult(
        parser_type="tw_electricity_factor_csv_v1",
        status=LIFECYCLE_PARSED,
        records=records,
        publication_date=pub,
        reason="Parsed supported electricity-factor CSV.",
    )


def _roc_year_to_gregorian(roc_year_text: str) -> str:
    """Convert a Republic of China year string to Gregorian year text."""
    try:
        roc_year = int(roc_year_text)
    except ValueError:
        return ""
    if roc_year <= 0:
        return ""
    return str(roc_year + 1911)


def parse_moea_electricity_news_html(content: bytes) -> ParseResult:
    """Extract categorized electricity factors from official MOEA news HTML.

    Values and categories come from the fetched page text. This function does
    not write to the active factor registry.
    """
    text = content.decode("utf-8", errors="replace")
    compact = re.sub(r"\s+", " ", text)
    publication_match = _MOEA_HTML_PUBLICATION_DATE_RE.search(compact)
    publication_date = publication_match.group(1) if publication_match else ""
    roc_match = _MOEA_HTML_ROC_YEAR_RE.search(compact)
    factor_year = (
        _roc_year_to_gregorian(roc_match.group(1)) if roc_match else ""
    )
    valid_from = f"{factor_year}-01-01" if factor_year else ""
    valid_to = f"{factor_year}-12-31" if factor_year else ""

    records: list[dict[str, Any]] = []
    seen_categories: set[str] = set()
    for pattern, category in _ELECTRICITY_HTML_CATEGORY_PATTERNS:
        if category in seen_categories:
            continue
        match = pattern.search(compact)
        if match is None:
            continue
        value = match.group(1)
        seen_categories.add(category)
        records.append(
            {
                "reference_type": "electricity_factor",
                "factor_year": factor_year,
                "factor_value": value,
                "numerator_unit": "kgCO2e",
                "denominator_unit": "kWh",
                "geography": "TW",
                "activity_type": "grid_electricity",
                "combustion_context": "not_applicable",
                "gas": "CO2e",
                "factor_category": category,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "publication_date": publication_date,
                "source_locator": (
                    f"moea_electricity_news;category={category};"
                    f"year={factor_year or 'unknown'}"
                ),
            }
        )

    if len(records) < 2:
        return ParseResult(
            parser_type="tw_moea_electricity_landing_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason=(
                "MOEA electricity news HTML did not contain enough "
                "categorized factor values for deterministic parsing."
            ),
        )
    return ParseResult(
        parser_type="tw_moea_electricity_landing_v1",
        status=LIFECYCLE_PARSED,
        records=records,
        publication_date=publication_date,
        reason=(
            "Parsed categorized electricity factors from official MOEA "
            "news HTML."
        ),
    )


def _strip_html_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


class _VisibleTextHTMLParser(HTMLParser):
    """Deterministic HTML → visible-text converter (stdlib only)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if lowered in {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "td", "th"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if lowered in {"p", "div", "li", "tr", "h1", "h2", "h3", "td", "th"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._chunks.append(data)

    def text(self) -> str:
        return "".join(self._chunks)


def _html_to_visible_text(value: str) -> str:
    """Convert HTML to normalized visible text without relying on CSS classes."""
    parser = _VisibleTextHTMLParser()
    try:
        parser.feed(value)
        parser.close()
        text = parser.text()
    except Exception:
        text = _strip_html_tags(value)
    text = html_module.unescape(text)
    text = (
        text.replace("\xa0", " ")
        .replace("\u3000", " ")
        .replace("\u200b", "")
    )
    # Tolerate broken official markup such as "</ div >".
    text = re.sub(r"</\s+>", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def _normalize_moenv_date_token(year: str, month: str, day: str) -> str:
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _extract_moenv_announcement_block(raw_html: str) -> str:
    """Return visible text for the single 2026-06-17 electricity announcement."""
    # 1) Live ASP.NET NewsList items (news-list-date / news-list-title).
    for match in _MOENV_LIST_ITEM_RE.finditer(raw_html):
        date_text = _html_to_visible_text(match.group(2))
        date_match = _MOENV_DATE_TOKEN_RE.search(date_text)
        if date_match is None:
            continue
        date_norm = _normalize_moenv_date_token(
            date_match.group(1), date_match.group(2), date_match.group(3)
        )
        item_text = _html_to_visible_text(match.group(0))
        if (
            date_norm == _MOENV_ANNOUNCEMENT_DATE
            and _MOENV_ANNOUNCEMENT_TITLE_TOKEN in item_text
        ):
            return item_text

    # 2) Simplified fixture markup (news-item / news-date / news-title).
    for item in _MOENV_NEWS_ITEM_RE.findall(raw_html):
        date_match = _MOENV_NEWS_DATE_RE.search(item)
        title_match = _MOENV_NEWS_TITLE_RE.search(item)
        if date_match is None or title_match is None:
            continue
        date_text = _normalize_moenv_date_token(
            date_match.group(1), date_match.group(2), date_match.group(3)
        )
        title_text = _html_to_visible_text(title_match.group(1))
        if (
            date_text == _MOENV_ANNOUNCEMENT_DATE
            and _MOENV_ANNOUNCEMENT_TITLE_TOKEN in title_text
        ):
            return _html_to_visible_text(item)

    # 3) CSS-independent fallback on full-page visible text.
    # Require both the announcement date and the stable title phrase, then
    # bound the block to the next news-date token when present.
    visible = _html_to_visible_text(raw_html)
    title_idx = visible.find(_MOENV_ANNOUNCEMENT_TITLE_TOKEN)
    if title_idx < 0:
        return ""
    date_matches = list(_MOENV_DATE_TOKEN_RE.finditer(visible))
    announcement_date = None
    for date_match in date_matches:
        date_norm = _normalize_moenv_date_token(
            date_match.group(1), date_match.group(2), date_match.group(3)
        )
        if date_norm != _MOENV_ANNOUNCEMENT_DATE:
            continue
        # Prefer a date token near the title phrase.
        if abs(date_match.start() - title_idx) <= 400:
            announcement_date = date_match
            break
        if announcement_date is None:
            announcement_date = date_match
    if announcement_date is None:
        return ""
    start = max(0, min(announcement_date.start(), title_idx) - 80)
    end = max(announcement_date.end(), title_idx) + 1800
    for date_match in date_matches:
        if date_match.start() <= max(announcement_date.start(), title_idx):
            continue
        end = min(end, date_match.start())
        break
    block = visible[start:end].strip()
    if _MOENV_ANNOUNCEMENT_TITLE_TOKEN not in block:
        return ""
    return block


def parse_moenv_electricity_news_html(content: bytes) -> ParseResult:
    """Parse MOENV GHG Registry news for the enterprise electricity announcement.

    Locates only the 2026-06-17 announcement by date/title evidence, then
    extracts categorized factors from that bounded block. Does not scrape
    unrelated news entries or invent values.
    """
    raw_html = content.decode("utf-8", errors="replace")
    block = _extract_moenv_announcement_block(raw_html)
    if not block:
        return ParseResult(
            parser_type="tw_moenv_electricity_news_landing_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason=(
                "Expected MOENV 2026-06-17 electricity-factor announcement "
                "was not found; source format may have changed."
            ),
        )

    compact = re.sub(r"\s+", " ", block)
    roc_match = _MOENV_FACTOR_YEAR_RE.search(compact)
    if roc_match is None:
        roc_match = _MOEA_HTML_ROC_YEAR_RE.search(compact)
    factor_year = (
        _roc_year_to_gregorian(roc_match.group(1)) if roc_match else ""
    )
    # Annual validity follows explicit ROC "114年度" semantics, not publication.
    valid_from = f"{factor_year}-01-01" if factor_year else ""
    valid_to = f"{factor_year}-12-31" if factor_year else ""
    publication_date = _MOENV_ANNOUNCEMENT_DATE
    upstream = (
        "Taiwan Ministry of Economic Affairs / Energy Administration"
    )

    intended_use_by_category = {
        "public_sales_average": "public_electricity_sales_average",
        "industrial_enterprise_inventory": (
            "enterprise GHG inventory / disclosure"
        ),
        "residential": "residential_electricity",
    }
    applicability_by_category = {
        "public_sales_average": (
            "Public electricity-sales average factor. Not interchangeable "
            "with industrial or residential factors."
        ),
        "industrial_enterprise_inventory": (
            "Enterprise inventory / disclosure uses the industrial "
            "electricity factor for applicable business electricity tariff "
            "categories. Do not assume applicability for every grid-"
            "electricity activity without tariff/use context."
        ),
        "residential": (
            "Residential electricity factor. Not interchangeable with "
            "industrial/enterprise-inventory factor."
        ),
    }

    records: list[dict[str, Any]] = []
    seen_categories: set[str] = set()
    for pattern, category in _MOENV_ELECTRICITY_CATEGORY_PATTERNS:
        if category in seen_categories:
            continue
        match = pattern.search(compact)
        if match is None:
            continue
        value = match.group(1)
        seen_categories.add(category)
        records.append(
            {
                "reference_type": REF_TYPE_ELECTRICITY_ENTERPRISE,
                "factor_year": factor_year,
                "factor_value": value,
                "numerator_unit": "kgCO2e",
                "denominator_unit": "kWh",
                "geography": "TW",
                "activity_type": "grid_electricity",
                "combustion_context": "not_applicable",
                "gas": "CO2e",
                "factor_category": category,
                "intended_use": intended_use_by_category.get(category, ""),
                "applicability_notes": applicability_by_category.get(
                    category, ""
                ),
                "upstream_factor_authority": upstream,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "publication_date": publication_date,
                "source_locator": (
                    "moenv_ghg_registry_news;"
                    f"date={publication_date};"
                    f"category={category};"
                    f"year={factor_year or 'unknown'}"
                ),
            }
        )

    required = {
        "public_sales_average",
        "industrial_enterprise_inventory",
        "residential",
    }
    if seen_categories != required:
        missing = sorted(required - seen_categories)
        return ParseResult(
            parser_type="tw_moenv_electricity_news_landing_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason=(
                "MOENV electricity announcement was found but categorized "
                "factor values could not be extracted deterministically; "
                f"missing categories: {', '.join(missing) or 'ambiguous'}; "
                "source format may have changed."
            ),
        )
    if not factor_year:
        return ParseResult(
            parser_type="tw_moenv_electricity_news_landing_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason=(
                "MOENV electricity announcement categories were found but "
                "ROC factor year (114年度) could not be determined "
                "deterministically."
            ),
        )
    return ParseResult(
        parser_type="tw_moenv_electricity_news_landing_v1",
        status=LIFECYCLE_PARSED,
        records=records,
        publication_date=publication_date,
        reason=(
            "Parsed categorized enterprise-inventory electricity factors "
            "from the official MOENV 2026-06-17 announcement."
        ),
    )


def parse_fuel_heating_values_csv(content: bytes) -> ParseResult:
    """Parse a supported structured fuel-heating-value CSV."""
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return ParseResult(
            parser_type="tw_fuel_heating_values_csv_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason="CSV has no header row.",
        )
    required = {"fuel_type", "heating_value", "unit", "factor_year"}
    present = {name.strip() for name in reader.fieldnames if name}
    if not required.issubset(present):
        return ParseResult(
            parser_type="tw_fuel_heating_values_csv_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason="CSV headers are not the supported heating-value format.",
        )

    records: list[dict[str, Any]] = []
    for raw in reader:
        records.append(
            {
                "reference_type": "fuel_heating_values",
                "fuel_type": _text(raw.get("fuel_type")),
                "factor_value": _text(raw.get("heating_value")),
                "numerator_unit": _text(raw.get("unit")),
                "denominator_unit": "",
                "factor_year": _text(raw.get("factor_year")),
                "geography": _text(raw.get("geography")) or "TW",
                "activity_type": _text(raw.get("activity_type")),
                "combustion_context": _text(raw.get("combustion_context")),
                "gas": "",
                "factor_category": _text(raw.get("fuel_type")),
                "valid_from": _text(raw.get("valid_from")),
                "valid_to": _text(raw.get("valid_to")),
                "publication_date": _text(raw.get("publication_date")),
                "source_locator": _text(raw.get("source_locator"))
                or (
                    f"fuel={_text(raw.get('fuel_type'))};"
                    f"year={_text(raw.get('factor_year'))}"
                ),
            }
        )
    if not records:
        return ParseResult(
            parser_type="tw_fuel_heating_values_csv_v1",
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason="CSV contained no heating-value rows.",
        )
    return ParseResult(
        parser_type="tw_fuel_heating_values_csv_v1",
        status=LIFECYCLE_PARSED,
        records=records,
        publication_date="",
        reason="Parsed supported fuel-heating-value CSV.",
    )


def extract_html_hrefs(content: bytes) -> list[str]:
    """Extract raw href values from an HTML document."""
    text = content.decode("utf-8", errors="replace")
    return [match.strip() for match in _HREF_RE.findall(text) if match.strip()]


def resolve_and_filter_allowlisted_urls(
    hrefs: list[str] | tuple[str, ...],
    *,
    landing_url: str,
    allowed_domain: str,
) -> list[str]:
    """Resolve hrefs and keep only allowlisted absolute URLs.

    Non-allowlisted links are ignored (never followed).
    """
    accepted: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        absolute = urljoin(landing_url, href)
        try:
            assert_url_allowlisted(absolute, allowed_domain)
        except ReferenceSyncError:
            continue
        if absolute not in seen:
            seen.add(absolute)
            accepted.append(absolute)
    return accepted


def _extension_rank(url: str, prefer_extensions: tuple[str, ...]) -> int:
    path = urlparse(url).path.lower()
    for index, extension in enumerate(prefer_extensions):
        if path.endswith(extension.lower()):
            return index
    return len(prefer_extensions) + 1


def discover_official_attachments(
    content: bytes,
    *,
    landing_url: str,
    allowed_domain: str,
    parser_type: str,
    prefer_extensions: tuple[str, ...] = (".ods", ".csv", ".xlsx", ".pdf"),
    required_url_keywords: tuple[str, ...] = (),
) -> DiscoveryResult:
    """Discover allowlisted official attachment URLs from a landing page."""
    hrefs = extract_html_hrefs(content)
    allowlisted = resolve_and_filter_allowlisted_urls(
        hrefs,
        landing_url=landing_url,
        allowed_domain=allowed_domain,
    )
    if required_url_keywords:
        lowered = [item.lower() for item in required_url_keywords]
        allowlisted = [
            url
            for url in allowlisted
            if any(token in url.lower() for token in lowered)
        ]
    ranked = sorted(
        allowlisted,
        key=lambda url: (
            _extension_rank(url, prefer_extensions),
            url,
        ),
    )
    if not ranked:
        return DiscoveryResult(
            parser_type=parser_type,
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            landing_url=landing_url,
            reason=(
                "No allowlisted official attachment URL was discovered "
                "on the landing page."
            ),
        )
    chosen = ranked[0]
    path = urlparse(chosen).path.lower()
    extension = ""
    for item in prefer_extensions:
        if path.endswith(item.lower()):
            extension = item.lower()
            break
    return DiscoveryResult(
        parser_type=parser_type,
        status=LIFECYCLE_DISCOVERED,
        landing_url=landing_url,
        artifact_url=chosen,
        preferred_extension=extension,
        candidate_urls=tuple(ranked),
        reason=(
            f"Discovered allowlisted attachment {chosen!r} "
            f"from official landing page."
        ),
    )


def discover_from_landing_parser(
    content: bytes,
    *,
    landing_url: str,
    allowed_domain: str,
    parser_type: str,
) -> DiscoveryResult:
    """Dispatch landing-page discovery for a configured parser_type."""
    parser = _text(parser_type)
    if parser == "tw_moea_electricity_landing_v1":
        return discover_official_attachments(
            content,
            landing_url=landing_url,
            allowed_domain=allowed_domain,
            parser_type=parser,
            prefer_extensions=(".csv", ".ods", ".xlsx", ".pdf"),
        )
    if parser == "tw_moenv_electricity_news_landing_v1":
        # Production enterprise electricity uses retrieval_strategy=parse_landing
        # and does not call this path. Kept for explicit discovery unit tests.
        return discover_official_attachments(
            content,
            landing_url=landing_url,
            allowed_domain=allowed_domain,
            parser_type=parser,
            prefer_extensions=(".csv", ".ods", ".xlsx", ".pdf"),
        )
    if parser == "tw_moenv_file_downloads_landing_v1":
        return discover_official_attachments(
            content,
            landing_url=landing_url,
            allowed_domain=allowed_domain,
            parser_type=parser,
            prefer_extensions=(".ods", ".pdf", ".csv", ".xlsx"),
        )
    if parser == "tw_moenv_news_heating_values_landing_v1":
        # Discover allowlisted attachments from the official registry/news site.
        return discover_official_attachments(
            content,
            landing_url=landing_url,
            allowed_domain=allowed_domain,
            parser_type=parser,
            prefer_extensions=(".csv", ".ods", ".xlsx", ".pdf"),
        )
    return DiscoveryResult(
        parser_type=parser or "unknown",
        status=LIFECYCLE_NEEDS_PARSER_REVIEW,
        landing_url=landing_url,
        reason=f"Unsupported landing discovery parser_type {parser!r}.",
    )


def is_landing_discovery_parser(parser_type: str) -> bool:
    """Return True when the source uses landing-page attachment discovery."""
    return _text(parser_type) in LANDING_DISCOVERY_PARSERS


def artifact_parser_for_discovery(
    *,
    landing_parser_type: str,
    artifact_url: str,
    reference_type: str,
) -> str:
    """Choose a deterministic artifact parser after discovery, if available."""
    path = urlparse(artifact_url).path.lower()
    if landing_parser_type == "tw_moea_electricity_landing_v1" and path.endswith(
        ".csv"
    ):
        return "tw_electricity_factor_csv_v1"
    if (
        landing_parser_type == "tw_moenv_electricity_news_landing_v1"
        and path.endswith(".csv")
    ):
        return "tw_electricity_factor_csv_v1"
    if (
        landing_parser_type == "tw_moenv_news_heating_values_landing_v1"
        and path.endswith(".csv")
    ):
        return "tw_fuel_heating_values_csv_v1"
    if landing_parser_type == "tw_moenv_file_downloads_landing_v1" and path.endswith(
        (".ods", ".xlsx")
    ):
        if reference_type == "gwp_reference":
            return "tw_moenv_gwp_ods_v1"
        if reference_type in {REF_TYPE_GENERAL_EF, REF_TYPE_FUEL_EF}:
            return "tw_moenv_general_emission_factors_ods_v1"
    if reference_type in ELECTRICITY_CANDIDATE_REF_TYPES and path.endswith(
        ".csv"
    ):
        return "tw_electricity_factor_csv_v1"
    return "needs_parser_review"


def parse_artifact(
    content: bytes,
    *,
    parser_type: str,
    expected_file_type: str = "",
) -> ParseResult:
    """Dispatch to a deterministic parser or return needs_parser_review."""
    parser = _text(parser_type)
    if parser == "tw_electricity_factor_csv_v1":
        return parse_electricity_factor_csv(content)
    if parser == "tw_fuel_heating_values_csv_v1":
        return parse_fuel_heating_values_csv(content)
    if parser == "tw_moenv_general_emission_factors_ods_v1":
        from carbon_ledger.official_table_parse import (
            parse_moenv_ods_fuel_emission_factors,
        )

        return parse_moenv_ods_fuel_emission_factors(content)
    if parser == "tw_moenv_gwp_ods_v1":
        from carbon_ledger.official_table_parse import parse_moenv_ods_gwp

        return parse_moenv_ods_gwp(content)
    if parser == "purchased_steel_average_data_v1":
        from carbon_ledger.official_table_parse import (
            steel_average_data_not_configured_result,
        )

        return steel_average_data_not_configured_result()
    if parser == "cfp_p_02_open_data_v1":
        from carbon_ledger.official_table_parse import parse_cfp_p_02_json

        return parse_cfp_p_02_json(content)
    if parser == "tw_moenv_electricity_news_landing_v1":
        html_parsed = parse_moenv_electricity_news_html(content)
        if html_parsed.status == LIFECYCLE_PARSED:
            return html_parsed
        return html_parsed
    if parser == "tw_moea_electricity_landing_v1":
        html_parsed = parse_moea_electricity_news_html(content)
        if html_parsed.status == LIFECYCLE_PARSED:
            return html_parsed
        return ParseResult(
            parser_type=parser,
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason=(
                "MOEA landing HTML did not yield categorized factors; "
                "use attachment discovery when available. "
                f"{html_parsed.reason}"
            ),
        )
    if parser in LANDING_DISCOVERY_PARSERS:
        return ParseResult(
            parser_type=parser,
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason=(
                "Landing-page HTML was supplied to parse_artifact; "
                "use discover_from_landing_parser then parse the artifact."
            ),
        )
    if parser == "needs_parser_review":
        return ParseResult(
            parser_type=parser,
            status=LIFECYCLE_NEEDS_PARSER_REVIEW,
            reason=(
                "Source is registered for discovery/snapshot/versioning only. "
                f"No deterministic parser is available yet "
                f"(expected_file_type={expected_file_type or 'unknown'})."
            ),
        )
    return ParseResult(
        parser_type=parser or "unknown",
        status=LIFECYCLE_NEEDS_PARSER_REVIEW,
        reason=f"Unsupported parser_type {parser!r}.",
    )


def _candidate_id(snapshot_id: str, record: dict[str, Any]) -> str:
    basis = "|".join(
        [
            snapshot_id,
            _text(record.get("reference_type")),
            _text(record.get("factor_year")),
            _text(record.get("factor_category") or record.get("fuel_type")),
            _text(record.get("geography")),
            _text(record.get("activity_type")),
            _text(record.get("combustion_context") or record.get("factor_context")),
            _text(record.get("gas")),
            _text(record.get("assessment_basis")),
            _text(record.get("factor_value")),
            _text(record.get("valid_from")),
            _text(record.get("valid_to")),
            _text(record.get("source_record_id") or record.get("source_locator")),
            _text(record.get("steel_product_type")),
        ]
    )
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]
    return f"cand_{digest}"


def upsert_candidates_from_parse(
    *,
    candidates_csv: Path,
    snapshot: dict[str, str],
    source_row: pd.Series | dict[str, Any],
    parsed: ParseResult,
) -> list[dict[str, str]]:
    """Create or reuse candidate rows from parser output (inactive by default)."""
    candidates = _read_csv(candidates_csv, CANDIDATE_COLUMNS)
    existing_ids = (
        set(candidates["candidate_id"].tolist())
        if not candidates.empty
        else set()
    )
    created: list[dict[str, str]] = []

    if parsed.status == LIFECYCLE_NEEDS_PARSER_REVIEW:
        review_id = f"cand_review_{snapshot['snapshot_id'][-12:]}"
        if review_id not in existing_ids:
            mismatch = wrong_document_issues(
                reference_type=_text(source_row.get("reference_type")),
                source_id=_text(source_row.get("source_id")),
                locator=_text(snapshot.get("retrieved_url")),
                source_url=_text(snapshot.get("retrieved_url")),
                source_location=_text(snapshot.get("retrieved_url")),
                existing_text=" ".join(
                    [
                        parsed.reason,
                        _text(snapshot.get("notes")),
                    ]
                ),
            )
            reason = parsed.reason
            if mismatch and WRONG_DOCUMENT_FOR_SOURCE not in reason:
                reason = (
                    f"{WRONG_DOCUMENT_FOR_SOURCE}; {reason}"
                    if reason
                    else WRONG_DOCUMENT_FOR_SOURCE
                )
            row = {
                "candidate_id": review_id,
                "snapshot_id": snapshot["snapshot_id"],
                "source_id": _text(source_row.get("source_id")),
                "reference_type": _text(source_row.get("reference_type")),
                "factor_year": "",
                "valid_from": "",
                "valid_to": "",
                "geography": "",
                "activity_type": "",
                "combustion_context": "",
                "gas": "",
                "factor_value": "",
                "numerator_unit": "",
                "denominator_unit": "",
                "factor_category": "",
                "intended_use": "",
                "applicability_notes": "",
                "upstream_factor_authority": _text(
                    source_row.get("upstream_factor_authority")
                )
                or _text(snapshot.get("upstream_factor_authority")),
                "publication_date": _text(snapshot.get("publication_date")),
                "source_locator": snapshot.get("retrieved_url", ""),
                "validation_status": VALIDATION_PENDING,
                "lifecycle_status": LIFECYCLE_NEEDS_PARSER_REVIEW,
                "parser_version": PARSER_VERSION,
                "reason": reason,
                "notes": (
                    "Snapshot retained; values not guessed "
                    "from unstructured text."
                ),
                "candidate_type": _text(source_row.get("reference_type")),
                "target_registry": "",
                "source_url": _text(snapshot.get("retrieved_url")),
                "source_snapshot_path": _text(snapshot.get("local_path")),
                "source_sha256": _text(snapshot.get("sha256")),
                "source_location": _text(snapshot.get("retrieved_url")),
                "reporting_year": "",
                "factor_context": "",
                "refrigerant": "",
                "assessment_basis": "",
                "factor_unit": "",
                "validation_messages": reason,
                "created_at": _text(snapshot.get("retrieved_at")),
            }
            candidates = pd.concat([candidates, pd.DataFrame([row])], ignore_index=True)
            created.append(row)
        _write_csv(candidates_csv, candidates, CANDIDATE_COLUMNS)
        return created

    for record in parsed.records:
        cand_id = _candidate_id(snapshot["snapshot_id"], record)
        if cand_id in existing_ids:
            continue
        row = {
            "candidate_id": cand_id,
            "snapshot_id": snapshot["snapshot_id"],
            "source_id": _text(source_row.get("source_id")),
            "reference_type": _text(record.get("reference_type"))
            or _text(source_row.get("reference_type")),
            "factor_year": _text(record.get("factor_year")),
            "valid_from": _text(record.get("valid_from")),
            "valid_to": _text(record.get("valid_to")),
            "geography": _text(record.get("geography")),
            "activity_type": _text(record.get("activity_type")),
            "combustion_context": _text(record.get("combustion_context")),
            "gas": _text(record.get("gas")),
            "factor_value": _text(record.get("factor_value")),
            "numerator_unit": _text(record.get("numerator_unit")),
            "denominator_unit": _text(record.get("denominator_unit")),
            "factor_category": _text(record.get("factor_category")),
            "intended_use": _text(record.get("intended_use")),
            "applicability_notes": _text(record.get("applicability_notes")),
            "upstream_factor_authority": _text(
                record.get("upstream_factor_authority")
            )
            or _text(source_row.get("upstream_factor_authority"))
            or _text(snapshot.get("upstream_factor_authority")),
            "publication_date": _text(record.get("publication_date"))
            or _text(snapshot.get("publication_date")),
            "source_locator": _text(record.get("source_locator")),
            "validation_status": VALIDATION_PENDING,
            "lifecycle_status": LIFECYCLE_CANDIDATE,
            "parser_version": PARSER_VERSION,
            "reason": "Awaiting deterministic validation before activation.",
            "notes": _text(record.get("applicability_notes")),
            "candidate_type": _text(record.get("candidate_type"))
            or _text(record.get("reference_type"))
            or _text(source_row.get("reference_type")),
            "target_registry": _text(record.get("target_registry")),
            "source_url": _text(snapshot.get("retrieved_url")),
            "source_snapshot_path": _text(snapshot.get("local_path")),
            "source_sha256": _text(snapshot.get("sha256")),
            "source_location": _text(record.get("source_locator"))
            or _text(snapshot.get("retrieved_url")),
            "reporting_year": _text(record.get("reporting_year")),
            "factor_context": _text(record.get("factor_context"))
            or _text(record.get("combustion_context")),
            "refrigerant": _text(record.get("refrigerant")),
            "assessment_basis": _text(record.get("assessment_basis")),
            "factor_unit": _text(record.get("factor_unit"))
            or (
                f"{_text(record.get('numerator_unit'))}/"
                f"{_text(record.get('denominator_unit'))}"
                if _text(record.get("numerator_unit"))
                and _text(record.get("denominator_unit"))
                else _text(record.get("numerator_unit"))
            ),
            "validation_messages": "",
            "created_at": _text(snapshot.get("retrieved_at")),
        }
        candidates = pd.concat([candidates, pd.DataFrame([row])], ignore_index=True)
        existing_ids.add(cand_id)
        created.append(row)

    _write_csv(candidates_csv, candidates, CANDIDATE_COLUMNS)
    return created


def _parse_date(value: str) -> date | None:
    text = _text(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    stamp = pd.Timestamp(parsed)
    return date(int(stamp.year), int(stamp.month), int(stamp.day))


def _official_applicability_issues(candidate: dict[str, Any] | pd.Series) -> list[str]:
    """Fail closed when official applicability is missing or copied from a notice."""
    issues: list[str] = []
    valid_from = _parse_date(_text(candidate.get("valid_from")))
    valid_to = _parse_date(_text(candidate.get("valid_to")))
    publication_date = _parse_date(_text(candidate.get("publication_date")))
    if valid_from is None:
        issues.append(
            "official applicability period is missing; "
            "publication_date is not a substitute for valid_from; "
            "manual_review_required"
        )
    elif valid_to is not None and valid_from > valid_to:
        issues.append("valid_from must be on or before valid_to")
    if (
        publication_date is not None
        and valid_from is not None
        and publication_date == valid_from
    ):
        issues.append("publication_date must not be used as valid_from")
    return issues


def validate_candidate_row(candidate: dict[str, Any] | pd.Series) -> list[str]:
    """Return validation issue messages; empty list means passed."""
    issues: list[str] = list(wrong_document_issues(candidate))
    lifecycle = _text(candidate.get("lifecycle_status"))
    if lifecycle == LIFECYCLE_NEEDS_PARSER_REVIEW:
        issues.append("Candidate requires parser review; values were not extracted.")
        return issues

    ref_type = _text(candidate.get("reference_type"))
    candidate_type = _text(candidate.get("candidate_type")) or ref_type
    if candidate_type == REF_TYPE_STEEL or ref_type == REF_TYPE_STEEL:
        if not _text(candidate.get("factor_value")):
            issues.append("official CFP_P_02 coe/factor_value is required")
        product_name = _text(candidate.get("factor_category")) or _text(
            candidate.get("steel_product_type")
        )
        if not product_name:
            issues.append("official CFP_P_02 steel product name is required")
        if not _text(candidate.get("source_id")):
            issues.append("source_id is required")
        if not _text(candidate.get("snapshot_id")):
            issues.append("snapshot_id is required")
        if not (
            _text(candidate.get("source_locator"))
            or _text(candidate.get("source_sha256"))
        ):
            issues.append("source_record_id or snapshot hash is required")
        if _text(candidate.get("valid_from")):
            issues.append(
                "CFP_P_02 does not provide valid_from; announcementyear "
                "must not be copied into valid_from"
            )
        if _text(candidate.get("valid_to")):
            issues.append(
                "CFP_P_02 does not provide valid_to; do not invent an "
                "official applicability end date"
            )
        return issues

    value_text = _text(candidate.get("factor_value"))
    try:
        number = Decimal(value_text.replace(",", ""))
    except (InvalidOperation, ValueError):
        issues.append("factor_value is not numeric")
        number = None
    if number is None or not number.is_finite() or number <= 0:
        issues.append("factor_value must be a finite Decimal greater than zero")

    if not _text(candidate.get("source_id")):
        issues.append("source_id is required")
    if not _text(candidate.get("factor_year")):
        issues.append("factor_year is required")
    if not _text(candidate.get("geography")):
        issues.append("geography is required")
    if not _text(candidate.get("source_locator")):
        issues.append("source_locator is required")
    if not _text(candidate.get("snapshot_id")):
        issues.append("snapshot_id is required")
    if not _text(candidate.get("parser_version")):
        issues.append("parser_version is required")
    if not (
        _text(candidate.get("source_sha256"))
        or _text(candidate.get("snapshot_id"))
    ):
        issues.append("source snapshot hash or snapshot_id is required")

    if ref_type in ELECTRICITY_CANDIDATE_REF_TYPES:
        if _text(candidate.get("activity_type")) != "grid_electricity":
            issues.append(
                f"{ref_type} activity_type must be grid_electricity"
            )
        if _text(candidate.get("numerator_unit")) not in SUPPORTED_NUMERATOR_UNITS:
            issues.append("unsupported numerator_unit")
        if _text(candidate.get("denominator_unit")) not in SUPPORTED_DENOMINATOR_UNITS:
            issues.append("unsupported denominator_unit")
        category = _text(candidate.get("factor_category")) or "unspecified"
        if category not in SUPPORTED_ELECTRICITY_CATEGORIES:
            issues.append(f"unsupported electricity factor_category {category!r}")
        valid_from = _parse_date(_text(candidate.get("valid_from")))
        valid_to = _parse_date(_text(candidate.get("valid_to")))
        if valid_from is None or valid_to is None:
            issues.append(
                f"{ref_type} requires explicit valid_from and valid_to "
                "(publication_date is not a substitute)"
            )
        elif valid_from > valid_to:
            issues.append("valid_from must be on or before valid_to")
        publication_date = _parse_date(_text(candidate.get("publication_date")))
        if (
            publication_date is not None
            and valid_from is not None
            and publication_date == valid_from
            and _text(candidate.get("notes")).find("publication_as_validity") >= 0
        ):
            issues.append("publication_date must not be used as validity")
        if (
            ref_type == REF_TYPE_ELECTRICITY_ENTERPRISE
            and category in ENTERPRISE_INVENTORY_CATEGORIES
        ):
            intended_use = _text(candidate.get("intended_use"))
            if intended_use not in ENTERPRISE_INVENTORY_INTENDED_USES:
                issues.append(
                    "industrial enterprise-inventory factor requires "
                    "intended_use for enterprise GHG inventory / disclosure"
                )

    if ref_type == "fuel_heating_values":
        if not _text(candidate.get("factor_category")):
            issues.append("fuel_type/factor_category is required")
        unit = _text(candidate.get("numerator_unit"))
        combined = _text(candidate.get("factor_unit"))
        if (
            unit not in SUPPORTED_HEATING_UNITS
            and combined not in SUPPORTED_HEATING_UNITS
            and unit not in {"kcal", "MJ"}
        ):
            issues.append("unsupported heating-value unit")

    if ref_type in {REF_TYPE_FUEL_EF, REF_TYPE_GENERAL_EF}:
        if not _text(candidate.get("activity_type")):
            issues.append("activity_type is required")
        if not _text(candidate.get("gas")):
            issues.append("gas is required")
        context = _text(candidate.get("factor_context")) or _text(
            candidate.get("combustion_context")
        )
        if not context:
            issues.append("factor_context/combustion_context is required")
        if not _text(candidate.get("geography")):
            issues.append("geography is required")
        if _text(candidate.get("denominator_unit")) != "TJ":
            issues.append("fuel emission factor denominator_unit must be TJ")
        if _text(candidate.get("numerator_unit")) not in {
            "kgCO2",
            "kgCH4",
            "kgN2O",
        }:
            issues.append("unsupported fuel emission-factor numerator_unit")
        issues.extend(_official_applicability_issues(candidate))

    if ref_type == REF_TYPE_GWP:
        if not _text(candidate.get("gas")):
            issues.append("GWP gas is required")
        context = _text(candidate.get("factor_context")) or _text(
            candidate.get("combustion_context")
        )
        if not context:
            issues.append("GWP emission context is required")
        basis = _text(candidate.get("assessment_basis"))
        if basis not in SUPPORTED_GWP_ASSESSMENTS:
            issues.append("GWP assessment_basis must be an explicit AR5 or AR6 value")
        if not _text(candidate.get("geography")):
            issues.append("geography is required")
        issues.extend(_official_applicability_issues(candidate))

    return issues


def _steel_candidate_is_new(frame: pd.DataFrame, retrieved_at: str) -> bool:
    if frame.empty:
        return False
    created = _text(frame.iloc[0].get("created_at"))
    retrieved = _text(retrieved_at)
    if not retrieved:
        return True
    return created == retrieved


def validate_candidates(
    candidates_csv: Path,
    *,
    candidate_ids: list[str] | None = None,
    official_sources_csv: Path | None = None,
) -> pd.DataFrame:
    """Validate pending candidates and update lifecycle/validation fields."""
    candidates = _read_csv(candidates_csv, CANDIDATE_COLUMNS)
    allowed_source_ids: set[str] | None = None
    if official_sources_csv is not None and Path(official_sources_csv).is_file():
        sources = load_official_sources(official_sources_csv)
        allowed_source_ids = {
            _text(value) for value in sources.get("source_id", pd.Series(dtype=str))
            if _text(value)
        }
    if candidates.empty:
        return candidates
    for index, row in candidates.iterrows():
        if candidate_ids is not None and row["candidate_id"] not in candidate_ids:
            continue
        if _text(row.get("lifecycle_status")) == LIFECYCLE_ACTIVE:
            continue
        issues = validate_candidate_row(row)
        source_id = _text(row.get("source_id"))
        if allowed_source_ids is not None and source_id not in allowed_source_ids:
            issues.append(
                "source_id is not an allowlisted official reference source"
            )
        for token in wrong_document_issues(row):
            if token not in issues:
                issues.insert(0, token)
        if issues:
            candidates.at[index, "validation_status"] = VALIDATION_FAILED
            if (
                WRONG_DOCUMENT_FOR_SOURCE in issues
                or _text(row.get("lifecycle_status")) != LIFECYCLE_NEEDS_PARSER_REVIEW
            ):
                candidates.at[index, "lifecycle_status"] = LIFECYCLE_REJECTED
            candidates.at[index, "reason"] = "; ".join(issues)
        else:
            candidates.at[index, "validation_status"] = VALIDATION_PASSED
            candidates.at[index, "lifecycle_status"] = LIFECYCLE_VALIDATED
            candidates.at[index, "reason"] = (
                "Passed deterministic validation; not active until activation."
            )
            candidates.at[index, "validation_messages"] = ""
        if issues:
            candidates.at[index, "validation_messages"] = "; ".join(issues)
    _write_csv(candidates_csv, candidates, CANDIDATE_COLUMNS)
    return candidates


def _active_duplicate_exists(
    emission_factors: pd.DataFrame,
    candidate: dict[str, Any],
) -> bool:
    if emission_factors.empty:
        return False
    category = _text(candidate.get("factor_category")) or "unspecified"
    year = _text(candidate.get("factor_year"))
    mask = (
        (emission_factors["activity_type"] == _text(candidate.get("activity_type")))
        & (emission_factors["geography"] == _text(candidate.get("geography")))
        & (emission_factors["factor_year"] == year)
        & (emission_factors["gas"] == _text(candidate.get("gas")))
        & (emission_factors["numerator_unit"] == _text(candidate.get("numerator_unit")))
        & (
            emission_factors["denominator_unit"]
            == _text(candidate.get("denominator_unit"))
        )
        & (emission_factors["valid_from"] == _text(candidate.get("valid_from")))
        & (emission_factors["valid_to"] == _text(candidate.get("valid_to")))
        & (emission_factors["factor_status"] != "inactive")
    )
    matches = emission_factors.loc[mask]
    if matches.empty:
        return False
    # Categories are not interchangeable: only the same category counts as
    # an equivalent active factor. Legacy 2024 rows without a category suffix
    # still collide within the same year/dates when category is unspecified.
    category_token = f"category={category}"
    id_token = f"ef_tw_grid_electricity_{year}_{category}"
    for _, row in matches.iterrows():
        factor_id = _text(row.get("factor_id"))
        notes = _text(row.get("notes"))
        if category_token in notes or factor_id == id_token or factor_id.startswith(
            f"{id_token}_"
        ):
            return True
        if category in {"unspecified", "utility_average"} and factor_id == (
            f"ef_tw_grid_electricity_{year}"
        ):
            return True
    return False


def format_candidate_activation_summary(
    candidate: dict[str, Any] | pd.Series,
    *,
    snapshot: dict[str, Any] | pd.Series | None = None,
) -> str:
    """Return the human-readable pre-activation review summary."""
    row = {
        key: _text(candidate.get(key))
        for key in (
            "candidate_id",
            "factor_year",
            "factor_category",
            "factor_value",
            "numerator_unit",
            "denominator_unit",
            "intended_use",
            "lifecycle_status",
            "validation_status",
            "upstream_factor_authority",
            "source_id",
        )
    }
    authority = ""
    upstream = row["upstream_factor_authority"]
    if snapshot is not None:
        authority = _text(snapshot.get("authority"))
        upstream = upstream or _text(snapshot.get("upstream_factor_authority"))
    units = ""
    if row["numerator_unit"] and row["denominator_unit"]:
        units = f"{row['numerator_unit']}/{row['denominator_unit']}"
    value_line = row["factor_value"]
    if value_line and units:
        value_line = f"{value_line} {units}"
    lines = [
        "Candidate to activate",
        "",
        f"Candidate ID: {row['candidate_id'] or '(missing)'}",
        "",
        "Year:",
        row["factor_year"] or "(missing)",
        "",
        "Category:",
        row["factor_category"] or "(missing)",
        "",
        "Value:",
        value_line or "(missing)",
        "",
        "Intended use:",
        row["intended_use"] or "(missing)",
        "",
        "Source:",
        authority
        or "Taiwan Ministry of Environment / Climate Change Administration",
        "",
        "Upstream authority:",
        upstream
        or "Taiwan Ministry of Economic Affairs / Energy Administration",
        "",
        "Status:",
        row["lifecycle_status"] or "(missing)",
    ]
    return "\n".join(lines)


def assert_candidate_ready_for_activation(
    candidate: dict[str, Any] | pd.Series,
    *,
    snapshot: dict[str, Any] | pd.Series | None = None,
) -> None:
    """Raise ReferenceSyncError when a candidate is not activation-ready."""
    candidate_id = _text(candidate.get("candidate_id"))
    lifecycle = _text(candidate.get("lifecycle_status"))
    validation = _text(candidate.get("validation_status"))

    if lifecycle == LIFECYCLE_NEEDS_PARSER_REVIEW:
        raise ReferenceSyncError(
            "CANDIDATE_NEEDS_PARSER_REVIEW",
            f"Candidate {candidate_id} needs parser review and cannot activate.",
        )
    if lifecycle in {LIFECYCLE_REJECTED, LIFECYCLE_SUPERSEDED}:
        raise ReferenceSyncError(
            "CANDIDATE_NOT_ACTIVATABLE",
            f"Candidate {candidate_id} has lifecycle_status={lifecycle!r}.",
        )
    if validation != VALIDATION_PASSED:
        raise ReferenceSyncError(
            "CANDIDATE_NOT_VALIDATED",
            f"Candidate {candidate_id} is not validated "
            f"(validation_status={validation!r}).",
        )
    if lifecycle != LIFECYCLE_VALIDATED:
        if lifecycle == LIFECYCLE_ACTIVE:
            raise ReferenceSyncError(
                "CANDIDATE_ALREADY_ACTIVE",
                f"Candidate {candidate_id} is already active.",
            )
        raise ReferenceSyncError(
            "CANDIDATE_NOT_VALIDATED",
            f"Candidate {candidate_id} lifecycle_status must be "
            f"{LIFECYCLE_VALIDATED!r} (found {lifecycle!r}).",
        )
    if not _text(candidate.get("factor_value")):
        raise ReferenceSyncError(
            "CANDIDATE_MISSING_VALUE",
            f"Candidate {candidate_id} is missing factor_value.",
        )
    if not _text(candidate.get("factor_year")):
        raise ReferenceSyncError(
            "CANDIDATE_MISSING_YEAR",
            f"Candidate {candidate_id} is missing factor_year.",
        )
    ref_type = _text(candidate.get("reference_type"))
    candidate_type = _text(candidate.get("candidate_type")) or ref_type
    if candidate_type == REF_TYPE_STEEL or ref_type == REF_TYPE_STEEL:
        raise ReferenceSyncError(
            "STEEL_FACTOR_NOT_AUTO_ACTIVATED",
            "Purchased-steel average-data factors cannot be auto-activated. "
            "Official CFP_P_02 candidates require reviewed applicability "
            "metadata before they can become active factors.",
        )
    if ref_type == REF_TYPE_GWP:
        if not (
            _text(candidate.get("numerator_unit"))
            or _text(candidate.get("factor_unit"))
        ):
            raise ReferenceSyncError(
                "CANDIDATE_MISSING_UNITS",
                f"Candidate {candidate_id} is missing GWP unit.",
            )
    elif ref_type == "fuel_heating_values":
        if not _text(candidate.get("numerator_unit")):
            raise ReferenceSyncError(
                "CANDIDATE_MISSING_UNITS",
                f"Candidate {candidate_id} is missing heating-value unit.",
            )
    elif not _text(candidate.get("numerator_unit")) or not _text(
        candidate.get("denominator_unit")
    ):
        raise ReferenceSyncError(
            "CANDIDATE_MISSING_UNITS",
            f"Candidate {candidate_id} is missing numerator/denominator units.",
        )
    if not _text(candidate.get("snapshot_id")):
        raise ReferenceSyncError(
            "SNAPSHOT_MISSING",
            f"Candidate {candidate_id} is missing snapshot_id.",
        )
    if snapshot is None:
        raise ReferenceSyncError(
            "SNAPSHOT_MISSING",
            f"Snapshot for candidate {candidate_id} is missing.",
        )
    if not _text(snapshot.get("sha256")):
        raise ReferenceSyncError(
            "SNAPSHOT_INCOMPLETE",
            f"Snapshot {candidate.get('snapshot_id')!r} is missing sha256.",
        )
    if not (
        _text(snapshot.get("retrieved_url"))
        or _text(candidate.get("source_locator"))
    ):
        raise ReferenceSyncError(
            "PROVENANCE_INCOMPLETE",
            f"Candidate {candidate_id} lacks retrieved_url / source_locator.",
        )
    if not (
        _text(candidate.get("upstream_factor_authority"))
        or _text(snapshot.get("upstream_factor_authority"))
        or _text(snapshot.get("authority"))
    ):
        raise ReferenceSyncError(
            "PROVENANCE_INCOMPLETE",
            f"Candidate {candidate_id} lacks source/upstream authority.",
        )
    valid_from = _parse_date(_text(candidate.get("valid_from")))
    valid_to = _parse_date(_text(candidate.get("valid_to")))
    publication_date = _parse_date(_text(candidate.get("publication_date")))
    if ref_type in ELECTRICITY_CANDIDATE_REF_TYPES:
        if valid_from is None or valid_to is None:
            raise ReferenceSyncError(
                "CANDIDATE_MISSING_VALIDITY",
                f"Candidate {candidate_id} requires valid_from and valid_to.",
            )
        if valid_from > valid_to:
            raise ReferenceSyncError(
                "CANDIDATE_INVALID_VALIDITY",
                f"Candidate {candidate_id} has valid_from after valid_to.",
            )
    elif ref_type in {REF_TYPE_GWP, REF_TYPE_FUEL_EF, REF_TYPE_GENERAL_EF}:
        if valid_from is None:
            raise ReferenceSyncError(
                "CANDIDATE_MISSING_VALIDITY",
                (
                    f"Candidate {candidate_id} requires an official "
                    "applicability period; publication_date is not valid_from."
                ),
            )
        if valid_to is not None and valid_from > valid_to:
            raise ReferenceSyncError(
                "CANDIDATE_INVALID_VALIDITY",
                f"Candidate {candidate_id} has valid_from after valid_to.",
            )
        if publication_date is not None and publication_date == valid_from:
            raise ReferenceSyncError(
                "CANDIDATE_INVALID_VALIDITY",
                f"Candidate {candidate_id} must not use publication_date "
                "as valid_from.",
            )
    elif valid_from is not None and valid_to is not None and valid_from > valid_to:
        raise ReferenceSyncError(
            "CANDIDATE_INVALID_VALIDITY",
            f"Candidate {candidate_id} has valid_from after valid_to.",
        )


def _portable_snapshot_path(snapshot: dict[str, Any]) -> str:
    file_name = Path(_text(snapshot.get("file_name"))).name
    if file_name:
        return f"data/reference_snapshots/{file_name}"
    text = _text(snapshot.get("local_path")).replace("\\", "/")
    marker = "data/reference_snapshots/"
    if marker in text:
        return marker + text.split(marker)[-1]
    return Path(text).name


def _content_json(payload: dict[str, Any] | list[dict[str, Any]] | None) -> str:
    if not payload:
        return ""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _active_fuel_duplicate_exists(
    emission_factors: pd.DataFrame,
    candidate: dict[str, Any],
) -> bool:
    if emission_factors.empty:
        return False
    context = _text(candidate.get("factor_context")) or _text(
        candidate.get("combustion_context")
    )
    mask = (
        (emission_factors["activity_type"] == _text(candidate.get("activity_type")))
        & (emission_factors["combustion_context"] == context)
        & (emission_factors["gas"] == _text(candidate.get("gas")))
        & (emission_factors["factor_year"] == _text(candidate.get("factor_year")))
        & (emission_factors["geography"] == _text(candidate.get("geography")))
        & (
            emission_factors["numerator_unit"]
            == _text(candidate.get("numerator_unit"))
        )
        & (
            emission_factors["denominator_unit"]
            == _text(candidate.get("denominator_unit"))
        )
        & (emission_factors["valid_from"] == _text(candidate.get("valid_from")))
        & (emission_factors["valid_to"] == _text(candidate.get("valid_to")))
        & (emission_factors["factor_status"] != "inactive")
    )
    return not emission_factors.loc[mask].empty


def _active_gwp_duplicate_exists(
    gwp_values: pd.DataFrame,
    candidate: dict[str, Any],
) -> bool:
    if gwp_values.empty:
        return False
    context = _text(candidate.get("factor_context")) or _text(
        candidate.get("combustion_context")
    )
    mask = gwp_values["gas"].astype(str).str.strip() == _text(candidate.get("gas"))
    mask &= gwp_values["emission_context"].astype(str).str.strip() == context
    mask &= (
        gwp_values["assessment_basis"].astype(str).str.strip()
        == _text(candidate.get("assessment_basis"))
    )
    if "valid_from" in gwp_values.columns:
        mask &= (
            gwp_values["valid_from"].astype(str).str.strip()
            == _text(candidate.get("valid_from"))
        )
    if "gwp_status" in gwp_values.columns:
        mask &= gwp_values["gwp_status"].astype(str).str.strip() != "inactive"
    return not gwp_values.loc[mask].empty


def _fuel_required_conversion(activity_type: str) -> str:
    if activity_type == "natural_gas":
        return "verified_natural_gas_heating_value_m3_to_TJ"
    if activity_type == "diesel":
        return "verified_diesel_heating_value_L_to_TJ"
    return "verified_fuel_heating_value"


def activate_candidate(
    *,
    candidate_id: str,
    candidates_csv: Path,
    snapshots_csv: Path,
    activations_csv: Path,
    emission_factors_csv: Path,
    fuel_heating_values_csv: Path,
    activated_at: str | pd.Timestamp | datetime,
    activated_by: str = "reference_sync",
    gwp_values_csv: Path | None = None,
) -> dict[str, str]:
    """Activate one validated candidate into the local versioned registry.

    Never deletes historical rows. Never activates from publication date alone.
    ``activated_at`` must be provided explicitly. Activates exactly one
    ``candidate_id`` — never all validated candidates.
    """
    if _blank(activated_at):
        raise ReferenceSyncError(
            "ACTIVATION_TIME_REQUIRED",
            "activated_at must be provided explicitly for reproducibility.",
        )
    activated_stamp = pd.Timestamp(activated_at)
    if pd.isna(activated_stamp):
        raise ReferenceSyncError(
            "INVALID_ACTIVATION_TIME",
            f"Invalid activated_at value: {activated_at!r}",
        )
    activated_text = activated_stamp.isoformat()

    candidates = _read_csv(candidates_csv, CANDIDATE_COLUMNS)
    match = candidates.loc[candidates["candidate_id"] == candidate_id]
    if match.empty:
        raise ReferenceSyncError(
            "CANDIDATE_NOT_FOUND",
            f"Unknown candidate_id {candidate_id!r}.",
        )
    candidate = match.iloc[0].to_dict()

    snapshots = _read_csv(snapshots_csv, SNAPSHOT_COLUMNS)
    snap = snapshots.loc[snapshots["snapshot_id"] == candidate["snapshot_id"]]
    snapshot_row = snap.iloc[0].to_dict() if not snap.empty else None
    assert_candidate_ready_for_activation(candidate, snapshot=snapshot_row)
    assert snapshot_row is not None
    sha256 = _text(snapshot_row["sha256"])
    ref_type = _text(candidate.get("reference_type"))
    previous_content = ""
    new_content = ""
    portable_path = _portable_snapshot_path(snapshot_row)

    if ref_type in ELECTRICITY_CANDIDATE_REF_TYPES:
        factors = _read_csv(
            emission_factors_csv,
            [
                "factor_id",
                "activity_type",
                "combustion_context",
                "gas",
                "factor_value",
                "numerator_unit",
                "denominator_unit",
                "geography",
                "factor_year",
                "valid_from",
                "valid_to",
                "source_reference_id",
                "source_locator",
                "factor_status",
                "required_conversion",
                "notes",
            ],
        )
        if _active_duplicate_exists(factors, candidate):
            raise ReferenceSyncError(
                "DUPLICATE_ACTIVE_FACTOR",
                "An active factor with identical applicability dimensions "
                "already exists.",
            )
        year = _text(candidate.get("factor_year"))
        category = _text(candidate.get("factor_category")) or "unspecified"
        factor_id = f"ef_tw_grid_electricity_{year}_{category}"
        if factor_id in set(factors["factor_id"].tolist()):
            factor_id = f"{factor_id}_{sha256[:8]}"
        source_reference_id = (
            f"ref_sync_{_text(candidate.get('source_id'))}_{year}"
        )
        intended_use = _text(candidate.get("intended_use"))
        applicability = _text(candidate.get("applicability_notes"))
        upstream = _text(candidate.get("upstream_factor_authority")) or _text(
            snapshot_row.get("upstream_factor_authority")
        )
        factor_row = {
            "factor_id": factor_id,
            "activity_type": "grid_electricity",
            "combustion_context": "not_applicable",
            "gas": _text(candidate.get("gas")) or "CO2e",
            "factor_value": _text(candidate.get("factor_value")),
            "numerator_unit": _text(candidate.get("numerator_unit")),
            "denominator_unit": _text(candidate.get("denominator_unit")),
            "geography": _text(candidate.get("geography")) or "TW",
            "factor_year": year,
            "valid_from": _text(candidate.get("valid_from")),
            "valid_to": _text(candidate.get("valid_to")),
            "source_reference_id": source_reference_id,
            "source_locator": (
                f"{_text(candidate.get('source_locator'))}; "
                f"snapshot={candidate['snapshot_id']}; sha256={sha256}"
            ),
            "factor_status": "ready",
            "required_conversion": "not_required",
            "notes": (
                f"Activated from official sync candidate {candidate_id}. "
                f"category={category}. intended_use={intended_use or 'n/a'}. "
                f"upstream_factor_authority={upstream or 'n/a'}. "
                f"applicability={applicability or 'n/a'}. "
                f"publication_date="
                f"{_text(candidate.get('publication_date')) or 'unknown'} "
                "(publication_date is not validity)."
            ),
        }
        factors = pd.concat([factors, pd.DataFrame([factor_row])], ignore_index=True)
        _write_csv(
            emission_factors_csv,
            factors,
            list(factor_row.keys()),
        )
        references_csv = emission_factors_csv.parent / "regulatory_references.csv"
        references = _read_csv(
            references_csv,
            [
                "reference_id",
                "framework",
                "title",
                "publisher",
                "identifier",
                "publication_date",
                "effective_from",
                "authority_level",
                "binding_status",
                "source_location",
                "notes",
            ],
        )
        if source_reference_id not in set(references["reference_id"].tolist()):
            ref_row = {
                "reference_id": source_reference_id,
                "framework": "corporate_ghg",
                "title": (
                    f"Official sync electricity factor {year} "
                    f"({category})"
                ),
                "publisher": _text(snapshot_row.get("authority")),
                "identifier": "",
                "publication_date": _text(candidate.get("publication_date")),
                "effective_from": _text(candidate.get("valid_from")),
                "authority_level": "official_government_publication",
                "binding_status": "official",
                "source_location": _text(snapshot_row.get("retrieved_url")),
                "notes": (
                    f"Created by reference sync activation. "
                    f"snapshot={candidate['snapshot_id']}; sha256={sha256}"
                ),
            }
            references = pd.concat(
                [references, pd.DataFrame([ref_row])],
                ignore_index=True,
            )
            _write_csv(references_csv, references, list(ref_row.keys()))
        registry_table = "emission_factors"
        registry_id = factor_id
        previous_content = _content_json(
            [
                row
                for row in factors.to_dict(orient="records")
                if _text(row.get("factor_id")) != factor_id
                and _text(row.get("activity_type")) == "grid_electricity"
                and _text(row.get("factor_year")) == year
                and _text(row.get("gas")) == _text(factor_row.get("gas"))
            ]
        )
        new_content = _content_json(factor_row)
    elif ref_type in {REF_TYPE_FUEL_EF, REF_TYPE_GENERAL_EF}:
        factors = _read_csv(emission_factors_csv, EMISSION_FACTOR_COLUMNS)
        if _active_fuel_duplicate_exists(factors, candidate):
            raise ReferenceSyncError(
                "DUPLICATE_ACTIVE_FACTOR",
                "An active fuel emission factor with identical identity "
                "already exists.",
            )
        activity_type = _text(candidate.get("activity_type"))
        context = _text(candidate.get("factor_context")) or _text(
            candidate.get("combustion_context")
        )
        gas = _text(candidate.get("gas"))
        year = _text(candidate.get("factor_year"))
        factor_id = (
            f"ef_{activity_type}_{context}_{gas}_{year}_{sha256[:8]}"
        )
        if factor_id in set(factors["factor_id"].tolist()):
            factor_id = f"{factor_id}_{candidate_id[-8:]}"
        conversion = _fuel_required_conversion(activity_type)
        previous_content = _content_json(
            [
                row
                for row in factors.to_dict(orient="records")
                if _text(row.get("activity_type")) == activity_type
                and _text(row.get("combustion_context")) == context
                and _text(row.get("gas")) == gas
            ]
        )
        factor_row = {
            "factor_id": factor_id,
            "activity_type": activity_type,
            "combustion_context": context,
            "gas": gas,
            "factor_value": _text(candidate.get("factor_value")),
            "numerator_unit": _text(candidate.get("numerator_unit")),
            "denominator_unit": _text(candidate.get("denominator_unit")),
            "geography": _text(candidate.get("geography")) or "TW_reference",
            "factor_year": year,
            "valid_from": _text(candidate.get("valid_from")),
            "valid_to": _text(candidate.get("valid_to")),
            "source_reference_id": (
                f"ref_sync_{_text(candidate.get('source_id'))}_{year}"
            ),
            "source_locator": (
                f"{_text(candidate.get('source_locator'))}; "
                f"snapshot={candidate['snapshot_id']}; sha256={sha256}"
            ),
            "factor_status": "registered_missing_conversion",
            "required_conversion": conversion,
            "notes": (
                f"Activated from official sync candidate {candidate_id}. "
                "Append-only; historical fuel-factor rows were not overwritten. "
                f"publication_date="
                f"{_text(candidate.get('publication_date')) or 'unknown'} "
                "(publication_date is not validity)."
            ),
        }
        new_content = _content_json(factor_row)
        factors = pd.concat([factors, pd.DataFrame([factor_row])], ignore_index=True)
        _write_csv(emission_factors_csv, factors, EMISSION_FACTOR_COLUMNS)
        registry_table = "emission_factors"
        registry_id = factor_id
    elif ref_type == REF_TYPE_GWP:
        gwp_path = (
            Path(gwp_values_csv)
            if gwp_values_csv is not None
            else emission_factors_csv.parent / "gwp_values.csv"
        )
        gwp_values = _read_csv(gwp_path, GWP_COLUMNS)
        if _active_gwp_duplicate_exists(gwp_values, candidate):
            raise ReferenceSyncError(
                "DUPLICATE_ACTIVE_FACTOR",
                "An active GWP row with identical gas, context, assessment "
                "basis, and valid_from already exists.",
            )
        gas = _text(candidate.get("gas"))
        context = _text(candidate.get("factor_context")) or _text(
            candidate.get("combustion_context")
        )
        basis = _text(candidate.get("assessment_basis"))
        year = _text(candidate.get("factor_year"))
        gwp_id = (
            f"gwp_{basis.replace(' ', '_').lower()}_"
            f"{gas}_{context}_{year}_{sha256[:8]}"
        )
        gwp_id = re.sub(r"[^A-Za-z0-9_]+", "_", gwp_id)
        previous_content = _content_json(
            [
                row
                for row in gwp_values.to_dict(orient="records")
                if _text(row.get("gas")) == gas
                and _text(row.get("emission_context")) == context
            ]
        )
        gwp_row = {
            "gwp_id": gwp_id,
            "gas": gas,
            "gwp_value": _text(candidate.get("factor_value")),
            "emission_context": context,
            "gwp_status": "ready",
            "assessment_basis": basis,
            "source_reference_id": (
                f"ref_sync_{_text(candidate.get('source_id'))}_{year}"
            ),
            "source_locator": (
                f"{_text(candidate.get('source_locator'))}; "
                f"snapshot={candidate['snapshot_id']}; sha256={sha256}"
            ),
            "valid_from": _text(candidate.get("valid_from")),
            "notes": (
                f"Activated from official sync candidate {candidate_id}. "
                "Append-only; prior-year GWP rows were not rewritten. "
                f"assessment_basis={basis}."
            ),
        }
        new_content = _content_json(gwp_row)
        gwp_values = pd.concat(
            [gwp_values, pd.DataFrame([gwp_row])], ignore_index=True
        )
        _write_csv(gwp_path, gwp_values, GWP_COLUMNS)
        registry_table = "gwp_values"
        registry_id = gwp_id
    elif ref_type == "fuel_heating_values":
        heating = _read_csv(fuel_heating_values_csv, HEATING_VALUE_COLUMNS)
        fuel = _text(candidate.get("factor_category"))
        year = _text(candidate.get("factor_year"))
        heating_id = f"hv_{fuel}_{year}_{sha256[:8]}"
        heating_row = {
            "heating_value_id": heating_id,
            "fuel_type": fuel,
            "fuel_subtype": "",
            "heating_value": _text(candidate.get("factor_value")),
            "unit": _text(candidate.get("numerator_unit")),
            "high_heating_value": "",
            "high_heating_value_unit": "",
            "factor_year": year,
            "geography": _text(candidate.get("geography")) or "TW",
            "authority": _text(snapshot_row.get("authority")),
            "valid_from": _text(candidate.get("valid_from")),
            "valid_to": _text(candidate.get("valid_to")),
            "source_reference_id": f"ref_sync_{_text(candidate.get('source_id'))}",
            "source_locator": _text(candidate.get("source_locator")),
            "snapshot_id": _text(candidate.get("snapshot_id")),
            "snapshot_sha256": sha256,
            "snapshot_local_path": portable_path,
            "status": "registered",
            "notes": (
                "Versioned heating-value reference. Does not automatically "
                "clear calculation_dependencies or invent conversions."
            ),
        }
        previous_content = _content_json(
            [
                row
                for row in heating.to_dict(orient="records")
                if _text(row.get("fuel_type")) == fuel
            ]
        )
        new_content = _content_json(heating_row)
        heating = pd.concat([heating, pd.DataFrame([heating_row])], ignore_index=True)
        _write_csv(fuel_heating_values_csv, heating, HEATING_VALUE_COLUMNS)
        registry_table = "fuel_heating_values"
        registry_id = heating_id
    else:
        raise ReferenceSyncError(
            "UNSUPPORTED_ACTIVATION_TYPE",
            f"Cannot activate reference_type {ref_type!r} in Phase 10A.",
        )

    activations = _read_csv(activations_csv, ACTIVATION_COLUMNS)
    # Reject duplicate activation of the same candidate (audit + lifecycle).
    prior = activations.loc[activations["candidate_id"] == candidate_id]
    if not prior.empty:
        raise ReferenceSyncError(
            "CANDIDATE_ALREADY_ACTIVE",
            f"Candidate {candidate_id} already has an activation audit row.",
        )
    activation_id = f"act_{candidate_id[-12:]}_{sha256[:8]}"
    activation_row = {
        "activation_id": activation_id,
        "candidate_id": candidate_id,
        "snapshot_id": _text(candidate.get("snapshot_id")),
        "factor_id": registry_id,
        "factor_year": _text(candidate.get("factor_year")),
        "factor_category": _text(candidate.get("factor_category")),
        "factor_value": _text(candidate.get("factor_value")),
        "numerator_unit": _text(candidate.get("numerator_unit")),
        "denominator_unit": _text(candidate.get("denominator_unit")),
        "activated_at": activated_text,
        "activated_by": activated_by,
        "registry_table": registry_table,
        "sha256": sha256,
        "source_id": _text(candidate.get("source_id")),
        "upstream_factor_authority": _text(
            candidate.get("upstream_factor_authority")
        )
        or _text(snapshot_row.get("upstream_factor_authority")),
        "retrieved_url": _text(snapshot_row.get("retrieved_url")),
        "notes": (
            "Historical rows preserved; prior years not overwritten. "
            "Activated exactly one selected candidate_id."
        ),
        "source_snapshot_path": portable_path,
        "previous_content": previous_content,
        "new_content": new_content,
    }
    activations = pd.concat(
        [activations, pd.DataFrame([activation_row])],
        ignore_index=True,
    )
    _write_csv(activations_csv, activations, ACTIVATION_COLUMNS)

    idx = candidates.index[candidates["candidate_id"] == candidate_id][0]
    candidates.at[idx, "lifecycle_status"] = LIFECYCLE_ACTIVE
    candidates.at[idx, "reason"] = (
        f"Activated into {registry_table} as {registry_id}."
    )
    _write_csv(candidates_csv, candidates, CANDIDATE_COLUMNS)
    return {key: _text(value) for key, value in activation_row.items()}


def _percent_change(old_value: str, new_value: str) -> str:
    try:
        old = Decimal(old_value.replace(",", ""))
        new = Decimal(new_value.replace(",", ""))
    except (InvalidOperation, ValueError, AttributeError):
        return ""
    if not old.is_finite() or not new.is_finite() or old == 0:
        return ""
    change = ((new - old) / old) * Decimal("100")
    return format(change.quantize(Decimal("0.01")), "f")


def _current_registry_value(
    *,
    ref_type: str,
    candidate: dict[str, Any],
    emission_factors: pd.DataFrame,
    heating: pd.DataFrame,
    gwp_values: pd.DataFrame,
) -> dict[str, str]:
    empty = {
        "factor_id": "",
        "factor_value": "",
        "factor_unit": "",
        "valid_from": "",
        "valid_to": "",
    }
    if ref_type in ELECTRICITY_CANDIDATE_REF_TYPES:
        year = _text(candidate.get("factor_year"))
        category = _text(candidate.get("factor_category")) or "unspecified"
        rows = emission_factors.loc[
            (emission_factors["activity_type"] == "grid_electricity")
            & (emission_factors["factor_year"] == year)
            & (emission_factors["factor_status"] != "inactive")
        ]
        for _, row in rows.iterrows():
            notes = _text(row.get("notes"))
            factor_id = _text(row.get("factor_id"))
            if f"category={category}" in notes or factor_id.endswith(f"_{category}"):
                return {
                    "factor_id": factor_id,
                    "factor_value": _text(row.get("factor_value")),
                    "factor_unit": (
                        f"{_text(row.get('numerator_unit'))}/"
                        f"{_text(row.get('denominator_unit'))}"
                    ),
                    "valid_from": _text(row.get("valid_from")),
                    "valid_to": _text(row.get("valid_to")),
                }
        return empty
    if ref_type in {REF_TYPE_FUEL_EF, REF_TYPE_GENERAL_EF}:
        context = _text(candidate.get("factor_context")) or _text(
            candidate.get("combustion_context")
        )
        rows = emission_factors.loc[
            (emission_factors["activity_type"] == _text(candidate.get("activity_type")))
            & (emission_factors["combustion_context"] == context)
            & (emission_factors["gas"] == _text(candidate.get("gas")))
            & (emission_factors["factor_status"] != "inactive")
        ]
        if rows.empty:
            return empty
        row = rows.iloc[-1]
        return {
            "factor_id": _text(row.get("factor_id")),
            "factor_value": _text(row.get("factor_value")),
            "factor_unit": (
                f"{_text(row.get('numerator_unit'))}/"
                f"{_text(row.get('denominator_unit'))}"
            ),
            "valid_from": _text(row.get("valid_from")),
            "valid_to": _text(row.get("valid_to")),
        }
    if ref_type == REF_TYPE_GWP:
        context = _text(candidate.get("factor_context")) or _text(
            candidate.get("combustion_context")
        )
        rows = gwp_values.loc[
            (gwp_values["gas"].astype(str).str.strip() == _text(candidate.get("gas")))
            & (gwp_values["emission_context"].astype(str).str.strip() == context)
        ]
        if rows.empty:
            return empty
        row = rows.iloc[-1]
        return {
            "factor_id": _text(row.get("gwp_id")),
            "factor_value": _text(row.get("gwp_value")),
            "factor_unit": "GWP",
            "valid_from": _text(row.get("valid_from")),
            "valid_to": "",
        }
    if ref_type == REF_TYPE_HEATING:
        rows = heating.loc[
            heating["fuel_type"].astype(str).str.strip()
            == _text(candidate.get("factor_category"))
        ]
        if rows.empty:
            return empty
        row = rows.iloc[-1]
        return {
            "factor_id": _text(row.get("heating_value_id")),
            "factor_value": _text(row.get("heating_value")),
            "factor_unit": _text(row.get("unit")),
            "valid_from": _text(row.get("valid_from")),
            "valid_to": _text(row.get("valid_to")),
        }
    return empty


def _affected_calculation_types(ref_type: str, candidate: dict[str, Any]) -> list[str]:
    if ref_type in ELECTRICITY_CANDIDATE_REF_TYPES:
        return ["grid_electricity"]
    if ref_type in {REF_TYPE_FUEL_EF, REF_TYPE_GENERAL_EF}:
        activity = _text(candidate.get("activity_type"))
        return [activity] if activity else ["fuel_combustion"]
    if ref_type == REF_TYPE_GWP:
        context = _text(candidate.get("factor_context")) or _text(
            candidate.get("combustion_context")
        )
        if context == "refrigerant_fugitive":
            return ["refrigerant_refill"]
        return ["natural_gas", "diesel"]
    if ref_type == REF_TYPE_HEATING:
        fuel = _text(candidate.get("factor_category"))
        return [fuel] if fuel else ["fuel_combustion"]
    if ref_type == REF_TYPE_STEEL:
        return ["purchased_steel"]
    return []


def propose_official_factor_update(
    repo_root: Path,
    *,
    retrieved_at: str = "",
) -> dict[str, Any]:
    """Build a review bundle. Never activates coefficients and never merges."""
    paths = default_paths(repo_root)
    validate_candidates(
        paths["candidates_csv"],
        official_sources_csv=paths["sources"],
    )
    candidates = _read_csv(paths["candidates_csv"], CANDIDATE_COLUMNS)
    snapshots = _read_csv(paths["snapshots_csv"], SNAPSHOT_COLUMNS)
    factors = _read_csv(paths["emission_factors"], EMISSION_FACTOR_COLUMNS)
    heating = _read_csv(paths["fuel_heating_values"], HEATING_VALUE_COLUMNS)
    gwp_values = _read_csv(paths["gwp_values"], GWP_COLUMNS)

    items: list[dict[str, Any]] = []
    cannot_activate: list[dict[str, Any]] = []
    activatable: list[str] = []
    steel_pending: list[str] = []
    manual_review = False
    snapshot_hashes: list[str] = []

    for _, candidate in candidates.iterrows():
        row = {column: _text(candidate.get(column)) for column in CANDIDATE_COLUMNS}
        ref_type = row["reference_type"]
        lifecycle = row["lifecycle_status"]
        snap = snapshots.loc[snapshots["snapshot_id"] == row["snapshot_id"]]
        snapshot = snap.iloc[0].to_dict() if not snap.empty else {}
        sha256 = row["source_sha256"] or _text(snapshot.get("sha256"))
        if sha256:
            snapshot_hashes.append(sha256)
        current = _current_registry_value(
            ref_type=ref_type,
            candidate=row,
            emission_factors=factors,
            heating=heating,
            gwp_values=gwp_values,
        )
        item = {
            "candidate_id": row["candidate_id"],
            "candidate_type": row["candidate_type"] or ref_type,
            "target_registry": row["target_registry"],
            "source_id": row["source_id"],
            "source_url": row["source_url"] or _text(snapshot.get("retrieved_url")),
            "source_sha256": sha256,
            "source_snapshot_path": _portable_snapshot_path(snapshot)
            if snapshot
            else row["source_snapshot_path"],
            "activity_type": row["activity_type"],
            "gas": row["gas"],
            "factor_context": row["factor_context"] or row["combustion_context"],
            "assessment_basis": row["assessment_basis"],
            "geography": row["geography"],
            "old_value": current["factor_value"],
            "new_value": row["factor_value"],
            "unit": row["factor_unit"]
            or (
                f"{row['numerator_unit']}/{row['denominator_unit']}"
                if row["numerator_unit"] and row["denominator_unit"]
                else row["numerator_unit"]
            ),
            "old_factor_id": current["factor_id"],
            "valid_from": row["valid_from"],
            "valid_to": row["valid_to"],
            "factor_year": row["factor_year"],
            "publication_date": row["publication_date"]
            or _text(snapshot.get("publication_date")),
            "percent_change": _percent_change(
                current["factor_value"], row["factor_value"]
            ),
            "affected_calculation_types": _affected_calculation_types(
                ref_type, row
            ),
            "validation_status": row["validation_status"],
            "lifecycle_status": lifecycle,
            "validation_messages": row["validation_messages"] or row["reason"],
            "manual_review_required": lifecycle
            in {LIFECYCLE_NEEDS_PARSER_REVIEW, STATUS_MANUAL_REVIEW_REQUIRED}
            or row["validation_status"] == VALIDATION_FAILED,
        }
        if lifecycle == LIFECYCLE_ACTIVE:
            continue
        if (
            lifecycle == LIFECYCLE_VALIDATED
            and row["validation_status"] == VALIDATION_PASSED
            and ref_type != REF_TYPE_STEEL
        ):
            item["can_activate"] = True
            activatable.append(row["candidate_id"])
        else:
            item["can_activate"] = False
            reason = row["validation_messages"] or row["reason"] or lifecycle
            if ref_type == REF_TYPE_STEEL:
                reason = (
                    "Official CFP_P_02 steel row is a candidate only. "
                    "Lifecycle boundary, geography, technology, and "
                    "approved_for_reporting_from/to require human review "
                    "before activation. Merging a candidate PR does not "
                    "overwrite active factors."
                )
                if lifecycle != LIFECYCLE_ACTIVE:
                    steel_pending.append(row["candidate_id"])
            cannot_activate.append(
                {
                    "candidate_id": row["candidate_id"],
                    "reason": reason,
                    "source_id": row["source_id"],
                }
            )
            if ref_type != REF_TYPE_STEEL:
                manual_review = True
        items.append(item)

    unique_hashes = sorted(set(snapshot_hashes))
    new_steel_pending = [
        candidate_id
        for candidate_id in steel_pending
        if _steel_candidate_is_new(
            candidates.loc[candidates["candidate_id"] == candidate_id],
            retrieved_at,
        )
    ]
    open_pr = bool(activatable) or bool(new_steel_pending)
    proposal = {
        "generated_at": retrieved_at or "",
        "open_pr": open_pr,
        "same_hash_noop": not items and not unique_hashes,
        "manual_review_required": manual_review,
        "activatable_candidate_ids": activatable,
        "steel_candidate_ids": new_steel_pending,
        "snapshot_sha256": unique_hashes,
        "items": items,
        "cannot_activate": cannot_activate,
        "notes": [
            "This proposal never auto-merges and never silently replaces "
            "production coefficients.",
            "Electricity/fuel activation still requires human merge of "
            "validated registry rows.",
            "Purchased-steel CFP_P_02 rows stay candidates until "
            "applicability review. This workflow must not write active "
            "steel factors or rewrite historical results.",
        ],
    }
    paths["proposal_json"].write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_lines = [
        "# Official factor update review",
        "",
        "Merging this PR is **human approval** to enable the new versioned",
        "registry rows. The workflow must **not** auto-merge.",
        "",
        f"- Open PR recommended: `{open_pr}`",
        f"- Manual review required: `{manual_review}`",
        f"- Activatable candidates: `{len(activatable)}`",
        "",
        "## Snapshot hashes",
        "",
    ]
    if unique_hashes:
        md_lines.extend(f"- `{digest}`" for digest in unique_hashes)
    else:
        md_lines.append("- (none)")
    md_lines.extend(["", "## Proposed changes", ""])
    if not items:
        md_lines.append("No pending candidates.")
    for item in items:
        md_lines.extend(
            [
                f"### {item['candidate_id']}",
                "",
                f"- Official source: `{item['source_id']}`",
                f"- Source URL: {item['source_url'] or '(missing)'}",
                f"- Snapshot SHA-256: `{item['source_sha256'] or '(missing)'}`",
                f"- Old value: {item['old_value'] or '(none)'} {item['unit']}",
                f"- New value: {item['new_value'] or '(none)'} {item['unit']}",
                f"- Unit: {item['unit'] or '(missing)'}",
                f"- Applicable activity: {item['activity_type'] or '(missing)'}",
                (
                    f"- Applicable period: {item['valid_from'] or '(open)'} → "
                    f"{item['valid_to'] or '(open)'}"
                    f" (factor_year={item['factor_year'] or 'n/a'}; "
                    f"publication_date={item['publication_date'] or 'n/a'})"
                ),
                f"- Change percent: {item['percent_change'] or 'n/a'}",
                "- Affected calculation types: "
                + (", ".join(item["affected_calculation_types"]) or "(none)"),
                (
                    f"- Validation: {item['validation_status']} / "
                    f"{item['lifecycle_status']}"
                ),
                f"- Manual handling: {item['manual_review_required']}",
                f"- Can activate: {item['can_activate']}",
                "",
            ]
        )
    md_lines.extend(["## Cannot activate", ""])
    if not cannot_activate:
        md_lines.append("- None.")
    else:
        for blocked in cannot_activate:
            md_lines.append(
                f"- `{blocked['candidate_id']}` ({blocked['source_id']}): "
                f"{blocked['reason']}"
            )
    paths["proposal_md"].write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    proposal["proposal_json"] = str(paths["proposal_json"])
    proposal["proposal_md"] = str(paths["proposal_md"])
    return proposal


def build_change_report(
    *,
    source_id: str,
    reference_type: str,
    previous_snapshot: dict[str, str] | None,
    new_snapshot: dict[str, str],
    previous_candidates: pd.DataFrame,
    new_candidates: list[dict[str, str]],
) -> ChangeReport:
    """Compare previous known years/values with newly created candidates."""
    previous_year_series = previous_candidates.get(
        "factor_year",
        pd.Series(dtype=str),
    )
    prev_years = tuple(
        sorted(
            {
                _text(value)
                for value in previous_year_series.tolist()
                if _text(value)
            }
        )
    )
    new_years = tuple(
        sorted(
            {
                _text(item.get("factor_year"))
                for item in new_candidates
                if _text(item.get("factor_year"))
            }
        )
    )
    changes: list[str] = []
    if previous_snapshot is None:
        changes.append("first snapshot for this source")
    elif previous_snapshot.get("sha256") != new_snapshot.get("sha256"):
        changes.append("artifact bytes changed")
    if prev_years != new_years:
        changes.append("factor year changed")
    if new_candidates:
        changes.append("new candidate row(s) created")
        if any(_text(item.get("valid_from")) for item in new_candidates):
            changes.append("applicability dates present on candidates")
        if any(_text(item.get("factor_value")) for item in new_candidates):
            changes.append("factor value changed or newly observed")
    return ChangeReport(
        source_id=source_id,
        reference_type=reference_type,
        previous_snapshot_id=_text((previous_snapshot or {}).get("snapshot_id")),
        new_snapshot_id=new_snapshot["snapshot_id"],
        previous_years=prev_years,
        new_years=new_years,
        changes=tuple(changes),
        activated=False,
    )


def check_official_sources(
    repo_root: Path,
    *,
    retrieved_at: str,
    fetch: FetchCallable | None = None,
) -> list[dict[str, Any]]:
    """Inspect allowlisted sources and report availability without activating."""
    paths = default_paths(repo_root)
    sources = active_sources(load_official_sources(paths["sources"]))
    results: list[dict[str, Any]] = []
    fetch_fn = fetch or (
        lambda url, allowed_domain, **kwargs: fetch_official_artifact(
            url,
            allowed_domain=allowed_domain,
            **kwargs,
        )
    )
    for _, source in sources.iterrows():
        tls_mode = normalize_tls_compatibility_mode(
            source.get("tls_compatibility_mode")
        )
        fetch_mode = normalize_fetch_mode(source.get("fetch_mode"))
        item: dict[str, Any] = {
            "source_id": _text(source["source_id"]),
            "reference_type": _text(source["reference_type"]),
            "status": "unchecked",
            "message": "",
            "sha256": "",
            "tls_verification": TLS_VERIFICATION_VERIFIED,
            "tls_compatibility_mode": tls_mode,
            "fetch_mode": fetch_mode,
            "upstream_canonical_url": _text(
                source.get("upstream_canonical_url")
            )
            or _text(source.get("canonical_url")),
            "upstream_factor_authority": _text(
                source.get("upstream_factor_authority")
            ),
        }
        if fetch_mode == FETCH_MODE_PROVENANCE_ONLY:
            item["status"] = "recorded_access_restricted"
            item["message"] = (
                "Upstream/canonical source recorded for provenance; "
                "runtime machine-fetch is disabled because official host "
                "access is restricted (HTTP 403). Normal sync uses the "
                "MOENV operational source instead."
            )
            results.append(item)
            continue
        retrieval_strategy = _text(source.get("retrieval_strategy"))
        if retrieval_strategy == RETRIEVAL_PAGINATED_OPEN_DATA_API:
            item["status"] = "scheduled_open_data_api"
            item["message"] = (
                "CFP_P_02 is fetched from the public data.gov.tw dataset "
                "page by parsing the current JSON/CSV resource URL. "
                "MOENV_API_KEY is optional API fallback only and is not "
                "required to download the public catalog. Check does not "
                "download the full dataset."
            )
            results.append(item)
            continue
        try:
            fetched = fetch_fn(
                _text(source["landing_url"]),
                allowed_domain=_text(source["allowed_domain"]),
                tls_compatibility_mode=tls_mode,
            )
            item["status"] = "available"
            item["sha256"] = fetched.sha256
            item["tls_compatibility_mode"] = fetched.tls_compatibility_mode
            item["tls_verification"] = fetched.tls_verification
            item["message"] = (
                f"Reachable at check time {retrieved_at}; "
                f"{fetched.byte_size} bytes."
            )
        except ReferenceSyncError as exc:
            item["status"] = _fetch_failure_status(exc)
            item["message"] = f"{exc.code}: {exc.message}"
        results.append(item)
    return results


def _fetch_and_stage_cfp_p_02(
    *,
    paths: dict[str, Path],
    source: pd.Series,
    retrieved_at: str,
    snapshots: pd.DataFrame,
    page_fetcher: Any = None,
    page_limit: int | None = None,
) -> dict[str, Any]:
    """Fetch every CFP_P_02 page, snapshot it, and stage steel candidates only."""
    from carbon_ledger.cfp_p_02 import (
        API_BASE_URL,
        DEFAULT_PAGE_LIMIT,
        CfpApiError,
        CfpParseError,
        candidate_records_from_snapshot,
        fetch_cfp_p_02_snapshot,
    )
    from carbon_ledger.steel_factor_catalog import (
        official_taxonomy_names,
        upsert_steel_candidates,
    )

    source_id = _text(source["source_id"])
    source_row = {column: _text(source.get(column)) for column in SOURCE_COLUMNS}
    previous = None
    prior_rows = snapshots.loc[snapshots["source_id"] == source_id]
    if not prior_rows.empty:
        previous = {
            col: _text(prior_rows.iloc[-1][col]) for col in SNAPSHOT_COLUMNS
        }
    try:
        snapshot_obj = fetch_cfp_p_02_snapshot(
            retrieved_at=retrieved_at,
            page_fetcher=page_fetcher,
            limit=page_limit or DEFAULT_PAGE_LIMIT,
        )
    except CfpApiError as exc:
        status = (
            "credential_required"
            if exc.code == "CREDENTIAL_REQUIRED"
            else "parse_failed"
        )
        return {
            "source_id": source_id,
            "status": status,
            "message": f"{exc.code}: {exc.message}",
            "candidates_created": 0,
            "review_reason": exc.message,
        }
    except CfpParseError as exc:
        return {
            "source_id": source_id,
            "status": "parse_failed",
            "message": exc.reason,
            "candidates_created": 0,
            "review_reason": exc.reason,
        }

    content = snapshot_obj.to_canonical_bytes()
    fetch_result = FetchResult(
        url=snapshot_obj.source_url or API_BASE_URL,
        final_url=snapshot_obj.source_url or API_BASE_URL,
        content=content,
        media_type="application/json",
        sha256=snapshot_obj.response_sha256,
        byte_size=len(content),
        discovered_url=snapshot_obj.dataset_page_url,
    )
    existing = find_snapshot_by_sha(snapshots, fetch_result.sha256)
    already_known = (
        existing is not None and _text(existing.get("source_id")) == source_id
    )
    snapshot = register_snapshot(
        snapshots_csv=paths["snapshots_csv"],
        artifact_dir=paths["artifact_dir"],
        source_row=source_row,
        fetch=fetch_result,
        retrieved_at=retrieved_at,
        publication_date="",
        status=LIFECYCLE_DOWNLOADED,
        notes=(
            "CFP_P_02 public open-data snapshot. Records hash is the "
            "snapshot SHA-256. Public access tokens were redacted from "
            "stored URLs. Official data does not state lifecycle boundary "
            "or a government validity period."
        ),
    )
    created: list[dict[str, str]] = []
    steel_created: list[dict[str, str]] = []
    if not already_known:
        parsed = parse_artifact(
            content,
            parser_type=_text(source["parser_type"]),
            expected_file_type=_text(source["expected_file_type"]),
        )
        if parsed.status != LIFECYCLE_PARSED:
            return {
                "source_id": source_id,
                "status": "parse_failed",
                "message": parsed.reason,
                "candidates_created": 0,
                "review_reason": parsed.reason,
                "snapshot_id": snapshot["snapshot_id"],
                "sha256": snapshot["sha256"],
            }
        created = upsert_candidates_from_parse(
            candidates_csv=paths["candidates_csv"],
            snapshot=snapshot,
            source_row=source,
            parsed=parsed,
        )
        steel_created = upsert_steel_candidates(
            candidate_records_from_snapshot(
                snapshot_obj,
                taxonomy_names=official_taxonomy_names(paths["reference_dir"]),
            ),
            snapshot_id=snapshot["snapshot_id"],
            source_id=source_id,
            retrieved_at=retrieved_at,
            reference_dir=paths["reference_dir"],
        )
    prev_candidates = _read_csv(paths["candidates_csv"], CANDIDATE_COLUMNS)
    prev_candidates = prev_candidates.loc[prev_candidates["source_id"] == source_id]
    report = build_change_report(
        source_id=source_id,
        reference_type=_text(source["reference_type"]),
        previous_snapshot=previous,
        new_snapshot=snapshot,
        previous_candidates=(
            prev_candidates if already_known else prev_candidates.iloc[0:0]
        ),
        new_candidates=created,
    )
    return {
        "source_id": source_id,
        "status": "already_known" if already_known else "staged",
        "snapshot_id": snapshot["snapshot_id"],
        "sha256": snapshot["sha256"],
        "candidates_created": len(created),
        "steel_candidates_created": len(steel_created),
        "parser_status": LIFECYCLE_PARSED,
        "retrieved_url": snapshot["retrieved_url"],
        "retrieval_strategy": RETRIEVAL_PAGINATED_OPEN_DATA_API,
        "change_report": report.to_text(),
        "message": (
            "CFP_P_02 snapshot already known; no candidate overwrite."
            if already_known
            else (
                f"Staged {len(created)} official candidate row(s) and "
                f"{len(steel_created)} steel review candidate(s). "
                "Active factors were not modified."
            )
        ),
    }


def fetch_and_stage_sources(
    repo_root: Path,
    *,
    retrieved_at: str,
    source_ids: list[str] | None = None,
    fetch: FetchCallable | None = None,
    cfp_page_fetcher: Any = None,
    cfp_page_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Download allowlisted artifacts, register snapshots, and stage candidates.

    Retrieval behavior is controlled by each source's explicit
    ``retrieval_strategy``:

    - ``parse_landing`` — fetch and parse the landing HTML itself; never
      auto-discover or substitute an attachment (e.g. PDF).
    - ``discover_attachment`` — fetch landing HTML, discover an allowlisted
      attachment, then download/parse that artifact.
    - ``paginated_open_data_api`` — parse the current public JSON/CSV
      resource URL from the official dataset page, then walk
      offset/limit until a short page. MOENV_API_KEY is optional
      fallback only; never assume a single page.
    - ``provenance_only`` — no network fetch (aligned with fetch_mode).

    Direct invented CSV endpoints are not assumed.
    """
    paths = default_paths(repo_root)
    all_active = active_sources(load_official_sources(paths["sources"]))
    if source_ids is not None:
        sources = all_active.loc[all_active["source_id"].isin(source_ids)].copy()
    else:
        sources = fetchable_sources(all_active)
    snapshots = _read_csv(paths["snapshots_csv"], SNAPSHOT_COLUMNS)
    candidates = _read_csv(paths["candidates_csv"], CANDIDATE_COLUMNS)
    fetch_fn = fetch or (
        lambda url, allowed_domain, **kwargs: fetch_official_artifact(
            url,
            allowed_domain=allowed_domain,
            **kwargs,
        )
    )
    reports: list[dict[str, Any]] = []

    for _, source in sources.iterrows():
        source_id = _text(source["source_id"])
        allowed_domain = _text(source["allowed_domain"])
        landing_url = _text(source["landing_url"])
        parser_type = _text(source["parser_type"])
        tls_mode = normalize_tls_compatibility_mode(
            source.get("tls_compatibility_mode")
        )
        fetch_mode = normalize_fetch_mode(source.get("fetch_mode"))
        retrieval_strategy = normalize_retrieval_strategy(
            source.get("retrieval_strategy")
        )
        if (
            fetch_mode == FETCH_MODE_PROVENANCE_ONLY
            or retrieval_strategy == RETRIEVAL_PROVENANCE_ONLY
        ):
            reports.append(
                {
                    "source_id": source_id,
                    "status": "skipped_provenance_only",
                    "message": (
                        "Upstream/canonical source is provenance-only; "
                        "no network fetch attempted."
                    ),
                    "upstream_canonical_url": _text(
                        source.get("upstream_canonical_url")
                    )
                    or _text(source.get("canonical_url")),
                    "candidates_created": 0,
                }
            )
            continue
        if retrieval_strategy == RETRIEVAL_PAGINATED_OPEN_DATA_API:
            report = _fetch_and_stage_cfp_p_02(
                paths=paths,
                source=source,
                retrieved_at=retrieved_at,
                snapshots=snapshots,
                page_fetcher=cfp_page_fetcher,
                page_limit=cfp_page_limit,
            )
            snapshots = _read_csv(paths["snapshots_csv"], SNAPSHOT_COLUMNS)
            candidates = _read_csv(paths["candidates_csv"], CANDIDATE_COLUMNS)
            reports.append(report)
            continue
        try:
            landing_fetch = fetch_fn(
                landing_url,
                allowed_domain=allowed_domain,
                tls_compatibility_mode=tls_mode,
            )
        except ReferenceSyncError as exc:
            reports.append(
                {
                    "source_id": source_id,
                    "status": _fetch_failure_status(exc),
                    "message": f"{exc.code}: {exc.message}",
                    "candidates_created": 0,
                }
            )
            continue

        artifact_parser = parser_type
        fetched = landing_fetch
        discovery_message = ""
        used_attachment_discovery = False

        if retrieval_strategy == RETRIEVAL_PARSE_LANDING:
            previous = None
            prior_rows = snapshots.loc[snapshots["source_id"] == source_id]
            if not prior_rows.empty:
                previous = {
                    col: _text(prior_rows.iloc[-1][col])
                    for col in SNAPSHOT_COLUMNS
                }
            existing = find_snapshot_by_sha(snapshots, landing_fetch.sha256)
            already_known = (
                existing is not None
                and _text(existing.get("source_id")) == source_id
            )
            source_for_snapshot = {
                column: _text(source.get(column)) for column in SOURCE_COLUMNS
            }
            parsed = parse_artifact(
                landing_fetch.content,
                parser_type=parser_type,
                expected_file_type=_text(source["expected_file_type"]),
            )
            snapshot = register_snapshot(
                snapshots_csv=paths["snapshots_csv"],
                artifact_dir=paths["artifact_dir"],
                source_row=source_for_snapshot,
                fetch=landing_fetch,
                retrieved_at=retrieved_at,
                publication_date=parsed.publication_date,
                status=LIFECYCLE_DOWNLOADED,
                notes=(
                    "Downloaded official landing HTML for parse_landing "
                    "retrieval; attachment discovery was not used."
                ),
            )
            snapshots = _read_csv(paths["snapshots_csv"], SNAPSHOT_COLUMNS)
            created = []
            if not already_known:
                created = upsert_candidates_from_parse(
                    candidates_csv=paths["candidates_csv"],
                    snapshot=snapshot,
                    source_row=source,
                    parsed=parsed,
                )
            prev_candidates = candidates.loc[
                candidates["source_id"] == source_id
            ]
            report = build_change_report(
                source_id=source_id,
                reference_type=_text(source["reference_type"]),
                previous_snapshot=previous,
                new_snapshot=snapshot,
                previous_candidates=prev_candidates,
                new_candidates=created,
            )
            reports.append(
                {
                    "source_id": source_id,
                    "status": (
                        "already_known" if already_known else "staged"
                    ),
                    "snapshot_id": snapshot["snapshot_id"],
                    "sha256": snapshot["sha256"],
                    "candidates_created": len(created),
                    "parser_status": parsed.status,
                    "discovered_artifact_url": "",
                    "canonical_url": snapshot.get("canonical_url", ""),
                    "upstream_canonical_url": snapshot.get(
                        "upstream_canonical_url", ""
                    ),
                    "upstream_factor_authority": snapshot.get(
                        "upstream_factor_authority", ""
                    ),
                    "retrieved_url": snapshot["retrieved_url"],
                    "retrieved_host": snapshot["retrieved_host"],
                    "retrieval_strategy": retrieval_strategy,
                    "change_report": report.to_text(),
                    "message": parsed.reason,
                }
            )
            candidates = _read_csv(paths["candidates_csv"], CANDIDATE_COLUMNS)
            continue

        if retrieval_strategy == RETRIEVAL_DISCOVER_ATTACHMENT:
            discovery = discover_from_landing_parser(
                landing_fetch.content,
                landing_url=landing_url,
                allowed_domain=allowed_domain,
                parser_type=parser_type,
            )
            discovery_message = discovery.reason
            if discovery.status != LIFECYCLE_DISCOVERED or not discovery.artifact_url:
                snapshot = register_snapshot(
                    snapshots_csv=paths["snapshots_csv"],
                    artifact_dir=paths["artifact_dir"],
                    source_row=source,
                    fetch=landing_fetch,
                    retrieved_at=retrieved_at,
                    publication_date="",
                    status=LIFECYCLE_DOWNLOADED,
                    notes=(
                        "Landing page snapshot retained; no allowlisted "
                        "attachment discovered yet."
                    ),
                )
                parsed = ParseResult(
                    parser_type=parser_type,
                    status=LIFECYCLE_NEEDS_PARSER_REVIEW,
                    reason=discovery.reason,
                )
                created = upsert_candidates_from_parse(
                    candidates_csv=paths["candidates_csv"],
                    snapshot=snapshot,
                    source_row=source,
                    parsed=parsed,
                )
                reports.append(
                    {
                        "source_id": source_id,
                        "status": "staged",
                        "snapshot_id": snapshot["snapshot_id"],
                        "sha256": snapshot["sha256"],
                        "candidates_created": len(created),
                        "parser_status": parsed.status,
                        "discovered_artifact_url": "",
                        "retrieval_strategy": retrieval_strategy,
                        "change_report": "",
                        "message": discovery.reason,
                    }
                )
                snapshots = _read_csv(paths["snapshots_csv"], SNAPSHOT_COLUMNS)
                candidates = _read_csv(paths["candidates_csv"], CANDIDATE_COLUMNS)
                continue

            # Separately validate the discovered attachment before download.
            assert_url_allowlisted(discovery.artifact_url, allowed_domain)
            try:
                fetched = fetch_fn(
                    discovery.artifact_url,
                    allowed_domain=allowed_domain,
                    tls_compatibility_mode=tls_mode,
                )
            except ReferenceSyncError as exc:
                reports.append(
                    {
                        "source_id": source_id,
                        "status": _fetch_failure_status(exc),
                        "message": (
                            "Landing page reachable but artifact fetch failed: "
                            f"{exc.code}: {exc.message}"
                        ),
                        "discovered_artifact_url": discovery.artifact_url,
                        "retrieval_strategy": retrieval_strategy,
                        "candidates_created": 0,
                    }
                )
                continue
            artifact_parser = artifact_parser_for_discovery(
                landing_parser_type=parser_type,
                artifact_url=discovery.artifact_url,
                reference_type=_text(source["reference_type"]),
            )
            used_attachment_discovery = True

        previous = None
        prior_rows = snapshots.loc[snapshots["source_id"] == source_id]
        if not prior_rows.empty:
            previous = {
                col: _text(prior_rows.iloc[-1][col]) for col in SNAPSHOT_COLUMNS
            }

        existing = find_snapshot_by_sha(snapshots, fetched.sha256)
        already_known = (
            existing is not None
            and _text(existing.get("source_id")) == source_id
        )
        expected_type = _text(source["expected_file_type"])
        if used_attachment_discovery:
            path = urlparse(fetched.final_url).path.lower()
            if path.endswith(".ods"):
                expected_type = "ods"
            elif path.endswith(".csv"):
                expected_type = "csv"
            elif path.endswith(".pdf"):
                expected_type = "pdf"
            elif path.endswith(".xlsx"):
                expected_type = "xlsx"
        source_for_snapshot = {
            column: _text(source.get(column)) for column in SOURCE_COLUMNS
        }
        source_for_snapshot["expected_file_type"] = expected_type
        snapshot = register_snapshot(
            snapshots_csv=paths["snapshots_csv"],
            artifact_dir=paths["artifact_dir"],
            source_row=source_for_snapshot,
            fetch=fetched,
            retrieved_at=retrieved_at,
            publication_date="",
            status=LIFECYCLE_DOWNLOADED,
            notes=(
                "Downloaded by official reference sync from allowlisted "
                "landing-page discovery."
                if used_attachment_discovery
                else "Downloaded by official reference sync."
            ),
        )
        snapshots = _read_csv(paths["snapshots_csv"], SNAPSHOT_COLUMNS)

        parsed = parse_artifact(
            fetched.content,
            parser_type=artifact_parser,
            expected_file_type=expected_type,
        )
        if parsed.publication_date and not snapshot.get("publication_date"):
            snap_frame = snapshots
            idx = snap_frame.index[
                snap_frame["snapshot_id"] == snapshot["snapshot_id"]
            ][0]
            snap_frame.at[idx, "publication_date"] = parsed.publication_date
            _write_csv(paths["snapshots_csv"], snap_frame, SNAPSHOT_COLUMNS)
            snapshot["publication_date"] = parsed.publication_date

        created = []
        if not already_known:
            created = upsert_candidates_from_parse(
                candidates_csv=paths["candidates_csv"],
                snapshot=snapshot,
                source_row=source,
                parsed=parsed,
            )
        else:
            created = []

        prev_candidates = candidates.loc[candidates["source_id"] == source_id]
        report = build_change_report(
            source_id=source_id,
            reference_type=_text(source["reference_type"]),
            previous_snapshot=previous,
            new_snapshot=snapshot,
            previous_candidates=prev_candidates,
            new_candidates=created,
        )
        reports.append(
            {
                "source_id": source_id,
                "status": "already_known" if already_known else "staged",
                "snapshot_id": snapshot["snapshot_id"],
                "sha256": snapshot["sha256"],
                "candidates_created": len(created),
                "parser_status": parsed.status,
                "discovered_artifact_url": (
                    fetched.final_url if used_attachment_discovery else ""
                ),
                "retrieval_strategy": retrieval_strategy,
                "change_report": report.to_text(),
                "message": discovery_message or parsed.reason,
            }
        )
        candidates = _read_csv(paths["candidates_csv"], CANDIDATE_COLUMNS)
    return reports


def reference_sync_status(repo_root: Path) -> SyncStatus:
    """Summarize local official-reference maintenance state."""
    paths = default_paths(repo_root)
    sources = load_official_sources(paths["sources"])
    snapshots = _read_csv(paths["snapshots_csv"], SNAPSHOT_COLUMNS)
    candidates = _read_csv(paths["candidates_csv"], CANDIDATE_COLUMNS)
    factors = _read_csv(
        paths["emission_factors"],
        [
            "factor_id",
            "activity_type",
            "factor_year",
            "factor_status",
            "valid_from",
            "valid_to",
        ],
    )
    heating = _read_csv(paths["fuel_heating_values"], HEATING_VALUE_COLUMNS)

    electricity_years: dict[str, str] = {}
    elec = factors.loc[
        (factors.get("activity_type", pd.Series(dtype=str)) == "grid_electricity")
        & (factors.get("factor_status", pd.Series(dtype=str)) != "inactive")
    ]
    for _, row in elec.iterrows():
        year = _text(row.get("factor_year"))
        if year:
            electricity_years[year] = "available"

    for _, row in candidates.iterrows():
        if _text(row.get("reference_type")) not in ELECTRICITY_CANDIDATE_REF_TYPES:
            continue
        year = _text(row.get("factor_year"))
        if not year:
            continue
        lifecycle = _text(row.get("lifecycle_status"))
        if year in electricity_years and electricity_years[year] == "available":
            continue
        if lifecycle == LIFECYCLE_ACTIVE:
            electricity_years[year] = "available"
        elif lifecycle in {LIFECYCLE_CANDIDATE, LIFECYCLE_VALIDATED}:
            electricity_years[year] = "candidate"
        elif lifecycle == LIFECYCLE_NEEDS_PARSER_REVIEW:
            electricity_years[year] = "needs_parser_review"
        else:
            electricity_years.setdefault(year, "unavailable")

    if "2024" not in electricity_years and not elec.empty:
        electricity_years["2024"] = "available"
    if "2025" not in electricity_years:
        electricity_years["2025"] = "unavailable"

    heating_latest: dict[str, str] = {}
    for _, row in heating.iterrows():
        fuel = _text(row.get("fuel_type"))
        year = _text(row.get("factor_year"))
        if fuel and year:
            prior = heating_latest.get(fuel, "")
            if not prior or year > prior:
                heating_latest[fuel] = year
    for fuel in ("natural_gas", "diesel", "gasoline", "lpg"):
        heating_latest.setdefault(fuel, "unregistered")

    last_checked = ""
    if not snapshots.empty and "retrieved_at" in snapshots.columns:
        values = [
            _text(value)
            for value in snapshots["retrieved_at"].tolist()
            if _text(value)
        ]
        last_checked = max(values) if values else ""

    active_candidates = 0
    if not candidates.empty:
        active_candidates = int(
            (candidates["lifecycle_status"] == LIFECYCLE_ACTIVE).sum()
        )

    category_rank = {
        LIFECYCLE_ACTIVE: 40,
        LIFECYCLE_VALIDATED: 30,
        LIFECYCLE_CANDIDATE: 20,
        LIFECYCLE_NEEDS_PARSER_REVIEW: 10,
        LIFECYCLE_REJECTED: 5,
        LIFECYCLE_SUPERSEDED: 1,
    }
    electricity_categories: dict[str, str] = {}
    category_scores: dict[str, int] = {}
    for _, row in candidates.iterrows():
        if _text(row.get("reference_type")) not in ELECTRICITY_CANDIDATE_REF_TYPES:
            continue
        category = _text(row.get("factor_category"))
        if not category:
            continue
        lifecycle = _text(row.get("lifecycle_status"))
        if lifecycle == LIFECYCLE_ACTIVE:
            label = "active"
        elif lifecycle == LIFECYCLE_VALIDATED:
            label = "validated / not active"
        elif lifecycle == LIFECYCLE_CANDIDATE:
            label = "candidate / not active"
        elif lifecycle == LIFECYCLE_NEEDS_PARSER_REVIEW:
            label = "needs_parser_review"
        else:
            label = lifecycle or "unknown"
        score = category_rank.get(lifecycle, 0)
        if score >= category_scores.get(category, -1):
            category_scores[category] = score
            electricity_categories[category] = label

    moea = sources.loc[
        sources["source_id"] == "src_tw_moea_electricity_factor"
    ]
    moenv = sources.loc[
        sources["source_id"] == "src_tw_moenv_electricity_factor_enterprise"
    ]
    upstream_status = "recorded / access restricted"
    if not moea.empty and normalize_fetch_mode(
        moea.iloc[0].get("fetch_mode")
    ) == FETCH_MODE_PROVENANCE_ONLY:
        upstream_status = "recorded / access restricted"
    operational_status = "configured"
    if not moenv.empty:
        operational_status = "available"
        # Prefer latest operational snapshot host as evidence of successful sync.
        op_snaps = snapshots.loc[
            snapshots["source_id"] == "src_tw_moenv_electricity_factor_enterprise"
        ]
        if op_snaps.empty:
            operational_status = "configured (not yet fetched)"

    return SyncStatus(
        electricity_years=dict(sorted(electricity_years.items())),
        heating_value_latest=heating_latest,
        last_checked_at=last_checked or "never",
        snapshot_count=int(len(snapshots)),
        candidate_count=int(len(candidates)),
        active_candidate_count=active_candidates,
        source_count=int(len(active_sources(sources))),
        upstream_factor_authority=(
            _text(moea.iloc[0].get("authority"))
            if not moea.empty
            else "Taiwan Ministry of Economic Affairs / Energy Administration"
        ),
        operational_source_authority=(
            _text(moenv.iloc[0].get("authority"))
            if not moenv.empty
            else (
                "Taiwan Ministry of Environment / Climate Change Administration"
            )
        ),
        upstream_source_status=upstream_status,
        operational_source_status=operational_status,
        upstream_canonical_url=(
            _text(moea.iloc[0].get("canonical_url"))
            if not moea.empty
            else ""
        ),
        operational_source_url=(
            _text(moenv.iloc[0].get("landing_url"))
            if not moenv.empty
            else ""
        ),
        electricity_categories=dict(sorted(electricity_categories.items())),
    )


def format_missing_year_factor_message(
    *,
    activity_year: str,
    registered_years: list[str] | tuple[str, ...],
) -> str:
    """Beginner-facing blocked message when the activity year has no factor."""
    registered = ", ".join(registered_years) if registered_years else "(none)"
    return (
        "尚未找到適用於這筆活動期間的官方排放係數。\n"
        f"活動期間：\n{activity_year}\n"
        f"目前已登錄：\n{registered}\n"
        "系統不會自動使用不同年度的係數。"
    )


def list_registered_electricity_years(emission_factors: pd.DataFrame) -> list[str]:
    """Return sorted electricity factor years from the local registry."""
    if emission_factors is None or emission_factors.empty:
        return []
    frame = emission_factors
    if "activity_type" not in frame.columns:
        return []
    rows = frame.loc[frame["activity_type"].astype(str) == "grid_electricity"]
    years = sorted(
        {
            _text(value)
            for value in rows.get("factor_year", pd.Series(dtype=str)).tolist()
            if _text(value)
        }
    )
    return years


def explicit_fallback_rule_applies(
    rules: pd.DataFrame,
    *,
    reference_type: str,
    activity_date: str | date | pd.Timestamp,
) -> dict[str, str] | None:
    """Return an active explicit fallback rule when one covers the activity date.

    Matching engines must not invent previous-year fallback. This helper only
    exposes rules that were registered with provenance.
    """
    if rules is None or rules.empty:
        return None
    activity = _parse_date(str(activity_date))
    if activity is None:
        return None
    for _, row in rules.iterrows():
        if not _truthy(row.get("active")):
            continue
        if _text(row.get("reference_type")) != reference_type:
            continue
        start = _parse_date(_text(row.get("valid_from")))
        end = _parse_date(_text(row.get("valid_to")))
        if start and activity < start:
            continue
        if end and activity > end:
            continue
        return {column: _text(row.get(column)) for column in RULE_COLUMNS}
    return None
