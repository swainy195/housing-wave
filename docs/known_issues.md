# Final Known Issues

| Issue | 현재 상태 | 영향 | 향후 해결 방법 |
|---|---|---|---|
| iH gateway | 공식 endpoint 접근/응답 경로가 안정적으로 재현되지 않음 | 인천 iH 실적의 확장 불가 | 기관 gateway 정책 확인 후 소량 schema 검증 |
| 공동주택 API gateway | base URL은 확인했지만 operation·응답을 안정적으로 확인하지 못함 | 단지 reference master 미구축 | 활용신청 명세와 실제 응답으로 operation 검증 |
| LH 공고 필드 부족 | Project-driven 공고 55건에서 공급호수 0건 | 공급계획과 공고 물량 비교 제한 | 공식 Excel/PDF의 구조화 가능 필드 검증 |
| 공통 Project ID 부재 | 공급계획·공고·입주계획에 공통 식별자가 없음 | 자동/반자동 확정 연결 위험 | 기관 공통 사업 ID 및 관계 API 필요 |
| 공식 좌표 부족 | LIVE LH Project 23건의 공식 좌표 0건 | LIVE 지도 marker 미표시 | 공식 주소·좌표 source 확보 후 별도 검증 |
| 입주계획 exact link 0건 | 공식 입주 원천 6건은 모두 REVIEW_REQUIRED | LIVE MOVE_IN 일정 연결 불가 | 지구·블록·공식 ID가 있는 source 확보 |
| REVIEW_REQUIRED 다수 | LH 공고 64건, 입주계획 6건 | 담당자 검토 없이는 확정 관계 없음 | evidence를 보강하고 human review 수행 |
| 실제 정책 KPI 관계 없음 | LH LIVE Project에 OFFICIAL/VERIFIED PolicyProjectLink 없음 | 정책 KPI에 LIVE 물량 미반영 | 정책 문서 기반 검증 관계 구축 |

이 이슈들은 오류를 숨기지 않고 데이터 품질 상태로 노출하는 PoC의 핵심 결과입니다.
