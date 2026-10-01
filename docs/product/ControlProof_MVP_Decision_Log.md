# ControlProof × WhyYou 2주 MVP 결정 기록

## 0. 문서 정보

- 기준일: 2026-09-23
- 상태: MVP 구현 기준으로 확정. 팀 합의 전 제품 책임자의 위임에 따른 임시 기준이며, 변경 시 이 문서에 변경 이유와 영향을 추가한다.
- 적용 범위: `ControlProof_WhyYou_2주_MVP_기능범위_v4.md`, `ControlProof_MVP_Product_Brief.md`, 후속 Spec Kit 문서와 구현
- 목적: 구현 중 같은 논의를 반복하거나, 편의상 제품 의미가 달라지는 것을 막는다.

## 1. 결정 원칙

결정이 충돌할 때는 다음 순서로 우선한다.

1. V4에 확정된 제품 원칙과 2주 범위
2. 시험 결과를 나중에 재현하고 설명할 수 있는가
3. `대상 없음`, `실행 불가`, `관찰 부족`, `실패`, `통과`를 서로 오인하지 않는가
4. WhyYou 운영 데이터와 실제 지원자에게 영향을 주지 않는가
5. 2주 안에 하나의 완결된 수직 흐름을 실제로 시연할 수 있는가

결정 상태는 다음과 같이 사용한다.

- `확정`: 현재 MVP 구현의 기본값이다.
- `재검토 조건`: 조건이 발생하면 팀이 변경 여부를 논의한다. 조건이 발생하지 않은 상태에서 구현자가 임의로 바꾸지 않는다.

---

## D-001. 실행과 시험 대상의 관계

- 상태: 확정
- 결정: 하나의 `Run`은 한 시나리오를 한 번 실행한 단위다. 한 Run 안에 여러 합성 지원자를 둘 수 있으며, 모든 관찰값과 증적에는 반드시 `subject_ref`를 기록한다. 지원자별 하위 Run은 MVP에서 만들지 않는다.
- 이유: 장애 조건과 대조군을 같은 실행 조건 안에서 비교해야 하는 H-03·E-03 유형은 여러 시험 대상을 한 Run에서 다루는 편이 의미가 명확하다. 반대로 `subject_ref`가 없으면 서로 다른 지원자의 점수·결정·증적이 섞일 수 있으므로 대상 식별은 필수다.
- 영향: 단일 지원자 시나리오도 `subject_ref`를 가진다. Run 결과는 시나리오 전체 판정이며, 개별 assertion은 대상별 결과를 남길 수 있다.
- 재검토 조건: 하나의 Run이 수백 건 이상을 처리해 실행·증적 크기가 과도해지거나, 지원자별 독립 재시험 요구가 생길 때 하위 실행 모델을 검토한다.

## D-002. 관찰 구간과 단계 식별

- 상태: 확정
- 결정: 관찰값에는 `phase`, `step_id`, `attempt`를 모두 둔다. `phase`는 `BASELINE`, `INJECTED`, `RECOVERED`의 세 값으로 고정하고, 세부 순서는 시나리오의 `step_id`로 표현한다. 재시도는 `attempt`로 구분한다.
- 이유: 구간만 있으면 어느 동작에서 나온 값인지 알 수 없고, 단계 ID만 있으면 전후 비교가 시나리오마다 달라진다. 세 필드를 함께 사용해야 정상 상태, 장애 중 상태, 복구 후 상태와 재시도를 안정적으로 비교할 수 있다.
- 영향: 모든 시나리오는 적어도 하나의 phase와 step을 선언한다. 시간에 따라 값이 달라져도 phase·step·attempt가 다르면 그 자체로 증적 충돌이 아니다.
- 재검토 조건: 장시간 부하 시험처럼 세 구간으로 표현할 수 없는 시험 유형을 도입할 때 phase 확장을 검토한다.

## D-003. 증적 충돌 판정 기준

- 상태: 확정
- 결정: `run_id + subject_ref + phase + step_id + attempt + key`가 모두 같은 관찰값 가운데, 같은 사건이나 상태를 표현해야 하는 독립 출처의 비결측 값이 허용 범위를 넘어 다를 때만 `EVIDENCE_CONFLICT`로 판정한다. 서로 다른 구간·단계·재시도의 값 변화는 충돌로 보지 않는다. 비동기 시스템은 시나리오가 정한 관찰 대기 시간 뒤의 안정화 값을 판정에 쓰되, 원시 시계열은 모두 보존한다.
- 이유: 현재 골격처럼 같은 key의 값이 다르다는 이유만으로 충돌 처리하면 정상적인 상태 전이가 전부 충돌이 된다. 충돌은 시간 변화가 아니라 같은 사실에 대한 모순이어야 한다.
- 영향: 시나리오는 비교 대상 출처, 안정화 시간, 허용 오차를 필요할 때 명시한다. 값이 없으면 충돌이 아니라 `INSUFFICIENT_EVIDENCE` 후보가 된다.
- 재검토 조건: 분산 추적 ID나 이벤트 버전으로 동일 사건을 더 정확히 묶을 수 있게 될 때 동일성 기준을 강화한다.

## D-004. 원본 증적 보관 방식

- 상태: 확정
- 결정: MVP는 혼합 방식을 쓴다. ControlProof가 실행 중 생성하거나 조회한 핵심 산출물인 HTTP 요청·응답, 화면 캡처, 추출한 로그·DB 조회 결과, 장애 주입·복구 기록은 Run의 증적 저장소에 복사한다. 동시에 원본 위치와 조회 조건을 locator로 남긴다. 전체 로그나 전체 DB 덤프는 복사하지 않는다.
- 이유: locator만 남기면 원본 보존 기간이나 환경 변화 때문에 데모와 사후 설명이 깨질 수 있다. 반대로 전체 데이터를 복사하면 개인정보와 저장 비용이 커진다. 판정에 사용한 최소 원본을 보존하는 방식이 재현성과 최소 수집을 함께 만족한다.
- 영향: 저장 전에 비밀값과 개인정보를 마스킹한다. 판정에 사용하지 않은 대량 데이터는 보관하지 않는다.
- 재검토 조건: 외부 고객 환경처럼 원본 반출이 금지되는 배포 방식을 지원할 때 해시·서명된 locator 전용 모드를 검토한다.

## D-005. 증적 무결성 해시

- 상태: 확정
- 결정: 모든 저장 증적에 SHA-256 해시, 수집 시각, MIME 유형, 크기를 필수로 기록한다. locator만 허용되는 증적은 판정에 사용한 정규화 추출물의 SHA-256을 남긴다. 전자서명과 공인 시점확인은 MVP 범위에서 제외한다.
- 이유: 해시는 구현 비용이 작으면서 결과 생성 뒤 증적이 바뀌지 않았는지 확인할 수 있다. 외부 서명 인프라는 2주 목표에 비해 과하다.
- 영향: 해시 생성에 실패한 증적은 완전한 증적으로 간주하지 않으며, 그 증적이 필수이면 판정 불가가 된다.
- 재검토 조건: 외부 감사 제출이나 법적 부인방지 수준이 필요해지면 서명, 체인 해시, 신뢰 시점확인을 추가 검토한다.

## D-006. 실행 중단과 복구 실패 상태

- 상태: 확정
- 결정: 실행 생명주기는 `PENDING`, `RUNNING`, `RESTORING`, `COMPLETED`, `ABORTED`, `RESTORE_FAILED`로 관리한다. 실행이 중단되거나 복구에 실패한 Run은 PASS/FAIL이 될 수 없으며, 표시 결과는 `INCONCLUSIVE`와 구체적 reason code를 사용한다. `RESTORE_FAILED`가 발생하면 위험 배너를 표시하고 수동 정리 확인 전까지 같은 대상의 추가 장애 시험을 막는다. `NOT_RUN`은 실행 전 시나리오 상태이지 생성된 Run의 상태가 아니다.
- 이유: 실행 상태와 통제 판정을 섞으면 시험기가 고장 난 일을 제품 통제 실패나 통과로 오인한다. 복구 실패 뒤 시험을 계속하는 것은 격리 환경도 오염시킬 수 있다.
- 영향: 복구 동작은 성공·실패와 관계없이 증적에 남는다. 중단된 Run도 삭제하지 않고 보존한다.
- 재검토 조건: 자동 환경 재생성으로 복구 실패를 완전히 격리할 수 있을 때 후속 실행 차단 정책을 조정한다.

## D-007. 브라우저 자동화 범위

- 상태: 확정
- 결정: Playwright는 N-01의 PC·모바일 고지 표시, 핵심 화면 이동, 화면 캡처에 사용한다. API·로그·DB 기반 검증은 pytest와 HTTP/adapter 계층으로 수행한다. WhyYou의 전체 사용자 흐름을 브라우저로 자동화하지 않는다. 수동 확인이 남으면 자동화된 결과와 섞지 않고 `MANUAL` 수집 방식으로 표시한다.
- 이유: 2주 동안 전체 UI 자동화까지 하면 취약한 셀렉터 유지에 시간이 소모된다. 화면에서만 증명 가능한 항목은 브라우저로, 시스템 상태는 더 안정적인 인터페이스로 확인하는 것이 적절하다.
- 영향: N-01은 두 viewport의 증적을 필수로 갖는다. 브라우저 자동화 실패는 대상 부재가 아니라 실행기 준비 또는 접근 문제로 분류한다.
- 재검토 조건: WhyYou UI가 안정된 테스트 ID와 테스트 환경을 제공하면 자동화 범위를 확대한다.

## D-008. H-03 첫 수직 흐름과 DLQ 범위

- 상태: 확정
- 결정: 첫 번째 수직 흐름에서는 `리포트 생성 실패 주입 → 담당자 화면에서 리포트 없음 표시 → 그 상태에서 최종 결정 차단 여부 확인 → 복구 → 증적·판정 생성`까지 구현한다. DLQ 전환과 재시도 소진 검증은 첫 수직 흐름 이후 H-03·E-03 완성 단계에 추가한다. 최종 2주 MVP 범위에서는 DLQ 누락 여부까지 포함한다.
- 이유: 가장 먼저 Run·Observation·Evidence·Verdict의 계약과 FAIL→수정→PASS 흐름을 검증해야 한다. DLQ부터 결합하면 메시징 세부 구현이 제품 의미 검증을 가린다. 다만 V4의 필수 실패 시나리오이므로 최종 범위에서는 제외하지 않는다.
- 영향: 기능 Spec은 H-03을 최소형과 확장형 acceptance criteria로 나눈다. 최소형 완료를 H-03 전체 완료로 보고하지 않는다.
- 재검토 조건: WhyYou 테스트 환경에 재시도와 DLQ를 제어할 접점이 없다면 `NO_TEST_TARGET`이 아니라 runner/adapter 미준비로 기록하고 대체 주입점을 별도 결정한다.

## D-009. 멱등성 책임 시나리오

- 상태: 확정
- 결정: 같은 요청 재전송과 재시도 시 Outbox 이벤트·결정 이력이 중복 또는 누락되지 않는지는 E-03의 핵심 판정으로 둔다. H-03은 리포트가 없을 때 사람의 결정을 안전하게 막거나 명확히 경고하는지만 판정한다. 한 번의 통합 실행에서 두 시나리오의 증적을 함께 수집할 수는 있지만 assertion과 verdict는 분리한다.
- 이유: H-03은 인간 결정 안전성, E-03은 장애 시 증적 완전성을 검증한다. 같은 동작을 공유해도 책임을 분리해야 실패 원인과 개선 담당이 명확하다.
- 영향: 중복 실행 방지 key와 이벤트 이력 확인은 E-03 Spec에서 정의한다. H-03 결과가 PASS여도 E-03이 자동으로 PASS가 되지 않는다.
- 재검토 조건: 두 시나리오가 실제 구현상 완전히 같은 통제 하나로 합쳐질 경우에도 보고서의 요구사항 추적성은 두 개로 유지한다.

## D-010. 첨부 골격의 채택 방식

- 상태: 확정
- 결정: `controlproof-skeleton_1`은 새로 버리는 샘플이 아니라 구현 시작점으로 채택한다. 단, 현재 코드·YAML·스키마는 spike이며 불변 계약이 아니다. 실제 개발 저장소로 반영하기 전에 Observation 식별 차원, readiness와 결과 분리, 충돌 판정, reason code를 먼저 바로잡고 그 위에 adapter와 UI를 만든다.
- 이유: scenario-as-data, Run/재시험, adapter 경계, 판정 엔진과 seed 구조는 재사용 가치가 있다. 그러나 현재 상태로 확장하면 서로 다른 지원자·구간의 관찰값이 섞이고 실행기 미준비가 대상 부재로 오판될 수 있다.
- 영향: 기존 테스트는 보존하되 새 계약에 맞게 수정한다. 현재 H-03 YAML을 제품 명세로 간주하지 않는다. 새 코드는 승인된 기능 Spec과 연결되어야 한다.
- 재검토 조건: 골격의 라이선스·의존성·구조가 실제 팀 저장소와 결합 불가능한 것으로 확인될 때 핵심 모델과 테스트만 이식한다.

## D-011. 판정 불가 reason code 표준

- 상태: 확정
- 결정: MVP의 표준 판정 불가 코드는 `NO_TEST_TARGET`, `ACCESS_LIMITED`, `INSUFFICIENT_EVIDENCE`, `EVIDENCE_CONFLICT` 네 개로 고정한다. 실행 준비 상태는 별도로 `READY`, `RUNNER_NOT_READY`, `ACCESS_BLOCKED`, `NO_TEST_TARGET`을 사용한다. 문서·YAML·코드·화면은 같은 이름을 사용한다.
- 이유: 현재 골격은 가이드와 코드의 명칭이 다르고, fault injector 미구현을 대상 없음으로 처리할 가능성이 있다. 결과와 실행 준비 상태를 분리해야 제품 부재, 권한 부족, 실행기 미구현을 정확히 설명할 수 있다.
- 영향: `NO_ACCESS`, `EVIDENCE_MISSING`, `CONFLICT` 같은 별칭은 새 구현에서 사용하지 않는다. 이전 샘플을 읽어야 한다면 입력 시 변환하고 출력은 표준 코드로만 한다.
- 재검토 조건: 실제 시나리오에서 네 코드로 설명할 수 없는 독립적인 판정 불가 사유가 반복 확인될 때만 코드를 추가한다.

## D-012. CLI 사람 시간 측정은 웹 결과 UX 검토로 이관

- 상태: 확정
- 변경일: 2026-09-27
- 변경 전: canonical PASS·FAIL·INCONCLUSIVE CLI 출력 세 건을 비작성자 1명이 건별 120초 안에 해석하는 시험을 Spec 001 완료 gate로 사용한다.
- 변경 후: CLI의 verdict, 핵심 이유, assertion, 증적 경로·SHA-256, 복구 상태와 미검증 범위는 자동 계약·통합 시험으로 검증한다. 사람 대상 시간 측정과 이해도 평가는 실제 고객용 웹 결과 화면이 구현된 후 별도 UX Spec에서 수행한다.
- 이유: CLI는 개발·검증 인터페이스이며 최종 고객 화면이 아니다. 정해진 필드의 존재와 연결은 자동 시험이 더 정확하고, CLI 읽기 시간은 웹 화면의 정보 구조와 시각적 탐색성을 대표하지 않는다.
- 영향: Spec 001의 SC-008과 T055를 자동 projection 검증으로 변경하고 Spec 001을 종료한다. 기존 합성 세 verdict package는 선택적 개발 데모로 유지하되 사람 시간 측정을 통과한 것으로 기록하지 않는다.
- 승인: 제품 책임자 요청
- 재검토 조건: 웹 결과 화면의 정보 구조와 대상 사용자 역할이 확정되면 표본, 과업, 제한 시간, 오답 기준을 새로 결정한다.

## D-013. Spec 003~005 후속 수직 흐름과 개발 순서

- 상태: 확정
- 결정일: 2026-09-30
- 변경 전: `남은 WhyYou 연결과 시험 조건`, `워크벤치와 보고서`, `나머지 대표 시나리오`를 A/B/C
  후보로 두었고, 실제 Spec 번호·경계·순서를 확정하지 않았다.
- 변경 후: Spec 003은 N-02 동의·AI 처리 순서, Spec 004는 E-01·E-02 점수 근거·평가 기준 보존,
  Spec 005는 웹 워크벤치·12개 시나리오 카탈로그·보고서로 진행한다.
- 연결 기반 결정: `남은 WhyYou 연결과 시험 조건`은 독립 Spec으로 만들지 않는다. 시나리오와 무관한
  범용 기반을 선행 구축하지 않고, N-02에 필요한 경로 시드·관찰·주입·복구는 Spec 003에,
  E-01·E-02에 필요한 잘못된 인용·기준 변경 조건과 수집 adapter는 Spec 004에 포함한다.
- 개발 순서: 각 Spec은 `clarify → plan → tasks → analyze → implement → actual validation → converge`를
  완료한 뒤 다음 Spec으로 넘어간다. Spec 003~005의 문서만 먼저 만든 뒤 개발을 시작하는 방식으로
  해석하지 않는다.
- V4와의 관계: H-03·E-03은 Spec 001·002에서 완료됐다. Spec 003이 N-02를 실제 완주하면 V4의
  비협상 대표 시나리오 세 개가 모두 완주된다. Spec 004는 V4 기반에서 요구한 잘못된 인용·기준 변경
  조건과 E-01·E-02 검증을 닫는다. Spec 005는 12개 시나리오 관리와 결과물 완료 기준을 닫는다.
- 남은 시나리오 처리: A-01~A-03은 기능을 새로 만들지 않고 `NO_TEST_TARGET`로 보고한다.
  H-01·H-02·N-01·N-03의 전체 실제 실행은 V4의 목표 상한이므로 Spec 005에서 `NOT_RUN`과 readiness를
  사실대로 표시하고, 실제 완주를 요구하려면 별도 후속 Spec 또는 명시적인 범위 변경을 승인한다.
- 완료 의미: Spec 005까지 구현·실제 검증을 완료하고 V4 완료 기준을 다시 확인해야 2주 MVP 완료로
  판정할 수 있다. Spec 문서 세 개의 작성 완료만으로 MVP 완료 또는 개발 착수 상태를 주장하지 않는다.
- 이유: Spec 001·002에서 검증한 것처럼 한 수직 흐름의 명세와 구현·실제 증적을 함께 닫아야 문서와
  코드가 장기간 분리되지 않는다. 또한 후보 A를 독립 기반으로 만들면 사용되지 않는 범용 adapter와
  주입 기능을 과도하게 설계할 위험이 있다.
- 영향: Product Brief 14.4~14.6, 팀 통합 인수인계와 README의 후속 로드맵을 같은 순서로 유지한다.
- 승인: 제품 책임자 요청
- 재검토 조건: WhyYou capability 조사에서 Spec 003과 004가 공유해야만 하는 독립 제품 기능이 확인되거나,
  2주 MVP의 비협상 완료 시나리오 자체가 변경될 때만 분할과 순서를 다시 결정한다.

## D-014. 0단계 정합성·재현성 기준과 12개 시나리오 주장 범위

- 상태: 확정
- 결정일: 2026-10-01
- 배경: Spec 001·002는 한 개발자 PC에서 실제 검증됐고, 팀원이 맡기로 했던 N-02 등 별도 명세는
  존재하지 않는다. 또한 Product Brief의 12개 시나리오와 D-013의 실제 실행 5개가 설명 없이 함께
  있으면 “12개 전부 실행”으로 오해할 수 있다.
- 범위 결정: 12개는 제품이 **관리하는 카탈로그 수**다. 2주 MVP 실제 실행 목표는 H-03, E-03,
  N-02, E-01, E-02의 5개다. H-01·H-02·N-01·N-03은 `NOT_RUN`, A-01~A-03은 WhyYou에 기능이 없어
  `NO_TEST_TARGET`로 표시한다. 공식 문구와 상태표는 `ControlProof_MVP_Scenario_Coverage_Matrix.md`를
  따른다.
- 태오 자료 대체: 존재하지 않는 문서를 기다리거나 내용을 추정하지 않는다. Spec 003은 WhyYou
  `bosung/controlproof-h03-integration`의 고정 commit을 직접 조사한 source baseline에서 시작하고,
  불확실한 사항은 clarify·plan에서 닫는다.
- N-02 초기 기준: 동의 완료는 브라우저 클릭이 아니라 서버 transaction이 durable consent record와
  `consented` 상태를 commit한 시점이다. Outbox 전달 지연은 별도 관찰 대상이며 현재 근거 없이 동의
  완료의 유일한 원본으로 간주하지 않는다.
- 독립 재현 gate: Spec 001·002를 main에 병합하기 전에 다른 팀원이 새 checkout에서
  `H03_DLQ_V2` 한 건을 실행하고 bundle verify·restore 성공, source SHA와 manifest SHA-256을
  Validation에 기록한다. 이 전에는 기존 한 PC 결과를 독립 재현 완료로 표현하지 않는다.
- 재현 문서: 개인 PC 절대 경로를 README와 Quickstart에서 제거하고 checkout 변수 또는 명시적
  placeholder를 사용한다. runtime `runs/`는 계속 Git에서 제외하며, 실제 bundle을 Git에 넣어 독립
  재현을 가장하지 않는다.
- AI 작업 방식: 저장소 루트 `AGENTS.md`와 `docs/AI_SPEC_KIT_PLAYBOOK.md`를 팀의 AI 작업 진입점으로
  둔다. 모든 기능은 `specify → clarify → plan → tasks → analyze → implement → actual validation →
  converge` 한 사이클씩 진행한다.
- 승인: 제품 책임자가 누락 자료에 대한 판단과 0단계 진행을 위임함
- 영향: README, TEAM_HANDOFF, Product Brief, 후속 Spec과 발표 문구는 범위표와 같은 상태를 사용한다.
- 재검토 조건: H-01·H-02·N-01·N-03의 실제 실행을 MVP에 추가하거나, WhyYou에 이의제기 기능이
  도입되거나, main 병합 전 독립 재현 gate를 변경하려면 새 결정으로 변경 이유와 영향을 남긴다.

## D-015. Spec 003 실제 경계·심층 probe·동의 fault 설계

- 상태: 확정
- 결정일: 2026-10-01
- 조사 기준: WhyYou `bosung/controlproof-h03-integration` commit
  `511ae9e2cae66b8d0ce31e8851537ed27ac6dd0c`
- 동의 완료: consent record, invitation의 `consented` 상태·state change와
  `invitation.consent_completed` Outbox가 한 HTTP transaction에서 commit된 사실을 기준으로 한다.
  Outbox 전달 완료 시각은 별도 사건이며 전달 지연만으로 N-02 FAIL을 만들지 않는다.
- 실제 처리 경계: 자료는 applicant upload-intent와 analysis event/worker, 녹화는 interview session 생성과
  recording 경계, AI 평가는 독립 applicant API가 없으므로 실제 `report.generation_requested` worker
  경계를 사용한다. ControlProof 전용 가짜 제품 endpoint는 만들지 않는다.
- lane 결정: pristine 기준선, 자료 우회, 녹화 심층 probe, AI 평가 심층 probe, 정상 순서, 동의
  fault·복구의 6개 독립 lane을 사용한다. 녹화·평가 경계가 앞 단계 산출물을 요구할 때는 digest와 허용
  효과가 고정된 합성 fixture를 쓰되 fixture와 probe 뒤 증분 효과를 분리하고 다른 lane의 PASS 근거로
  재사용하지 않는다.
- 동의 fault: `save_consent()` 뒤 invitation 상태 전이·Outbox append 전에 local/test one-shot fault를
  발동한다. 실제 발동 receipt를 fsync한 뒤 예외를 전파해 request transaction 전체 rollback을 시험한다.
  marker는 Run·subject allowlist, 최대 10분 TTL, 의무 복구를 갖는다.
- 순서 증적: timestamp만 비교하지 않고 request/trace, domain event identity, aggregate version,
  consent 응답 뒤 다음 command를 보내는 program order와 worker boundary receipt로 causal graph를 만든다.
- 최초 FAIL gate: seed·observer·fault·adapter는 첫 Run 전에 만들 수 있지만 analysis/recording/assessment
  consent 보호조치는 actual FAIL bundle을 먼저 봉인한 뒤에만 WhyYou 개인 브랜치에서 보완한다.
- 구현 구조: `N02_CONSENT_ORDER_V1`, scenario v3와 Spec 003 bundle profile을 additive하게 추가한다.
  기존 Spec 001·002 scenario와 sealed bundle은 변경하지 않는다. 고객 웹 UI는 Spec 005 범위를 유지한다.
- 이유: 업로드 경계의 403만으로 downstream 녹화·평가 side door까지 PASS 처리하면 거짓 보장이 된다.
  반대로 prerequisite 없는 깊은 호출은 consent가 아니라 입력 부재로 거부되므로 실제 authorization을
  검증하지 못한다. fixture와 증분 효과 분리는 두 문제를 동시에 피한다.
- 영향: Spec 003 spec의 FR-007과 lane 설명을 기술 조사 결과에 맞게 명확화하고 Plan, Data Model,
  contracts, Quickstart에 반영한다. 구현은 `$speckit-tasks`와 analyze 이후에만 시작한다.
- 승인: 제품 책임자의 미결정 사항 위임과 Spec 003 진행 요청
- 재검토 조건: WhyYou의 실제 처리 경계가 바뀌거나 deep probe fixture 없이 독립적으로 같은 경계를
  시험하는 공식 API/event가 추가될 때 capability와 lane 설계를 새 결정으로 갱신한다.

## D-016. Spec 003 Analyze 보완과 구현 착수 gate

- 상태: 확정
- 결정일: 2026-10-01
- 배경: Tasks 생성 뒤 첫 `$speckit-analyze`에서 HIGH 5건·MEDIUM 7건이 확인됐다. 요구사항이나 제품
  범위를 바꾸는 문제가 아니라 subject 격리 표현, 실제 observer 삽입 위치, 시간 예산, 비부작용 시험,
  조건부 보완 책임과 추적성의 구현 전 모호함이었다.
- subject 결정: US1은 지원자 한 명으로 세 경로를 연속 시험하지 않는다. pristine 확인용 subject와
  자료·녹화·평가별 독립 subject lane을 사용하며 상태를 다른 경로의 PASS 근거로 재사용하지 않는다.
- observer 결정: session 생성·시작·녹화 확정 receipt는 authorization adapter가 아니라 실제 효과가
  확정되는 `SessionApplicationService`의 `_create_session_once`, `_start_session_once`,
  `confirm_recording_upload` 성공 직후 남긴다. optional port로 주입하며 observer 저장 실패는 제품
  transaction을 실패시키지 않고 N-02 증적 부족으로 처리한다.
- 시간 결정: 성공 기준의 Run+bundle verify 10분을 실제로 만족하도록 scenario snapshot에
  `run_deadline_seconds=540`, `bundle_verify_deadline_seconds=60`을 고정한다. polling 2초, 연속 3회·최소
  4초 안정화, fault TTL 600초와 restore 120초는 별도 안전 계약으로 유지한다.
- readiness·seed 결정: non-READY는 비민감 `operator_action`을 필수로 제공하고 preflight는 Run directory,
  subject, marker와 event를 만들지 않는다. 6개 lane seed는 하나의 transaction이며 일부 실패 시 전체
  rollback한다.
- 조건부 보완 결정: 최초 actual Run의 직접 FAIL은 `TARGET_CONTROL_DEFECT`,
  `RUNNER_OR_OBSERVER_DEFECT`, `RESTORE_OPERATOR_DEFECT`로 먼저 분류한다. A5~A7도 증적으로 책임 경계를
  정하고 해당 경계만 수정하며 시험기 결함을 WhyYou 결함으로, WhyYou 결함을 시험기 수정으로 숨기지
  않는다.
- 결과: 위 내용을 Spec, Plan, contracts, Tasks와 Quickstart에 반영한 뒤 재분석에서 CRITICAL·HIGH 및
  팀 해석 차이를 만드는 MEDIUM 0건을 확인했다. Spec 003은 구현 착수 가능하지만 코드와 actual Run은
  아직 시작되지 않았다.
- 영향: Tasks 수는 93개로 유지한다. 다음 단계는 `$speckit-implement`이며 최초 factual Run 봉인 전
  WhyYou product guard 수정 금지 원칙은 유지한다.
- 승인: 제품 책임자의 Analyze 권장 조치 재검토·해결 요청
- 재검토 조건: 실제 WhyYou source boundary가 달라지거나 540+60초 예산이 준비된 로컬 환경에서 반복적으로
  달성 불가능한 근거가 생길 때 새 결정으로 갱신한다.

---

## 2. 결정 적용 순서

아래 목록은 2026-09-23 당시 구현 착수 순서이며 Spec 001·002에서는 모두 수행됐다. 현재 다음 작업을
뜻하지 않는다. 최신 상태와 후속 결정 지점은 [팀 통합 인수인계](../TEAM_HANDOFF.md)를 따른다.

1. 이 결정과 V4·Product Brief를 Spec Kit Constitution에 반영한다.
2. 기능 Spec 001에서 H-03 최소형 수직 흐름의 사용자 이야기와 acceptance criteria를 작성한다.
3. 기능 Spec 001의 데이터 계약에 `subject_ref`, `phase`, `step_id`, `attempt`, readiness, 실행 상태, 표준 reason code를 반영한다.
4. Plan에서 첨부 골격의 수정 범위와 WhyYou adapter 경계를 정한다.
5. Tasks를 만든 뒤에만 실제 코드 수정에 착수한다.

## 3. 변경 기록 규칙

이 문서의 결정을 바꿀 때는 기존 문장을 조용히 덮어쓰지 않는다. 각 변경에 다음을 남긴다.

- 변경한 결정 ID
- 변경 전과 변경 후
- 변경 이유와 근거
- V4, Product Brief, Constitution, 기능 Spec, 코드와 시험에 미치는 영향
- 변경 승인자와 날짜
