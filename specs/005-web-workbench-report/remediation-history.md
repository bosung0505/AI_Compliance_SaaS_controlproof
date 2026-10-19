# H-02 발견·대상 서비스 보완·재테스트 표시 (2026-10-19)

## Specify / clarify

사용자가 제안한 개요·실행 결과·비교 화면의 세 단계 설명을 승인했다. H02부터 반영하고,
완료된7개 시나리오의 WhyYou 수정 이력을 조사해 별도 근거 문서로 보고한다. 다른 시나리오
화면 확대나 새 WhyYou 수정/실행/커밋/push는 이번 범위가 아니다. Spec005 전체 종료와 비작성자
사용성은 별도다. 브랜치 fixes-and-remaining-work, 기존 dirtyH01/H02 작업 보존.

- R1 개요 상단에 발견FAIL→WhyYou보완→재테스트PASS와 비교 링크를 표시한다.
- R2 최종 실행의 초록 상자는 '보완 후 재테스트 결과'; 이유/이전실패/비교 링크를 가까이 둔다.
  과거 FAIL에는 과거 결과임을 유지하고 이후 기록을 안내한다. 초기INC는 제품FAIL로 부르지 않는다.
- R3 비교 상단에 발견/보완/재확인3카드, 실제 전후 채용단계·결정기록, 양쪽 근거 링크를 둔다.
  WhyYou개발코드보완과ControlProof테스트 역할을 구분한다. 로컬 개발 반영 범위를 명시한다.
- R4 이전ID/버전/계보/규칙 비교는 하단에 유지, H02의 직접 부모를 '이전 문제 확인'으로 표시한다.
  초기수집INC도 전체이력에서 보존한다. 디자인은 기존card/badge/표/버튼 재사용.
- R5 설명은 프로젝트 검토 문서, 판정과 관찰은 검증된 봉인 자료에서 가져온다. 수정 주체를
  실행기나 모델로 꾸미지 않는다. 특정H02버전쌍의 설명을 새Run/DEMO에 자동전용하지 않는다.
  부모 누락/변조/불일치 때3단계완료주장과깨진링크를 표시하지 않는다. 봉인원문/메모불변.
- R6 다른 사례는 코드/문서/실행 계보로 교차확인한다. WhyYou보호조치/실행기보정/테스트환경
  준비/원래PASS를 구분하며 E03·N02의 혼합 이력을 모두WhyYou결함으로 간주하지 않는다.

## Plan

engine/web/remediation.py: 버전·봉인manifest를 고정한 H02 검토 설명과 안전한 읽기 전용 조립.
양쪽 verify와 childparent연결/대상소스/판정/원본관찰 참조 후 공통view.remediation 전달.
기록이 없거나 검증되지 않은 경우는 표시하지 않고 기존 무결성/기록부재 안내를 유지한다.
readmodel.run/scenario/compare에서 재사용; 템플릿3곳 및 공유partial만 수정. 새의존성/판정계산없음.
관찰표는 봉인 h02-reader-cases의 실제1조건과 전체요약을 사용, 테스트용상태와 서비스반응 구분.

## Tasks / analyze (before implementation)

- [X] T096 기록 누락/변조/다른버전/DEMO 음성 사례와 읽기 전용 조립, 3화면 공통설명 구현 [R1~5].
- [X] T097 7개 완료시나리오 이력감사 및 근거표, WhyYou/ControlProof/준비수정 구분 [R6].
- [X] T098 의미있는 자동회귀, 실제봉인자료 브라우저1280/1024, 원문해시불변,
  Validation/Traceability/README/인수인계/범위표/제품/결정기록 수렴 [R1~6].

CRITICAL0/HIGH0/의미차이MEDIUM0. ConstitutionI/II/VI준수: 검증없는성공안내금지, 판정불변,
초기INC별도, source-bound설명. 새로운보호조치실행이아니므로 actual validation은 보관된 실제
bundle읽기·UI검수로 수행한다. 타시나리오는 조사만, 보완없이이후PASS인경우를추정하지않는다.

## 구현·실제 화면 검수 — 2026-10-19

H02 개요 상단에 발견→WhyYou개발보완→재테스트 안내와 비교 링크를 추가했다. 최종실행은
'보완 후 재테스트 결과'로, 부모는 '문제가 확인된 당시 테스트 결과'로 구분하며 이유와
서로의결과/비교링크를 가까이둔다. 비교상단3카드에는실제미지정→최종합격/결정기록0→0과
보완후미지정→미지정/0→0표를표시한다. 서비스개발보완과ControlProof검증의역할, 로컬개발
코드반영범위와개발기록/봉인관찰출처를구분했다. ID·버전·전체초기INC이력·원본사유·메모·
규칙비교는하단접기영역에보존했다. 기존card/table/badge/button스타일재사용, CSS추가없음.

engine/web/remediation.py의설명은검토된H02버전쌍에만적용한다. 부모/자식원본verify,
manifestSHA256,시나리오/프로필/상태/대상SHA/봉인판정/부모digest연결을모두확인한다.
누락·변조·버전불일치·새Run에서는설명을추정하지않으며, DEMO에서는호출하지않는다.
관찰표는봉인reader기록을읽고 판정은새로계산하지않는다. 최초INC는제품문제FAIL로바꾸지않았다.

예상RED:새모듈부재ImportError. 구현후새회귀8PASS(정상역할구분,부모누락,무결성실패,
재봉인변조,다른소스/부모/digest,다른Run적용방지). 공유readmodel/compare/scenario/H02선택31PASS.
확장회귀는단위44PASS, HTTP8건은샌드박스localhost10013권한제한으로실패하여동일HTTP선택을
승인된로컬통신환경에서재실행했다(아래최종결과참고). 판정실패로간주하거나테스트완료로숨기지않았다.

실제보관bundle기반브라우저검수: 8화면×1280/1024=16화면, 기존10개근거패널×2=20패널,
실패/수정후근거링크각2회총4회, 개요→비교/실패→재테스트탐색, 초기INC전체이력펼치기확인.
모든HTTP200/가로넘침0/console·page오류0. E01이전비교/E02개요/N02·H01기존화면포함.
새비교1280/개요1024스크린샷시각검수완료. 첫검수의원본발췌는기본접힘상태여서검수코드가
펼치도록수정했다. 제품관찰이나원본자료를고친것이아니다.

현재viewerroot291개파일의모든바이트SHA256이작업전후동일하다. 카탈로그에있는13개
현지공식bundle을실제verify했다(모두VERIFIED). H03/E03공식bundle은이root에없으므로
두사례는기존실행원장·보완commit기록을근거로분류했다. 신규WhyYou실행이나코드수정없음;
현재WhyYou소스205Python tree a062993…불변. 원본브랜치fixes-and-remaining-work유지.
localhost:8766서버를소유PID/생성시각검증후재시작, 실제3주소에서새설명·HTTP200확인.
브라우저결과/캡처·해시원장은Git제외cp-local/h02-20261019/remediation-web-qa및.controlproof.

완료7개조사결과: H02외H01/H03/E01/E03/N02에서서비스보완이력확인. E03는WhyYou멱등성
보완외CPactor표현정규화도포함, N02는과거동의보호조치보완외최근문서분석모델/환경준비가
최종PASS에필요했다. E02자체보호조치수정근거는없고최초부터PASS. 모든전후자료유지.
조사표: [WhyYou 보완 이력 감사](../../docs/research/WhyYou_Remediation_History_Audit.md).
Spec005전체마감/비작성자사용성검증과별도이며실제범위12/7/2/3/LOCAL_EMULATED/AWSNOTRUN불변.


## Final closure — 2026-10-19

T096~098 complete in this display/audit scope. Expanded unit/readmodel selection44 PASS; HTTP8
PASS in35.24s after rerunning with permitted localhost access (initial sandbox10013 failures were
environment restrictions). Total52 regression cases accepted; no further product change needed.
New source-history8cases are included in44, not counted twice. Actual browser16screens/20proof
panels/4scoped evidence-link visits at1280/1024 pass. Public localhost:8766 overview/result/compare
allHTTP200 with updated text. Additional real-bundle checks confirm DEMO never loads the actual
development history and a standalone child missing its parent has PARENT_NOT_IN_ROOT/no completed
story. The missing-parent copy stays outside Git.

All291viewerfiles byte-identical; actual source tree unchanged; changed Python RuffCP52/Why13
PASS, git diff --check PASS; all4H01 original/viewer bundles reverified unchanged. No new WhyYou
code change/Run/commit/push. The published runtime record remains the prior H02test, not a new one.
Completed7-scenario remediation audit and required handoff/product/matrix/README/decision docs
converged. Spec005 overall closure and non-author usability remain separate.
