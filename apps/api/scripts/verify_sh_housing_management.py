"""Read-only verification for the official SH housing-management ingestion."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from apps.api.repositories.postgres_repository import sqlalchemy_database_url
from apps.api.repositories.postgres_repository import PostgresRepository
from apps.api.services.dashboard_service import DashboardService


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ID = "DS-SH-HOUSING-MANAGEMENT"


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    engine = create_engine(sqlalchemy_database_url(database_url))
    with engine.connect() as connection:
        result = connection.execute(text("""SELECT
            (SELECT COUNT(*) FROM housing_complex_references WHERE source_id=:source_id) AS references,
            (SELECT COUNT(*) FROM raw_api_records WHERE source_id=:source_id) AS raw_records,
            (SELECT COUNT(*) FROM housing_complex_references WHERE source_id=:source_id AND address_raw IS NOT NULL AND btrim(address_raw) <> '') AS addresses,
            (SELECT COUNT(*) FROM housing_complex_references WHERE source_id=:source_id AND total_households IS NOT NULL) AS households,
            (SELECT COUNT(*) FROM housing_complex_references WHERE source_id=:source_id AND move_in_start_raw IS NOT NULL AND btrim(move_in_start_raw) <> '') AS open_date_raw,
            (SELECT COUNT(*) FROM housing_complex_references WHERE source_id=:source_id AND move_in_start_date IS NOT NULL) AS open_date_parsed,
            (SELECT COUNT(*) FROM project_housing_complex_references p JOIN housing_complex_references r ON r.id=p.reference_id WHERE r.source_id=:source_id) AS exact_matches,
            (SELECT data_status FROM organization_stage_coverage WHERE organization_id='ORG-SH' AND stage='SUPPLY') AS sh_supply_coverage,
            (SELECT COUNT(*) FROM projects WHERE organization_id='ORG-LH' AND is_demo=false) AS lh_projects,
            (SELECT COALESCE(SUM(planned_units), 0) FROM projects WHERE organization_id='ORG-LH' AND is_demo=false) AS lh_units,
            (SELECT COUNT(*) FROM project_candidates WHERE organization_id='ORG-LH' AND match_status='REVIEW_REQUIRED') AS lh_review_required
        """), {"source_id": SOURCE_ID}).mappings().one()
    report = dict(result)
    report["unmatched"] = report["references"] - report["exact_matches"]
    repository = PostgresRepository(database_url)
    report["data_mode"] = repository.data_mode()
    report["seoul_dashboard_region"] = next(row for row in DashboardService(repository).regions() if row["region"] == "서울")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
