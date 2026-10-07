"""Rebuild non-binding, explainable review suggestions for LH candidates."""
from apps.api.dependencies import get_repository
from apps.api.repositories.postgres_repository import PostgresRepository
from apps.api.services.match_review_service import MatchReviewService

if __name__ == "__main__":
    repo = get_repository()
    if not isinstance(repo, PostgresRepository): raise SystemExit("DATABASE_MODE=postgres is required")
    print(MatchReviewService(repo).rebuild())
