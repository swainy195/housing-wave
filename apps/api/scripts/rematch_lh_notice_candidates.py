"""Re-evaluate LH notice candidates against real Project Master using exact rules."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from apps.api.ingest.lh_move_in_plan import PROVINCE_MAP, exact_match, extract_blocks, normalize_block_name
from apps.api.repositories.postgres_repository import sqlalchemy_database_url

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env"); url = os.getenv("DATABASE_URL")
    if not url: raise SystemExit("DATABASE_URL is required")
    engine=create_engine(sqlalchemy_database_url(url))
    with engine.begin() as connection:
        projects=[dict(row) for row in connection.execute(text("SELECT id,name,province,housing_type,planned_units FROM projects WHERE organization_id='ORG-LH' AND is_demo=false")).mappings()]
        candidates=[dict(row) for row in connection.execute(text("SELECT id,pan_id,pan_name,region_name,supply_type,district_name,block_name,address_raw FROM lh_notice_candidates ORDER BY pan_id")).mappings()]
        matched=0
        for candidate in candidates:
            identity_name=" ".join(value for value in (candidate.get("district_name"),candidate.get("block_name")) if value) or candidate["pan_name"]
            row={"province":PROVINCE_MAP.get(candidate["region_name"]),"district_block_name":identity_name,"district_block_name_normalized":normalize_block_name(identity_name),"blocks":extract_blocks(identity_name),"housing_type":candidate["supply_type"],"construction_units":None}
            project,match_type,evidence=exact_match(row,projects)
            status="MATCHED" if project else "REVIEW_REQUIRED"
            connection.execute(text("""UPDATE lh_notice_candidates SET project_match_status=:status,matched_project_id=:project_id,match_type=:match_type,match_evidence=CAST(:evidence AS jsonb),review_reason=:reason,updated_at=now() WHERE id=:id"""), {"status":status,"project_id":project["id"] if project else None,"match_type":match_type,"evidence":json.dumps(evidence,ensure_ascii=False),"reason":None if project else evidence["reason"],"id":candidate["id"]})
            matched += int(project is not None)
    print(json.dumps({"candidates":len(candidates),"matched":matched,"review_required":len(candidates)-matched,"pan_project_links":matched},ensure_ascii=False))


if __name__ == "__main__": main()
