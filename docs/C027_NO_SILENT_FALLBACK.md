# C027 — 장편 원본 검색 결과 0건의 정확한 안내와 수동 대안 전환

**체크리스트:** C027 / R1_원본·클립검색 / P0 / 3점.
**코드·Windows CI 검증:** PASS 3/3점 (2026-11-07).
**사용자 실제 Windows PC C027 조작:** NOT_TESTED (단일 기존 V2 설치본에서 확인 대기).
**검증 코드 SHA:** `504aa0d02930bc235a790dd889e7409fe553ce30`.
**CI:** https://github.com/1976haru/newvideo/actions/runs/42346058776
**Windows 네이티브 GUI/시험 EXE 증빙:** https://github.com/1976haru/newvideo/actions/runs/42346058776/artifacts/13563528250

## 수용 기준과 기능

1. **진짜 장편 원본 0건:** 하나 이상의 장편 지원 제공처가 성공(OK)했고, 오류인 장편 제공처가 없으며, 요청된 최소·최대 길이/원본 증빙 필터를 통과한 후보가 하나도 없으면 `LaneStatus.EMPTY`, 결과 수 `0건`. 장편 탭은 그대로 유지된다. 예: 3분 이상 원본 검색에 60초 영상만 나온 경우.
2. **대안 안내:** 선택한 원본 길이(기본 3분, 최대 길이를 지정했다면 해당 범위)를 포함한 0건 안내, 검색어·길이·화질을 바꿔 보라는 제안과 **짧은 영상 조합 탭 직접 열기** 버튼 표시.
3. **수동 이동만:** 별도 `longNoResultsAlternative` 버튼 클릭 전에는 `active_mode=LONG_ORIGINAL`, 다른 탭 결과·검색 상태가 보존된다. 버튼 클릭은 화면 탭 이동만 수행하고 짧은 클립 요청/다운로드/자동 혼합을 실행하지 않는다.
4. **확인 불가능한 경우 구분:** 아무 제공처도 없거나 모든 장편 제공처가 모드 미지원이면 `UNAVAILABLE`, 실패·타임아웃·무효 응답만 있다면 `FAILED`; 두 경우 결과 수는 0이 아닌 `확인 불가`이고 대안 CTA도 표시되지 않는다. 일부 성공하고 일부 실패한 경우는 `PARTIAL`, `0건 (부분 결과·전체 미확인)`이며 확정 0건 CTA가 나오지 않는다.
5. **C027 오프라인 0건 화면 검사:** 실사용 V2 시험판은 실제 공식 제공처 어댑터가 아직 미연결이므로, `C027 오프라인 0건 화면 검사` 버튼을 제공. 단일 코드 경로의 `EMPTY` 화면/대안 버튼을 보여주지만 결과 수는 명확히 `0건 (오프라인 테스트)`, 안내는 `실제 제공처 검색 아님`. 사용자 데이터를 읽거나 API를 호출하지 않는다. 다음 일반 검색을 누르면 모의 화면은 사라지고, 기존 정상 미연동 `확인 불가` 상태로 되돌아간다.
6. **C024/C025/C026 보존:** 모드별 독립 검색·정렬·건수, ≥180초 원본/조합 180초 차단, 3·10·20·30분 및 최대 길이 필터, 짧은 클립 5~120초 범위 그대로 유지.

## 수정 파일

- `src/nature_video_studio/search_mode_state.py` — 확인된 0건 대안 문구·부분 결과 0건 의미 구분·`offline_zero_demo` 상태, 새 검색 때 모의 상태 초기화.
- `src/nature_video_studio/search_tabs.py` — 실 0건 상태에만 나타나는 `짧은 영상 조합 탭 직접 열기` 버튼 및 `C027 오프라인 0건 화면 검사` 버튼. 모드 전환은 직접 클릭할 때만 발생. 미연동/실패/부분 0건은 CTA 숨김.
- `tests/test_c027_no_silent_fallback.py` — 실제 성공·확정 0건, 제공처 실패·미지원·일부 실패, 길이 미달/조합 거부, 다른 탭 독립 보존, 오래된 응답 무시, 명시적 전환만.
- `tests/test_c027_gui_no_silent_fallback.py` — Windows Qt GUI의 0건 안내·대안 CTA 표시/클릭/독립 검색·미연동 복귀·부분 결과 처리.
- `tools/c022_windows_gui_probe.py` — 실제 Windows 네이티브 HWND 검사에서 0건 모의 화면·사용자가 직접 전환 클릭·실 제공처 미연동 복귀 확인, 실화면 캡처·시험 EXE 회귀 보존.
- `.github/workflows/ci.yml` — Windows/Ubuntu × Python 3.11/3.12의 독립 `pytest -k no_silent_fallback` Gate, Windows Qt 전용 테스트와 native EXE 회귀.

## 재현 가능한 테스트·PASS 범위

성공한 GitHub Actions run: https://github.com/1976haru/newvideo/actions/runs/42346058776, SHA `504aa0d02930bc235a790dd889e7409fe553ce30`; 7/7 jobs SUCCESS.

실제 Windows Python 3.11 로그:

    python -m pytest -q -k no_silent_fallback
    # 20 passed, 3 skipped (Qt GUI 3건은 별도 전용 Windows GUI job)
    python -m pytest -q
    # 386 passed, 9 skipped, 0 failed
    python -m pytest -q tests/test_c011_version_identity.py tests/test_c011_gui.py tests/test_c024_gui_search_modes.py tests/test_c025_gui_self_check.py tests/test_c026_gui_duration_presets.py tests/test_c027_gui_no_silent_fallback.py
    # Windows Qt: 14 passed

네이티브 Windows `tools.c022_windows_gui_probe` 로그:
- `C027_WINDOWS_NATIVE_NO_SILENT_FALLBACK_PASS`
- `C027_LIVE_ZERO_RESULT_SEARCH: SKIP_PROVIDER_NOT_CONNECTED`
- `C022_NATIVE_WINDOWS_GUI_CAPTURE_PASS`
- `C022_WINDOWS_ONEDIR_TRIAL_PACKAGE_PASS`
- `C022_WINDOWS_PACKAGED_NATIVE_GUI_PASS`

첫 시도 `67446834`는 기존 C024 수용 테스트가 검사하던 `짧은 영상은 자동 대체하지 않습니다` 문구가 바뀌어 1 FAIL. 해당 안내를 **유지**하면서 새 문구를 추가한 `504aa0d0`에서 전체 CI 재실행 7/7 PASS. 앞선 실패 은폐 금지.

## 사용자 PC에서 한 번만 실행하는 기존 V2 안전 업데이트

1. 먼저 현재 실행 중인 V2 창을 닫는다.
2. 일반 권한 PowerShell에 아래 한 줄을 붙여넣는다. **새 사용자용 프로그램 폴더를 생성하지 않는다**.

       powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\NVS_V2_Trial_App\C011_Titlebar_10206483\NVS_V2_Updater.ps1' -Mode Update -TargetCommit '504aa0d02930bc235a790dd889e7409fe553ce30'

3. `NVS_V2_EXISTING_INSTALL_UPDATE_PASS`와 `ACTIVE_COMMIT: 504aa0d02930bc235a790dd889e7409fe553ce30` 확인 후 기존 V2가 실행되면 **3분 이상 원본** 탭에 남아 있는다.
4. **C027 오프라인 0건 화면 검사** 클릭. `이 탭의 결과: 0건 (오프라인 테스트)` 및 대안 안내와 `짧은 영상 조합 탭 직접 열기` 버튼이 보이되, 클릭 전에는 장편 탭에 머무르는지 확인한다.
5. 직접 `짧은 영상 조합 탭 직접 열기` 클릭 → 짧은 탭으로 이동하지만 **이 탭의 결과: 미검색**인 상태인지 확인한다. 짧은 클립 검색은 자동으로 실행하지 않는다.
6. 장편 탭으로 돌아온 뒤 검색창에 `호수` 입력하고 `이 탭 검색` 클릭 → 실제 검색 제공처가 아직 연결되지 않았다는 안내, `이 탭의 결과: 확인 불가`, 0건 대안 버튼 숨김 상태인지 확인한다.
7. 결과가 정상이면 **`C027 정상`**이라고 회신한다. 오류라면 스크린샷/PowerShell 출력 공유.

## 점수와 아직 안 된 일

- C027 **코드·모의 API·Windows GUI/시험 EXE 범위 PASS 3/3**, 사용자 실제 PC의 버튼 클릭 검사는 별도 확인 대기. 새로운 체크리스트 항목은 생성하지 않음.
- 실 제공처(Wikimedia Commons/Internet Archive 등)의 진짜 0건 검색 결과는 아직 확인하지 못함. 전체 공식 API 어댑터 미연결; `C027 오프라인 0건 화면 검사`는 **오프라인 합성 화면으로 실 검색 결과를 만들었다고 주장하면 안 됨**.
- R1 실제 원본 길이 증빙, ffprobe 실파일 해상도, R2 썸네일·실재생, R3 권리·다운로드, R4 조합, R5 정식 EXE/Windows 실환경 설치 테스트는 별도 미완료.
- 기존 단일 V2 코드·복원 사본만 같은 경로에 유지. V1.0.2 프로그램·D:\NatureVideoStudio 데이터·OS API 비밀키·복구 데이터는 수정 대상이 아니며 로컬 디스크 변경 전후 해시 직접 검증을 주장하지 않음.
- 체크리스트 개수 기준 완료 **21/162개 = 약 13.0%** (가중 제품 완성률 아님). `feature/v2-research-rebuild` 브랜치·Draft PR #1 유지, `main` 변경 없음.
