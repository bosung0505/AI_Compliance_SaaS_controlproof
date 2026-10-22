"""Informational context is on demand; result-critical state remains in the content."""
from __future__ import annotations

from html.parser import HTMLParser

import pytest

from tests.contract.test_platform_delivery import shared, request, N01
from tests.contract.test_platform_public_pages import site, page, Markup


class InfoText(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.depth = 0
        self.inside, self.outside = [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details' and (self.depth or attrs.get('data-testid') == 'verification-info'):
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == 'details' and self.depth:
            self.depth -= 1

    def handle_data(self, text):
        (self.inside if self.depth else self.outside).append(text)


@pytest.mark.parametrize('path', ['/', '/results', '/prepare', '/report', '/scenarios/N-03', f'/runs/{N01}'])
def test_shared_context_is_in_one_closed_accessible_info_panel(shared, path):
    html, _ = request(shared, path)
    panels = [attrs for tag, attrs in Markup(html).tags if tag == 'details' and attrs.get('data-testid') == 'verification-info']
    assert len(panels) == 1 and 'open' not in panels[0]
    text = InfoText(html)
    inside, outside = ' '.join(text.inside), ' '.join(text.outside)
    assert '검증 정보' in inside and 'PASS 비율이나 법적 준수율을 뜻하지 않습니다.' in inside
    assert '팀과 함께 보는 실제 기록' in inside and '팀과 함께 보는 실제 기록' not in outside
    assert shared.readers['ACTUAL'].shared_snapshot['snapshot_digest'] in inside
    assert '실제 AWS' in inside and 'LOCAL_EMULATED' in inside
    assert 'class="shared-record-context"' not in html


def test_overview_preserves_scope_and_moves_only_informational_notes(shared):
    html, _ = request(shared, '/')
    outside = ' '.join(InfoText(html).outside)
    assert 'coverage-footnote' not in html and 'overview-disclaimer' not in html
    assert '법적 준수율' not in outside and '새 독립 실행' not in outside
    assert '일부 범위 1개' in outside and 'N-03은 일부 조건만 실행했습니다.' in outside
    assert '대상 기능 미제공' in outside
    for treatment, count in [('EXECUTED', 9), ('NOT_RUN', 0), ('NO_TEST_TARGET', 3)]:
        assert f'data-coverage="{treatment}">{count}</strong>' in html


@pytest.mark.parametrize('path', ['/', '/demo/'])
def test_local_and_demo_do_not_claim_shared_context(site, path):
    html = page(site, path)
    tags = Markup(html).tags
    assert any(attrs.get('data-testid') == 'verification-info' for _, attrs in tags)
    assert '팀과 함께 보는 실제 기록' not in html
    assert ('class="demo-banner"' in html) == path.startswith('/demo')
    if path.startswith('/demo'):
        assert '합성 데이터로 만든 화면' in ' '.join(InfoText(html).outside)
