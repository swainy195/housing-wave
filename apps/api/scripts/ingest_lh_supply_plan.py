"""Ingest the official LH 2026 rental supply-plan table into Project Master."""
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

from apps.api.ingest.lh_supply_plan import CAPITAL_REGION_CODES, LhSupplyPlanAdapter, PROVINCE_MAP, SOURCE_ID, SOURCE_SYSTEM, SOURCE_URL, normalized_name, parse_month
from apps.api.repositories.postgres_repository import sqlalchemy_database_url

ROOT = Path(__file__).resolve().parents[3]


def stable_id(prefix: str, value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}{hashlib.sha256(raw.encode()).hexdigest()[:20]}"


def source_record_id(row: dict[str, Any]) -> str:
    return stable_id("LHSP-", {key: row[key] for key in ("region_name", "housing_type", "housing_name", "exclusive_area", "supply_units", "planned_supply_period", "planned_move_in_period")})


def collect(max_rows: int | None = None) -> tuple[list[dict[str, Any]], dict[str, int | None]]:
    adapter = LhSupplyPlanAdapter(); records: list[dict[str, Any]] = []; totals: dict[str, int | None] = {}
    for region_name, region_code in CAPITAL_REGION_CODES.items():
        page = 1
        while True:
            rows, total = adapter.fetch(region_code, page=page)
            totals[region_name] = total
            records.extend(rows)
            if max_rows and len(records) >= max_rows: return records[:max_rows], totals
            if len(rows) < 100: break
            page += 1
    return records, totals


def persist(records: list[dict[str, Any]], database_url: str) -> dict[str, int]:
    engine = create_engine(sqlalchemy_database_url(database_url)); groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in records:
        groups.setdefault((row["region_name"], normalized_name(row["housing_name"]), row["housing_type"], row["planned_supply_period"]), []).append(row)
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO data_sources (id,organization_id,source_name,source_url,source_type,collection_method,reference_date,collected_at,validation_status,is_demo)
          VALUES (:id,'ORG-LH','LH청약플러스 2026 임대주택 공급계획',:url,'WEB','OFFICIAL_WEB_TABLE',:today,:now,'VALIDATED',false)
          ON CONFLICT (id) DO UPDATE SET collected_at=EXCLUDED.collected_at, validation_status=EXCLUDED.validation_status"""), {"id": SOURCE_ID, "url": SOURCE_URL, "today": date.today(), "now": datetime.now(timezone.utc)})
        for row in records:
            row_id = source_record_id(row); payload = json.dumps(row, ensure_ascii=False, sort_keys=True); checksum = hashlib.sha256(payload.encode()).hexdigest(); raw_id = stable_id("RAW-LHSP-", row)
            connection.execute(text("""INSERT INTO raw_api_records (id,source_id,source_system,endpoint_name,request_key,request_params,raw_payload,response_format,fetched_at,reference_date,http_status,parse_status,checksum)
              VALUES (:id,:source_id,:system,'supply_plan_web_table',:key,CAST(:params AS jsonb),CAST(:payload AS jsonb),'HTML_TABLE',now(),:today,200,'PARSED',:checksum)
              ON CONFLICT (source_id,checksum) DO UPDATE SET fetched_at=EXCLUDED.fetched_at, parse_status=EXCLUDED.parse_status"""), {"id": raw_id, "source_id": SOURCE_ID, "system": SOURCE_SYSTEM, "key": row_id, "params": json.dumps({"source_url": SOURCE_URL, "region": row["region_name"]}), "payload": payload, "today": date.today(), "checksum": checksum})
            candidate_id = stable_id("PC-LHSP-", row)
            connection.execute(text("""INSERT INTO project_candidates (id,source_id,organization_id,source_record_id,project_name_raw,project_name_normalized,province_raw,planned_units,housing_type,supply_type,planned_supply_period_text,source_stage,normalized_stage,match_status,matched_project_id,validation_status,review_reason,is_demo)
              VALUES (:id,:source_id,'ORG-LH',:record_id,:name,:normalized,:province,:units,:housing_type,'RENTAL',:period,'SUPPLY','SUPPLY','PROMOTED',NULL,'VALIDATED',NULL,false)
              ON CONFLICT (source_id,source_record_id) DO UPDATE SET planned_units=EXCLUDED.planned_units, planned_supply_period_text=EXCLUDED.planned_supply_period_text, matched_project_id=NULL, match_status='PROMOTED', validation_status='VALIDATED', updated_at=now()"""), {"id": candidate_id, "source_id": SOURCE_ID, "record_id": row_id, "name": row["housing_name"], "normalized": normalized_name(row["housing_name"]), "province": PROVINCE_MAP[row["region_name"]], "units": row["supply_units"], "housing_type": row["housing_type"], "period": row["planned_supply_period"]})
        for group_key, group_rows in groups.items():
            region_name, name, housing_type, period = group_key; project_id = stable_id("P-LHSP-", group_key); units = sum(row["supply_units"] or 0 for row in group_rows)
            connection.execute(text("""INSERT INTO projects (id,name,organization_id,province,district,address,latitude,longitude,planned_units,housing_type,current_stage,data_status,is_demo)
              VALUES (:id,:name,'ORG-LH',:province,NULL,NULL,NULL,NULL,:units,:housing_type,'SUPPLY','PARTIAL',false)
              ON CONFLICT (id) DO UPDATE SET planned_units=EXCLUDED.planned_units, data_status='PARTIAL', updated_at=now()"""), {"id": project_id, "name": group_rows[0]["housing_name"], "province": PROVINCE_MAP[region_name], "units": units, "housing_type": housing_type})
            connection.execute(text("""UPDATE project_candidates SET matched_project_id=:project_id, updated_at=now()
              WHERE source_id=:source_id AND province_raw=:province AND project_name_normalized=:name AND housing_type=:housing_type AND planned_supply_period_text=:period"""), {"project_id": project_id, "source_id": SOURCE_ID, "province": PROVINCE_MAP[region_name], "name": name, "housing_type": housing_type, "period": period})
            parsed = parse_month(period)
            if parsed:
                year, month = parsed; schedule_id = stable_id("PSP-LHSP-", (project_id, period))
                connection.execute(text("""INSERT INTO project_schedule_periods (id,project_id,stage,period_text,period_year,period_month,planned_units,source_id,data_status)
                  VALUES (:id,:project_id,'SUPPLY',:period,:year,:month,:units,:source_id,'PARTIAL')
                  ON CONFLICT (project_id,stage,period_text,source_id) DO UPDATE SET planned_units=EXCLUDED.planned_units, updated_at=now()"""), {"id": schedule_id, "project_id": project_id, "period": period, "year": year, "month": month, "units": units, "source_id": SOURCE_ID})
        connection.execute(text("""INSERT INTO organization_stage_coverage (organization_id,stage,data_status,note) VALUES ('ORG-LH','BUSINESS','PARTIAL','LH 2026 임대주택 공급계획: 서울·경기·인천 표 행 기반 Project Master'),('ORG-LH','SUPPLY','PARTIAL','공급계획만 확보: 계획량이며 실제 공급실적·공고 전체가 아님') ON CONFLICT (organization_id,stage) DO UPDATE SET data_status=EXCLUDED.data_status,note=EXCLUDED.note,updated_at=now()"""))
    return {"raw_records": len(records), "candidates": len(records), "projects": len(groups), "schedule_periods": sum(1 for key in groups if parse_month(key[3]))}


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env")
    parser = argparse.ArgumentParser(); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--max-rows", type=int)
    args = parser.parse_args(); records, totals = collect(args.max_rows)
    result: dict[str, Any] = {"dry_run": args.dry_run, "source": SOURCE_URL, "official_total_by_region": totals, "rows": len(records), "regions": {province: sum(r["region_name"] == source_region for r in records) for source_region, province in PROVINCE_MAP.items()}}
    if not args.dry_run:
        database_url = os.getenv("DATABASE_URL")
        if not database_url: raise SystemExit("DATABASE_URL is required")
        result.update(persist(records, database_url))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__": main()
