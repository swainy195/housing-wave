from .base import Repository
from .postgres_repository import PostgresRepository
from .sample_repository import SampleRepository

JsonRepository = SampleRepository

__all__ = ["Repository", "PostgresRepository", "SampleRepository", "JsonRepository"]
