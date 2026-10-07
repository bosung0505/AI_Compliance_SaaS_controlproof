# Contract: WhyYou Fixed Model Fixture `spec004-report-v1`

## Ownership and scope

- 저장소: WhyYou. 파일: `backend/src/interview_evidence/runtime/controlproof_model_substitute.py`와
  `backend/tests/unit/runtime/test_controlproof_model_substitute.py`만.
- 브랜치: `eec8f70`에서 분기한 개인 브랜치 `yeonwoo/controlproof-e01-e02-fixture`, remote `fork` push, PR base
  `bosung/controlproof-n02-integration`. origin·`main` push 금지.
- 성격: local/test 시험 대체물. 제품 코드(`reporting/`, `runtime/worker.py` 등)는 바꾸지 않는다. 최초 FAIL 전에 추가해도
  되는 instrumentation이다(Spec 003 R-013과 같은 구분).

## Safety

- 기존 `validate_controlproof_test_controls`, `controlproof_ai_isolation_digest` 규칙을 그대로 따른다. local/test 밖이면
  기동 실패, 외부 AI 허용이면 실패.
- `CONTROLPROOF_MODEL_FIXTURE_ID`가 `h03-report-v1` 또는 `spec004-report-v1`이 아니면 기동 실패.
- `h03-report-v1`의 출력·digest·health 값은 바꾸지 않는다.
- health는 활성 fixture의 ID와 digest를 보고한다.

## Identity

```text
fixture_id     = spec004-report-v1
fixture_seed   = controlproof:spec004-report-v1
fixture_digest = sha256(fixture_seed)
```

## Marker

`assess_interview_criterion` payload의 `criterion.text`가 다음 표식으로 시작하면 적용한다.

```text
[controlproof-spec004 mode=<MODE>( arg=<VALUE>)?( score=<0..100>)?]
```

| MODE | arg | 축마다 내는 `quoted_evidence_ids` | 점수 |
|---|---|---|---|
| `VALID` | 없음 | `provided_answers[0].evidence_id` | score 또는 72 |
| `EMPTY` | 없음 | `[]` | score 또는 72 (점수는 냄) |
| `NONEXISTENT` | UUID | `[arg]` | score 또는 72 |
| `OTHER_APPLICANT` | UUID | `[arg]` | score 또는 72 |
| `OTHER_CRITERION` | 참조 criterion UUID | 같은 처리 호출에서 그 기준에 제공된 첫 Evidence ID | score 또는 72 |

- 표식이 없으면 `h03-report-v1`과 같은 출력(첫 Evidence, 72, 답변 없으면 `None`)이다.
- `provided_answers`가 비면 모든 모드에서 점수 `None`·인용 `[]`(h03과 같음).
- 표식 문법 오류는 출력 없이 `ValueError`를 내지 않고 `DEFAULT`로 처리하며 receipt에 `MARKER_INVALID`를 남긴다(대상
  작업자가 모델 실패로 오인하지 않게).
- `assessment_state`는 인용이 비지 않으면 `confirmed`, 비면 `insufficient_evidence`(h03 규칙). `EMPTY`도 점수를 내므로
  작업자 검증 경로를 실제로 통과시킨다.
- `assess_job_requirement`은 h03과 같다.

## OTHER_CRITERION memory

- 인스턴스는 보고서 요청 범위 기억 `last_provided[(company_id, request_id, criterion_id)] = provided_answers[0].evidence_id`를 갖는다. 같은
  `generate` 흐름에서 기준이 `code` 오름차순으로 평가되므로, 참조 기준의 code가 더 앞이면 그 값이 이미 있다
  (ControlProof seed가 code 순서를 보장한다).
- **세션·지원자 경계(H-3)**: `TenantContext.company_id`와 `request_id`가 모두 일치해야 기억을 사용한다.
  보고서 작업자의 `request_id`는 Outbox event ID이며, 한 사건은 한 세션의 보고서를 요청하고 같은 context가
  모든 기준 평가에 전달된다. 따라서 다른 회사나 다른 보고서 요청은 시간값이 같아도 기억을 공유하지 않는다.
  UUIDv7 밀리초 일치는 재전달에서 오래된 기억을 거르는 추가 조건일 뿐, 보고서 식별값이 아니다.
  범위 또는 시간 조건이 다르면 `MODE_SOURCE_MISSING`이다. 참조 기준 ID는 Run 소유 버전에 속하고
  E-01 버전은 lane 하나의 세션에만 쓰인다.
- 다른 지원자 Evidence ID는 기억으로 만들지 않는다. `OTHER_APPLICANT`는 실행기가 넣은 표식 인자만 쓴다.
- 키는 `(company UUID, report request UUID, criterion UUID)`이며, 전체 항목은 최대 256개로 제한하고 오래된 것부터 버린다. 참조 기준 값이 없거나 경계 검사에 실패하면
  인용 `[]`, 점수 `None`을 내고 receipt `MODE_SOURCE_MISSING`.
- 기억은 local/test fixture 인스턴스 안에만 있고 영속하지 않는다.

## E-02 score values (H-2)

E-02 기준 표식은 `mode=VALID score=NN`이다. 값은 plan §Plan Decisions의 표(v1 72/73, v2 72/74)를 따르며 fixture는
그 값을 모든 축에 그대로 낸다.

## Emission receipt

`CONTROLPROOF_OBSERVER_ROOT`가 설정돼 있으면 **기준 평가 응답(`assess_interview_criterion`)마다**
`{root}/model/{receipt_id}.json`을 원자적으로 쓴다(임시 파일 → fsync → rename). 직무 요건 평가(`assess_job_requirement`)
응답은 기준 ID가 없고 E-01 범위 밖이므로 receipt를 쓰지 않는다. 쓰기 실패는 응답을 막지 않는다(observer 원칙).
구현: WhyYou `yeonwoo/controlproof-e01-e02-fixture` `3423f16`(PR jhkim0602/gbsa_aws#6, 검토 보완 포함).

```json
{
  "schema_version": "controlproof.spec004-model-emission.v1",
  "receipt_id": "uuid",
  "fixture_id": "spec004-report-v1",
  "criterion_id": "uuid",
  "mode": "OTHER_APPLICANT",
  "mode_status": "EMITTED",
  "provided_evidence_ids": ["uuid"],
  "emitted_quoted_ids": ["uuid"],
  "emitted_score": 72,
  "emitted_at": "aware datetime"
}
```

질문·답변·기준 설명 원문, payload 전체는 넣지 않는다. Run ID는 payload에 없으므로 ControlProof가 criterion ID로 Run을
연결한다(criterion ID는 Run 소유).

## Tests (WhyYou, RED 먼저)

1. 표식 없음 → h03과 같은 출력
2. 다섯 모드 각각의 인용·점수
3. `score=` 반영, 범위 밖 값은 `MARKER_INVALID`
4. `OTHER_CRITERION` 앞 기준 있음/없음
   - 동일 밀리초에서도 회사·보고서 요청 경계가 다르면 거부, 교차 실행 시 각 요청의 기억 유지
   - 같은 회사·요청에서도 UUIDv7 밀리초가 다르면 오래된 기억 거부
5. 답변 없음 → `None`
6. receipt 내용·원자적 쓰기, observer root 없으면 쓰지 않음, 쓰기 실패가 응답을 막지 않음
7. local/test 밖·알 수 없는 fixture ID 기동 거부, h03 digest 불변
8. `ruff check` 변경 파일 PASS, reporting·runtime 단위 시험 불변(기존 실패 1건 `test_no_module_imports_another_lanes_
   private_package`는 기준선 그대로 기록)
