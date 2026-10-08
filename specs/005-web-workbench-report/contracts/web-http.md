# Contract: 로컬 웹 HTTP 경계

실행: `python -m engine.web [--port 8765] [--run-root <경로>] [--demo-root <경로>] [--target whyyou-local]`. `127.0.0.1`에만 연결하며 다른 주소
옵션은 없다. run root 우선순위는 `--run-root` > `CONTROLPROOF_RUN_ROOT` > `.controlproof/runs`.

## 요청 규칙

- `Host`가 `127.0.0.1:<port>` 또는 `localhost:<port>`가 아니면 `421`과 오류 JSON.
- 상태를 바꾸는 요청은 POST만. 폼의 `csrf_token`이 서버 기동 때 만든 값과 다르면 `403`.
- 모든 응답 헤더: `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'`, `X-Content-Type-Options: nosniff`,
  `Cache-Control: no-store`, `Referrer-Policy: no-referrer`.
- 모든 응답 바이트는 출력 경계 redaction을 거친다(SC-007).

## 경로

| 메서드 | 경로 | 응답 |
|---|---|---|
| GET | `/` | 워크벤치 HTML (`view=workbench`) |
| GET | `/scenarios/{id}` | 시나리오 상세 HTML |
| GET | `/runs/{run_id}` | 실행 결과·증적 HTML |
| GET | `/runs/{run_id}/evidence?ref={ref}` | 증적 원본 보기(텍스트·256 KB 이하·경계 검사 통과분만, 아니면 사유) |
| GET | `/compare/{child_run_id}` | 재시험 비교 HTML |
| GET | `/report` | 결과 보고서 HTML |
| GET | `/demo/...` | 위 경로의 DEMO root 버전(항상 DEMO 띠) |
| GET | `/api/{view}` · `/api/runs/{run_id}` · `/api/compare/{id}` · `/api/scenarios/{id}` | 같은 뷰의 JSON([web-read-model.md](./web-read-model.md)) |
| POST | `/preflight` | 폼 `scenario_id`, `execution_profile`, `csrf_token` → 준비 상태 확인 1건 실행 뒤 상세로 303 |
| POST | `/runs/{run_id}/memos` | 폼 `author`, `text`, `csrf_token` → 메모 추가 뒤 303 |
| GET | `/static/*` | CSS·JS(같은 출처) |

Run·재시험·정리 확인을 시작하는 경로는 없다(D-018, SC-010). 준비 상태 확인이 진행 중이면 두 번째 POST는 `409`.

## 오류 응답

```json
{"schema_version": "controlproof.web.v1", "view": "error", "error_kind": "NOT_FOUND", "code": "RUN_NOT_FOUND", "detail": "요청한 실행 기록이 없습니다."}
```

| HTTP | `error_kind` | 예 |
|---|---|---|
| 400 | `USAGE` | 알 수 없는 시나리오·프로필, 메모 길이 초과 |
| 403 | `CONTRACT` | 토큰 불일치 |
| 404 | `NOT_FOUND` | 없는 Run·증적 참조 |
| 409 | `BUSY` | 준비 상태 확인 진행 중 |
| 421 | `CONTRACT` | Host 불일치 |
| 422 | `INTEGRITY` | 무결성 실패 기록의 증적 원본 요청 |
| 500 | `UNEXPECTED` | 처리 중 예외(내부 정보·경로 없이) |

HTML 요청이면 같은 내용을 오류 화면으로 그린다. 무결성 실패 Run의 `/runs/{id}`는 오류가 아니라 200과 무결성 실패 화면이다.
