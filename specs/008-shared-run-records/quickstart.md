# Spec008 Quickstart

팀원용 실행은 [공유 기록 README](../../review-data/README.md)를 따른다.

```powershell
& .\.venv\Scripts\python.exe -m scripts.share_records --verify
& .\.venv\Scripts\python.exe -m engine.web --shared-snapshot review-data/snapshot.json --port 8766
```

공유본을 만드는 담당자는 실제 기록 root를 명시한다. `--run-root`는 카탈로그 참조만 선택하며 추가 보존·복구한
원본은 `--bundle <Run폴더>`로 지정한다. 중복 ID의 다른 내용은 거부한다. 새 목적지만 허용한다.

```text
python -m scripts.share_records --run-root <actual-root> --run-root <legacy-actual-root>
  --bundle <recovered-E01> --bundle <recovered-E02> --bundle <extra-N02-1> --bundle <extra-N02-2>
  --reviewed-png <visually-reviewed-sha256> --reviewed-png <visually-reviewed-sha256>
  --preserve-invalid ce5f2750-5b31-48e8-aca5-f1d85d440ca3 --out <new-snapshot-directory>
```

위는 설명용 인자 목록이며 개인 경로를 고정한 실행 명령이 아니다. 이번 원본 선택·검사·결과는 validation에 기록한다.
`--preserve-invalid`는 기존 INVALID 보존을 명시할 뿐 판정을 바꾸지 않는다. 민감정보/미등록 파일 검사는 그대로 적용된다.
공유본을 새 테스트의 실행 root로 사용하지 않는다. 기존 `.controlproof/`/`cp-local`은 백업 원본으로 계속 보존한다.
