# Contract: 12개 시나리오 카탈로그 (`catalog/mvp-scenarios.yaml`)

원천은 `docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md`(범위표)다. 카탈로그는 범위표에서 파생한 데이터이며 화면 설명 자료와
공식 기록 참조를 더한다. 엔티티 정의는 [data-model.md](../data-model.md) §1.

## 형식

```yaml
schema_version: controlproof.catalog.v1
source: docs/product/ControlProof_MVP_Scenario_Coverage_Matrix.md
fixed_scope_sentence: >-
  ControlProof MVP는 12개 시나리오를 한 화면에서 관리한다. 이 가운데 5개는 실제 실행과 증적을
  제공하고, 4개는 이번 실행 범위 밖인 `NOT_RUN`, 3개는 대상 기능이 없는 `NO_TEST_TARGET`로
  사실대로 구분한다.
scenarios:
  - id: E-01
    control: E
    control_label: 근거·기록 (E)
    question: 근거 인용 없는 점수가 저장되지 않는가
    mvp_treatment: EXECUTED
    owner_spec: Spec 004
    target_exists: true
    profiles:
      - execution_profile: E01_CITATION_EVIDENCE_V1
        scenario_file: scenarios/E-01.yaml
        run_command: python -m engine.cli run E-01 --profile E01_CITATION_EVIDENCE_V1 --target {target} --label {label} --json
        retest_command: python -m engine.cli retest {parent_run_id} --target {target} --label {label} --json
    official_status:
      result: PASS
      summary: 부모 FAIL 보존 → 수정 child PASS, 새 checkout 재현 PASS
      validation_ref: specs/004-e01-e02-score-evidence/validation.md
      records:
        - {role: parent, run_id: "<Validation의 Run ID>", result: FAIL}
        - {role: child, run_id: "<Validation의 Run ID>", result: PASS}
    explanation:
      intent: {text: "…", source: "specs/004-e01-e02-score-evidence/spec.md Feature Goal"}
      protected_object: {text: "…", source: "…"}
      policy_basis: {text: "내부 통제 기준 … · V4 §10.10 E-01", source: "V4 §10.10"}
      implementation_location: {text: "…(사람 말)", source: "docs/research/Spec004_E01_E02_WhyYou_Source_Baseline.md"}
      synthetic_data: {text: "…", source: "…"}
      manual_steps: [{text: "공식 실행 전 사람 승인", source: "AGENTS.md"}]
```

`NOT_RUN` 항목은 `profiles: []`, `official_status.result: NOT_RUN`, `explanation.not_run_reason`·`follow_up_condition`.
`NO_TEST_TARGET` 항목은 `target_exists: false`, `profiles: []`, `official_status: {result: INCONCLUSIVE, reason_code: NO_TEST_TARGET}`,
`explanation.absence_evidence`(WhyYou 조사 자료 출처 필수).

## 규칙과 시험

1. 범위표 §3 표의 각 행과 `id`·`question`·처리(`실제 실행`→`EXECUTED`, `` `NOT_RUN` ``→`NOT_RUN`, `` `NO_TEST_TARGET` ``→`NO_TEST_TARGET`)·
   `owner_spec`이 12/12 같아야 한다.
2. 처리별 개수 5·4·3, `fixed_scope_sentence`는 범위표 §2 인용문과 같은 글자.
3. `EXECUTED` 항목의 `profiles[].scenario_file`이 존재하고 그 YAML의 `scenario_id`·`execution_profile`이 같아야 한다(7개 프로필).
4. 모든 `explanation` 값에 `source`가 있어야 하고 `policy_basis`에 법 조문 번호가 없어야 한다(FR-009).
5. `official_status.records[].run_id`는 해당 `validation_ref` 문서에 그 문자열이 있어야 한다(Run ID 오타 방지).
6. 비개발자용 `text`에 WhyYou 내부 이름·fixture 이름·봉인 파일 이름이 없어야 한다(FR-019; 금지 단어 목록 시험).
