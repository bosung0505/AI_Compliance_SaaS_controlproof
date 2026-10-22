# Spec010 7단계 — 기본 전환·복구·최종 인수인계

2026-10-21 · `010-platform-ui-integration` · **T001~T022 완료, Spec010 로컬 프론트엔드 범위 Complete**.
사용자가 “팀 검토는 했다 치고” 남은 단계를 지시하여 팀 검토를 완료로 간주하고 전환을 승인했다.
이번에 별도의 비작성자 사용성 세션을 관찰/수행한 것은 아니다. Spec005 전체 마감이나 외부 사용성 시험을 대신하지 않는다.
HEAD `fb219d0c6923c6be09691fcae0ead670f9700b39`; 이번 작업은 미커밋/미게시다.

## 전환 결과

- 검증된 stage6 r3 JSON을 **바이트 그대로** `review-data/snapshot.json`으로 승격했다. 새 결과나 판정을 만들지 않았다.
- ID `shared-ui-stage6-20261021-r3`, digest `5c1cfd81dd20a4d441141f889ae9837eac32be453620f1e25d0f938ff625a8ad`.
  JSON 파일 SHA `011ce767128cc96c05b21416ef0bf742b916bee0063183c8389fb9c2bad95e21`.
- 이전 JSON을 같은 bundles 부모의 `review-data/snapshot.shared-actual-20261020-r2.json`으로 보존했다.
  SHA `26df887d6a8b26bf2a29b311e805de7a7eaebb0eb6ccdcf19710e358d64d99df`로 전환 전과 같다.
- records/target/missing 선언과 실제652개 파일 SHA를 대조했다. 원본28건/11프로필·27 VERIFIED/원래 INVALID1개·미확보1건,
  검토된 PNG6개, 12/9/0/3과 N03 일부 범위, 원래 source SHA/계보/판정을 보존했다.
- 신규 제품 코드/화면/의존성 변경은 없다. `baseline.json`과 모든 이전 후보도 보존했다.
  기본 경로가 변경돼도 후보 생성기가 정확한 동결 SHA의 보존본을 선택하게 했으며 누락/변조를 거부한다.

## 실제 검증

전환/보존/후보 원천 검사6개를 먼저 실패시킨 뒤 반영했다. 최종 **51개 고유 검사 통과**:
`checks/test_default_transition.py`6개, shared entrypoint/records, 현재 기본 snapshot 계약,
Spec010 baseline 계약, platform integration, shared web. 초기 제한 환경에서는49개 통과/실제 loopback2개가
WinError10013으로 실패했다. 해당 shared web4개를 loopback 허용 환경에서 재실행하여4개 모두 통과했다.
결과는 `.controlproof/ui-integration-20261021/stage7-tests.xml`, `stage7-loopback.xml`에 보존한다.

- snapshot 옵션이나 `CONTROLPROOF_UI_TEST_SNAPSHOT` override 없이 `python -m engine.web --port 8784`로 실제 실행했다.
- 실제 HTTP **17개 요청**: 현황/소개/안내/결과/N03/H01 실제 결과/H02 비교/보고서/준비/DEMO,
  workbench·report API, DEMO404/공유 POST403/Host421. 기본 ID·9/0/3·보고서22개 내용 상태를 확인했다.
- 앱 브라우저에서 기본 서버의 현황 → 테스트 결과12개 → 현황 복귀를 확인했다. 최종 화면/탭을 사용자에게 유지한다.
- 이전 `fb219d0`의 engine/catalog/scenarios를 별도 임시 폴더에 git archive로 풀고, 그 코드의 실제
  load_snapshot으로 보존 r2+현재 불변 bundles를 읽었다. 표시 pin·28건·전체 verify 통과를 확인했다.
- 기본 전환 뒤 후보 생성기 전체 명령도 새 `stage7-builder-check` 경로로 실행하여 동결 원천 선택·28/652 불변·전체 로드를 확인했다.

원본/HTTP 감사는 `stage7-default-audit.json`, 이전 코드 복구 검증은 `stage7-rollback-check/checks.json`에 있다.
현재 코드와 stage6의 표시 자산이 같으므로 [324회귀·44너비/키보드·실제 PDF26페이지](stage6-validation.md)는
그대로 적용한다. 이번에 전체 엔진 suite·반응형44개·PDF를 다시 실행/생성한 것으로 집계하지 않는다.

## 실행과 한계

[최종 실행·화면별 사용·복구 안내](quickstart.md). 일반 실행은 이제 후보 옵션 없이 새 화면을 연다.
현재 기본 실행 확인 화면은 `http://127.0.0.1:8784/`다. 기존8782 미리보기는 종료하지 않았다.
자동 승인 검토가 기존 서버의 종료를 거부하여 해당 동작을 취소하고 별도 포트를 사용했다.
제한 환경에서 기동한8783은 브라우저 연결이 시간 초과였으며 실제 검수/사용자 안내는 정상 연결한8784 기준이다.
현재 루트의 `review-data/README.md`도 기본 공유본과 맞췄다.

새 actual Run·WhyYou/봉인 원본 수정·AWS/외부 모델 검증·의존성 설치·외부 게시·commit/push/PR/main 병합은 없다.
팀원이 pull하여 받을 게시 commit은 아직 없다. 최종 PDF는6단계 검수 산출물을 그대로 보존하며 새 봉인 증거가 아니다.
