# 완료 시나리오의 WhyYou 보완 이력 조사 — 2026-10-19

현재 카탈로그의 실제 실행 완료7개를 대상으로, 원래 문제→대상 코드 보완→후속 판정을
Validation/Implementation Decisions/actual closure와 이 PC의 봉인 자료로 대조했다.
이번 조사는 읽기 전용이며 WhyYou 코드를 새로 수정하거나 테스트를 다시 실행하지 않았다.
단순히 대상commit이 다르거나 최종PASS라는 이유로 서비스 보완 사례로 분류하지 않았다.

## 확인 결과

| 시나리오 | 확인한 문제와 WhyYou 보완 | 결과를 읽을 때 주의할 점 | 근거 |
|---|---|---|---|
| H-02 | 단계가 비어 있는 지원자 현황을 묻자 담당자 결정 없이 최종합격으로 채워짐. AI 조회를 조회 전용 저장소 기능에 연결 | FAILdd52deb1→보완된childc12c2ce8 PASS. 이번 화면 보완 대상 | [Spec007 actual closure](../../specs/007-h02-capability-surface/actual-closure.md) |
| H-01 | SYSTEM 내부 호출로 지원자를 최종합격·불합격 단계로 일괄 이동할 수 있었음. 최종 단계 변경 전에 COMPANY_USER 검사를 추가 | FAIL7d6024ce→중간INC→39a0d317 PASS. AI 경로를 입증할 테스트 연결 보완도 포함 | [Spec006 actual closure: Product remedy](../../specs/006-h01-human-decision/actual-closure.md#product-remedy-and-actual-ai-boundary) |
| H-03 | 보고서 부재·장기지연이 화면에서 준비 상태처럼 보이거나 명확한 거부 사유가 없었음. 상태 표시·거부 사유 보완. 확장 테스트에서는 보고서 없이 일괄 최종단계 변경 가능/최종실패가queued로숨음. 보고서준비검사와영속실패상태추가 | 최소/확장 두 프로필에 각각 보완 이력. ControlProof 관찰 횟수·표시 판독 보정도 별도 포함 | [Spec001 보호조치 수정](../../specs/001-execution-evidence-h03/validation.md#whyyou-보호조치-수정), [Spec002 T082~083](../../specs/002-h03-e03-fault-expansion/validation.md#2026-09-29--최초-fail-근거-기반-whyyou-보완-t082t084) |
| E-01 | 실제 근거 답변 구간을 제거해도 보고서 조회 응답에 부재를 알리는 정보가 없었음. 응답에 현재 근거 존재 여부(transcript_available)추가 | A3문제. A1/A2는 최초부터PASS. 원본점수·보고서저장값을지우는수정이아님. D1별도저장소진단과실행기보완도제품보완과구분 | [Spec004 T085~088](../../specs/004-e01-e02-score-evidence/validation.md#2026-10-08--t085-approval-and-t086-whyyou-remedy-pr), [ID00434 원인분류](../../specs/004-e01-e02-score-evidence/implementation-decisions.md) |
| E-03 | 동일 결정요청 재전송이 최초성공과같은응답으로재생되지않았음. 결정·검토·감사·멱등성연결을동일트랜잭션으로묶고같은요청은기존결과재사용 | WhyYou보완후에도중간child는FAIL. 이후ControlProof가company_user/COMPANY_USER를다르게읽던판정오류를보정한grandchild가PASS. 전체FAIL을대상결함으로설명하면안됨. AFTER프로필의최초PASS와구분 | [Spec002 T084](../../specs/002-h03-e03-fault-expansion/validation.md#2026-09-29--최초-fail-근거-기반-whyyou-보완-t082t084), [E03 계보](../../specs/002-h03-e03-fault-expansion/validation.md#e03-fail--보정된-pass-계보) |
| N-02 | 과거검증에서동의없는면접시작/평가처리시작이발견돼WhyYou에동의확인과거부처리추가 | 서비스보호조치수정이력은있음. 최초전체판정은INC/중간자료일부INVALID이며실행기결함과구분. 2026-10-18 최종PASS의최근작업은문서분석테스트모델·환경준비와수집/정리보완. 이번에새동의결함을고쳐PASS로바꾼것이아님 | [Spec003 ID00317~18](../../specs/003-n02-consent-order/implementation-decisions.md), [후속준비범위](../../specs/003-n02-consent-order/analysis-preparation.md), [최종실행](../../specs/003-n02-consent-order/actual-closure.md) |
| E-02 | 해당시나리오실패를이유로WhyYou보호조치를수정한근거를찾지못함 | 최초A1~A3PASS. 최신통합대상이다른시나리오수정을포함한다고E02문제보완으로분류하지않음. T087 NOT_REQUIRED | [Spec004 ID00434](../../specs/004-e01-e02-score-evidence/implementation-decisions.md), [Spec004 validation](../../specs/004-e01-e02-score-evidence/validation.md) |

2026-10-20 Spec009 추가(연우):

| 시나리오 | 확인한 문제와 보완 | 결과를 읽을 때 주의할 점 | 근거 |
|---|---|---|---|
| N-01 | WhyYou 보완 없음. 부모 PASS 뒤 ControlProof 측정이 숨김·투명·조상 잘림·line-clamp를 잡지 못함을 음성 대조로 발견해 ControlProof 측정을 v2로 보강 | 부모`48a70f5e` PASS(측정v1, 보존)→child`d3aac7d9` PASS(측정v2). WhyYou`0166d9e` 그대로. 서비스 보완 사례로 분류하지 않음 | [Spec009 actual closure](../../specs/009-n01-n03-notice-scenarios/actual-closure.md) |
| N-03 | 해당 없음. 최초 Run PASS | `f27b68e8` PASS. N03-A1~A3만 판정, 정책 교체 주입·분석 작업 귀속은 미검증 범위 | [Spec009 validation](../../specs/009-n01-n03-notice-scenarios/validation.md) |

H02 외 추가서비스보완이력은 H01/H03/E01/E03/N02 다섯 시나리오에서 확인했다.
E03와N02는단순한'WhyYou수정만으로PASS'가아닌혼합이력이다. H03는두프로필을한시나리오로계산한다.
이번사용자승인은H02화면반영+타사례조사이므로타사례화면에수정설명을추정확장하지않는다.

## 이 PC에서 재검증한 자료

현재viewer root는 cp-local/spec004-official/runs. 카탈로그에연결된N02 2개/H01 4개/H02 3개/
E01 3개/E02 1개, 총13개bundle을실제verify했고모두VERIFIED. WhyYou SHA/parent/reason/manifest를
읽어문서와대조했다. H03/E03의공식bundle은이root에없어이번에원본재검증했다고주장하지않는다.
두시나리오는기존Validation의실제Run·수정commit·전후결과·보완범위를근거로분류했다.

| 계보 | 문서/실제기록에있는대상버전및판정 |
|---|---|
| H03최소 | f738081a FAIL(Why573ce0c)→e42482c9 PASS(aa0ae2b) |
| H03확장 | 60b19e5a FAIL→3ff1c0c7 PASS(Why보완511ae9e) |
| E03 BEFORE | e17e0af0 FAIL→5a7f09ff FAIL(Why보완)→ebeed35e PASS(CP판독보정) |
| E01 | 09c9d9bb FAIL(ce8d862)→a5ad4676 PASS(374b122). 중간ec0c895d도ce8d862/FAIL |
| H01 | 7d6024ce FAIL(6ba6379)→39a0d317 PASS(08c397e) |
| H02 | dd52deb1 FAIL(02aff2c)→c12c2ce8 PASS(af36f25) |
| N02 | 15cef078 INC(94ad7f2)→과거보호조치추가be81ebc/7b59237e INC→16dbd987 PASS(e64ff9d,테스트모델준비) |
| E02 | e39e62ae PASS(ce8d862), 이후clean재현970108fe PASS(374b122). 자체보호조치수정없음 |

현재최신PASS는검증한버전과조건에한정된다. ControlProof자체의자동수정기능을뜻하지않으며,
WhyYou개발코드수정·테스트접점준비·ControlProof실행기/판정기수정은기록에서구분한다.
모든이전FAIL/INC/INVALID는그대로보존한다. 조사raw출력은 .controlproof/remediation-audit-records.json
에만두고게시하지않는다. 과거별도저장소진단의결과를AI검증동작으로재해석하지않았다.


화면 반영·검증 마감: H02 개요/실행 결과/비교에 발견·WhyYou개발보완·ControlProof재테스트를
구분해 표시했다. 회귀52건(단위44+로컬HTTP8) 통과, 실제16화면/근거20패널 검수 완료.
291개 기존viewer파일과WhyYou소스바이트불변. 새서비스수정·새Run·커밋push없음.
상세 Spec005 remediation-history.md.
