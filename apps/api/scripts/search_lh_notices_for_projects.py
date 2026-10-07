"""Retrieve LH official notice candidates from existing real Project Master rows.

Results are non-binding: a retrieval creates provenance and a REVIEW_REQUIRED
notice candidate only. It never updates matched_project_id.
"""
from __future__ import annotations
import argparse, hashlib, json, os, time
from datetime import date, datetime
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from apps.api.ingest.lh_notice_detail import LhNoticeDetailAdapter
from apps.api.ingest.lh_project_notice_search import LhProjectNoticeSearchAdapter, normalize, search_queries
from apps.api.repositories.postgres_repository import sqlalchemy_database_url

ROOT=Path(__file__).resolve().parents[3]; SOURCE_ID="DS-LH-HOUSING-NOTICE"; SYSTEM="LH_PROJECT_NOTICE_SEARCH"
REGION_CODE={"서울":"11","경기":"41","인천":"28"}
def parse_date(value: str|None):
    for fmt in ("%Y.%m.%d","%Y-%m-%d"):
        try:return datetime.strptime(value or "",fmt).date()
        except ValueError: pass
    return None
def region_ok(project: str, result: str) -> bool:
    return {"서울":"서울","경기":"경기","인천":"인천"}.get(project,project) in (result or "")
def related(project: dict[str,Any], result: dict[str,Any]) -> bool:
    name=normalize(project["name"]); candidate=normalize(result["name"])
    tokens=[x for x in __import__("re").split(r"[A-Z]+\d+(?:\d+)?", name) if len(x)>=3]
    return any(token in candidate for token in tokens)

def run(args: argparse.Namespace) -> dict[str,Any]:
    load_dotenv(ROOT/"apps/api/.env"); url=os.getenv("DATABASE_URL")
    if not url: raise SystemExit("DATABASE_URL is required")
    engine=create_engine(sqlalchemy_database_url(url),pool_pre_ping=True); search=LhProjectNoticeSearchAdapter(); detail=LhNoticeDetailAdapter()
    with engine.connect() as c:
        sql="SELECT id,name,province,housing_type,planned_units FROM projects WHERE is_demo=false AND organization_id='ORG-LH' ORDER BY id"
        if args.project_id: sql += " AND id=:project_id"
        projects=[dict(r) for r in c.execute(text(sql),{"project_id":args.project_id}).mappings()]
    if args.limit_projects: projects=projects[:args.limit_projects]
    report=[]; seen:set[str]=set(); totals={"projects":len(projects),"search_success":0,"zero_results":0,"queries":0,"rows":0,"unique_pan":0,"new_candidates":0,"existing_candidates":0,"details":0,"districts":0,"blocks":0,"addresses":0,"units":0}
    with engine.begin() as c:
      for project in projects:
        result_rows: list[tuple[str,str,dict[str,Any]]]=[]
        for query in search_queries(project):
          totals["queries"]+=1
          try: source_url, rows=search.search(query,project["province"],args.max_results_per_query)
          except Exception as exc:
            report.append({"project":project["name"],"query":query,"error":type(exc).__name__}); continue
          for rank,row in enumerate(rows,1):
            if region_ok(project["province"],row["region"]) and related(project,row): result_rows.append((query,source_url,{**row,"rank":rank}))
          time.sleep(args.request_interval)
        unique={row["pan_id"]:(query,url,row) for query,url,row in result_rows}
        totals["rows"]+=len(result_rows); totals["search_success"]+=int(bool(unique)); totals["zero_results"]+=int(not unique)
        project_summary={"project":project["name"],"queries":search_queries(project),"results":len(result_rows),"unique_notices":len(unique),"details":0}
        for pan,(query,source_url,row) in unique.items():
          if pan not in seen: seen.add(pan); totals["unique_pan"]+=1
          exists=c.execute(text("SELECT id FROM lh_notice_candidates WHERE pan_id=:pan"),{"pan":pan}).scalar_one_or_none()
          if exists: candidate_id=exists; totals["existing_candidates"]+=1
          else:
            payload=json.dumps(row,ensure_ascii=False,sort_keys=True); checksum=hashlib.sha256(payload.encode()).hexdigest(); raw_id=f"RAW-LHPS-{checksum[:20]}"
            if not args.dry_run: c.execute(text("""INSERT INTO raw_api_records (id,source_id,source_system,endpoint_name,request_key,request_params,raw_payload,response_format,fetched_at,reference_date,http_status,parse_status,checksum)
              VALUES (:id,:source_id,:system,'project_notice_search',:key,CAST(:params AS jsonb),CAST(:payload AS jsonb),'HTML_PAGE',now(),:day,200,'PARSED',:checksum) ON CONFLICT (source_id,checksum) DO UPDATE SET fetched_at=now()"""),{"id":raw_id,"source_id":SOURCE_ID,"system":SYSTEM,"key":pan,"params":json.dumps({"project_id":project["id"],"query":query,"source_url":source_url}),"payload":payload,"day":date.today(),"checksum":checksum})
            candidate_id="LHC-"+hashlib.sha256(pan.encode()).hexdigest()[:20]
            if not args.dry_run: c.execute(text("""INSERT INTO lh_notice_candidates (id,pan_id,pan_name,region_code,region_name,supply_type,notice_status,notice_start_date,closing_date,detail_url,raw_record_id,source_id,review_reason,validation_status,is_demo)
              VALUES (:id,:pan,:name,:code,:region,'OTHER',:status,:start,:end,:detail,:raw,:source,'PROJECT_DRIVEN_RETRIEVAL','REVIEW_REQUIRED',false)
              ON CONFLICT (id) DO UPDATE SET pan_name=EXCLUDED.pan_name, region_name=EXCLUDED.region_name, notice_status=EXCLUDED.notice_status, notice_start_date=EXCLUDED.notice_start_date, closing_date=EXCLUDED.closing_date, detail_url=EXCLUDED.detail_url, raw_record_id=EXCLUDED.raw_record_id, updated_at=now()"""),{"id":candidate_id,"pan":pan,"name":row["name"],"code":REGION_CODE.get(project["province"]),"region":row["region"],"status":row["status"],"start":parse_date(row["notice_date"]),"end":parse_date(row["closing_date"]),"detail":row["detail_url"],"raw":raw_id,"source":SOURCE_ID})
            totals["new_candidates"]+=1
            if not args.dry_run:
              try:
                _,meta=detail.fetch(row["detail_url"]); project_summary["details"]+=1; totals["details"]+=1
                for key,total in (("district_name","districts"),("block_name","blocks"),("address_raw","addresses")): totals[total]+=int(bool(meta.get(key)))
                totals["units"]+=int(meta.get("notice_supply_units") is not None)
                c.execute(text("""UPDATE lh_notice_candidates SET detail_fetch_status='FETCHED',detail_fetched_at=now(),district_name=:district,block_name=:block,address_raw=:address,notice_supply_units=:units,detail_metadata=CAST(:meta AS jsonb),updated_at=now() WHERE id=:id"""),{"id":candidate_id,"district":meta.get("district_name"),"block":meta.get("block_name"),"address":meta.get("address_raw"),"units":meta.get("notice_supply_units"),"meta":json.dumps(meta,ensure_ascii=False)})
              except Exception: pass
          if not args.dry_run: c.execute(text("""INSERT INTO project_notice_retrievals (id,project_id,candidate_id,search_query,search_rank,source_url)
            VALUES (:id,:project,:candidate,:query,:rank,:url) ON CONFLICT (project_id,candidate_id,search_query) DO UPDATE SET search_rank=EXCLUDED.search_rank,retrieved_at=now(),source_url=EXCLUDED.source_url"""),{"id":"PNR-"+hashlib.sha256(f"{project['id']}:{candidate_id}:{query}".encode()).hexdigest()[:20],"project":project["id"],"candidate":candidate_id,"query":query,"rank":row["rank"],"url":source_url})
        report.append(project_summary)
    report_path=ROOT/"docs/lh_project_search_report.md"
    lines=["# LH Project-driven Notice Search", "", "| Project | Queries | Results | Unique notices | Detail pages |", "|---|---:|---:|---:|---:|"]+[f"| {r['project']} | {len(r.get('queries',[]))} | {r.get('results',0)} | {r.get('unique_notices',0)} | {r.get('details',0)} |" for r in report if "project" in r]
    if not args.dry_run: report_path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return {**totals,"report":str(report_path),"dry_run":args.dry_run}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--dry-run",action="store_true");p.add_argument("--persist",action="store_true");p.add_argument("--project-id");p.add_argument("--limit-projects",type=int);p.add_argument("--max-results-per-query",type=int,default=5);p.add_argument("--request-interval",type=float,default=.4);a=p.parse_args();a.dry_run=not a.persist;print(json.dumps(run(a),ensure_ascii=False))
