# Spec008 Tasks

- [x] T01 원천 조사·specify·clarify·plan: 사용자 승인, 기존 원본 위치와 모드 차이 조사
- [x] T02 analyze: 아래 사전 분석 확정
- [x] T03 공유 목록 구성·검증 도구와 의미 있는 실패 테스트
- [x] T04 실제 원본/중단 기록 수집, 마스킹·PNG·중복·무결성 검토와 공유 snapshot
- [x] T05 웹 공유 읽기 모드·시작 명령·공통 안내와 기존 모드 회귀 확인
- [x] T06 별도 checkout 실제 결과/API·근거·비교/화면 검증, 원본 불변 감사
- [x] T07 validation/traceability/README/인수인계/범위표 수렴

## 구현 전 analyze

CRITICAL/HIGH/해석 차이를 남기는 MEDIUM 0건. 다음은 해결 방법이 명시된 검증 과제다.

- 과거 INVALID를 정상화하면 안 됨 → 파일 해시·원래 검사 상태를 고정하고 기존 판독 차단을 유지.
- PC별 state로 결과가 달라짐 → 공유 reader는 readiness/memos를 사용하지 않고 POST 거부.
- 직접 실행된 원본과 DEMO 혼동 → 명시한 실제 보관 경로만 포함, catalog ID/manifest 대조. 출처를 공유 actual로 표시.
- 누락 N02 기록 → 없는 ID를 snapshot 부재 목록에 남김. 알려진 주요 최종/부모 계보는 존재.
- 기존 PNG 2개 → 이미지 직접 검토 완료: 채용 화면의 오류/로딩 상태, 개인정보·토큰·주소 표시 없음.
- 원본의 비밀값/미등록 파일 → strict scan/allowlist/verify 후 복사, 원본 변경 없음.
- 신규 WhyYou actual 불필요 → 기록 읽기 기능의 실제 파일·HTTP·별도 checkout 검증으로 범위 한정.
