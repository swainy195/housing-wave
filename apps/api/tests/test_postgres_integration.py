import os

import pytest
from sqlalchemy import create_engine, text

from apps.api.repositories.postgres_repository import PostgresRepository, sqlalchemy_database_url
from apps.api.scripts.seed_demo import seed_demo


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.integration


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not configured")
def test_postgres_repository_and_idempotent_seed():
    assert TEST_DATABASE_URL is not None
    first = seed_demo(TEST_DATABASE_URL)
    second = seed_demo(TEST_DATABASE_URL)
    assert first == second
    repository = PostgresRepository(TEST_DATABASE_URL)
    assert len(repository.all("projects")) == 16
    assert repository.data_mode() == "DEMO"
    latest = next(row for row in repository.all("construction_progress") if row["project_id"] == "P003")
    assert latest["reference_date"] == "2026-09-30"
    assert latest["progress_gap"] == -12
    unavailable = next(row for row in repository.all("construction_progress") if row["project_id"] == "P008")
    assert unavailable["actual_progress_rate"] is None
    sh = next(row for row in repository.all("coverage") if row["organization"] == "SH")
    assert set(sh["stages"].values()) == {"NOT_CONNECTED"}

    engine = create_engine(sqlalchemy_database_url(TEST_DATABASE_URL))
    with engine.connect() as connection:
        count = connection.execute(text("SELECT COUNT(*) FROM projects WHERE is_demo")).scalar_one()
    assert count == 16
