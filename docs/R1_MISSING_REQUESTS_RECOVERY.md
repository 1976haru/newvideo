# R1 Windows 기존 설치본 'requests' 누락 복구

날짜: 2026-11-07. 사용자 실제 오류:
- V2 경로: D:\NVS_V2_Trial_App\C011_Titlebar_10206483
- 업데이트 중 새 stage commons_adapter.py에서 ModuleNotFoundError: No module named 'requests'
- 출력: NVS_V2_UPDATE_FAILED / NVS_V2_UPDATE_ABORTED
- 실패 지점이 기존 src를 백업으로 이동하기 전이므로 updater 설계상 기존 active 소스와 SHA가 보존되는 단계. 실제 PC 마커는 Audit 결과로 재확인 필요.

## 이번 사용자 복구 로그

기존 V2 전용 .venv의 python.exe를 사용해 Successfully installed 확인:
- requests 2.34.2
- keyring 25.7.0

사용자가 실행한 pip 명령은 V1 설치본, DB, 영상, Windows Credential Manager 키를 수정하지 않는다.

동일 V2 설치본에 이전에 CI PASS한 소스 SHA 123c4c213d1d11c2f1cf0d81b2c4b4c3e4625a9c를 재적용하고, 실제 GUI 검색 결과/오류 화면으로 검증한다.

진단 명령:

    & 'D:\NVS_V2_Trial_App\C011_Titlebar_10206483\.venv\Scripts\python.exe' -c "import requests, keyring; print('NVS_V2_LIVE_DEPENDENCIES_PASS')"

사용자 실행 명령 (한 줄, V2 창 닫고):

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\NVS_V2_Trial_App\C011_Titlebar_10206483\NVS_V2_Updater.ps1' -Mode Update -TargetCommit '123c4c213d1d11c2f1cf0d81b2c4b4c3e4625a9c'

## 영구 개선 브랜치 (별도 코드 변경)

tools/NVS_V2_Update_Existing.ps1:
- 기존 V2의 정확한 .venv python.exe만 대상으로 requests/keyring 사전 검사.
- 새 stage 코드를 실제 src로 옮기기 전에 누락 의존성 복구.
- pip 실패/디스크 잔량 부족이면 기존 src를 보존하고 차단.
- FixtureMode에서는 실제 사용자 V2 Python 환경을 수정하지 않음.
- CI pytest 정적 검증, Windows PowerShell fixture, 실제 사용자 PC 단계는 별도 확인.

패키지 설치 성공은 실제 Commons/Pixabay 검색 성공을 보장하지 않는다. 키 값, 개인 자료를 채팅에 게시하지 않는다.
