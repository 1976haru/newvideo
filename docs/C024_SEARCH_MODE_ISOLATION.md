# C024 — 장편 원본/짧은 클립 검색 모드 분리 (R1 P0)

상태: 기능 및 자동 테스트 구현. 실제 GitHub Actions 증빙 검증 후 3/3점 판정 예정. 본 항목은 UI/상태/모의 API의 모드 격리를 다루며, 실 제공처 API 검색은 별도 개발 단계다.

## 요구 대비 구현

| 체크 | 구현 | 미구현 경계 |
| --- | --- | --- |
| 독립된 두 탭 | Qt QTabWidget: '3분 이상 원본' 및 '짧은 영상 조합' | 정식 Windows 앱 아님. V2 시험판 화면 |
| 각각의 검색 | 검색어·화질 필터·검색 버튼·요청 번호를 모드마다 별도 보존 | 실제 공식 API SourceAdapter 미연결. 버튼은 미연동 상태 정확히 표시 |
| 결과 건수와 목록 | 모드별 LaneState와 결과 테이블, 검색 결과 수 독립 계산 | 검색 전/진행 중/제공처 전체 오류/미연결을 0건으로 표시하지 않음 |
| 서로 다른 정렬 | 장편: 길이 긴 순 (또는 4K 우선). 단편: 짧은 컷 순 (또는 4K 우선) | 실제 4K 파일 촬영 여부는 향후 별도 검증 |
| 명시적 전환 | 양쪽 탭에 다른 모드로 전환하는 클릭 버튼 | 자동 탭 전환 및 단편으로의 몰래 대체 없음 |
| 원본 길이 | 장편은 검증된 원본 180초 이상, 단편은 검증된 5~120초 | 실제 원본 검증/ffprobe 및 출처 증거는 후속 구현 |
| 비동기·안전 | 모의 Coordinator는 GUI와 별도 QThread 호출, provider 오류 격리, 오래된 요청 응답 거부 | 실제 네트워크 연결/취소/프록시/토큰/스레드 종료 실사용은 R1 통합 Gate |

## 추가/수정 파일

- src/nature_video_studio/search_mode_state.py: SearchModeSession, LaneState, SearchTicket, LaneSort, 모드별 상태와 정렬
- src/nature_video_studio/search_tabs.py: QTabWidget, 2개 독립 입력·정렬·결과 수·결과 표, 명시적 모드 전환
- src/nature_video_studio/filtering.py: 단편 5~120초 제한
- src/nature_video_studio/trial_gui.py: C024 탭을 버전 구분된 기존 V2 시험판에 삽입
- src/nature_video_studio/version_identity.py: 실제 제공처 미연결임을 명시
- tests/test_c024_search_mode_isolation.py: 긴 영상/클립 경계, 독립 검색·건수·정렬, 만료된 응답 무시, 실패·미연동과 실제 0건 분리
- tests/test_c024_gui_search_modes.py: Windows Qt GUI 버튼·탭/독립 검색·비동기 모의 API 결과 검사
- tools/c022_windows_gui_probe.py: Windows 네이티브 스크린샷에 모드 전환 버튼 존재 검사 포함
- .github/workflows/ci.yml: Windows/Ubuntu × Python 3.11/3.12에서 pytest -k search_mode_isolation을 별도 Gate로 실행, Windows Qt GUI 테스트 및 native Windows onedir EXE 테스트

## 수용 검증 실행 명령

    python -m pytest -q -k search_mode_isolation
    python -m pytest -q
    python -m pytest -q tests/test_c011_version_identity.py tests/test_c011_gui.py tests/test_c024_gui_search_modes.py
    python -m nature_video_studio --smoke
    python -m tools.c022_windows_gui_probe <temp-evidence-dir>

마지막 세 명령은 실제 Windows Qt CI에서 실행한다. 해당 Windows CI의 PNG·JSON 아티팩트는 현재 화면이 단순한 모의 검색/탭 구성인 점을 명시해야 한다.

## 진실성·보호 요구

C024 3/3 PASS는 (1) 상태/데이터/모드 격리 자동 테스트 PASS (2) Windows Qt GUI 탭·버튼·실패 표시 PASS (3) C022 Windows 실제 스크린샷/시험 EXE 회귀 PASS를 각각 확인한 경우에만 인정한다.

실제 사용자 PC의 Windows 10/11 설치형 EXE, 실제 Wikimedia/Archive/Pexels/Pixabay 검색, 180초 원본 확인·4K 실파일 검증·적합도, 썸네일·비디오 재생, 권리 검토, 다운로드·편집은 구현/검증되었다고 표시하지 않는다. UI에서 검색 버튼을 누르면 실 검색 결과 0건으로 속이지 않고 제공처 연결 전이라고 표시한다.

기존 V1.0.2, 사용자 API 키, DB, 영상, D: 드라이브, 백업은 접근하지 않으며 main 및 Draft PR #1의 미병합 상태를 유지한다.

## 2026-11-07 실제 GitHub Actions 수용 증거

**C024 독립 UI/모의 검색 기능 범위: 최종 PASS 3/3점.** 코드 검증 SHA **8482a070a67afb63d8ad28fc92520dd701a4ec3b**.

- 실제 성공 워크플로: https://github.com/1976haru/newvideo/actions/runs/42328565712
- Windows/Ubuntu × Python 3.11/3.12 전체 4개 테스트 job **SUCCESS**, C005 보존 PowerShell **SUCCESS**, Qt Windows 오프스크린 8 PASS, C022 Windows 네이티브 화면/시험 EXE **SUCCESS**. 총 7개 job 전부 성공.
- Windows Python 3.11의 정확한 CI 명령 및 집계:
  - python -m pytest -q -k migration_and_preservation → 26 passed
  - python -m pytest -q tests/test_legacy_regression.py → 26 passed
  - python -m pytest -q tests/test_c020_module_boundaries.py → 21 passed
  - python -m pytest -q -k "security or ssrf or redact" → 81 passed
  - python -m pytest -q tests/test_c022_ci_contract.py → 7 passed
  - python -m pytest -q -k search_mode_isolation → **25 passed, 2 skipped** (Qt 2개는 기본 headless 작업에서 의도적으로 SKIP)
  - python -m pytest -q → **309 passed, 3 skipped, 0 failed**
- Windows Qt 작업 실제 명령:
  - python -m pytest -q tests/test_c011_version_identity.py tests/test_c011_gui.py tests/test_c024_gui_search_modes.py → **8 passed**
  - 별도의 네이티브 Windows 작업 → **C024_WINDOWS_NATIVE_SEARCH_TABS_PASS**, **C022_NATIVE_WINDOWS_GUI_CAPTURE_PASS**, **C022_WINDOWS_ONEDIR_TRIAL_PACKAGE_PASS**, **C022_WINDOWS_PACKAGED_NATIVE_GUI_PASS**
  - 테스트 로그는 **C024_LIVE_SOURCE_SEARCH: SKIP_NOT_IMPLEMENTED**도 명시.
- 스크린샷 및 JSON 증빙(네이티브 QWidget/Windows HWND + 패키징된 trial EXE): https://github.com/1976haru/newvideo/actions/runs/42328565712/artifacts/13555873339
  - GitHub artifact ID **13555873339**, 7개 파일, 73,447 압축 바이트, 실제 업로드 확인.
  - 화면 캡처/GUI 시험은 **시범 탭의 표시** 증거이며 실제 출처 검색의 네트워크 성공이나 R2 비디오 재생 증거가 아니다.

**완료 체크리스트:** C024가 3/3으로 완료되어 확인된 완료 항목 **18/162개 = 약 11.1% (항목 수 기준)**. 가중치 기반 제품 완성률은 아직 산출하지 않는다. `main`과 기존 V1.0.2 데이터/API 키는 변경하지 않았으며 Draft PR #1 미병합 유지.
