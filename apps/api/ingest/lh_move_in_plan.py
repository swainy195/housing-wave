"""Official LH move-in-plan parser and deliberately conservative matcher."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

import httpx

SOURCE_URL = "https://apply.lh.or.kr/lhapply/apply/noti/mp/list.do?mi=1331"
SOURCE_ID = "DS-LH-MOVE-IN-PLAN"
SOURCE_SYSTEM = "LH_MOVE_IN_PLAN"
PROVINCE_MAP = {"서울특별시": "서울", "경기도": "경기", "인천광역시": "인천"}
MONTH_RE = re.compile(r"^(?P<year>\d{4})\.(?P<month>\d{1,2})$")
BLOCK_RE = re.compile(r"(?<![A-Z0-9])([A-Z]+[- ]?\d+(?:[- ]?\d+)?)(?:BL|블록)?(?![A-Z0-9])")


def clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def normalize_block_name(value: str) -> str:
    """Normalize only case, spacing, hyphen, and BL spelling; preserve meaning."""
    text = clean(value).upper().replace("블록", "BL")
    text = re.sub(r"\s+", "", text)
    text = text.replace("-", "")
    return text


def extract_blocks(value: str) -> tuple[str, ...]:
    blocks = []
    for matched in BLOCK_RE.finditer(clean(value).upper().replace("블록", "BL")):
        block = normalize_block_name(matched.group(1))
        if block and block not in blocks: blocks.append(block)
    return tuple(blocks)


def district_key(value: str) -> str:
    """The district portion must also agree; a block code alone is not a match."""
    text = normalize_block_name(value)
    text = re.sub(r"[A-Z]+\d+(?:\d+)?(?:BL)?", "", text)
    return text


class _MoveInTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.in_tbody = False; self.row: list[str] | None = None; self.cell: list[str] | None = None; self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tbody": self.in_tbody = True
        elif self.in_tbody and tag == "tr": self.row = []
        elif self.row is not None and tag == "td": self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None: self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self.cell is not None and self.row is not None:
            self.row.append(clean("".join(self.cell))); self.cell = None
        elif tag == "tr" and self.row is not None:
            if len(self.row) == 7: self.rows.append(self.row)
            self.row = None
        elif tag == "tbody": self.in_tbody = False


def parse_month(value: str) -> tuple[int, int] | None:
    matched = MONTH_RE.match(clean(value))
    return (int(matched["year"]), int(matched["month"])) if matched else None


def parse_move_in_plan(html: str) -> tuple[list[dict[str, Any]], int | None]:
    parser = _MoveInTableParser(); parser.feed(html)
    total_match = re.search(r"전체\s*<strong>\s*([\d,]+)\s*</strong>\s*건", html)
    total = int(total_match.group(1).replace(",", "")) if total_match else None
    fields = ("region_name", "housing_type", "district_block_name", "construction_units", "planned_move_in_period", "move_in_designation_period", "note")
    rows: list[dict[str, Any]] = []
    for row_number, cells in enumerate(parser.rows, start=1):
        row = dict(zip(fields, cells, strict=True))
        try: row["construction_units"] = int(row["construction_units"].replace(",", ""))
        except ValueError: row["construction_units"] = None
        row["source_row_number"] = row_number
        row["district_block_name_normalized"] = normalize_block_name(row["district_block_name"])
        row["blocks"] = extract_blocks(row["district_block_name"])
        row["province"] = PROVINCE_MAP.get(row["region_name"])
        rows.append(row)
    return rows, total


class LhMoveInPlanAdapter:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=30.0, follow_redirects=True)

    def fetch(self) -> tuple[list[dict[str, Any]], int | None]:
        response = self.client.get(SOURCE_URL)
        response.raise_for_status(); response.encoding = "utf-8"
        return parse_move_in_plan(response.text)


def exact_match(row: dict[str, Any], projects: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    """Return a match only if a documented exact rule produces one project."""
    region_projects = [project for project in projects if project["province"] == row.get("province")]
    normalized = row["district_block_name_normalized"]
    full = [project for project in region_projects if normalize_block_name(project["name"]) == normalized]
    if len(full) == 1:
        return full[0], "EXACT_NORMALIZED_NAME", {"region": row["province"], "move_in_name": row["district_block_name"], "project_name": full[0]["name"], "housing_type": row["housing_type"]}
    blocks = set(row["blocks"])
    row_district = district_key(row["district_block_name"])
    block_matches = [
        project for project in region_projects
        if blocks and blocks.intersection(extract_blocks(project["name"]))
        and district_key(project["name"]) == row_district
    ]
    if len(block_matches) == 1:
        candidate = block_matches[0]
        return candidate, "EXACT_BLOCK", {"region": row["province"], "block": sorted(blocks.intersection(extract_blocks(candidate["name"]))), "move_in_name": row["district_block_name"], "project_name": candidate["name"], "housing_type": row["housing_type"], "construction_units": row["construction_units"], "planned_supply_units": candidate["planned_units"]}
    reason = "NO_EXACT_MATCH" if not full and not block_matches else "AMBIGUOUS_EXACT_MATCH"
    return None, None, {"reason": reason, "region": row.get("province"), "move_in_name": row["district_block_name"], "candidate_count": len(full) or len(block_matches)}
