# 팀 공유용 실제 실행 기록

2026-10-25 UI 후속 main 전달 승인. 기본 `shared-ui-n02-capture-20261023-r3`와 대응 표시 코드, 이전 공유본 보존 JSON을 함께 커밋·push한다. 원본28/652·records/target/missing 불변. [검증·기존 문제](../specs/010-platform-ui-integration/copy-publication-20261025.md).

2026-10-23 현재 기본 `shared-ui-n02-capture-20261023-r3`: N02 A6/A7 좌우 비교 복원/표 여백 보완. 직전 r2 JSON 그대로 보존, 원본28/652·records/target/missing 불변. [31개 검사·실제 확인](../specs/010-platform-ui-integration/n02-recovery-capture.md). 아래 기본 이름은 이전 이력이다.

2026-10-23 현재 기본 `shared-ui-n02-capture-20261023-r2`: N02 그룹4 A6/A7만 캡처용 가독성/상시 표 적용. 직전 scenario-title JSON 보존, 원본28/652·records/target/missing 불변. [검증](../specs/010-platform-ui-integration/n02-recovery-capture.md).

2026-10-23 현재 기본 `shared-ui-scenario-title-20261023-r1`: H02 전체 화면 표시 제목/검색 통일. 직전 summary 기본 JSON 보존, 원본28/652·records/target/missing 불변. [검증](../specs/010-platform-ui-integration/scenario-title-consistency.md).

2026-10-23 현재 기본 `shared-ui-result-summary-20261023-r1`: H02 핵심 두 문장·강조. 직전 header 기본 JSON 보존, 원본28/652·records/target/missing 불변. [검증](../specs/010-platform-ui-integration/result-summary-emphasis.md).

2026-10-23 현재 기본 `shared-ui-result-header-20261023-r1`: 결과 상단 탐색 이동·쉬운 표시 용어. 직전 observations r2 JSON을 같은 폴더에 보존했다. 원본28/652·records/target/missing 불변. [검증](../specs/010-platform-ui-integration/result-header-readability.md).

2026-10-23 현재 기본은 `shared-ui-observations-20261023-r2`다. 기대/관찰 대응과 기록 출처 안내를 보완했다.
이전 카드 기본 JSON은 `snapshot.shared-ui-cards-20261023-r1.json`에 그대로 보존했다.
원본28건/652파일·판정/계보/미확보 선언 불변. [범위·검증](../specs/010-platform-ui-integration/observation-readability.md).

2026-10-23 기본 표시 공유본은 `shared-ui-cards-20261023-r1`이다. 카드 제목·비링크 표시만 정리했다.
이전 main 기본 JSON을 같은 폴더의 `snapshot.shared-ui-main-20261022-r2.json`에 그대로 보존했다.
28개 실행/652개 원본·판정/계보/미확보 선언은 불변이다. [변경과 검증](../specs/010-platform-ui-integration/control-card-readability.md).

이 폴더는 합성 지원자·격리 로컬 환경에서 실제 실행한 봉인 기록의 공유본이다. DEMO 화면용 생성 데이터가 아니다.
같은 코드와 `snapshot.json`을 받으면 같은 결과·근거·계보를 조회한다.
새 테스트를 실행한 것, 외부 AI 품질이나 AWS를 검증한 것은 아니다.

2026-10-22 기본 공유본은 **`shared-ui-main-20261022-r2`**이다. 공통 검증 정보/발표 화면과 하위 템플릿 pin을 검수한 JSON을 승격했으며
`010-platform-ui-integration`의 새 소개·현황·결과·상세·증빙·비교·보고서·준비 화면과 함께 사용한다.
28건/652개 봉인 파일과 판정은 이전 r2와 같다. 일반 실행에 별도 후보 경로가 필요하지 않다.
[현재 실행·복구 안내](../specs/010-platform-ui-integration/quickstart.md) · [최종 검증](../specs/010-platform-ui-integration/stage7-validation.md).
최신 [정보 정돈/검증](../specs/010-platform-ui-integration/presentation-polish.md). 직전 r3 JSON은
`snapshot.shared-ui-stage6-20261021-r3.json`에 원래 바이트로 보존한다. 앞선 기본 전환 기록은 당시 이력이다.
사용자가 ControlProof origin/main 전달을 승인했다. [main 게시 검증/범위](../specs/010-platform-ui-integration/main-publication.md).
직전 발표 정돈 공유본은 `snapshot.shared-ui-presentation-20261022-r1.json`에 원래 바이트로 보존했다.

이력: 2026-10-20 `shared-actual-20261020-r2`는 `009-closure-followups` 브랜치 코드에 맞춰 구성한 제안본이었다
(`shared-actual-20261020`과 28건 기록·bundle 바이트가 같고, N-03 시나리오 화면 표시 코드만 다시 고정했다).
당시 검토/통합 대기는 위 Spec010 기본 전환 기록으로 대체한다. 이전 JSON은
`snapshot.shared-actual-20261020-r2.json`에 원래 바이트로 보존한다. 표시 코드·카탈로그가 다른 checkout에서는
공유본이 시작을 거부한다. 이전 JSON은 이전 코드 `fb219d0`와 함께만 사용한다.

## 실행

저장소 루트에서 Python 3.12 이상과 프로젝트 의존성을 준비한다. 기존 `.venv`가 있다면 그대로 사용한다.
처음 설치할 때는 다음과 같다(Windows PowerShell).

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e .
```

공유 기록을 확인하고 화면을 연다.

```powershell
& .\.venv\Scripts\python.exe -m scripts.share_records --verify
& .\.venv\Scripts\python.exe -m engine.web --shared-snapshot review-data/snapshot.json --port 8766
```

Chrome 주소: `http://localhost:8766/`. 일반 `python -m engine.web --port 8766`도 로컬 root 환경 변수가 없으면 이 공유본을 연다.
기존 `CONTROLPROOF_RUN_ROOT`가 설정돼 있으면 명시적 공유 옵션과 충돌하므로 현재 터미널에서 해당 변수만 해제한다.
WhyYou·Docker·DB·.env·다른 사람의 PC 폴더는 기존 결과 열람에 필요하지 않다.

새 테스트의 준비 상태 확인과 로컬 메모 기능은 별도 로컬 모드에서 사용한다.
예: `python -m engine.web --run-root .controlproof/runs --port 8767`.
공유 화면은 읽기 전용이며 해당 PC의 READY·개인 메모를 섞지 않는다. 공유 화면 시각은 KST로 고정한다.

## 포함 범위와 보존

- 공유본 `shared-ui-main-20261022-r2`: 9개 시나리오·11개 프로필의 대표 최종 결과, 발견한 최초 FAIL·재테스트·중단 등
  **28개 Run / 652개 파일**. `share_records --verify` 기대 출력:
  `shared-ui-main-20261022-r2 records=28 missing=1 sha256=d282eb49e1fa448715a307f2879b3ef75a9f5d51ed2231a3de603658ef007788`.
  직전 `shared-actual-20261020`과 28건 record(파일 해시·무결성 상태·메타데이터)·bundle 바이트는 차이 0이다.
- N01 2개(부모 `48a70f5e…` 측정 v1 PASS, final `d3aac7d9…` 측정 v2 PASS), N02 4개, N03 1개(`f27b68e8…` PASS), H01 4개, H02 3개,
  H03 4개, E01 4개, E02 2개, E03 4개. E01/E02 추가 재현 원본도 포함한다. N01 화면 캡처 PNG 4장은 사실 관찰을
  [Spec009 validation](../specs/009-n01-n03-notice-scenarios/validation.md)에 남기고 검토 PNG로 허용했다.
- 이전 공유본 `shared-actual-20261019`의 25건(600개 파일)은 파일 해시·무결성 상태·바이트가 그대로이며 3건만 더했다.
  원본 약 3.30MB. 27개 VERIFIED와 원래 INVALID인 N02 중단 `ce5f2750…` 1개를 바이트 그대로 보존했다.
  INVALID는 오류 기록으로 유지하며 결과·근거 열람은 기존 무결성 차단을 따른다.
- N02 과거 중간 `7b59237e-0a96-403a-9add-28b91011e950` 원본은 조사 범위에서 찾지 못했다. 문서 요약과 부재 표시를 유지한다.
  최종 N02 및 직접 부모 원본은 포함돼 있다.
- `snapshot.json`은 파일별 SHA-256, 원래 무결성 상태, 표시 코드·시나리오·H02 검토 기준 JSON을 고정한다.
  원본 파일의 줄바꿈은 `.gitattributes`의 `-text`로 보존한다. 코드/카탈로그가 다른 버전이면 시작을 거부한다.
- 신규 공유본은 원본을 바꾸지 않고 새 버전으로 구성·검토한다. 기존 공유본에 파일을 임의 추가하거나 재봉인하지 않는다.

상세 검증은 [Spec008 Validation](../specs/008-shared-run-records/validation.md),
설계 이유와 정책은 [공유 준비 조사](../docs/research/Run_Record_Sharing_Preparation.md)를 따른다.
