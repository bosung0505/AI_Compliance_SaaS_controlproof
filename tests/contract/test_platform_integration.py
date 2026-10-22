"""Stage6: truthful page navigation and keyboard skip target across actual service routes."""
from __future__ import annotations

import re

import pytest

from tests.contract.test_platform_delivery import shared, request, N01
from tests.contract.test_platform_public_pages import Markup


@pytest.mark.parametrize('path,current',[
    ('/','/'),('/results','/results'),('/prepare','/prepare'),('/report','/report'),
    ('/scenarios/N-03','/scenarios/N-03'),(f'/runs/{N01}',f'/runs/{N01}'),
    (f'/compare/{N01}','/report'),('/demo/prepare','/demo/prepare'),
])
def test_workspace_navigation_exposes_page_links_and_exactly_one_current(shared,path,current):
    html,_ = request(shared,path)
    nav = re.search(r'<nav[^>]*id="primary-navigation".*?</nav>',html,re.S).group()
    tags = Markup(nav).tags
    assert not any(attrs.get('role') in {'tab','tablist'} for _,attrs in tags)
    links = [attrs for tag,attrs in tags if tag=='a']
    assert len(links)==5
    assert [a['href'] for a in links if a.get('aria-current')=='page']==[current]
    assert 'href="#main"' in html and 'id="main"' in html and 'tabindex="-1"' in html


def test_public_workflow_keeps_real_in_page_tabs_separate(shared):
    html,_ = request(shared,'/product')
    tags=Markup(html).tags
    tabs=[a for tag,a in tags if a.get('role')=='tab']
    assert tabs and all('data-step' in a for a in tabs)


def test_report_version_provenance_does_not_claim_missing_files_or_print_raw_commit_dict(shared):
    report=shared.readers['ACTUAL'].report()
    legacy=[r for r in report['ui']['records'] if r['versions'] and r['versions']['environment'] is None]
    assert legacy
    for row in legacy:
        assert 'environment.snapshot.json' not in row['versions']['source_refs']
    html,_=request(shared,'/report')
    assert "ControlProof commit {&#39;commit_sha&#39;" not in html


@pytest.mark.parametrize('prefix',['','/demo'])
def test_error_recovery_keeps_selected_mode_without_changing_json_error(shared,prefix):
    html,_=request(shared,prefix+'/scenarios/N-99',status=404)
    assert f'href="{prefix}/"' in html
    assert ('class="demo-banner"' in html) == bool(prefix)
    assert f'href="{prefix}/results"' in html and f'href="{prefix}/prepare"' in html
    body,_=request(shared,prefix+'/api/scenarios/N-99',status=404)
    import json
    payload=json.loads(body)
    assert set(payload)=={'schema_version','view','error_kind','code','detail'}
    assert payload['code']=='SCENARIO_NOT_FOUND'
