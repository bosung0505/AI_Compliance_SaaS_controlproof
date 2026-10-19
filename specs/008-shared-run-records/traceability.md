# Spec008 Traceability

| 요구/기준 | 작업 | 검증 |
|---|---|---|
| FR01/02, SC01/02 | T03/04 | 실제 원본 목록·해시·기존 판정·scan, missing 명시 |
| FR03, SC02/03 | T03/04 | snapshot 경로/추가 파일/변조/중복 실패, INVALID 보존 |
| FR04/05, SC03 | T05 | 진입점·읽기 전용 HTTP·로컬 state 독립 |
| FR06/07, SC01/04 | T05/06 | 기존 판독 회귀, 별도 checkout API·근거·계보·화면 동등성 |
| FR08, SC04 | T07 | 문서·실행 방법·제한 수렴 |

2026-10-19 T01~07 완료. FR01/02: 실제25건/600파일 원본 해시 일치·strict scan0, PNG2 시각 검토.
FR03: 경로/변조/누락/충돌/민감정보/JSON 검토 기준 고정 테스트, 원래 INVALID 보존.
FR04/05: 기본/명시 공유/로컬/env 모드, 공유 POST403, 로컬 state 무접근과 KST 고정 확인.
FR06/07: 별도 Git clone API53개 동일, HTML53개·근거24개 정상, 1280/1024px24화면 검증.
FR08: README/인수인계/범위표/정책/실행 방법 수렴. 상세는 validation.md를 따른다.
