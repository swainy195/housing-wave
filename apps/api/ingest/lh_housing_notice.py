"""LH notice-list adapter; list data never automatically establishes a project match."""
import json
from datetime import date
from typing import Any
from urllib.parse import unquote
import httpx

BASE_URL = "https://apis.data.go.kr/B552555/lhLeaseNoticeInfo1/lhLeaseNoticeInfo1"
REGION_CODES = {"seoul": "11", "gyeonggi": "41", "incheon": "28"}
TYPE_MAP = {"분양주택": "PUBLIC_SALE", "임대주택": "PUBLIC_RENTAL", "행복주택": "HAPPY_HOUSING", "신혼희망타운": "NEWLYWED"}

def parse_payload(payload: str) -> list[dict[str, Any]]:
    data = json.loads(payload)
    if not isinstance(data, list) or not any("resHeader" in part for part in data if isinstance(part, dict)):
        raise ValueError("Unexpected LH response envelope")
    header = next(part["resHeader"] for part in data if isinstance(part, dict) and "resHeader" in part)
    if not header or header[0].get("SS_CODE") != "Y":
        raise ValueError("LH API returned an unsuccessful response")
    return [dict(row) for part in data if isinstance(part, dict) for row in part.get("dsList", [])]

def normalize(row: dict[str, Any]) -> dict[str, Any]:
    notice_type = row.get("AIS_TP_CD_NM") or row.get("UPP_AIS_TP_NM")
    return {"external_id": row.get("PAN_ID"), "name": row.get("PAN_NM"), "region": row.get("CNP_CD_NM"), "source_type": notice_type, "supply_type": TYPE_MAP.get(notice_type, "OTHER"), "notice_status": row.get("PAN_SS"), "announcement_date": row.get("PAN_NT_ST_DT"), "application_end_date": row.get("CLSG_DT"), "source_url": row.get("DTL_URL"), "supply_units": None, "target_group": None, "validation_status": "REVIEW_REQUIRED", "raw_item": row}

class LhHousingNoticeAdapter:
    def __init__(self, service_key: str) -> None:
        if not service_key: raise ValueError("LH_HOUSING_NOTICE_API_KEY is required")
        self.service_key = unquote(service_key)
    def fetch(self, region: str, start: date, end: date, page: int = 1, page_size: int = 20) -> list[dict[str, Any]]:
        if region not in REGION_CODES: raise ValueError("region must be seoul, gyeonggi, or incheon")
        params = {"ServiceKey": self.service_key, "PG_SZ": page_size, "PAGE": page, "CNP_CD": REGION_CODES[region], "PAN_NT_ST_DT": start.strftime("%Y.%m.%d"), "CLSG_DT": end.strftime("%Y.%m.%d")}
        response = httpx.get(BASE_URL, params=params, timeout=20.0)
        response.raise_for_status()
        return parse_payload(response.text)
