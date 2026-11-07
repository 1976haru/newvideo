# C029 — Pixabay VIDEO API duration / large 렌디션 검증

**체크리스트:** C029 / R1 / P0 / 2점
**개발 브랜치:** feature/v2-research-rebuild
**공식 문서:** https://pixabay.com/api/docs/
**약관:** https://pixabay.com/service/terms/
**검토:** 2026-11-07

## 수용 기준

Pixabay 공식 Video API의 hits[].duration 은 개별 영상의 길이이다.
유한하고 양수인 숫자만 신뢰 가능한 제공처 메타데이터로 채택한다.
179초는 장편 후보에서 제외하고, 180초는 포함한다. 길이 미확인,
문자열, NaN, 0, 음수, boolean 은 제외한다. 5~120초 클립 탭은
장편 탭과 별도이며 원본 자동 대체가 없다.

large 라는 이름만으로 4K로 표시하지 않는다. 공식 API 응답 예시에도
large = 1920x1080 이다. CDN HTTPS URL, size > 0, width/height 유효
확인 후 해상도를 분류한다. large 가 비었거나 size 0이면 다른 안전한
렌디션만 허용한다. 출처 URL과 크레딧도 보존한다. 타이틀/태그에
호수가 있다고 해서 실제 자연풍경으로 자동 확인하지 않는다.

Pixabay API상의 크기와 실제 파일 검증은 다른 단계다.
validate_pixabay_ffprobe 는 별도로 확보한 *로컬 영상 파일*의
ffprobe JSON에 포함된 비디오 스트림의 크기 및 실제 duration을
메타데이터와 비교한다. API가 4K여도 실제 파일이 1920x1080이면
verified_4k_file=False, 실제 파일이 179.95초면 verified_long_original
=False로 처리한다. 이 함수는 외부 영상을 내려받거나 ffprobe를
직접 실행하지 않으며, 업스케일 여부를 증명하지 못한다.

## 변경 파일

- src/nature_video_studio/pixabay_video.py
- tests/test_c029_pixabay_video_fixture.py
- .github/workflows/ci.yml — C029 독립 테스트 게이트
- docs/C029_PIXABAY_VIDEO_METADATA.md

## 테스트 명령

    python -m pip install -e ".[dev]"
    python -m pytest -q -k pixabay_video_fixture
    python -m pytest -q

## 검증 경계와 실사용

C029는 공급처 응답을 판정하는 오프라인 테스트이지 Pixabay API 키를
연결해 실제 3분 원본을 찾아냈다는 뜻이 아니다. 다음 항목은
미검증이다.

1. 실제 Pixabay Video API 키를 사용한 1건 검색, 제한 응답 처리.
2. 24시간 의무 캐시, API 속도 제한, 429 Retry-After, 안전한 리다이렉트.
3. 사용자가 선택한 실제 샘플의 ffprobe 실행/해상도·길이·fps 확인.
4. 개별 영상의 제3자 권리, 상업적 재사용과 실제 다운로드.
5. 기존 Windows V2 시험판의 실제 공급처 연결 및 표시.

현재 GUI에는 실제 Pixabay 검색 어댑터가 연결되지 않았으므로
검색 버튼에서 제공처 미연결을 그대로 표시한다.
Windows 사용자 데이터, V1 앱, 기존 API 키를 건드리지 않는다.
동일 시험 V2 위치 D:\NVS_V2_Trial_App\C011_Titlebar_10206483 를
유지하며, 체크리스트마다 새 설치 폴더를 만들지 않는다.

**QA 상태 구분:** fixture 테스트/CI는 테스트 결과 확인 후 기입.
실제 API / 실파일 / 사용자 PC 테스트는 NOT_TESTED로 유지.
전체 제품 또는 실제 4K 원본 검색 완료로 포장하지 않는다.
