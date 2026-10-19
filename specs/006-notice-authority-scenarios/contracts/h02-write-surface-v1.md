# Contract: H-02 Write Surface Static Scan v1

상태: 금지 집합의 **기본 단계 채움**(Q-P1)과 **주입 객체 보유 능력**(Q-P2) 처리가 제품 책임자 답을 기다린다. 아래 "열림" 표시 외
부분은 확정이다. 근거는 [research.md](../research.md) R4.

## 입력

- 검사 대상 커밋: 대상 스냅샷 git sha(40자). 소스는 `git show <sha>:<path>`로만 읽는다. 작업 트리·설치된 패키지는 읽지 않는다.
- 패키지 루트: `backend/src/interview_evidence/`.
- 표면 원천: `recruiting_assistant/api.py`(어시스턴트), `runtime/worker.py`(`EVENT_QUEUE_ROUTING`,
  `create_production_worker_runtime`), 주입 해석 원천 `runtime/production.py`.

## 표면 항목

| 종류 | 열거 방법 | 항목 키 |
|---|---|---|
| 어시스턴트 경로 | `create_assistant_router` 안의 `@router.<method>(path)` 데코레이터 전부 | `METHOD /v1<path>` |
| 작업자 사건 | `EVENT_QUEUE_ROUTING` dict의 키 전부 | `queue:event` |
| 작업자 처리기 | `create_production_worker_runtime`의 사건→처리기 대응 전부 | `event → HandlerClass` |

처리기가 없는 사건은 분류 `NO_HANDLER`이고 도달 분석 대상이 아니다(소비자가 "ignored"로 확인 응답, research R4.2).

## 분류

`READ_ONLY` | `WRITES` | `NO_HANDLER` | `UNRESOLVED`. `WRITES`는 바꿀 수 있는 상태(표·열 또는 저장 함수)를 함께 기록한다.
모든 항목은 근거 위치(`path:line`)를 가진다.

## 금지 집합 (확정)

정의 위치는 research R4.3과 같다.

```text
reporting.application.final_decision_service.FinalDecisionService.record
reporting.application.review_service.ReviewService.record_final_decision
reporting.application.review_service.ReviewService.record_recruiting_stage_decision
reporting.application.review_service.ReviewService.close_invitation_review
reporting.domain.review.HumanReview.final_decision
reporting.domain.review.HumanReview.recruiting_stage_decision
company_management.domain.hiring.Invitation.move_to_recruiting_stage
company_management.application.hiring_service.HiringService.move_applicants
integration.reporting_company.ReportingHiringBoundary.move_to_recruiting_stage
company_management.repositories.postgres.SqlAlchemyCompanyRepository.save_invitation   # 단계 열을 쓰는 저장
reporting.repositories.postgres.SqlAlchemyReportingRepository.save_review
```

## 열림 — Q-P1 기본 단계 채움

`HiringService.ensure_default_stages`는 `Invitation.move_to_recruiting_stage`와 `save_invitation`을 부른다.

- 답 A(추천): 별도 처리 없음. 위 금지 집합에 이미 닿으므로 도달이다.
- 답 B: `ensure_default_stages`를 통한 도달은 "기본 단계 채움" 관찰로 분리하고 H02-A3 도달에서 뺀다. 다른 경로로의 도달은 그대로다.

## 열림 — Q-P2 주입 객체 보유 능력

- 답 B(추천): 판정은 호출 도달만. 주입 객체가 가진 금지 집합 메서드 목록은 항목의 `held_capabilities` 관찰과 한계 H02-L2에 기록한다.
- 답 A: 주입 객체가 금지 집합 메서드를 하나라도 가지면 그 항목을 도달로 본다.

## 도달 규칙 (확정)

1. 시작점: 어시스턴트 경로 처리 함수, 운영 처리기 클래스의 `handle`(또는 대응표가 가리키는 callable).
2. 호출 해석: 같은 모듈 함수, import된 저장소 내부 심볼, `self.<attr>.<method>`는 `__init__` 대입·생성자 인자 주석으로 클래스를 정한다.
3. 주입 해석: 생성자 인자가 Protocol이면 `runtime/production.py`의 실제 생성 호출 인자로 구체 클래스를 정한다. 정할 수 없으면 그
   호출은 `UNRESOLVED`.
4. 깊이: 저장소 내부 호출을 금지 집합·외부 라이브러리·표준 라이브러리에 닿을 때까지 따라간다. 상한 12. 상한에서 끊기면 `UNRESOLVED`.
5. 동적 디스패치: dict 조회·`getattr`·`importlib`는 키·이름이 상수 문자열일 때만 해석한다. 아니면 `UNRESOLVED`.
6. 항목 판정: 금지 집합 도달 경로가 하나라도 있으면 `WRITES`(도달). 도달 없고 `UNRESOLVED` 호출이 있으면 `UNRESOLVED`. 둘 다
   없으면 `READ_ONLY`.

## 결과 형식 (EV6-08)

```json
{
  "commit": "<sha>",
  "rule_version": "h02-write-surface-v1",
  "depth_limit": 12,
  "forbidden": ["..."],
  "items": [
    {"kind": "assistant_route", "key": "POST /v1/assistant/answers", "location": "path:line",
     "classification": "READ_ONLY|WRITES|NO_HANDLER|UNRESOLVED",
     "mutable_state": ["..."], "reach_paths": [["start", "...", "forbidden"]],
     "unresolved": [{"location": "path:line", "reason": "..."}],
     "held_capabilities": ["..."]}
  ]
}
```

## 고정 fixture (SC-005)

`tests/fixtures/spec006_h02/`에 합성 소스 트리 세 개: 쓰기 노출(→ FAIL), 상수 아닌 `getattr`(→ INCONCLUSIVE), 읽기 전용(→ PASS).
