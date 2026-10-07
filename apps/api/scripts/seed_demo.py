import argparse
import json
import os
from calendar import monthrange
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import Connection, create_engine, text

from apps.api.repositories.postgres_repository import sqlalchemy_database_url


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA = ROOT / "data" / "sample" / "housing_wave.json"


def _upsert(connection: Connection, table: str, rows: list[dict[str, Any]], conflict: list[str], update: list[str]) -> None:
    if not rows:
        return
    columns = list(rows[0])
    values = ", ".join(f":{column}" for column in columns)
    conflict_sql = ", ".join(conflict)
    update_sql = ", ".join(f"{column} = EXCLUDED.{column}" for column in update)
    statement = text(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({values}) ON CONFLICT ({conflict_sql}) DO UPDATE SET {update_sql}")
    connection.execute(statement, rows)


def prepare_rows(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    organizations = [dict(row) for row in data["organizations"]]
    existing_names = {row["name"] for row in organizations}
    if "국토교통부" not in existing_names:
        organizations.append({"id": "ORG-MOLIT", "name": "국토교통부", "organization_type": "CENTRAL_GOVERNMENT"})
    if "서울특별시" not in existing_names:
        organizations.append({"id": "ORG-SEOUL", "name": "서울특별시", "organization_type": "LOCAL_GOVERNMENT"})

    projects = [{**row, "is_demo": True} for row in data["projects"]]
    policies = [{**row, "is_demo": True} for row in data["policies"]]
    links = [{**row, "evidence_text": "Phase 1 DEMO 연결", "verified_at": None} for row in data["policy_project_links"]]
    project_org = {row["id"]: row["organization_id"] for row in projects}
    org_by_name = {row["name"]: row["id"] for row in organizations}

    sources = []
    source_by_org: dict[str, str] = {}
    for row in data["data_sources"]:
        organization_id = org_by_name[row["organization"]]
        source_by_org[organization_id] = row["id"]
        sources.append({
            "id": row["id"], "organization_id": organization_id, "source_name": row["source_name"],
            "source_url": row.get("source_url"), "source_type": "DEMO", "collection_method": row["collection_method"],
            "reference_date": row.get("reference_date"), "collected_at": row.get("collected_at"),
            "validation_status": row["validation_status"], "is_demo": True,
        })

    events = []
    for row in data["project_events"]:
        events.append({
            "id": row["id"], "project_id": row["project_id"], "stage": row["stage"], "event_type": row["event_type"],
            "planned_date": row.get("planned_date"), "actual_date": row.get("actual_date"), "status": row["status"],
            "reference_date": row["reference_date"], "source_id": source_by_org.get(project_org[row["project_id"]]),
            "data_status": row["data_status"],
        })

    progress_rows = []
    for row in data["construction_progress"]:
        points = {point["month"]: point for point in row.get("monthly_series", [])}
        reference_month = row["reference_date"][:7]
        if reference_month not in points:
            points[reference_month] = {"month": reference_month, "planned": row.get("planned_progress_rate"), "actual": row.get("actual_progress_rate")}
        for month, point in sorted(points.items()):
            year, month_number = (int(value) for value in month.split("-"))
            reference_date = f"{month}-{monthrange(year, month_number)[1]:02d}"
            is_latest = month == reference_month
            progress_rows.append({
                "id": row["id"] if is_latest else f'{row["id"]}-{month.replace("-", "")}',
                "project_id": row["project_id"], "reference_date": row["reference_date"] if is_latest else reference_date,
                "planned_progress_rate": point.get("planned"), "actual_progress_rate": point.get("actual"),
                "planned_completion_date": row.get("planned_completion_date"),
                "forecast_completion_date": row.get("forecast_completion_date") if is_latest else None,
                "source_id": source_by_org.get(project_org[row["project_id"]]), "data_status": row["data_status"],
            })

    announcements = []
    for row in data["supply_announcements"]:
        announcements.append({
            "id": row["id"], "project_id": row["project_id"], "supply_type": row["supply_type"],
            "supply_units": row["supply_units"], "target_group": row["target_group"], "announcement_date": row["announcement_date"],
            "application_start_date": row["application_start_date"], "application_end_date": row["application_end_date"],
            "planned_move_in_date": row["planned_move_in_date"], "source_id": source_by_org.get(project_org[row["project_id"]]),
            "data_status": row["data_status"],
        })

    coverage = []
    for row in data["coverage"]:
        for stage, status in row["stages"].items():
            coverage.append({"organization_id": org_by_name[row["organization"]], "stage": stage, "data_status": status, "note": row.get("note")})

    return {
        "organizations": organizations, "policies": policies, "projects": projects, "data_sources": sources,
        "policy_project_links": links, "project_events": events, "construction_progress": progress_rows,
        "supply_announcements": announcements, "organization_stage_coverage": coverage,
    }


def seed_demo(database_url: str, data_path: Path = DEFAULT_DATA) -> dict[str, int]:
    with data_path.open(encoding="utf-8") as source:
        rows = prepare_rows(json.load(source))
    engine = create_engine(sqlalchemy_database_url(database_url), pool_pre_ping=True)
    with engine.begin() as connection:
        _upsert(connection, "organizations", rows["organizations"], ["id"], ["name", "organization_type"])
        _upsert(connection, "policies", rows["policies"], ["id"], ["name", "organization_id", "announced_date", "target_units", "target_stage", "target_region", "target_date", "source_url", "data_status", "is_demo"])
        _upsert(connection, "projects", rows["projects"], ["id"], ["name", "organization_id", "province", "district", "address", "latitude", "longitude", "planned_units", "housing_type", "current_stage", "data_status", "is_demo"])
        _upsert(connection, "data_sources", rows["data_sources"], ["id"], ["organization_id", "source_name", "source_url", "source_type", "collection_method", "reference_date", "collected_at", "validation_status", "is_demo"])
        _upsert(connection, "policy_project_links", rows["policy_project_links"], ["id"], ["policy_id", "project_id", "link_type", "evidence_url", "evidence_text", "verified_at"])
        _upsert(connection, "project_events", rows["project_events"], ["id"], ["project_id", "stage", "event_type", "planned_date", "actual_date", "status", "reference_date", "source_id", "data_status"])
        _upsert(connection, "construction_progress", rows["construction_progress"], ["id"], ["project_id", "reference_date", "planned_progress_rate", "actual_progress_rate", "planned_completion_date", "forecast_completion_date", "source_id", "data_status"])
        _upsert(connection, "supply_announcements", rows["supply_announcements"], ["id"], ["project_id", "supply_type", "supply_units", "target_group", "announcement_date", "application_start_date", "application_end_date", "planned_move_in_date", "source_id", "data_status"])
        _upsert(connection, "organization_stage_coverage", rows["organization_stage_coverage"], ["organization_id", "stage"], ["data_status", "note", "updated_at"])
    return {entity: len(values) for entity, values in rows.items()}


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env")
    parser = argparse.ArgumentParser(description="Idempotently seed Housing Wave DEMO data into PostgreSQL")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--dry-run", action="store_true", help="Validate and summarize transformed rows without connecting")
    args = parser.parse_args()
    with args.data.open(encoding="utf-8") as source:
        prepared = prepare_rows(json.load(source))
    if args.dry_run:
        print(json.dumps({entity: len(rows) for entity, rows in prepared.items()}, ensure_ascii=False, indent=2))
        return
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required (or use --dry-run)")
    print(json.dumps(seed_demo(args.database_url, args.data), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
