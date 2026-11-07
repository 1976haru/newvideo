# 기존 로컬 V2 프로그램 하나로 계속 업데이트·실행하기

**사용자 승인 운영 방식 (2026-11-07): 체크리스트마다 새 설치 폴더를 만들지 않는다.** 최초 사용자 확인 경로는
`D:\NVS_V2_Trial_App\C011_Titlebar_10206483`이다. 이름은 C011이지만 이 위치에서 C024 및 후속 코드를 갱신한다.

## 1. 지금 PC에서 한 번만 실행할 명령

Windows PowerShell을 일반 권한으로 열고 다음 명령을 한 번에 붙여넣는다.

```powershell
$ErrorActionPreference = 'Stop'
$script = Join-Path $env:TEMP 'NVS_V2_Update_Existing.ps1'
$url = 'https://raw.githubusercontent.com/1976haru/newvideo/fba5aa02615b33dbf33c4b18ad452709264dbe6c/tools/NVS_V2_Update_Existing.ps1'
Invoke-WebRequest -Uri $url -OutFile $script -UseBasicParsing
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -Mode Update
```

**먼저 V2 시험판 창을 닫아야 한다.** 관리자 권한이 필요하지 않다. 로컬 설치/기존 PySide6 격리 가상환경이 확인되지 않거나, 코드 경로가 정해진 V2 경로와 다르면 자동으로 차단한다. 이 사용자 명령은 새 C024 설치 폴더를 만들지 않는다.

업데이트에 필요한 **고정/CI 검증 소스 SHA**는 `501fe01209f2e2a2a75f863e4aa938d56415fdf4`이다. 연결된 GitHub의 해당 고정 소스 ZIP을 안전하게 받아서 기존 V2의 **프로그램 소스 `src`만** 교체한다. 업데이트 전에 새 코드를 임시 디렉터리에서 검증하고 이전 소스를 같은 설치 폴더의 숨겨진 복원용 디렉터리에 보관한다. ZIP 임시 압축파일은 제거한다.

성공 출력:
```text
C011_GUI_SMOKE_PASS
C024_LOCAL_SEARCH_TABS_SMOKE_PASS
NVS_V2_EXISTING_INSTALL_UPDATE_PASS
ACTIVE_COMMIT: 501fe01209f2e2a2a75f863e4aa938d56415fdf4
V1_DATA_KEYS_MEDIA_TOUCHED: NO
```

업데이트 후 자동으로 **기존 V2 프로그램**이 실행된다. 처음에 뜨는 V2 창에서 다음 항목을 직접 클릭해서 검증한다.

1. `3분 이상 원본` / `짧은 영상 조합` 탭 두 개가 존재.
2. 각 탭에 서로 다른 검색어 입력 후 전환 버튼을 눌러도 입력이 유지됨.
3. 장편 기본 정렬 `원본 길이 긴 순`, 단편 기본 정렬 `짧은 컷부터`; 한 탭 정렬 변경이 다른 탭 정렬을 바꾸지 않음.
4. 검색 버튼을 눌렀을 때 `검색 제공처가 아직 연결되지 않았습니다` 등 정직한 `미연동` 안내. 이는 **정상**이며 실제 API 검색은 다음 작업에서 구현.

**사용자 응답은** `C024 로컬 PASS` 또는 화면 스크린샷/오류 메시지 공유. 그 결과가 확인된 뒤 다음 C025에 착수한다.

## 2. 이후 실행은 한 번 클릭

최초 업데이트 후 기존 동일 폴더에 아래 파일이 생성된다.

```text
D:\NVS_V2_Trial_App\C011_Titlebar_10206483\NVS_V2_Start.cmd
```

이 파일을 더블클릭하면 **같은 프로그램**을 실행한다. 새 폴더, 새 가상환경, 새 설치 파일을 만들지 않는다. 이후 체크리스트 기능 수정 후에는 개발 브랜치/CI에서 검증된 고정 SHA로 **같은 updater만 갱신**하여 기존 위치의 코드만 업데이트한다.

## 3. 실패 시와 안전성

- 오류 메시지 `NVS_V2_BLOCKED_*`가 나오면 업데이트를 진행하지 않는다. 명령 출력만 전달하고, V1을 재설치하거나 V1 키를 입력하지 않는다.
- 업데이트 후 C024 탭이 보이지 않거나 비정상 종료가 반복되면 **현재 오류 출력/스크린샷을 먼저 공유**한다. 새 프로그램 폴더를 추가하지 않고 동일 설치본에서 원인 수정한다.
- 이전 코드로 되돌려야 할 때 **최초 성공 업데이트 이후에만**, V2 창을 닫고 다음 명령을 실행할 수 있다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\NVS_V2_Trial_App\C011_Titlebar_10206483\NVS_V2_Updater.ps1' -Mode Rollback
```

이 명령은 현재 사용자 V2 코드를 같은 설치 위치 안에서 별도 보관하고, 직전 프로그램 코드로 복구하는 작업이다. **V1.0.2 프로그램과 `D:\NatureVideoStudio`·`D:\NVS_Recovery`·`D:\NatureVideoStudio_V2_Data`·Windows Credential Manager 비밀키는 업데이트 대상이 아니다.** 기존 V2 가상환경을 재설치하지도 않는다. 초기에 사용자 PC에 설치된 C011의 소스 및 Python 환경이 변경되었다면 업데이트를 중단할 수 있다.

## 4. 검증 결과의 정확한 범위

- GitHub Windows runner의 **모의 기존 V2 설치본**에서 코드를 같은 경로에 갱신→검증·중복 업데이트 차단→악성/잘못된 ZIP 거절→백업 복원·데이터 변형 없는지 확인한다. 이 실행은 사용자 개인 PC에 접속하거나 데이터를 검사한 것이 아니다.
- `tests/test_v2_existing_install_update.ps1` 명령은 **Windows PowerShell 5.1**이며, `.github/workflows/ci.yml`의 전용 Windows Qt 작업에서 시행.
- C024의 전체 pytest는 직전 309 PASS·3 SKIP·0 FAIL; 실제 Windows 새 GUI/시범 EXE 네이티브 캡처도 통과했다. 단, 이번 **사용자 PC에서 같은 설치본으로 실제 업데이트한 결과는 아직 NOT_TESTED**다.
- Windows Python 미설치 PC에서 정식 EXE 실행, 실제 제공처 180초 원본 검색, 미리보기/다운로드/영상 합성은 별도 R1~R5 목표이며 이 C024 시범 실행으로 완료되었다고 주장하지 않는다.

**중요:** 이 절차는 프로그램 소스 코드를 원래 V2 폴더 안에서 교체하는 개발 시험판 업데이트다. 임시 스테이징과 복구본은 내부적으로만 생성되며 새 사용자용 앱 설치 폴더나 체크리스트 항목을 만들지 않는다. 사용자 데이터와 V1.0.2는 어느 경우에도 자동 삭제하지 않는다.
