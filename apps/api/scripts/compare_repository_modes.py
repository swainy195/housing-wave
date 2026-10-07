"""Check that seeded PostgreSQL and JSON repositories produce the same dashboard contract."""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from apps.api.repositories.postgres_repository import PostgresRepository
from apps.api.repositories.sample_repository import SampleRepository
from apps.api.services.dashboard_service import DashboardService


ROOT = Path(__file__).resolve().parents[3]


def _without_mode(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "data_mode"}


def contract_snapshot(service: DashboardService) -> dict[str, Any]:
    coverage = service.data_coverage()
    coverage["organizations"] = sorted(coverage["organizations"], key=lambda row: row["organization"])
    return {
        "summary": _without_mode(service.summary()),
        "pipeline": service.pipeline(),
        "coverage": coverage,
        "alerts": service.alerts(),
        "construction": service.construction_progress(),
        "upcoming": service.upcoming(12),
    }


def difference_paths(left: Any, right: Any, path: str = "", limit: int = 12) -> list[str]:
    if len(path) > 240:
        return [path]
    if isinstance(left, dict) and isinstance(right, dict):
        result: list[str] = []
        for key in sorted(set(left) | set(right)):
            result.extend(difference_paths(left.get(key), right.get(key), f"{path}.{key}".strip("."), limit))
            if len(result) >= limit:
                return result[:limit]
        return result
    if isinstance(left, list) and isinstance(right, list):
        result = []
        if len(left) != len(right):
            result.append(f"{path}.length")
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            result.extend(difference_paths(left_item, right_item, f"{path}[{index}]", limit))
            if len(result) >= limit:
                return result[:limit]
        return result
    return [] if left == right else [path]


def main() -> None:
    load_dotenv(ROOT / "apps" / "api" / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    json_snapshot = contract_snapshot(DashboardService(SampleRepository()))
    postgres_snapshot = contract_snapshot(DashboardService(PostgresRepository(database_url)))
    matching_sections = [name for name in json_snapshot if json_snapshot[name] == postgres_snapshot[name]]
    result = {
        "matching_sections": matching_sections,
        "mismatch_fields": {
            name: difference_paths(json_snapshot[name], postgres_snapshot[name])
            for name in json_snapshot if name not in matching_sections
        },
        "all_sections_match": len(matching_sections) == len(json_snapshot),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_sections_match"]:
        raise SystemExit("Repository contract mismatch")


if __name__ == "__main__":
    main()
