from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any

from apps.api.models.domain import DataStatus, LinkType, STAGE_ORDER, Stage, progress_status
from apps.api.repositories.base import Repository


STAGE_LABELS = {
    Stage.POLICY: "정책",
    Stage.BUSINESS: "사업화",
    Stage.PERMIT: "인허가",
    Stage.CONSTRUCTION: "건설",
    Stage.SUPPLY: "공급",
    Stage.MOVE_IN: "입주",
}

STATUS_WEIGHT = {
    DataStatus.AVAILABLE: 1.0,
    DataStatus.PARTIAL: 0.5,
    DataStatus.NOT_CONNECTED: 0.0,
    DataStatus.NOT_AVAILABLE: 0.0,
}


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def calculate_delay_days(planned_date: str | None, actual_date: str | None, reference_date: str) -> int | None:
    if not planned_date:
        return None
    planned = date.fromisoformat(planned_date)
    comparison = date.fromisoformat(actual_date) if actual_date else date.fromisoformat(reference_date)
    return max((comparison - planned).days, 0)


def calculate_progress_gap(planned: float | None, actual: float | None) -> float | None:
    if planned is None or actual is None:
        return None
    return round(actual - planned, 1)


class DashboardService:
    def __init__(self, repository: Repository) -> None:
        self.repo = repository
        self.metadata = self.repo.metadata
        self.reference_date = self.metadata["reference_date"]

    def _organization_map(self) -> dict[str, dict[str, Any]]:
        return {item["id"]: item for item in self.repo.all("organizations")}

    def _eligible_project_ids(self) -> set[str]:
        return {
            link["project_id"]
            for link in self.repo.all("policy_project_links")
            if link["link_type"] in {LinkType.OFFICIAL, LinkType.VERIFIED}
        }

    def _enriched_projects(self) -> list[dict[str, Any]]:
        organizations = self._organization_map()
        links_by_project = {
            link["project_id"]: link["link_type"]
            for link in self.repo.all("policy_project_links")
        }
        return [
            {
                **project,
                "organization": organizations[project["organization_id"]]["name"],
                "organization_type": organizations[project["organization_id"]]["organization_type"],
                "policy_link_type": links_by_project.get(project["id"]),
                "is_policy_metric": links_by_project.get(project["id"]) in {LinkType.OFFICIAL, LinkType.VERIFIED},
            }
            for project in self.repo.all("projects")
        ]

    def summary(self) -> dict[str, Any]:
        policies = self.repo.all("policies")
        target_units = sum(policy["target_units"] for policy in policies)
        eligible_ids = self._eligible_project_ids()
        projects = [project for project in self._enriched_projects() if project["id"] in eligible_ids]
        alerts = self.alerts()
        return {
            "is_demo": True,
            "reference_date": self.reference_date,
            "last_updated_at": self.metadata["last_updated_at"],
            "data_mode": self.metadata.get("data_mode", "DEMO"),
            "policy_target_units": target_units,
            "linked_units": sum(project["planned_units"] for project in projects),
            "project_count": len(projects),
            "delayed_project_count": len({a["project_id"] for a in alerts if a["issue_type"] in {"SCHEDULE_DELAY", "PROGRESS_DELAY"}}),
            "data_gap_project_count": len({a["project_id"] for a in alerts if a["issue_type"] == "DATA_GAP"}),
        }

    def pipeline(self) -> list[dict[str, Any]]:
        policies = self.repo.all("policies")
        target_units = sum(policy["target_units"] for policy in policies)
        eligible_ids = self._eligible_project_ids()
        projects = [project for project in self._enriched_projects() if project["id"] in eligible_ids]
        result: list[dict[str, Any]] = []
        for index, stage in enumerate(STAGE_ORDER):
            if stage == Stage.POLICY:
                rows = policies
                units = target_units
                count = len(policies)
            else:
                rows = [project for project in projects if STAGE_ORDER.index(Stage(project["current_stage"])) >= index]
                units = sum(project["planned_units"] for project in rows)
                count = len(rows)
            statuses = [DataStatus(row["data_status"]) for row in rows]
            coverage = round(sum(STATUS_WEIGHT[s] for s in statuses) / len(statuses) * 100) if statuses else 0
            aggregate = DataStatus.AVAILABLE if coverage == 100 else DataStatus.PARTIAL if coverage > 0 else (statuses[0] if statuses else DataStatus.NOT_AVAILABLE)
            result.append({
                "stage": stage,
                "label": STAGE_LABELS[stage],
                "units": units,
                "project_count": count,
                "target_ratio": round(units / target_units * 100, 1) if target_units else None,
                "data_status": aggregate,
                "coverage_rate": coverage,
                "is_reference_metric": any(policy["target_stage"] != stage for policy in policies),
            })
        return result

    def projects(self, stage: str | None = None, region: str | None = None, organization: str | None = None,
                 data_status: str | None = None, progress_state: str | None = None) -> list[dict[str, Any]]:
        progress_by_project = {item["project_id"]: item for item in self.construction_progress()}
        rows = []
        for project in self._enriched_projects():
            progress = progress_by_project.get(project["id"])
            row = {**project, "progress": progress}
            if stage and project["current_stage"] != stage:
                continue
            if region and project["province"] != region:
                continue
            if organization and project["organization"] != organization:
                continue
            if data_status and project["data_status"] != data_status:
                continue
            if progress_state and (not progress or progress["status"] != progress_state):
                continue
            rows.append(row)
        return rows

    def project_detail(self, project_id: str) -> dict[str, Any] | None:
        project = next((p for p in self._enriched_projects() if p["id"] == project_id), None)
        if not project:
            return None
        events = [self._event_with_delay(e) for e in self.repo.all("project_events") if e["project_id"] == project_id]
        progress = next((p for p in self.construction_progress() if p["project_id"] == project_id), None)
        announcements = [a for a in self.repo.all("supply_announcements") if a["project_id"] == project_id]
        schedule_periods = [item for item in self.repo.all("project_schedule_periods") if item["project_id"] == project_id]
        candidates = [item for item in self.repo.all("project_candidates") if item.get("matched_project_id") == project_id]
        notices = [item for item in self.repo.all("lh_notice_candidates") if item.get("matched_project_id") == project_id]
        source_ids = {item.get("source_id") for item in candidates + notices + schedule_periods if item.get("source_id")}
        sources = [s for s in self.repo.all("data_sources") if s["id"] in source_ids]
        if not sources:
            sources = [s for s in self.repo.all("data_sources") if s["organization"] == project["organization"]]
        return {**project, "timeline": events, "construction_progress": progress, "supply_announcements": announcements, "schedule_periods": schedule_periods, "project_master_records": candidates, "lh_notice_candidates": notices, "data_sources": sources}

    def policies(self) -> list[dict[str, Any]]:
        organizations = self._organization_map()
        return [{**p, "organization": organizations[p["organization_id"]]["name"]} for p in self.repo.all("policies")]

    def _event_with_delay(self, event: dict[str, Any]) -> dict[str, Any]:
        return {**event, "delay_days": calculate_delay_days(event.get("planned_date"), event.get("actual_date"), event.get("reference_date") or self.reference_date)}

    def construction_progress(self) -> list[dict[str, Any]]:
        projects = {project["id"]: project for project in self._enriched_projects()}
        rows = []
        for item in self.repo.all("construction_progress"):
            gap = calculate_progress_gap(item.get("planned_progress_rate"), item.get("actual_progress_rate"))
            project = projects[item["project_id"]]
            rows.append({**item, "progress_gap": gap, "status": progress_status(gap), "project_name": project["name"], "organization": project["organization"], "region": project["province"]})
        return rows

    def alerts(self) -> list[dict[str, Any]]:
        projects = {project["id"]: project for project in self._enriched_projects()}
        alerts: list[dict[str, Any]] = []
        for event in self.repo.all("project_events"):
            project = projects[event["project_id"]]
            enriched = self._event_with_delay(event)
            issue = None
            if event["status"] == "CHANGED":
                issue = "SCHEDULE_CHANGED"
            elif enriched["delay_days"] and enriched["delay_days"] > 0 and not event.get("actual_date"):
                issue = "SCHEDULE_DELAY"
            if issue:
                alerts.append(self._alert(project, issue, enriched))
        for progress in self.construction_progress():
            project = projects[progress["project_id"]]
            if progress["status"] in {"WARNING", "DELAYED"}:
                alerts.append(self._alert(project, "PROGRESS_DELAY", progress))
        for project in projects.values():
            if project["data_status"] in {DataStatus.NOT_CONNECTED, DataStatus.NOT_AVAILABLE}:
                alerts.append(self._alert(project, "DATA_GAP", {}))
        priority = {"PROGRESS_DELAY": 0, "SCHEDULE_DELAY": 1, "SCHEDULE_CHANGED": 2, "DATA_GAP": 3, "STALE_DATA": 4}
        return sorted(alerts, key=lambda item: (priority.get(item["issue_type"], 9), -(item.get("delay_days") or 0)))

    @staticmethod
    def _alert(project: dict[str, Any], issue_type: str, detail: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": f'{project["id"]}-{issue_type}-{detail.get("id", "project")}',
            "project_id": project["id"],
            "project_name": project["name"],
            "organization": project["organization"],
            "region": f'{project["province"]} {project["district"]}',
            "current_stage": project["current_stage"],
            "issue_type": issue_type,
            "planned_date": detail.get("planned_date"),
            "actual_or_forecast_date": detail.get("actual_date") or detail.get("forecast_completion_date"),
            "delay_days": detail.get("delay_days"),
            "progress_gap": detail.get("progress_gap"),
            "data_status": detail.get("data_status", project["data_status"]),
        }

    def upcoming(self, months: int) -> dict[str, Any]:
        start = date.fromisoformat(self.reference_date)
        end = add_months(start, months)
        projects = {project["id"]: project for project in self._enriched_projects()}
        buckets = {"PERMIT": [], "CONSTRUCTION": [], "SUPPLY": [], "COMPLETION": [], "MOVE_IN": []}
        type_to_stage = {"PERMIT_APPROVAL": "PERMIT", "HOUSING_CONSTRUCTION_PROJECT_APPROVAL": "PERMIT", "CONSTRUCTION_START": "CONSTRUCTION", "SUPPLY_ANNOUNCEMENT": "SUPPLY", "COMPLETION": "COMPLETION", "MOVE_IN_START": "MOVE_IN"}
        for event in self.repo.all("project_events"):
            event_date_text = event.get("actual_date") or event.get("planned_date")
            stage = type_to_stage.get(event["event_type"])
            if not event_date_text or not stage:
                continue
            event_date = date.fromisoformat(event_date_text)
            if start <= event_date <= end:
                project = projects[event["project_id"]]
                buckets[stage].append({"project_id": project["id"], "project_name": project["name"], "date": event_date_text, "units": project["planned_units"], "data_status": event["data_status"]})
        # Official supply-plan rows only specify YYYY년MM월.  Use that month for
        # the monthly dashboard; do not manufacture a day or project event.
        if isinstance(self.repo, object):
            for item in self.repo.all("project_schedule_periods"):
                month_start = date(item["period_year"], item["period_month"], 1)
                if start <= month_start <= end and item["stage"] in {"SUPPLY", "MOVE_IN"}:
                    project = projects[item["project_id"]]
                    buckets[item["stage"]].append({"project_id": project["id"], "project_name": project["name"], "date": f'{item["period_year"]:04d}-{item["period_month"]:02d}', "units": item.get("planned_units"), "data_status": item["data_status"], "period_text": item["period_text"], "event_type": f'PLANNED_{item["stage"]}'})
        return {
            "months": months,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "items": [
                {"stage": stage, "label": "준공" if stage == "COMPLETION" else STAGE_LABELS[Stage(stage)], "project_count": len(items), "units": sum(item["units"] for item in items) if items else None, "events": items, "data_status": DataStatus.PARTIAL if items else DataStatus.NOT_AVAILABLE}
                for stage, items in buckets.items()
            ],
        }

    def regions(self) -> list[dict[str, Any]]:
        result = []
        for region in ["서울", "경기", "인천"]:
            projects = [p for p in self._enriched_projects() if p["province"] == region]
            progress = [p for p in self.construction_progress() if p["region"] == region]
            region_alerts = [a for a in self.alerts() if a["region"].startswith(region)]
            result.append({
                "region": region,
                "project_count": len(projects),
                "planned_units": sum(p["planned_units"] for p in projects),
                "schedule_delay_count": len({a["project_id"] for a in region_alerts if a["issue_type"] == "SCHEDULE_DELAY"}),
                "progress_delay_count": len({p["project_id"] for p in progress if p["status"] in {"WARNING", "DELAYED"}}),
                "data_gap_count": len([p for p in projects if p["data_status"] in {"NOT_CONNECTED", "NOT_AVAILABLE"}]),
                "data_status": "NOT_CONNECTED" if region == "서울" else "PARTIAL",
                "note": "서울열린데이터광장 API 배포 후 연계 예정" if region == "서울" else ("LH/GH 샘플 구조 일부 확보" if region == "경기" else "iH 샘플 구조 일부 확보"),
            })
        return result

    def data_coverage(self) -> dict[str, Any]:
        return {"stages": [stage.value for stage in STAGE_ORDER], "organizations": self.repo.all("coverage")}
