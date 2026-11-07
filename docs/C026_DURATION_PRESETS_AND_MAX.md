# C026 — 장편 원본 3·10·20·30분 프리셋과 독립 최대 길이

**구분:** R1 원본·클립검색 / P0 / C026 (2점).
**코드·Windows CI 수용 범위:** PASS 2/2점 (2026-11-07).
**실제 사용자 PC 조작 확인:** 아직 NOT_TESTED — 동일 V2 기존 설치본 갱신 후 직접 확인이 필요.
**코드 검증 SHA:** `271d0ea611341a3890dbcf7fc2ceb41745273733`.
**공개 CI:** https://github.com/1976haru/newvideo/actions/runs/42340359232

## 요구사항과 구현

| 항목 | 구현 및 UI | 근거 |
| --- | --- | --- |
| 기본 3분 | 장편 원본 탭의 최소 길이 **3분 이상**이 초기 선택, 실제 값 **180초** | `LONG_DURATION_PRESETS_SECONDS`; GUI `longMinDurationPreset` |
| 10분 | **10분 이상** → 600초 | 위와 같음 |
| 20분 | **20분 이상** → 1,200초 | 위와 같음 |
| 30분 | **30분 이상** → 1,800초 | 위와 같음 |
| 최대 길이 별도 지정 | `최대 길이 제한` 체크박스와 분 단위 `QSpinBox` (1~1,440분), **기본 해제**. 체크 시 설정한 최대 길이를 초로 변환. 최소 프리셋을 바꿔도 최대값이 임의로 변경되지 않음 | `longMaxDurationEnabled`, `longMaxDurationMinutes` |
| 조건 전파 | 버튼 클릭 시 `SearchTicket.criteria`에 최소·최대(또는 None) 포함하여 `SearchQuery`→`SearchCoordinator`→`SourceAdapter` 비동기 검색 경로로 전달 | `SearchModeSession.begin_search()`, `search_tabs._SearchThread` |
| 필터링 | 확인된 원본 중 `min <= duration <= max` (최대 없으면 상한 없음). 원본 길이 미확인, 180초 미만, 조합 영상은 여전히 제외. 모의 코디네이터가 필터를 건너뛰어도 GUI의 모드 상태 수신 단계에서 **동일한 ticket.criteria**로 다시 필터 | `filtering.duration_reason`, `search_mode_state.finish_search` |
| 부적합 범위 | 최대가 최소 미만이면 검색 전에 `ValueError`로 거부; 화면에 **길이 조건 오류** 표시; 기존 결과/검색 번호 변경 없음 | `SearchCriteria`, `SearchModeSession`, GUI `request_search` |
| 모드 분리 | 짧은 영상 조합 탭은 해당 길이 프리셋의 영향을 받지 않음; 다른 탭의 검색어·정렬·검색 건수 보존 | C024 계약 유지 |
| 정직한 미연동 안내 | 실제 제공처 SourceAdapter가 연결되지 않은 시범 UI에서 검색을 누르면 **연결되지 않았습니다** 상태, 결과 수는 확인 불가. 선택한 조건이 실제 원격에서 실행됐다고 주장하지 않음 | `SearchTabsWidget(coordinator=None)` |

길이 프리셋은 사용자 입력의 기본 목적에 맞춘 **검색 요청·필터 조건**이며, 다운로드된 원본의 실제 길이·촬영 4K·저작권/상업적 재사용 승인은 아직 검증하지 않았다.

## 변경 파일 (총 6개)

- `src/nature_video_studio/search_mode_state.py` — 4개 프리셋 상수와 독립 최대 길이 상태, 검색 요청 전달, 최대/최소 검증, 실제 요청별 정확한 필터.
- `src/nature_video_studio/search_tabs.py` — 장편 탭에 최소 프리셋 콤보·최대 길이 체크박스·분 입력·현재 선택 조건/오류 문구.
- `tests/test_c026_duration_presets.py` — 180·600·1200·1800초 경계, 최대값 포함, 길이 미확인·조합 영상 제외, 오류시 이전 상태 보존, mock SourceAdapter 요청 및 필터.
- `tests/test_c026_gui_duration_presets.py` — Windows Qt GUI에서 네 프리셋/상한 조작, 독립 상태, 잘못된 범위 표시, 비동기 모의 API 검색값과 결과 수 확인.
- `tools/c022_windows_gui_probe.py` — Windows 네이티브 화면 캡처 시 4개 초 프리셋·기본 최대 제한 해제·입력 위젯 존재 검사.
- `.github/workflows/ci.yml` — Windows/Ubuntu Python 3.11/3.12에 `pytest -k duration_preset` 별도 Gate, Windows Qt 전용 작업에 C026 GUI 테스트 포함.

## 검증 결과 (실제 GitHub Actions run 42340359232)

**워크플로 7개 job 전부 SUCCESS.** Windows·Ubuntu × Python 3.11·3.12 매트릭스 4개 PASS, 기존 C005 PowerShell 보존 테스트 PASS, Windows Qt 위젯 시험 PASS, Windows 네이티브 화면 캡처·시험용 PyInstaller onedir EXE PASS.

실제 Windows Python 3.11 테스트 로그:

    python -m pytest -q -k duration_preset
    # 25 passed, 2 skipped (Qt 전용 2개는 별도 Windows Qt job에서 수행)

    python -m pytest -q
    # 366 passed, 6 skipped, 0 failed

    python -m pytest -q tests/test_c011_version_identity.py tests/test_c011_gui.py tests/test_c024_gui_search_modes.py tests/test_c025_gui_self_check.py tests/test_c026_gui_duration_presets.py
    # Windows Qt job: 11 passed

추가 검사: **C026_WINDOWS_NATIVE_DURATION_PRESETS_PASS**, **C022_NATIVE_WINDOWS_GUI_CAPTURE_PASS**, **C022_WINDOWS_ONEDIR_TRIAL_PACKAGE_PASS**, **C022_WINDOWS_PACKAGED_NATIVE_GUI_PASS**. 실 제공처 검색은 로그에서 **C026_LIVE_PROVIDER_FILTER: SKIP_NOT_CONNECTED**로 별도 표시.

Windows 네이티브 GUI 화면·시험 EXE 증빙 PNG/JSON 7개 업로드:

https://github.com/1976haru/newvideo/actions/runs/42340359232/artifacts/13561282902

## 사용자 PC 동일 V2 설치본 업데이트와 확인

**현재 사용자 기존 V2 시험판(기존 단일 위치)**

    D:\NVS_V2_Trial_App\C011_Titlebar_10206483

**사용자가 할 일:**
1. 현재 V2 창을 닫는다. 기존 V1.0.2 프로그램을 건드리지 않는다.
2. 일반 권한 PowerShell에서 아래 명령을 실행한다. 새 프로그램 설치 폴더를 만들지 않는다.

       powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\NVS_V2_Trial_App\C011_Titlebar_10206483\NVS_V2_Updater.ps1' -Mode Update -TargetCommit '271d0ea611341a3890dbcf7fc2ceb41745273733'

3. `NVS_V2_EXISTING_INSTALL_UPDATE_PASS`, `ACTIVE_COMMIT: 271d0ea611341a3890dbcf7fc2ceb41745273733`을 확인한다. 기존 프로그램이 실행된다.
4. **3분 이상 원본 탭**에서 기본 3분을 확인하고 10/20/30분 프리셋을 각각 선택해 본다.
5. `최대 길이 제한`을 체크하고 `20분`으로 입력한 뒤 최소 10분을 선택한다. 화면에 **선택 조건: 10~20분**이 나타나는지 확인한다.
6. 검색어 `호수`를 입력하고 `이 탭 검색` 클릭 시 제공처 미연동 안내가 나타나는지 확인한다 (아직 실 검색 없음).
7. 최대 20분을 유지하고 최소 30분을 선택하면 **조건 오류**가 표시되는지 확인한다. 체크 해제 시 **30분 이상 / 최대 제한 없음**이 정상으로 표시되는지 확인한다.
8. 짧은 영상 조합 탭으로 넘어갔다가 다시 장편 탭으로 돌아왔을 때 입력값이 유지되는지 확인한다. 스크린샷이나 `C026 정상` 응답으로 사용자 PC 검증을 마친다.

업데이터는 기존 V2 설치 폴더의 **프로그램 소스만 교체**하고 종전 소스 백업을 같은 폴더에 둔다. 사용자 영상·DB·API 키·복구 백업을 삭제/초기화하지 않도록 설계했으며 Windows CI의 **합성 기존 설치본**에서 업데이트/롤백과 가상 사용자 파일 비변경을 검증했다. 사용자 개인 DB/키의 사전·사후 해시 직접 검증은 하지 않았다.

## 남은 과제와 점수 범위

- C026 **코드/UI/모의 쿼리·필터/Windows CI 범위 2/2 PASS**; 실제 사용자 PC 조작 확인은 별도 **대기**.
- R1 실 제공처 API 장편 180초 메타데이터 신뢰 검증·원본 적합성·4K 실파일 검증 미구현. 따라서 GUI 미연동 메시지는 정상.
- R2 실제 미리보기·재생, R3 선택 다운로드·권리 증빙, R4 합성, R5 설치형 EXE·개별 사용 데이터 보존 모두 후속 수용 Gate.
- 완료 체크리스트 항목 수 기준 **20/162개, 약 12.3%** (기능별 가중 진행률 미산출). Draft PR #1 유지, `main` 미수정, 기존 V1.0.2 설치·데이터 미접근.
