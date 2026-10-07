"""List non-sensitive LH notice candidate metadata for official-detail research."""
import json, os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from apps.api.repositories.postgres_repository import sqlalchemy_database_url

ROOT=Path(__file__).resolve().parents[3]
load_dotenv(ROOT/'apps/api/.env')
engine=create_engine(sqlalchemy_database_url(os.environ['DATABASE_URL']))
with engine.connect() as conn:
    rows=[dict(row) for row in conn.execute(text("SELECT pan_id,pan_name,region_name,supply_type,detail_url FROM lh_notice_candidates ORDER BY pan_id")).mappings()]
print(json.dumps(rows,ensure_ascii=False))
