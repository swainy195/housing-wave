from fastapi import APIRouter, Depends

from apps.api.dependencies import get_service
from apps.api.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(service: DashboardService = Depends(get_service)):
    return service.summary()


@router.get("/pipeline")
def pipeline(service: DashboardService = Depends(get_service)):
    return service.pipeline()


@router.get("/data-coverage")
def data_coverage(service: DashboardService = Depends(get_service)):
    return service.data_coverage()

