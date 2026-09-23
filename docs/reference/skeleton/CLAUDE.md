# ControlProof

WhyYou(AI 면접 서비스)를 대상으로 AI 기본법 절차적 통제 4종의 작동 여부를
실제로 시험하고, 증적과 판정을 남기는 검증 도구. 2주 MVP.

기준 문서: `docs/기능범위_v4.md`

---

## 절대 규칙

**1. 시험 대상은 만들지 않는다. 시험 수단만 만든다.**
WhyYou 에 없는 통제를 우리가 구현해 넣고 시험하지 않는다. 그렇게 하면
PASS 는 우리가 만든 것을 우리가 통과시킨 결과가 된다.
장애 주입 훅은 예외다 — 시험 대상이 아니라 시험 수단이고, 테스트 환경에서만
켜지며, 보고서에 "시험을 위해 추가"로 표시한다.

**2. 근거 없는 통과 금지.**
관찰하지 못한 것을 PASS 로 처리하지 않는다. 판정은 네 값이다.
`PASS` / `FAIL` / `INCONCLUSIVE` / `NOT_RUN`.
"못 한 것"(INCONCLUSIVE)과 "안 한 것"(NOT_RUN)을 섞지 않는다.

**3. 고치고 시험하지 말고, 시험하고 고친다.**
알고 있는 결함을 미리 수정하고 시험하면 FAIL → 수정 → PASS 데모를 잃는다.
최초 실행의 FAIL 을 증적으로 보존한 뒤 수정하고 같은 조건으로 재시험한다.
재시험은 최초 결과를 덮어쓰지 않는다 (`Run.retest_of`).

**4. 시나리오는 데이터다. 코드가 아니다.**
시나리오가 바뀌어도 엔진은 바뀌지 않는다. 엔진을 고쳐야 하는 사유는 셋뿐이다.
  - 새 관찰 수단이 필요할 때 → 어댑터 추가
  - 판정 규칙 타입이 모자랄 때 → 규칙 추가
  - 증적 스키마가 바뀔 때 → 비싸다. D1 에 고정하고 바꾸지 않는다.

---

## 아키텍처 계약

```
시나리오 YAML  ──(관찰값 키)──>  판정 규칙
                                    ↑
어댑터 ──(관찰값 키로 Observation 생성)──┘
```

**관찰값 키가 시나리오와 어댑터를 잇는 유일한 접점이다.**
시나리오 규칙은 `invitation.state` 같은 추상 키만 가리킨다. 키를 실제
엔드포인트·테이블·필드로 바꾸는 일은 어댑터의 연결 설정이 한다.
고객이 바뀌면 연결 설정만 교체하고 시나리오 YAML 은 그대로 둔다.

키는 `engine/observations.py` 의 `REGISTRY` 에 등록된 것만 쓴다.
등록되지 않은 키를 시나리오가 가리키면 로드 시점에 거부된다.

### Observation 의 세 가지 상태 — 이 구분이 FAIL 과 INCONCLUSIVE 를 가른다

| 상황 | 표현 | 판정에 미치는 영향 |
|---|---|---|
| 조회했고 값이 있음 | `Observation(value=...)` | 규칙 평가 |
| 조회했고 존재하지 않음 | `Observation(absent=True)` | 규칙 평가 (없음이 정답일 수 있음) |
| 조회 자체를 못 함 | Observation 을 만들지 않음 | INCONCLUSIVE |

어댑터는 "없었다"와 "못 봤다"를 반드시 구분해야 한다. 조회에 실패했는데
`absent=True` 를 만들면 없는 것을 확인한 것처럼 판정된다.

---

## 디렉터리

```
engine/
  models.py        증적 스키마. 이 파일이 계약이다. 함부로 바꾸지 않는다.
  observations.py  관찰값 키 사전
  judge.py         판정 규칙 4타입, PASS/FAIL/INCONCLUSIVE 결정
  scenario.py      YAML 로더·검증
  adapters/        api / log / browser / fault
  evidence.py      증적 저장 (SQLite + 원본 파일)
  report.py        HTML 보고서
scenarios/         시나리오 YAML (_TEMPLATE.yaml 은 로드 대상에서 제외)
seeds/
  state_seed.py    DB 직접 삽입. 리포트까지 준비된 검토 대기 지원자
  path_seed.py     실제 API 순서 호출. 동의까지 거친 지원자
tests/
```

### 시드 두 종류는 섞지 않는다 (기능범위 3.3)

- 상태 시드로 만든 지원자는 동의 화면을 거치지 않았다 → N 계열에 쓰지 않는다
- 경로 시드로 만든 지원자는 면접·리포트가 없다 → H·E 계열에 쓰지 않는다

---

## WhyYou 연동 사실

- 저장소: `github.com/jhkim0602/gbsa_aws` (public), Python 3.12 / FastAPI / PostgreSQL+pgvector
- 로컬: `make up` (Postgres + LocalStack + Mailpit), `make api` :8080, `make worker`
- **LocalStack 으로 가는 것**: S3, SQS, SESv2, Secrets Manager
- **실제 AWS/GCP 로 나가는 것**: Bedrock, Cognito, Transcribe, Polly, MediaConvert, Document AI
  → 면접을 실제로 돌리면 과금된다. 고정 AI 결과 대역이 필요한 이유.
- SQS 가 LocalStack 이므로 큐 장애 주입은 WhyYou 코드 수정 없이 가능하다.
- 데모 시드는 커밋 `7d977f7` 에서 제거됐다. 복원하지 않고 우리 시드를 새로 만든다.

### 실행 ID 연결 (기능범위 6.2)

1단계 **상관관계 연결**이 기본이다. WhyYou 를 수정하지 않고, 합성 지원자 ID·
초대 ID·시각 범위·WhyYou 의 `trace_id` 를 `Run.correlation` 에 담아 매핑한다.
2단계 전파(헤더로 실행 ID 전달)는 1단계 완주 후에 검토한다.

---

## 작업 순서

D1 에 증적 스키마를 고정하고 H-03 하나를 수직으로 관통시킨다. 레이어별로
수평으로 쌓지 않는다 — 스키마가 틀렸다면 D4 에 드러나야지 D11 에 드러나면 비싸다.

---

## 하지 말 것

- 관찰값 키를 우회해 어댑터가 판정 로직에 직접 값을 넘기는 것
- `absent=True` 를 조회 실패 시 기본값으로 쓰는 것
- 실행하지 않은 시나리오를 목업 데이터로 채워 화면에 표시하는 것
- 재시험 결과로 최초 실행 결과를 덮어쓰는 것
- 실제 지원자 개인정보를 시험 데이터로 쓰는 것
- 장애 주입 훅이 운영 환경에서 켜질 수 있게 두는 것
