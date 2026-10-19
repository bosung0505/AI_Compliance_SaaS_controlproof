# H-02 1단계 조사 결과 — 2026-10-19

Current stage2 is Complete in the documented local scope; this section is preserved stage1 data/history. See actual-closure.md and contracts/execution.md for actual records and final review.

기능 목록과 다음 확인 지점이다. 실제 테스트 결과나 통과 판정이 아니다. H-02는 NOT_RUN이며
전체12개/실제 실행6개/미실행3개/대상 없음3개를 유지한다.

| 영역 | 수집 내용 | 개수 |
|---|---|---:|
| 어시스턴트 진입 | 자료 검색, 답변, 스트리밍 답변 API | 3 |
| 어시스턴트 연결 | 검색·답변·색인 생성·모델 선택·API 조립 | 5 |
| 모델 입력 계약 | system, max_tokens, temperature, messages, anthropic_version | 5 |
| 모델 답변 계약 | answer, source_ids | 2 |
| 실제 워커 처리 연결 | 아래9개 이벤트 | 9 |
| 라우팅만 있는 이벤트 | handler 미등록 항목 별도 기록 | 8 |
| API 실행 환경 보조 처리 | 초대 메일, 미디어, 보고서, 개인정보 삭제 | 4 |
| 추적 시작 지점 | 답변/조회 단축 경로/모델 호출/이벤트 처리/워커 조립/실행 진입 | 6 |
| 합계 | 조사 단위이며 테스트 통과 개수가 아님 | 42 |

워커 연결: submission.analysis_requested, submission.analysis_completed, interview.completed,
media.postprocess_requested, report.generation_requested, deletion.requested, retention.expired,
position.capacity_changed, capacity.reconcile_requested.

라우팅만 있는 항목: system.parity_probe, invitation.consent_completed, strategy.ready,
interview.turn_finalized, interview.session_paused, report.ready, deletion.target_requested,
deletion.target_verified. 등록 부재와 실제 런타임에서 무시되는지는 구분한다.

보고서·검색 자료 저장, 면접 완료 진행 상태, 감사 기록은 합격 결정과 구분한다. 각 기능이
실제로 바꾸는 대상을 확인한 뒤 조회/보조 저장/채용 결정 변경/확인 불가로 분류한다.

특히 채용 단계 조회가 오래된 데이터의 빈 단계를 채우는 코드로 이어진다. 일부 상태는
최종합격 단계로 연결될 수 있어2단계 확인이 필요하다. 아직 실제 FAIL로 판정하거나 수정하지 않았다.

개인정보 삭제 보조 기능은 다른 실행 객체의 속성을 거쳐 연결된다. 수집기는 임의로 해석하지
않고 UNRESOLVED_TARGET으로 남긴다. 준비 출력은 BLOCKED,42개 모두 UNREVIEWED다. 1단계 조사·
수집 코드 완성과 실제 실행 준비 READY는 다르다.

2단계에서는 간접 연결·실제 구독 목록을 대조하고 모든 호출/저장 경로를 확인한다. 낮은 점수
지원자를 선택하고 높은 점수 지원자를 거절할 수 있는지도 별도 대조한다. 최초 실제 결과를
보존한 후 필요하면 수정·재테스트하고, 증거·정리·공통 결과 화면을 마감한다.

현재 Python204개/추적161개; tree fce256e1d3f8975c8dbc709522d57fedf584732bef30c6ab84bb8bc351c810f6.
HEAD/branch/dirty와 바이트 해시는 별도다. 원본 준비 JSON은 .controlproof에 두고 게시하지 않는다.
