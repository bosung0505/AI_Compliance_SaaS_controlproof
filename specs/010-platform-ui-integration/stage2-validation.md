# Spec010 2단계 검증·실행

2026-10-21 · `010-platform-ui-integration` · 기준 `fb219d0` 위의 로컬 변경.

**T009/T010 완료.** 팀원 폴더의 소개/도입 안내 디자인과 공통 워크스페이스 프레임을 현재 Python/Jinja 웹에 적용했다.
전체 Spec010 완료는 아니다. 대시보드/목록·실행 상세/증빙 확장·PNG content·기본 공유본 전환은 후속 단계다.

## 반영 내용

- `/product`: 팀원 index의 소개·제품 요약·검증 과정 탭·네 통제 관점·공식 H03 사례·FAQ.
  공식 범위 수치는 HTML 전용 catalog 투영에서 읽는다. 예시 7/2/3을 복사하지 않고 현재 9/0/3과 N03 일부 실행을 보인다.
- `/guide`: 팀원 guide의 9개 안내 체크·진행 표시·UTF-8 BOM TXT 다운로드. 체크 값은 서버로 보내거나 READY로 저장하지 않는다.
- `/` 등 기존 업무 화면: 같은 브랜드/색상·공통 헤더·왼쪽 탐색·모드 표시·접근 가능한 좁은 화면 메뉴를 적용했다.
  기존 판정/규칙/증빙/보고서 본문과 deep link/API 의미는 유지했다.
- 공통 CSS/JS는 자체 정적 파일이며 외부 폰트/CDN·인라인 script/style·CSP 완화가 없다.
  메뉴 닫기 후 라벨/aria 상태, Escape·포커스, 과정 탭 Home/End·방향키를 지원한다.
- 실제 결과 `/`와 합성 DEMO `/demo/` 진입을 구분한다. 대표 사례는 시나리오/실행 이력으로 연결한다.
- 현황 문장에서 0개 NOT_RUN key가 생략돼 숫자가 빈칸으로 보이던 기존 표시 오류를 default(0)으로 바로잡았다.
  새 그래프나 목록 필터를 구현한 것은 아니다.

## 후보 공유본

최종 후보: `.controlproof/ui-integration-20261021/stage2-shared-r3/snapshot.json`.

- ID `shared-ui-stage2-20261021-r3`.
- digest `31222dfb638455d6e395716679ff688eabee506325b85508caf73950852c8be1`.
- 이전 기본 r2의 **28개 records 전체·652개 파일 SHA·판정·source SHA·계보·target·missing_records가 동일**하다.
- 27 VERIFIED/원래 INVALID 1개, N02 미확보 이력1개, 검토 PNG 해시를 보존했다.
- `checks/build_candidate.py`는 새로운 `.controlproof/` 하위 목적지만 허용한다. 기존 경로를 덮어쓰거나 원본을 재봉인하지 않는다.
  생성 후 전체 `load_snapshot` 검증이 성공했다. r1/r2 후보는 CSS/문구 보완 전 맥락으로 보존하며 현재 코드는 r3와 맞는다.

**기본 `review-data/snapshot.json`은 변경하지 않았다.** 현재 새 표시 코드에서 이전 기본 r2로 시작하면 해시 불일치로 거부하는 것이
예상 동작이다. 검증을 끄지 말고 아래 후보 경로를 명시한다. 기본 공유본 게시/전환은 후속 단계다.

## 로컬 실행

```powershell
& .\.venv\Scripts\python.exe -m engine.web --shared-snapshot .controlproof/ui-integration-20261021/stage2-shared-r3/snapshot.json --port 8782
```

소개 `http://127.0.0.1:8782/product` · 안내 `/guide` · 실제 기록 `/` · 합성 `/demo/`.
공유본 열람에는 WhyYou·Docker·DB·.env가 필요 없다. 기존 CONTROLPROOF_RUN_ROOT 환경 변수가 있으면 공유 옵션과 혼용하지 않는다.

검토용 후보를 다시 생성할 때는 기존 목적지를 재사용하지 않고 새 경로/ID를 사용한다.

```powershell
& .\.venv\Scripts\python.exe -m specs.010-platform-ui-integration.checks.build_candidate --out .controlproof/ui-integration-20261021/<새-경로> --snapshot-id <새-ID>
```

## 자동 검사

| 묶음 | 결과 | 검증 범위 |
| --- | --- | --- |
| 신규 public/shell 계약 | 9 PASS | 새 GET·카탈로그 수치·원본/준비 미조회·체크9개·정적 자산/인라인 금지·공통 nav·Host/공유 POST |
| 현재 기준/기존 handler | 9 PASS | 원본/디자인/83사례 구조·현재 API·N01/N03·compare/report·예외·아직 없는 후속 경로 |
| 기존 카탈로그 정합성 | 8 PASS | 현재 12/9/0/3·11프로필·문서/정의 |
| 기존 HTTP·US2·공유 웹 | 30 PASS | 실제 loopback HTTP, CSP/Host/CSRF·무결성·증빙·메모·보고서·readonly |
| JS 구문·신규 Python ruff·diff 공백 | 통과 | platform.js, public.py 및 새 검사/후보 도구 |

**최종 26+30=56개 통과.** 신규 시험의 최초 실행은 7 failed/2 passed로 `/product`·`/guide` 부재와 공통 shell 부재를 확인했다.
구현 도중 1개 shell 미적용 실패를 해결했고, 실제 화면에서 원본 미연결 문장·0개 숫자 누락·기존 span 스타일의 로고 색 영향을 수정했다.
계약 JSON 83개 전체의 미래 동작을 이번에 모두 통과시킨 것은 아니다.

```powershell
$env:CONTROLPROOF_UI_TEST_SNAPSHOT='.controlproof/ui-integration-20261021/stage2-shared-r3/snapshot.json'
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_platform_public_pages.py specs/010-platform-ui-integration/checks/test_contract_baseline.py tests/unit/test_catalog_matrix_parity.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage2-final-01 --tb=short
& .\.venv\Scripts\python.exe -m pytest tests/contract/test_web_http.py tests/contract/test_web_http_us2.py tests/contract/test_shared_web.py -q -p no:cacheprovider --basetemp .controlproof/ui-integration-20261021/pytest-stage2-http-01 --tb=short
node --check engine/web/static/platform.js
```

재검사 시 basetemp는 새 경로를 지정한다. 전체 프로젝트 시험은 재실행하지 않았다. 이전 기본 snapshot과 현재 코드 일치를 가정하는
`test_shared_snapshot_matches_current_code.py`는 기본 전환 전 현재 checkout에 그대로 적용할 수 없다. 후보와의 일치는 위 검증으로 확인했다.

## 실제 브라우저 확인

앱 내 브라우저로 실행한 서비스의 HTTP 페이지를 확인했다. 전달된 file:// 목업을 열람한 것으로 대체하지 않았다.
처음 샌드박스 서버는 앱 브라우저에서 timeout이 났고, 로컬 통신 권한 승인 뒤 별도 서버/HTTP 시험으로 확인했다.
기존 샌드박스 서버와 중간 후보 서버는 종료했다.

- 소개 너비 1440/1280/1024/900/390px, 안내 1440/1024/390px, 기존 업무 화면 1280/1024/390px에서 문서 가로 넘침 없음.
- 소개 범위 9/0/3, N03 일부 실행·미검증 한계 안내와 실제 자료 진입을 확인했다.
- 모바일 메뉴 열기/닫기·Escape, 같은 페이지 링크를 누른 뒤 메뉴 라벨/expanded=false를 확인했다.
- 검증 과정 탭 클릭·Home/End 선택과 표시 패널을 확인했다.
- 안내 체크9개, 하나 선택 후 1/9 표시, TXT 실제 다운로드를 확인했다.
  파일은 UTF-8 BOM이며 선택1/미선택8과 실행 승인 비대체 문구를 확인했다.
- 실제 공유 화면 r3 ID·KST·readonly·원본 미확보1건·대상/환경과 0개 표기를 확인했다.
- 관측한 브라우저 콘솔 error 0. 화면/상호작용 결과는 로컬 `browser-checks-stage2.json`에 기록했다.

로컬 화면 자료: `.controlproof/ui-integration-20261021/stage2-product-desktop.jpg`, `stage2-product-mobile.jpg`,
`stage2-guide-mobile.jpg`, `stage2-workspace-desktop.jpg`.

## 한계·다음 단계

전체 Run/증빙 동선의 새 디자인 이식, PNG 표시/접근 차단, 보고서 PDF 최종 검수, 비작성자 사용성은 후속이다.
다음은 T011/T012의 현황 그래프·네 기준 카드/목적·기준별 결과 목록과 URL 검색 초기화다.
새 WhyYou 실제 실행, 모델 호출·운영/AWS 검증, 설치·커밋·push·PR·main 병합·호스팅은 수행하지 않았다.
