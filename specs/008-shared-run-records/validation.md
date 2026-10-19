# Spec008 Validation

2026-10-19 로컬 기능 범위 Complete. source baseline CP `4c2a73d` 위의 사용자 승인된 공유 정책·Spec008 변경.
WhyYou 제품 변경/새 actual Run 없음. 이번 actual validation은 봉인된 실제 기록을 다른 checkout에서 읽는 기능 검증이다.

초기 조사: catalog 24개 Run 참조 중 두 root에 21개 고유 원본. 별도 보관 폴더에서 E01/E02 재현 2개 추가 발견, 둘 다 VERIFIED/strict scan0.
N02 `7b59237e…` 미발견. 두 root의 나머지 선택 원본 strict scan0.
추가 N02 시도 `691abd8a…` VERIFIED, `ce5f2750…` INVALID(`N02-A7:recovered-proof-unreadable`) 상태 보존 대상.
광역 파일 검색에서 테스트 cache 일부 접근 거부가 있었으므로 전체 디스크 부재로 단정하지 않는다.
원본 PNG2개 시각 검토 완료(PII/비밀값 노출 없음). 자동/실제 검증 결과는 구현 후 덧붙인다.

## 최종 검증

- 공유 snapshot: `69fed94e9c45aeae72fd1debd4aa63e99a803316535292484e4516f9c66e73ee`.
  원본25건/600파일/2,616,606바이트. 24개 VERIFIED, 원래 INVALID인 `ce5f2750…`는 동일 오류 상태 보존.
  최초 FAIL·중단/판정 불가를 삭제/정상화하지 않았다. 최종 대표9프로필과 발견한 계보를 포함한다.
- 원본 모든 파일과 공유본 SHA 일치, strict scan0, 허용 텍스트/검토 PNG2만 배포. 임시 probe/환경/DB는 미포함.
- 최종 자동101 PASS(104.40초): 공유 목록·변조/부재/경로/중복/비밀값·코드 줄바꿈·JSON 검토 기준 고정,
  기본/명시 공유/로컬/env 선택, PC state 무접근·POST 차단·KST, 기존 workbench/scenario/compare/report/remediation와 HTTP 회귀.
  변경 Python Ruff 통과. 최초 sandbox HTTP는 WinError10013으로 실패했고 허용된 loopback 실행에서 확인했다.
- 실제 Git roundtrip: 별도 seed 저장소에 현재 표시 원천과 공유본을 커밋하고 `core.autocrlf=true`로 새 clone.
  원래 `.controlproof`, `.env`, `cp-local`이나 WhyYou 없이 실행했다. Python interpreter/의존성만 기존 설치를 재사용했고,
  `engine.__file__`이 새 clone을 가리킴을 확인했다. 이는 같은 PC의 별도 clone 열람 검증이다.
- 최초 roundtrip에서 H02 검토 기준 `scenarios/h02-reviewed-trees.json` 누락으로 기록 검증이 실패했다.
  파일을 표시 원천 고정 목록에 추가하고 회귀 테스트를 넣은 뒤 최종 roundtrip을 통과했다. 원본은 수정하지 않았다.
- 두 서버 API53개(workbench/report/12시나리오/25Run/14비교) JSON 전체 일치. HTML53개 HTTP200,
  VERIFIED 각 Run의 대표 근거24개 HTTP200. 원래 INVALID는 기존 무결성 차단 표시를 유지한다.
- 실제 브라우저24페이지(1280/1024px 각12): 목록/보고서/개요/실행/비교/무결성 오류/근거 화면,
  가로 넘침·console/page 오류0. 스크린샷 직접 검토. 기존 공통 디자인 유지.
- 기계 검증 요약은 [validation-results.json](validation-results.json), 실행 방법은 [Quickstart](quickstart.md).

## 보존·제한·인계

N02 과거 중간 `7b59237e-0a96-403a-9add-28b91011e950`는 원본 미발견으로 명시한다. 최종 N02와 직접 부모는 포함.
모든 과거 중간 실행을 확보했다고 주장하지 않는다. 새 WhyYou actual Run, 외부 AI 품질, AWS, 팀원 PC 새 실행은 미수행.
Spec005 외부 사용성·main 병합도 별도다. 공유 화면 검증을 시나리오 새 PASS로 쓰지 않는다.
기존 source SHA/Run 시각/판정/manifest는 불변이다. 후속 게시 commit을 과거 Run source SHA에 대입하지 않는다.

공유 화면을 현재 `localhost:8766`에 연결했다. 기존 실행 root는 삭제하지 않았으며 명시적 로컬 모드로 다시 읽을 수 있다.
코드와 `review-data/`는 기존 `fixes-and-remaining-work`에 함께 전달한다. 실제 게시 commit은 Git HEAD/remote로 확인한다.
