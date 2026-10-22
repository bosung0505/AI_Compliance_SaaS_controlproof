# Spec010 Validation — 0·1단계

2026-10-22 main 마감 검증: 고유1762개 통과/OS 의존1개 skip, 최종 공유/기본 UI50개 재검증 통과.
현재 기본 shared-ui-main-20261022-r2·원본28/652 불변·부분 템플릿5개 pin 보완. [상세 근거/한계](main-publication.md).

2026-10-22 게시 전 검증: 사용자가 main commit/push를 승인했다. 하위partial pin 누락을 RED 시험 뒤 보완하고
새 `shared-ui-main-20261022-r1`을 구성했다. [최신 검증/게시 범위](main-publication.md).
아래 후보/기본 이름·미게시 문구는 당시 기록이다.

2026-10-22 최신: T023/T024(FR-017) 발표 화면 정보 정돈도 완료했다. 관련95개 자동 검사·네 너비의8개 상태/키보드,
원본 불변·새 기본 공유본 `shared-ui-presentation-20261022-r1` 검증 완료. [현재 검증/한계](presentation-polish.md).
이전r3 원본 JSON은 보존했다. 아래 단계별 기본/후보 상태는 당시 기록이며 PDF 신규 출력은 이번에 수행하지 않았다.

최종: **Spec010 Complete — 0~7단계/T001~T022 완료**. 사용자의 팀 검토 완료 간주/전환 승인으로
검증된 stage6 r3를 기본 승격하고 이전 r2 원본·복구 쌍을 보존/검증했다.
[최종 검증·실행·한계](stage7-validation.md) · [팀원 사용/복구 안내](quickstart.md).
51개 고유 전환 검사·일반 실행 HTTP17개·앱 동선 확인. 아래0~6단계의 후보/기본 전환 대기는 당시 이력이다.

최신 후속: **6단계 T020/T021 완료**. 최종 후보 원본/PNG·민감정보와 웹324개 회귀, 실제 앱44개 너비/키보드·
Edge A4 PDF26페이지와22개 내용/원본 링크를 검수했다. [현재 증거·실행·한계](stage6-validation.md). 7단계는 후속이다.
아래0~5단계는 당시 이력이다.

최신 후속: **5단계 T018/T019 완료**. 비교·보고서22개 내용·별도 준비/로컬 메모와 모드 경계를 반영했다.
[현재 구현·자동/실제 검수·r4 실행](stage5-validation.md). 아래0~4단계는 당시 이력이다. 통합/PDF·기본 전환은 후속이다.

최신 후속: **4단계 T013~T017 완료**. 현재 코드·후보·자동 회귀 및 실제 화면 검수는
[4단계 검증 기록](stage4-validation.md)을 따른다. 이하0~3단계 문단은 당시 이력이다.

최신 후속: **3단계 T011/T012 완료**. 현재 업무 화면·후보 공유본·95개 검사와 브라우저 검수는
[3단계 검증 기록](stage3-validation.md)을 따른다. 아래 0·1·2단계 기록은 당시 이력이다.

후속: 사용자 승인으로 2단계 T009/T010도 완료했다. 현재 구현과 후보 공유본 실행은
[2단계 검증 기록](stage2-validation.md)을 따른다. 아래는 0·1단계 당시의 검사/미실시 이력이다.

검증일: 2026-10-21 · 브랜치 `010-platform-ui-integration` · 기준 HEAD `fb219d0`.

**0단계 기준/명세와 1단계 데이터·HTTP·상태·PNG 계약 준비 완료.**
T001~T008 완료, T009~T022 및 신규 제품 화면/라우트/표시 투영/PNG 제공은 미착수다.
이번 완료는 프론트엔드 구현이나 최종 화면 검수 통과가 아니다.

## 실제 수행 결과

| 검사 | 결과 | 의미 |
| --- | --- | --- |
| 검토 snapshot 로드/verify | 성공 | r2, 28건, missing1, digest `8e88ccf5bcccce7a870124cbd711b1ebe38e3fceab1c6c4484783e05d9e18bcb` |
| 기준 inventory | 652개 실파일 SHA 일치 | 27 VERIFIED/1 원래 INVALID, 미확보 N02 1건·기존 판정/계보 보존 |
| 디자인 5개 | 원본 SHA=로컬 보존본=baseline | 전달 폴더를 수정하지 않음, 보존본은 `.controlproof/ui-integration-20261021/design` |
| 기존 카탈로그 시험 | **8 passed** | 관리12·9/0/3·프로필11·정의/문서 정합성 |
| 준비/기존 동작 검사 | **11 passed** | 기준·사례 구조·현재 API 핸들러/데이터·오류/읽기 전용·미구현 상태 확인 |
| 준비한 계약 입력/기대 | **83개, 제품 동작 미실행** | COV18 + HTTP35 + IMG30; HTTP/IMG는 기존 회귀15·미래 계약50 |
| 신규 검사 파일 ruff | 통과 | `checks/test_contract_baseline.py` |
| 독립 설계 교차 검토 | 미해결 CRITICAL/HIGH 0 | 문구 권고 2건·profile query 충돌 반영, 실제 구현 검수와 구분 |

검사 명령(프로젝트 루트, 기존 `.venv`):

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/unit/test_catalog_matrix_parity.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-catalog-01 --tb=short
& .\.venv\Scripts\python.exe -m pytest specs/010-platform-ui-integration/checks/test_contract_baseline.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-contract-01 --tb=short
& .\.venv\Scripts\python.exe -m ruff check specs/010-platform-ui-integration/checks/test_contract_baseline.py
```

이미 사용한 basetemp는 재사용하지 않고 새 경로를 지정한다. pytest가 기존 임시 경로를 정리할 수 있으므로 원본/사용자 폴더를 지정하지 않는다.
전체 기존 시험을 이번 문서/계약 준비에 대해 다시 수행하지 않았다.

## 현재 API 특성 확인의 범위

새 검사 파일은 현재 `server._Handler._dispatch`와 기존 라우트/reader/redaction을 **프로세스 안에서 직접 호출**하고
출력을 캡처한다. 실제 loopback HTTP 전송이나 브라우저 검수는 아니다.

- workbench API: v1, 현재 범위와 판정, 선택 snapshot.
- N01/N03 시나리오 API: 대상 접근과 N03 scope 4줄.
- N01/N03 Run API: 실제 PASS·scope·공유 memo 거부 표시.
- N01 compare API: 부모 불변·계보 문제 없음. report API: 22항목 제공.
- 기존 없는 시나리오404, Host421, 공유 POST403 정책을 실제 dispatch로 확인.
- 신규 `/product`, `/guide`, `/results`, `/prepare`, PNG content는 **현재404**임을 확인.
  이 404 확인은 신규 경로의 미래 정상 동작을 통과시킨 것이 아니다.

## 실행 환경 문제와 조치

1. 최초 카탈로그 pytest 실행은 sandbox 기본 Temp의 numbered directory/cache 접근 문제로 setup 8 errors였다.
   assertions를 실행하기 전 실패였고, 새 프로젝트 내부 basetemp와 cacheprovider 비활성화로 재실행해 8 passed를 얻었다.
   기존 임시 폴더를 삭제하거나 프로젝트 코드를 바꾸지 않았다.
2. 실제 loopback 연결 시도는 `PermissionError [WinError 10013]`으로 첫 요청 전에 차단됐다.
   서버는 finally에서 닫았다. 네트워크 제한을 우회하지 않고 기존 핸들러 in-process 시험으로 범위를 한정했다.
   실제 HTTP transport·브라우저 클릭/반응형/PDF는 **미검증**이다.

## 이후 수행할 검증

계약 JSON은 후속 구현의 입력이다. PNG의 안전한 파일 처리·경쟁 조건·신뢰 허용·8MiB·헤더·현재 파일 변조,
새 query와 집계의 실제 동작, 현재/봉인 정의·공식 대표·전체 이력·N03 부분 범위의 새 화면 표시는 아직 시험하지 않았다.
후속 T009부터 실패 시험→구현→실제 검증을 수행하고 각 사례를 실행 결과에 연결해야 한다.
새 표시 코드에 맞춘 후보 snapshot도 아직 생성/전환하지 않았다.

새 WhyYou actual Run·Docker/DB·외부 모델·설치·push·PR·병합을 수행하지 않았다.
원본652파일·원래 source SHA·판정·카탈로그·시나리오·엔진/웹 런타임을 유지했다.
`.gitignore`의 기존 수정과 Git 제외 목업/전달 보존 파일을 보존했다.
