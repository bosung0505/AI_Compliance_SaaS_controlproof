# Spec 001 구현 검증 기록

**검증일**: 2026-09-26  
**범위**: deterministic adapter harness와 WhyYou target-side 안전 제어의 자동 검증

## 완료된 자동 검증

| 검증 | 결과 |
|---|---|
| `python -m ruff check .` | PASS |
| `python -m ruff format --check .` | PASS, 86 files formatted |
| `python -m pytest -q` | PASS, 130 tests in 132.13s |
| WhyYou ControlProof target tests 3개 파일 | PASS, 20 tests |
| WhyYou 변경 파일 `ruff check` | PASS |
| `controlproof --help` | PASS, 6개 명령 노출 |
| fake H-03 EV-01~EV-09 manifest/link와 verify | PASS |
| fake FAIL→PASS child retest 후 parent verify/digest 불변 | PASS |
| delayed receipt·transient/no-stable report·delayed restore convergence | PASS |
| adversarial bundle semantic linkage verification | PASS |
| actual subject role·initial-state retest comparison | PASS |
| `run`·`show`·`retest` CLI envelope stability | PASS |
| 단계별 durable checkpoint와 중단·restore 예외 보존 | PASS |

자동 검증은 실제 개인정보와 외부 네트워크 없이 수행했다. target-side 시험은 WhyYou의 전체
의존성 설치 도구가 Windows 보안 계층의 Python 탐색 출력에 영향을 받는 문제를 피하기 위해,
ControlProof의 격리된 Python 환경에 WhyYou `backend/src`를 읽기 전용 import path로 연결하여
실행했다. 변경된 target 모듈과 안전 시험 자체는 모두 수행됐다.

## 아직 완료되지 않은 외부 검증

### SC-008 비작성자 2분 검토

코드 작성에 참여하지 않은 팀원 1명이
`review-usability-checklist.md`의 PASS/FAIL/INCONCLUSIVE 세 case를 수행해야 한다. 현재 검토자,
실행 시각, 답변, 소요 시간이 없으므로 **미검증**이다. 자동 projection 테스트 통과로 대신하지
않는다.

### 실제 WhyYou 격리 스택 H-03 Run

PostgreSQL·LocalStack·회사 콘솔·worker·고정 모델 fixture·로컬 회사 credential이 함께 실행된
상태의 opt-in Run은 아직 수행하지 않았다. 따라서 실제 Run ID, canonical target snapshot,
bundle digest, 실제 target verdict는 기록하지 않는다. fake harness PASS는 target PASS의 대체가
아니다.

### clean-environment quickstart 전 과정

현재 `.venv`의 설치, 전체 정적 검사, 전체 테스트, CLI entry point는 검증했다. Chromium 설치와
실제 WhyYou 서비스 기동이 필요한 quickstart 3~10절은 위 실제 스택 검증과 함께 남아 있다.

## 판정

- ControlProof 코드 기준: 자동 구현 게이트 PASS
- WhyYou 시험 제어 기준: 단위/안전 게이트 PASS
- 제품 완료 기준: **PARTIAL** — SC-008 비작성자 시험과 실제 격리 스택 Run이 남음
