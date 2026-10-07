from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url


ENTITY_QUERIES = {
    "organizations": "SELECT id, name, organization_type, created_at, updated_at FROM organizations ORDER BY id",
    "policies": "SELECT id, name, organization_id, announced_date, target_units, target_stage, target_region, target_date, source_url, data_status, is_demo, created_at, updated_at FROM policies ORDER BY id",
    "projects": "SELECT id, name, organization_id, province, district, address, latitude, longitude, planned_units, housing_type, current_stage, data_status, is_demo, created_at, updated_at FROM projects ORDER BY id",
    "policy_project_links": "SELECT id, policy_id, project_id, link_type, evidence_url, evidence_text, verified_at, created_at FROM policy_project_links ORDER BY id",
    "project_events": "SELECT id, project_id, stage, event_type, planned_date, actual_date, status, reference_date, source_id, data_status, created_at, updated_at FROM project_events ORDER BY id",
    "supply_announcements": "SELECT id, project_id, supply_type, supply_units, target_group, announcement_date, application_start_date, application_end_date, planned_move_in_date, source_id, data_status, created_at, updated_at FROM supply_announcements ORDER BY id",
    "project_schedule_periods": "SELECT id, project_id, stage, period_text, period_year, period_month, planned_units, source_id, source_record_id, period_granularity, period_start_text, period_end_text, data_status FROM project_schedule_periods ORDER BY period_year, period_month, id",
    "project_candidates": "SELECT id, source_id, organization_id, source_kind, source_record_id, source_row_number, project_name_raw, project_name_normalized, province_raw, planned_units, construction_units, housing_type, supply_type, planned_supply_period_text, planned_move_in_period_text, move_in_period_start_text, move_in_period_end_text, match_status, matched_project_id, match_type, match_evidence, validation_status, review_reason, is_demo FROM project_candidates ORDER BY id",
    "lh_notice_candidates": "SELECT id, pan_id, pan_name, region_name, supply_type, detail_url, source_id, project_match_status, matched_project_id, match_type, match_evidence, validation_status, review_reason, is_demo FROM lh_notice_candidates ORDER BY pan_id",
    "data_sources": "SELECT ds.id, o.name AS organization, ds.organization_id, ds.source_name, ds.source_url, ds.source_type, ds.collection_method, ds.reference_date, ds.collected_at, ds.validation_status, ds.is_demo, ds.created_at FROM data_sources ds JOIN organizations o ON o.id = ds.organization_id ORDER BY ds.id",
}


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(ZoneInfo("Asia/Seoul")).isoformat()
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row_dict(row: Any) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in row._mapping.items()}


def sqlalchemy_database_url(database_url: str) -> str:
    """Use psycopg 3 for both standard and SQLAlchemy-form PostgreSQL URLs."""
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    return url.render_as_string(hide_password=False)


class PostgresRepository:
    """PostgreSQL/Supabase implementation preserving the Phase 1 repository contract."""

    def __init__(self, database_url: str, engine: Engine | None = None) -> None:
        if not database_url and engine is None:
            raise ValueError("DATABASE_URL is required when DATABASE_MODE=postgres")
        self.engine = engine or create_engine(sqlalchemy_database_url(database_url), pool_pre_ping=True)

    @property
    def metadata(self) -> dict[str, Any]:
        query = text("""
            SELECT
              COALESCE(
                (SELECT MAX(reference_date) FROM construction_progress),
                (SELECT MAX(reference_date) FROM project_events),
                CURRENT_DATE
              ) AS reference_date,
              COALESCE(
                (SELECT MAX(collected_at) FROM data_sources),
                (SELECT MAX(created_at) FROM projects),
                NOW()
              ) AS last_updated_at
        """)
        with self.engine.connect() as connection:
            row = connection.execute(query).one()
        result = _row_dict(row)
        return {**result, "dataset_name": "Housing Wave PostgreSQL", "data_mode": self.data_mode()}

    def data_mode(self) -> str:
        query = text("""
            SELECT BOOL_AND(is_demo) AS all_demo, BOOL_OR(is_demo) AS any_demo,
                   BOOL_OR(NOT is_demo) AS any_live
            FROM (
              SELECT is_demo FROM policies
              UNION ALL
              SELECT is_demo FROM projects
              UNION ALL
              SELECT is_demo FROM data_sources
            ) records
        """)
        with self.engine.connect() as connection:
            row = connection.execute(query).mappings().one()
        if row["all_demo"]:
            return "DEMO"
        if row["any_demo"] and row["any_live"]:
            return "MIXED"
        return "LIVE"

    def all(self, entity: str) -> list[dict[str, Any]]:
        if entity == "construction_progress":
            return self._construction_progress()
        if entity == "coverage":
            return self._coverage()
        query = ENTITY_QUERIES.get(entity)
        if query is None:
            raise KeyError(f"Unsupported repository entity: {entity}")
        with self.engine.connect() as connection:
            return [_row_dict(row) for row in connection.execute(text(query))]

    def get(self, entity: str, item_id: str) -> dict[str, Any] | None:
        return next((item for item in self.all(entity) if item.get("id") == item_id), None)

    def _construction_progress(self) -> list[dict[str, Any]]:
        latest_query = text("""
            SELECT id, project_id, reference_date, planned_progress_rate,
                   actual_progress_rate, progress_gap, planned_completion_date,
                   forecast_completion_date, data_status
            FROM v_latest_construction_progress ORDER BY project_id
        """)
        series_query = text("""
            SELECT project_id, reference_date, planned_progress_rate, actual_progress_rate
            FROM construction_progress
            WHERE planned_progress_rate IS NOT NULL OR actual_progress_rate IS NOT NULL
            ORDER BY project_id, reference_date
        """)
        with self.engine.connect() as connection:
            latest = [_row_dict(row) for row in connection.execute(latest_query)]
            series_rows = [_row_dict(row) for row in connection.execute(series_query)]
        series_by_project: dict[str, list[dict[str, Any]]] = {}
        for row in series_rows:
            series_by_project.setdefault(row["project_id"], []).append({
                "month": row["reference_date"][:7],
                "planned": row["planned_progress_rate"],
                "actual": row["actual_progress_rate"],
            })
        return [{**row, "source_url": None, "monthly_series": series_by_project.get(row["project_id"], [])} for row in latest]

    def _coverage(self) -> list[dict[str, Any]]:
        query = text("""
            SELECT organization, stage, data_status, note
            FROM v_data_coverage ORDER BY organization, stage_order
        """)
        with self.engine.connect() as connection:
            rows = [_row_dict(row) for row in connection.execute(query)]
        organizations: dict[str, dict[str, Any]] = {}
        for row in rows:
            target = organizations.setdefault(row["organization"], {"organization": row["organization"], "stages": {}, "note": row["note"] or ""})
            target["stages"][row["stage"]] = row["data_status"]
        return list(organizations.values())
