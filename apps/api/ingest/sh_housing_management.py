"""Adapter for Seoul Open Data's SH housing-management reference service.

This source describes managed housing complexes.  It is deliberately kept
separate from supply-plan projects: no coordinates or supply quantities are
invented from a management row.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import httpx


SERVICE_NAME = "SearchSHRentApt"
BASE_URL = "http://openapi.seoul.go.kr:8088"
SOURCE_ID = "DS-SH-HOUSING-MANAGEMENT"
SOURCE_URL = "https://data.seoul.go.kr/dataList/OA-12027/S/1/datasetView.do"
REQUIRED_FIELDS = ("GU_NM", "APT_NM", "APT_TYPE", "APT_CNT", "APT_OPEN_DT", "APT_ADDR", "APT_ZIP", "APT_TEL")
_NUMERIC_RE = re.compile(r"^\d+(?:\.0+)?$")


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    result_code: str | None
    result_message: str | None
    total_count: int | None
    rows: list[dict[str, Any]]
    envelope_keys: list[str]


def normalize_name(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def nullable_integer(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    cleaned = str(value).replace(",", "").strip()
    if not _NUMERIC_RE.fullmatch(cleaned):
        return None
    return int(float(cleaned))


def parse_open_date(raw_value: Any) -> tuple[date | None, str | None]:
    """Return a date only for explicitly recognised formats.

    The SH preview shows Excel serial values.  The raw value is always kept by
    the caller; this conservative conversion merely exposes a verified date.
    """
    if raw_value is None or str(raw_value).strip() == "":
        return None, None
    raw = str(raw_value).strip()
    if _NUMERIC_RE.fullmatch(raw):
        serial = int(float(raw))
        if 1 <= serial <= 60000:
            return date(1899, 12, 30) + timedelta(days=serial), "EXCEL_SERIAL"
        return None, None
    for separator in ("-", ".", "/"):
        parts = raw.split(separator)
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            try:
                return date(int(parts[0]), int(parts[1]), int(parts[2])), "ISO_DATE"
            except ValueError:
                return None, None
    return None, None


class ShHousingManagementAdapter:
    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None) -> None:
        self.api_key = api_key or os.getenv("SEOUL_OPEN_DATA_API_KEY")
        self.client = client or httpx.Client(timeout=30.0)

    def fetch(self, start: int, end: int) -> FetchResult:
        if not self.api_key:
            raise ValueError("SEOUL_OPEN_DATA_API_KEY is required")
        if start < 1 or end < start:
            raise ValueError("start/end must be positive and ordered")
        # Never include this URL in an exception or log: it contains the key.
        url = f"{BASE_URL}/{self.api_key}/json/{SERVICE_NAME}/{start}/{end}/"
        try:
            response = self.client.get(url)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Seoul Open Data request failed: {type(exc).__name__}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("Seoul Open Data returned a non-JSON response") from exc
        envelope = payload.get(SERVICE_NAME) if isinstance(payload, dict) else None
        if not isinstance(envelope, dict):
            raise RuntimeError("Seoul Open Data response did not contain the expected service envelope")
        result = envelope.get("RESULT") if isinstance(envelope.get("RESULT"), dict) else {}
        rows = envelope.get("row") if isinstance(envelope.get("row"), list) else []
        total = nullable_integer(envelope.get("list_total_count"))
        return FetchResult(
            status_code=response.status_code,
            result_code=result.get("CODE"),
            result_message=result.get("MESSAGE"),
            total_count=total,
            rows=[row for row in rows if isinstance(row, dict)],
            envelope_keys=sorted(envelope.keys()),
        )
