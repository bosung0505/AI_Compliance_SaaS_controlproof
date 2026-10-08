# Implementation Plan: 웹 워크벤치·12개 시나리오 카탈로그·결과 보고서

**Branch**: `005-web-workbench-report` | **Date**: 2026-10-08 | **Spec**: [spec.md](./spec.md)

**Input**: Clarified spec(2026-10-08), 승인 목업 [mockups/workbench-mockup.html](./mockups/workbench-mockup.html)과
[REVIEW.md](./mockups/REVIEW.md), [원천 기준선](../../docs/research/Spec005_Workbench_Report_Source_Baseline.md),
`.specify/memory/constitution.md`, Decision Log D-018(추가 결정 포함). 결정 근거는 [research.md](./research.md).

## Summary

봉인된 Run 기록과 12개 카탈로그를 읽어 네 화면(워크벤치, 시나리오 상세·실행 안내, 실행 결과·증적, 재시험 비교·보고서)을 보여 주는
로컬 PC 전용 웹을 만든다. 웹은 판정을 만들지 않는다. 판정·assertion·증적은 기존 엔진의 verify·검토 projection 경로에서 읽고, 웹에서
시작하는 동작은 준비 상태 확인(명령줄 preflight 하위 프로세스)과 봉인 기록 밖 수정 메모뿐이다. 웹이 기대는 엔진 결함(경로 노출, 이스케이프
경로 미검출, 증적 링크 누락, 출력 불일치)을 실패 시험부터 고친다. 마지막으로 웹 PC에서 7개 프로필을 다시 실행한 기록으로 화면을 검증하고
역할별 사용성 검토를 한다.

## Technical Context

**Language/Version**: Python 3.12(기존 `.venv`, `requires-python >=3.12`)

**Primary Dependencies**: 기존 의존성만 사용 — Pydantic 2(모델), PyYAML(카탈로그), Jinja2 3.1(서버 렌더링 템플릿), Playwright(화면 시험).
웹 서버는 표준 라이브러리 `http.server.ThreadingHTTPServer`. **새 의존성 없음**(research R-001).

**Storage**: 파일만. 봉인 bundle(run root, 읽기 전용), 합성 bundle(`.controlproof/web-demo/runs`), 카탈로그(`catalog/mvp-scenarios.yaml`),
웹 상태(`.controlproof/web/` 아래 준비 상태 확인 결과와 수정 메모, Git 제외).

**Testing**: pytest(단위·계약·통합), Playwright 화면 시험(1280·1024px), ruff.

**Target Platform**: 개발·검증 담당자의 Windows/macOS/Linux PC, 데스크톱 브라우저(Edge·Chrome). 휴대폰·태블릿 제외(A-10).

**Project Type**: 기존 Python CLI 엔진 + 같은 패키지 안의 로컬 웹 서버(단일 프로젝트).

**Performance Goals**: 화면 전환 2초 안(A-8). bundle 30개 이하에서 워크벤치 첫 표시 2초 안. verify 결과 캐시의 키는 manifest
`bundle_digest`와 bundle 안 모든 파일의 (상대 경로, 크기, 수정 시각)이며, 하나라도 바뀌면 다시 verify한다(봉인 뒤 파일 변경을 놓치지 않음, FR-017).

**Constraints**: `127.0.0.1` 전용, 로그인 없음, 외부 CDN·폰트·네트워크 없음, 판정 비재계산, 봉인 파일 불변, 화면·응답에 절대 경로·토큰·원문 없음.

**Scale/Scope**: 사용자 1명, 시나리오 12개(실행 프로필 7개), bundle 수십 개, 화면 4개.

## Constitution Check

### Pre-design gate

| 원칙 | 판단 | 근거 |
|---|---|---|
| I 판정은 증적에서만 | 통과 | 판정은 VERIFIED bundle의 봉인 판정만 보임(R-003). 무결성 실패면 판정을 보이지 않음. 법적 인증 표현 금지(FR-026·028). |
| II 대상·준비·결과 분리 | 통과 | 대상 존재·준비 상태·결과를 다른 열·배지로 분리(spec 화면 어휘). `NOT_RUN`은 화면 값, `RESTORE_FAILED`는 실행 안전 문제. |
| III 사람 최종 결정 | 통과 | AI 점수는 참고 정보 원칙을 보고서에 고정(FR-027). 웹에는 결정 기능이 없음. |
| IV 시나리오는 데이터·연결은 어댑터 | 통과 | 12개 카탈로그는 데이터 파일, 화면은 WhyYou 내부 이름을 기본 문장에 쓰지 않음(FR-019). |
| V 격리·결정론·복구 | 통과 | 웹은 Run·재시험·정리 확인을 시작하지 않음(D-018). 실행 안전 규칙은 명령줄 그대로. |
| VI 결과 불변·계보 | 통과 | bundle 읽기 전용, 수정 메모는 bundle 밖(R-008), 계보 비교는 부모 무결성 값으로 확인(FR-023). |
| VII 명세→증적 추적 | 통과 | assertion별 증적 색인(R-011), 공식 상태와 Validation 연결(R-006). |
| 데이터 안전 | 통과 | 합성 데이터만, 출력 경계 redaction(R-009), 다른 PC 기록 가져오기 없음. |
| 상태 명칭 | 통과 | D-011 명칭만 사용, 별칭 없음. 확인 도구 오류·무결성 실패는 판정·준비 상태 값을 늘리지 않는 별도 표시. |

### Post-design re-check

설계 후에도 위반 없음. 다음 두 가지는 위반이 아니라 보성 확인이 필요한 정밀화로 위험 표에서 관리한다: (1) R-012의 "봉인 시점 검사 버전으로
verify"는 과거 판정을 바꾸지 않는다. (2) R-010의 `result_kind`·`error_kind`는 판정이나 준비 상태 값을 늘리지 않는 출력 메타데이터다.

## Source-derived Boundary Map

| 화면 요소 | 원천 | 비고 |
|---|---|---|
| 12개 목록·처리·담당 Spec | `catalog/mvp-scenarios.yaml`(범위표 파생, 일치 시험) | R-005 |
| 공식 상태·Run ID | 카탈로그의 Validation 참조 | R-006 |
| 판정·assertion·reason code | `verify_bundle` → `load_bundle_summary` | R-003 |
| 증적 목록·SHA-256·단계 | manifest + 새 `evidence_index` | R-011 |
| 계보·바뀐 차원 | `retest-link.json`·`retest-diff.json`, 부모 verify | Spec 001·002 계보는 엔진의 부모 검증이 없어 링크·digest 대조로 표시 |
| 준비 상태·확인 시각 | 명령줄 preflight JSON(하위 프로세스) 저장본 | R-007 |
| 시나리오 상세 | 봉인 snapshot(Run별) 또는 `scenarios/*.yaml`(Run 없음) + 카탈로그 설명 | FR-008·009 |
| 수정 메모 | `.controlproof/web/memos/` | R-008 |

## Design

### 1. 패키지 구성

- `engine/web/server.py`: 서버 기동(포트 인자, 기본 8765), Host 검사, 토큰, 라우팅, 보안 헤더.
- `engine/web/readmodel.py`: 카탈로그·실제 run root·DEMO root를 읽어 [contracts/web-read-model.md](./contracts/web-read-model.md)의 뷰를 만든다.
  verify 캐시 키는 Performance Goals의 규칙을 따른다.
- `engine/web/badges.py`: 상태 → 배지(이름·아이콘·모양·설명) 표 하나. 템플릿은 이 표만 쓴다(R-016).
- `engine/web/preflight.py`: 하위 프로세스 실행·저장·해석(R-007).
- `engine/web/memos.py`: 메모 추가·조회(R-008).
- `engine/web/templates/`: `base.html`(DEMO 띠·머리글·탭), `workbench.html`, `scenario.html`, `run.html`, `compare.html`, `report.html`.
- `engine/web/static/workbench.css`, `workbench.js`(필터·펼치기·복사·폼 제출만).
- `catalog/mvp-scenarios.yaml`: 12개 카탈로그([contracts/catalog.md](./contracts/catalog.md)).
- 엔진 보완: `engine/evidence.py`(경로 정규식, `scan_bytes_strict`, `redaction_profile`), `engine/presentation.py`(`evidence_index`, 사람용
  문장 경계 redaction), `engine/cli.py`(run root 규칙, `result_kind`·`error_kind`, JSON 사용법 오류, `bundle_path` 표기).
- `scripts/scan_bundles.py`(R-012), `scripts/prepare_web_demo.py`(합성 bundle 생성, 기존 테스트 fixture 재사용).

### 2. 화면별 데이터 흐름

- **워크벤치**: 카탈로그 12개 × (공식 상태, 실제 root의 해당 Run 존재·무결성, 최신 준비 상태 저장본). 개수는 카탈로그 상태 집계(판정 불가는
  reason code 배지별). 웹 검증 기록과 DEMO 기록은 별도 영역.
- **시나리오 상세**: 정의(Run의 봉인 snapshot, 없으면 현재 YAML) + 카탈로그 설명 + 최신 준비 상태 + 복사용 명령(카탈로그의 프로필별 명령 틀).
  `NOT_RUN`·`NO_TEST_TARGET` 항목은 카탈로그 설명만 보이고 실행 안내 영역이 없다.
- **실행 결과·증적**: verify → VERIFIED면 projection + `evidence_index` + 메모, 아니면 무결성 실패 화면. 원본 증적 보기는 텍스트·256 KB 이하·
  경계 검사 통과분만(R-009 e).
- **재시험 비교·보고서**: child의 `retest-link`·`retest-diff` + 부모·자식 projection. 보고서는 카탈로그 + 공식 상태 + 각 Run 한계 + 고정 문구.

### 3. 엔진 보완 순서 (모두 실패 시험 먼저)

1. 경로 정규식과 출력 경계 경로 정책(위험 1·2) → 2. `scan_bundles.py`로 이 PC bundle 검사·보고서 → 3. 보성 PC 검사 결과 수령·Validation 기록 →
4. 봉인 시점 검사 v2 전환(`redaction_profile`) → 5. `evidence_index`(위험 3) → 6. `result_kind`·`error_kind`, JSON 사용법 오류, 준비 안 됨 `run`의
`command`, H-03 cleanup 오류 JSON(위험 5) → 7. `show`·`verify` run root 규칙. 위험 4는 Spec 005 밖 별도 보완(R-013).

## Test Strategy

| 층 | 대상 | 예 |
|---|---|---|
| 단위 | 카탈로그 일치, 경로 정책, 스캐너 v1/v2, `evidence_index`, read model 매핑, 배지 표 | 범위표 §3 12/12, 이스케이프 Windows 경로 검출, `file:` 참조 해석 |
| 계약 | 명령줄 추가 필드·오류 JSON·종료 코드 불변, 웹 HTTP 응답·오류 형식 | [cli-output-additions](./contracts/cli-output-additions.md), [web-http](./contracts/web-http.md) |
| 통합 | 합성 PASS·FAIL·INCONCLUSIVE·RESTORE_FAILED·변조·계보 bundle로 네 화면 뷰 | `tests/fixtures/bundles/cases.json`, Spec 003·004 fixture |
| 화면 | 브라우저 자동화 1280·1024px | 탭·필터 5/0/4·배지·DEMO 띠·콘솔 오류 0·가로 넘침 0·실행 버튼 부재 |
| 보안 | Host 검사, POST 토큰, 외부 주소 바인딩 불가, 응답 전체 경로·토큰 스캔 | SC-007 |

### 성공 기준 측정

| SC | 측정 |
|---|---|
| SC-001 | 카탈로그 일치 시험 12/12 + 화면 시험이 `NOT_RUN`·`NO_TEST_TARGET`·`INCONCLUSIVE` 행·개수에 PASS 배지 0개 |
| SC-002 | 모든 합성·실제 bundle에서 화면 판정 = `verify`+`show` 판정 100%, 변조 bundle 100% 무결성 실패 |
| SC-003 | 화면 시험: 워크벤치 → 결과 → 증적 클릭 ≤3, PASS·FAIL assertion마다 SHA-256 있는 증적 ≥1 |
| SC-004 | 보고서 R1~R13·C1~C9 표지 22/22(화면 시험) |
| SC-005 | E-01 실제 계보와 합성 계보에서 부모 판정 불변·assertion 변화·변경 차원 표시 |
| SC-006 | 12개 행의 배지 종류가 배지 표와 같음(화면 시험) |
| SC-007 | 모든 라우트 응답 바이트를 강화 스캐너로 검사해 위반 0(이스케이프 경로 포함) |
| SC-008·009 | 사용성 검토 기록(quickstart §6): 6명, 질문당 3분, 질문별 6명 중 5명 이상 정답, 치명적 오독 0, 미검증 범위 질문 6명 중 5명 이상 |
| SC-010 | 라우트 목록에 Run·재시험·정리 확인 시작 경로 0, 사용법 오류 응답이 준비 상태 배지로 표시되지 않음 |
| SC-011 | actual validation 기록의 실행 PC·source SHA 기록, DEMO root 기록 100% DEMO 표시·실제 집계 제외 |

## Actual Validation Plan

[quickstart.md](./quickstart.md) §5. 요약: 위험 4 보완 병합 확인 → 두 저장소 branch·HEAD·dirty 기록 → fixture `h03-report-v1`로 H-03 `H03_DLQ_V2`
(새 checkout이면 독립 재현 gate 기록 겸용) → `H03_MINIMAL_V1` → E-03 BEFORE → E-03 AFTER → N-02 → fixture `spec004-report-v1`로 E-02(`374b122`) →
E-01 부모(`ce8d862`, FAIL 봉인) → E-01 재시험(`374b122`). 매 Run 전 preflight READY와 사람 승인. 웹을 띄워 네 화면을 이 기록으로 확인하고
사용성 검토를 한다. 이 기록은 Spec 005 웹 검증용이며 공식 상태를 바꾸지 않는다(D-018 추가 결정 3). H-03·E-03이 `374b122`에서 재현되지 않으면
멈추고 보고한다(research R-015 위험).

보성 확인(2026-10-08, 추천안):

- H-03·E-03은 `374b122`로 H-03 한 건을 먼저 실행한다. 결과가 공식 상태와 다르면 원인을 먼저 분류한다. seed나 실행기 결함이면 실패 시험부터
  쓰고 고친다. 대상 버전 문제면 멈추고 `511ae9e`로 바꿀지는 보성이 정한다.
- 그 H-03 `H03_DLQ_V2` 실행은 "현재 통합 대상(`374b122`) 기준" 독립 재현 gate 기록으로 인정한다. 플레이북 §6의 원래 지정 commit과 다르다는
  점을 Validation 기록에 적는다.
- 보성 PC의 스캐너 검사는 검사 스크립트가 생긴 뒤 보성이 실행하고 보고서만 받는다(Tasks 대기 작업).
- 위험 4 보완(Spec 004 재시험 정리 확인 경로)은 2026-10-08 기준 원격 Spec 004 브랜치에 아직 없다. actual validation 전에 병합을 확인한다(Tasks).

## Risks and Responses

| 위험 | 대응 |
|---|---|
| `374b122`에서 H-03·E-03 재현 실패(동의 확인이 들어간 대상, seed 보완 뒤 실제 Run 없음) | H-03 한 건 먼저. 다르면 원인 분류: seed·실행기 결함은 실패 시험부터 수정, 대상 버전 문제는 멈추고 보성 결정(R-015 확인됨) |
| 강화 스캐너가 기존 공식 bundle을 소급 INVALID로 만듦 | 봉인 시점 검사 버전으로 verify, 강화 결과는 비차단 필드(R-012) |
| 명령줄 출력 변경이 기존 소비자를 깨뜨림 | 키·종료 코드 유지, 값 형식·필드 추가만. 보성 확인 3건(R-004·R-009·R-010) |
| 로그인 없는 로컬 서버를 다른 웹 페이지가 호출 | `127.0.0.1` 전용, Host 검사, POST 토큰, CSP(R-002) |
| Playwright 브라우저 미설치 PC | 설치 명령 또는 설치된 Edge·Chrome 채널 사용(R-014) |
| 사용성 검토 참여자 확보 지연 | 태오 담당. 지연은 Validation에 기록 |

## Project Structure

### Documentation (this feature)

```text
specs/005-web-workbench-report/
├── spec.md
├── plan.md              # 이 파일
├── research.md          # 결정·이유·버린 대안
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── web-read-model.md
│   ├── web-http.md
│   ├── cli-output-additions.md
│   └── catalog.md
├── mockups/             # 승인 목업과 검토 기록
└── checklists/requirements.md
```

### Source Code (repository root)

```text
engine/
├── web/                 # 새 패키지
│   ├── __main__.py      # python -m engine.web
│   ├── server.py
│   ├── readmodel.py
│   ├── badges.py
│   ├── preflight.py
│   ├── memos.py
│   ├── templates/       # base, workbench, scenario, run, compare, report
│   └── static/          # workbench.css, workbench.js
├── evidence.py          # 경로 정규식, scan_bytes_strict, redaction_profile
├── presentation.py      # evidence_index, 사람용 문장 경계 redaction
└── cli.py               # run root 규칙, result_kind/error_kind, bundle_path 표기
catalog/
└── mvp-scenarios.yaml
scripts/
├── scan_bundles.py
└── prepare_web_demo.py
tests/
├── unit/                # 카탈로그·경로·스캐너·증적 색인·read model·배지
├── contract/            # CLI 추가 필드, 웹 HTTP
├── integration/         # 합성 bundle → 네 화면 뷰
└── web/                 # Playwright 화면 시험
```

**Structure Decision**: 단일 프로젝트에 `engine/web` 패키지를 더한다. 프런트엔드 빌드 단계가 없으므로 별도 frontend 프로젝트를 만들지 않는다.

## Complexity Tracking

없음. Constitution 위반이나 예외가 필요하지 않다.
