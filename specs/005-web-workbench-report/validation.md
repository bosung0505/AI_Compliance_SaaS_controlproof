# Spec 005 Validation

## Current status

- Workflow stage: Implement 진행 중. Phase 1(T001~T003)과 Phase 2 Foundation(T004~T018)이 이번 세션 범위. T019(보성 PC 검사)·T020(봉인 검사 v2
  전환)과 Phase 3 이후는 시작 전.
- Actual validation(웹 PC 재실행)·사용성 검토: 아직 없음(`NOT_RUN`). AWS: `NOT_RUN`.
- 이 문서는 시간순 기록이다. 실패·판정 불가 결과를 나중 결과로 덮어쓰지 않는다. 값·절대 경로·토큰은 쓰지 않는다.

## Source

| 항목 | 값 |
|---|---|
| ControlProof branch / 시작 HEAD | `005-web-workbench-report` / `c208604` |
| WhyYou | `bosung/controlproof-n02-integration` `374b122` (이번 세션에서 읽기·실행 없음) |
| Spec 004 재시험 정리 확인 경로 수정(PR #2) | 2026-10-08 세션 시작 시 원격 Spec 004 브랜치에 미병합 → merge 건너뜀(T061에서 다시 확인) |

## T001 starting regression (2026-10-08)

```text
.venv python -m ruff check .   -> All checks passed!
.venv python -m pytest -q      -> 943 passed in 252.88s
```

## 기록 틀 (T003)

### 엔진 보완 RED → GREEN (Phase 2)

| 작업 | 시험 파일 | RED(명령·수치) | GREEN(명령·수치) | 바꾼 기존 기대값 |
|---|---|---|---|---|

### 기존 bundle 검사 (T016, T019)

| PC | root 라벨 | bundle 수 | 규칙별 v1 | 규칙별 v2 | v2에서 새로 걸린 bundle |
|---|---|---|---|---|---|

### 사용자 스토리 gate

| Phase | 시험 | 결과 |
|---|---|---|

### Actual validation (웹 PC 재실행, Phase 9)

| 순서 | 시나리오·프로필 | WhyYou | ControlProof HEAD·dirty | preflight | Run ID | verdict / 복구 | manifest SHA-256 |
|---|---|---|---|---|---|---|---|

### 사용성 검토 (Phase 10)

| 참여자(익명) | 역할 | 질문별 정답·시간 | 치명적 오독 |
|---|---|---|---|
