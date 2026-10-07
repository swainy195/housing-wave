# Phase 3-1 국토교통부 주택인허가 수집

공식 공공데이터포털의 건축HUB 주택인허가정보 서비스에서 `getHpBasisOulnInfo`만 사용한다. Base URL은 `https://apis.data.go.kr/1613000/HsPmsHubService`이며 JSON/XML 응답, `serviceKey`, `pageNo`, `numOfRows` 및 필지 키(`sigunguCd`, `bjdongCd`, `platGbCd`, `bun`, `ji`)를 사용한다.

이 operation은 시도 단위 검색 API가 아니다. 따라서 서울/경기/인천이라는 지역 라벨과 **공식 필지 키**를 함께 입력해야 하며, 이름 유사도나 임의 주소로 자동 매칭하지 않는다.

```powershell
python -m apps.api.scripts.apply_migration --apply
python -m apps.api.scripts.ingest_molit_permits --region seoul --sigungu-cd 11545 --bjdong-cd 10200 --bun 0308 --ji 0000 --dry-run
python -m apps.api.scripts.ingest_molit_permits --region seoul --sigungu-cd 11545 --bjdong-cd 10200 --bun 0308 --ji 0000 --persist
```

환경변수는 `MOLIT_HOUSING_PERMIT_API_KEY` 하나이며 키와 DB URL은 로그에 출력하지 않는다. 원본 item은 `raw_api_records`에 checksum으로 보존하고, `external_identifiers`의 `MOLIT_HSPMS_HUB + mgmHsrgstPk`를 프로젝트 중복 방지 키로 사용한다. 불완전한 원천 행은 raw로 보존하고 `REVIEW_REQUIRED`로 남기며 core project로 자동 생성하지 않는다.
