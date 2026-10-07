from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from apps.api.models.domain import DataStatus, LinkType, Stage


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Organization(StrictModel):
    id: str
    name: str
    organization_type: str


class Policy(StrictModel):
    id: str
    name: str
    organization_id: str
    announced_date: date
    target_units: int
    target_stage: Stage
    target_region: str
    target_date: date
    source_url: str | None
    data_status: DataStatus


class Project(StrictModel):
    id: str
    name: str
    organization_id: str
    province: str
    district: str
    address: str
    latitude: float | None
    longitude: float | None
    planned_units: int
    housing_type: str
    current_stage: Stage
    data_status: DataStatus


class PolicyProjectLink(StrictModel):
    id: str
    policy_id: str
    project_id: str
    link_type: LinkType
    evidence_url: str | None


class ProjectEvent(StrictModel):
    id: str
    project_id: str
    stage: Stage
    event_type: str
    planned_date: date | None
    actual_date: date | None
    status: str
    delay_days: int | None
    reference_date: date
    source_url: str | None
    data_status: DataStatus


class ProgressPoint(StrictModel):
    month: str
    planned: float
    actual: float


class ConstructionProgress(StrictModel):
    id: str
    project_id: str
    reference_date: date
    planned_progress_rate: float | None
    actual_progress_rate: float | None
    progress_gap: float | None
    planned_completion_date: date | None
    forecast_completion_date: date | None
    source_url: str | None
    data_status: DataStatus
    monthly_series: list[ProgressPoint] = []


class SupplyAnnouncement(StrictModel):
    id: str
    project_id: str
    supply_type: str
    supply_units: int
    target_group: str
    announcement_date: date
    application_start_date: date
    application_end_date: date
    planned_move_in_date: date
    source_url: str | None
    data_status: DataStatus


class DataSource(StrictModel):
    id: str
    organization: str
    source_name: str
    source_url: str | None
    collected_at: datetime | None
    reference_date: date | None
    collection_method: str
    validation_status: str

