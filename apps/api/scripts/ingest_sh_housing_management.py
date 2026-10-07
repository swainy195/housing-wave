"""Persist official SH housing-management rows as reference-master data.

Only exact complex-name plus district matches to non-demo SH projects are
recorded.  This script never promotes a management complex to a project,
creates a marker, or treats managed households as supply-plan units.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from apps.api.ingest.sh_housing_management import (
    REQUIRED_FIELDS, SERVICE_NAME, SOURCE_ID, SOURCE_URL, ShHousingManagementAdapter,
    normalize_name, nullable_integer, parse_open_date,
)
from apps.api.repositories.postgres_repository import sqlalchemy_database_url


ROOT = Path(__file__).resolve().parents[3]
SOURCE_SYSTEM = "SEOUL_OPEN_DATA_SH_HOUSING_MANAGEMENT"
REFERENCE_DATE = date(2026, 2, 20)


def stable_id(prefix: str, value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}{hashlib.sha256(raw.encode()).hexdigest()[:20]}"


def source_record_id(row: dict[str, Any]) -> str:
    return stable_id("SHHM-", {field: row.get(field) for field in REQUIRED_FIELDS})


def fetch_all(adapter: ShHousingManagementAdapter, page_size: int = 1000) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    first = adapter.fetch(1, 5)
    if first.status_code != 200 or first.result_code != "INFO-000":
        raise RuntimeError(f"SH API unsuccessful: HTTP {first.status_code}, result {first.result_code or 'missing'}")
    if first.total_count is None:
        raise RuntimeError("SH API response did not provide list_total_count")
    rows: list[dict[str, Any]] = []
    for start in range(1, first.total_count + 1, page_size):
        page = adapter.fetch(start, min(start + page_size - 1, first.total_count))
        if page.status_code != 200 or page.result_code != "INFO-000":
            raise RuntimeError(f"SH API page unsuccessful: HTTP {page.status_code}, result {page.result_code or 'missing'}")
        rows.extend(page.rows)
    return rows, dry_run_summary(first)


def dry_run_summary(result: Any) -> dict[str, Any]:
    sample = result.rows[0] if result.rows else {}
    return {
        "http_status": result.status_code,
        "result_code": result.result_code,
        "result_message": result.result_message,
        "total_count": result.total_count,
        "returned_rows": len(result.rows),
        "envelope_keys": result.envelope_keys,
        "row_fields": sorted(sample.keys()),
        "required_fields_present": {field: field in sample for field in REQUIRED_FIELDS},
        "apt_open_dt_raw_type": type(sample.get("APT_OPEN_DT")).__name__ if sample else None,
        "apt_open_dt_date_format": parse_open_date(sample.get("APT_OPEN_DT"))[1] if sample else None,
    }


def persist(rows: list[dict[str, Any]], database_url: str) -> dict[str, int]:
    engine = create_engine(sqlalchemy_database_url(database_url))
    matched = 0
    with engine.begin() as connection:
        connection.execute(text("""INSERT INTO organizations (id,name,organization_type)
            VALUES ('ORG-SH','SH','LOCAL_CORPORATION')
            ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, organization_type=EXCLUDED.organization_type"""))
        connection.execute(text("""INSERT INTO data_sources
            (id,organization_id,source_name,source_url,source_type,collection_method,reference_date,collected_at,validation_status,is_demo)
            VALUES (:id,'ORG-SH','서울주택도시개발공사 주택관리현황',:url,'API','SEOUL_OPEN_DATA_API',:reference_date,now(),'VALIDATED',false)
            ON CONFLICT (id) DO UPDATE SET collected_at=EXCLUDED.collected_at, validation_status='VALIDATED', reference_date=EXCLUDED.reference_date"""),
            {"id": SOURCE_ID, "url": SOURCE_URL, "reference_date": REFERENCE_DATE})
        # The connected source is reference-master data only.  This does not
        # claim an SH supply-plan, notice, or performance integration.
        connection.execute(text("""INSERT INTO organization_stage_coverage (organization_id,stage,data_status,note)
            VALUES ('ORG-SH','SUPPLY','PARTIAL','SH 주택관리현황 reference master 연결: 단지 관리현황만 확보했으며 공급계획·공고·실적은 미연계')
            ON CONFLICT (organization_id,stage) DO UPDATE SET data_status='PARTIAL', note=EXCLUDED.note, updated_at=now()"""))
        for row in rows:
            record_id = source_record_id(row)
            payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            checksum = hashlib.sha256(payload.encode()).hexdigest()
            raw_id = stable_id("RAW-SHHM-", row)
            connection.execute(text("""INSERT INTO raw_api_records
                (id,source_id,source_system,endpoint_name,request_key,request_params,raw_payload,response_format,fetched_at,reference_date,http_status,parse_status,checksum)
                VALUES (:id,:source_id,:system,:endpoint,:request_key,CAST(:params AS jsonb),CAST(:payload AS jsonb),'JSON',now(),:reference_date,200,'PARSED',:checksum)
                ON CONFLICT (source_id,checksum) DO UPDATE SET fetched_at=EXCLUDED.fetched_at, parse_status='PARSED'"""),
                {"id": raw_id, "source_id": SOURCE_ID, "system": SOURCE_SYSTEM, "endpoint": SERVICE_NAME,
                 "request_key": record_id, "params": json.dumps({"service": SERVICE_NAME}), "payload": payload,
                 "reference_date": REFERENCE_DATE, "checksum": checksum})
            opened, _kind = parse_open_date(row.get("APT_OPEN_DT"))
            ref_id = stable_id("HCR-SH-", {"source_id": SOURCE_ID, "source_record_id": record_id})
            connection.execute(text("""INSERT INTO housing_complex_references
                (id,source_id,raw_record_id,source_record_id,district,complex_name,complex_name_normalized,housing_type,total_households,move_in_start_date,move_in_start_raw,address_raw,postal_code,phone,validation_status,is_demo)
                VALUES (:id,:source_id,:raw_id,:record_id,:district,:name,:normalized,:housing_type,:households,:opened,:opened_raw,:address,:postal_code,:phone,'VALIDATED',false)
                ON CONFLICT (source_id,source_record_id) DO UPDATE SET raw_record_id=EXCLUDED.raw_record_id,district=EXCLUDED.district,complex_name=EXCLUDED.complex_name,complex_name_normalized=EXCLUDED.complex_name_normalized,housing_type=EXCLUDED.housing_type,total_households=EXCLUDED.total_households,move_in_start_date=EXCLUDED.move_in_start_date,move_in_start_raw=EXCLUDED.move_in_start_raw,address_raw=EXCLUDED.address_raw,postal_code=EXCLUDED.postal_code,phone=EXCLUDED.phone,validation_status='VALIDATED',updated_at=now()"""),
                {"id": ref_id, "source_id": SOURCE_ID, "raw_id": raw_id, "record_id": record_id,
                 "district": row.get("GU_NM"), "name": row.get("APT_NM") or "(단지명 미상)",
                 "normalized": normalize_name(row.get("APT_NM")), "housing_type": row.get("APT_TYPE"),
                 "households": nullable_integer(row.get("APT_CNT")), "opened": opened,
                 "opened_raw": None if row.get("APT_OPEN_DT") is None else str(row.get("APT_OPEN_DT")),
                 "address": row.get("APT_ADDR"), "postal_code": row.get("APT_ZIP"), "phone": row.get("APT_TEL")})
            projects = connection.execute(text("""SELECT id FROM projects
                WHERE organization_id='ORG-SH' AND is_demo=false AND district=:district
                  AND upper(regexp_replace(name, '\\s+', '', 'g'))=:normalized"""),
                {"district": row.get("GU_NM"), "normalized": normalize_name(row.get("APT_NM"))}).fetchall()
            for project in projects:
                connection.execute(text("""INSERT INTO project_housing_complex_references (project_id,reference_id,match_type,match_evidence)
                    VALUES (:project_id,:reference_id,'EXACT_NAME_DISTRICT',CAST(:evidence AS jsonb))
                    ON CONFLICT (project_id,reference_id) DO NOTHING"""),
                    {"project_id": project[0], "reference_id": ref_id,
                     "evidence": json.dumps({"rule": "exact normalized complex name + district", "complex_name": row.get("APT_NM"), "district": row.get("GU_NM")}, ensure_ascii=False)})
                matched += 1
    return {"raw_records": len(rows), "references": len(rows), "exact_matches": matched, "unmatched": len(rows) - matched}


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()
    adapter = ShHousingManagementAdapter()
    dry = adapter.fetch(1, 5)
    result: dict[str, Any] = {"dry_run": dry_run_summary(dry)}
    if not args.dry_run:
        if dry.status_code != 200 or dry.result_code != "INFO-000":
            raise SystemExit("SH API dry-run failed; persistence was not attempted")
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise SystemExit("DATABASE_URL is required")
        rows, _ = fetch_all(adapter, page_size=args.page_size)
        result["collection"] = {"total_rows": len(rows)}
        result["persistence"] = persist(rows, database_url)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
