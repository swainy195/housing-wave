# Phase 1 아키텍처

## 데이터 흐름

```text
data/sample JSON ── SampleRepository ─┐
                                      ├─ Repository contract
Supabase PostgreSQL ─ PostgresRepository ┘
          │
          ▼
   DashboardService ── KPI / delay / progress / upcoming calculations
          │
          ▼
      FastAPI routers
          │ JSON
          ▼
 React services/api.ts
          │
          ▼
 Dashboard + filters + detail drawer
```

`DATABASE_MODE`가 같은 Repository 계약을 구현하는 JSON 또는 PostgreSQL 저장소를 선택합니다. 서비스와 라우터는 어떤 저장소가 사용되는지 알 필요가 없습니다.

## 데이터 모델 관계

```text
Organization 1 ── N Policy
Organization 1 ── N Project
Policy N ── N Project  (PolicyProjectLink: OFFICIAL / VERIFIED / CANDIDATE)
Project 1 ── N ProjectEvent
Project 1 ── N ConstructionProgress
Project 1 ── N SupplyAnnouncement
Organization 1 ── N DataSource
```

## 핵심 설계 결정

- 생애주기 순서는 `STAGE_ORDER` 한 곳에서 관리합니다.
- `DataStatus`는 모든 주요 엔터티에서 동일한 네 상태를 사용합니다.
- 계산식은 `DashboardService`에 두고 라우터는 HTTP 입출력만 담당합니다.
- `null`을 정상적인 미확보 값으로 유지하며 직렬화 과정에서 0으로 변환하지 않습니다.
- 프런트엔드는 화면 구성요소와 API 호출 계층을 분리합니다.
- 빌드된 프런트엔드가 있으면 FastAPI가 단일 PoC 서버로 함께 제공합니다.
- MapLibre GL은 네트워크 타일 대신 내장 수도권 GeoJSON 경계와 사업 마커를 사용합니다. 따라서 지도는 외부 API 키 없이도 동작합니다.
