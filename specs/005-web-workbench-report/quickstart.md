# Quickstart: Spec 005 웹 워크벤치·보고서

이 문서는 구현 뒤 검증 절차의 안내다. 명령은 저장소 루트에서 실행한다. 개인 절대 경로 대신 `<ControlProof checkout>`,
`<WhyYou checkout>`을 쓴다. 공식 Run이 아니라 Spec 005 웹 검증 기록을 만드는 절차이며 각 시나리오의 공식 상태는 해당 Spec Validation을 따른다
(D-018 추가 결정 3).

## 1. 범위와 전제

- 화면은 PC 전용(1280px 기준, 1024px 이상)이고 `127.0.0.1`에서만 열린다. 로그인은 없다.
- 웹에서 시작할 수 있는 동작은 준비 상태 확인과 수정 메모뿐이다. Run·재시험·정리 확인은 명령줄로 한다.
- 실행 환경은 `LOCAL_EMULATED`, 실제 AWS는 `NOT_RUN`, 데이터는 합성, 외부 AI는 차단, 고정 모델 대체물을 쓴다.

## 2. 소스와 환경

1. 두 저장소의 branch·HEAD·dirty를 기록한다. ControlProof는 `005-web-workbench-report`, WhyYou는 `bosung/controlproof-n02-integration`
   (`374b122`)이며 둘 다 clean이어야 한다.
2. ControlProof 가상환경을 준비한다(Spec 004 quickstart §2). 화면 시험용 브라우저: `.venv` Python으로 `-m playwright install chromium`.
   설치가 막힌 PC는 설치된 Edge·Chrome 채널을 쓴다.
3. 각 PC 고유 환경 사항(DB 포트, `.env` 수동 로드, 보안 정책 우회 등)은 그 PC 담당자의 기록을 따른다. 이 문서에는 넣지 않는다.

## 3. 자동 gate

```text
.venv 의 python -m ruff check .
.venv 의 python -m pytest -q
.venv 의 python -m pytest -q tests/web        # 브라우저 화면 시험
```

예상: ruff 통과, 실패 0. 카탈로그 일치 시험이 범위표와 12/12, 응답 경로·토큰 스캔 위반 0.

## 4. DEMO 데이터로 화면 열기

```text
.venv 의 python -m scripts.prepare_web_demo --out .controlproof/web-demo
.venv 의 python -m engine.web --demo-root .controlproof/web-demo/runs
```

브라우저로 `http://127.0.0.1:8765/demo/`를 연다. 모든 화면 상단에 `DEMO DATA` 띠가 있어야 하고 실제 개수·보고서에 합성 기록이 섞이지 않아야 한다.

## 5. actual validation (웹 PC 재실행)

각 Run 전: 두 저장소 branch·HEAD·dirty 기록 → 해당 프로필 preflight `READY`(웹의 "준비 상태 확인" 또는 명령줄) → 사람 승인. 각 Run 뒤:
`show`·`verify` 결과와 Run ID·manifest SHA-256을 Spec 005 Validation에 기록한다.

0. 위험 4 보완(Spec 004 재시험 정리 확인 경로, FR-037)이 병합됐는지 확인한다.
1. fixture `h03-report-v1`로 WhyYou를 띄운다(Spec 004 quickstart §3, fixture 전환은 Spec 004 quickstart의 전환 절).
2. H-03 `H03_DLQ_V2` 한 건을 `374b122`로 먼저 실행한다(Spec 002 quickstart §7~§9). 새 checkout 조건을 갖췄으면 "현재 통합 대상(`374b122`) 기준"
   독립 재현 gate 기록으로도 남기고, 플레이북 §6의 원래 지정 commit과 다르다는 점을 함께 적는다.
   결과가 공식 상태(PASS)와 다르면 원인을 먼저 분류한다. seed·실행기 결함이면 실패 시험부터 쓰고 고친 뒤 다시 실행한다. 대상 버전 문제면 멈추고,
   `511ae9e`로 바꿀지는 보성이 정한다(research R-015, 보성 확인 2026-10-08).
3. H-03 `H03_MINIMAL_V1`(Spec 001 quickstart), E-03 `E03_BEFORE_V2`, `E03_AFTER_V2`(Spec 002 quickstart §7~§9).
4. N-02 `N02_CONSENT_ORDER_V1`(Spec 003 quickstart §6~§7). 결과는 웹 검증용이며 N-02 공식 상태는 Spec 003 converge를 따른다.
5. fixture `spec004-report-v1`로 전환하고 API·작업자를 다시 띄운다.
6. E-02 `E02_SCORING_FREEZE_V1`(`374b122`, Spec 004 quickstart §5~§6).
7. E-01 부모: WhyYou를 `ce8d862`로 둔 별도 checkout에서 실행한다(FAIL 예상, 봉인만 하고 고치지 않음).
8. E-01 재시험: WhyYou `374b122`로 같은 run root에서 `retest <부모 Run ID>`.
9. 웹을 실제 root로 띄운다: `.venv 의 python -m engine.web`(run root 규칙: `--run-root` > `CONTROLPROOF_RUN_ROOT` > `.controlproof/runs`).
   네 화면에서 SC-001~SC-007·SC-010·SC-011을 확인하고 결과를 Validation에 적는다.
10. 끝나면 API·작업자를 멈추고 fixture를 원래대로 되돌린다(Spec 004 quickstart §8).

## 6. 사용성 검토 (SC-008·SC-009)

- 진행: 태오. 참여자: 비작성자 6명(실행 담당자·검증 책임자·결과 검토자 각 2명).
- 화면: §5의 실제 기록으로 연 웹(DEMO가 아님).
- 과업 3개: (1) 12개 상태 읽기, (2) E-01 최초 FAIL의 판정 근거 증적 찾기, (3) E-01 재시험 비교에서 달라진 점 찾기.
- 질문 7개: Product Brief §10.3. 질문당 3분.
- 통과: 질문마다 6명 중 5명 이상 정답, 치명적 오독(`NOT_RUN`·`NO_TEST_TARGET`·`INCONCLUSIVE`를 통과로, AI 점수를 채용 결정으로, 결과를 법적
  인증으로 읽음) 0건, "무엇은 아직 검증하지 못했는가"에 6명 중 5명 이상이 범위표와 같은 답.
- 기록: 참여자 익명 ID·역할, 질문별 시간·정답·오독 유형, 사용한 Run ID를 Validation에 남긴다.

## 7. 스캐너 강화 전 기존 bundle 검사 (FR-036)

```text
.venv 의 python -m scripts.scan_bundles --run-root <실제 run root> --out .controlproof/web/scan-before-v2.json
```

검사 스크립트가 생긴 뒤 보성이 자기 PC에서 같은 명령을 실행하고 보고서의 요약(bundle ID·파일 상대 경로·규칙·건수)만 전달하면 Validation에
적는다. bundle은 옮기지 않는다.
두 PC 결과를 기록한 뒤에만 봉인 시점 검사를 v2로 바꾼다.
