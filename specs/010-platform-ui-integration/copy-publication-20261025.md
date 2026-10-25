# 화면 가독성 후속 변경 main 전달 — 2026-10-25

사용자가 사전 검토 결과를 확인한 뒤 현재 변경을 커밋하고 origin/main에 push하며 로컬 서버를 실행하도록 명시 승인했다.
대상은 ControlProof 저장소이며 WhyYou 소스·운영 서비스·Figma 파일은 이번 Git 전달 범위에 포함하지 않는다.
아래 전달 범위에서는 앞선 미커밋/미게시 상태 문구를 당시 작업 이력으로 읽는다.

## 전달 범위와 순서

T025~T037의 카드 명칭·시나리오 링크 정리, 기대/관찰 설명, H02 핵심 요약/제목 통일, 결과 탐색 이동,
N02 A6/A7 캡처 배치와 대응 검사·문서·기본 공유본/이전 공유본 보존을 함께 전달한다.
새 문구 모듈과 공유본 보존 JSON을 포함한다. 환경 파일·로컬 실행 로그·임시 검사 자료는 제외한다.

현재 기능 브랜치에서 검토한 변경을 커밋하고, 최신 origin/main과의 관계를 확인한 뒤 main에 반영한다.
force push는 사용하지 않는다. 반영한 코드로 127.0.0.1:8785 서버를 실행하고 localhost 응답을 확인한다.
실제 push 성공 여부와 커밋 SHA는 원격 ref와 Git 상태로 확인하며, 실패를 게시 완료로 기록하지 않는다.

## 사전 검증

- 관련 회귀 121 passed/skip0(94.29초), 변경 Python 파일 Ruff 및 git diff --check 통과.
- Git 게시 대상만 복사한 환경에서 기본 공유본 verify 및 주요 화면/API/CSS 9개 HTTP 경로 정상.
- 게시 검토 파일의 private-key/GitHub/AWS/OpenAI credential signature0, 새 .env/runtime/runs 경로0.
- 원본 records/target/missing 선언과 28개 기록·652개 파일·기존 판정/계보는 이전 HEAD와 동일하다.
- 기본은 `shared-ui-n02-capture-20261023-r3`, digest
  `dd4c487d14cb9f4b767c7517660a7d166c69e94a062a173af4b9fe472bfdc335`.
  JSON SHA는 `c608290e3b5d0a82053d11fe223f8a30a7be21d053d887051d9dce1361e222aa`.
  표시 코드와 원본 바이트는 사전 검토 이후 변경하지 않았다. 이번 문서 추가는 표시 pin 대상이 아니다.

## 남은 기존 문제와 검증 범위

`tests/web/test_clickable_affordance.py:18~19`의 예전 `a.detail-link` 선택자 timeout은 현재 코드와
수정 전 main에서 동일하게 재현했다. 전역 Ruff22건도 HEAD와 동일한 기존 테스트4파일의 진단이다.
이번 변경 관련 검사는 통과했지만 전체 suite가 모두 통과한 릴리스로 표현하지 않는다.
광범위 엔진/웹 suite는 완료하지 않았고, 완료된 관련121개와 별도 복사본 HTTP9개를 근거로 삼는다.

새 WhyYou 실제 Run·DB/모델/AWS 실행, 외부 고객 사용성 시험이나 외부 SaaS 배포는 하지 않았다.
사전 검토 원본은 ignored `.controlproof/main-readiness-20261025/`에 보존한다.
