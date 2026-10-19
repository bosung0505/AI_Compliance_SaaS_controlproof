# 팀 공유용 실제 실행 기록

이 폴더는 합성 지원자·격리 로컬 환경에서 실제 실행한 봉인 기록의 공유본이다. DEMO 화면용 생성 데이터가 아니다.
같은 `fixes-and-remaining-work` 코드와 `snapshot.json`을 받으면 같은 결과·근거·계보를 조회한다.
새 테스트를 실행한 것, 외부 AI 품질이나 AWS를 검증한 것은 아니다.

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

- 7개 시나리오·9개 프로필의 대표 최종 결과, 발견한 최초 FAIL·재테스트·중단 등 **25개 Run / 600개 파일**.
- N02 4개, H01 4개, H02 3개, H03 4개, E01 4개, E02 2개, E03 4개. E01/E02 추가 재현 원본도 포함한다.
- 원본 약 2.62MB. 24개 VERIFIED와 원래 INVALID인 N02 중단 `ce5f2750…` 1개를 바이트 그대로 보존했다.
  INVALID는 오류 기록으로 유지하며 결과·근거 열람은 기존 무결성 차단을 따른다.
- N02 과거 중간 `7b59237e-0a96-403a-9add-28b91011e950` 원본은 조사 범위에서 찾지 못했다. 문서 요약과 부재 표시를 유지한다.
  최종 N02 및 직접 부모 원본은 포함돼 있다.
- `snapshot.json`은 파일별 SHA-256, 원래 무결성 상태, 표시 코드·시나리오·H02 검토 기준 JSON을 고정한다.
  원본 파일의 줄바꿈은 `.gitattributes`의 `-text`로 보존한다. 코드/카탈로그가 다른 버전이면 시작을 거부한다.
- 신규 공유본은 원본을 바꾸지 않고 새 버전으로 구성·검토한다. 기존 공유본에 파일을 임의 추가하거나 재봉인하지 않는다.

상세 검증은 [Spec008 Validation](../specs/008-shared-run-records/validation.md),
설계 이유와 정책은 [공유 준비 조사](../docs/research/Run_Record_Sharing_Preparation.md)를 따른다.
