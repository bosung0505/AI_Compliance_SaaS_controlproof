"""Spec010 stage4: actual sealed READS, no new target execution."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from engine.web.details import definition_document, profile_metadata, select_profile
from engine.web.preflight import ReadinessStore
from engine.web.readmodel import WorkbenchReader, _definition, load_catalog

ROOT = Path(__file__).parents[2]
CASES = json.loads((ROOT / 'specs/010-platform-ui-integration/contracts/coverage-cases.json').read_text(encoding='utf-8'))['cases']


@pytest.fixture(scope='module')
def reader(tmp_path_factory):
    return WorkbenchReader(load_catalog(), ROOT / 'review-data/bundles',
                           readiness=ReadinessStore(tmp_path_factory.mktemp('details-state')),
                           shared_snapshot=json.loads((ROOT / 'review-data/snapshot.json').read_text(encoding='utf-8')))


@pytest.mark.parametrize('case', [c for c in CASES if c['case_type']=='profile_compatibility'], ids=lambda c:c['case_id'])
def test_profile_compatibility(case):
    actual = profile_metadata(**case['input'])
    assert all(actual[k] == v for k,v in case['expected'].items() if k != 'extra_profile_count')


@pytest.mark.parametrize('case', [c for c in CASES if c['case_type']=='official_selection' and 'profile' in c['input']], ids=lambda c:c['case_id'])
def test_official_selection_contract(case):
    data = case['input']
    actual = select_profile(data['profile'], data['catalog_records'], data['records'])
    expected = case['expected']
    for key in ('selected_run_id','catalog_role','selection_problems','latest_temporally_confirmed','selected_verdict'):
        if key in expected:
            assert actual[key] == expected[key]


def test_all_profiles_and_complete_history_without_five_link_limit(reader):
    seen, profiles = set(), []
    for entry in reader.catalog['scenarios']:
        data = reader.scenario(entry['id'])
        ui = data['ui']
        assert len(ui['profile_results']) == len(entry['profiles'])
        profiles.extend(ui['profile_results'])
        for row in ui['history']:
            assert row['run_id'] not in seen
            seen.add(row['run_id'])
        assert len(ui['current_definitions']) == len(entry['profiles'])
    assert len(profiles) == 11 and len(seen) == 29
    assert all(p['selected_run_id'] and not p['selection_problems'] for p in profiles)
    e01 = reader.scenario('E-01')['ui']
    assert e01['profile_results'][0]['selected_run_id'].startswith('4030503c')
    n02 = reader.scenario('N-02')['ui']['history']
    missing = next(r for r in n02 if r['run_id'].startswith('7b59237e'))
    invalid = next(r for r in n02 if r['run_id'].startswith('ce5f2750'))
    assert missing['present'] is False and missing['verdict'] is None
    assert invalid['integrity'] == 'INVALID' and invalid['verdict'] is None
    assert reader.scenario('H-03')['ui']['history'][0]['profile_source'] in ('RUN_RECORD','LEGACY_H03_COMPATIBILITY')
    e03 = reader.scenario('E-03')['ui']['profile_results']
    assert [p['execution_profile'] for p in e03] == ['E03_BEFORE_V2','E03_AFTER_V2']
    assert e03[0]['selected_run_id'] != e03[1]['selected_run_id']


def test_current_and_sealed_scope_never_merge(reader, tmp_path):
    data = reader.scenario('N-03')
    current = data['ui']['current_definitions'][0]
    sealed = reader.run('f27b68e8-0df8-46b3-a198-c7917c2f08bb')['ui']['sealed_definition']
    assert current['source'] == 'scenario_file' and sealed['source'] == 'sealed_snapshot'
    assert len(current['sha256']) == len(sealed['sha256']) == 64
    assert [i['id'] for i in sealed['scope']['unverified_items']] == ['N03-U1','N03-U2','N03-U3']
    assert sealed['scope']['applicable_assertion_ids'] == ['N03-A1','N03-A2','N03-A3']
    path = tmp_path / 'current.yaml'
    original = (ROOT / 'scenarios/N-03.yaml').read_text(encoding='utf-8')
    path.write_text(original.replace('N03-U3','FUTURE-U4'), encoding='utf-8')
    future = definition_document(path, 'N03_STALE_CONSENT_V1', 'scenario_file', 'fixture/current.yaml', describe=_definition)
    assert future['sha256'] != sealed['sha256']
    assert future['scope']['unverified_items'][-1]['id'] == 'FUTURE-U4'
    assert sealed['scope']['unverified_items'][-1]['id'] == 'N03-U3'


def test_missing_and_invalid_selection_never_falls_back(reader):
    entry = copy.deepcopy(next(e for e in reader.catalog['scenarios'] if e['id']=='N-01'))
    profile = entry['profiles'][0]['execution_profile']
    history = reader.scenario('N-01')['ui']['history']
    final = next(r for r in history if r['run_id'].startswith('d3aac7d9'))
    final.update(present=False, verdict=None, started_at=None)
    choice = select_profile(profile, entry['official_status']['records'], history)
    assert choice['selected_run_id'].startswith('d3aac7d9')
    assert 'RECORD_MISSING' in choice['selection_problems']


def test_n01_measurement_versions_policy_and_capture_links_are_sealed(reader):
    for run_id, version in [('48a70f5e-aa62-41fc-bf58-3624a6102b4f',1),('d3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18',2)]:
        data = reader.run(run_id)
        assert data['verdict']['value'] == 'PASS'
        lanes = data['ui']['notice_measurements']
        assert [row['lane'] for row in lanes] == ['pc','mobile']
        assert all(row['measurement_display_version'] == version and len(row['items']) == 5 for row in lanes)
        if version == 1:
            assert all(row['measurement_version'] is None and row['measurement_version_source']=='LEGACY_N01_COMPATIBILITY' for row in lanes)
        assert all(row['capture_ref'].startswith('file:') and row['policy']['screen']['digest'] for row in lanes)
    # The real INVALID record is selected by metadata; do not assume its UUID suffix.
    invalid_id = next(r['run_id'] for r in reader.shared_snapshot['records'] if r['verification']['bundle_status']=='INVALID')
    assert reader.run(invalid_id)['ui']['sealed_definition'] is None
    assert reader.run(invalid_id)['verdict'] is None
