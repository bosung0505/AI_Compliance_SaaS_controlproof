# 플랫폼 화면 실행·인수인계

2026-10-25 UI 후속 전달의 기본은 `shared-ui-n02-capture-20261023-r3`이다. 하위 템플릿의 표시 pin도 포함한다.
[최신 전달 검증·기존 테스트 문제](copy-publication-20261025.md). 아래 이전 공유본/미게시 문구는 당시 기록이며 실행 명령은 같다.

2026-10-22 · Spec010 로컬 프론트엔드 전환/정보 정돈 완료 · `010-platform-ui-integration`.

상단 `검증 정보`에서 기록 출처/해시·실행 환경·집계/판정 한계를 확인한다. 기본 화면에서는 접혀 있다.
[최신 변경·검증](presentation-polish.md). 이전 서버/후보의 기록은 당시 이력이다.

## 실행

저장소 루트에서 기존 Python 3.12+ 프로젝트 가상환경을 사용한다.

```powershell
& .\.venv\Scripts\python.exe -m scripts.share_records --verify
& .\.venv\Scripts\python.exe -m engine.web --port 8785
```

브라우저에서 `http://127.0.0.1:8785/`를 연다. 이미 켜진 서버가 있으면 그 주소를 이용하거나 다른 포트를 지정한다.
이 명령은 기본 `review-data/snapshot.json`을 검증하고 공유 읽기 전용으로 연다. 후보 경로를 별도로 지정할 필요가 없다.
`CONTROLPROOF_RUN_ROOT`가 설정되어 있다면 일반 명령은 로컬 모드를 선택한다. 공유 열람을 원하면 해당 터미널의
이 변수만 해제하거나, 변수가 없는 터미널에서 실행한다. 다른 환경 변수/자격 증명을 수정할 필요는 없다.
기존 결과 열람에는 WhyYou·Docker·DB·외부 모델·`.env`가 필요하지 않다.

| 화면 | 주소 | 확인할 내용 |
| --- | --- | --- |
| 전체 현황 | `/` | 9/0/3, N03 일부 범위, 네 기준의 목적/시나리오 |
| 서비스 소개·도입 안내 | `/product`, `/guide` | 제품 범위와 사용 절차 |
| 테스트 결과 | `/results` | N/H/A/E 목록·검색/필터·전체 초기화 |
| 정의와 실행 기록 | `/scenarios/N-03` 등 | 현재 정의·프로필·공식 결과·전 이력 |
| 선택 결과·증빙 | 목록의 실제 Run 링크 | 조건별 관찰·출처·검토된 원본 PNG |
| 비교·보고서 | `/report`와 실제 child 비교 링크 | 최초 FAIL/재테스트·N01 측정 보강·버전/한계·인쇄 |
| 테스트 준비 | `/prepare` | 공유에서는 읽기 전용; 준비 확인/메모는 명시적 로컬 모드 |
| 합성 예시 | `/demo/` | 실제 기록과 분리된 DEMO |

## 함께 보존할 파일

HTML 하나를 배포하는 방식이 아니다. Python 코드, Jinja 템플릿·정적 파일, 카탈로그/시나리오,
`review-data/snapshot.json`과 `review-data/bundles/`를 같은 버전으로 보존한다.
현재 기본 ID는 `shared-ui-main-20261022-r2`이며 검수한 후보와 JSON까지 바이트가 같다.
직전 발표 정돈 JSON은 `review-data/snapshot.shared-ui-presentation-20261022-r1.json`에 보존했다.
직전 기본 r3 JSON도 `review-data/snapshot.shared-ui-stage6-20261021-r3.json`에 보존했다.
원본28건/652파일·27 VERIFIED/1 INVALID·미확보 N02 1건을 유지한다. 표시 코드가 달라지면 시작을 거부하는 검증도 유지한다.
검토 기록은 [최종 전환 검증](stage7-validation.md), 전체 자동/화면/PDF 근거는 [6단계](stage6-validation.md)에 있다.
이번 릴리스의 전달 대상은 사용자 승인된 origin/main이다. 게시 검증/전달 범위는 위 main 마감 기록을 따른다.

## 이전 화면으로 복구

현재 작업을 reset하거나 파일 일부만 덮어쓰지 않는다. 이전 코드 `fb219d0`와 그 코드에 맞는
`shared-actual-20261020-r2`를 별도 폴더에서 함께 실행한다. 보존 JSON은
`review-data/snapshot.shared-actual-20261020-r2.json`이며 SHA는
`26df887d6a8b26bf2a29b311e805de7a7eaebb0eb6ccdcf19710e358d64d99df`다.
현재 코드에 이 JSON만 지정하면 정상적으로 표시 코드 불일치로 거부한다.

저장소 루트에서 다음처럼 **새 이름**을 사용한다. 기존 서버와 작업 폴더는 유지한다.

```powershell
$uiProject = (Get-Location).Path
$uiRollback = Join-Path $uiProject '.controlproof/ui-integration-20261021/rollback-view-NEW'
$uiArchive = "$uiRollback.zip"
if ((Test-Path -LiteralPath $uiRollback) -or (Test-Path -LiteralPath $uiArchive)) { throw '새 경로를 지정하세요.' }
git archive --format=zip "--output=$uiArchive" fb219d0c6923c6be09691fcae0ead670f9700b39
if ($LASTEXITCODE -ne 0) { throw '이전 코드 보존 실패' }
Expand-Archive -LiteralPath $uiArchive -DestinationPath $uiRollback
$uiPython = Join-Path $uiProject '.venv/Scripts/python.exe'
Push-Location $uiRollback
try {
    & $uiPython -m scripts.share_records --verify
    & $uiPython -m engine.web --port 8767
} finally {
    Pop-Location
}
```

이전 코드/로더와 보존 r2의 실제 로드 검증은 별도 임시 경로에서 통과했다. 위 명령은 이전 화면의 열람 복구이며,
현재 데이터 삭제·새 대상 테스트 실행·기존 포트의 서버 종료를 하지 않는다.
