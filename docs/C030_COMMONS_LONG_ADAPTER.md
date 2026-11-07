# C030 — Wikimedia Commons 장편 원본 후보 검색 어댑터

체크리스트: C030 / R1 / P0 / 3점. 브랜치 feature/v2-research-rebuild.
검토일 2026-11-07.

공식 문서:
- https://www.mediawiki.org/wiki/Extension:TimedMediaHandler/API
- https://commons.wikimedia.org/wiki/Commons:Machine-readable_data
- https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy

Wikimedia 공식 Action API에서 generator=search, gsrnamespace=6,
gsrsearch=filetype:video + 사용자 검색어, gsrlimit=5, prop=videoinfo,
viprop=url|size|mime|mediatype|metadata|extmetadata|user 를 요청한다.
imageinfo와 videoinfo는 동시 요청 불가.
extmetadata는 비싼 속성이라 5건 이하 및 필요한 키만 조회.
서버 보호 maxlag=5, 식별 User-Agent, 2MB 응답 제한, 20초 응답 제한,
리다이렉트 차단. 429/503이면 검색 실패로 표시하고 0건으로 속이지 않는다.
실제 UI/백그라운드 수집 및 다운로드는 연결되지 않았다.

장편 후보의 duration은 WebM metadata[playtime_seconds] 또는
Ogg metadata[length]를 읽는다. 누락/오류/충돌하는 기간은
'원본 길이 미확인'. 최소 180초에서 절대 자동 완화하지 않음.
제공처 영상 URL은 Wikimedia 정식 호스트만 허용한다.
VIDEO mediatype, MIME, 파일 크기, width/height를 점검한다.
실제 재생 파일의 ffprobe, 업스케일 여부, 촬영된 무편집 연속성은 별도다.
길이 값이 있다고 해서 촬영된 장면이 완전히 연속적이었다고 증명하지 않는다.

Artist HTML은 텍스트로 바꾸고 LicenseUrl/LicenseShortName/
UsageTerms를 추출하여 출처 페이지와 함께 보존한다.
CC BY/SA는 수동 표시 조건 검토, NC/ND/불명은 차단되며
자동 다운로드 또는 유튜브 상업 이용 승인은 없다.
자연풍경 적합성은 아직 검증 안 됨으로 표시한다.

수정 파일:
- src/nature_video_studio/commons_adapter.py
- tests/test_c030_commons_adapter.py
- .github/workflows/ci.yml
- docs/C030_COMMONS_LONG_ADAPTER.md

테스트:
    python -m pip install -e ".[dev]"
    python -m pytest -q -k commons_adapter
    python -m pytest -q

CI 결과는 해당 실행 완료 후 판단. 실제 Wikimedia API 소량 검색,
실파일 검증, Windows 사용자 PC GUI 검사는 NOT_TESTED.
기존 V2 시험판 동일 위치를 유지하고 V1/DB/키/영상을 변경하지 않는다.
다음 과제: C031 Internet Archive, C032 자연풍경 아닌 영상 차단.
