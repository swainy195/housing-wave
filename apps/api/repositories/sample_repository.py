import json
from pathlib import Path
from typing import Any

from apps.api.schemas.domain import (
    ConstructionProgress,
    DataSource,
    Organization,
    Policy,
    PolicyProjectLink,
    Project,
    ProjectEvent,
    SupplyAnnouncement,
)


ENTITY_SCHEMAS = {
    "organizations": Organization,
    "policies": Policy,
    "projects": Project,
    "policy_project_links": PolicyProjectLink,
    "project_events": ProjectEvent,
    "construction_progress": ConstructionProgress,
    "supply_announcements": SupplyAnnouncement,
    "data_sources": DataSource,
}


class SampleRepository:
    """JSON-backed repository that can later be replaced by PostgreSQL/Supabase."""

    def __init__(self, data_path: Path | None = None) -> None:
        default_path = Path(__file__).resolve().parents[3] / "data" / "sample" / "housing_wave.json"
        self.data_path = data_path or default_path
        with self.data_path.open(encoding="utf-8") as source:
            self._data: dict[str, Any] = json.load(source)
        # Fail fast when sample/source data no longer matches the documented domain model.
        for entity, schema in ENTITY_SCHEMAS.items():
            self._data[entity] = [
                schema.model_validate(item).model_dump(mode="json")
                for item in self._data.get(entity, [])
            ]

    @property
    def metadata(self) -> dict[str, Any]:
        return {**self._data["metadata"], "data_mode": "DEMO"}

    def all(self, entity: str) -> list[dict[str, Any]]:
        rows = list(self._data.get(entity, []))
        if entity in {"policies", "projects", "data_sources"}:
            return [{**row, "is_demo": True} for row in rows]
        return rows

    def get(self, entity: str, item_id: str) -> dict[str, Any] | None:
        return next((item for item in self.all(entity) if item.get("id") == item_id), None)
