from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from apps.api.dependencies import get_repository
from apps.api.repositories.postgres_repository import PostgresRepository
from apps.api.services.match_review_service import MatchReviewService

router = APIRouter(prefix="/api/review", tags=["match review"])
def service(repo=Depends(get_repository)) -> MatchReviewService:
    if not isinstance(repo, PostgresRepository): raise RuntimeError("Review workflow requires PostgreSQL")
    return MatchReviewService(repo)
class ReviewRequest(BaseModel): review_note: str | None = None
@router.get("/candidates")
def candidates(s: MatchReviewService = Depends(service)): return s.candidates()
@router.get("/candidates/{candidate_type}/{candidate_id}")
def detail(candidate_type: Literal['LH_NOTICE','LH_MOVE_IN'], candidate_id: str, s: MatchReviewService = Depends(service)): return s.detail(candidate_type, candidate_id)
@router.get("/candidates/{candidate_type}/{candidate_id}/suggestions")
def suggestions(candidate_type: Literal['LH_NOTICE','LH_MOVE_IN'], candidate_id: str, s: MatchReviewService = Depends(service)): return s.detail(candidate_type, candidate_id)["suggestions"]
@router.post("/rebuild-suggestions")
def rebuild(s: MatchReviewService = Depends(service)): return s.rebuild()
@router.post("/suggestions/{suggestion_id}/verify")
def verify(suggestion_id: str, body: ReviewRequest, s: MatchReviewService = Depends(service)): return s.decide(suggestion_id, 'VERIFIED', body.review_note)
@router.post("/suggestions/{suggestion_id}/reject")
def reject(suggestion_id: str, body: ReviewRequest, s: MatchReviewService = Depends(service)): return s.decide(suggestion_id, 'REJECTED', body.review_note)
