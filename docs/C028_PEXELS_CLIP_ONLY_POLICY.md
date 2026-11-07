# C028 — Pexels 업로드 상한 120초: 클립 전용/장편 후보 추천 제외

**체크리스트:** C028 / R1_원본·클립검색 / P0 / 2점.
**검증 코드 커밋:** `69fdaf82afb1f7365d917fa0493faeeeaf1091d7`.
**GitHub Actions:** https://github.com/1976haru/newvideo/actions/runs/42348193787 — Windows·Ubuntu × Python 3.11·3.12 테스트, Qt GUI, 실제 Windows 화면 캡처, 시험용 EXE, 모의 업데이트/복원 7/7 jobs SUCCESS.
**사용자 PC 실행:** C028 로컬 버튼/문구 확인은 **NOT_TESTED**, 업데이트·직접 확인 대기.
**공식 출처:** [Pexels 공식 도움말 — 영상 업로드 요건](https://help.pexels.com/hc/en-us/articles/360042795133-What-are-the-requirements-for-uploading-videos), 마지막 갱신 **2026-10-04**, 검토 **2026-11-07**. 업로드 최소 5초, **최대 2분(120초)**. 이는 **업로드 정책**이며, 개별 과거 게시물의 실파일 길이·적법성·재사용 허락을 자동 입증하지 않는다.

## 구현 및 수용

| 기준 | 구현 | 검증 |
|---|---|---|
| Pexels 장편 공급처 추천 제외 | `src/nature_video_studio/provider_policy.py`가 제공처 'Pexels' 및 공식 명칭 변형에 장편 원본 지원을 허용하지 않음. 어댑터가 실수로 장편 모드를 선언해도 **API 요청 전에 제외** | `SearchCoordinator`의 `supports_mode(...)` 검증 |
| 잘못된 180초 Pexels 결과 차단 | 부정확한 외부 메타데이터나 모의 코디네이터가 180·600·1,800초 Pexels를 반환해도 `filtering.duration_reason`이 Pexels 장편 원본을 거절하고 GUI 검색 상태도 최종 필터에서 재거절함 | 장편·GUI 상태 필터 테스트 |
| Pexels는 짧은 클립 전용 | `SHORT_COMPOSER`에서 길이 확인된 **5~120초**만 통과. 5·120초 포함, 4.999·120.001초 제외. 길이 미확인·조합은 기존 C025 정책대로 거절 | `pytest -k pexels_lane` |
| GUI 제공처 정책을 명확히 표시 | 장편 탭: `Pexels는 ... 최대 120초 ... 장편 원본 공급처에서 제외`. 짧은 탭: `Pexels는 5~120초 짧은 클립 전용 후보`. 둘 다 `실제 제공처 미연결` 표시. 짧은 탭에 **상업 재사용 별도 권리 검토** 안내 | Windows Qt 및 네이티브 화면 검사 |
| 자동 대체 없음 | Pexels만 연결된 모의 환경에서 장편 검색은 `MODE_UNSUPPORTED`, `UNAVAILABLE`/확인 불가; 클립 탭 자동 전환·자동 검색 없음. 실제 해당 탭의 사용자 검색 요청만 Pexels 소스 호출 | 모의 Provider + C024/C027 회귀 |
| 중립적인 다른 출처 | Wikimedia Commons/Internet Archive 등 다른 장편 원본 후보를 Pexels 제한 때문에 차단하지 않음. 단, 실제 제공처 어댑터는 아직 GUI에 미연동 | fake adapter 테스트 |

## 수정 파일 (8개 + 문서)

- `src/nature_video_studio/provider_policy.py` — Pexels 식별·최소/최대·출처 URL·지원 검색 모드·두 탭 안내.
- `src/nature_video_studio/filtering.py` — Pexels를 180초 이상 연속 원본 후보로 승인하지 않는 최종 길이 정책.
- `src/nature_video_studio/search_coordinator.py` — 검색 전 정책적 기능 지원 검증으로 잘못된 Pexels 장편 API 호출 차단.
- `src/nature_video_studio/search_tabs.py` — '장편 제외'와 '5~120초 클립 전용' 안내를 해당 탭에 별도 표시.
- `tests/test_c028_pexels_lane.py` — 정책값·Pexels 이름 변형·진입 차단·모의 소스·시간 경계·오인된 180초 차단.
- `tests/test_c028_gui_pexels_lane.py` — 실제 Windows Qt UI에서 두 탭 정책·상태·수동 이동 검증.
- `tests/test_c020_module_boundaries.py` — 신규 **순수 정책 모듈**을 C020 검색 서비스 허용 의존성에 추가. 오래된 C020 오류 응답 fixture를 장편 지원 소스인 Internet Archive로 바꾸어, 잘못된 제공처 응답에 대한 원래 테스트 의미를 유지.
- `tools/c022_windows_gui_probe.py` — Windows 네이티브 화면에서 정책 표시·실 Pexels API 미연결 검사.
- `.github/workflows/ci.yml` — Windows·Linux `pytest -k pexels_lane` 독립 Gate 및 Windows Qt 전용 GUI 테스트 포함.

## 정확한 실행 명령과 증거

GitHub Actions 성공 코드 SHA `69fdaf82afb1f7365d917fa0493faeeeaf1091d7`, workflow run 42348193787 — **7/7 SUCCESS**.

Windows Python 3.11 CI 로그:

    python -m pytest -q -k pexels_lane
    # 46 passed, 1 skipped (Qt 전용 GUI는 Windows Qt 별도 job)

    python -m pytest -q
    # 432 passed, 10 skipped, 0 failed

    python -m pytest -q tests/test_c011_version_identity.py tests/test_c011_gui.py tests/test_c024_gui_search_modes.py tests/test_c025_gui_self_check.py tests/test_c026_gui_duration_presets.py tests/test_c027_gui_no_silent_fallback.py tests/test_c028_gui_pexels_lane.py
    # Windows Qt 별도 job: 15 passed

Windows 네이티브 증빙:
- `C028_WINDOWS_NATIVE_PEXELS_CLIP_ONLY_PASS`
- `C028_LIVE_PEXELS_API_SEARCH: SKIP_NOT_CONNECTED`
- `C022_NATIVE_WINDOWS_GUI_CAPTURE_PASS`
- `C022_WINDOWS_ONEDIR_TRIAL_PACKAGE_PASS`
- `C022_WINDOWS_PACKAGED_NATIVE_GUI_PASS`

Windows 이미지·패키징 증빙: https://github.com/1976haru/newvideo/actions/runs/42348193787/artifacts/13565020359

**수정 이력 공개:** 첫 코드 커밋 `94c76c24`는 C020 구형 테스트가 Pexels 장편 요청을 허용할 것으로 기대하여 2 FAIL(의존성 허용 목록, 오류 결과 fixture). `69fdaf82`에서 C020의 본래 무효 응답 경계 테스트를 유지하는 방식으로 fixture를 조정했고, C028의 Pexels 장편 차단은 별도 테스트로 증명. 이후 전체 7/7 PASS.

## 사용자 PC 같은 V2 설치본 업데이트·검증

**기존 V2 위치를 그대로 사용**: `D:\NVS_V2_Trial_App\C011_Titlebar_10206483`. **새 설치 폴더 생성 금지**, V1.0.2 앱/DB/키/영상/복구 백업 자동 수정·삭제 금지.

1. 실행 중인 V2 창을 닫는다.
2. **일반 권한** PowerShell에 한 줄 붙여넣기:

       powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\NVS_V2_Trial_App\C011_Titlebar_10206483\NVS_V2_Updater.ps1' -Mode Update -TargetCommit '69fdaf82afb1f7365d917fa0493faeeeaf1091d7'

3. `NVS_V2_EXISTING_INSTALL_UPDATE_PASS` 및 `ACTIVE_COMMIT: 69fdaf82afb1f7365d917fa0493faeeeaf1091d7` 확인, 기존 V2 시험판 자동 실행.
4. **3분 이상 원본 탭**에 'Pexels ... 최대 120초 ... 장편 원본 공급처에서 제외' 안내가 보이는지 확인.
5. **짧은 영상 조합 탭**으로 직접 이동하여 'Pexels ... 5~120초 ... 클립 전용', '실제 제공처 미연결', '상업적 재사용 별도 권리 검토'가 표시되는지 확인.
6. 짧은 영상 탭에서 `호수` 검색을 누르면 현재 **검색 제공처 미연결·확인 불가**가 나오는지 확인. **실제 API 검색 아님.**
7. 양쪽의 설명이 정상이라면 `C028 정상`이라고 회신. 오류라면 PowerShell 출력 또는 화면 캡처 공유.

## 점수·미완료

- C028 **코드/정책·모의 API·Windows Qt/EXE CI 검증 2/2 PASS**, 실제 사용자 PC GUI 검증은 **NOT_TESTED**.
- **실제 Pexels 검색 API 연결·해상도 및 길이 실파일 확인·인물/제3자권리/상업 재사용 판정·합법적 선택 다운로드**는 미완료. 공식 업로드 정책을 확인했다는 이유로 수익화 허가를 주장하지 않는다.
- R1 장편 소스 Wikimedia Commons/Internet Archive 실제 검색, R2 썸네일·동영상 플레이어, R3 권리/다운로드, R4 편집, R5 배포 EXE는 후속 체크리스트.
- C028 포함 체크리스트 항목 수 완료 **22/162개 ≈ 13.6%** (가중 제품 완성률 아님). 개발 브랜치 `feature/v2-research-rebuild`, Draft PR #1 유지, `main` 미수정. 사용자 설치 위치에서 한 번만 업그레이드하고 직접 UI 확인 후 C029.
