# Project Master

Project Master는 정책·인허가·건설·공급·입주를 연결하는 기준축이다. 공식 원본은 먼저 RAW 문서/레코드로 보존하고 `project_candidates`에서 검증한다. 후보는 기관, 원문 사업명, 지역, 계획호수 또는 사업규모, 공식 출처가 확인될 때만 core `projects`로 승격한다.

사업명 단독 또는 fuzzy match는 금지한다. 외부 식별자, 정확한 주소+사업명, 지구+블록처럼 강한 근거가 없으면 `REVIEW_REQUIRED`로 남긴다. 정확한 날짜가 아닌 공급시기는 `planned_supply_period_text`에 보존하며 임의 날짜로 변환하지 않는다.

공동주택 단지, LH 공고, 정책사업은 동일 개념이 아니므로 자동 병합하지 않는다. 실제 project가 승격되면 `is_demo=false`이며 정책 KPI는 별도 `OFFICIAL`/`VERIFIED` 정책 연결이 있을 때만 반영된다.

## LH 입주계획 연결

LH청약플러스 입주계획은 후보로 먼저 저장한다. 건설호수는 공급계획의 계획 공급호수와 다른 의미이므로 `construction_units`로 분리하며, core project의 `planned_units`를 덮어쓰지 않는다. 자동 매칭은 같은 지역에서 원문명 정규화가 정확히 같거나, 유일한 블록명이 정확히 같은 경우에만 수행한다. 그 밖의 행은 `REVIEW_REQUIRED`로 보존한다.

입주년월은 원문 `YYYY.MM` 및 `project_schedule_periods`의 `MONTH` granularity로 저장한다. UI는 원문 월만 표시하며 내부 기간 필터 이외의 가짜 일자를 제시하지 않는다. PAN_ID는 공고 ID이므로 `external_identifiers`에 project ID처럼 저장하지 않고 `lh_notice_candidates.matched_project_id` 관계에만 남긴다.

## 사람 검토 기반 연결

정확한 자동 규칙으로도 연결하지 못한 LH 공고·입주계획은 후보 추천으로 재평가할 수 있다. 추천 단계는 LH와 광역지역을 hard filter로 사용하고, 지역·지구명·사업명 유사도·지구명과 결합한 블록·유형·주소·호수 비교를 `MATCH`/`PARTIAL`/`MISMATCH`/`UNKNOWN` evidence로 남긴다. SequenceMatcher 유사도는 순위 산정용일 뿐 확정 근거가 아니다.

특히 `A1`, `A-1BL` 같은 블록 코드만 일치하는 경우 positive evidence나 자동 매칭에 쓰지 않는다. 담당자가 VERIFIED할 때만 candidate ↔ project 관계가 확정되며, 모든 결정은 audit history에 snapshot으로 남는다. 이 연결은 PolicyProjectLink가 아니므로 정책 KPI에 자동 포함되지 않는다.

## LH 2026 임대주택 공급계획

공식 LH청약플러스의 임대주택 공급계획 웹 표를 `raw_api_records`에 원문 행으로 보존한다. 지역·유형·지구명/공급예정지역·전용면적·공급호수·공급예정시기·입주예정·본부·비고를 보존하며, 서울·경기·인천 행만 현재 범위다. 동일 사업의 면적별 행은 같은 지역·유형·공급월 단위로만 합산하여 core project의 `planned_units`에 적재한다. 이 값은 **사업 전체 규모가 아닌 해당 공급계획의 계획 공급호수**다.

공급/입주 시기는 원문 `YYYY년MM월`을 유지한다. 일자를 임의로 만들지 않으며 `project_schedule_periods`가 월 단위 향후 일정만 표시한다. 원본에는 공식 project ID·주소·좌표가 없으므로 `external_identifiers`, 정책 연결, 지도 marker는 만들지 않는다.
