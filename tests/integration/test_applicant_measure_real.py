"""Real-Chromium negative controls for the N-01 notice measurement (measure_fragments + MEASURE_JS, measurement v2).

A static page with the WhyYou consent-step structure is measured at PC 1440x900 and mobile 390x844. Each case hides
or damages one notice fragment; the four flags the current code reports are pinned. Cases the measurement does not
catch (every flag still true although the text cannot be read) are strict xfail: they document a gap, not a fix.
"""

from __future__ import annotations

import html

import pytest

from engine.adapters.whyyou.applicant_browser import measure_fragments
from engine.n01 import FLAGS_V2, VIEWPORTS, N01LaneId, expected_fragments

POLICY = {
    "policy_version": "2026-08-v1",
    "ai_role": "AI는 지원자 자료를 바탕으로 질문과 평가 초안을 만들지만 최종 채용 결정은 기업의 사람이 수행합니다.",
    "recording_notice": "면접 중 음성과 영상이 녹화되며 답변 자막과 Evidence 재생 구간을 만드는 데 사용됩니다.",
    "processing_purposes": [
        {"purpose": "document_analysis", "title": "문서 분석", "description": "제출한 이력서와 공개 저장소를 질문 준비와 사실 확인에 사용합니다."},
        {"purpose": "recording", "title": "면접 녹화", "description": "면접 영상과 음성을 자막, 복구, 사람 검토를 위해 저장합니다."},
        {"purpose": "ai_assessment", "title": "AI 평가 보조", "description": "최종 답변 근거로 평가 초안을 만들며 기술 장애 구간은 평가에서 제외합니다."},
    ],
    "retention_days": 180,
    "deletion_method": "기업의 삭제 요청 또는 보관기간 만료 시 PostgreSQL, S3, 검색 인덱스의 원본과 파생 데이터를 확인하며 삭제합니다.",
    "required_purposes": ["ai_assessment", "document_analysis", "recording"],
    "content_digest": "a" * 64,
}
LONG_DELETION = "삭제방법" * 60
BASE_CSS = """
body { margin: 0; font: 16px/1.5 sans-serif; }
main { max-width: 760px; margin: 0 auto; padding: 24px 16px; }
.policy { background: #eef; padding: 16px; border-radius: 8px; }
dl div { display: flex; gap: 12px; } dt { flex: 0 0 76px; } dd { margin: 0; }
label { display: flex; gap: 8px; padding: 12px; border: 1px solid #ccc; }
strong, small { display: block; }
"""


def build_page(case: str) -> str:
    """WhyYou consent-step shaped page; ``case`` applies one damage (``base`` = none)."""
    p = {key: html.escape(str(value)) for key, value in POLICY.items() if isinstance(value, (str, int))}
    css = BASE_CSS
    ai_role = f'<p id="ai-role">{p["ai_role"]}</p>'
    recording = f'<p id="recording">{p["recording_notice"]}</p>'
    retention_dd = '<dd id="retention">180일</dd>'
    deletion_dd = f'<dd id="deletion">{p["deletion_method"]}</dd>'
    overlay = ""
    if case == "overlay_retention":
        overlay = '<div id="cover" style="position:fixed;background:#000;z-index:10"></div>'
    elif case == "nowrap_deletion":
        deletion_dd = f'<dd id="deletion" style="white-space:nowrap">{p["deletion_method"]}{LONG_DELETION}</dd>'
    elif case == "offscreen_ai_role":
        ai_role = f'<p id="ai-role" style="position:absolute;left:-3000px">{p["ai_role"]}</p>'
    elif case == "hidden_deletion":
        deletion_dd = f'<dd id="deletion" style="visibility:hidden">{p["deletion_method"]}</dd>'
    elif case == "transparent_recording":
        recording = f'<p id="recording" style="opacity:0">{p["recording_notice"]}</p>'
    elif case == "clipped_recording":
        recording = f'<div style="height:1.2em;overflow:hidden"><p id="recording">{p["recording_notice"]}</p></div>'
    elif case == "line_clamp_recording":
        recording = (
            '<p id="recording" style="display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:1;'
            f'overflow:hidden">{p["recording_notice"]}</p>'
        )
    elif case == "missing_ai_role":
        ai_role = ""
    purposes = "".join(
        f'<label><input type="checkbox"><span><strong>{html.escape(item["title"])}</strong>'
        f'<small>{html.escape(item["description"])}</small></span></label>'
        for item in POLICY["processing_purposes"]
    )
    return (
        f"<!doctype html><html lang=ko><head><meta charset=utf-8><style>{css}</style></head><body><main>"
        '<section aria-label="동의 정책"><div class="policy">'
        f'{ai_role}{recording}<dl><div><dt>보관기간</dt>{retention_dd}</div><div><dt>삭제 방법</dt>{deletion_dd}</div></dl>'
        f"</div>{purposes}<button disabled>동의하고 계속</button></section></main>{overlay}</body></html>"
    )


COVER_JS = """
() => {
  const rect = document.getElementById("retention").getBoundingClientRect();
  const cover = document.getElementById("cover");
  Object.assign(cover.style, {left: rect.left + "px", top: rect.top + "px", width: rect.width + "px", height: rect.height + "px"});
}
"""


@pytest.fixture(scope="module")
def chromium():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001 - no bundled Chromium installed
            pytest.skip(f"Playwright Chromium unavailable: {type(exc).__name__}")
        yield browser
        browser.close()


def measure(chromium, case: str, lane: N01LaneId) -> dict[str, dict[str, bool]]:
    width, height = VIEWPORTS[lane]
    context = chromium.new_context(viewport={"width": width, "height": height}, locale="ko-KR")
    try:
        page = context.new_page()
        page.set_content(build_page(case))
        if case == "overlay_retention":
            page.evaluate(COVER_JS)
        items, _operations = measure_fragments(page, expected_fragments(POLICY))
    finally:
        context.close()
    return {fragment["fragment_id"]: {flag: fragment[flag] for flag in FLAGS_V2} for item in items for fragment in item["fragments"]}


def false_flags(flags: dict[str, dict[str, bool]]) -> dict[str, list[str]]:
    return {fid: [flag for flag in FLAGS_V2 if not values[flag]] for fid, values in flags.items() if not all(values.values())}


PC, MOBILE = N01LaneId.PC, N01LaneId.MOBILE


ALL_FRAGMENTS = [fid for pairs in expected_fragments(POLICY).values() for fid, _ in pairs]
#: Flags measurement v2 reports false, per case (case 3 overflows the document, so every fragment fails it).
CAUGHT = {
    ("base", PC): {},
    ("base", MOBILE): {},
    ("overlay_retention", PC): {"retention.days": ["not_occluded"]},
    ("nowrap_deletion", MOBILE): {
        **{fid: ["no_horizontal_overflow"] for fid in ALL_FRAGMENTS if fid != "deletion.method"},
        "deletion.method": ["in_viewport", "not_occluded", "no_horizontal_overflow"],
    },
    ("offscreen_ai_role", PC): {"human_final.ai_role": ["in_viewport", "not_occluded"]},
    ("offscreen_ai_role", MOBILE): {"human_final.ai_role": ["in_viewport", "not_occluded"]},
    ("hidden_deletion", PC): {"deletion.method": ["not_occluded", "style_visible"]},
    ("hidden_deletion", MOBILE): {"deletion.method": ["not_occluded", "style_visible"]},
    ("transparent_recording", PC): {"recording_purpose.notice": ["style_visible"]},
    ("transparent_recording", MOBILE): {"recording_purpose.notice": ["style_visible"]},
    ("clipped_recording", MOBILE): {"recording_purpose.notice": ["not_occluded", "not_clipped"]},
    ("line_clamp_recording", MOBILE): {"recording_purpose.notice": ["not_clipped"]},
    ("missing_ai_role", PC): {"human_final.ai_role": list(FLAGS_V2)},
    ("missing_ai_role", MOBILE): {"human_final.ai_role": list(FLAGS_V2)},
}


@pytest.mark.parametrize(("case", "lane"), list(CAUGHT), ids=lambda value: getattr(value, "value", value))
def test_v2_flags_are_pinned(chromium, case, lane) -> None:
    assert false_flags(measure(chromium, case, lane)) == CAUGHT[(case, lane)]


def test_v2_records_clip_ancestor_and_computed_style(chromium) -> None:
    def fragment(case, lane, fragment_id):
        width, height = VIEWPORTS[lane]
        context = chromium.new_context(viewport={"width": width, "height": height}, locale="ko-KR")
        try:
            page = context.new_page()
            page.set_content(build_page(case))
            items, _ = measure_fragments(page, expected_fragments(POLICY))
        finally:
            context.close()
        return next(f for item in items for f in item["fragments"] if f["fragment_id"] == fragment_id)

    clipped = fragment("clipped_recording", MOBILE, "recording_purpose.notice")
    assert clipped["clip_ancestor"] == "div"
    transparent = fragment("transparent_recording", PC, "recording_purpose.notice")
    assert transparent["computed_opacity"] == 0 and transparent["computed_visibility"] == "visible"
    hidden = fragment("hidden_deletion", PC, "deletion.method")
    assert hidden["computed_visibility"] == "hidden"
    base = fragment("base", PC, "recording_purpose.notice")
    assert base["clip_ancestor"] is None and base["computed_opacity"] == 1
