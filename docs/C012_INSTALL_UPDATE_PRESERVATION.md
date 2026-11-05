# C012 — 설치형 업데이트 DB·영상·API 키 보존 강제 Gate

**현재 범위:** V2 설치형 EXE/업데이터는 아직 미구현이므로, 이 항목의 실제 설치기 업데이트 최종 PASS는 보류한다. 대신 **V2 프로그램만 새 버전 폴더에 배치**하는 재사용 가능한 보호 엔진과 `pytest -k migration_and_preservation` CI 차단 Gate를 구현한다.

## 보존할 폴더와 쓰기 정책

| 경로 | 취급 |
| --- | --- |
| `D:\03 자연풍경 비디오\NatureVideoStudio_V1_0_2` | 기존 V1 프로그램: 읽기만, 어떠한 덮어쓰기/삭제도 금지 |
| `D:\NatureVideoStudio` | V1 `library.sqlite3`·downloads·cache·설정: 변경 금지 |
| `D:\NVS_Recovery` | C002/C004 원본 및 C008 롤백 파일: 변경 금지 |
| `D:\NatureVideoStudio_V2_Data` | V2 사용자 DB·영상·설정: 업데이트 대상 아님 |
| `D:\NVS_V2_Trial_App` | 새 버전 프로그램 파일만 저장. 기존 버전 폴더 보존 |

C011 최소 Qt GUI 실행 실험은 이미 별도의 V2 전용 폴더에 설치되었으나, **그 시험 스크립트는 실제 버전 업데이트 엔진을 이용하지 않았다.** 앞으로 제작하는 EXE/MSI/portable 업데이터는 반드시 C012 검사를 통과하는 검증된 방식으로 배치해야 한다.

## 강제 Gate 절차

1. 업데이트 위치 `UpdateLocations` 검증. V2 프로그램 폴더가 V1 앱·V1 데이터·복구 디렉터리·V2 데이터와 같거나 포함 관계면 차단. 기존 V1 디렉터리와 복구 루트가 없으면 차단.
2. SQLite는 URI `mode=ro`, `PRAGMA query_only=ON`으로 `integrity_check`와 `foreign_key_check` 확인. V2 DB가 있으면 `PRAGMA user_version = 1`만 허용. 없으면 생성하지 않음. `-wal/-shm/-journal`이 존재하면 실행 앱을 닫도록 요청하고 차단.
3. `D:\NVS_Recovery` 아래 C008 이관 저널이 `PREPARED`, `ACTIVATING`, `ROLLING_BACK`, 알 수 없는 상태면 차단. `ACTIVE`와 `ROLLED_BACK`만 허용.
4. V1/V2 사용자 DB·영상·캐시·백업 폴더의 파일 및 디렉터리 목록과 각 파일 SHA256으로 **읽기 전용 보존 기준선** 생성. 링크/정션을 통한 경로 우회는 거부. 대용량 영상 해시 계산은 시간이 길어질 수 있으나 일괄 삭제보다 안전성을 우선.
5. 패키지의 심볼릭 링크·정션과 충돌 파일명을 확인하고 새 `release-<version>` 폴더만 생성. 기존 릴리스 경로가 있으면 덮어쓰지 않고 차단. 새 프로그램 파일은 고유 `.c012-staging-<UUID>`에 복사/해시 확인.
6. 보호 폴더의 해시 기준선이 그대로인지 재검사하고, 새 릴리스 폴더에 이름 변경. 다시 한 번 보호 폴더 변경 여부 확인. 전 과정 **기존 릴리스 및 사용자 데이터 삭제 없음**.
7. 복사 실패·동시 사용자 데이터 변경·디스크 부족·지원하지 않는 DB 버전 등은 실패 처리. 새 staging 폴더는 재검토할 때까지 보존하고 임의로 사용자 데이터를 삭제하거나 이전 릴리스를 덮어쓰지 않음.
8. 업데이터 코드에서는 `keyring`를 import하거나 `get_password/set_password/delete_password`를 호출하지 않는다. 자동 테스트는 이 세 호출에 실패를 발생시키는 가상 백엔드를 넣어 실행 경로에서 호출하지 않는지 확인. **실제 Windows 키의 보존을 보증하는 시험은 C009 실제 V2 연동/UAT에서 후속 수행**해야 한다.

## 자동 테스트와 차단

```sh
python -m pytest -q -k migration_and_preservation
python -m pytest -q
```

GitHub Actions `.github/workflows/ci.yml`의 기본 Python 테스트 매트릭스(Windows/Ubuntu, Python 3.11/3.12)에서 **보존 Gate를 전체 테스트보다 먼저 실행**한다. 이 단계가 실패하면 동일 CI 작업이 실패하여 전체 테스트 단계에 도달하지 않는다. 다만 GitHub 브랜치 보호 규칙에서 이 작업을 '필수'로 설정하지 않았다면 **머지가 기술적으로 불가능하다고 주장할 수 없다.** 실제 릴리스 워크플로/설치 패키지 연결은 아직 작업 필요.

테스트는 임시 디렉터리에서 실제 SQLite 파일과 가상 영상·백업 파일을 만들어 사용하며, 다음 실패를 검증한다: V1→V2 이관 후 프로그램 업데이트와 DB 롤백, 이전 V2 사용자 행 보존, 기존 프로그램 폴더 덮어쓰기 방지, 임의 경로·상위/하위 겹침 차단, 손상·알 수 없는 스키마 및 미완료 C008 저널 차단, 복사 중 장애, 사용자 영상 외부 변경 감지, API 키 저장소 미접근, 기존/신규 V2 DB 부재, 심볼릭 링크 차단.

## 현재 미해결 Gate

- 실제 Windows EXE/MSI 설치기/업데이터 및 재부팅 업데이트가 아직 없음. 신규 설치·실제 버전 업데이트·복구·제거와 외부 설치 관리자 이벤트의 DB·키 보존 시험은 **SKIP**.
- 별도 C011 실험 설치 프로그램은 C012 검사 엔진을 사용하지 않았으므로 C012 최종 설치형 Gate로 인정 불가.
- 백업/영상의 실제 대규모 파일·디스크 부족·권한/잠금·백신 격리, USB 드라이브 제거 등 실기기 시험 필요.
- V2 데이터 원본을 사용한 실제 업그레이드, Windows 자격 증명 저장소의 마스킹 재확인, 최종 설치 파일 체크섬/서명/재현가능 빌드는 후속 Gate.
- `main`은 건드리지 않고 `feature/v2-research-rebuild`만 작업. 기존 V1.0.2 API 키·DB·영상·백업에는 접근하지 않았음.

**C012 수용 기준:** 보호 코드를 실제 업데이트 진입점에서 호출하도록 강제하고, Windows 설치형 업데이트 전후 DB/영상·키 미변경 자동 및 UAT 증거를 확보한 때만 3/3점 최종 PASS.

## C012 verified CI evidence — 2026-11-06

**Preservation code/test gate: PASS. Actual installer upgrade: SKIP / C012 final remains PENDING.**

GitHub Actions run: https://github.com/1976haru/newvideo/actions/runs/42119797636 (verified source HEAD before this documentation-only commit: `1bf2e51ff4fc0502830e40346a8f9e316e303616`).

Actual CI jobs: Windows Python 3.11, 3.12; Ubuntu Python 3.11, 3.12; Windows C011 Qt GUI smoke; Windows C005 PowerShell safety fixtures — all SUCCESS.

- Required preservation command: `python -m pytest -q -k migration_and_preservation` → **26 PASSED / 125 DESELECTED** on Windows Python 3.11 (and the other matrix operating systems passed their jobs).
- Full regression command: `python -m pytest -q` → **150 PASSED / 1 SKIPPED / 0 FAILED** on Windows Python 3.11. SKIP is the Qt GUI smoke that is executed in a separate dedicated Windows job.
- Dedicated Windows Qt job: **6 PASSED**, `C011_GUI_SMOKE_PASS`.
- CI gates exercise synthetic SQLite databases, media, backup snapshots and fake keyring. No actual Windows credential was read and no real D: user file was changed.
- **Progress**: C012 provisional design + CI coverage accepted; installation workflow still unimplemented, so preserve **0/3 final acceptance points** until real packaged update tests. Alternatively report 2/3 internal design/test stages separately, never claim C012 final PASS.

Missing before final acceptance: wire this guard into an actual Windows installer/updater and uninstall process, package signature/provenance verification, simulated disk-full/locked database and real VM upgrade, check Windows Credential Manager masked status before/after, recovery/rollback after interrupted installer. Branch protection required checks not independently verified.
