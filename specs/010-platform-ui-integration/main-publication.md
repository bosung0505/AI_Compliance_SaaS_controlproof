# main 반영 — 게시 전 검증

2026-10-22 사용자가 현재 변경을 main에 커밋하고 push하도록 명시 승인했다. 이전의 게시/main 미승인 문구를 이 요청 범위에서
대체한다. 대상은 ControlProof origin/main이며 WhyYou와 다른 저장소는 변경하지 않는다.

## 계획·분석

원격 main은71a2c25, 현재 작업 기준fb219d0의 조상이다(원격 고유0/기존 기능172 commits). 따라서 현재 완성된 서비스에는
이전에 기능 브랜치에 게시된 엔진/시나리오/실제 공유 기록도 포함된다. 현재 변경을 전용 브랜치에서 검증·커밋하고,
main을 fast-forward하여 force 없이 push한다. push 직전에 remote를 다시 fetch하고 최종원격SHA를 확인한다.
사전 변경의 .gitignore(UI제안 제외)도 기존 사용자 승인 범위다. .controlproof 임시자료/자격 증명은 게시하지 않는다.

게시 전 발견: display_hashes의 top-level HTML glob은 신규partials를 포함하지 않았다. recursive HTML glob으로 보완하고
partial 추가/변경 때 snapshot이 거부되는 실패 시험을 먼저 작성한다. 판정/652원본은 불변이며 새 표시 snapshot으로 갱신한다.
린트의 loop closure binding·타입 오류 처리/스타일5건은 의미를 보존하며 정리하고 관련 회귀를 확인한다.
새 actual/WhyYou/모델/DB 테스트는 실행하지 않는다. unit/contract/합성 integration과 기존 HTTP display를 검증한다.
실제 브라우저를 외부 Playwright로 구동하는 suite는 제외하며 기존 CUA 검수와 구분한다.
사전 미해결 제품 의미/승인 질문은 없고, 위 pin 결함은 수정/검증 전 main 게시 gate로 둔다.

## 검증 결과와 릴리스

pin 누락은 add/edit RED2개 뒤 recursive glob으로 보완했다. shared_records 단위18개 통과, 웹 코드/공유 로더/검수
도구 Ruff 및 두 JS 구문 검사를 통과했다. 게시 대상 파일에서 private-key/GitHub/AWS/OpenAI credential signature0,
신규 .env/runtime/runs 경로0을 확인했다. 기존 UI제안/임시자료 ignore는 유지한다.

광범위 회귀1763개를 실행했다: 최초1760 passed/2 failed/1 skipped(1312.40s).
실패2개는 Spec004 wrapper의 state-root가 저장소 바깥이어야 한다는 기존 안전장치를 저장소 내부 basetemp가 건드린
시험 설정 문제였다. 두 시험만 운영체제 기본 외부 임시 폴더에서 재실행하여2개 모두 통과했다.
따라서 고유1762개 통과/OS 의존1개 skip이며 제품 실패를 skip으로 바꾸지 않았다. skip은
`test_h02_source_inventory.py::test_linked_source_is_rejected_not_read`의 비관리자 symlink 생성 불가다.
전체 엔진/단위/계약/합성 통합/HTTP 및200개 이상 응답·증빙의 strict redaction 검사가 포함됐다.
외부 Playwright 브라우저 suite와 실제 Chromium N01 측정 suite는 이 실행에서 제외했다. 기존 CUA/PDF 검증과 구분한다.

광범위 회귀는 main 후보r1에서 실행했다. 이후 stage 검사에서 발견한 scenario_preparation.html 끝의 빈 줄1개만 제거했다.
표시 의미/로직은 같고 해당 HTML 해시가 달라져 최종 r2를 새 경로/ID로 만들었다. 후보r1은 로컬 이력으로 보존한다.
최종 기본 `shared-ui-main-20261022-r2`, snapshot digest
`d282eb49e1fa448715a307f2879b3ef75a9f5d51ed2231a3de603658ef007788`, JSON SHA
`aec6ca6284e0a9cfead97b73193a9e63e840c498415777f7a945959a205c2197`.
최종 r2의 공유/기본 전환/공통 UI 관련50개 재검증도 모두 통과했다(24.55s, `main-final-tests.xml`).

기존28건/652개 실파일 SHA와 records/target/missing 선언은 동일하다. 원래27 VERIFIED/1 INVALID·미확보1건,
N03 일부/판정·모든 original source SHA/계보는 보존한다. 이전 기본 r2·stage6 r3·presentation r1 JSON을 그대로 보존한다.
게시할 index만 별도 폴더로 내보내 그 폴더의 코드로 기본 공유본을 verify했으며, 무시된 개인 runtime 상태가 없어도
28건/missing1 및 nested partial5개의 일관성을 확인했다. 최종 r2도 같은 방식으로 재확인했다.

ignored 근거: `.controlproof/ui-integration-20261021/`의 main-release-tests.xml, main-wrapper-check.xml,
main-final-tests.xml, main-clean-export.json, main-final-clean-export.json. 이 검증은 새 WhyYou 실제 실행/외부 모델/AWS 검증이 아니다.
이번 전달은 사용자 승인된 ControlProof origin/main 코드 게시이며 외부 SaaS 호스팅·WhyYou 수정·새 실제 Run은 없다.
