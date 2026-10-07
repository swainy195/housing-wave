from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.models.domain import STAGE_ORDER
from apps.api.services.dashboard_service import calculate_delay_days, calculate_progress_gap

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_stage_order_is_fixed():
    assert [stage.value for stage in STAGE_ORDER] == ["POLICY", "BUSINESS", "PERMIT", "CONSTRUCTION", "SUPPLY", "MOVE_IN"]


def test_policy_kpi_and_candidate_exclusion():
    pipeline = client.get("/api/dashboard/pipeline").json()
    projects = client.get("/api/projects").json()
    candidate = next(project for project in projects if project["id"] == "P016")
    business = next(item for item in pipeline if item["stage"] == "BUSINESS")
    eligible_units = sum(project["planned_units"] for project in projects if project["id"] != candidate["id"])
    assert business["units"] == eligible_units
    assert business["target_ratio"] == round(eligible_units / 100_000 * 100, 1)


def test_delay_days_calculation():
    assert calculate_delay_days("2026-01-01", "2026-01-11", "2026-09-30") == 10
    assert calculate_delay_days("2026-10-10", None, "2026-09-30") == 0
    assert calculate_delay_days(None, None, "2026-09-30") is None


def test_progress_gap_calculation_and_null_preservation():
    assert calculate_progress_gap(55, 43) == -12
    assert calculate_progress_gap(0, 0) == 0
    assert calculate_progress_gap(None, None) is None
    rows = client.get("/api/construction/progress").json()
    unavailable = next(row for row in rows if row["project_id"] == "P008")
    assert unavailable["actual_progress_rate"] is None
    assert unavailable["progress_gap"] is None
    assert unavailable["status"] == "DATA_CHECK"


def test_not_connected_data_is_retained():
    pipeline = client.get("/api/dashboard/data-coverage").json()
    sh = next(row for row in pipeline["organizations"] if row["organization"] == "SH")
    assert set(sh["stages"].values()) == {"NOT_CONNECTED"}
    projects = client.get("/api/projects?data_status=NOT_CONNECTED").json()
    assert projects
    assert all(project["data_status"] == "NOT_CONNECTED" for project in projects)


def test_zero_and_null_are_distinct():
    assert calculate_progress_gap(0, 0) == 0
    assert calculate_progress_gap(None, 0) is None


def test_upcoming_keeps_completion_and_move_in_separate():
    response = client.get("/api/upcoming?months=12")
    assert response.status_code == 200
    stages = [item["stage"] for item in response.json()["items"]]
    assert stages == ["PERMIT", "CONSTRUCTION", "SUPPLY", "COMPLETION", "MOVE_IN"]


def test_summary_reports_demo_mode_without_breaking_contract():
    summary = client.get("/api/dashboard/summary").json()
    assert summary["data_mode"] == "DEMO"
    assert {"reference_date", "policy_target_units", "linked_units", "project_count"} <= summary.keys()
