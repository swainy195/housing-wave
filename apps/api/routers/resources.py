from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.dependencies import get_service
from apps.api.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api", tags=["resources"])


@router.get("/projects")
def projects(
    service: Annotated[DashboardService, Depends(get_service)],
    stage: str | None = None,
    region: str | None = None,
    organization: str | None = None,
    data_status: str | None = None,
    progress_status: str | None = None,
):
    return service.projects(stage, region, organization, data_status, progress_status)


@router.get("/projects/{project_id}")
def project_detail(project_id: str, service: Annotated[DashboardService, Depends(get_service)]):
    project = service.project_detail(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/policies")
def policies(service: Annotated[DashboardService, Depends(get_service)]):
    return service.policies()


@router.get("/construction/progress")
def construction_progress(service: Annotated[DashboardService, Depends(get_service)]):
    return service.construction_progress()


@router.get("/alerts")
def alerts(service: Annotated[DashboardService, Depends(get_service)]):
    return service.alerts()


@router.get("/upcoming")
def upcoming(months: Annotated[int, Query(ge=1, le=12)] = 3, service: DashboardService = Depends(get_service)):
    return service.upcoming(months)


@router.get("/regions")
def regions(service: Annotated[DashboardService, Depends(get_service)]):
    return service.regions()

