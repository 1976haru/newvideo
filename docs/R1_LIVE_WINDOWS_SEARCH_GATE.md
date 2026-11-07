# R1 실제 Windows GUI 검색 확인 (C029·C030 연결 검증)

날짜 2026-11-07. 단일 설치본 위치:
D:\NVS_V2_Trial_App\C011_Titlebar_10206483

## 실제 연결 범위

- 시작: NVS_V2_Start.cmd(기존 위치) 또는 현재 updater의 Update.
- 실제 QWidget: `trial_gui.build_window(live_providers=True)`
- `3분 이상 원본`: Wikimedia Commons(공식 Action API),
  Pixabay(공식 비디오 API, API 키 필요).
- `짧은 영상 조합`: Pixabay(5~120초). Pexels 5~120초 제공처는
  아직 실제 API 어댑터 미구현. 자동 클립 대체/다운로드 없음.
- 검색은 사용자가 버튼을 누를 때만 실행. 독립 QThread에서
  공식 API만 조회하며 결과는 두 탭에 섞이지 않음.
- 제휴 업체 API 결과의 길이와 해상도는 **제공처 메타데이터**.
  실파일 ffprobe 검증/4K 원본 촬영 여부/무편집 장면 증명은 여전히 필요.
- 결과 선택 시 제작자·라이선스·권리 triage 표시.
  미리보기 썸네일은 독립 worker에서 실제 HTTP 검사, 제한된 캐시.
  원본 페이지는 사용자 클릭으로만 허용된 출처 링크를 엶.
  실제 동영상 재생·다운로드·편집 버튼은 존재하지 않음.

## 반드시 사람이 자기 PC에서 수행할 순서

1. V2 실행 창 닫고 업데이트. V1/Data/keys 삭제나 교체 금지.
2. 동일 NVS_V2_Start.cmd로 실제 GUI 실행.
3. 장편 탭에서 `lake` 입력 → `이 탭 검색` 클릭.
   - Commons의 제공처별 결과 또는 HTTP/시간초과 코드가 표시되어야 함.
   - 결과가 없으면 0건/부분결과/확인불가를 구분.
   - 적어도 한 후보가 표시되면 행 선택 → 제작자/라이선스·썸네일/
     출처 링크 확인. 실제 풍경인지 영상 내용은 별도 확인.
4. Pixabay 기존 키가 있는 경우 Python keyring 모듈을 통해
   NatureVideoStudio_2026 / provider username을 읽기 전용 조회.
   모듈이 없거나 인증 실패면 명시적 오류가 보임.
   필요한 경우 Pixabay 키를 GUI에 직접 **한 번만** 입력하고
   'Pixabay 키 적용'을 누름. 키는 현재 실행의 메모리에만 저장되며
   출력·사용자 데이터 파일·레거시 키는 변경하지 않음.
5. 장편 검색 반복: 180초 미만이 끼지 않는지, 제공처 수집 원본
   길이 미확인은 제외되는지, 4K만 선택 시 제공처 FHD가 제외되는지.
6. 짧은 조합 탭에서 `lake` 검색 → 5~120초만 표기되는지,
   장편 탭 결과/조건이 바뀌지 않는지 확인.
7. 영상 미리보기/실파일 ffprobe/실다운로드는 **미구현**이므로
   PASS 대상으로 간주하지 않는다. 403/404/시간 초과는
   정확한 오류 출력을 회신. API 키를 채팅에 붙여넣지 않음.

## 테스트와 상태

- `python -m pytest -q tests/test_r1_live_search_gui.py`
- `python -m pytest -q`
- `NVS_RUN_QT_TESTS=1` CI 전용 Windows Qt 작업에서
  위 파일을 포함하는 실 Qt 버튼/화면 모의 API 응답 검증.
- GitHub CI에는 실제 사용자 API 키를 넣지 않고 대량 검색/다운로드하지 않음.
- GitHub/Qt mock PASS != Windows 실제 API/사용자 PC PASS.
- 기존 설치본 업데이트 검증도 실제 검색 PASS와 별도.

## 미해결 P0 / 우선 순위

P0-1: Windows 사용자 PC 실제 Commons+Pixabay API 결과/오류 확인.
P0-2: 실제 썸네일 HTTP/Qt 표시 및 영상 로컬 재생 구현, 실제 파일 검증.
P0-3: UI 권리 증빙을 이용한 수동 검토·안전 다운로드.
P1: C031 Internet Archive, C032 자연풍경 비적합 영상 배제.
