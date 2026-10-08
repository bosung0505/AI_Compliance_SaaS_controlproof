"""T022 — badge table equals the 15 rows of spec "승인된 화면 구조와 상태 이름" (FR-005, SC-006, R-016). RED until T028."""

from __future__ import annotations

import re
from pathlib import Path

from engine.web import badges

SPEC = Path("specs/005-web-workbench-report/spec.md")


def _spec_rows():
    text = SPEC.read_text(encoding="utf-8")
    table = text[text.index("| 분류 | 이름 | 아이콘 | 모양 | 설명 |"):]
    rows = []
    for line in table.splitlines()[2:]:
        if not line.startswith("|"):
            break
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def _shape(text: str) -> str:
    if "채운" in text:
        return "filled"
    if "각진" in text:
        return "square"
    return "round"


def _labels(name: str) -> tuple[str, str | None]:
    match = re.search(r"`([A-Z_]+)`", name)
    english = match.group(1) if match else None
    korean = re.sub(r"`[A-Z_]+`", "", name).strip()
    return korean or english, english


def test_exactly_the_fifteen_spec_rows() -> None:
    rows = _spec_rows()
    assert len(rows) == 15
    assert len(badges.BADGES) == 15
    table = list(badges.BADGES.values())
    for (category, name, icon, shape, description), badge in zip(rows, table, strict=True):
        korean, english = _labels(name)
        assert badge.category == category
        assert (badge.label_ko, badge.label_en) == (korean, english), badge.key
        assert badge.icon == ("" if icon == "(제목)" else icon), badge.key
        assert badge.shape == _shape(shape), badge.key
        assert badge.description == description, badge.key


def test_shape_families() -> None:
    by_category = {}
    for badge in badges.BADGES.values():
        by_category.setdefault(badge.category, set()).add(badge.shape)
    assert by_category["판정"] == {"round"}
    assert by_category["준비 상태"] == {"square"}
    assert by_category["실행 안전"] == {"filled"}


def test_lookups_use_the_table() -> None:
    assert badges.result_badge("PASS", None).key == "pass"
    assert badges.result_badge("NOT_RUN", None).key == "not_run"
    assert badges.result_badge("INCONCLUSIVE", "NO_TEST_TARGET").key == "reason_no_test_target"
    assert badges.result_badge("INCONCLUSIVE", "INSUFFICIENT_EVIDENCE").key == "insufficient_evidence"
    assert badges.readiness_badge("RUNNER_NOT_READY").key == "runner_not_ready"
    assert badges.readiness_badge("NO_TEST_TARGET").key == "readiness_no_test_target"
    ntt, rnr = badges.BADGES["readiness_no_test_target"], badges.BADGES["runner_not_ready"]
    assert (ntt.label_en, ntt.icon, ntt.tone) != (rnr.label_en, rnr.icon, rnr.tone)
    reason = badges.BADGES["reason_no_test_target"]
    assert (reason.icon, reason.shape, reason.tone) == (ntt.icon, ntt.shape, ntt.tone)
