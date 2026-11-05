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
$url = "https://raw.githubusercontent.com/1976haru/newvideo/de7f3d1135f3aec1b8db570b7bd041992ab3d186/tools/C011_Run_V2_Trial.ps1"
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
