"""Official LH notice detail collector; it records only fields visibly present."""
from __future__ import annotations
import re
from html.parser import HTMLParser
from typing import Any
import httpx

LABELS = {"사업지구": "district_name", "지구명": "district_name", "블록": "block_name", "주소": "address_raw", "소재지": "address_raw", "공급호수": "notice_supply_units", "모집호수": "notice_supply_units", "입주예정": "planned_move_in"}

class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.text: list[str]=[]; self.inputs: dict[str,str]={}; self.links: list[str]=[]
    def handle_data(self,data:str)->None:
        value=" ".join(data.split())
        if value:self.text.append(value)
    def handle_starttag(self,tag:str,attrs:list[tuple[str,str|None]])->None:
        attr=dict(attrs)
        if tag=="input" and attr.get("name") and attr.get("value"):
            self.inputs[attr["name"]]=attr["value"]
        if tag=="a" and attr.get("href"):
            self.links.append(attr["href"])

def clean(value:str)->str:return " ".join(value.split())

def parse_detail(html:str)->dict[str,Any]:
    parser=_TextParser();parser.feed(html); text="\n".join(parser.text)
    fields:dict[str,Any]={"official_identifiers":{key:value for key,value in parser.inputs.items() if key.upper() in {"PAN_ID","AIS_TP_CD","SPL_INF_ID","LCC_ID","UPP_AIS_TP_CD"}},"attachment_links":[link for link in parser.links if any(ext in link.lower() for ext in (".pdf",".hwp",".xls","download"))]}
    for label,key in LABELS.items():
        match=re.search(rf"{re.escape(label)}\s*[:：]?\s*([^\n]{{1,160}})",text)
        if not match: continue
        value=clean(match.group(1))
        if key=="notice_supply_units":
            number=re.search(r"([\d,]+)",value); fields[key]=int(number.group(1).replace(",","")) if number else None
        else: fields[key]=value
    fields["page_text_excerpt"]=text[:12000]
    return fields

class LhNoticeDetailAdapter:
    def __init__(self,client:httpx.Client|None=None)->None:self.client=client or httpx.Client(timeout=30.0,follow_redirects=True)
    def fetch(self,url:str)->tuple[str,dict[str,Any]]:
        response=self.client.get(url);response.raise_for_status();response.encoding="utf-8"
        return response.text,parse_detail(response.text)
