"""Report non-sensitive integrity checks for the LH supply-plan ingestion."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from apps.api.repositories.postgres_repository import PostgresRepository, sqlalchemy_database_url
from apps.api.services.dashboard_service import DashboardService

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url: raise SystemExit("DATABASE_URL is required")
    engine = create_engine(sqlalchemy_database_url(database_url))
    query = text("""
      SELECT
        (SELECT COUNT(*) FROM raw_api_records WHERE source_id='DS-LH-2026-RENTAL-PLAN') AS raw_records,
        (SELECT COUNT(*) FROM project_candidates WHERE source_id='DS-LH-2026-RENTAL-PLAN') AS candidates,
        (SELECT COUNT(*) FROM project_candidates WHERE source_id='DS-LH-2026-RENTAL-PLAN' AND matched_project_id IS NOT NULL) AS promoted_candidates,
        (SELECT COUNT(*) FROM projects WHERE is_demo=false) AS live_projects,
        (SELECT COUNT(*) FROM projects WHERE is_demo=false AND (latitude IS NOT NULL OR longitude IS NOT NULL)) AS live_projects_with_coordinates,
        (SELECT COUNT(*) FROM policy_project_links ppl JOIN projects p ON p.id=ppl.project_id WHERE p.is_demo=false) AS live_policy_links
    """)
    distribution_query = text("SELECT province, COUNT(*) AS projects, SUM(planned_units) AS planned_supply_units FROM projects WHERE is_demo=false GROUP BY province ORDER BY province")
    move_in_query = text("""SELECT p.name AS project, psp.period_text, psp.planned_units AS construction_units, pc.match_type
      FROM project_schedule_periods psp JOIN projects p ON p.id=psp.project_id
      LEFT JOIN project_candidates pc ON pc.matched_project_id=p.id AND pc.source_id='DS-LH-MOVE-IN-PLAN'
      WHERE psp.stage='MOVE_IN' AND psp.source_id='DS-LH-MOVE-IN-PLAN' ORDER BY p.name""")
    notice_query = text("SELECT COUNT(*) FILTER (WHERE project_match_status='MATCHED') AS matched, COUNT(*) FILTER (WHERE project_match_status='REVIEW_REQUIRED') AS review_required FROM lh_notice_candidates")
    with engine.connect() as connection:
        counts = dict(connection.execute(query).mappings().one())
        distribution = [dict(row) for row in connection.execute(distribution_query).mappings()]
        move_in_matches = [dict(row) for row in connection.execute(move_in_query).mappings()]
        notice_matches = dict(connection.execute(notice_query).mappings().one())
    repository = PostgresRepository(database_url)
    service = DashboardService(repository); upcoming = service.upcoming(3)["items"]
    real_project = next(project for project in service.projects(organization="LH") if not project["is_demo"])
    provenance = service.project_detail(real_project["id"])["data_sources"]
    print(json.dumps({**counts, "distribution": distribution, "move_in_matches": move_in_matches, "notice_matches": notice_matches, "data_mode": repository.data_mode(), "coverage": repository.all("coverage"), "upcoming_3m": upcoming, "project_drawer_provenance": {"project_id": real_project["id"], "has_lh_plan_source": any(source["id"] == "DS-LH-2026-RENTAL-PLAN" for source in provenance)}}, ensure_ascii=False))


if __name__ == "__main__": main()
