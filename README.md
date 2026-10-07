# 주택파동 · Housing Wave

주택파동은 정책에서 입주까지 분산된 주택공급 정보를 사업 단위로 연결해, 진행상황과 데이터 공백을 함께 보여주는 주택공급 통합 상황판 PoC입니다.

## 프로젝트 소개

정책 담당자와 국민은 공급 물량만이 아니라 사업이 어느 단계에 있는지, 어떤 정보가 실제 데이터인지, 어디에서 연결이 끊기는지를 함께 알아야 합니다. 이 PoC는 공식 원문을 보존하고 검증 상태를 공개하는 방식으로 수도권 주택공급 흐름을 시각화합니다.

## 문제 정의

주택공급 관련 공식 데이터는 정책·사업화·인허가·건설·공급·입주 단계별 여러 시스템에 분산되어 있습니다. 각 시스템은 개별적으로 공식 데이터를 제공하지만 동일 사업을 연결하는 공통 식별체계가 부족하여, 공급 흐름을 사업 단위로 추적하기 어렵습니다.

## 핵심 기능

- 6단계 공급 lifecycle: POLICY → BUSINESS → PERMIT → CONSTRUCTION → SUPPLY → MOVE_IN
- React 상황판: 지역·기관·단계 필터, 지도, 공정 현황, 향후 3/6/12개월 일정
- LIVE/DEMO/MIXED 및 데이터 커버리지 상태의 명시적 구분
- RAW → Candidate → Project Master → Analytics provenance pipeline
- 공고·입주계획을 자동 확정하지 않는 human-in-the-loop 연결 검토

## 실제 데이터 현황

| 항목 | 검증 값 |
|---|---:|
| LH 2026 공급계획 원문 행 | 48 |
| 수도권 LIVE Project Master | 23 |
| 서울 / 경기 / 인천 | 3 / 15 / 5 |
| 계획 공급호수 | 8,072호 |
| SH 주택관리현황 reference master | 825건 |
| Project-driven 공식 공고 검색어 | 80 |
| 신규 공식 PAN_ID 공고 | 55 |
| 자동 오매칭 / VERIFIED | 0 / 0 |

`MIXED`는 오류가 아니라, 검증된 실제 데이터와 시연용 DEMO 데이터를 함께 표시한다는 뜻입니다. 실제 LH 사업은 공식 좌표가 없어 지도 marker를 만들지 않으며, 좌표가 확인된 사업만 지도에 표시합니다.

## 데이터 검증 및 연결 방식

공식 데이터라도 사업 ID·주소·지구·블록이 충분히 공통되지 않으면 연결을 확정하지 않습니다.

```text
Official source → RAW record → Normalize → REVIEW_REQUIRED candidate
                                             ↓
                              evidence-based suggestion → human review
                                             ↓
                                    VERIFIED / REJECTED
```

추천은 자동 연결이 아닙니다. 지역만 같거나 블록 코드만 같은 경우는 확정 근거로 사용하지 않으며, 정책 KPI에는 OFFICIAL/VERIFIED 정책-사업 관계만 반영합니다.

## 기술 스택과 구조

```text
React + Vite + TypeScript + MapLibre + ECharts
                    ↓
              FastAPI / Python
                    ↓
        Supabase PostgreSQL + PostGIS
```

세부 스키마는 [database.md](docs/database.md), Project Master 원칙은 [project_master.md](docs/project_master.md), 역검색 결과는 [lh_project_search_report.md](docs/lh_project_search_report.md)를 참고하세요.

## 로컬 실행

```powershell
# API
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

# Web
cd apps/web
npm run dev
```

`apps/api/.env`에는 `DATABASE_MODE=postgres`와 `DATABASE_URL`이 필요합니다. 비밀값은 저장소·문서·로그에 포함하지 않습니다.

## 테스트

```powershell
python -m pytest apps/api/tests -q
cd apps/web
npx tsc --noEmit -p tsconfig.app.json
npm run build
```

## Deployment

- Frontend: Vercel (`apps/web`, build output `dist`)
- Backend: Render (`uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT`)
- Database: Supabase PostgreSQL/PostGIS

Production frontend API URL is supplied only through `VITE_API_BASE_URL`; backend CORS uses the explicit `CORS_ALLOWED_ORIGINS` setting. Public service URLs are intentionally not listed until a Vercel and Render account deployment has completed. The deployment procedure is in [deployment.md](docs/deployment.md).

Seoul Open Data API status: **PARTIAL**. SH 주택관리현황(`SearchSHRentApt`) 825건은 RAW와 단지 reference master로 연결됐습니다. 이 데이터는 관리현황이며 공급계획·공고·실적·좌표를 뜻하지 않습니다. 단지명과 자치구가 모두 정확히 일치할 때만 비-DEMO SH 사업과 연결하며, 현재 공식 SH 공급계획 Project Master가 없어 자동 연결은 하지 않습니다.

## 데이터 품질 원칙

- `AVAILABLE`: 검증된 core 데이터가 충분히 확보됨
- `PARTIAL`: 공식 source는 연결됐으나 필드·사업·단계 연결이 불완전함
- `NOT_CONNECTED`: source가 아직 연계되지 않음
- `NOT_AVAILABLE`: 공식 source에서 해당 정보를 제공하지 않음
- `REVIEW_REQUIRED`: 공식 원천은 확보됐지만 동일 사업 연결은 추가 검증이 필요함

NULL 공정률은 0으로 바꾸지 않고, 공급계획·공급완료·건설호수·입주예정을 서로 다른 의미로 보존합니다.

## 현재 한계와 시사점

실제 연계 과정에서 발견한 가장 큰 문제는 데이터가 없다는 점이 아니라, 공식 데이터 사이의 연결키가 부족하다는 점이었습니다. 따라서 공통 Project ID, provenance, 계획/실적 분리, 데이터 품질 상태 공개, 자동 추천과 담당자 검증이 필요합니다.

SH/GH/iH 전체 연계, 공식 주소·좌표, 실제 인허가·공정률, 정책 KPI의 실제 연결은 이 PoC 범위 밖입니다. 최종 known issues는 [known_issues.md](docs/known_issues.md)에 정리했습니다.

## 팀프로젝트 활용

4주 4인 팀프로젝트에서는 문제 정의·데이터 조사·Backend/Data·Frontend/Visualization·QA/발표로 역할을 나누어 설명할 수 있습니다. 역할 배정 자체는 팀의 실제 참여 구조에 맞춰 정합니다.
