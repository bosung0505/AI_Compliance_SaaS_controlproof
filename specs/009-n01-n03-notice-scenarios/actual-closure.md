# N-01·N-03 actual closure — 2026-10-20

Spec009 LOCAL_EMULATED scope Complete (N-03 일부 실행). 실행·판정·봉인 기록은 [validation.md](./validation.md)의 "2단계 실제 Run"·
"N-01 측정 v2 child Run" 절이 원본이다. 이 문서는 마감 사실만 모은다. 봉인 bundle은 어느 단계에서도 다시 쓰지 않았다.

## 최종 기록

| Run | 시나리오·프로필 | 역할 | verdict / 상태 | verify | manifest SHA-256 | bundle digest | 소스 CP / WhyYou |
|---|---|---|---|---|---|---|---|
| `f27b68e8-0df8-46b3-a198-c7917c2f08bb` | N-03 `N03_STALE_CONSENT_V1` | final | PASS / COMPLETED | VERIFIED17 | `2a8511c3884548a34974d0aa6e4dfd167e49a8fb525742b109761661aae2f59a` | `562c251e59e1de4de497b8596f98f6ce9f6475261351aca9035e02a3b64bb317` | `914a4d957bfa8b52654d3c05defde0a807599d93` (`yeonwoo/spec009-cp-run`) / `0166d9eb5d25c7a95fafdbe39b802fdbd69a8713` (`yeonwoo/spec009-run`) |
| `48a70f5e-aa62-41fc-bf58-3624a6102b4f` | N-01 `N01_NOTICE_V1` | parent(측정 v1, 보존) | PASS / COMPLETED | VERIFIED15 | `82c1b6ce554873d78b8c121bb35a1c19c1c7b4d03f6c5339dd8eaeb408c542a9` | `65a49f31fa99dacf4cc1d4e51bd0e07e33823dc4a87146a8d1f4abe410024583` | `914a4d957bfa8b52654d3c05defde0a807599d93` (`yeonwoo/spec009-cp-run`) / `0166d9eb5d25c7a95fafdbe39b802fdbd69a8713` (`yeonwoo/spec009-run`) |
| `d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18` | N-01 `N01_NOTICE_V1` | final(측정 v2) | PASS / COMPLETED | VERIFIED17 | `68220e0088e8468345cbdcc7fe1af3ba91547bca7c6188b2d6a97dc0273ccf0f` | `aa2521725c71ab3b3db83b3c75240f851f381e7ce67a2ff9167a34c25033e927` | `04f4f9e3a6cbd338ef06f414758d62936d4ce8a7` (`yeonwoo/spec009-cp-run`) / `0166d9eb5d25c7a95fafdbe39b802fdbd69a8713` (`yeonwoo/spec009-run`) |

실행 시각(UTC): N-03 2026-10-20T00:56:48.744755Z~00:56:51.480476Z, N-01 부모 00:58:21.572177Z~00:58:30.262987Z, child
06:38:10.118975Z~06:38:18.348996Z. 두 소스 브랜치는 로컬 실행 전용 worktree 브랜치이며 게시 commit이 아니다. 같은 커밋이 원래
checkout `009-n01-n03-notice-scenarios`에 있다.

## N-01 계보

1. 부모 `48a70f5e…`: 측정 v1(조각마다 텍스트 있음·화면 안·가림 없음·가로 넘침 없음) A1~A3 PASS. 봉인된 그대로 보존한다.
2. Run 뒤 같은 측정 코드를 실제 Chromium에서 음성 대조(`tests/integration/test_applicant_measure_real.py`)했다. `visibility:hidden`,
   `opacity:0`, 조상 `overflow` 잘림, `line-clamp` 네 가지를 v1이 잡지 못함을 발견했다(analysis.md "Run 뒤 음성 대조").
3. 분류: **실행기 결함(ControlProof 측정 누락)**. WhyYou 동작 결함이 아니며 WhyYou 코드는 바꾸지 않았다. 부모 캡처에는 네 상황이
   보이지 않았다.
4. ControlProof 측정 v2(`04f4f9e`): `style_visible`·`not_clipped`를 더하고 `not_occluded`를 좁혔다. 판정은 lane 기록의
   `measurement_version`으로 규칙을 고르므로 v1 부모는 새 코드로도 같은 결과로 다시 판정된다(새 코드 verify VERIFIED·mismatch 0).
5. child `d3aac7d9…`(retest, 부모 `48a70f5e…`): 측정 v2, PC·모바일 각 5항목 11조각 여섯 플래그 모두 참, A1~A3 PASS. retest-diff에
   ControlProof 소스 `914a4d9`→`04f4f9e`, WhyYou `0166d9e` 그대로가 남았다. 실행 전후 부모 폴더 16개 파일 SHA-256 차이 0.

## N-03 범위 (일부 실행)

N03-A1(이전 정책 식별값 제출 거부·상태 불변), N03-A2(재조회 값 저장·식별값 일치), N03-A3(과거 동의 기록 불변)만 판정했다.

| ID | 종류 | 내용 | 후속 조건 |
|---|---|---|---|
| N03-U1 | 미검증 범위 | 실행 중 정책 교체 주입 | WhyYou 시험용 정책 교체 수단과 분석 작업 정책 귀속 저장 필드 |
| N03-U2 | 미검증 범위 | 교체 시점 근접 제출 | 같음 |
| N03-U3 | 미검증 범위 | 분석 작업의 정책 귀속 | 같음 |
| N03-L1 | 한계 | 이전 정책 식별값은 실제 교체 없이 만든 값 | — |

## 공통 한계와 실행 조건

- `LOCAL_EMULATED`, AWS `NOT_RUN`, 합성 지원자(Run 소유), 외부 AI 차단, 고정 모델 fixture `n02-analysis-v1`(호출하지 않음).
- 하네스 `scripts/spec009_local.py` instance `s009`, API 8080, 지원자 앱은 node가 vite를 직접 띄운 단일 프로세스(5174).
- WhyYou 실행 worktree의 `node_modules`는 원본 `gbsa_aws\node_modules`를 가리키는 junction이다. 지원자 앱의 워크스페이스
  패키지(`@iep/*`)는 원본 폴더를 가리키며 같은 커밋 `0166d9e`, 변경 없음이었다.
- 원래 ControlProof checkout에 `.env`가 있어 하네스는 `.env` 없는 별도 worktree(`AI_Compliance_SaaS_controlproof-spec009`)에서
  돌렸다. 첫 2단계 기동에서 Docker 기동 직후 `docker compose up --wait` 120초 초과가 1회 있었고 같은 프로젝트를 stop한 뒤 재시도했다.
- 독립 잔여 확인(읽기 전용 `engine.spec009_recovery.recount`): 세 Run 모두 44개 표 잔여 0, 복구 차단 없음.
- 이 결과는 실행한 두 시나리오의 범위와 확보한 증적에 한정되며 법적 준수 전체를 인증하거나 보증하지 않는다. 다른 PC 재현,
  외부 AI 모델 품질, 실제 AWS는 검증하지 않았다.
