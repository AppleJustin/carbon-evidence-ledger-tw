"""環境部／政府資料開放平臺 CFP_P_02 碳足跡排放係數擷取與解析。

官方紀錄只提供 name / coe / unit / departmentname / announcementyear。
本模組不臆測生命週期邊界、valid_from / valid_to、geography 或技術途徑。
announcementyear 只當資料／公告年份，不得當作 valid_from。

預設從 https://data.gov.tw/dataset/28176 的 JSON-LD 解析目前公開 JSON／CSV
resource URL 下載。MOENV_API_KEY 只是可選的環境部 API 備援，不得寫入原始碼、
測試、log 或 snapshot URL。
"""

from __future__ import annotations

import csv
import hashlib
import html as html_lib
import io
import json
import os
import re
import ssl
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import (
    parse_qsl,
    quote,
    urlencode,
    urlparse,
    urlsplit,
    urlunparse,
    urlunsplit,
)
from urllib.request import HTTPSHandler, Request, build_opener

DATASET_CODE = "CFP_P_02"
DATA_GOV_DATASET_ID = "28176"
DATA_GOV_DATASET_PAGE_URL = "https://data.gov.tw/dataset/28176"
DATASET_PAGE_URL = "https://data.moenv.gov.tw/dataset/detail/CFP_P_02"
API_BASE_URL = "https://data.moenv.gov.tw/api/v2/CFP_P_02"
API_KEY_ENV = "MOENV_API_KEY"
PARSER_TYPE = "cfp_p_02_open_data_v1"
DEFAULT_PAGE_LIMIT = 1000
PAGINATION_SAFETY_LIMIT = 1_000_000
ALLOWED_HOST = "data.moenv.gov.tw"
ALLOWED_FETCH_HOSTS = frozenset(
    {
        "data.gov.tw",
        "data.moenv.gov.tw",
    }
)
QUERY_TOKEN_NAMES = frozenset({"api_key", "token", "access_token", "apikey"})
OFFICIAL_FIELDS = (
    "name",
    "coe",
    "unit",
    "departmentname",
    "announcementyear",
)
REQUIRED_RECORD_FIELDS = ("name", "coe", "unit", "announcementyear")

GENERIC_STEEL_LABELS = frozenset(
    {
        "採購鋼材",
        "purchased steel",
        "purchased_steel",
        "鋼材",
        "steel",
        "其他／尚不確定",
        "其他/尚不確定",
        "undecided",
        "other",
    }
)

STEEL_OFFICIAL_PRODUCT_NAMES = (
    "鋼板",
    "熱軋粗鋼捲",
    "熱軋鋼捲",
    "熱軋酸洗塗油鋼捲",
    "熱軋鋼板片",
    "冷軋鋼捲",
    "碳鋼冷軋鋼捲",
    "不鏽鋼",
)

_KG_UNITS = frozenset({"kg", "公斤", "千克", "kilogram", "kilograms"})
_T_UNITS = frozenset({"t", "公噸", "噸", "tonne", "tonnes", "ton", "metric ton"})

PageFetcher = Callable[..., Mapping[str, Any] | Sequence[Any] | str | bytes]


class CfpApiError(Exception):
    """Missing credentials or a transport failure. Never includes the API key."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class CfpParseError(Exception):
    """Fail-closed parse/schema error with a human-readable review reason."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class OfficialCfpRecord:
    """One official CFP_P_02 row. Review metadata is intentionally absent."""

    name: str
    coe: str
    unit: str
    departmentname: str
    announcementyear: str
    source_record_id: str

    def to_official_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "coe": self.coe,
            "unit": self.unit,
            "departmentname": self.departmentname,
            "announcementyear": self.announcementyear,
            "source_record_id": self.source_record_id,
        }


@dataclass(frozen=True)
class CfpSnapshot:
    """Canonical snapshot of a complete paginated CFP_P_02 retrieval."""

    dataset_code: str
    source_url: str
    dataset_page_url: str
    retrieved_at: str
    response_sha256: str
    page_count: int
    record_count: int
    records: tuple[OfficialCfpRecord, ...]
    parser_status: str = "parsed"
    review_reason: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_canonical_dict(self) -> dict[str, Any]:
        payload = {
            "dataset_code": self.dataset_code,
            "source_url": self.source_url,
            "dataset_page_url": self.dataset_page_url,
            "retrieved_at": self.retrieved_at,
            "response_sha256": self.response_sha256,
            "page_count": self.page_count,
            "record_count": self.record_count,
            "parser_status": self.parser_status,
            "review_reason": self.review_reason,
            "records": [row.to_official_dict() for row in self.records],
        }
        if self.extra:
            payload["extra"] = self.extra
        return payload

    def to_canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_canonical_dict())


def resolve_moenv_api_key(environ: Mapping[str, str] | None = None) -> str:
    """Return MOENV_API_KEY if present. Blank means use the public resource."""
    source = os.environ if environ is None else environ
    return str(source.get(API_KEY_ENV) or "").strip()


def redact_api_key_from_url(url: str) -> str:
    """Drop secrets and encode query values so the stored URL is one href.

    Snapshots never store api_key/token. Values such as ``ImportDate desc``
    become ``ImportDate%20desc``. Query names and meaning are unchanged.
    """
    text = str(url or "")
    parsed = urlparse(text)
    if not parsed.query:
        return text
    kept: list[tuple[str, str]] = []
    for name, value in parse_qsl(parsed.query, keep_blank_values=True):
        if name.strip().lower() in QUERY_TOKEN_NAMES:
            continue
        kept.append((name, value))
    return urlunparse(
        parsed._replace(query=urlencode(kept, quote_via=quote))
    )


def official_source_record_id(
    *,
    name: str,
    coe: str,
    unit: str,
    departmentname: str,
    announcementyear: str,
) -> str:
    """Deterministic id from official fields only."""
    basis = "|".join(
        [
            _canon(name),
            _canon(coe),
            _canon(unit),
            _canon(departmentname),
            _canon(announcementyear),
        ]
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def is_generic_steel_label(value: str) -> bool:
    return _canon(value).lower() in {item.lower() for item in GENERIC_STEEL_LABELS}


def is_steel_official_product(
    name: str,
    *,
    taxonomy_names: Sequence[str] | None = None,
) -> bool:
    """Keep distinct official product names. Never treat 採購鋼材 as a product."""
    cleaned = _canon(name)
    if not cleaned or is_generic_steel_label(cleaned):
        return False
    names = (
        tuple(taxonomy_names)
        if taxonomy_names is not None
        else STEEL_OFFICIAL_PRODUCT_NAMES
    )
    if cleaned in names:
        return True
    return False


def parse_declared_factor_units(unit: str) -> tuple[str, str] | None:
    """Map a CFP declared unit to kgCO2e / mass denominator when unambiguous.

    Coe is documented as kgCO2e. Unknown units are not guessed.
    """
    cleaned = _canon(unit).lower().replace(" ", "")
    cleaned = cleaned.replace("（", "(").replace("）", ")")
    if not cleaned:
        return None
    if cleaned in {item.lower() for item in _T_UNITS} or "公噸" in cleaned:
        return "kgCO2e", "t"
    if cleaned in {item.lower() for item in _KG_UNITS}:
        return "kgCO2e", "kg"
    if "公斤" in cleaned or "(kg)" in cleaned or cleaned == "kg":
        return "kgCO2e", "kg"
    return None


def extract_records(payload: Mapping[str, Any] | Sequence[Any]) -> list[dict[str, Any]]:
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return [dict(item) for item in payload if isinstance(item, Mapping)]
    if not isinstance(payload, Mapping):
        raise CfpParseError(
            "CFP_P_02 response is not a JSON object or record list; "
            "fail closed pending schema review."
        )
    for key in ("records", "result", "data"):
        value = payload.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [dict(item) for item in value if isinstance(item, Mapping)]
        if isinstance(value, Mapping):
            nested = value.get("records")
            if isinstance(nested, Sequence) and not isinstance(nested, (str, bytes)):
                return [dict(item) for item in nested if isinstance(item, Mapping)]
    raise CfpParseError(
        "CFP_P_02 JSON is missing a records array; fail closed because "
        "required official fields cannot be confirmed."
    )


def normalize_official_record(raw: Mapping[str, Any]) -> OfficialCfpRecord:
    lowered = {_canon(key).lower(): raw.get(key) for key in raw}
    values: dict[str, str] = {}
    for field_name in OFFICIAL_FIELDS:
        values[field_name] = _canon(lowered.get(field_name.lower()))
    missing = [name for name in REQUIRED_RECORD_FIELDS if not values[name]]
    if missing:
        raise CfpParseError(
            "CFP_P_02 record is missing required official field(s) "
            f"{', '.join(missing)}; fail closed and do not invent values."
        )
    if not _is_numeric(values["coe"]):
        raise CfpParseError(
            f"CFP_P_02 coe is not numeric for name={values['name']!r}; "
            "fail closed."
        )
    source_id = official_source_record_id(
        name=values["name"],
        coe=values["coe"],
        unit=values["unit"],
        departmentname=values["departmentname"],
        announcementyear=values["announcementyear"],
    )
    return OfficialCfpRecord(
        name=values["name"],
        coe=values["coe"],
        unit=values["unit"],
        departmentname=values["departmentname"],
        announcementyear=values["announcementyear"],
        source_record_id=source_id,
    )


def parse_official_records(
    payload: Mapping[str, Any] | Sequence[Any],
) -> list[OfficialCfpRecord]:
    records = extract_records(payload)
    return [normalize_official_record(item) for item in records]


def steel_official_records(
    records: Sequence[OfficialCfpRecord],
    *,
    taxonomy_names: Sequence[str] | None = None,
) -> list[OfficialCfpRecord]:
    return [
        record
        for record in records
        if is_steel_official_product(
            record.name, taxonomy_names=taxonomy_names
        )
    ]


def fetch_all_pages(
    page_fetcher: PageFetcher,
    *,
    api_key: str = "",
    limit: int = DEFAULT_PAGE_LIMIT,
) -> list[Any]:
    """Walk offset/limit until a short or empty page. Never assume one page."""
    if limit <= 0:
        raise CfpParseError("CFP_P_02 page limit must be a positive integer.")
    offset = 0
    pages: list[Any] = []
    while offset <= PAGINATION_SAFETY_LIMIT:
        payload = page_fetcher(offset=offset, limit=limit, api_key=api_key)
        decoded = _coerce_payload(payload)
        records = extract_records(decoded)
        pages.append(decoded)
        if not records or len(records) < limit:
            return pages
        offset += limit
    raise CfpParseError(
        "CFP_P_02 pagination exceeded the safety limit without a terminal "
        "page; fail closed."
    )


def build_snapshot(
    pages: Sequence[Any],
    *,
    retrieved_at: str,
    source_url: str = API_BASE_URL,
    taxonomy_names: Sequence[str] | None = None,
) -> CfpSnapshot:
    records: list[OfficialCfpRecord] = []
    for page in pages:
        records.extend(parse_official_records(_coerce_payload(page)))
    canonical_records = [row.to_official_dict() for row in records]
    digest = hashlib.sha256(
        _canonical_json_bytes(
            {
                "dataset_code": DATASET_CODE,
                "records": canonical_records,
            }
        )
    ).hexdigest()
    return CfpSnapshot(
        dataset_code=DATASET_CODE,
        source_url=redact_api_key_from_url(source_url) or API_BASE_URL,
        dataset_page_url=DATASET_PAGE_URL,
        retrieved_at=retrieved_at,
        response_sha256=digest,
        page_count=len(pages),
        record_count=len(records),
        records=tuple(records),
        extra={
            "steel_record_count": len(
                steel_official_records(records, taxonomy_names=taxonomy_names)
            ),
            "lifecycle_boundary_stated_by_api": False,
            "official_validity_period_stated_by_api": False,
            "geography_stated_by_api": False,
            "technology_stated_by_api": False,
        },
    )


def fetch_cfp_p_02_snapshot(
    *,
    retrieved_at: str,
    api_key: str = "",
    page_fetcher: PageFetcher | None = None,
    limit: int = DEFAULT_PAGE_LIMIT,
    environ: Mapping[str, str] | None = None,
    dataset_page_url: str = DATA_GOV_DATASET_PAGE_URL,
    dataset_page_fetcher: Callable[[], str] | None = None,
    public_resource_fetcher: Callable[[str], bytes] | None = None,
) -> CfpSnapshot:
    """Fetch CFP_P_02. Public data.gov.tw resource first; API key is optional."""
    if page_fetcher is not None:
        pages = fetch_all_pages(page_fetcher, api_key=api_key, limit=limit)
        return build_snapshot(
            pages,
            retrieved_at=retrieved_at,
            source_url=API_BASE_URL,
        )
    public_error: Exception | None = None
    try:
        return fetch_snapshot_from_data_gov(
            retrieved_at=retrieved_at,
            dataset_page_url=dataset_page_url,
            dataset_page_fetcher=dataset_page_fetcher,
            resource_fetcher=public_resource_fetcher,
            limit=limit,
        )
    except (CfpApiError, CfpParseError) as exc:
        public_error = exc
    key = api_key or resolve_moenv_api_key(environ)
    if not key:
        if public_error is not None:
            raise public_error
        raise CfpApiError(
            "PUBLIC_RESOURCE_UNAVAILABLE",
            "CFP_P_02 public resource could not be fetched and no "
            "MOENV_API_KEY fallback is configured.",
        )
    pages = fetch_all_pages(
        default_http_page_fetcher, api_key=key, limit=limit
    )
    return build_snapshot(pages, retrieved_at=retrieved_at, source_url=API_BASE_URL)


def parse_data_gov_dataset_distributions(html: str) -> list[dict[str, str]]:
    """Parse JSON-LD DataDownload links from the government dataset page."""
    if not _canon(html):
        raise CfpParseError(
            "data.gov.tw dataset page is empty; fail closed."
        )
    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.I | re.S,
    )
    distributions: list[dict[str, str]] = []
    for block in blocks:
        try:
            payload = json.loads(html_lib.unescape(block))
        except json.JSONDecodeError:
            continue
        for dataset in _jsonld_datasets(payload):
            for item in dataset.get("distribution") or []:
                if not isinstance(item, Mapping):
                    continue
                content_url = html_lib.unescape(_canon(item.get("contentUrl")))
                encoding = _encoding_kind(item.get("encodingFormat"))
                if content_url:
                    distributions.append(
                        {
                            "encoding_format": encoding,
                            "content_url": content_url,
                        }
                    )
    if not distributions:
        raise CfpParseError(
            "data.gov.tw dataset page JSON-LD has no DataDownload "
            "contentUrl; fail closed."
        )
    return distributions


def select_public_cfp_resource_url(
    distributions: Sequence[Mapping[str, str]],
) -> tuple[str, str]:
    """Return (url, format) preferring JSON, then CSV. Never invent a token."""
    by_format: dict[str, str] = {}
    for item in distributions:
        encoding = _encoding_kind(item.get("encoding_format"))
        url = _canon(item.get("content_url"))
        if encoding and url and encoding not in by_format:
            by_format[encoding] = url
    if "JSON" in by_format:
        return by_format["JSON"], "JSON"
    if "CSV" in by_format:
        return by_format["CSV"], "CSV"
    raise CfpParseError(
        "Official dataset page has no JSON or CSV resource URL; fail closed."
    )


def fetch_snapshot_from_data_gov(
    *,
    retrieved_at: str,
    dataset_page_url: str = DATA_GOV_DATASET_PAGE_URL,
    dataset_page_fetcher: Callable[[], str] | None = None,
    resource_fetcher: Callable[[str], bytes] | None = None,
    limit: int = DEFAULT_PAGE_LIMIT,
) -> CfpSnapshot:
    html = (
        dataset_page_fetcher()
        if dataset_page_fetcher is not None
        else _http_get_text(dataset_page_url)
    )
    resource_url, encoding = select_public_cfp_resource_url(
        parse_data_gov_dataset_distributions(html)
    )
    _assert_allowed_host(resource_url)
    pages = fetch_public_resource_pages(
        resource_url,
        encoding=encoding,
        limit=limit,
        resource_fetcher=resource_fetcher,
    )
    snapshot = build_snapshot(
        pages,
        retrieved_at=retrieved_at,
        source_url=redact_api_key_from_url(resource_url),
    )
    extra = dict(snapshot.extra)
    extra.update(
        {
            "source_dataset": DATASET_CODE,
            "data_gov_dataset_id": DATA_GOV_DATASET_ID,
            "data_gov_dataset_page": DATA_GOV_DATASET_PAGE_URL,
            "public_resource_format": encoding,
            "public_resource_url_redacted": redact_api_key_from_url(resource_url),
        }
    )
    return CfpSnapshot(
        dataset_code=snapshot.dataset_code,
        source_url=snapshot.source_url,
        dataset_page_url=DATA_GOV_DATASET_PAGE_URL,
        retrieved_at=snapshot.retrieved_at,
        response_sha256=snapshot.response_sha256,
        page_count=snapshot.page_count,
        record_count=snapshot.record_count,
        records=snapshot.records,
        parser_status=snapshot.parser_status,
        review_reason=snapshot.review_reason,
        extra=extra,
    )


def fetch_public_resource_pages(
    resource_url: str,
    *,
    encoding: str,
    limit: int = DEFAULT_PAGE_LIMIT,
    resource_fetcher: Callable[[str], bytes] | None = None,
) -> list[Any]:
    """Walk offset/limit on the parsed public URL. Do not invent query tokens."""
    if limit <= 0:
        raise CfpParseError("CFP_P_02 page limit must be a positive integer.")
    pages: list[Any] = []
    offset = 0
    while offset <= PAGINATION_SAFETY_LIMIT:
        page_url = _with_offset_limit(resource_url, offset=offset, limit=limit)
        raw = (
            resource_fetcher(page_url)
            if resource_fetcher is not None
            else _http_get_bytes(page_url)
        )
        payload = _payload_from_public_bytes(raw, encoding=encoding)
        records = extract_records(payload)
        pages.append(payload)
        if not records or len(records) < limit:
            return pages
        offset += limit
    raise CfpParseError(
        "CFP_P_02 public resource pagination exceeded the safety limit; "
        "fail closed."
    )


def default_http_page_fetcher(
    *,
    offset: int,
    limit: int,
    api_key: str = "",
) -> dict[str, Any]:
    if not api_key:
        raise CfpApiError(
            "CREDENTIAL_REQUIRED",
            "MOENV_API_KEY is required only for the optional API fallback.",
        )
    query = urlencode(
        {
            "offset": str(offset),
            "limit": str(limit),
            "format": "json",
            "api_key": api_key,
        }
    )
    url = f"{API_BASE_URL}?{query}"
    raw = _http_get_bytes(url)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CfpParseError(
            "CFP_P_02 response is not UTF-8 JSON; fail closed."
        ) from exc
    if not isinstance(payload, (Mapping, Sequence)):
        raise CfpParseError("CFP_P_02 JSON root type is unsupported.")
    return dict(payload) if isinstance(payload, Mapping) else {"records": payload}


def candidate_records_from_snapshot(
    snapshot: CfpSnapshot,
    *,
    taxonomy_names: Sequence[str] | None = None,
) -> list[dict[str, str]]:
    """Steel candidates with official fields only. Review fields stay blank."""
    rows: list[dict[str, str]] = []
    for record in steel_official_records(
        snapshot.records, taxonomy_names=taxonomy_names
    ):
        units = parse_declared_factor_units(record.unit)
        numerator = units[0] if units else ""
        denominator = units[1] if units else ""
        rows.append(
            {
                "reference_type": "purchased_steel_average_data",
                "candidate_type": "purchased_steel_average_data",
                "activity_type": "purchased_steel",
                "factor_category": record.name,
                "steel_product_type": record.name,
                "factor_year": record.announcementyear,
                "factor_value": record.coe,
                "numerator_unit": numerator,
                "denominator_unit": denominator,
                "factor_unit": (
                    f"{numerator}/{denominator}" if numerator and denominator else ""
                ),
                "geography": "",
                "valid_from": "",
                "valid_to": "",
                "lifecycle_boundary": "",
                "technology": "",
                "approved_for_reporting_from": "",
                "approved_for_reporting_to": "",
                "approval_status": "pending_review",
                "reviewer": "",
                "approved_at": "",
                "factor_version": "",
                "source_record_id": record.source_record_id,
                "source_locator": record.source_record_id,
                "source_url": snapshot.source_url,
                "snapshot_hash": snapshot.response_sha256,
                "official_name": record.name,
                "official_coe": record.coe,
                "official_unit": record.unit,
                "official_departmentname": record.departmentname,
                "source_dataset": DATASET_CODE,
                "retrieved_at": snapshot.retrieved_at,
                "official_valid_from": "",
                "official_valid_to": "",
                "publisher": record.departmentname,
                "official_announcementyear": record.announcementyear,
                "target_registry": "purchased_steel_factors",
                "is_secondary_or_proxy": "true",
                "applicability_notes": (
                    "Official CFP_P_02 raw fields only. The API does not "
                    "state cradle-to-gate boundary, geography, technology, "
                    "or a reporting validity period. announcementyear is "
                    "the data/announcement year, not valid_from."
                ),
            }
        )
    return rows


def _canon(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_numeric(value: str) -> bool:
    try:
        number = Decimal(value.replace(",", ""))
    except (InvalidOperation, ValueError):
        return False
    return number.is_finite()


def _coerce_payload(payload: Any) -> Mapping[str, Any] | Sequence[Any]:
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CfpParseError(
                "CFP_P_02 page is not UTF-8 JSON; fail closed."
            ) from exc
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise CfpParseError(
                "CFP_P_02 page is not JSON; fail closed."
            ) from exc
    if isinstance(payload, (Mapping, Sequence)) and not isinstance(
        payload, (str, bytes)
    ):
        return payload
    raise CfpParseError("CFP_P_02 page type is unsupported; fail closed.")


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _jsonld_datasets(payload: Any) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            types = node.get("@type")
            type_list = types if isinstance(types, Sequence) and not isinstance(
                types, (str, bytes)
            ) else [types]
            if any(_canon(item) == "Dataset" for item in type_list):
                found.append(node)
            if "@graph" in node:
                walk(node.get("@graph"))
            for key in ("hasPart", "dataset", "mainEntity"):
                if key in node:
                    walk(node.get(key))
            return
        if isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
            for item in node:
                walk(item)

    walk(payload)
    return found


def _encoding_kind(value: str) -> str:
    cleaned = _canon(value).upper()
    if "JSON" in cleaned:
        return "JSON"
    if "CSV" in cleaned:
        return "CSV"
    if "XML" in cleaned:
        return "XML"
    return cleaned


def _assert_allowed_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_FETCH_HOSTS:
        raise CfpApiError(
            "HOST_NOT_ALLOWLISTED",
            f"CFP_P_02 fetch host {host!r} is not allowlisted.",
        )
    return host


def _safe_request_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode(parse_qsl(parts.query, keep_blank_values=True), quote_via=quote)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, query, parts.fragment)
    )


def _ssl_context_for_host(host: str) -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    if host == ALLOWED_HOST and hasattr(ssl, "VERIFY_X509_STRICT"):
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def _http_get_bytes(url: str) -> bytes:
    _assert_allowed_host(url)
    safe_url = _safe_request_url(url)
    host = (urlparse(safe_url).hostname or "").lower()
    opener = build_opener(HTTPSHandler(context=_ssl_context_for_host(host)))
    request = Request(
        safe_url,
        headers={"User-Agent": "carbon-evidence-ledger/cfp-p-02"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=60) as response:
            final_host = (
                urlparse(getattr(response, "url", safe_url)).hostname or ""
            ).lower()
            if final_host not in ALLOWED_FETCH_HOSTS:
                raise CfpApiError(
                    "HOST_NOT_ALLOWLISTED",
                    f"CFP_P_02 fetch redirected off allowlisted hosts to "
                    f"{final_host!r}.",
                )
            return response.read()
    except HTTPError as exc:
        raise CfpApiError("HTTP_ERROR", f"CFP_P_02 HTTP {exc.code}.") from exc
    except URLError as exc:
        raise CfpApiError("NETWORK_ERROR", "CFP_P_02 network error.") from exc


def _http_get_text(url: str) -> str:
    raw = _http_get_bytes(url)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CfpParseError("Official page is not UTF-8; fail closed.") from exc


def _with_offset_limit(url: str, *, offset: int, limit: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["offset"] = str(offset)
    query["limit"] = str(limit)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query, quote_via=quote),
            parts.fragment,
        )
    )


def _payload_from_public_bytes(raw: bytes, *, encoding: str) -> Mapping[str, Any]:
    kind = encoding.upper()
    if kind == "CSV":
        return {"records": _records_from_csv(raw)}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CfpParseError(
            "Official public resource is not UTF-8 JSON; fail closed."
        ) from exc
    coerced = _coerce_payload(payload)
    if isinstance(coerced, Mapping):
        return coerced
    return {"records": list(coerced)}


def _records_from_csv(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CfpParseError("Official CSV is not UTF-8; fail closed.") from exc
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, Any]] = []
    for item in reader:
        rows.append({str(key).strip(): item.get(key) for key in item})
    if not rows:
        raise CfpParseError("Official CSV has no data rows; fail closed.")
    return rows
