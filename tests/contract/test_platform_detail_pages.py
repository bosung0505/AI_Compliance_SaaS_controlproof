"""Real handler/template/PNG response boundaries on immutable reviewed actual records."""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

from engine.web import server
from tests.contract.test_platform_public_pages import Markup

ROOT=Path(__file__).parents[2]
N01='d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18'
N03='f27b68e8-0df8-46b3-a198-c7917c2f08bb'


@pytest.fixture(scope='module')
def site(tmp_path_factory):
    source=json.loads((ROOT/'review-data/snapshot.json').read_text(encoding='utf-8'))
    state=tmp_path_factory.mktemp('stage4-pages')
    instance=server.make_server(0,run_root=ROOT/'review-data/bundles',demo_root=state/'demo/runs',state_dir=state/'state',shared_snapshot=source)
    yield instance
    instance.server_close()


class Capture(server._Handler):
    def __init__(self,site,path,*,host=None,method='GET',extra_headers=None):
        self.server,self.path,self.command=site,path,method
        self.headers={'Host':host or f'127.0.0.1:{site.server_address[1]}','Content-Length':'0',**(extra_headers or {})}
        self.rfile=io.BytesIO(); self.wfile=io.BytesIO(); self.headers_out={}

    def send_response(self,status):
        self.status=int(status)

    def send_header(self,name,value):
        self.headers_out[name]=value

    def end_headers(self):
        pass

    def _send(self,status,body,content_type):
        self.status=int(status);self.headers_out.update({'Content-Type':content_type,**server.SECURITY_HEADERS})
        self.wfile.write(body)


def request(site,path,expected=200,**kwargs):
    handler=Capture(site,path,**kwargs)
    handler._dispatch(handler.command)
    body=handler.wfile.getvalue()
    assert handler.status==expected,(path,handler.status,body[:100])
    return body,handler.headers_out


@pytest.mark.parametrize('scenario_id',['N-01','N-02','N-03','H-01','H-02','H-03','E-01','E-02','E-03','A-01','A-02','A-03'])
def test_scenario_service_keeps_profiles_history_and_security(site,scenario_id):
    body=request(site,f'/scenarios/{scenario_id}')[0].decode()
    assert 'service-detail' in body and 'href="/results"' in body
    assert '[REDACTED]' not in body
    tags=Markup(body).tags
    assert not any('style' in attrs or any(k.startswith('on') for k in attrs) for tag,attrs in tags)
    assert not any(tag=='form' for tag,attrs in tags)
    if scenario_id.startswith('A'):
        assert 'NO_TEST_TARGET' in body and 'data-badge="pass"' not in body
        assert 'role="progressbar"' not in body
    else:
        assert 'id="runs"' in body and 'SHA-256' in body
    if scenario_id=='N-02':
        assert '7b59237e-0a96-403a-9add-28b91011e950' in body and '원본 미확보' in body


def test_selected_runs_scope_and_condition_cards(site):
    body=request(site,f'/runs/{N03}')[0].decode()
    assert 'service-observation' in body and '일부 범위' in body and 'N03-U1' in body
    assert 'N03-L1' in body and 'sealed_snapshot' in body and 'data-run-picker' in body
    parent=request(site,'/runs/48a70f5e-aa62-41fc-bf58-3624a6102b4f')[0].decode()
    child=request(site,f'/runs/{N01}')[0].decode()
    assert '측정 v1' in parent and '원본 버전 필드는 없습니다' in parent
    assert '측정 v2' in child and '이미지 허용 목록이 없어' not in child
    assert f'/runs/{N01}/evidence/content?' in child
    entry=next(e for e in site.catalog['scenarios'] if e['id']=='E-01')
    run_id=next(r['run_id'] for r in entry['official_status']['records'] if r['role']=='repeat')
    data=site.readers['ACTUAL'].run(run_id)
    assert data['review']['rule_count']==4 and len(data['review']['conditions'])==7
    assert not any('D1' in str(c['facts'].get('mode','')) for c in data['review']['conditions'] if isinstance(c['facts'],dict))
    html=request(site,f'/runs/{run_id}')[0].decode()
    assert '원본 규칙 4개 · 표시 조건 7개' in html and 'data-testid="all-evidence"' in html


@pytest.mark.parametrize('run_id', [
    'c12c2ce8-f607-4be3-9524-0dec27dc7260',
    'dd52deb1-cf07-4268-9547-3db21294514b',
])
def test_result_header_keeps_navigation_below_observations_for_pass_and_fail(site, run_id):
    html = request(site, f'/runs/{run_id}')[0].decode()
    assert html.index('data-testid="plain-explanation"') < html.index('data-testid="condition-review"') < html.index('data-testid="run-navigation"')
    nav = next(attrs for tag, attrs in Markup(html).tags if attrs.get('data-testid') == 'run-navigation')
    assert 'open' not in nav
    assert html.index('data-testid="run-navigation"') < html.index('data-run-picker')
    assert 'href="/scenarios/H-02"' in html and '검토할 실행 기록' in html
    assert 'AI·자동 처리 기능의 채용 결정 변경 가능성 검사</h2>' in html
    assert '원본 기록 변경 없음 확인 (VERIFIED)' in html
    assert '봉인 판정' not in html
    summary = html.split('data-testid="plain-explanation"', 1)[1].split('data-testid="remediation-reason"', 1)[0]
    assert summary.count('<p class="result-') == 2 and '<strong>' in summary
    assert '원본 판정 규칙' not in summary and '누락 증적' not in summary
    details = html.split('data-testid="summary-details"', 1)[1].split('data-testid="run-navigation"', 1)[0]
    assert '원본 판정 규칙 6개' in details and '누락 증적' in details
    if run_id.startswith('c12c2ce8'):
        assert '조회·답변으로 채용 상태가 바뀌지 않았습니다.' in summary
        assert '35점 합격·90점 불합격' in summary
    else:
        assert '조회·답변만으로 채용 상태가 바뀌었습니다.' in summary
        assert '4조건 중 2조건에서 발생' in summary


def test_n02_recovery_capture_is_readable_and_always_open_only_for_a6_a7(site):
    html = request(site, '/runs/16dbd987-23a5-4030-bb62-77787488969b')[0].decode()
    assert 'id="n02-consent-recovery"' in html
    for key in ('N02-A6', 'N02-A7'):
        card = re.search(r'<article[^>]*id="condition-' + key + r'".*?</article>', html, re.DOTALL).group()
        tags = Markup(card).tags
        proof = next(attrs for tag, attrs in tags if attrs.get('id') == 'proof-' + key)
        assert 'hidden' not in proof
        assert not any('data-inspect' in attrs or 'data-close-proof' in attrs for tag, attrs in tags)
        assert '· 연결된 자료' not in card and '실행 기록에서 확인된 값' in card
        assert 'capture-source-details' in card and 'condition-source' in card and '관찰값 원문' in card
        assert 'n02-capture-condition' in card and 'capture-observed' in card
        assert 'expect-observe capture-comparison' in card and 'capture-expected' in card
    card = re.search(r'<article[^>]*id="condition-N02-A5".*?</article>', html, re.DOTALL).group()
    proof = next(attrs for tag, attrs in Markup(card).tags if attrs.get('id') == 'proof-N02-A5')
    assert 'hidden' in proof and 'data-inspect="proof-N02-A5"' in card
    assert 'n02-capture-condition' not in card
    h02 = request(site, '/runs/c12c2ce8-f607-4be3-9524-0dec27dc7260')[0].decode()
    assert 'n02-capture-condition' not in h02 and 'data-inspect="proof-H02-A3"' in h02


def test_png_response_bytes_headers_range_and_strict_query(site):
    path=f'/runs/{N01}/evidence/content?ref=file%3An01-pc-capture.png'
    body,headers=request(site,path,extra_headers={'Range':'bytes=0-3'})
    assert body==(ROOT/f'review-data/bundles/{N01}/n01-pc-capture.png').read_bytes()
    assert headers['Content-Type']=='image/png' and int(headers['Content-Length'])==len(body)
    assert headers['Content-Disposition']=='inline; filename="controlproof-evidence.png"'
    assert all(headers[k]==v for k,v in server.SECURITY_HEADERS.items())
    request(site,path,expected=421,host='invalid.example')
    assert b'EVIDENCE_REF_INVALID' in request(site,path+'&ref=x',expected=400)[0]
    request(site,f'/demo/runs/{N01}/evidence/content?ref=file%3An01-pc-capture.png',expected=404)
    page=request(site,f'/runs/{N01}/evidence?ref=file%3An01-pc-capture.png')[0].decode()
    assert '<img src=' in page and 'data-testid="evidence-sha256"' in page


def test_invalid_missing_and_shared_post_are_not_hidden(site):
    invalid=next(r['run_id'] for r in site.readers['ACTUAL'].shared_snapshot['records'] if r['verification']['bundle_status']=='INVALID')
    body=request(site,f'/runs/{invalid}')[0].decode()
    assert '무결성' in body and 'data-testid="condition-review"' not in body
    assert 'service-observation"' not in body and 'data-badge="pass"' not in body
    request(site,'/runs/00000000-0000-0000-0000-000000000000',expected=404)
    request(site,'/scenarios/N-99',expected=404)
    assert b'SHARED_READ_ONLY' in request(site,f'/runs/{N01}/memos',expected=403,method='POST')[0]
