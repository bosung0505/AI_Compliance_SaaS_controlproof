# ControlProof

2026-10-25 main 전달: 사용자가 검토 완료된 화면 가독성 후속(T025~T037)의 커밋·origin/main push와 로컬 서버 실행을 승인했다. [전달 범위·121개 검사·기존 테스트 문제](specs/010-platform-ui-integration/copy-publication-20261025.md). 기본 `shared-ui-n02-capture-20261023-r3`, 원본28/652 보존. 아래 미커밋/미게시 문구는 당시 이력이다.

2026-10-23 N02 후속: 기대/관찰을 좌우 두 박스로 복원하고 표 행의 상하 패딩을 1px→5px로 늘렸다. 확대 글씨·상시 표 유지. 기본 `shared-ui-n02-capture-20261023-r3`. [31개 검사·실제 확인](specs/010-platform-ui-integration/n02-recovery-capture.md). 아래 r2 배치는 이전 이력이다.

2026-10-23 N02 캡처 구간: 장애·복구 A6/A7만 큰 글씨·전폭 설명·상시 표로 밀집 배치했다. 기본 `shared-ui-n02-capture-20261023-r2`. [48개 검사·실측/캡처](specs/010-platform-ui-integration/n02-recovery-capture.md). 다른 조건·원본28/652·판정/API 보존.

2026-10-23 H02 제목 누락 보완: 전체 현황/결과/준비/보고서도 공통 새 표시 제목을 사용하고 검색에 새 이름을 반영했다. 기본 `shared-ui-scenario-title-20261023-r1`. [60개 검사·실제 확인](specs/010-platform-ui-integration/scenario-title-consistency.md). 원본28/652·API/판정 보존.

2026-10-23 H02 결과 핵심 요약: 문제 발견/재테스트 블록을 두 문장과 색·굵기로 강조하고 상세는 아래 접힌 영역으로 이동했다. 기본 `shared-ui-result-summary-20261023-r1`. [41개 검사·실제 화면·범위](specs/010-platform-ui-integration/result-summary-emphasis.md). 원본28/652·판정/API 보존.

2026-10-23 실행 결과 상단: 상세/비교·기록 선택을 결과 아래의 닫힌 영역으로 이동하고 제목·원본 확인 용어를 쉽게 표시했다. 기본 `shared-ui-result-header-20261023-r1`. [49개 검사·실제 PASS/FAIL 캡처](specs/010-platform-ui-integration/result-header-readability.md). 원본28/652·판정/API 불변.

2026-10-23 관찰 설명 보완: 기대 조건에 직접 답하는 결과, 소스 검토/실제 실행 범위와 세부 기록의 유무를 구분했다.
기본 `shared-ui-observations-20261023-r2`, 이전 카드 공유본·원본28/652·판정·계보 보존.
[변경·검증·한계](specs/010-platform-ui-integration/observation-readability.md). 작업 브랜치 미커밋/미게시.

2026-10-23 화면 명칭·탐색 정리: 보호조치 제목을 발표자료와 맞추고 현황 카드의 시나리오 링크를 일반 텍스트로 바꿨다.
기준별 ‘결과 보기’는 유지한다. 기본 공유본 `shared-ui-cards-20261023-r1`, 원본28/652·판정·12/9/0/3 불변.
[변경·검증·범위](specs/010-platform-ui-integration/control-card-readability.md). 작업 브랜치에서 미커밋/미게시다.

2026-10-22 main 게시 승인: 사용자가 현재 완성한 프로젝트를 ControlProof `origin/main`에 커밋/push하도록 지시했다.
이번 전달 대상은 main이며 기존 작업 기준fb219d0에 누적된 완료 기능/기록과 새 플랫폼 UI를 함께 반영한다.
현재 기본 공유본은 `shared-ui-main-20261022-r2`(하위 템플릿5개도 표시 pin에 포함)이다.
[게시 전 검증/범위](specs/010-platform-ui-integration/main-publication.md) · [화면 실행](specs/010-platform-ui-integration/quickstart.md).
아래 미커밋/미게시·기본 공유본 이름은 당시 단계 이력이다.

2026-10-22 최신: 안내/주의 문구를 상단의 닫힌 **검증 정보**로 통합했다. 본문은 수치·네 기준·실제 결과를 먼저 보여준다.
N03 일부/DEMO·오류는 유지하며95개 관련 검사와 실제8개 너비/열림 상태를 검수했다.
[현재 실행/변경/한계](specs/010-platform-ui-integration/presentation-polish.md). 기본 공유본은 `shared-ui-presentation-20261022-r1`이며,
이전 r3 JSON과28건/652원본은 보존한다. 아래 기본 r3/8784는 이전 시점 기록이다.

2026-10-21 최신: **Spec010 플랫폼 UI 전환 0~7단계 완료**. 새 화면이 기본 실행에 반영됐다.
현황·네 기준별 결과·정의/실행/증빙·실제 비교·보고서·테스트 준비를 기존 프로젝트 데이터와 연결했다.
사용자는 팀 검토를 완료로 간주하여 기본 전환을 승인했다. 원본28건/652파일·12/9/0/3·N03 일부는 불변이다.
[실행·화면 안내·복구](specs/010-platform-ui-integration/quickstart.md) · [최종 검증](specs/010-platform-ui-integration/stage7-validation.md).
작업은 미커밋/미게시이며 아래 단계별 대기/전환 전 문구는 당시 이력이다.

2026-10-21 Spec010 **6단계 T020/T021 완료**. 웹 관련324개 검사와 실제 앱44개 너비·키보드/동선 검수,
A4 26페이지 PDF의22개 내용·버전·근거/누락 링크·페이지 검수를 통과했다. 탐색 의미·DEMO 오류 복귀와 인쇄를 보완했다.
[현재 검수·실행](specs/010-platform-ui-integration/stage6-validation.md). 최종 후보 `stage6-shared-r3`; 원본28건/652파일 불변.
7단계 팀 이해도·기본 공유본 전환/복구가 남아 있다. 아래0~5단계는 당시 이력이다. 새 actual/게시는 없다.

2026-10-21 Spec010 **5단계 T018/T019 완료**. 실제 child 비교·22개 내용의 보고서·별도 테스트 준비와 로컬 메모 외형을 반영했다.
N01 측정 보강과 H02 서비스 보완, 원본 누락/무결성·N03 일부 범위를 구분한다. 현재 후보 `stage5-shared-r4`.
[현재 실행·검증](specs/010-platform-ui-integration/stage5-validation.md). 6단계 통합/PDF 검수·7단계 기본 전환은 남아 있다.
아래0~4단계 설명은 당시 이력이다. 원본28건/652파일과 기본 snapshot은 불변이며 새 실제 Run/게시는 없다.

2026-10-21 Spec010 **4단계 T013~T017 완료**: 실제 테스트 상세→선택 실행→증빙을 새 서비스 화면으로 연결했다.
프로필별 공식 대표/전체 이력·현재/봉인 정의·N03 일부 범위와 N01 PC/모바일 PNG·v1/v2를 구분한다.
현재 후보는 `stage4-shared-r4`이며 원본28건/652파일은 불변이다. 기본 공유본 전환·비교/보고서/별도 준비 화면 개편은 남아 있다.
[현재 실행 방법·검증](specs/010-platform-ui-integration/stage4-validation.md). 아래 0~3단계 문단은 당시 이력이다.

2026-10-21 Spec010 **3단계 T011/T012 완료**: 실제 업무 대시보드의 9/0/3 도넛·네 기준 카드,
`/results` 기준별 결과·검색/필터와 전체 진입 초기화를 적용했다. N03 일부 범위와 A 대상 없음, 기존 상세/이력을 보존한다.
현재 미리보기는 새 후보 `stage3-shared-r2`와 실행한다. 기본 공유본 전환·상세/PNG 개편은 후속 단계다.
[현재 실행 방법·검증](specs/010-platform-ui-integration/stage3-validation.md). 아래 0·1·2단계 문단은 당시 이력이다.

2026-10-21 Spec010 **2단계 완료**: 팀원 디자인의 서비스 소개 `/product`·도입 안내 `/guide`, 공통 헤더/탐색/테마를
현재 웹에 연결했다. 9/0/3은 카탈로그에서 읽으며 실제 기록과 합성 DEMO를 구분한다. 대시보드/목록 개편은 다음 단계다.
기존 28건/652파일은 보존했고 현재 표시 코드는 새 로컬 후보 공유본으로 실행한다. 기본 공유본은 아직 전환하지 않았다.
[실행 명령·56개 검사·브라우저 확인](specs/010-platform-ui-integration/stage2-validation.md).

2026-10-21 Spec010: 팀원 플랫폼 디자인을 실제 웹에 반영하기 위한 **0·1단계 명세·데이터/HTTP/PNG 계약 준비**를
`010-platform-ui-integration`에서 마쳤다. 현재 화면·API·판정·봉인 자료는 유지하며 신규 화면과 PNG 경로는 미구현이다.
현재 공유 기준은 `shared-actual-20261020-r2`, 28개 실행/11개 프로필/652파일이다.
[프론트엔드 반영 명세](specs/010-platform-ui-integration/spec.md) · [단계별 작업](specs/010-platform-ui-integration/tasks.md) ·
[이번 검증과 미실시 범위](specs/010-platform-ui-integration/validation.md).

2026-10-20 Spec 009: **N-01·N-03 실제 실행 완료**. N-01 final `d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18` PASS(PC·390px 모바일
동의 화면의 다섯 고지와 정책 식별값; ControlProof 측정 보강 뒤 재테스트, 부모 `48a70f5e…` PASS 보존), N-03 final
`f27b68e8-0df8-46b3-a198-c7917c2f08bb` PASS(이전 정책 거부·최신 정책 저장·과거 기록 불변; 실행 중 정책 교체는 미검증).
현재 **12개 관리 / 9개 실제 실행(N-03은 일부 범위) / 0개 NOT_RUN / 3개 NO_TEST_TARGET**. `LOCAL_EMULATED`, 합성 데이터,
외부 AI 차단, AWS 미검증. [Spec 009 마감 기록](specs/009-n01-n03-notice-scenarios/actual-closure.md).
아래 공유 열람 명령은 그대로이며, 두 시나리오 기록을 더한 새 공유본은 보성 검토 뒤 확정한다.

2026-10-19 Spec008: **실제 기록 공동 열람 구현**. `fixes-and-remaining-work`의 코드와 공유 기록을 함께 받으면
7개 완료 시나리오·9개 프로필의 결과·근거·계보를 같은 화면에서 볼 수 있다. 원본 25건/600개 파일을
`review-data/`에 포함한다. H03/E03도 상세 연결되며, N02 과거 중간 원본 1건의 부재와 원래 INVALID 중단 기록은 명시한다.
실제 결과 열람에 WhyYou·Docker·DB·.env는 필요 없다. [팀원 실행 방법](review-data/README.md) ·
[검증 기록](specs/008-shared-run-records/validation.md) · [기존 설계 이유](docs/research/Run_Record_Sharing_Preparation.md).

```powershell
& .\.venv\Scripts\python.exe -m scripts.share_records --verify
& .\.venv\Scripts\python.exe -m engine.web --shared-snapshot review-data/snapshot.json --port 8766
```

주소는 `http://localhost:8766/`. 기본 웹 모드는 공유 기록 읽기 전용이다. 새 테스트 준비·로컬 메모는
명시적 `--run-root <local-root>` 모드에서 사용한다. 공유 기록 조회와 새 독립 실행은 구분한다.

2026-10-19 결과 설명 보완: H-02 개요·실행 결과·비교 화면에서 **문제 발견 → WhyYou 개발 코드 보완 → ControlProof 재테스트**를 구분한다. 이전 FAIL과 실제 근거를 함께 보존하며 서비스 코드 보완은 별도 개발 작업임을 명시했다. 완료 시나리오 보완 이력은 [조사표](docs/research/WhyYou_Remediation_History_Audit.md) 참고. 실행 범위·봉인 판정·WhyYou 코드는 이번 표시 작업에서 변경하지 않았다.

2026-10-19 H-02 **2단계 로컬 범위 완료**. 최종 `c12c2ce8-f607-4be3-9524-0dec27dc7260` A1~A6 PASS / VERIFIED19 / 복구 성공.
현황 질문만으로 이전 데이터가 최종합격으로 바뀌던 최초 FAIL을 보존한 뒤, AI의 조회 연결을 조회 전용으로 수정했다.
조회4조건 상태 유지·같은 포지션35점 합격/90점 불합격 담당자 결정·독립44개 테이블 잔여행0을 확인했다.
현재 **12개 관리 /7개 실제 실행 /2개 NOT_RUN(N-01·N-03) /3개 NO_TEST_TARGET**. 고정 합성 AI이며 AWS·외부 모델 품질은 미검증.
이전 단계 상태와 수치는 당시 기록이다. 최신 소스·계보·한계는 [Spec007 검증 기록](specs/007-h02-capability-surface/actual-closure.md)를 따른다.

2026-10-19 H-02 **1단계 조사·검사 준비 완료, actual NOT_RUN**.
AI·워커 연결42개 항목을 수집했다. 간접 연결1개와 조회 중 데이터 초기화 경로는2단계 확인 대상이다.
실제 판정·공식 실행·결과 화면은 아직 진행하지 않았으며 현재 범위12/6/3/3을 유지한다. [Spec007 검증 기록](specs/007-h02-capability-surface/validation.md).

후속 수정·남은 작업의 통합 브랜치: **`fixes-and-remaining-work`** (2026-10-18 사용자 승인).
ControlProof는 `origin`, WhyYou의 같은 이름 브랜치는 `bosung0505/gbsa_aws` 포크에서 관리한다.

2026-10-18 H-01 2단계 actual 완료: **`39a0d317-b36d-4cf1-8b09-aebb404d5891` A1~A6 PASS / VERIFIED17**.
세 경로×다섯 주체15조건 통과, 복구 성공, 독립 읽기 감사44개 테이블 잔여행0·기본 회사/사용자 각1 보존.
최초 SYSTEM 일괄 이동 FAIL을 보존하고 해당 경로를 수정한 child 결과다. 고정 테스트용 AI이며 AWS/H-02는 미실행.
현재6개 실제 실행 완료·3개 NOT_RUN·3개 NO_TEST_TARGET. [상세 검증](specs/006-h01-human-decision/validation.md).

2026-10-18 최신: N-02 최종 재테스트 `16dbd987…` **A1~A7 PASS / VERIFIED21**,
복구 성공·실행 소유 DB 잔여행 0. 로컬 실행 목표 5개 완료. 자세한 기록은 Spec003
`actual-closure.md`·`validation.md`. 아래 과거 checkpoint는 이력을 보존한 것이다.


ControlProof는 합성 데이터를 이용해 AI 서비스의 절차적 보호조치가 정상·우회·예외·장애 조건에서 실제로 작동하는지 테스트하고, 판정과 재현 가능한 증적을 남기는 도구다. 첫 번째 검증 대상은 AI 면접 서비스 WhyYou다.

## 로컬 웹 워크벤치 (Spec 005)

2026-10-16 화면 용어를 테스트·재테스트·테스트용으로 통일했다. 비교 표는 '테스트에 넣은 AI 평가'와
'서비스가 실제 저장한 결과'를 보여준다. 원본 기록과 과거 검증 이력은 보존한다.

현재 UX 개편 브랜치는 `refactor/controlproof-web-ux`이며, `005-web-workbench-report`에서 분기했다. 웹은 구현되어 있으며 시나리오 개요·조건별 실제 관찰·연결 근거·재테스트 비교·보고서를 제공한다.
2026-10-15 승인 UX 개편은 공통 헤더·탐색·표·버튼을 유지하면서 E-01 조건별 관찰과 E-02 규칙 설명을 우선 개선한다.
봉인된 판정·파일은 수정하지 않으며, 원본 규칙의 개수와 조건별 관찰의 개수를 구분한다.

```powershell
.\.venv\Scripts\python.exe -m engine.web
# 다른 곳에 보관한 실제 기록을 볼 때:
.\.venv\Scripts\python.exe -m engine.web --port 8766 --run-root <실제-기록-폴더>
```

기본 주소는 `http://localhost:8765/`, 합성 화면은 `/demo/`다. 카탈로그의 공식 검증 이력과 현재 서버에 연결된 실제 기록은 구분한다.
시나리오 상단의 최근 결과 또는 실행 기록에서 개별 결과로 이동하고, 조건별 ‘이 결과의 확인 자료 보기’로 자료를 펼친다.
V4 원래 시나리오 이름 12개와 쉬운 설명을 함께 표시한다. E-01 결과는 실제 처리·복원 결과를 요약하고,
고정 테스트용 모델의 출력과 WhyYou 응답 검증 후 저장값을 비교한다. 새 테스트 준비 안내는 실행 기록 뒤에 있다.
상세와 문서에 보존한 별도 진단 범위: [결과 설명 보완](specs/005-web-workbench-report/readable-results.md).
웹에서 새 테스트·재테스트을 시작하지 않는다. 새 테스트 준비 상태는 과거 결과와 별도다.
준비 확인은 알려진 Windows 진단 로그가 섞여도 정상 JSON을 읽는다. 서버에 새 테스트용 설정이 없으면
'테스트 환경 설정 필요'와 다음 조치를 표시한다. 이는 READY를 뜻하지 않는다([오류 보완](specs/005-web-workbench-report/preflight-fix.md)).
Spec 005 전체 종료와 비작성자 사용성 검토는 아직 완료로 선언하지 않는다. 상세: [승인 UX 개편 명세](specs/005-web-workbench-report/ux-redesign.md).


## 현재 개발 기준

- 제품 범위: [ControlProof × WhyYou 2주 MVP 기능 범위 V4](./docs/product/ControlProof_WhyYou_2주_MVP_기능범위_v4.md)
- 시나리오 범위표: [12개 관리·9개 실행(N-03 일부)·0개 NOT_RUN·3개 NO_TEST_TARGET](./docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md)
- 제품 정의: [MVP Product Brief](./docs/product/ControlProof_MVP_Product_Brief.md)
- 제품 결정: [MVP Decision Log](./docs/product/ControlProof_MVP_Decision_Log.md)
- 개발 원칙: [ControlProof Constitution](./.specify/memory/constitution.md)
- 완료 기능: [Spec 001 — 실행·증적 기본 모델과 H-03 최소 수직 흐름](./specs/001-execution-evidence-h03/spec.md)
- 완료 명세: [Spec 002 — H-03·E-03 장애·재시도·DLQ 확장](./specs/002-h03-e03-fault-expansion/spec.md)
- Spec 002 재현 절차: [로컬 actual-stack quickstart](./specs/002-h03-e03-fault-expansion/quickstart.md)
- Spec 002 검증 기록: [자동·실제 스택 검증 결과](./specs/002-h03-e03-fault-expansion/validation.md)
- Spec 002 추적성: [요구사항→작업→테스트→구현](./specs/002-h03-e03-fault-expansion/traceability.md)
- 팀 인수인계: [현재 공식 상태·재현·검토 통합 가이드](./docs/TEAM_HANDOFF.md)
- AI 작업 플레이북: [다른 AI 세션에서도 같은 Spec Kit 사이클을 재현하는 방법](./docs/AI_SPEC_KIT_PLAYBOOK.md)
- Spec 003 소스 기준선: [WhyYou N-02 확인 사실과 미확인 사항](./docs/research/Spec003_N02_WhyYou_Source_Baseline.md)
- 작성된 기능 명세: [Spec 003 — N-02 동의·AI 처리 순서 검증](./specs/003-n02-consent-order/spec.md)
- Spec 003 기술 계획: [경계·lane·fault·인과관계·테스트 설계](./specs/003-n02-consent-order/plan.md)
- Spec 003 작업 목록: [테스트 우선 구현·최초 Run·조건부 보완 순서](./specs/003-n02-consent-order/tasks.md)
- Spec 003 검증 기록: [부모·child actual Run 원장, 회귀 기록, 알려진 한계](./specs/003-n02-consent-order/validation.md)
  — 최신 child `16dbd987…` A1~A7 PASS·VERIFIED21; 이전 `7b59237e…` INCONCLUSIVE는 보존
- Spec 003 구현 계약: [데이터 모델](./specs/003-n02-consent-order/data-model.md),
  [계약](./specs/003-n02-consent-order/contracts/),
  [구현 후 재현 절차](./specs/003-n02-consent-order/quickstart.md)
- 도입 결정: [ADR-0001 — Spec Kit과 팀 골격 채택](./docs/decisions/0001-adopt-spec-kit-and-skeleton.md)

`docs/reference/skeleton/`은 팀원이 만든 초기 골격의 원문 보관본이다. 제품 의미가 충돌할 때는 위 문서와 Constitution을 우선한다.

## Spec Kit

이 저장소는 GitHub Spec Kit 1.0.10을 다음 구성으로 초기화했다.

- Integration: Codex skills
- Scripts: PowerShell
- Feature numbering: sequential
- Extension: Git workflow

Codex에서 프로젝트를 다시 연 뒤 `.agents/skills/`의 기능을 사용한다.

```text
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

Spec 001과 Spec 002는 clarify, plan, tasks, analyze, implement와 actual-stack 검증을 마쳤다.
Spec 002는 로컬 WhyYou를 대상으로 H-03 재시도 소진·DLQ·결정 우회와 E-03 저장 전/후 장애,
사람 최종결정 멱등성, 봉인 증적과 불변 FAIL→PASS 재테스트을 구현했다. 이는 전체 2주 MVP나
ControlProof 웹 UI가 완성됐다는 뜻이 아니며, 현재 사용자 접점은 개발·검증용 CLI와 로컬 웹 워크벤치다. 웹의 실제 검증·내부 검토 기록은 Spec 005를 따른다.

## 후속 Spec 로드맵

후속 순서는 [Product Brief](./docs/product/ControlProof_MVP_Product_Brief.md)와
[Decision Log D-013](./docs/product/ControlProof_MVP_Decision_Log.md)을 기준으로 한다.

| 순서 | 상태 | 범위 |
|---|---|---|
| Spec 003 | Complete (LOCAL_EMULATED) | 2026-10-18 final child `16dbd987…`: A1~A7 PASS, VERIFIED21, restore SUCCEEDED, owned DB residues0. Historical failures preserved; exact source/manifest in Spec003 validation. |
| Spec 004 | Complete | T001~T097 및 converge 완료(T087 NOT_REQUIRED). 최초 E-01 FAIL 보존 → 승인 수정 child PASS; WhyYou 374b122에서 새 checkout E-01 4030503c…·E-02 970108fe… 실제 PASS/SUCCEEDED/VERIFIED, 잔여행 0. 전체 CP 939 PASS·WhyYou scoped 188 PASS. 다른 PC·AWS는 미검증. |
| Spec 005 | 웹 구현·실제 검증 기록·내부 UX 개편 중 | 조건별 관찰·연결 근거·공통 디자인. 전체 converge와 비작성자 사용성 검토는 별도 |

WhyYou 연결 기반을 별도 Spec으로 먼저 만들지 않는다. 각 시나리오에 필요한 capability를 해당 Spec의
수직 흐름 안에서 구현한다. 또한 세 Spec 문서만 먼저 완성한 뒤 개발하는 방식이 아니라, Spec 003의
Spec 004는 명세→구현→실제 검증→converge를 닫았다. 현재 웹 작업은 Spec 005이며, 구현·웹 실제 검증 기록 위에서 내부 UX 개편을 진행한다. 최종 converge는 별도다.

Spec 001·002의 actual Run은 현재 한 PC에서만 수행됐다. main 통합 전 다른 팀원이 새 checkout에서
`H03_DLQ_V2` 한 건을 재현해 source SHA·manifest SHA-256·restore 결과를 Validation에 추가해야 한다.
이 외부 gate 전에는 “독립 재현 완료”라고 표현하지 않는다.

## 개발 환경

프로젝트 코드는 Python 3.12 이상을 요구한다.

```powershell
uv sync --extra dev
uv run pytest
```

로컬 보안 도구가 `uv sync`의 Python 탐색 출력을 방해하는 Windows 환경에서는 다음 방식으로 같은 개발환경을 만들 수 있다.

```powershell
python3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

## 저장소와 브랜치 안전성

Spec 002는 나란히 있는 두 저장소를 사용한다.

| 저장소 | 허용 브랜치 | 용도 |
|---|---|---|
| `AI_Compliance_SaaS_controlproof` | `yeonwoo/004-e01-e02-score-evidence` | Spec 001~003 기반(병합된 `003-n02-consent-order`)과 현재 기능 Spec 004 |
| `gbsa_aws` | `bosung/controlproof-n02-integration` | WhyYou local/test 전용 N-02 observer·fault hook; product guard 변경 전 최초 사실 테스트 대상 |

WhyYou의 `main`에 ControlProof 변경을 직접 commit 또는 push하지 않는다. actual Run 전에는 두 checkout이
모두 clean이어야 하며, preflight가 commit·dirty 상태와 target snapshot을 다시 고정한다. `.env`,
credential, 원본 queue URL, receipt handle, message body와 실제 지원자 자료는 commit하거나 bundle에
복사하지 않는다.

처음 합류한 팀원은 아래를 먼저 확인한다.

```powershell
$controlProofRepo = (Resolve-Path -LiteralPath "<ControlProof-checkout>").Path
$whyYouRepo = (Resolve-Path -LiteralPath "<WhyYou-checkout>").Path

Set-Location -LiteralPath $controlProofRepo
git branch --show-current
git status --short

Set-Location -LiteralPath $whyYouRepo
git branch --show-current
git status --short
```

두 placeholder는 각 팀원의 실제 checkout으로 한 번만 바꾼다. 두 저장소가 같은 부모 폴더에 있을
필요는 없다.

## 실행 프로필의 의미

| Profile | Scenario | 테스트하는 경계 | 핵심 질문 |
|---|---|---|---|
| `H03_MINIMAL_V1` | H-03 | Spec 001 최소 흐름 | 기본 장애·복구·사람 최종결정 안전성이 작동하는가 |
| `H03_DLQ_V2` | H-03 | 저장 전 반복 장애와 DLQ | 실패가 숨지 않고 세 최종결정 경로가 모두 차단되는가 |
| `E03_BEFORE_V2` | E-03 | 결과 내구 저장 전 | 장애 중 부분 효과가 없고 복구 후 reporting·사람 결정 효과가 정확히 한 세트인가 |
| `E03_AFTER_V2` | E-03 | DB commit 후 SQS ack 전 | 재전달이 handler를 다시 실행하지 않고 duplicate-ack로 끝나는가 |

H-03과 E-03은 일부 증적을 공유해도 독립 verdict다. BEFORE PASS가 AFTER 미실행을 대신하지 않으며,
AI 점수는 어떤 profile에서도 자동 합격·탈락 조건이나 verdict 입력으로 사용하지 않는다.

## 실행 흐름

실제 실행 전 `.env.example`의 로컬 전용 변수들을 별도 `.env` 또는 shell에 설정한다. 운영 URL,
운영 DB, 실제 지원자 자료를 사용하면 안 된다.

```powershell
controlproof preflight H-03 --target whyyou-local --json
controlproof run H-03 --target whyyou-local --label first-h03 --json
controlproof show <RUN_ID> --json
controlproof verify <RUN_ID> --json
controlproof retest <RUN_ID> --target whyyou-local --label after-fix --json
```

Spec 002는 profile을 명시한다. E-03은 profile 생략을 허용하지 않는다.

```powershell
controlproof preflight H-03 --profile H03_DLQ_V2 --target whyyou-local --json
controlproof preflight E-03 --profile E03_BEFORE_V2 --target whyyou-local --json
controlproof preflight E-03 --profile E03_AFTER_V2 --target whyyou-local --json

controlproof run H-03 --profile H03_DLQ_V2 --target whyyou-local --label h03-local --json
controlproof run E-03 --profile E03_BEFORE_V2 --target whyyou-local --label e03-before-local --json
controlproof run E-03 --profile E03_AFTER_V2 --target whyyou-local --label e03-after-local --json
```

- preflight가 `READY`가 아니면 Run은 만들어지지 않는다.
- target의 보호조치가 실제로 실패한 정상 테스트 결과는 exit 3이다. 이는 ControlProof 구현 실패가 아니다.
- 실행 중 오류나 중단 뒤에도 restore를 먼저 수행한다.
- `RESTORE_FAILED`이면 같은 target/subject의 다음 Run이 막힌다. marker 부재와 target 안전을
  확인한 evidence 파일로만 `cleanup-confirm`할 수 있으며 force 해제는 없다.
- `verify`는 원본을 고치지 않고 hash, manifest, artifact envelope, scenario/target 연결을 검사한다.
- `retest`는 부모 bundle을 수정하지 않고 새 Run과 `retest-diff.json`을 만든다. 부모가 이미
  PASS라면 데모를 위해 결함 버전을 만들 필요가 없다.

최초 actual Run의 FAIL은 테스트기 실패로 덮어쓰지 않는다. 먼저 bundle을 봉인하고 `verify`한 뒤,
그 증적으로 확인된 제품 또는 판정 경계만 수정한다. 수정 후 결과는 반드시 새 child Run으로 만들고
부모 FAIL의 manifest digest와 모든 파일을 그대로 보존한다. Spec 002의 실제 H-03/E-03 계보와
manifest SHA-256은 [검증 기록](./specs/002-h03-e03-fault-expansion/validation.md)에 있다.

## 결과를 읽는 법과 주장 범위

- `PASS`: 그 Run에서 실행한 profile의 모든 필수 assertion, 증적 무결성과 환경 복구가 확인됐다.
- `FAIL`: 관찰 가능한 보호조치 위반·누락·중복이 직접 확인됐다. ControlProof 실행기 자체 실패와 다르다.
- `INCONCLUSIVE`: 접근 제한, 증적 부족·충돌 또는 복구 불확실성 때문에 제품 PASS/FAIL을 주장할 수 없다.
- `NOT_RUN`: 실행하지 않은 환경 또는 범위다. 실제 AWS는 현재 항상 `NOT_RUN`이다.

모든 결과의 정확한 주장 범위는 `EXECUTED_SCENARIO_AND_EVIDENCE_ONLY`다. ControlProof는 실행한
시나리오와 수집·검증한 증적만 보고하며, **서비스 전체의 법적 준수를 인증하거나 보증하지 않는다.**

공식 target은 `whyyou-local`, 환경은 `LOCAL_EMULATED`다. LocalStack의 SQS/DLQ PASS는 로컬 메시징
계약에만 적용된다. 실제 AWS SQS·ECS·IAM·CloudWatch·운영 네트워크를 검증한 결과가 아니며,
향후 staging/AWS를 검증하려면 별도 target ID와 새 Run을 만들어야 한다. 로컬 verdict나 bundle을
클라우드 결과로 복사·승격하지 않는다.

처음 합류한 팀원은 먼저 [팀 통합 인수인계](./docs/TEAM_HANDOFF.md)를 읽고, Spec 002는
[Spec 002 quickstart](./specs/002-h03-e03-fault-expansion/quickstart.md)를 따른다. Spec 001의 상세
실제 스택 재현 절차는 [Spec 001 quickstart](./specs/001-execution-evidence-h03/quickstart.md),
CLI 결과 검토 정책과 웹 UX 이관 결정은
[review policy](./specs/001-execution-evidence-h03/review-usability-checklist.md)를 따른다.

## 구현 구조

- `engine/`: 실행·관찰·판정·증적·재테스트 엔진
- `scenarios/`: 버전 고정 H-03 시나리오와 템플릿
- `seeds/`: 합성 상태 seed 구현
- `tests/`: 단위·계약·통합·보안 회귀 테스트
- `specs/`: 기능별 Spec·Plan·Tasks·검증 기록
- `.specify/`: Spec Kit 설정·스크립트·템플릿·Constitution
- `.agents/skills/`: Codex용 Spec Kit skills

- `engine/runner.py`: profile dispatch와 Spec 001 호환 실행
- `engine/executors/`: H-03 DLQ, E-03 BEFORE/AFTER 실행과 봉인 orchestration
- `engine/evidence.py`: redaction, 원자 저장, manifest 봉인, 읽기 전용 검증
- `engine/judges/`: H03-A7~A9와 E03-A1~A8 증적 기반 판정
- `engine/judge.py`: Spec 001 H03-A1~A6와 공통 verdict 우선순위
- `engine/presentation.py`: 비개발자 검토용 요약
- `engine/retest.py`: 부모 불변 재테스트 계보와 diff
- `engine/adapters/whyyou/`: WhyYou HTTP/DB/브라우저/fault/capability 경계
- `scenarios/H-03.yaml`: Spec 001 버전 고정 시나리오
- `scenarios/H-03-DLQ.yaml`, `E-03-BEFORE.yaml`, `E-03-AFTER.yaml`: Spec 002 profile snapshot
- `tests/`: 단위, 계약, 통합 및 합성 bundle case


## Spec 004 완료 checkpoint (2026-10-08)

ControlProof 전달 브랜치 `yeonwoo/004-e01-e02-score-evidence`; 실행 코드 checkpoint
`f75ada7172fc48802e231d24e08886de4292c276` (Q1 실제 실행은 ca3df77, Q2는 f75ada7).
WhyYou `bosung/controlproof-n02-integration`:
`374b122e1296c0159ccd88ed4763d358973c59cb`. 이후 문서 마감 commit을 Run source로 바꿔 적지 않는다.

재현은 [Spec 004 Quickstart](specs/004-e01-e02-score-evidence/quickstart.md) 하나를 따른다.
`scripts/spec004_local.py`가 별도 합성 DB·큐·고정 모델 API/작업자를 기동한다. 실제 AI 키와 `.env`는 필요 없다.
이 2026-10-08 checkpoint 당시 원본 bundle은 Git 전달 대상이 아니었다. 당시 재실행 방법과 상세 Run ID·manifest·시간·
명령·이식성 수정·한계는 [Validation](specs/004-e01-e02-score-evidence/validation.md) 마지막 closure 기록에 있다.
현재 공유 정책은 D-029와 위 준비 문서를 따른다. 기존 결과 열람과 새 Run 실행은 구분한다.

같은 PC의 두 번째 clean checkout 재현은 승인된 SC-006 기준을 충족한다(ID-004-36/D-017).
다른 PC 재현과 main 통합 승인은 별도이며 아직 완료되지 않았다. AWS NOT_RUN, 전체 MVP 미완료,
이 문단은 2026-10-08 checkpoint다. N-02의 최신 결과는 아래 2026-10-18 closure를 따른다.


## N-02 문서 분석 후속 준비 — 2026-10-18

두 저장소의 작업 브랜치 `feature/n02-analysis-preparation`에서 1단계 구현·자동 검증을 마쳤다.
상세 명세·분할 범위·검증 원장은 [Spec003 후속 기록](specs/003-n02-consent-order/analysis-preparation.md).
1단계 시점에는 기존 INCONCLUSIVE 및 4개 완료 상태를 유지했다. 이후 2단계의 최신 결과는 아래와 같다.
기존 UX 미커밋 변경도 그대로 보존했으며 이번 단계에서 웹 디자인은 수정하지 않는다.

## N-02 2단계 로컬 마감 — 2026-10-18

최종 Run `16dbd987-23a5-4030-bb62-77787488969b`: COMPLETED/PASS, A1~A7 PASS,
VERIFIED21, 복구 SUCCEEDED, DB 잔여행0. 문서 분석도 실제 업로드·모델 응답 검증·저장 경로로 완주했다.
CP 실제 실행 소스 `3ea1509`, WhyYou `e64ff9d`; 원래 작업 폴더의 미커밋 UX 변경은 보존했다.
초기 INVALID와 중간 실행 뒤 정리 결함은 새 실행으로 보완했고 원본은 유지했다.
재현은 `scripts/n02_local.py`와 Spec003 Quickstart의 2026-10-18 절차를 따른다.
화면: http://localhost:8766/scenarios/N-02 / 최종 실행은 해당 화면의 실행 기록에서 연다.
AWS NOT_RUN, 고정 테스트 모델 사용, 별도 PC 재현·main 통합·Spec005 전체 마감은 별도다.
