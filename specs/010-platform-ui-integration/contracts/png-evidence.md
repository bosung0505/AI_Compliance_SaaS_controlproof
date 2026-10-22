# PNG 증빙 원본 제공 계약

2026-10-21 · **4단계 endpoint 구현·경계 시험·실제 이미지 열람 확인**.
현재 구현/미실시 범위는 [4단계 검증](../stage4-validation.md)을 따른다. 아래0·1단계 문구는 계약 작성 당시 이력이다.
`viewable`의 기존 텍스트 의미는 유지하고 PNG는 별도 image 표시/엄격한 binary 응답으로 제공한다.
현행 `WorkbenchReader.evidence()`와 `_viewability()`는 텍스트 원문만 제공한다. 이 계약은 N-01의 PC·모바일 캡처를
안전하게 열람하기 위한 별도 확장이며, 기존 봉인 파일·판정·PNG 바이트를 수정하지 않는다.

## 1. 경로·입력

`GET /runs/{run_id}/evidence/content?ref={opaque_ref}`

DEMO 대응은 `GET /demo/runs/{run_id}/evidence/content?ref={opaque_ref}`다.
`run_id`는 기존 canonical UUID 소문자 문자열이고 `ref`는 해당 Run의 기존 evidence index 식별값이다.
`file:n01-pc-capture.png`도 파일 경로 입력이 아니라 등록된 ref와의 정확한 일치로만 사용한다.
서버는 manifest/index에서 상대 경로를 찾는다. query에 path, root, 파일 URL, 원격 URL을 받지 않는다.
ref는 정확히 한 번 필요하며 중복·빈값·다른 키·잘못된 percent/UTF-8·제어 문자는 400 `USAGE/EVIDENCE_REF_INVALID`다.
ref의 디코딩 길이는 512 code point 이하로 제한한다. 임의 ref를 path로 붙이지 않으며 두 번 디코딩하지 않는다.

## 2. 모드별 신뢰 원천과 허용 집합

| 모드 | PNG 허용 근거 | 기본 거부 |
| --- | --- | --- |
| SHARED | `load_snapshot`으로 검증한 **선택 snapshot**의 `records` 내 해당 Run, `files` map의 PNG 경로→SHA-256와 봉인 manifest/index가 모두 일치 | 선택 snapshot 밖 Run·파일, 다른 root의 동일 ID, manifest에 없는 자료는 제공하지 않음 |
| LOCAL | 서버가 신뢰하는 별도 검토 허용 목록의 정확한 `(run_id, ref, sha256)`와 봉인 manifest/index가 일치 | 허용 목록이 없거나 해당 tuple이 없으면 403. 로컬 폴더에 존재한다는 이유로 허용하지 않음 |
| DEMO | 합성 캡처에 대해 독립적으로 검토된 DEMO 전용 tuple 허용 목록과 해당 DEMO manifest/index가 일치 | ACTUAL 허용 목록 재사용 금지. 미등록 DEMO PNG는 403 |

현재 snapshot v1에는 `reviewed_pngs`라는 필드가 **없다**. `build_snapshot`의 `reviewed_pngs` 입력은 게시 시점의
개별 PNG 검토 허용 집합이며, 결과 snapshot의 `records[].files`가 게시한 바이트 해시를 고정한다.
SHARED 런타임 허용 집합은 검증해 로드한 이 PNG 항목에서 파생한다. 새 필드를 이미 존재한다고 가정하지 않는다.
기준 목록은 `../baseline.json`의 `reviewed_png_files`와 연결한다(현재 파일 6개, 고유 해시 5종).
단순히 파일 확장자가 PNG인 모든 디스크 파일을 탐색해 허용 집합을 만들지 않는다.
후보 snapshot은 기존 검토/민감정보 검사 과정으로 생성하며 원래 INVALID 1건을 VERIFIED로 바꾸지 않는다.
LOCAL/DEMO 허용 목록의 구체 저장 형식은 구현 작업에서 테스트 가능한 서버 내부 입력으로 둔다. URL·form·브라우저
저장소로 허용 목록을 바꾸는 기능은 추가하지 않으며 명시적 신뢰 입력이 없으면 거부한다.

## 3. 요청 시 검증 순서

4단계 보충: 신뢰되지 않은 경로를 읽기 전에 root/Run/manifest와 등록 경로의 link·이탈을 우선 거부한다.
아래2의 Run 존재/선택 범위 검사를 마친 뒤 strict verify를 먼저 수행하고, 이어 index의 ref를 찾는다.
따라서 INVALID와 unknown ref가 함께 있으면 422가 우선한다. 정상 Run의 unknown ref는 계속404다.
이는 검증 불가 index를 사실로 파싱/노출하지 않기 위한 구현 선택이며 PNG 허용 범위를 넓히지 않는다.
Windows path stat과 handle fstat의 ctime 의미 차이를 고려하여 동일 API 안의 시간, 공통 identity/크기/mtime,
최종 handle 경로와 동일 buffer hash를 함께 검사한다.

1. 기존 Host·메서드·모드 경계를 먼저 적용한다. 선택 reader와 신뢰 root는 서버 설정에서만 가져온다.
2. canonical Run과 ref를 해석하고 해당 Run의 봉인 manifest/index에 등록된 증빙 한 건을 찾는다.
   없는 Run/ref는 404다. 유사한 이름이나 다른 Run의 자료로 대체하지 않는다.
3. Run은 **엄격한 원래 `verify_bundle` 결과 `VERIFIED`**여야 한다. 기존 텍스트 화면의 ABORTED missing-link 완화가
   있더라도 이 바이너리 경로에는 적용하지 않는다. INVALID·무결성 불명·필수 근거 누락은 422다.
4. SHARED는 로드한 snapshot의 `snapshot_id + snapshot_digest + records[run_id].files` 문맥에 해당 항목이 있어야 한다.
   선택 snapshot이 처음부터 누락/변조/표시 해시 불일치면 서버 시작 자체를 거부하는 기존 정책을 유지한다.
   정상 시작 뒤 파일이 변한 경우도 요청 시 재검사해 차단한다. LOCAL/DEMO는 전용 tuple 승인 여부를 검사한다.
5. manifest/index의 상대 경로는 canonical POSIX 상대 경로여야 한다. 빈 경로, `.`/`..`, 절대 경로, 역슬래시,
   드라이브/UNC, ADS(`:`), NUL과 root 이탈을 거부한다. root와 Run 및 모든 중간 경로·파일의 symlink/junction을 거부한다.
   일반 파일만 허용하며 다른 Run 안의 파일로 넘어가지 못한다. 폴더 전체 static 공개는 금지한다.
6. 봉인 metadata의 MIME은 정확히 `image/png`, 상대 경로 suffix는 `.png`여야 한다. 실제 파일은
   **8,388,608 bytes(8 MiB) 이하**이고 manifest size와 일치해야 한다. 상한은 raw byte 기준이며 같으면 허용한다.
   bound된 읽기로 상한+1 byte에서 중단한다. 기존 텍스트 원문 256 KiB 상한을 바꾸지 않는다.
7. 제공할 바이트가 `89 50 4E 47 0D 0A 1A 0A` PNG signature로 시작하고 SHA-256이 봉인 metadata 및 모드별 허용 해시와
   일치하는지 확인한다. 확장자/브라우저 sniffing만으로 승인하지 않는다. signature만 일치하는 임의 신규 PNG도 허용하지 않는다.
8. 검증한 **동일 byte buffer**만 응답한다. 검증 뒤 경로를 다시 열어 새 바이트를 제공하지 않는다.
   안전한 handle을 확보하고 검증 중 경로/링크가 바뀌는 경쟁을 방지하거나 탐지해 차단한다.
   캐시는 현재 파일 바이트·manifest·snapshot·승인 tuple의 동일성을 확인할 수 없으면 승인 근거가 될 수 없다.

실제 PNG의 내용에 개인정보가 없는지는 게시/승인 전에 사람이 검토한다. 텍스트 scanner가 PNG를 해독해 개인정보를
제거한다고 주장하지 않는다. PNG는 서버에서 변환·redaction·재압축하지 않으며 원본 해시·증빙 연결을 유지한다.
이 경로는 PNG만 대상으로 하며 SVG/HTML/PDF/JPEG 또는 사용자 업로드 기능으로 확대하지 않는다.

## 4. 응답·실패 계약

성공 200은 검증된 원본 PNG 바이트이며 헤더는 다음과 같다.

```text
Content-Type: image/png
Content-Length: <검증한 buffer의 정확한 길이>
Content-Disposition: inline; filename="controlproof-evidence.png"
Cache-Control: no-store
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'
```

inline은 같은 출처 `<img>` 열람용이다. 파일명은 고정하며 Run·지원자·디스크 경로를 넣지 않는다.
별도 다운로드가 필요하면 UI에서 같은 안전한 이름을 쓰며 임의 `download` query를 추가하지 않는다.
Range·변환·원격 가져오기·이미지 proxy는 구현하지 않는다. Range를 요청해도 정상 파일을 검증한 200 전체 응답이다.
검증에 실패한 바이트를 오류 body나 data URI에 포함하지 않는다. 기존 generic 오류 화면과 출력 마스킹을 유지한다.

| HTTP | 기존 error_kind / 신규 code | 조건 |
| --- | --- | --- |
| 400 | `USAGE/EVIDENCE_REF_INVALID` | ref 누락/중복/형식·길이·인코딩 오류 또는 알 수 없는 query |
| 403 | `CONTRACT/EVIDENCE_POLICY_BLOCKED` | 해당 Run·ref가 등록되어 있음을 확인한 뒤 모드별 검토 허용 불충족, PNG 이외 MIME, 부적절 경로·링크 또는 공유 PNG 허용 항목 불충족 |
| 404 | `NOT_FOUND/RUN_NOT_FOUND` 또는 `EVIDENCE_NOT_FOUND` | 선택 root에 canonical Run이 없거나 선택 공유본에 Run이 미등록, 또는 해당 Run에 등록된 ref 없음 |
| 422 | `INTEGRITY/INTEGRITY_FAILED` | INVALID/검증 불가 Run, 등록 파일 부재, 크기/해시 불일치 |
| 422 | `INTEGRITY/PNG_CONTENT_INVALID` | 상한 초과 또는 PNG signature 불일치 |
| 421 | `CONTRACT/HOST_NOT_ALLOWED` | 허용 Host 불일치, 기존 dispatch와 동일 |
| 500 | `UNEXPECTED/UNEXPECTED` | 기타 오류, 내부 경로·비밀값 미노출 |

여러 실패가 있으면 위 §3의 검사 순서를 따른다. 시작 검증 실패는 HTTP 422가 아니라 서버 시작 거부다.
다른 root/공유본에만 존재하는 Run은 선택 범위에서 없는 Run이므로 404다(IMG-20).
이를 찾기 위해 다른 디렉터리를 검색하지 않으며, 등록 Run·ref를 확인한 뒤의 PNG 허용 정책 실패인 403과 구분한다.
등록 파일 부재는 실행을 NOT_RUN으로 바꾸지 않고 원본을 제공하지 못하는 무결성 문제로 표시한다.
정상 PNG 헤더가 아닌 오류 응답은 기존 HTML 오류 계약을 사용한다(HTTP 상태는 유지).

## 5. 시험과 단계의 경계

[사례 JSON](http-cases.json)의 IMG 항목은 후속 구현에 연결할 입력·expected status·assertion 목록이다.
현재 0·1단계에는 endpoint를 구현하거나 PNG 실제 열람 시험을 통과했다고 표시하지 않는다.
fixture는 별도 임시 디렉터리에 만들고 652개 봉인 원본을 변조해서 시험하지 않는다.
정상 N-01 PC/모바일 각 1건, 부모·child 다른 캡처, 실제 공유본 밖 root, LOCAL/DEMO 미승인, 변조/링크/경로/
잘못된 MIME·signature·크기·cache 이후 변조를 모두 시험한다. 기존 text evidence 회귀도 함께 유지한다.
