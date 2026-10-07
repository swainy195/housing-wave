"""MOLIT Building-HUB housing-permit ingestion, using only documented parcel-key queries."""

import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import httpx
from sqlalchemy import Engine, create_engine, text

from apps.api.repositories.postgres_repository import sqlalchemy_database_url


BASE_URL = "https://apis.data.go.kr/1613000/HsPmsHubService"
ENDPOINT = "getHpBasisOulnInfo"
SOURCE_ID = "DS-MOLIT-HOUSING-PERMIT"
SOURCE_SYSTEM = "MOLIT_HSPMS_HUB"
REGION_NAMES = {"seoul": "서울", "gyeonggi": "경기", "incheon": "인천"}


class MolitApiError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ParcelQuery:
    region: str
    sigungu_cd: str
    bjdong_cd: str
    plat_gb_cd: str
    bun: str
    ji: str

    def __post_init__(self) -> None:
        if self.region not in REGION_NAMES:
            raise ValueError("region must be seoul, gyeonggi, or incheon")
        for value, length, label in ((self.sigungu_cd, 5, "sigungu_cd"), (self.bjdong_cd, 5, "bjdong_cd"), (self.bun, 4, "bun"), (self.ji, 4, "ji")):
            if not value.isdigit() or len(value) != length:
                raise ValueError(f"{label} must be {length} digits")
        if self.plat_gb_cd not in {"0", "1"}:
            raise ValueError("plat_gb_cd must be 0 (land) or 1 (mountain)")

    @property
    def request_key(self) -> str:
        return "-".join((self.sigungu_cd, self.bjdong_cd, self.plat_gb_cd, self.bun, self.ji))

    def params(self) -> dict[str, str]:
        return {"sigunguCd": self.sigungu_cd, "bjdongCd": self.bjdong_cd, "platGbCd": self.plat_gb_cd, "bun": self.bun, "ji": self.ji}


def _first(item: dict[str, Any], *names: str) -> str | None:
    for name in names:
        value = item.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    if len(digits) != 8:
        return None
    try:
        return datetime.strptime(digits, "%Y%m%d").date()
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value.replace(",", "")))
    except ValueError:
        return None


def _element_to_dict(element: ET.Element) -> dict[str, Any]:
    return {child.tag.split("}")[-1]: (child.text or "").strip() for child in element}


def parse_response(payload: str, content_type: str = "") -> tuple[list[dict[str, Any]], int, str]:
    """Parse the public API's JSON/XML envelope; reject portal error responses."""
    if "xml" not in content_type.lower() and payload.lstrip().startswith(("{", "[")):
        data = json.loads(payload)
        response = data.get("response", data)
        header = response.get("header", {}) if isinstance(response, dict) else {}
        code = str(header.get("resultCode", "00"))
        if code not in {"00", "0", "NORMAL_SERVICE"}:
            raise MolitApiError(f"MOLIT resultCode={code}: {header.get('resultMsg', 'unknown error')}")
        body = response.get("body", {})
        items = body.get("items", {}) if isinstance(body, dict) else {}
        rows = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(rows, dict):
            rows = [rows]
        return [dict(row) for row in rows], int(body.get("totalCount", len(rows)) or 0), "JSON"

    root = ET.fromstring(payload)
    header = root.find(".//header")
    code = (header.findtext("resultCode") if header is not None else "00") or "00"
    if code not in {"00", "0", "NORMAL_SERVICE"}:
        message = header.findtext("resultMsg") if header is not None else "unknown error"
        raise MolitApiError(f"MOLIT resultCode={code}: {message}")
    rows = [_element_to_dict(item) for item in root.findall(".//items/item")]
    total = root.findtext(".//body/totalCount") or str(len(rows))
    return rows, int(total), "XML"


def normalize_item(item: dict[str, Any], parcel: ParcelQuery, reference_date: date) -> dict[str, Any]:
    external_id = _first(item, "mgmHsrgstPk")
    name = _first(item, "bldNm", "splotNm")
    address = _first(item, "platPlc")
    units = _parse_int(_first(item, "totHhldCnt"))
    approval_date = _parse_date(_first(item, "apprvDay"))
    status = "VALIDATED" if external_id and name and units is not None else "REVIEW_REQUIRED"
    return {
        "external_id": external_id,
        "name": name or (f"국토부 주택인허가 원천 {external_id}" if external_id else None),
        "province": REGION_NAMES[parcel.region],
        "district": None,
        "address": address,
        "planned_units": units,
        "housing_type": _first(item, "purpsCdNm"),
        "approval_date": approval_date,
        "reference_date": reference_date,
        "data_status": "AVAILABLE" if status == "VALIDATED" else "PARTIAL",
        "validation_status": status,
        "raw_item": item,
    }


class MolitHousingPermitAdapter:
    source_id = SOURCE_ID

    def __init__(self, service_key: str, client: httpx.Client | None = None) -> None:
        if not service_key:
            raise ValueError("MOLIT_HOUSING_PERMIT_API_KEY is required")
        self.service_key = service_key
        self.client = client or httpx.Client(timeout=20.0)

    def fetch(self, parcel: ParcelQuery, page: int = 1, num_rows: int = 20) -> tuple[str, int, list[dict[str, Any]], int, str]:
        params = {"serviceKey": self.service_key, "pageNo": str(page), "numOfRows": str(num_rows), "type": "json", **parcel.params()}
        for attempt in range(2):
            try:
                response = self.client.get(f"{BASE_URL}/{ENDPOINT}", params=params)
                response.raise_for_status()
                rows, total, response_format = parse_response(response.text, response.headers.get("content-type", ""))
                return response.text, response.status_code, rows, total, response_format
            except (httpx.TimeoutException, httpx.TransportError) as error:
                if attempt:
                    raise MolitApiError(f"MOLIT transport error: {error.__class__.__name__}") from error
                time.sleep(0.5)
            except httpx.HTTPStatusError as error:
                raise MolitApiError(f"MOLIT HTTP status={error.response.status_code}") from error
        raise AssertionError("unreachable")


class MolitPermitPersister:
    def __init__(self, database_url: str, engine: Engine | None = None) -> None:
        self.engine = engine or create_engine(sqlalchemy_database_url(database_url), pool_pre_ping=True)

    @staticmethod
    def _id(prefix: str, value: str) -> str:
        return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:20]}"

    def persist(self, parcel: ParcelQuery, payload: str, http_status: int, response_format: str, normalized: list[dict[str, Any]], fetched_at: datetime | None = None) -> dict[str, int]:
        fetched_at = fetched_at or datetime.now(timezone.utc)
        summary = {"inserted": 0, "updated": 0, "skipped": 0, "review_required": 0, "raw_inserted": 0}
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO organizations (id, name, organization_type) VALUES ('ORG-MOLIT', '국토교통부', 'CENTRAL_GOVERNMENT') ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name"))
            conn.execute(text("""INSERT INTO data_sources (id, organization_id, source_name, source_url, source_type, collection_method, reference_date, collected_at, validation_status, is_demo)
                VALUES (:id, 'ORG-MOLIT', '건축HUB 주택인허가 기본개요', :url, 'API', 'API', :reference_date, :collected_at, 'RAW', false)
                ON CONFLICT (id) DO UPDATE SET reference_date = EXCLUDED.reference_date, collected_at = EXCLUDED.collected_at, validation_status = EXCLUDED.validation_status"""), {"id": SOURCE_ID, "url": f"{BASE_URL}/{ENDPOINT}", "reference_date": date.today(), "collected_at": fetched_at})
            for record in normalized:
                raw_json = record["raw_item"]
                checksum = hashlib.sha256(json.dumps(raw_json, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                raw_id = self._id("RAW", f"{parcel.request_key}:{checksum}")
                parse_status = "PARSED" if record["validation_status"] == "VALIDATED" else "REVIEW_REQUIRED"
                raw_result = conn.execute(text("""INSERT INTO raw_api_records (id, source_id, source_system, endpoint_name, request_key, request_params, raw_payload, response_format, fetched_at, reference_date, http_status, parse_status, checksum)
                    VALUES (:id, :source_id, :source_system, :endpoint, :request_key, CAST(:params AS jsonb), CAST(:payload AS jsonb), :format, :fetched_at, :reference_date, :http_status, :parse_status, :checksum)
                    ON CONFLICT (source_id, checksum) DO NOTHING"""), {"id": raw_id, "source_id": SOURCE_ID, "source_system": SOURCE_SYSTEM, "endpoint": ENDPOINT, "request_key": parcel.request_key, "params": json.dumps(parcel.params()), "payload": json.dumps(raw_json, ensure_ascii=False), "format": response_format, "fetched_at": fetched_at, "reference_date": record["reference_date"], "http_status": http_status, "parse_status": parse_status, "checksum": checksum})
                summary["raw_inserted"] += raw_result.rowcount
                if record["validation_status"] != "VALIDATED":
                    summary["review_required"] += 1
                    continue
                external_id = record["external_id"]
                project_id = conn.execute(text("SELECT entity_id FROM external_identifiers WHERE entity_type = 'PROJECT' AND source_system = :source AND external_id = :external"), {"source": SOURCE_SYSTEM, "external": external_id}).scalar_one_or_none()
                if project_id is None:
                    project_id = self._id("PRJ-MOLIT", external_id)
                    conn.execute(text("""INSERT INTO projects (id, name, organization_id, province, district, address, planned_units, housing_type, current_stage, data_status, is_demo)
                        VALUES (:id, :name, 'ORG-MOLIT', :province, :district, :address, :units, :housing_type, 'PERMIT', :data_status, false)"""), {"id": project_id, **record, "units": record["planned_units"]})
                    conn.execute(text("INSERT INTO external_identifiers (entity_type, entity_id, source_system, external_id, raw_record_id) VALUES ('PROJECT', :entity, :source, :external, :raw)"), {"entity": project_id, "source": SOURCE_SYSTEM, "external": external_id, "raw": raw_id})
                    summary["inserted"] += 1
                else:
                    conn.execute(text("""UPDATE projects SET name=:name, province=:province, district=:district, address=:address, planned_units=:units, housing_type=:housing_type, current_stage='PERMIT', data_status=:data_status, is_demo=false WHERE id=:id"""), {"id": project_id, **record, "units": record["planned_units"]})
                    summary["updated"] += 1
                event_id = self._id("EVT-MOLIT", f"{external_id}:PERMIT")
                conn.execute(text("""INSERT INTO project_events (id, project_id, stage, event_type, planned_date, actual_date, status, reference_date, source_id, data_status)
                    VALUES (:id, :project_id, 'PERMIT', 'HOUSING_CONSTRUCTION_PROJECT_APPROVAL', NULL, :approval_date, :status, :reference_date, :source_id, :data_status)
                    ON CONFLICT (id) DO UPDATE SET actual_date=EXCLUDED.actual_date, status=EXCLUDED.status, reference_date=EXCLUDED.reference_date, data_status=EXCLUDED.data_status, source_id=EXCLUDED.source_id"""), {"id": event_id, "project_id": project_id, "approval_date": record["approval_date"], "status": "COMPLETED" if record["approval_date"] else "UNKNOWN", "reference_date": record["reference_date"], "source_id": SOURCE_ID, "data_status": record["data_status"]})
            coverage = "AVAILABLE" if summary["inserted"] + summary["updated"] else "PARTIAL"
            conn.execute(text("""INSERT INTO organization_stage_coverage (organization_id, stage, data_status, note) VALUES ('ORG-MOLIT', 'PERMIT', :status, '건축HUB 주택인허가 기본개요 수동 수집')
                ON CONFLICT (organization_id, stage) DO UPDATE SET data_status=EXCLUDED.data_status, note=EXCLUDED.note, updated_at=now()"""), {"status": coverage})
        return summary
