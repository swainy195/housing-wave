"""Explainable, human-approved project link recommendations.

Suggestions are deliberately not matches.  Only ``verify`` changes a source
candidate's project relation, and every decision is snapshotted for audit.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text

from apps.api.ingest.lh_move_in_plan import district_key, extract_blocks, normalize_block_name
from apps.api.repositories.postgres_repository import PostgresRepository, _row_dict

TOP_K = 3
MIN_SCORE = 40


def _has_identity_evidence(evidence: dict[str, Any]) -> bool:
    """A retrieval hit plus province is never enough to show a suggestion."""
    return any(
        evidence.get(key, {}).get("status") in {"MATCH", "PARTIAL"}
        for key in ("district", "project_name", "block", "address")
    )


def _normal(value: str | None) -> str:
    value = (value or "").upper().replace("블록", "BL")
    return re.sub(r"[^0-9A-Z가-힣]", "", value)


def _province(value: str | None) -> str | None:
    value = (value or "").strip()
    return {"서울특별시": "서울", "경기도": "경기", "인천광역시": "인천"}.get(value, value or None)


def _evidence(status: str, candidate: Any, project: Any, reason: str) -> dict[str, Any]:
    return {"status": status, "candidate": candidate, "project": project, "reason": reason}


def score_candidate(candidate: dict[str, Any], project: dict[str, Any], retrieval: dict[str, Any] | None = None) -> tuple[float, dict[str, Any]] | None:
    """Rank a same-province project without ever treating the rank as a match."""
    province = _province(candidate.get("province"))
    if province != project["province"]:
        return None  # hard filter: cross-province suggestions are unsafe
    name = candidate.get("name") or ""
    district = candidate.get("district") or ""
    block = candidate.get("block") or ""
    address = candidate.get("address") or ""
    units = candidate.get("units")
    project_name = project["name"]
    evidence: dict[str, Any] = {"region": _evidence("MATCH", province, project["province"], "광역 지역 일치")}
    score = 30.0
    if retrieval:
        score += 10
        evidence["retrieval"] = _evidence("PARTIAL", retrieval["search_query"], project_name if "project_name" in locals() else project["name"], "LH 공식 공고 검색 결과로 발견됨; 단독 확정 근거 아님") | {"search_rank": retrieval["search_rank"]}

    candidate_district = _normal(district) or _normal(district_key(name))
    project_district = _normal(district_key(project_name))
    if candidate_district and project_district:
        if candidate_district == project_district:
            score += 20; evidence["district"] = _evidence("MATCH", district, district_key(project_name), "지구명 정규화 일치")
        elif candidate_district in project_district or project_district in candidate_district:
            score += 8; evidence["district"] = _evidence("PARTIAL", district, district_key(project_name), "지구명 일부 유사")
        else:
            evidence["district"] = _evidence("MISMATCH", district, district_key(project_name), "지구명이 달라 확정 근거로 사용하지 않음")
    else:
        evidence["district"] = _evidence("UNKNOWN", district or None, district_key(project_name) or None, "지구명 미확보")

    similarity = SequenceMatcher(None, _normal(name), _normal(project_name)).ratio() if name else 0
    if _normal(name) and _normal(name) == _normal(project_name):
        score += 30; status, reason = "MATCH", "사업명 정규화 일치"
    elif similarity >= .78:
        score += 15; status, reason = "PARTIAL", "사업명 고유사도"
    elif similarity >= .55:
        score += 5; status, reason = "PARTIAL", "사업명 약한 유사도"
    else:
        status, reason = "MISMATCH", "사업명 유사도 낮음"
    evidence["project_name"] = _evidence(status, name or None, project_name, reason) | {"similarity": round(similarity, 3)}

    candidate_blocks = set(extract_blocks(block or name))
    project_blocks = set(extract_blocks(project_name))
    shared_blocks = sorted(candidate_blocks & project_blocks)
    district_match = evidence["district"]["status"] == "MATCH"
    if shared_blocks and district_match:
        score += 30; evidence["block"] = _evidence("MATCH", block or name, project_name, "지구명과 블록의 복합 일치") | {"shared": shared_blocks}
    elif shared_blocks:
        evidence["block"] = _evidence("PARTIAL", block or name, project_name, "블록 단독 일치: 점수와 확정 근거에서 제외") | {"shared": shared_blocks}
    elif candidate_blocks:
        evidence["block"] = _evidence("MISMATCH", block or name, project_name, "블록 불일치")
    else:
        evidence["block"] = _evidence("UNKNOWN", None, next(iter(project_blocks), None), "후보 블록 미확보")

    if candidate.get("housing_type") and project.get("housing_type"):
        if _normal(candidate["housing_type"]) == _normal(project["housing_type"]):
            score += 10; evidence["housing_type"] = _evidence("MATCH", candidate["housing_type"], project["housing_type"], "주택유형 일치")
        else: evidence["housing_type"] = _evidence("MISMATCH", candidate["housing_type"], project["housing_type"], "주택유형 불일치")
    else: evidence["housing_type"] = _evidence("UNKNOWN", candidate.get("housing_type"), project.get("housing_type"), "유형 비교 정보 부족")

    if address and project.get("address"):
        a, b = _normal(address), _normal(project["address"])
        if a == b: score += 40; status, reason = "MATCH", "주소 정규화 일치"
        elif a in b or b in a: score += 15; status, reason = "PARTIAL", "주소 일부 일치"
        else: status, reason = "MISMATCH", "주소 불일치"
        evidence["address"] = _evidence(status, address, project["address"], reason)
    else: evidence["address"] = _evidence("UNKNOWN", address or None, project.get("address"), "공식 주소 비교 불가")
    if units is not None and project.get("planned_units") is not None:
        gap = abs(int(units) - int(project["planned_units"]))
        if gap == 0: score += 10; status, reason = "MATCH", "호수 일치"
        elif gap <= max(5, int(units) * .1): score += 5; status, reason = "PARTIAL", "호수 근접"
        else: status, reason = "MISMATCH", "호수 차이 큼"
        evidence["units"] = _evidence(status, units, project["planned_units"], reason)
    else: evidence["units"] = _evidence("UNKNOWN", units, project.get("planned_units"), "호수 비교 불가")
    return score, evidence


class MatchReviewService:
    def __init__(self, repo: PostgresRepository) -> None: self.repo = repo

    def _rows(self, sql: str, **params: Any) -> list[dict[str, Any]]:
        with self.repo.engine.connect() as c: return [_row_dict(row) for row in c.execute(text(sql), params)]

    def rebuild(self) -> dict[str, Any]:
        projects = self._rows("SELECT id,name,province,district,address,planned_units,housing_type FROM projects WHERE is_demo=false AND organization_id='ORG-LH'")
        notices = self._rows("SELECT id,pan_id,pan_name,region_name,district_name,block_name,address_raw,notice_supply_units,supply_type,project_match_status FROM lh_notice_candidates WHERE project_match_status='REVIEW_REQUIRED'")
        moves = self._rows("SELECT id,project_name_raw,province_raw,project_name_normalized,construction_units,housing_type,match_status,source_kind FROM project_candidates WHERE source_kind='MOVE_IN_PLAN' AND match_status='REVIEW_REQUIRED'")
        retrievals = {(row["candidate_id"], row["project_id"]): row for row in self._rows("SELECT candidate_id,project_id,search_query,search_rank FROM project_notice_retrievals")}
        created: dict[str, int] = {"LH_NOTICE": 0, "LH_MOVE_IN": 0, "candidates": 0}
        with self.repo.engine.begin() as c:
            for kind, source in (("LH_NOTICE", notices), ("LH_MOVE_IN", moves)):
                for row in source:
                    candidate = ({"province": row["region_name"], "name": row["pan_name"], "district": row.get("district_name"), "block": row.get("block_name"), "address": row.get("address_raw"), "units": row.get("notice_supply_units"), "housing_type": row.get("supply_type")} if kind == "LH_NOTICE" else {"province": row["province_raw"], "name": row["project_name_raw"], "district": district_key(row["project_name_raw"]), "block": row["project_name_raw"], "address": None, "units": row.get("construction_units"), "housing_type": row.get("housing_type")})
                    ranked = [(score, evidence, project) for project in projects if (result := score_candidate(candidate, project, retrievals.get((row["id"], project["id"])) if kind == "LH_NOTICE" else None)) is not None for score, evidence in [result] if score >= MIN_SCORE and _has_identity_evidence(evidence)]
                    ranked.sort(key=lambda item: (-item[0], item[2]["name"]))
                    pending_ids = [r[0] for r in c.execute(text("SELECT id FROM candidate_match_suggestions WHERE candidate_type=:kind AND candidate_id=:candidate AND review_status='PENDING'"), {"kind": kind, "candidate": row["id"]})]
                    if pending_ids: c.execute(text("DELETE FROM candidate_match_suggestions WHERE id = ANY(:ids)"), {"ids": pending_ids})
                    for rank, (score, evidence, project) in enumerate(ranked[:TOP_K], 1):
                        c.execute(text("""INSERT INTO candidate_match_suggestions (id,candidate_type,candidate_id,project_id,score,match_rank,match_evidence)
                          VALUES (:id,:kind,:candidate,:project,:score,:rank,CAST(:evidence AS jsonb))
                          ON CONFLICT (candidate_type,candidate_id,project_id) DO UPDATE SET score=EXCLUDED.score,match_rank=EXCLUDED.match_rank,match_evidence=EXCLUDED.match_evidence,updated_at=now()"""), {"id": f"CMS-{uuid.uuid4().hex[:20]}", "kind":kind,"candidate":row["id"],"project":project["id"],"score":score,"rank":rank,"evidence":json.dumps(evidence, ensure_ascii=False)})
                        created[kind] += 1
                    created["candidates"] += 1
        return {"review_candidates": created["candidates"], "suggestions": created["LH_NOTICE"] + created["LH_MOVE_IN"], "by_type": created, "threshold": MIN_SCORE, "top_k": TOP_K}

    def candidates(self) -> dict[str, Any]:
        sql = """SELECT 'LH_NOTICE' AS candidate_type,n.id AS candidate_id,n.pan_name AS name,n.region_name AS province,n.project_match_status AS candidate_status,n.validation_status,n.is_demo,COUNT(s.id) FILTER (WHERE s.review_status='PENDING') AS suggestion_count
          FROM lh_notice_candidates n LEFT JOIN candidate_match_suggestions s ON s.candidate_type='LH_NOTICE' AND s.candidate_id=n.id WHERE n.is_demo=false GROUP BY n.id
          UNION ALL SELECT 'LH_MOVE_IN',p.id,p.project_name_raw,p.province_raw,p.match_status,p.validation_status,p.is_demo,COUNT(s.id) FILTER (WHERE s.review_status='PENDING') FROM project_candidates p LEFT JOIN candidate_match_suggestions s ON s.candidate_type='LH_MOVE_IN' AND s.candidate_id=p.id WHERE p.source_kind='MOVE_IN_PLAN' AND p.is_demo=false GROUP BY p.id ORDER BY candidate_type,candidate_id"""
        rows = self._rows(sql)
        counts = {"review_required": sum(r["candidate_status"] == "REVIEW_REQUIRED" for r in rows), "matched": sum(r["candidate_status"] == "MATCHED" for r in rows), "rejected": self._rows("SELECT COUNT(*) AS count FROM candidate_match_suggestions WHERE review_status='REJECTED'")[0]["count"]}
        return {"summary": counts, "items": rows}

    def detail(self, candidate_type: str, candidate_id: str) -> dict[str, Any]:
        if candidate_type == "LH_NOTICE":
            rows = self._rows("SELECT id,pan_id,pan_name AS name,region_name AS province,district_name AS district,block_name AS block,address_raw AS address,notice_supply_units AS units,supply_type AS housing_type,project_match_status AS candidate_status,detail_url FROM lh_notice_candidates WHERE id=:id", id=candidate_id)
        elif candidate_type == "LH_MOVE_IN":
            rows = self._rows("SELECT id,project_name_raw AS name,province_raw AS province,NULL::text AS district,project_name_raw AS block,NULL::text AS address,construction_units AS units,housing_type,match_status AS candidate_status,planned_move_in_period_text FROM project_candidates WHERE id=:id AND source_kind='MOVE_IN_PLAN'", id=candidate_id)
        else: raise HTTPException(404, "Unsupported candidate type")
        if not rows: raise HTTPException(404, "Candidate not found")
        suggestions = self._rows("""SELECT s.id,s.score,s.match_rank,s.review_status,s.reviewed_by,s.reviewed_at,s.review_note,s.match_evidence,p.id AS project_id,p.name AS project_name,p.province,p.district,p.address,p.planned_units,p.housing_type FROM candidate_match_suggestions s JOIN projects p ON p.id=s.project_id WHERE s.candidate_type=:kind AND s.candidate_id=:id ORDER BY s.match_rank""", kind=candidate_type,id=candidate_id)
        retrievals = self._rows("""SELECT r.project_id,p.name AS project_name,r.search_query,r.search_rank,r.source_url,r.retrieved_at
          FROM project_notice_retrievals r JOIN projects p ON p.id=r.project_id WHERE r.candidate_id=:id ORDER BY r.search_rank,p.name""", id=candidate_id) if candidate_type == "LH_NOTICE" else []
        return {"candidate_type": candidate_type, "candidate": rows[0], "suggestions": suggestions, "retrievals": retrievals}

    def decide(self, suggestion_id: str, decision: str, note: str | None) -> dict[str, Any]:
        if decision not in {"VERIFIED", "REJECTED"}: raise HTTPException(400, "Unsupported decision")
        with self.repo.engine.begin() as c:
            row = c.execute(text("SELECT * FROM candidate_match_suggestions WHERE id=:id FOR UPDATE"), {"id": suggestion_id}).mappings().first()
            if not row: raise HTTPException(404, "Suggestion not found")
            if row["review_status"] != "PENDING": raise HTTPException(409, "Suggestion has already been reviewed")
            c.execute(text("UPDATE candidate_match_suggestions SET review_status=:decision,reviewed_by='LOCAL_REVIEWER',reviewed_at=now(),review_note=:note,updated_at=now() WHERE id=:id"), {"decision":decision,"note":note,"id":suggestion_id})
            c.execute(text("""INSERT INTO candidate_match_reviews (id,suggestion_id,candidate_type,candidate_id,project_id,decision,review_note,match_evidence_snapshot)
              VALUES (:id,:sid,:kind,:candidate,:project,:decision,:note,CAST(:evidence AS jsonb))"""), {"id":f"CMR-{uuid.uuid4().hex[:20]}","sid":suggestion_id,"kind":row["candidate_type"],"candidate":row["candidate_id"],"project":row["project_id"],"decision":decision,"note":note,"evidence":json.dumps(row["match_evidence"], ensure_ascii=False)})
            if decision == "VERIFIED":
                c.execute(text("UPDATE candidate_match_suggestions SET review_status='REJECTED',reviewed_by='LOCAL_REVIEWER',reviewed_at=now(),review_note='SUPERSEDED_BY_VERIFIED_SUGGESTION',updated_at=now() WHERE candidate_type=:kind AND candidate_id=:candidate AND id<>:id AND review_status='PENDING'"), {"kind":row["candidate_type"],"candidate":row["candidate_id"],"id":suggestion_id})
                if row["candidate_type"] == "LH_NOTICE":
                    c.execute(text("UPDATE lh_notice_candidates SET matched_project_id=:project,project_match_status='MATCHED',match_type='HUMAN_VERIFIED_RECOMMENDATION',match_evidence=CAST(:evidence AS jsonb),review_reason='VERIFIED_HUMAN_REVIEW',updated_at=now() WHERE id=:candidate"), {"project":row["project_id"],"candidate":row["candidate_id"],"evidence":json.dumps(row["match_evidence"], ensure_ascii=False)})
                else:
                    c.execute(text("UPDATE project_candidates SET matched_project_id=:project,match_status='MATCHED',match_type='HUMAN_VERIFIED_RECOMMENDATION',match_evidence=CAST(:evidence AS jsonb),validation_status='VALIDATED',review_reason='VERIFIED_HUMAN_REVIEW',updated_at=now() WHERE id=:candidate"), {"project":row["project_id"],"candidate":row["candidate_id"],"evidence":json.dumps(row["match_evidence"], ensure_ascii=False)})
        return {"suggestion_id": suggestion_id, "decision": decision, "candidate_linked": decision == "VERIFIED"}
