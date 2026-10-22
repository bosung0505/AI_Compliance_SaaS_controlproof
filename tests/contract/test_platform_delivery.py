"""Stage5: actual child comparisons, complete report contents and local-only preparation."""
from __future__ import annotations

import copy
import io
import json
import re
from pathlib import Path
from urllib.parse import urlencode

import pytest

from engine.web import delivery, server
from engine.web.readmodel import WorkbenchReader, load_catalog
from engine.web.preflight import ReadinessStore
from tests.contract.test_platform_detail_pages import Capture
from tests.contract.test_platform_public_pages import Markup
from tests.fixtures import web_bundles as wb

ROOT = Path(__file__).parents[2]
N01 = 'd3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18'
H02 = 'c12c2ce8-f607-4be3-9524-0dec27dc7260'
ITEMS = {f'R{i}' for i in range(1, 14)} | {f'C{i}' for i in range(1, 10)}


@pytest.fixture(scope='module')
def shared(tmp_path_factory):
    state = tmp_path_factory.mktemp('stage5')
    snapshot = json.loads((ROOT/'review-data/snapshot.json').read_text(encoding='utf-8'))
    site = server.make_server(0, run_root=ROOT/'review-data/bundles', demo_root=state/'demo/runs', state_dir=state/'state', shared_snapshot=snapshot)
    yield site
    site.server_close()


def request(site, path, status=200, method='GET', data=None, host=None):
    handler = Capture(site, path, method=method, host=host)
    body = urlencode(data or {}).encode()
    handler.rfile = io.BytesIO(body)
    handler.headers['Content-Length'] = str(len(body))
    handler._dispatch(method)
    content = handler.wfile.getvalue().decode()
    assert handler.status == status, (path, handler.status, content[:200])
    return content, handler.headers_out


def test_n01_compare_is_measurement_improvement_not_target_fix(shared):
    view = shared.readers['ACTUAL'].compare(N01)
    assert view['ui']['comparison_available'] is True
    assert view['ui']['cause']['kind'] == 'CONTROLPROOF_MEASUREMENT'
    assert view['ui']['cause']['source'] and 'WhyYou' in view['ui']['cause']['text']
    assert view['parent']['verdict'] == view['child']['verdict'] == 'PASS'
    assert view['ui']['measurement_versions'] == {'parent': 1, 'child': 2}
    assert view['ui']['scopes']['parent']['source'] == 'sealed_snapshot'
    assert view['ui']['scopes']['child']['run_id'] == N01


def test_h02_compare_keeps_reviewed_development_provenance(shared):
    view = shared.readers['ACTUAL'].compare(H02)
    assert view['ui']['cause']['kind'] == 'WHYYOU_DEVELOPMENT'
    assert view['remediation'] and view['ui']['comparison_available']
    assert view['parent']['verdict'] == 'FAIL' and view['child']['verdict'] == 'PASS'


def test_all_actual_child_ids_have_complete_evidence_links(shared):
    reader = shared.readers['ACTUAL']
    children = [r for r in reader.shared_snapshot['records'] if r.get('parent_run_id')]
    assert len(children) >= 6
    for row in children:
        view = reader.compare(row['run_id'])
        assert view['child']['run_id'] == row['run_id']
        if view['ui']['comparison_available']:
            assert view['ui']['assertions']
            for item in view['ui']['assertions']:
                for side in ('before', 'after'):
                    assert all(ev['ref'] and ev['run_id'] for ev in item[side+'_evidence'])


@pytest.mark.parametrize('problem', ['missing', 'invalid', 'digest', 'cycle', 'scenario', 'profile', 'link'])
def test_compare_relationship_errors_block_ui_without_rewriting_api(tmp_path, problem):
    root = tmp_path/'runs'
    parent, child, _ = wb.e01_lineage(root)
    reader = WorkbenchReader(load_catalog(), root, readiness=ReadinessStore(tmp_path/'state'))
    before = reader.run(parent.run_id)
    after = reader.run(child.run_id)
    view = reader.compare(child.run_id)
    if problem == 'missing': before = None
    elif problem == 'invalid': before['integrity']['status'] = 'INVALID'
    elif problem == 'digest': view['lineage_problem'] = {'code':'PARENT_DIGEST_CHANGED','detail':'changed'}
    elif problem == 'cycle': after['run']['parent_run_id'] = child.run_id
    elif problem == 'scenario': before['run']['scenario_id'] = 'E-02'
    elif problem == 'profile': before['run']['execution_profile'] = 'E02_SCORING_FREEZE_V1'
    elif problem == 'link': after['run']['parent_run_id'] = '00000000-0000-0000-0000-000000000000'
    frozen = copy.deepcopy(view)
    ui = delivery.compare_projection(reader, view, before, after)
    assert not ui['comparison_available'] and ui['relationship_problem']
    assert ui['assertions'] == [] and ui['cause']['kind'] == 'UNCONFIRMED'
    assert view == frozen


def test_legacy_digest_unknown_is_not_a_false_error(tmp_path):
    parent, child = wb.h03_lineage(tmp_path/'runs')
    reader = WorkbenchReader(load_catalog(), tmp_path/'runs', readiness=ReadinessStore(tmp_path/'state'))
    view = reader.compare(child.run_id)
    assert view['parent_unchanged'] is None
    assert view['ui']['comparison_available']
    assert view['ui']['cause']['kind'] == 'UNCONFIRMED'


def test_report_additive_actual_inventory_scopes_and_all_22_sections(shared):
    report = shared.readers['ACTUAL'].report()
    assert all(report['items_present'].values()) and set(report['items_present']) == ITEMS
    ui = report['ui']
    assert [g['control'] for g in ui['groups']] == ['N','H','A','E']
    assert ui['coverage']['counts'] == {'EXECUTED':9,'NOT_RUN':0,'NO_TEST_TARGET':3}
    assert len(ui['records']) == 29
    assert sum(r['present'] for r in ui['records']) == 28
    missing = [r for r in ui['records'] if not r['present']]
    assert missing[0]['run_id'] == '7b59237e-0a96-403a-9add-28b91011e950'
    invalid = next(r for r in ui['records'] if r['integrity'] == 'INVALID')
    assert invalid['verdict'] is None and invalid['versions'] is None
    n03 = next(r for r in ui['scenario_scopes'] if r['id'] == 'N-03')
    assert n03['current_scope']['partial'] and len(n03['current_scope']['unverified_items']) == 3
    n01 = next(r for r in ui['records'] if r['run_id'] == N01)
    assert n01['versions']['source'] == 'sealed_bundle'
    assert n01['versions']['target'] and n01['versions']['scenario']['sha256']


def test_demo_report_only_links_its_own_synthetic_records(tmp_path):
    root = tmp_path/'demo'
    _parent, child = wb.e03_lineage(root)
    reader = WorkbenchReader(load_catalog(), root, readiness=ReadinessStore(tmp_path/'state'), origin='DEMO')
    report = reader.report()
    assert all(row['present'] for row in report['ui']['records'])
    assert {r['run_id'] for r in report['ui']['records']} == {p.name for p in root.iterdir() if (p/'run.json').is_file()}
    assert {r['child_run_id'] for r in report['ui']['comparisons']} == {child.run_id}


@pytest.mark.parametrize('path', ['/report', f'/compare/{N01}', f'/compare/{H02}', '/prepare', '/demo/prepare'])
def test_service_pages_are_safe_read_only_and_preserve_scope(shared, path):
    html, headers = request(shared, path)
    assert 'service-delivery' in html
    tags = Markup(html).tags
    assert not any(tag == 'form' for tag, _ in tags)
    assert not any('style' in attrs or any(k.startswith('on') for k in attrs) for _, attrs in tags)
    assert headers['Content-Security-Policy'] == server.SECURITY_HEADERS['Content-Security-Policy']
    if path == '/report':
        assert set(re.findall(r'data-item="([RC]\d+)"',html)) == ITEMS
        assert 'N03-U1' in html and 'N03-L1' in html and '후속 조건' in html
        assert '공유 기록' in html and '이 PC의 기록</th>' not in html
        assert 'data-print-report' in html and 'data-report-section' in html
    if path == '/prepare':
        assert '읽기 전용' in html and 'name="csrf_token"' not in html


def test_preparation_get_does_not_execute_and_local_form_exact_return(tmp_path):
    calls = []
    class Runner:
        def check(self, scenario_id, profile): calls.append((scenario_id, profile))
    site = server.make_server(0, run_root=tmp_path/'runs', demo_root=tmp_path/'demo', state_dir=tmp_path/'state', preflight_runner=Runner())
    try:
        html, _ = request(site, '/prepare')
        assert calls == []
        assert html.count('data-testid="preflight-form"') == 11
        assert 'value="/prepare"' in html and 'name="csrf_token"' in html
        data = {'csrf_token':site.csrf_token,'scenario_id':'N-01','execution_profile':'N01_NOTICE_V1','return_to':'/prepare'}
        _, headers = request(site, '/preflight', status=303, method='POST', data=data)
        assert headers['Location'] == '/prepare#prepare-N-01' and len(calls) == 1
        for wrong in ('//example.com','/demo/prepare','/prepare?x=1','/prepare/','https://example.com'):
            request(site, '/preflight', status=400, method='POST', data={**data,'return_to':wrong})
        request(site, '/preflight', status=403, method='POST', data={**data,'csrf_token':'wrong'})
        assert len(calls) == 1
        demo, _ = request(site, '/demo/prepare')
        assert '<form' not in demo and 'DEMO DATA' in demo
        request(site, '/demo/preflight', status=404, method='POST', data=data)
        request(site, '/prepare', status=421, host='foreign.example')
    finally: site.server_close()


def test_shared_rejects_all_preparation_and_memo_posts(shared):
    for path in ('/preflight','/prepare',f'/runs/{N01}/memos','/demo/preflight'):
        body, _ = request(shared, path, status=403, method='POST')
        assert 'SHARED_READ_ONLY' in body


@pytest.mark.parametrize('state',['ABORTED','RESTORE_FAILED'])
def test_unsafe_execution_blocks_comparison_even_with_sealed_pass(shared,state):
    reader = shared.readers['ACTUAL']
    view = reader.compare(N01)
    before,after = reader.run(view['parent']['run_id']),reader.run(N01)
    after['run']['run_state'] = state
    ui = delivery.compare_projection(reader,view,before,after)
    assert not ui['comparison_available']
    assert ui['relationship_problem']['code'] == 'PAIR_EXECUTION_UNSAFE'
    assert ui['assertions'] == []


@pytest.mark.parametrize('ancestor,code',[('cycle','LINEAGE_CYCLE'),('../escape','LINEAGE_ID_INVALID'),('00000000-0000-0000-0000-000000000000','ANCESTOR_NOT_IN_ROOT')])
def test_ancestor_cycle_bad_id_and_missing_are_explicit(shared,monkeypatch,ancestor,code):
    reader = shared.readers['ACTUAL']
    view = reader.compare(N01)
    before,after = reader.run(view['parent']['run_id']),reader.run(N01)
    original = delivery._json
    def metadata(path,fallback=None):
        doc = original(path,fallback)
        if path.name == 'run.json' and path.parent.name == view['parent']['run_id']:
            return {**doc,'parent_run_id':N01 if ancestor=='cycle' else ancestor}
        return doc
    monkeypatch.setattr(delivery,'_json',metadata)
    ui = delivery.compare_projection(reader,view,before,after)
    assert ui['relationship_problem']['code'] == code and not ui['comparison_available']


def test_report_reproduction_and_print_copy_keep_explicit_scope(shared):
    html,_ = request(shared,'/report')
    assert 'D-019' in html and '277d3f5a-766a-45ab-9f1d-28a3a30a82e6' in html
    assert 'PDF 내보내기는 범위 밖' not in html
    assert '다른 PC 재현 미검증' not in html
    assert '그 밖의 재테스트·중간 기록' in html
    prepare,_ = request(shared,'/prepare')
    assert '동의 화면의 필수 고지 항목 표시' in prepare


@pytest.mark.parametrize('mode',['SHARED','LOCAL','DEMO'])
def test_stored_preparation_does_not_scan_run_history(shared,tmp_path,monkeypatch,mode):
    reader = shared.readers['ACTUAL'] if mode == 'SHARED' else WorkbenchReader(
        load_catalog(),tmp_path/'unused-runs',readiness=ReadinessStore(tmp_path/'state'),origin='DEMO' if mode=='DEMO' else 'ACTUAL')
    def forbidden(*args,**kwargs):
        raise AssertionError('Preparation must not load result archives or verify historical bundles')
    for name in ('scenario','run','_scenario_runs','_bundles_by_scenario'):
        monkeypatch.setattr(reader,name,forbidden)
    if mode == 'SHARED': monkeypatch.setattr(reader.readiness,'latest',forbidden)
    view = delivery.preparation(reader)
    assert view['mode'] == mode
    assert sum(len(row['profiles']) for group in view['groups'] for row in group['scenarios']) == 11
