import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from apps.api.repositories.base import Repository
from apps.api.repositories.postgres_repository import PostgresRepository
from apps.api.repositories.sample_repository import SampleRepository
from apps.api.services.dashboard_service import DashboardService

load_dotenv(Path(__file__).resolve().parent / ".env")


@lru_cache
def get_repository() -> Repository:
    mode = os.getenv("DATABASE_MODE", "json").strip().lower()
    if mode == "json":
        return SampleRepository()
    if mode == "postgres":
        return PostgresRepository(os.getenv("DATABASE_URL", ""))
    raise ValueError("DATABASE_MODE must be either 'json' or 'postgres'")


def get_service() -> DashboardService:
    return DashboardService(get_repository())
