# Phase 2 PostgreSQL/Supabase 기반

## 연결 방식

React는 Supabase에 직접 연결하지 않습니다.

```text
React → FastAPI → Repository → PostgreSQL/Supabase
                              ├─ PostGIS
                              ├─ provenance
                              └─ DEMO/LIVE 구분
```

백엔드는 `DATABASE_MODE=json|postgres`로 구현체를 선택합니다. 운영 환경에서는 `postgres`, 로컬 UI 개발과 단위 테스트에서는 `json`을 사용할 수 있습니다.

## 테이블

- `organizations`
- `policies`
- `projects` — 위·경도와 `geometry(Point, 4326)` 동시 보존
- `policy_project_links`
- `project_events`
- `construction_progress` — 프로젝트별 여러 기준일을 허용
- `supply_announcements`
- `data_sources`
- `data_status_history`
- `organization_stage_coverage`

상태와 단계는 PostgreSQL enum 대신 CHECK constraint를 사용합니다. 향후 값 추가 시 enum type 교체보다 migration이 단순합니다.

## View

- `v_latest_construction_progress`: 사업별 최신 공정과 NULL-safe `progress_gap`
- `v_project_current_status`: 사업과 최신 공정 결합
- `v_policy_progress`: OFFICIAL/VERIFIED만 포함한 단계별 누적 물량
- `v_data_coverage`: 기관×단계 커버리지
- `v_upcoming_events`: 계획/실제 일정을 단일 날짜로 조회

## DEMO seed

`python -m apps.api.scripts.seed_demo`는 현재 JSON을 정규화해 upsert합니다. 동일 ID와 기관×단계 키를 사용하므로 반복 실행해도 행이 무한 증가하지 않습니다. 월별 공정 샘플은 각각 별도 `reference_date` 행으로 변환됩니다.

## 운영 검증 절차

`apps/api/.env`에 `DATABASE_MODE=postgres`와 `DATABASE_URL`을 설정한 뒤 다음을 실행합니다. URL과 비밀번호는 어떤 스크립트 출력에도 포함하지 않습니다.

```powershell
python -m apps.api.scripts.apply_migration --apply
python -m apps.api.scripts.seed_demo
python -m apps.api.scripts.seed_demo
python -m apps.api.scripts.compare_repository_modes
```

`apply_migration`은 PostGIS extension, 필수 table/view, `projects.location` geometry type, GIST spatial index, 프로젝트 trigger를 검사합니다. 표준 `postgresql://` URL과 `postgresql+psycopg://` URL 모두 psycopg 3 드라이버로 정규화합니다.

Phase 2.1 검증에서는 Supabase PostgreSQL/PostGIS migration과 두 번의 DEMO upsert를 완료했습니다. 16개 사업과 21개 월별 공정 행이 유지됐고, JSON fallback과 PostgreSQL의 summary/pipeline/coverage/alerts/construction/upcoming 응답이 일치했습니다.

## SH 주택관리현황 reference master

`012_sh_housing_management_references.sql`은 서울시 Open Data `SearchSHRentApt`의 단지 관리현황을 `housing_complex_references`에 저장하고, 허용된 사업 연결만 `project_housing_complex_references`에 분리한다. RAW 응답은 `raw_api_records`에 JSON/checksum으로 보존한다.

`APT_OPEN_DT`는 원문을 `move_in_start_raw`에 먼저 보존한다. 실제 응답의 Excel serial 형식이 확인된 경우에만 `move_in_start_date`로 변환하며, NULL 세대수는 0으로 대체하지 않는다. `APT_CNT`는 관리 세대수이고 공급계획 공급호수가 아니다. 주소·세대수는 exact match의 보강 근거일 뿐, 자동 확정 기준이 아니다.

연결 규칙은 비-DEMO SH 사업에 대해 정규화 단지명과 자치구가 모두 정확히 일치할 때만 `EXACT_NAME_DISTRICT` 관계를 생성한다. fuzzy match, 좌표 추정, marker 생성, 정책 KPI 연결은 하지 않는다. 이 source는 관리현황만 제공하므로 SH `SUPPLY` coverage는 `PARTIAL`이며 note에 공급계획·공고·실적 미연계를 명시한다.

## Phase 3-6A: LH 구조화 공급계획

`007_lh_supply_plan_periods.sql`은 월 단위 공식 공급계획을 위한 `project_schedule_periods`를 추가한다. `period_text`와 `period_year`/`period_month`를 분리해 저장하며, 기존 `project_events.planned_date`에는 임의의 일자를 쓰지 않는다. LH 표는 `raw_api_records`에 `HTML_TABLE` 형식으로 보존하고, 행은 `project_candidates`에 먼저 저장한다.

2026 LH 임대주택 공급계획은 사업 ID·주소·좌표를 주지 않으므로 `external_identifiers`에는 쓰지 않는다. 공식 출처·지역·사업명·공급호수·유형·공급월이 함께 있는 행만 같은 키의 core `projects`로 승격한다. 이때 `planned_units`는 계획상 공급호수이며 총 사업규모가 아니다. 이 core 사업에는 정책 링크를 만들지 않아 정책 KPI에 포함되지 않는다.

## Phase 3-7: LH 입주계획

`008_lh_move_in_plan.sql`은 기존 후보·월 일정 구조를 확장한다. 입주계획의 `construction_units`, 월 원문, 입주지정기간, source row와 규칙기반 match evidence를 `project_candidates`에 보존한다. `project_schedule_periods`는 `MOVE_IN` 월과 granularity를 저장하며, 실제 일자가 없을 때 `project_events`에 가짜 일자를 생성하지 않는다.

입주계획의 건설호수는 `projects.planned_units`를 변경하지 않는다. 기존 LH 공고의 PAN_ID는 공고 ID로 유지되며, 확정 매칭된 경우에도 `lh_notice_candidates.matched_project_id` 관계만 사용한다.

## Phase 3-8: LH 공고 상세 identity 조사

`009_lh_identity_enrichment.sql`은 LH 공고 후보에 공식 상세 원문에서 확인한 지구·블록·주소·공급호수·첨부 메타데이터를 보존한다. 상세 원문은 `raw_api_records`의 `HTML_PAGE`로 checksum과 함께 보관한다. 블록은 반드시 지구명과 함께 비교하며, PAN_ID는 계속 공고 식별자로만 취급한다.

## Phase 3-9: Human-in-the-loop 사업 연결 검토

`010_match_review_workflow.sql`은 `candidate_match_suggestions`와 `candidate_match_reviews`를 추가한다. 전자는 후보별 Project Master 추천과 설명 가능한 `match_evidence`를, 후자는 사람의 VERIFIED/REJECTED 판단 당시의 근거 snapshot, 검토자(`LOCAL_REVIEWER`), 시각 및 메모를 보존한다.

추천은 `PENDING`, `VERIFIED`, `REJECTED` 상태를 가지며 candidate의 `REVIEW_REQUIRED`/`MATCHED` 상태와 분리된다. VERIFY는 같은 candidate의 다른 PENDING 추천을 REJECTED로 전환하고, 해당 candidate에만 `matched_project_id`와 `HUMAN_VERIFIED_RECOMMENDATION` provenance를 기록한다. 후보 추천 또는 사람 검증은 `policy_project_links`를 만들지 않으므로 정책 KPI에는 영향을 주지 않는다.

입주계획은 검증 후에도 공식 월 원문과 `MONTH` granularity를 유지한다. 공식 일자가 없는 동안 `project_events`에 임의의 날짜를 만들지 않는다.

## Phase 3-10: Project-driven LH 공고 역검색

`011_project_driven_lh_retrieval.sql`의 `project_notice_retrievals`는 실제 LH Project Master에서 시작한 공식 공고 검색의 provenance를 저장한다. `project_id`, `candidate_id`, `search_query`, 공식 목록 URL, 결과 순위 및 수집시각을 보존한다. 후보는 기존 `lh_notice_candidates`와 Phase 3-9 review workflow를 재사용하며, 검색 결과만으로 `MATCHED`가 되지 않는다.

공식 검색 발견은 score의 보조 evidence일 뿐이며, 같은 지역(+30)과 검색 발견(+10)만으로는 suggestion을 만들 수 없다. 지구·사업명·지구+블록·주소 중 하나의 독립 identity evidence가 있어야 40점 이상 suggestion으로 표시된다.

## 향후 ingest

기관별 수집기는 `apps/api/ingest/base.py`의 `SourceAdapter` 경계를 구현합니다. 수집 결과는 `IngestBatch`로 정규화한 뒤 다음 순서로 저장합니다.

1. `data_sources`와 수집 기준일 확인
2. 원천 레코드 검증 및 기관 식별
3. 정책·사업·이벤트·공정·공급 upsert
4. 커버리지와 상태 변경 이력 기록
5. API 조회는 기존 Repository 계약을 그대로 사용
