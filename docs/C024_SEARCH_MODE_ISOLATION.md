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
