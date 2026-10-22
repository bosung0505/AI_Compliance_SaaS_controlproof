# 발표 화면 정돈 — Spec010 후속

2026-10-22 · 사용자: 전체 현황의 기록/주의 주석을 한곳에 모아 눌렀을 때만 보고, 실제 프로덕트처럼 정돈하고 싶다.
이 변경은 기본 UX의 정보 계층 정리다. 발표 전용으로 사실/판정을 바꾸거나 숨김 모드를 추가하지 않는다.

## Specify / Clarify

FR-017: 업무 공통 헤더의 닫힌 `검증 정보` 한곳에서 공유 원천/검토 시각/해시/누락 선언, 대상 버전/환경/AWS,
집계 의미/판정 한계·사람의 결정 원칙을 확인한다. 기록 banner·중복 주석·sidebar 교육 문장은 기본 본문에서 걷어낸다.
SHARED 읽기 전용/DEMO의 합성 구분은 유지한다. N03 일부·대상 부재·FAIL/INVALID/누락 오류는 결과와 가까운 위치에 유지한다.
전체 현황의 숫자9/0/3과 차트는 실행 범위 그대로다. 최신 검토 카드의 중복 AWS 주석만 정보 패널로 이동한다.
보고서 본문의 범위/비보증·원본 증거·판정/API/웹 실행 경계는 변경하지 않는다.
긴 프로필 코드/Run ID·상세 본문과 기타 발표 디자인은 확인 후 후속 제안으로 제공한다.

## Plan / Tasks

- T023: 공통 base·overview·shell CSS의 안내를 native details 하나로 묶고 실패 계약 → 최소 구현 → 키보드/모바일 검수.
- T024: 이전 기본 r3 JSON 보존, 새 표시 코드와 맞는 새 ID/새 경로의 후보 검증·기본 승격, 관련 회귀와 문서 수렴.

native details를 사용하여 별도 JS/모달/외부 의존성이 필요 없고 Tab/Enter/Space로 접근한다.
헤더 우측의 작은 버튼 모양 summary에 설명적인 접근성 이름을 제공한다. 열리면 헤더 아래 본문 폭으로 펼쳐
모바일에서도 겹침 없이 읽게 한다. 인쇄에서는 공통 헤더 정보를 숨기되 보고서 본문의 범위/한계를 유지한다.
새 후보는 `.controlproof/ui-integration-20261021/presentation-20261022-r1`에 생성한다. 이전 기본 r3 JSON은
`review-data/snapshot.shared-ui-stage6-20261021-r3.json`에 원래 바이트로 보존하며28개/652파일은 수정하지 않는다.
display pin 우회나 원본 재봉인 없이 새 표시 코드/공유본 쌍을 검증한다. 원격 게시/새 actual은 없다.

## Analyze — 구현 전

현재 base의 환경·대상 details, 본문 공유 details, sidebar 교육 문장과 overview의 footnote/footer가 중복된다.
상태와 부가 설명을 분리할 수 있으며 해당 문구의 삭제 대신 닫힌 정보 패널로 옮겨 근거 접근을 유지한다.
N03 일부·DEMO 구분은 이동하지 않는다. report의 실제22내용은 수정하지 않으므로 report PDF 내용 의미는 보존된다.
헤더 변경으로 인쇄 외형이 달라질 수 있어 기존 PDF 바이트를 이번 출력인 것처럼 재사용하지 않는다.
기본 전환 검사의 r3 상수는 이전 JSON 보존 검사로 전환하고, 현재 공유본은 새 ID/현재 display pin을 검증한다.
미결 제품 선택/CRITICAL/HIGH 0. 실제 수행 결과는 아래에 추가한다.

## 실제 검증·완료

T023/T024 완료. base/overview/shell.css만 제품 표시를 변경했다. native details 기본 닫힘, 기록 출처와 판정/환경
설명을 한곳으로 이동했다. 공통 SHARED/DEMO 구분·N03 일부 범위·기존 보고서 내용과 모든 API 의미는 보존했다.

- 새 계약9개 RED 후 구현. UI/공통 탐색/overview50개, 공유본/전환/비교/보고서/준비/public45개 = **95 passed /0 failed /0 skipped**.
  `tests/contract/test_platform_verification_info.py`9개가6개 실제 업무 경로·로컬/DEMO의 정보 위치/기본 닫힘·중요 상태를 검증한다.
  결과: ignored `presentation-ui-tests.xml`(65.61s), `presentation-regression.xml`(137.51s).
- 실제 앱에서 클릭/Enter/Space로 정보 패널의 열림/닫힘을 확인했다. 1440/1280/1024/390px 각각2상태 총8검사,
  닫히면 주석/출처가 보이지 않고 N03 일부 범위는 보임, 열면 모든 설명/해시가 보임, 가로 넘침0, console error0.
  데스크톱 닫힘과 모바일 열림/닫힘을 직접 시각 확인했다. 최종 캡처 `presentation-overview-20261022.jpg`,
  너비/열림 상태 기록 `presentation-browser-checks.json`은 `.controlproof/ui-integration-20261021/`에 보존한다.
- 새 후보 `shared-ui-presentation-20261022-r1`을 기본으로 승격했다. snapshot digest
  `1309c16b418d95d4cb9c932ef7fabfda088b2a6aaa54943c9815bd7f5932dea3`, JSON SHA
  `a7545eeffdb977760a595b4e9a6193a1b83c0ecc8e82a0a06d9871604056a39e`.
  이전 r3는 `review-data/snapshot.shared-ui-stage6-20261021-r3.json`에 원래 SHA
  `011ce767128cc96c05b21416ef0bf742b916bee0063183c8389fb9c2bad95e21` 그대로 보존했다.
- 새 load_snapshot의 표시 pin·전체 원본/verify를 통과했다. 기존/신규652파일의 실해시와 records/target/missing 선언이 같다.
  28건·11프로필·27 VERIFIED/원래 INVALID1개·미확보1건·PNG6개·12/9/0/3·N03 일부·판정/계보/원본 source SHA 불변이다.

최신 미리보기는 `http://127.0.0.1:8785/`다. 해당 서버는 검증한 후보를 명시해 실행했고 그 JSON은 현재 기본과 동일하다.
이전 서버는 종료하지 않았다. 일반 실행도 새 기본을 검증한다. 새 WhyYou Run·원본 변경·외부 게시·commit/push/병합은 없다.
별도 발표 모드·모달/JS·의존성 추가 없음. PDF 신규 생성·전체 엔진 시험·외부 사용성 검수는 이번에 수행하지 않았다.
이전 PDF는 당시 출력물로 보존하며 이번 수정 후 PDF로 표시하지 않는다. 보고서의 기존22개 내용 계약은 통과했다.
미해결 CRITICAL/HIGH 0. 추가 디자인 제안(프로필 코드의 쉬운 이름/결과 요약/캡처 구성)은 구현 완료로 집계하지 않는다.
