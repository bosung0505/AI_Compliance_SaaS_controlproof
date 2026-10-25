"""Spec010 display projections and URL filters. Never computes or rewrites a verdict."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode

from engine.web.result_copy import display_title

CONTROLS = {
    "N": {"title": "AI 사용 사전 고지", "purpose": "AI 사용을 알리고, 지원자가 확인한 정책과 동의 기록이 일치하는지 살펴봅니다."},
    "H": {"title": "인간 개입 · 안전한 예외처리", "purpose": "AI가 최종 결정을 대신하지 않고, 권한 있는 사람이 판단하고 개입할 수 있는지 확인합니다."},
    "A": {"title": "이용자 보호 · 이의처리", "purpose": "결과에 이의를 제기하고, 사람의 재검토와 후속 조치를 요청할 수 있는지 확인합니다."},
    "E": {"title": "증적 기록의 완전성", "purpose": "AI 평가가 정해진 기준과 근거에 연결되고, 잘못된 결과가 차단되는지 확인합니다."},
}
TREATMENTS = ("EXECUTED", "NOT_RUN", "NO_TEST_TARGET")
TREATMENT_LABELS = {"EXECUTED": "로컬 테스트 실행", "NOT_RUN": "아직 테스트하지 않은 항목", "NO_TEST_TARGET": "대상 기능이 없는 항목"}


def current_scope(scenario_id: str, definition: dict) -> dict:
    if scenario_id == "N-03" and not definition.get("unverified_scope_items"):
        raise ValueError("CURRENT_SCOPE_UNAVAILABLE")
    return {
        "source": "scenario_file" if definition else None,
        "source_ref": f"scenarios/{scenario_id}.yaml" if definition else None,
        "version": definition.get("version"),
        "partial": scenario_id == "N-03" and bool(definition.get("unverified_scope_items")),
        "applicable_assertion_ids": definition.get("applicable_assertion_ids", []),
        "target_access": definition.get("target_access", []),
        "unverified_items": [{k: item.get(k) for k in ("id", "text", "follow_up")} for item in definition.get("unverified_scope_items", [])],
        "limitations": [{k: item.get(k) for k in ("id", "text")} for item in definition.get("limitations", [])],
    }


def coverage(rows: list[dict]) -> dict:
    counts = dict.fromkeys(TREATMENTS, 0)
    for row in rows:
        treatment = row["mvp_treatment"]
        if treatment not in counts or (row["target_exists"] is False) != (treatment == "NO_TEST_TARGET"):
            raise ValueError("TARGET_TREATMENT_CONFLICT")
        counts[treatment] += 1
    return {
        "total": len(rows), "counts": counts,
        "partial_count": sum(bool(row["ui"]["current_scope"]["partial"]) for row in rows),
        "segments": [{"treatment": key, "count": value, "draw": value > 0} for key, value in counts.items()],
    }


def projection(groups: list[dict]) -> dict:
    ordered = []
    for control, description in CONTROLS.items():
        group = next((g for g in groups if g["control"] == control), None)
        if group is None:
            continue
        rows = sorted(group["scenarios"], key=lambda row: int(row["id"].split("-")[1]))
        counts = coverage(rows)
        targeted = [r for r in rows if r["target_exists"]]
        ordered.append({
            **group, **description, "scenarios": rows,
            "ui": {"coverage": {
                "counts": counts["counts"], "partial_count": counts["partial_count"],
                "targeted_progress": ({"executed": sum(r["mvp_treatment"] == "EXECUTED" for r in targeted), "targeted": len(targeted)} if targeted else None),
            }},
        })
    return {"coverage": coverage([r for g in ordered for r in g["scenarios"]]), "groups": ordered}


def chart(coverage_view: dict) -> dict:
    """SVG presentation attributes only; the same counts drive chart, legend and accessible text."""
    offset = 0.0
    segments = []
    total = coverage_view["total"]
    for segment in coverage_view["segments"]:
        length = 100 * segment["count"] / total if total else 0
        segments.append({**segment, "dash": f"{length:.5f} {100-length:.5f}", "offset": f"{-offset:.5f}"})
        offset += length
    label = " · ".join(f"{TREATMENT_LABELS[k]} {v}개" for k, v in coverage_view["counts"].items())
    return {"segments": segments, "label": f"관리 항목 {total}개. {label}", "labels": TREATMENT_LABELS}


class FilterInvalid(ValueError):
    pass


def parse_filters(query: str) -> dict:
    if re.search(r"%(?![0-9a-fA-F]{2})", query):
        raise FilterInvalid
    try:
        pairs = parse_qsl(query, keep_blank_values=True, encoding="utf-8", errors="strict")
    except (UnicodeError, ValueError) as exc:
        raise FilterInvalid from exc
    values = {"q": "", "control": "", "status": "ALL", "treatment": "ALL"}
    seen = set()
    for key, value in pairs:
        if key not in values or key in seen or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise FilterInvalid
        seen.add(key)
        values[key] = value or values[key]
    values["q"] = values["q"].strip()
    if (len(values["q"]) > 200 or values["control"] not in ("", *CONTROLS)
            or values["status"] not in ("ALL", "PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN")
            or values["treatment"] not in ("ALL", *TREATMENTS)):
        raise FilterInvalid
    canonical = [(k, v) for k, v in values.items() if v and not (k in ("status", "treatment") and v == "ALL")]
    return {**values, "query": urlencode(canonical)}


def filter_groups(groups: list[dict], filters: dict) -> list[dict]:
    result = []
    for group in groups:
        if filters["control"] and group["control"] != filters["control"]:
            continue
        rows = []
        for row in group["scenarios"]:
            text = " ".join([
                *(str(row.get(k) or "") for k in ("id", "title", "question", "description")),
                display_title(row.get("title") or ""),
            ]).casefold()
            if filters["q"].casefold() not in text:
                continue
            if filters["status"] != "ALL" and row["official"]["result"] != filters["status"]:
                continue
            if filters["treatment"] != "ALL" and row["mvp_treatment"] != filters["treatment"]:
                continue
            rows.append(row)
        result.append({**group, "scenarios": rows})
    return result
