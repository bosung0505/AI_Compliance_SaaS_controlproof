"""Additive display projections for comparison, reports and stored preparation information."""
from __future__ import annotations

from collections import Counter
from uuid import UUID

from engine.web.details import PROFILE_PURPOSES, _json, definition_document, history_projection

N01_PAIR = ('48a70f5e-aa62-41fc-bf58-3624a6102b4f', 'd3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18')
N01_MANIFESTS = ('82c1b6ce554873d78b8c121bb35a1c19c1c7b4d03f6c5339dd8eaeb408c542a9',
                 '68220e0088e8468345cbdcc7fe1af3ba91547bca7c6188b2d6a97dc0273ccf0f')


def _uuid(value):
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def _relationship_problem(reader, view, parent, child):
    if view.get('lineage_problem'):
        return view['lineage_problem']
    if parent is None:
        return {'code':'PARENT_NOT_IN_ROOT', 'detail':'부모 실행의 원본이 없어 비교할 수 없습니다.'}
    if parent['integrity']['status'] != 'VERIFIED' or child['integrity']['status'] != 'VERIFIED':
        return {'code':'PAIR_NOT_VERIFIED', 'detail':'양쪽 실행의 무결성을 모두 확인해야 비교할 수 있습니다.'}
    before, after = parent['run'], child['run']
    if any(side.get('run_state') in {'ABORTED','RESTORE_FAILED'} for side in (before,after)):
        return {'code':'PAIR_EXECUTION_UNSAFE', 'detail':'중단되거나 복구에 실패한 실행입니다. 봉인 판정을 대상 서비스의 정상 비교 결과로 사용하지 않습니다.'}
    if before['scenario_id'] != after['scenario_id'] or before['execution_profile'] != after['execution_profile']:
        return {'code':'PAIR_SCOPE_MISMATCH', 'detail':'서로 다른 시나리오나 실행 프로필의 결과입니다.'}
    if after.get('parent_run_id') != before['run_id']:
        return {'code':'PARENT_LINK_MISMATCH', 'detail':'실행 원본과 재테스트 연결의 부모 ID가 일치하지 않습니다.'}
    seen, current = {after['run_id']}, before['run_id']
    while current:
        if current in seen:
            return {'code':'LINEAGE_CYCLE', 'detail':'계보에 같은 실행이 반복돼 비교를 중단했습니다.'}
        if not _uuid(current):
            return {'code':'LINEAGE_ID_INVALID', 'detail':'계보의 실행 ID 형식을 확인할 수 없습니다.'}
        seen.add(current)
        directory = reader.run_root / current
        if not directory.is_dir() or directory.is_symlink() or directory.is_junction():
            return {'code':'ANCESTOR_NOT_IN_ROOT', 'detail':'더 이전 계보의 원본이 없어 전체 연결을 확인할 수 없습니다.'}
        record = _json(directory/'run.json', {})
        if (reader._integrity(directory,record.get('state'))['status'] != 'VERIFIED'
                or record.get('run_id') != current or record.get('scenario_id') != after['scenario_id']):
            return {'code':'ANCESTOR_NOT_VERIFIED', 'detail':'이전 계보의 무결성 또는 실행 식별 정보를 확인하지 못했습니다.'}
        current = record.get('parent_run_id')
    return None


def compare_projection(reader, view, parent, child):
    problem = _relationship_problem(reader, view, parent, child)
    unknown = {'kind':'UNCONFIRMED', 'label':'기록된 변화만 비교합니다',
               'text':'판정이나 버전 차이만으로 서비스 수정 여부와 원인을 단정하지 않습니다. 아래 사유의 출처와 양쪽 원본을 확인하세요.',
               'source':None}
    result = {'scenario_id':child['run']['scenario_id'], 'comparison_available':problem is None,
              'relationship_problem':problem, 'cause':unknown, 'assertions':[],
              'scopes':{'parent':None,'child':None}, 'measurement_versions':{'parent':None,'child':None}}
    result['execution_states'] = {key:(side['run'].get('run_state') if side else None) for key,side in (('parent',parent),('child',child))}
    for key, side in (('parent',parent),('child',child)):
        if side and side['integrity']['status'] == 'VERIFIED':
            result['scopes'][key] = side.get('ui',{}).get('sealed_definition')
            values = {i['measurement_display_version'] for i in side.get('ui',{}).get('notice_measurements',[])}
            result['measurement_versions'][key] = next(iter(values)) if len(values) == 1 else None
    if problem:
        return result
    pair = (view['parent']['run_id'], view['child']['run_id'])
    if (reader.origin == 'ACTUAL' and pair == N01_PAIR
            and (parent['run'].get('manifest_sha256'),child['run'].get('manifest_sha256')) == N01_MANIFESTS
            and result['measurement_versions'] == {'parent':1,'child':2}
            and view['parent']['verdict'] == view['child']['verdict'] == 'PASS'
            and view.get('parent_unchanged') is True):
        result['cause'] = {'kind':'CONTROLPROOF_MEASUREMENT', 'label':'고지 표시의 측정 방식을 보강했습니다',
                           'text':'두 실행 모두 PASS입니다. ControlProof의 숨김·투명·잘림·줄 수 제한 고지 측정을 v1에서 v2로 보강했습니다. WhyYou 서비스 수정 이력이 아닙니다.',
                           'source':'specs/009-n01-n03-notice-scenarios/actual-closure.md · 각 실행 n01-measurements.json'}
    elif view.get('remediation'):
        result['cause'] = {'kind':'WHYYOU_DEVELOPMENT', 'label':'문제 발견 후 조회 기능을 보완했습니다',
                           'text':view['remediation']['remedy'], 'source':view['remediation']['review_source']}
    before_rules = {r['assertion_id']:r for r in (parent.get('assertions') or [])}
    after_rules = {r['assertion_id']:r for r in (child.get('assertions') or [])}
    for item in view.get('assertion_changes') or []:
        result['assertions'].append({**item,
            'description':(after_rules.get(item['assertion_id']) or before_rules.get(item['assertion_id']) or {}).get('description'),
            'before_evidence':[{**ev,'run_id':pair[0]} for ev in item['before_evidence']],
            'after_evidence':[{**ev,'run_id':pair[1]} for ev in item['after_evidence']],
        })
    return result


def report_projection(reader, report, workbench):
    from engine.web.readmodel import _definition

    records = []
    comparisons = []
    for entry in reader.catalog['scenarios']:
        history = history_projection(reader, entry, reader._scenario_runs(entry['id']))
        official_children = {r['run_id'] for r in entry['official_status'].get('records', []) if r.get('role') in {'final','repeat'}}
        for row in history:
            versions = None
            if row['present'] and row['integrity'] == 'VERIFIED':
                directory = reader.run_root/row['run_id']
                sealed = definition_document(directory/'scenario.snapshot.yaml', row['execution_profile'], 'sealed_snapshot',
                    f"{row['run_id']}/scenario.snapshot.yaml", describe=_definition, run_id=row['run_id'])
                def fields(name, keys, *, directory=directory):
                    raw = _json(directory/name)
                    return {key:raw.get(key) for key in keys} if isinstance(raw,dict) else None

                versions = {'source':'sealed_bundle',
                            'target':fields('target.snapshot.json', ('target_id','target_version','git_commit_sha','git_diff_digest','git_dirty','model_fixture_digest','source_kind')),
                            'environment':fields('environment.snapshot.json', ('environment_kind','aws_deployment_status','controlproof_commit','whyyou_commit','model_fixture_digest','unverified_scope')),
                            'scenario':{key:sealed[key] for key in ('source','source_ref','run_id','version','sha256','problem') if key in sealed},
                            'run':fields('run.json', ('scenario_version','target_version','model_fixture_digest','policy_snapshot_digest','scoring_rule_source_digest','prompt_version')),
                            'notice_policy':_json(directory/'n01-policy-identifiers.json') if entry['id']=='N-01' else None,
                            'source_refs':[name for name in ('run.json','target.snapshot.json','environment.snapshot.json','scenario.snapshot.yaml') if (directory/name).is_file()]}
            records.append({**row,'scenario_id':entry['id'],'versions':versions})
            if row['present'] and row.get('parent_run_id'):
                comparisons.append({'scenario_id':entry['id'], 'child_run_id':row['run_id'],
                                    'parent_run_id':row['parent_run_id'], 'integrity':row['integrity'],
                                    'execution_profile':row['execution_profile'],
                                    'primary':reader.origin == 'ACTUAL' and row['run_id'] in official_children})
    return {'coverage':workbench['ui']['coverage'], 'groups':workbench['ui']['groups'],
            'scenario_scopes':[{'id':r['id'],'current_scope':r['ui']['current_scope']} for g in workbench['ui']['groups'] for r in g['scenarios']],
            'records':records, 'comparisons':comparisons,
            'reproduction_context':{'text':'D-019는 별도 PC의 H-03 DLQ 한 건(277d3f5a-766a-45ab-9f1d-28a3a30a82e6)을 당시 통합 대상 374b122 기준으로 인정했습니다. 현재 공유본 열람과 구분하며, 다른 시나리오·현재 버전·AWS 전체의 독립 재현으로 확대하지 않습니다.',
                                    'source':'docs/AI_SPEC_KIT_PLAYBOOK.md §6 · Decision D-019 · specs/005-web-workbench-report/validation.md Phase 9'},
            'inventory':{'present':sum(r['present'] for r in records),'missing':sum(not r['present'] for r in records),
                         'integrity_counts':dict(Counter(r['integrity'] for r in records if r['present']))}}


def preparation(reader):
    """Only read saved local readiness. GET never calls a runner or writes state."""
    from engine.web.review import test_plan

    groups = []
    for control in ('N','H','A','E'):
        rows = []
        for entry in reader.catalog['scenarios']:
            if entry['control'] != control:
                continue
            profiles = [reader._scenario_profile(entry,profile,[]) for profile in entry['profiles']]
            rows.append({'id':entry['id'], 'question':entry['question'], 'profiles':profiles,
                         'test_plan':test_plan(entry['id'],profiles[0]['definition'] if profiles else None),
                         'ui':{'profile_results':[{'execution_profile':p['execution_profile'],
                             'display_purpose':PROFILE_PURPOSES.get(p['execution_profile'],p['definition'].get('intent'))} for p in profiles]}})
        groups.append({'control':control, 'scenarios':rows})
    return {**reader.header('prepare'), 'groups':groups, 'mode':('DEMO' if reader.origin=='DEMO' else 'SHARED' if reader.shared_snapshot else 'LOCAL')}
