import json
from pathlib import Path

from apps.api.scripts.seed_demo import DEFAULT_DATA, prepare_rows


def test_seed_transformation_is_deterministic_and_preserves_null_progress():
    with Path(DEFAULT_DATA).open(encoding="utf-8") as source:
        payload = json.load(source)
    first = prepare_rows(payload)
    second = prepare_rows(payload)
    assert first == second
    assert len(first["projects"]) == 16
    assert all(project["is_demo"] is True for project in first["projects"])
    unavailable = [row for row in first["construction_progress"] if row["project_id"] == "P008"]
    assert len(unavailable) == 1
    assert unavailable[0]["planned_progress_rate"] is None
    assert unavailable[0]["actual_progress_rate"] is None


def test_seed_expands_progress_series_and_keeps_latest_reference_date():
    with Path(DEFAULT_DATA).open(encoding="utf-8") as source:
        rows = prepare_rows(json.load(source))["construction_progress"]
    project_rows = sorted((row for row in rows if row["project_id"] == "P003"), key=lambda row: row["reference_date"])
    assert len(project_rows) == 5
    assert project_rows[-1]["reference_date"] == "2026-09-30"
    assert project_rows[-1]["actual_progress_rate"] == 43

