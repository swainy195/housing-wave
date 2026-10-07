from apps.api.services.match_review_service import _has_identity_evidence, score_candidate


PROJECT = {"id": "P1", "name": "성남금토 A-1BL", "province": "경기", "district": "성남", "address": None, "planned_units": 100, "housing_type": "국민임대"}


def test_same_region_district_block_is_explainable_recommendation_not_match():
    result = score_candidate({"province": "경기도", "name": "성남금토 A1", "district": "성남금토", "block": "A-1BL", "address": None, "units": 100, "housing_type": "국민임대"}, PROJECT)
    assert result is not None
    score, evidence = result
    assert score >= 80
    assert evidence["block"]["status"] == "MATCH"
    assert evidence["project_name"]["status"] in {"MATCH", "PARTIAL"}


def test_cross_region_is_hard_filtered():
    assert score_candidate({"province": "인천", "name": "성남금토 A1"}, PROJECT) is None


def test_block_only_is_not_positive_evidence_regression():
    result = score_candidate({"province": "경기", "name": "성남복정1 A1", "district": "성남복정1", "block": "A1", "units": None}, PROJECT)
    assert result is not None
    score, evidence = result
    assert evidence["block"]["status"] == "PARTIAL"
    assert score < 50


def test_official_project_retrieval_adds_explainable_non_decisive_evidence():
    result = score_candidate({"province": "경기", "name": "성남금토 A1", "district": "성남금토", "block": "A1"}, PROJECT, {"search_query": "성남금토 A1", "search_rank": 1})
    assert result is not None
    assert result[1]["retrieval"]["status"] == "PARTIAL"


def test_region_plus_retrieval_alone_cannot_create_suggestion():
    result = score_candidate({"province": "경기", "name": "전혀 다른 공고"}, PROJECT, {"search_query": "성남금토", "search_rank": 1})
    assert result is not None and result[0] == 40
    assert not _has_identity_evidence(result[1])
