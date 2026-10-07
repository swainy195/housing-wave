"""Project-driven retrieval from the official LH notice-list form."""
from __future__ import annotations
import re
from html.parser import HTMLParser
from urllib.parse import urlencode
from typing import Any
import httpx
from apps.api.ingest.lh_move_in_plan import extract_blocks

LIST_URL = "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do"
REGION_CODE = {"서울": "11", "경기": "41", "인천": "28"}

def clean(value: str) -> str: return " ".join(value.replace("\xa0", " ").split())
def normalize(value: str | None) -> str: return re.sub(r"[^0-9A-Z가-힣]", "", (value or "").upper().replace("블록", "BL"))

def search_queries(project: dict[str, Any]) -> list[str]:
    name = clean(project["name"])
    base = re.sub(r"\s+[A-Z]+[- ]?\d+(?:[- ]?\d+)?(?:BL|블록)?\b", "", name, flags=re.I).strip()
    values = [name, base]
    blocks = extract_blocks(name)
    if base and blocks: values.append(f"{base} {blocks[0]}BL")
    # Housing type alone is intentionally never a query.
    if base and project.get("housing_type"): values.append(f"{base} {project['housing_type']}")
    unique: list[str] = []
    for value in values:
        value = clean(value)
        if len(normalize(value)) >= 3 and value not in unique: unique.append(value)
    return unique[:4]

class _Rows(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.rows: list[dict[str, Any]]=[]; self.row: list[str]|None=None; self.cell: list[str]|None=None; self.attrs: dict[str,str]={}
    def handle_starttag(self, tag: str, attrs: list[tuple[str,str|None]]) -> None:
        if tag == "tr": self.row=[]; self.attrs={}
        elif self.row is not None and tag == "td": self.cell=[]
        elif self.row is not None and tag in {"a","button"}:
            d={k:v or "" for k,v in attrs}
            if "wrtancInfoBtn" in d.get("class", ""):
                self.attrs={"pan_id":d.get("data-id1",""),"ccr":d.get("data-id2",""),"upp":d.get("data-id3",""),"ais":d.get("data-id4","")}
    def handle_data(self,data:str)->None:
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag:str)->None:
        if tag=="td" and self.cell is not None and self.row is not None:self.row.append(clean("".join(self.cell)));self.cell=None
        elif tag=="tr" and self.row is not None:
            if self.attrs.get("pan_id") and len(self.row)>=5:
                self.rows.append({**self.attrs,"cells":self.row})
            self.row=None

def parse_results(html: str) -> list[dict[str, Any]]:
    parser=_Rows(); parser.feed(html); out=[]
    for row in parser.rows:
        cells=row["cells"]
        # Official list columns: no, type, name, region, attachment, notice date, close date, status.
        if len(cells)<4: continue
        pan=row["pan_id"]
        if not pan: continue
        params={"panId":pan,"ccrCnntSysDsCd":row["ccr"],"uppAisTpCd":row["upp"],"aisTpCd":row["ais"],"mi":"1026"}
        out.append({"pan_id":pan,"name":cells[2],"region":cells[3],"notice_date":cells[5] if len(cells)>5 else None,"closing_date":cells[6] if len(cells)>6 else None,"status":cells[7] if len(cells)>7 else None,"detail_url":"https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancInfo.do?"+urlencode(params),"raw":row})
    return out

class LhProjectNoticeSearchAdapter:
    def __init__(self, client: httpx.Client|None=None) -> None: self.client=client or httpx.Client(timeout=30,follow_redirects=True)
    def search(self, query: str, province: str, max_results: int=10) -> tuple[str,list[dict[str,Any]]]:
        params={"mi":"1026","viewType":"srch","panNm":query,"cnpCd":REGION_CODE.get(province,""),"panSs":"","startDt":"2020-01-01","endDt":"2026-10-06","listCo":str(min(max_results,10))}
        response=self.client.get(LIST_URL,params=params);response.raise_for_status();response.encoding="utf-8"
        return str(response.url),parse_results(response.text)[:max_results]
