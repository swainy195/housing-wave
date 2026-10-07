# LH Project-driven Notice Search Report

Phase 3-10은 실제 LH Project Master 23건을 출발점으로 LH청약플러스 공식 공고 목록을 역검색했다. 검색 endpoint는 `https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do`이며, `panNm`·지역·유형·기간·페이지 조건을 사용한다. 외부 검색엔진 결과는 사용하지 않았다.

| Metric | Result |
|---|---:|
| Search target projects | 23 |
| Generated specific queries | 80 |
| Projects with retained official results | 16 |
| Projects with no retained result | 7 |
| Retrieval provenance relations | 82 |
| Unique official PAN_ID | 55 |
| New REVIEW_REQUIRED candidates | 55 |
| Existing pre-Phase-3-10 candidates rediscovered | 0 |
| Detail pages fetched | 55 |
| District values retained | 55 |
| Block values retained | 26 |
| Address values retained | 55 |
| Notice supply-unit values retained | 0 |
| Suggestions at threshold 40 | 0 |

Each retrieval is stored in `project_notice_retrievals` with the source Project, query, result rank, official source URL and retrieval time. A retrieval is only a candidate-generation clue. Region match plus retrieval alone cannot pass the suggestion threshold; an independent identity signal (district, project name, district+block, or address) is required. No candidate was auto-verified.
| 인천검단 AA19 | 4 | 9 | 7 | 0 |
| 의왕초평(뉴스테이) A4 | 4 | 1 | 1 | 0 |
| 의왕청계2 A1 | 4 | 7 | 5 | 0 |
| 남양주진접2 A7 | 4 | 5 | 5 | 0 |
| 군포대야미 A1 | 4 | 5 | 5 | 0 |
| 구리갈매역세권 A-3 | 4 | 5 | 5 | 0 |
| 성남금토 A2 | 4 | 5 | 5 | 0 |
| 성남금토 A4 | 4 | 5 | 5 | 0 |
| 의왕월암 A1 | 4 | 5 | 5 | 0 |
| 인천서구(거북이기지) 1 | 2 | 0 | 0 | 0 |
| 인천부평(도시재생뉴딜) A | 2 | 0 | 0 | 0 |
| 인천검단 AA19 | 4 | 9 | 7 | 0 |
| 서울공릉(복합개발) 1 | 2 | 0 | 0 | 0 |
| 부천대장 A6 | 4 | 5 | 5 | 0 |
| 과천지식정보타운 S-12 | 4 | 5 | 5 | 0 |
| 과천주암(뉴스테이) C2 | 4 | 0 | 0 | 0 |
| 서울대방(복합개발) 1 | 2 | 0 | 0 | 0 |
| 강서염창(가로주택) 01 | 2 | 0 | 0 | 0 |
| 구리갈매역세권 A-1 | 4 | 7 | 7 | 0 |
| 인천서구(석남어울림) 1 | 2 | 0 | 0 | 0 |
| 부천대장 A5 | 4 | 6 | 5 | 0 |
| 의왕월암 A3 | 4 | 5 | 5 | 0 |
