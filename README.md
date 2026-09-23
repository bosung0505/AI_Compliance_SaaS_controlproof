# ControlProof

AI 기본법 절차적 통제 4종이 실제로 작동하는지 시험하고 증적을 남기는 도구.
첫 검증 대상은 WhyYou (AI 면접 서비스).

## 시작

```bash
pip install -e ".[dev]"
pytest
python -m engine.scenario   # 시나리오 로드 확인
```

## 문서

- `CLAUDE.md` — 절대 규칙과 아키텍처 계약. 먼저 읽을 것
- `docs/기능범위_v4.md` — 제품 범위와 완료 기준
- `docs/아키텍처.md` — 다이어그램으로 보는 설계
- `docs/시나리오-명세-가이드.md` — 시나리오 작성법
- `scenarios/_TEMPLATE.yaml` — 명세 템플릿

## 현재 상태

- [x] 증적 스키마 (`engine/models.py`)
- [x] 관찰값 키 사전 (`engine/observations.py`)
- [x] 판정 엔진 4규칙 (`engine/judge.py`)
- [x] 시나리오 로더·검증 (`engine/scenario.py`)
- [x] H-03 명세
- [x] 상태 시드 (`seeds/state_seed.py`)
- [ ] 경로 시드
- [ ] 어댑터 (api / log / fault)
- [ ] 장애 주입 훅 (WhyYou 테스트 전용)
- [ ] 증적 저장·보고서
- [ ] 나머지 8개 시나리오 명세
