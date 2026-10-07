"""Persist official LH move-in-plan rows and exact matches only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from apps.api.ingest.lh_move_in_plan import LhMoveInPlanAdapter, SOURCE_ID, SOURCE_SYSTEM, SOURCE_URL, exact_match, parse_month
from apps.api.scripts.ingest_lh_supply_plan import stable_id
from apps.api.repositories.postgres_repository import sqlalchemy_database_url

ROOT = Path(__file__).resolve().parents[3]


def source_record_id(row: dict[str, Any]) -> str:
    return stable_id("LHMP-", {key: row[key] for key in ("region_name", "housing_type", "district_block_name", "construction_units", "planned_move_in_period", "move_in_designation_period")})


def persist(rows: list[dict[str, Any]], database_url: str) -> dict[str, int]:
    engine = create_engine(sqlalchemy_database_url(database_url))
    with engine.begin() as connection:
        projects = [dict(row) for row in connection.execute(text("SELECT id,name,province,housing_type,planned_units FROM projects WHERE organization_id='ORG-LH' AND is_demo=false")).mappings()]
        # Rebuild only this source's derived monthly links.  RAW checksums retain
        # previous source versions while the current candidate stays idempotent.
        connection.execute(text("DELETE FROM project_schedule_periods WHERE source_id=:source_id"), {"source_id": SOURCE_ID})
        connection.execute(text("""INSERT INTO data_sources (id,organization_id,source_name,source_url,source_type,collection_method,reference_date,collected_at,validation_status,is_demo)
          VALUES (:id,'ORG-LH','LH청약플러스 입주계획',:url,'WEB','OFFICIAL_WEB_TABLE',:today,:now,'VALIDATED',false)
          ON CONFLICT (id) DO UPDATE SET collected_at=EXCLUDED.collected_at,validation_status=EXCLUDED.validation_status"""), {"id": SOURCE_ID, "url": SOURCE_URL, "today": date.today(), "now": datetime.now(timezone.utc)})
        matched = 0; periods = 0
        for row in rows:
            record_id = source_record_id(row); payload = json.dumps(row, ensure_ascii=False, sort_keys=True); checksum = hashlib.sha256(payload.encode()).hexdigest(); raw_id = stable_id("RAW-LHMP-", row)
            project, match_type, evidence = exact_match(row, projects)
            status = "MATCHED" if project else "REVIEW_REQUIRED"; validation = "VALIDATED" if project else "REVIEW_REQUIRED"
            connection.execute(text("""INSERT INTO raw_api_records (id,source_id,source_system,endpoint_name,request_key,request_params,raw_payload,response_format,fetched_at,reference_date,http_status,parse_status,checksum)
              VALUES (:id,:source_id,:system,'move_in_plan_web_table',:record_id,CAST(:params AS jsonb),CAST(:payload AS jsonb),'HTML_TABLE',now(),:today,200,'PARSED',:checksum)
              ON CONFLICT (source_id,checksum) DO UPDATE SET fetched_at=EXCLUDED.fetched_at,parse_status='PARSED'"""), {"id":raw_id,"source_id":SOURCE_ID,"system":SOURCE_SYSTEM,"record_id":record_id,"params":json.dumps({"source_url":SOURCE_URL,"source_row_number":row["source_row_number"]}),"payload":payload,"today":date.today(),"checksum":checksum})
            candidate_id = stable_id("PC-LHMP-", row)
            connection.execute(text("""INSERT INTO project_candidates (id,source_id,organization_id,source_kind,source_record_id,source_row_number,project_name_raw,project_name_normalized,province_raw,planned_units,construction_units,housing_type,supply_type,planned_move_in_period_text,move_in_period_start_text,move_in_period_end_text,source_stage,normalized_stage,match_status,matched_project_id,match_type,match_evidence,validation_status,review_reason,is_demo)
              VALUES (:id,:source_id,'ORG-LH','MOVE_IN_PLAN',:record_id,:row_number,:name,:normalized,:province,NULL,:construction_units,:housing_type,'MOVE_IN',:move_in_period,:designation,NULL,'MOVE_IN','MOVE_IN',:status,:project_id,:match_type,CAST(:evidence AS jsonb),:validation,:reason,false)
              ON CONFLICT (source_id,source_record_id) DO UPDATE SET construction_units=EXCLUDED.construction_units,planned_move_in_period_text=EXCLUDED.planned_move_in_period_text,move_in_period_start_text=EXCLUDED.move_in_period_start_text,match_status=EXCLUDED.match_status,matched_project_id=EXCLUDED.matched_project_id,match_type=EXCLUDED.match_type,match_evidence=EXCLUDED.match_evidence,validation_status=EXCLUDED.validation_status,review_reason=EXCLUDED.review_reason,updated_at=now()"""), {"id":candidate_id,"source_id":SOURCE_ID,"record_id":record_id,"row_number":row["source_row_number"],"name":row["district_block_name"],"normalized":row["district_block_name_normalized"],"province":row["province"],"construction_units":row["construction_units"],"housing_type":row["housing_type"],"move_in_period":row["planned_move_in_period"],"designation":row["move_in_designation_period"],"status":status,"project_id":project["id"] if project else None,"match_type":match_type,"evidence":json.dumps(evidence,ensure_ascii=False),"validation":validation,"reason":None if project else evidence["reason"]})
            if project:
                matched += 1; month = parse_month(row["planned_move_in_period"])
                if month:
                    year, month_number = month; period_id = stable_id("PSP-LHMP-", (project["id"], row["planned_move_in_period"], record_id))
                    connection.execute(text("""INSERT INTO project_schedule_periods (id,project_id,stage,period_text,period_year,period_month,planned_units,source_id,source_record_id,period_granularity,period_start_text,period_end_text,data_status)
                      VALUES (:id,:project_id,'MOVE_IN',:period,:year,:month,:units,:source_id,:record_id,'MONTH',:period_start,NULL,'PARTIAL')
                      ON CONFLICT (project_id,stage,period_text,source_id) DO UPDATE SET planned_units=EXCLUDED.planned_units,source_record_id=EXCLUDED.source_record_id,period_start_text=EXCLUDED.period_start_text,updated_at=now()"""), {"id":period_id,"project_id":project["id"],"period":row["planned_move_in_period"],"year":year,"month":month_number,"units":row["construction_units"],"source_id":SOURCE_ID,"record_id":record_id,"period_start":row["move_in_designation_period"]}); periods += 1
        connection.execute(text("""INSERT INTO organization_stage_coverage (organization_id,stage,data_status,note) VALUES ('ORG-LH','MOVE_IN','PARTIAL','LH청약플러스 입주계획 표를 수집했으며, 강한 규칙으로 매칭된 사업만 월 단위 일정 반영') ON CONFLICT (organization_id,stage) DO UPDATE SET data_status=EXCLUDED.data_status,note=EXCLUDED.note,updated_at=now()"""))
    return {"raw_records":len(rows),"candidates":len(rows),"matched":matched,"review_required":len(rows)-matched,"move_in_periods":periods}


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env"); parser = argparse.ArgumentParser(); parser.add_argument("--dry-run",action="store_true"); args=parser.parse_args()
    rows,total=LhMoveInPlanAdapter().fetch(); summary:dict[str,Any]={"dry_run":args.dry_run,"source":SOURCE_URL,"total_rows":total,"rows":len(rows),"capital_rows":sum(row["province"] is not None for row in rows),"regions":{province:sum(row["province"]==province for row in rows) for province in ("서울","경기","인천")}}
    if not args.dry_run:
        url=os.getenv("DATABASE_URL")
        if not url: raise SystemExit("DATABASE_URL is required")
        summary.update(persist(rows,url))
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == "__main__": main()
