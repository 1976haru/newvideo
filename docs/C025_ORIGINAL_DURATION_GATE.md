# C025 — 180초 이상 단일 원본 정확 판정 강화

**체크리스트:** C025 / R1_원본·클립검색 / P0 / 3점.
**판정:** GitHub 코드·Windows CI 범위 PASS 3/3. 실제 사용자 PC C025 버튼 조작은 아직 확인 전.
**실제 기능 검증 코드 커밋:** 106d6c08f4247e54bbbff3d1d3d7a917b4b4703c.
**성공한 GitHub Actions:** https://github.com/1976haru/newvideo/actions/runs/42336162238
**현장 확인과 별도인 증빙 아티팩트:** https://github.com/1976haru/newvideo/actions/runs/42336162238/artifacts/13559427572

## 1. 기존 C025 재감사

기존 2026-11-04 기초 코어 CI https://github.com/1976haru/newvideo/actions/runs/41918500325 는 성공했다. 이전 tests/test_long_duration.py에는 179.999초 제외, 180초 포함, 원본 길이 미검증 제외, 조합을 나타내는 검증 플래그 False에 대한 검사가 있었다.

남은 구멍: MediaCandidate에 **명시적인 조합 영상 표식이 없어**, 60초 세 클립을 합친 180초 영상이 길이 검증 플래그까지 잘못 True인 상태에서 원본으로 승인될 위험이 있었다. 비정상 길이 숫자(NaN/무한대/문자열)와 검색 최소시간 180초보다 낮게 강제 변경할 가능성도 있었다.

## 2. 이번 변경 — 코드 경계

- src/nature_video_studio/models.py: 기존 MediaCandidate에 is_assembled: bool = False 속성 추가(기존 API·시험 코드와 역호환). 합성물로 파악한 후보는 True로 표시해야 한다.
- src/nature_video_studio/filtering.py: 180초 미만 원본 거부, 180초 정확히 포함, 미검증·길이 없음·비수치·NaN·무한대 거부. **is_assembled=True이면 총 길이 및 verified 플래그와 관계없이 장편 원본/개별 단편 양쪽에서 제외**한다. 사용자 또는 어댑터가 long min_original_duration_seconds를 180 미만으로 낮추는 요청은 ValueError로 차단한다.
- src/nature_video_studio/search_mode_state.py: GUI가 조정기 결과를 받을 때 별도 수치 비교를 복제하지 않고 실제 duration_reason 규칙으로 최종 재검증한다. 따라서 잘못 구성된 결과 객체를 통해 조합 영상이 장편 목록으로 들어가는 것도 차단한다.
- src/nature_video_studio/duration_self_check.py: 파일·네트워크·자격증명 비접근 **8개 오프라인 합성 후보**로 실제 filter_candidates 함수 자가검사.
- src/nature_video_studio/search_tabs.py: '3분 이상 원본' 탭에 **C025 180초 규칙 검사** 버튼 추가. 클릭하면 오프라인 샘플 8개 판정을 PASS/FAIL로 팝업에 표시한다. 실제 공급자 검색 결과가 아니라는 안내도 함께 표시한다.
- tools/c022_windows_gui_probe.py: Windows 네이티브 GUI 스크린샷 시험에서 새 버튼의 존재 확인 및 실제 API 미연결 명시.
- tests/test_long_duration.py, tests/test_c025_duration_self_check.py, tests/test_c025_gui_self_check.py: 코드·장편과 단편 양쪽의 차단·검색 조정기·GUI 상태·화면 팝업의 테스트 추가.
- .github/workflows/ci.yml: Windows/Ubuntu Python 3.11·3.12 매트릭스에 C025 검사를 독립 Gate로 추가, Windows Qt 별도 작업에 버튼 클릭/팝업 검사 포함.

## 3. 재현 가능한 증거 및 실제 명령

    python -m pytest -q tests/test_long_duration.py tests/test_c025_duration_self_check.py
    # 49 passed
    python -m pytest -q
    # 341 passed, 4 skipped
    python -m pytest -q tests/test_c011_version_identity.py tests/test_c011_gui.py tests/test_c024_gui_search_modes.py tests/test_c025_gui_self_check.py
    # Windows Qt OFFSCREEN CI: 9 passed

GitHub Actions run 42336162238 / commit 106d6c08: Windows 및 Ubuntu × Python 3.11·3.12 4개 행렬 SUCCESS, C005 Windows 백업 보존 테스트 SUCCESS, Qt Windows 9 PASS, C022 Windows 네이티브 HWND·실화면 캡처·시험형 onedir EXE SUCCESS. 전체 **7/7 jobs SUCCESS**. 1차 코드 커밋 35ddd89에서는 180·181초 정렬을 테스트가 거꾸로 기대하여 1 FAIL이 발생했고, 106d6c08에서 테스트만 바로잡은 뒤 전체 재검증 PASS. 숨기지 않고 이력을 구분해 기록한다.

**중요:** 341 PASS와 Qt 9 PASS는 본 수용 조건의 코드/모의 GUI 검사 성공 증거이지 실제 영상 제공처에서 180초 원본을 검색했다는 증거가 아니다. 조합 여부와 길이 검증을 표시하는 제공처 어댑터가 실제로 만들어지기 전에는, 진짜 긴 영상 여부를 승인할 수 없다.

## 4. 사용자 PC — 같은 기존 설치본에서만 실행

현재 실제 Windows 사용자 설치 위치:

    D:\NVS_V2_Trial_App\C011_Titlebar_10206483

**다른 설치 폴더를 만들지 않는다.** 이미 기존 폴더 안에 생성된 NVS_V2_Updater.ps1을 사용한다. 실제 갱신을 실행하기 전에 V2 창을 반드시 닫는다.

관리자 권한 없는 Windows PowerShell:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\NVS_V2_Trial_App\C011_Titlebar_10206483\NVS_V2_Updater.ps1' -Mode Update -TargetCommit '106d6c08f4247e54bbbff3d1d3d7a917b4b4703c'

검증된 SHA로 코드를 같은 기존 V2 폴더의 src에만 교체하고, 이전 코드의 롤백 사본을 기존 V2 설치 폴더 안에 둔다. 기존 V1.0.2 앱, D:\NatureVideoStudio DB·파일, D:\NatureVideoStudio_V2_Data, 복구 백업 및 Windows Credential Manager 키는 대상이 아니다. 업데이트에는 기존 C024 모드 기본 GUI 스모크가 포함되지만, **C025 실제 화면의 버튼 클릭은 사용자 확인이 필요하다**.

업데이트 완료 후 '3분 이상 원본' 탭에서 **C025 180초 규칙 검사** 버튼을 클릭한다. **8/8 PASS** 메시지와 다음 구분이 나오는지 확인한다.

- 179초 및 179.999초: 장편 제외.
- 180초·181초 단일 검증 원본: 장편 포함.
- 길이 미확인·180초 미검증 원본: 장편 제외.
- 60초 × 3개 = 180초 조합: 장편 제외.
- NaN 숫자 오류: 장편 제외.

이 검사는 **합성 예제 8개**를 이용하며 실제 다운로드나 네트워크 요청이 아니다. 사용자에게 결과 화면/ '8/8 PASS' 확인을 받은 뒤 C025의 실제 Windows 로컬 확인 상태를 PASS로 갱신하고 C026으로 이동한다.

## 5. 남은 위험 및 배포 차단

- 실 공급자 API 어댑터가 **아직 없다**. 원본 여부, 원본 길이·실파일 4K·자연풍경/회의 영상 거짓양성에 관한 원격/실파일 검증은 후속 R1 Gate.
- MediaCandidate.is_assembled 표식과 original_duration_verified는 정보가 진실하게 설정된 경우에만 유효하다. 출처 자체가 거짓/불명확하면 원본 인증으로 취급하지 말고 original_duration_verified=False로 둬야 한다. 코어 테스트만으로 provenance를 자동 감정할 수 없다.
- C025 오프라인 자가검사 성공이 다운로드/상업 이용권/실영상 재생/정식 EXE의 PASS를 뜻하지 않는다.
- C017 실제 V1 오류 재현, C014 main 브랜치 강제 보호 설정, R2-R5 필수 수용 Gate는 미완료.
- Draft PR #1 유지, feature/v2-research-rebuild만 수정, 사용자 데이터 삭제/강제 푸시 없음.

**전체 진행률:** C025 코어 수용 3/3 포함 체크리스트 **19/162개 = 약 11.7%** (항목 수 기준, 기능별 가중 진행률 미산출). 사용자 PC의 C025 버튼 조작은 별도 대기.
