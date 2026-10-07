"""Apply and inspect the Housing Wave PostgreSQL/PostGIS schema without logging secrets."""

import argparse
import json
import os
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MIGRATION = ROOT / "supabase" / "migrations" / "001_initial_schema.sql"
EXPECTED_TABLES = (
    "organizations", "policies", "projects", "policy_project_links", "data_sources",
    "project_events", "construction_progress", "supply_announcements", "data_status_history",
    "organization_stage_coverage", "raw_api_records", "external_identifiers", "project_candidates", "project_schedule_periods",
    "housing_complex_references", "project_housing_complex_references",
)
EXPECTED_VIEWS = (
    "v_latest_construction_progress", "v_project_current_status", "v_policy_progress",
    "v_data_coverage", "v_upcoming_events",
)


def _conninfo(database_url: str) -> str:
    url = make_url(database_url)
    if not url.host:
        raise ValueError("DATABASE_URL must include a database host")
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


def apply_migration(database_url: str, migration_path: Path = DEFAULT_MIGRATION) -> None:
    sql = migration_path.read_text(encoding="utf-8")
    # The migration owns BEGIN/COMMIT, so use autocommit and avoid prepared multi-statement execution.
    with psycopg.connect(_conninfo(database_url), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, prepare=False)


def inspect_database(database_url: str) -> dict[str, Any]:
    with psycopg.connect(_conninfo(database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            postgis = cursor.fetchone()
            cursor.execute("SELECT to_regclass(%s)", ("public.projects",))
            projects_table = cursor.fetchone()[0]
            cursor.execute(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'projects' AND column_name = 'location'"
            )
            location_type = cursor.fetchone()
            cursor.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' "
                "AND tablename = 'projects' AND indexname = 'idx_projects_location'"
            )
            spatial_index = cursor.fetchone()
            project_triggers: list[str] = []
            if projects_table:
                cursor.execute(
                    "SELECT tgname FROM pg_trigger WHERE tgrelid = 'public.projects'::regclass "
                    "AND NOT tgisinternal ORDER BY tgname"
                )
                project_triggers = [row[0] for row in cursor.fetchall()]
            cursor.execute(
                "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace "
                "AND relkind = 'r' ORDER BY relname"
            )
            found_tables = {row[0] for row in cursor.fetchall()}
            cursor.execute(
                "SELECT table_name FROM information_schema.views WHERE table_schema = 'public'"
            )
            found_views = {row[0] for row in cursor.fetchall()}
            counts: dict[str, int] = {}
            for table in ("organizations", "policies", "projects", "construction_progress", "raw_api_records", "external_identifiers", "project_candidates", "project_schedule_periods", "housing_complex_references", "project_housing_complex_references"):
                if table in found_tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]

    return {
        "postgis_version": postgis[0] if postgis else None,
        "projects_table": projects_table,
        "projects_location_type": location_type[0] if location_type else None,
        "projects_spatial_index": spatial_index[0] if spatial_index else None,
        "projects_triggers": project_triggers,
        "missing_tables": sorted(set(EXPECTED_TABLES) - found_tables),
        "missing_views": sorted(set(EXPECTED_VIEWS) - found_views),
        "row_counts": counts,
    }


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env")
    parser = argparse.ArgumentParser(description="Apply or inspect the Housing Wave PostgreSQL migration")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--migration", type=Path, default=DEFAULT_MIGRATION)
    parser.add_argument("--apply", action="store_true", help="Apply the migration before inspection")
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required")
    if args.apply:
        if args.migration == DEFAULT_MIGRATION:
            for migration in sorted(DEFAULT_MIGRATION.parent.glob("*.sql")):
                apply_migration(args.database_url, migration)
        else:
            apply_migration(args.database_url, args.migration)
    print(json.dumps(inspect_database(args.database_url), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
