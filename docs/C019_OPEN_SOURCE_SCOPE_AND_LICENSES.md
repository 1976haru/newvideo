# C019 — 외부 오픈소스 후보 라이선스·활용 범위 검증

**C019: PASS 2/2점 (2026-11-07).** 체크리스트의 FootageFlow, Media Buddy, PySceneDetect 3종에 대해 실제 GitHub LICENSE, README, 최근 커밋, 워크플로와 공개 Actions 결과를 확인했다. **모든 자료는 설계·UX 참고용이며 이번 변경에 외부 코드는 복사하지 않았다.** 이 문서는 외부 코드를 직접 실행/빌드한 테스트 증거가 아니다.

## 1. FootageFlow (xcslys99/FootageFlow)

- 저장소: https://github.com/xcslys99/FootageFlow
- 실제 LICENSE: https://github.com/xcslys99/FootageFlow/blob/main/LICENSE — **MIT**, Copyright (c) 2026 FootageFlow contributors. LICENSE blob SHA: **8a278ebd40743b6712e2920ae7915788998737ba**.
- 최근 HEAD **6b1110639854b4e4e59fa6dde701ea85350f63dc**, 2026-09-17 문서/화면 캡처 갱신. 2026-09-17 **3ced9baff2cd266e2c816c2c3ca5196b40ef88d1**의 Smart Duplicate Review v0.13.0 병합 및 Windows 결과 필터 수정 기록 확인.
- CI 정의: https://github.com/xcslys99/FootageFlow/blob/main/.github/workflows/ci.yml — macOS lint/secret scan, Swift build/test, Windows Swift core tests, WPF/.NET UI test, Windows 패키징 및 라이선스 확인 등. 실제 테스트 파일: Tests/FootageFlowTests/SearchDuplicateReviewTests.swift, SearchRelevanceTests.swift, ThumbnailPipelineTests.swift 및 여러 provider JSON fixtures.
- 최근 공개 실행: https://github.com/xcslys99/FootageFlow/actions/runs/35186720710 — 2026-09-17 **success**.
- V2에 적용할 **아이디어만**: 다중 검색 제공처의 실패 격리, 결과 목록의 출처·권리 분리, 로컬 프로젝트와 다운로드 큐, URL/source ID·썸네일 해시 기반의 후보 중복 검토, 선택 다운로드·재시도 UX.
- 가져오지 않을 기능: FootageFlow README의 **yt-dlp 기반 범용 링크 다운로더**는 Nature Video Studio의 무단 YouTube 다운로드 금지 및 공식 API·권한 확인 원칙과 충돌할 수 있으므로 이식 금지. 검색 결과 중복 판단과 저작권 승인은 별개이다.

## 2. Media Buddy (aivrar/mediabuddy)

- 저장소: https://github.com/aivrar/mediabuddy
- 실제 LICENSE: https://github.com/aivrar/mediabuddy/blob/main/LICENSE — **MIT**, Copyright (c) 2026 Media Buddy contributors. LICENSE blob SHA **7c31ee13ce83628ab82036b44ae0b3e4b4662888**.
- 최근 HEAD **f753ed8fb5fc28afda31575b5f7bfaa539544fd6**, 2026-06-12 저장소 정보 변경. 같은 날 공개 배포 준비.
- 실제 사용 기술: **Rust + Tauri 2 + SolidJS**, Tauri/Cargo.toml과 README 확인. Python/PySide6 프로젝트로 기술하면 잘못된 설명.
- CI 정의: https://github.com/aivrar/mediabuddy/blob/main/.github/workflows/ci.yml — Windows에서 npm ci / npm run build / cargo test / cargo clippy / git diff --check. 최근 공개 CI: https://github.com/aivrar/mediabuddy/actions/runs/27445884796 — 2026-06-12 **success**.
- V2에 적용할 **아이디어만**: 검색 결과 카드, 영상 미리보기 UX, SQLite WAL 카탈로그, 풍부한 메타데이터 및 선택 다운로드 대기열, Windows 포터블/설치형 UX.
- 핵심 비채택: README상 Media Buddy는 **data/config/settings.json에 공급자 API 키 및 REST 토큰 저장**. V2 요구사항인 Windows OS 자격증명 저장소 방식과 충돌하므로 키 저장 구현은 재사용 금지. Florence-2 ONNX 모델 및 REST 서버는 초기 단계에서 과도한 복잡성.

## 3. PySceneDetect (Breakthrough/PySceneDetect)

- 저장소: https://github.com/Breakthrough/PySceneDetect
- 실제 LICENSE: https://github.com/Breakthrough/PySceneDetect/blob/main/LICENSE — **BSD-3-Clause**, Copyright (C) 2014, Brandon Castellano. LICENSE blob SHA **c03985e60181f431b181735b4d06ada21272322a**.
- 최근 HEAD **c5ce29c73751e77139e838bd9ce9ab66a8e71a23**, 2026-11-02 자동 다운스케일 옵션 개선. 2026-10-31 FFmpeg 분할 출력 폴더 안내 수정, 2026-10-25 VideoStream close/context manager 기능 추가.
- 테스트 구성: tests/test_detectors.py, tests/test_scene_manager.py, tests/test_video_stream.py, tests/test_vfr.py, tests/release/test_backends.py 및 GitHub Actions build.yml / test-installer.yml / Windows 배포. 공식 README에는 독립 개발 시 pytest와 선택적 ffmpeg/mkvmerge 의존성 조건이 명시됨.
- 최근 공개 CI: https://github.com/Breakthrough/PySceneDetect/actions/runs/42172362790 — 2026-11-06 **Windows Distribution success**. 같은 HEAD의 https://github.com/Breakthrough/PySceneDetect/actions/runs/42168724290 — **Python Distribution cancelled**. 모든 워크플로가 통과했다고 주장하지 않음.
- V2에 적용할 **아이디어만/조건부 라이브러리 후보**: 장면별 컷·전환 검출, 지나친 반복 분석, R4 Composer의 디졸브 설계. 나중에 성능·코덱 검증 후 공식 Python API로 통합 검토.
- 의무: https://github.com/Breakthrough/PySceneDetect/blob/main/THIRD-PARTY.md — OpenCV, NumPy, PyAV 및 FFmpeg/mkvmerge 등 별도 조건. BSD 3-Clause의 저작권·면책문 보존, 저작권자 및 기여자 이름을 허가 없이 보증/홍보로 사용 금지. **원본 180초 증빙, 촬영된 진짜 4K, 상업적 이용권**을 장면 탐지 결과로 대체할 수 없음.

## 결정: 설계 참고만 허용, 복제·배포는 별도 Gate

| 행위 | C019 판정 | 이유/조건 |
| --- | --- | --- |
| 공개 README/사용자 흐름/기능 구조를 참고하여 독립 구현 | **허용** | 출처는 이 문서에 기록, 자체 코드·모의 테스트 작성 |
| 오픈소스 원본 코드 조각/모듈의 무검토 복제 | **금지** | 직접 재사용하려면 소스별 명시적 코드·보안·라이선스·NOTICE·SBOM 검토 후 승인 |
| MIT 소스 포함·재배포 | **후속 심사** | LICENSE 저작권 및 허가 문구를 필요한 범위에 포함, 전이 의존성 확인 |
| BSD-3-Clause 소스/바이너리 포함 | **후속 심사** | 원저작권/면책문 보존 및 원저작자 보증 금지, 전이 라이선스 확인 |
| yt-dlp·무단 YouTube 다운로드 기능 차용 | **불허** | 공식 API/약관/허용 재사용/명시적 선택 정책 위배 위험 |
| Media Buddy의 JSON 설정 파일에 키 저장하는 방식 차용 | **불허** | V2는 Windows 자격증명 저장소 사용 |
| FFmpeg/OpenCV/PyAV 포함한 최종 Windows EXE | **R5 Gate** | 직접/전이 의존성 고지, FFmpeg LGPL/GPL 옵션, 설치형·폴더형 EXE 테스트 |

MIT 및 BSD 3-Clause 자체가 코드 수정·재배포를 전면 금지하는 것은 **아니다**. 무검토 코드 복사는 이번 Nature Video Studio 개발 절차상 금지하는 것으로 구분한다. 업체의 오픈소스 라이선스는 영상/음악 저작물의 다운로드나 YouTube 상업 재업로드 허가와 별개이다.

## 범위·증빙·후속

- 체크리스트 요구였던 세 프로젝트의 **기능, LICENSE 원문, 최근 변경, 정의된 테스트 및 공개 CI 성공/취소 구분, V2 활용 경계**를 충족하므로 C019 **PASS 2/2**.
- 외부 소스 코드를 복사, 의존성에 추가, 실행하거나 V1.0.2 원본·사용자 DB·API 키·영상·백업을 읽거나 변경하지 않았다. **main 변경 금지, feature/v2-research-rebuild에 문서만 기록, Draft PR #1 유지**.
- 새 기능 테스트는 작성하지 않았다. 문서 커밋 전후 V2 CI 검사 상태는 별도로 검증해 보고한다.
- 다음 필요 과제: 180초 실제 원본 검증·자연풍경 거짓양성 차단(R1), 실영상 미리보기(R2), 권리 검토 후 파일 수집(R3), 장면 전환/중복 검사와 라이선스 고지 포함 패키징(R4/R5).
