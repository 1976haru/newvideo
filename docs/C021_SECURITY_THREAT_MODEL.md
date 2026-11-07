# C021 — 비밀키·로그·허용 URL·SSRF 위협 모델

**검증 범위: 2026-11-07 / P0 정적·모의 테스트.** 실제 V2 다운로드 백엔드는 아직 없다. 이 문서는 공격 표면과 방어 규칙, 재현 명령, 잔여 위험을 다룬다. 기존 V1.0.2 데이터·API 키는 접근하지 않았다.

## 주요 위협과 통제

| 자산/경계 | 공격 및 예상 피해 | C021 적용 방어 | 남은 검증 |
| --- | --- | --- | --- |
| Pexels/Pixabay API 키와 Windows Credential Manager | Authorization/URL/query/예외/로그를 통한 키 노출 | 비밀값 미접근, 안전 오류 코드, Authorization/Bearer/JSON/query 마스킹, raw URL 로그 금지 | R1 실제 adapter와 Windows keyring, 설치 EXE 검사 |
| 썸네일 URL과 30x Location | localhost/RFC1918/169.254, cloud metadata 등 SSRF | 목적별 호스트 허용 목록, HTTPS/443, userinfo·empty userinfo/encoded controls 거부, 리디렉션 매 hop 검증 | 실제 연결 peer IP pinning/검증 및 DNS rebinding 차단 |
| 공식 출처 외 arbitrary URL | 임의 사이트·YouTube·사설 호스트의 무단 다운로드 | 임의 URL 다운로더 없음; provider/file URL 정책 검증, 사용자 선택·권리 검토 인텐트, 미구현 큐 fail-closed | R3 실제 다운로드 백엔드 및 허용 제공처 API 동작 |
| Qt 재생 오류 | 파일 경로·서명된 URL·계정 정보가 화면에 노출 | 상세 문자열을 직접 표시하지 않고 분류된 안정 코드 + 일반 설명만 노출 | R2 실제 Windows Qt/codec 오류 확인 |
| 사용자 DB·영상·복구 백업 | 보안 검사 중 기존 데이터 변경·삭제 | 테스트 전부 임시 폴더와 fake HTTP/키링만 사용, 설치/업데이트는 기존 C012 보존 Gate | R5 실 EXE/업데이트 테스트 |

## 적용 코드

1. src/nature_video_studio/network_security.py
   - poster/download 구분이 있는 승인 미디어 호스트 목록
   - Pexels 포스터 images.pexels.com / 파일 videos.pexels.com
   - Pixabay 포스터·파일 cdn.pixabay.com
   - Wikimedia 포스터 upload.wikimedia.org 또는 commons.wikimedia.org / 파일 upload.wikimedia.org
   - Internet Archive archive.org 및 지역별 공식 .archive.org 저장 서버
   - HTTP/file/ftp, 사용자정보(빈 @ 포함), 잘못된 포트, 외부/유사 도메인, IP literal, 개행·NUL, 인코딩·이중 인코딩된 경로 traversal, URL fragment 거부
   - dns_is_public: 모든 A/AAAA 응답의 공개 라우팅 가능 여부 확인. mixed/private/linklocal/loopback/reserved, DNS 실패 모두 차단
   - require_download_url: 재사용 가능한 다운로드 대상 검사 (다운로드 자체는 하지 않음)
   - redact_sensitive: Authorization, Bearer, JSON 비밀값, query token, 서명된 URL 노출 방지용 보조 함수
2. src/nature_video_studio/preview.py
   - provider_url_allowed를 사용해 **매 Location** 주소 검사, requests 자동 리디렉션 비활성화
   - 실제 session은 trust_env=False로 OS 환경 프록시/.netrc 자동 상속 금지
   - 실제 각 URL 접속 전 DNS 공개 IP 검사. 실패하면 PREVIEW_UNSAFE_DNS 코드 및 안전한 안내 메시지
   - 예외 원문/민감 URL을 GUI 메시지에 출력하지 않음
3. src/nature_video_studio/download_queue.py
   - DownloadIntent 생성 시 사용자 명시 선택 + USER_VERIFIED 권리 상태 요구
   - URL과 제공처가 모두 주어지면 승인된 파일 호스트인지 확인; source_key에 전체 URL 및 signed query를 저장하지 못하게 차단
   - 호환성 때문에 source_url 없는 인텐트 객체 자체는 생성될 수 있지만, **실제 DownloadQueue는 없고 FeatureUnavailable 반환**. R3 실제 구현 시 URL 필수 및 재검증 Gate가 필요
4. src/nature_video_studio/local_player.py
   - Qt 미디어 오류의 details 원문 대신 playback_diagnostics의 안정 코드/일반 한국어 메시지만 화면에 표시

## 반복 가능한 모의 공격 검증

- tests/test_c021_security_ssrf_redact.py
- GitHub Actions 기본 매트릭스: Windows/Ubuntu × Python 3.11/3.12. CI가 C012/C017/C020 Gate 다음에 C021 전용 Gate를 수행하도록 설정.

실제 검사 명령:

    python -m pytest -q -k "security or ssrf or redact"
    python -m pytest -q tests/test_c021_security_ssrf_redact.py
    python -m pytest -q

모의 테스트에 포함한 사례: 공식 호스트 허용, 사설/localhost/IPv6/169.254/100.64 주소 차단, 사용자정보 및 변조 authority, 302를 통한 외부/사설 도메인 이동 거부, 모든 DNS 답이 공개 주소일 때만 허용, 리디렉션별 재검증, 프록시 자동 상속 차단, 토큰/JSON/Authorization 마스킹, Qt 오류 상세 문자열 출력 방지, 실제 다운로드 및 비밀키 호출 금지.

단위테스트는 외부 HTTP, 실제 OS 키링, 실 다운로드, 사용자의 C:·D: 파일을 요구하지 않는다.

## 중요: 미해결 보안 한계

**DNS 재바인딩/TOCTOU**: 공개 IP 사전 DNS 조회와 requests의 실제 소켓 연결이 분리되어 있어, 연결 시점에 DNS가 변하거나 중간 네트워크 경로가 변경되는 위험은 완전히 해소되지 않았다. 실제 다운로드 백엔드 전제 조건으로 TLS/SNI 호스트 검증과 실제 연결 peer IP 고정/재검증, IPv4/IPv6/프록시 동작에 대한 Windows 통합 테스트를 별도 수용 Gate로 남긴다. C021 모의 테스트의 PASS를 모든 SSRF 공격의 방어 완료라고 표현하지 않는다.

**Token redaction**: redaction 함수는 보조적 필터다. 임의 문자열에 포함된 모든 비밀을 완벽히 인식하지 못할 수 있다. 실제 운영 로그에는 raw HTTP headers/requests exceptions, 키, 토큰, 인증 URL을 애초에 기록하지 않아야 한다. API key 저장·접근은 C006 정적 설계가 있을 뿐 아직 V2 실제 연동이 없다.

**실 다운로드 미구현**: DownloadIntent와 URL allowlist 검사는 계약이며 실제 파일 검증, Retry-After, redirect peer pinning, 데이터 무결성, 용량/디스크 검사, 경로 정규화는 R3·R5의 별도 실기기 수용 기준이다. 임의 웹사이트 스크래핑/무단 YouTube 다운로드 기능은 추가하지 않는다.

**UI/EXE 미검증**: 실제 다운로드용 네트워크와 Qt 스트리밍 코덱, 장시간 미리보기, Windows credential 동작, 설치형 EXE 자체에 대한 보안 시험은 아직 수행하지 않았다.

## 수용 판정 범위

C021은 위협 모델 + 허용 URL/리디렉션/private DNS/키 노출에 관한 **재현 가능한 오프라인 시험**에 한정하여 판정한다. 실 운영 다운로드와 실제 peer pinning은 C021 문서상 미해결 위험으로 명확히 기록하고 후속 R2/R3/R5 릴리스 Gate에서 별도로 차단할 것.

feature/v2-research-rebuild 브랜치와 Draft PR #1만 사용하며, main 및 기존 V1.0.2·사용자 DB·비밀키·복구 백업은 변경하지 않는다.
