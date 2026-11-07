# C020 — 모듈 경계 / 의존성 계약 (R0 P0)

상태: 7개 서비스 경계 인터페이스·회귀 테스트 구현. C020의 책임 분리 수용 기준을 검증하는 문서이며, 실제 다운로드/DB/편집 기능 구현을 의미하지 않는다.

## 서비스 책임과 현황

| 경계 | 코드 경로 | 책임 | 현재 상태 |
| --- | --- | --- | --- |
| SearchCoordinator | src/nature_video_studio/search_coordinator.py | 여러 SourceAdapter를 동시에 조회, 한 제공처 오류를 다른 결과와 분리, 180초/4K 필터 사용 | 비동기 제어 로직 / 모의 어댑터 테스트 완료, 실 API 미연결 |
| SourceAdapter | src/nature_video_studio/source_adapter.py | 제공처 공식 API, 페이징, 제한·Retry-After, 메타데이터 수집의 계약 | Protocol/SearchQuery/SearchPage만 정의, 실제 제공처 미구현 |
| PreviewService | src/nature_video_studio/preview_service.py | 기존 HTTPS 이미지 다운로드/HTTP 상태 진단/캐시 처리, 호출 경로에서 asyncio.to_thread 사용 | 비동기 썸네일 래퍼 테스트, 실제 Qt GUI 연동 전 |
| RightsReview | src/nature_video_studio/rights_review.py | 기존 보수적 라이선스 상태를 분리된 서비스로 반환 | 기본 분류 동작, 개별 제3자 권리/사람 승인 증거 미완성 |
| DownloadQueue | src/nature_video_studio/download_queue.py | 선택·권리 검증 완료된 후보의 다운로드 계약/큐 | 프로토콜과 실패 차단만 구현. 실제 다운로드 없음 |
| Catalog | src/nature_video_studio/catalog.py | V2 사용자 DB/영상 메타데이터 관리 계약, V1 DB와 분리 | 프로토콜과 실패 차단만 구현. DB 백엔드 없음 |
| Composer | src/nature_video_studio/composer.py | 승인된 자료로 3/10/20/30/60분 영상을 만드는 계약 | 프로토콜과 출력 시간 검증 및 실패 차단만 구현. FFmpeg 렌더링 없음 |

공통 service_errors.py에서 FeatureUnavailable 예외를 제공한다. 실제 다운로드·DB·합성 백엔드가 없는 경우 완료를 가장하거나 빈 파일을 만들지 않고 오류를 돌려준다. 기존 models.py / filtering.py / rights.py / preview.py는 그대로 유지한다.

## 허용 의존성 방향

- GUI → 애플리케이션 작업 스케줄러 → 각각의 서비스. GUI 이벤트 처리 스레드에서 차단 네트워크·ffprobe·SQLite를 실행하지 않는다.
- search_coordinator → source_adapter, filtering, models.
- source_adapter → filtering, models.
- preview_service → preview. 이미지와 실제 Qt Multimedia 영상 플레이어는 별개이다.
- rights_review → rights, models.
- download_queue → rights, service_errors.
- catalog → models, service_errors.
- composer → service_errors.
- 위 7개 서비스 파일에는 PySide6, requests, sqlite3, keyring, subprocess, httpx, urllib.request, shutil 직접 import 금지. Network/SQLite/FFmpeg 접근은 허용된 하위 구체 구현이 생기는 R1-R5에서만 작성한다.
- SourceAdapter는 async 검색을 제공해야 한다. 실제 네트워크 구현은 비차단 방식을 사용하고, Qt에서는 작업 스레드/비동기 브리지로 연동한다. Qt 이벤트 핸들러에서 asyncio.run()을 직접 호출해 GUI를 차단하면 안 된다.
- 서비스는 다른 서비스의 내부 구현을 직접 가져오지 않고 명시적 타입 계약으로 데이터를 교환한다. 예외적인 의존성은 설계 검토와 테스트 변경을 거쳐야 한다.

## 데이터 흐름

1. 사용자는 Long Original(180초 이상 검증 원본)과 Short Composer(짧은 클립) 중 하나를 명시적으로 선택.
2. SearchCoordinator는 해당 모드에 맞는 SourceAdapter만 비동기 호출하고, 출처별 실패 사유를 구분. 원본 길이 미검증/180초 미만 후보가 장편으로 넘어가지 않음. 단편 자동 대체 금지.
3. 선택된 후보만 PreviewService의 이미지 미리보기 및 별도 Qt Multimedia 영상 재생 대상으로 전달. 이미지 디코딩 실패와 재생 실패는 다른 오류.
4. RightsReview는 출처별 조건을 분류하고, 사용자의 명시적 권리 확인이 없으면 다운로드를 승인하지 않음.
5. 향후 DownloadQueue에서 명시적 선택과 권리/URL 검증을 재확인한 뒤 V2 데이터 폴더에만 다운로드. 정상 완료 후 Catalog에 해시·출처·라이선스·길이·해상도 기록.
6. 향후 Composer는 Catalog에 등록된 승인된 자료만 ffprobe/FFmpeg로 조합하며 합성 길이와 3분 원본 길이를 분리해서 표시.

## C020 구조 자동 테스트

파일: tests/test_c020_module_boundaries.py

- 7개 파일의 존재와 AST 상대 import 허용 목록 검사. GUI/HTTP/SQLite/보안 저장소/FFmpeg 관련 직접 의존성 유입 차단.
- 179초 및 확인 안 된 원본은 장편 검색에서 제외, 정확히 180초인 검증 원본은 허용. 단편 제공처를 장편 모드에서 호출하지 않음.
- 제공처 실패에도 다른 검색 결과 보존, 원시 예외에 섞인 API 키 문자열 누출 차단, 잘못된 제공처 결과 거부.
- 포스터 실행이 호출 스레드와 다른 스레드인지 합성 fetcher로 검증.
- CC BY 검토는 자동 승인되지 않음, 사용자 선택 없는 다운로드 요청 차단, Catalog/Composer/DownloadQueue 미구현은 거짓 성공 대신 FeatureUnavailable 처리.
- 테스트에 네트워크·실제 API 키·사용자 D 드라이브·저작권 있는 미디어가 필요하지 않음.

실제 CI 검증 명령:

    python -m pytest -q tests/test_c020_module_boundaries.py
    python -m pytest -q

기존 C012, C017 전용 Gate 및 전체 회귀 테스트도 유지한다. GitHub Actions Windows/Ubuntu × Python 3.11/3.12 매트릭스의 별도 C020 단계를 통해 파일 간 직접 의존성 역행이 발견되면 CI를 실패시킨다.

## 수용 기준과 별도 미완성 Gate

- C020 2/2점은 역할/인터페이스/의존성 규칙을 문서화하고 CI 테스트를 통과한 경우에만 판정. 이것은 설계·구현 경계 완료이며 **기능 전체 완료가 아니다**.
- R1: 공식 제공처 어댑터, 실제 장편 원본 및 자연풍경 적합도 검증. 현재 실 API 검색은 아직 없음.
- R2: 실제 Windows 화면 썸네일, HTTP 오류와 로컬 QMediaPlayer 재생·일시정지·탐색. 현재 C011 시험 GUI와 별개.
- R3: 안전한 실 다운로드/중단·재개, 권리 증빙, V2 catalog 백엔드 구축.
- R4: ffprobe/FFmpeg 실제 조합 및 중복 방지, 렌더링 출력 확인.
- R5: Windows EXE·설치형 업데이트·C012 보존 Gate 실제 연결.
- C014는 절차상 feature/Draft PR 운영 PASS지만 main branch 보호 규칙이 서버에서 아직 활성화되지 않음.

이번 작업은 feature/v2-research-rebuild 브랜치에서만 진행한다. 기존 V1.0.2 프로그램, 사용자 DB·영상·키·복구 백업 및 main을 수정하지 않는다.
