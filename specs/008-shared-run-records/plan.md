# Spec008 Plan

구현 전 2026-10-19 확정. Constitution I/II/V/VI/VII 준수: 판정 재계산 없음, 합성 원본/과거 실패 보존,
실행 안전 상태를 공유하지 않음, 새 actual 실행 없음. 저장소/엔진 기본 root는 공유 웹 모드에만 변경하며 CLI Run은 그대로다.

1. `engine/shared_records.py`: 경로·파일 허용 목록, SHA 목록, strict scan, snapshot 구성/검증. 기존 verify 결과 중 시각을 제외한 상태 고정.
   snapshot digest는 digest 필드를 제외한 canonical JSON 해시. 표시 원천은 engine/catalog/scenarios 파일 해시로 고정.
   snapshot 목록/파일은 실행하지 않고 기존 엔진에서 판독. 주어진 루트 안의 정규 파일만 허용한다.
2. `scripts/share_records.py`: 명시한 실제 root와 복구한 두 원본 경로에서 목록 구성. 같은 ID는 모든 파일 해시가 같을 때만 중복 제거.
   원본을 읽기만 하며 새 빈 목적지에만 생성. 기존 snapshot 덮어쓰기 금지. 발견한 비공식 중단 기록도 포함.
3. 웹 진입점/서버/reader: 공유 snapshot 선택·시작 전 검증, 원본 root만 주입, 준비 기록과 memo store를 생성하지 않는 공유 모드.
   header의 generated_at은 snapshot 시각 고정, 대상 맥락은 보관된 target snapshot에서 선택. POST 차단과 공통 안내.
4. 기존 템플릿의 공통 구성 유지. 공유 묶음 안내, 부재 이력, 로컬 준비/메모 쓰기 대신 읽기 안내만 변경.
5. 무결성 실패/원래 INVALID/경로·중복 실패/실제 화면·별도 checkout 동등성 검증. 전체 sealed 원본 보존 감사.

공유 파일 범위: manifest에 등록된 텍스트와 manifest 자체, 검토 PNG 2개. 미등록 파일은 허용하지 않는다.
정비 기록 등 외부 참조는 원본 판독에 필요한지 조사하고 필요한 경우 별도 해시된 supporting 파일로 추가한다.
archive는 만들지 않고 Git 원본 파일+snapshot 해시로 전달한다. 용량 현재 약 3MB 규모로 LFS/별도 DB 불필요.
