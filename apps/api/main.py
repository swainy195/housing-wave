import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.api.routers.dashboard import router as dashboard_router
from apps.api.routers.resources import router as resources_router
from apps.api.routers.review import router as review_router
from apps.api.dependencies import get_repository


def cors_allowed_origins() -> list[str]:
    """Return explicit local and deployment origins without exposing secrets."""
    local_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "")
    production_origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return list(dict.fromkeys([*local_origins, *production_origins]))


app = FastAPI(
    title="주택파동 API",
    description="정책에서 입주까지 주택공급의 흐름을 연결하는 Phase 1 DEMO API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(resources_router)
app.include_router(review_router)


@app.get("/health", tags=["system"])
def health():
    repository = get_repository()
    return {
        "status": "ok",
        "service": "housing-wave-api",
        "mode": repository.metadata.get("data_mode", "DEMO"),
        "repository": repository.__class__.__name__,
        "database_mode": os.getenv("DATABASE_MODE", "json").strip().lower(),
    }


# When the Vite production bundle exists, FastAPI also serves the PoC as one app.
# API routes are registered first so the catch-all static mount cannot shadow them.
web_dist = Path(__file__).resolve().parents[1] / "web" / "dist"
if web_dist.exists():
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
