# C011 — V1/V2 버전 식별 및 시험판 타이틀바

**상태:** V2 시험판 Qt 창·명시적 버전 표시 구현. 실제 사용자의 Windows 타이틀바 캡처는 **대기**, V1.0.2 기존 프로그램은 절대 변경하지 않았음.

## V2 타이틀바/화면 규격

- 창 타이틀: `[V2 시험판] Nature Video Studio v2.0.0.dev0 | 기존 V1.0.2 아님`
- 창 내부: `Nature Video Studio v2.0.0.dev0 · 시험판`
- 경고문: `이 창은 V2 개발·검증용 화면입니다.` 및 V1 데이터 보존/검색·다운로드·재생·편집 미연동 명시.
- `__version__`을 하나의 버전 출처로 사용하며, `AppIdentity`가 타이틀·내부 라벨 생성.
- 현재 GUI는 **버전 검증 전용 최소 실행 화면**으로서 V2 검색·재생·다운로드 완성을 뜻하지 않음.
- 앱은 시작할 때 QSettings, 키링, SQLite, 다운로드 폴더에 접근하지 않음. C007의 V2 별도 앱 폴더만 설치 스크립트에서 사용. 기존 V1.0.2 코드·DB·캐시·보안 키·기존 설치 폴더는 전혀 수정하지 않음.

## 실제 Windows 사용자 스크린샷 시험

기존 V1.0.2는 그대로 유지합니다. C011 V2 시험판을 처음 설치/실행할 때:

```powershell
$script = "$env:TEMP\NVS_C011_Run_V2_Trial.ps1"
$url = "https://raw.githubusercontent.com/1976haru/newvideo/6d07ff33b0be05738a433a031fe4adc730cf36d3/tools/C011_Run_V2_Trial.ps1"
Invoke-WebRequest -Uri $url -OutFile $script -UseBasicParsing
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script
```

- 기존 V1 실행 폴더: `D:\03 자연풍경 비디오\NatureVideoStudio_V1_0_2`. 원본 V1.0.2에 손대지 않음.
- 새로 생성할 V2 전용 경로: `D:\NVS_V2_Trial_App\C011_Titlebar_10206483`. 기존 경로가 있으면 안전하게 중단(덮어쓰기 없음).
- 스크립트는 GitHub에 고정된 `10206483d704af57e3c13df2b58b4e1548f66163` 소스를 다운로드하여 새로운 가상환경에 PySide6를 설치함. 인터넷 연결 및 사용자 PC에 Python `py -3`가 있어야 함. **실행형 EXE가 아닌 개발용 시범 창**임.
- GUI가 열리면 **Windows 제목 표시줄 전체와 내부 시험판 문구가 보이게** 캡처. 기존 V1 실행창 제목도 별도 캡처. V1 키/계정/개인 폴더 등이 화면에 노출되면 가림 처리.
- 설치·실행 실패 시 기존 V1을 수정하거나 API 키를 재입력하지 말 것. 오류만 공유해 재검증.
- 타이틀에 V2 버전/시험판 여부가 정확히 보이고 V1과 혼동되지 않을 때만 C011 **1/1 PASS**. V1 타이틀이 버전을 표시하지 않는다면 그 사실을 증거로 남기고 V1 수정 없이 호환 가능한 표기 전략을 새로 설계해야 함.

## 자동 테스트

- `python -m pytest -q` — 버전 식별·시험판 경고 문자열 단위 테스트.
- 전용 Windows GUI CI(별도 job): `python -m pip install -e ".[dev,gui]"`, `python -m pytest -q tests/test_c011_version_identity.py tests/test_c011_gui.py`, `python -m nature_video_studio --smoke` with `QT_QPA_PLATFORM=offscreen`.
- `--smoke`는 Qt 위젯과 창 제목을 검사하되 Windows 실제 타이틀바 캡처의 대체가 아님.
- 최종 실제 Windows UAT 스크린샷은 사용자 캡처로 증빙.

## C011 미완료/별도 승인 항목

1. V1 실물 타이틀바 화면 확인 — 이전 V1 소스 수정·재설치 금지.
2. 사용자 PC에 표시되는 V2 시험판 타이틀바 캡처 — 현재 미확인.
3. 향후 V2 정식 버전 표시는 개발/시험판 꼬리표를 제거하되, 릴리스 검증 전에는 절대 정식판으로 표기 금지.

## GitHub Actions 검증 증거 — 2026-11-06

- 검증된 코드 SHA: `f7a0cb8aad0536f8af4cbbd1b6f95e9b22eed898`.
- CI 실행 기록: https://github.com/1976haru/newvideo/actions/runs/42117366964
- `python -m pytest -q`: Windows 3.11/3.12, Ubuntu 3.11/3.12 각 **124 PASS, 1 SKIP, 0 FAIL**. SKIP은 기본 환경에서 별도의 Windows 전용 Qt 실행 검사를 중복 실행하지 않기 위한 조건부 테스트.
- Windows 전용 GUI job: `python -m pytest -q tests/test_c011_version_identity.py tests/test_c011_gui.py` → **6 PASS**, `python -m nature_video_studio --smoke` → `C011_GUI_SMOKE_PASS`, PowerShell 5.1 설치 스크립트 **문법 검사 PASS**(`C011_INSTALLER_PARSE_PASS`).
- `QT_QPA_PLATFORM=offscreen` 검사이므로 Windows 사용자 화면의 **네이티브 타이틀바 스크린샷은 아직 SKIP**.
- 사용자의 Windows V1.0.2 타이틀바 문구도 실제 캡처로 확인되지 않았음. V1 원본 코드는 그대로 보존.
- **C011 최종 1/1점은 사용자 Windows 캡처 확인 후 부여**.

## 사용자 실제 Windows 실행 증빙 — 2026-11-06

**C011 설치/실행 PASS; 실제 타이틀바 캡처 대기 (최종 1/1점은 보류).**

사용자가 다음과 같이 검증된 스크립트(`6d07ff33b0be05738a433a031fe4adc730cf36d3`)를 PowerShell로 실행함:

```powershell
$script = "$env:TEMP\NVS_C011_Run_V2_Trial.ps1"
$url = "https://raw.githubusercontent.com/1976haru/newvideo/6d07ff33b0be05738a433a031fe4adc730cf36d3/tools/C011_Run_V2_Trial.ps1"
Invoke-WebRequest -Uri $url -OutFile $script -UseBasicParsing
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script
```

사용자가 제출한 실제 핵심 출력:

```text
C011_NEW_V2_TRIAL_FOLDER_CREATED: True
C011_DOWNLOADING_PINNED_SOURCE
C011_CREATING_ISOLATED_VENV
C011_INSTALLING_PYSIDE6_IN_ISOLATED_VENV
Successfully installed PySide6-6.12.0 ...
C011_GUI_SMOKE_START
C011_GUI_SMOKE_PASS
TITLE_UNICODE_ESCAPE: [V2 \uc2dc\ud5d8\ud310] Nature Video Studio v2.0.0.dev0 | \uae30\uc874 V1.0.2 \uc544\ub2d8
WINDOW_OBJECT_NAME: NVS_V2_TRIAL_WINDOW
V1_DATA_READ_OR_WRITTEN: False
REAL_WINDOWS_TITLEBAR_CAPTURE: SKIP_NOT_RUN
C011_OPENING_V2_TITLEBAR_WINDOW
C011_V1_PROGRAM_AND_DATA_UNMODIFIED_BY_INSTALLER_DESIGN
C011_TRIAL_RUN_COMPLETE
```

**확인된 사실:** Windows에서 별도 V2 시험 디렉터리 생성 및 격리 Python 가상환경/PySide6 설치가 완료됐고, Qt 스모크 테스트 후 실제 V2 창 진입·종료 경로가 정상 종료했다. 버전 식별 표시 문자열은 V1.0.2를 명확히 구분한다.

**아직 확인되지 않은 사항:** 실제 Windows 제목 표시줄에 표시된 문구의 스크린샷, V1.0.2 실제 창 제목과의 비교, V1 파일/DB 실행 전후 독립적 SHA256 검증. `V1_DATA_READ_OR_WRITTEN: False`는 프로그램이 출력한 설계상 진술이지 원본 디스크/보안 저장소를 독립 계측한 결과가 아니다.

C011 최종 1/1 PASS는 사용자의 제목 표시줄 및 시험판 경고문 화면 캡처 확보 후 판정한다. 기존 C009/C010의 V1 무변경 증거는 **이번 V2 시험창 실행 이전 시점**의 증빙이며 이후 해시를 재검사한 것이 아니다. 별도 동작 검증이 필요한 C007/C009/C010 전체 완료로 확장해 해석하지 않는다.

## Actual user Windows screenshot acceptance — 2026-11-06

**C011 FINAL PASS — 1/1 point for the scoped V2 identity/titlebar acceptance.**

The user provided a screenshot from the actual Windows PC, filename `08.JPG` in conversation (not uploaded to GitHub, since it includes a desktop environment). The screenshot visibly shows:

- Native window titlebar: `[V2 시험판] Nature Video Studio v2.0.0.dev0 | 기존 V1.0.2 아님`.
- In-window heading: `Nature Video Studio v2.0.0.dev0 · 시험판`.
- Korean warning: `이 창은 V2 개발·검증용 화면입니다.`, notice that existing V1.0.2 program/data are not changed, and disclosure that search, download, playback, and editing are not yet connected.
- Normal Windows titlebar controls and readable, uncut labels.

These user-provided image observations supplement the prior real Windows console output `C011_GUI_SMOKE_PASS`, `C011_OPENING_V2_TITLEBAR_WINDOW`, `C011_TRIAL_RUN_COMPLETE` and passing Windows CI Qt tests. **C011 V2 trial labeling is now fully accepted (1/1)**, with no false claim of a complete V2 application.

Evidence boundaries: Screenshot of *original V1.0.2 window titlebar* is not included; V1 itself was not modified, and its prior exact title remains unverified. The screenshot alone does not independently prove no V1 DB writes or API key changes; keep C007/C009/C010 parallel-run, credential reuse, and rollback gates open. The screenshot is not distributed or committed to avoid exposing user desktop information.

**Remaining program work:** V2 search/preview/download GUI and packaging, plus separate actual V1/V2 user-data safety checks. C011 passage does not advance those unfinished milestones.
