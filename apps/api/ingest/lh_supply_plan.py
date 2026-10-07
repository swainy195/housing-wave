"""Parser for the official LH rental-housing supply-plan table.

The source only supplies month-level periods, so this adapter never invents a
day.  A row remains a row even when its district appears with several areas.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

import httpx

SOURCE_URL = "https://apply.lh.or.kr/lhapply/apply/noti/sp/list.do"
SOURCE_ID = "DS-LH-2026-RENTAL-PLAN"
SOURCE_SYSTEM = "LH_RENTAL_SUPPLY_PLAN"
CAPITAL_REGION_CODES = {"서울특별시": "11", "경기도": "41", "인천광역시": "28"}
PROVINCE_MAP = {"서울특별시": "서울", "경기도": "경기", "인천광역시": "인천"}
PERIOD_RE = re.compile(r"^(?P<year>\d{4})년\s*(?P<month>\d{1,2})월$")


def clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


class _SupplyPlanParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_tbody = False
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tbody": self._in_tbody = True
        elif self._in_tbody and tag == "tr": self._row = []
        elif self._row is not None and tag == "td": self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None: self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._cell is not None and self._row is not None:
            self._row.append(clean("".join(self._cell))); self._cell = None
        elif tag == "tr" and self._row is not None:
            if len(self._row) == 9: self.rows.append(self._row)
            self._row = None
        elif tag == "tbody": self._in_tbody = False


def parse_supply_plan(html: str) -> tuple[list[dict[str, Any]], int | None]:
    parser = _SupplyPlanParser(); parser.feed(html)
    count_match = re.search(r"전체\s*<strong>\s*([\d,]+)\s*</strong>\s*건", html)
    total = int(count_match.group(1).replace(",", "")) if count_match else None
    names = ("region_name", "housing_type", "housing_name", "exclusive_area", "supply_units", "planned_supply_period", "planned_move_in_period", "regional_headquarters", "note")
    rows = []
    for row in parser.rows:
        item = dict(zip(names, row, strict=True))
        try: item["supply_units"] = int(item["supply_units"].replace(",", ""))
        except ValueError: item["supply_units"] = None
        if item["region_name"] in CAPITAL_REGION_CODES: rows.append(item)
    return rows, total


def parse_month(value: str) -> tuple[int, int] | None:
    match = PERIOD_RE.match(clean(value))
    return (int(match["year"]), int(match["month"])) if match else None


def normalized_name(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


class LhSupplyPlanAdapter:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30.0, follow_redirects=True)

    def fetch(self, region_code: str, page: int = 1, page_size: int = 100) -> tuple[list[dict[str, Any]], int | None]:
        params = {"mi": "1042", "sUppAisTpCd": "06", "srchCnpCd": region_code, "currPage": page, "listCo": page_size}
        response = self.client.get(SOURCE_URL, params=params)
        response.raise_for_status()
        # LH serves a UTF-8 document but does not consistently advertise it.
        response.encoding = "utf-8"
        return parse_supply_plan(response.text)
