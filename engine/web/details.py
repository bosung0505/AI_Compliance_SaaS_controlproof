"""Read-only Spec010 detail projections. Catalog approval, time order and sealed facts remain separate."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
EVIDENCE_TITLES = {
    'file:n03-lanes.json':'합성 지원자와 동의 상태별 구분',
    'file:n03-stale-before.json':'이전 정책 제출 전 동의 상태',
    'file:n03-stale-attempt.json':'이전 정책 식별값 제출 응답',
    'file:n03-stale-after.json':'이전 정책 제출 후 동의 상태',
    'file:n03-latest-commit.json':'최신 정책 재조회·동의 저장 결과',
    'file:n03-past-before.json':'기존 동의 기록 · 테스트 전',
    'file:n03-past-after.json':'기존 동의 기록 · 테스트 후',
    'file:n03-scope.json':'N-03 실행 범위와 미검증 항목',
    'file:n01-measurements.json':'PC·모바일 고지 표시 측정',
    'file:n01-policy-identifiers.json':'화면·서버·저장된 정책 식별값',
    'file:n01-pc-capture.png':'PC 고지 화면 캡처',
    'file:n01-mobile-capture.png':'모바일 고지 화면 캡처',
}
CONDITION_TITLES = {
    'N03-A1':'이전 정책으로 동의를 제출했을 때', 'N03-A2':'최신 정책을 다시 읽고 동의했을 때',
    'N03-A3':'이미 완료한 과거 동의 기록', 'N01-A1':'PC 화면의 고지 표시',
    'N01-A2':'모바일 화면의 고지 표시', 'N01-A3':'화면·서버·저장 기록의 정책 일치',
}
CONDITION_SETUPS = {
    'N03-A1':'실제 교체 없이 만든 이전 정책 식별값으로 동의를 제출하고, 제출 전후의 동의 상태를 읽었습니다.',
    'N03-A2':'정책을 다시 조회한 뒤 해당 식별값으로 동의를 제출하고 저장된 기록을 확인했습니다.',
    'N03-A3':'테스트 전에 동의를 완료한 합성 지원자의 기록을 테스트 전후에 읽어 비교했습니다.',
    'N01-A1':'PC 화면에서 동의하기 전에 다섯 필수 고지의 표시 상태를 측정했습니다.',
    'N01-A2':'모바일 화면에서 동의하기 전에 다섯 필수 고지의 표시 상태를 측정했습니다.',
    'N01-A3':'화면에 제시한 정책 식별값과 서버 응답·저장된 동의 기록을 대조했습니다.',
}
PROFILE_PURPOSES = {
    'H03_MINIMAL_V1':'리포트 생성 장애가 드러나고, 결과를 확인하지 못한 상태에서 최종 결정이 차단되는지 확인합니다.',
    'H03_DLQ_V2':'처리 실패와 재시도·DLQ 기록을 보존하고, 정상 상태로 복구할 수 있는지 확인합니다.',
    'E03_BEFORE_V2':'결과 저장 전에 장애가 생겼을 때, 중복 결과 없이 처리와 기록을 복구할 수 있는지 확인합니다.',
    'E03_AFTER_V2':'결과 저장 후 같은 사건이 다시 전달돼도, 결과와 결정 이력이 중복되거나 달라지지 않는지 확인합니다.',
}


def _json(path: Path, fallback: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def profile_metadata(scenario_id: str, raw_execution_profile: str | None, legacy_h03_confirmed: bool = False) -> dict:
    if raw_execution_profile:
        return {'execution_profile': raw_execution_profile, 'raw_execution_profile': raw_execution_profile, 'profile_source': 'RUN_RECORD'}
    if scenario_id == 'H-03' and legacy_h03_confirmed:
        return {'execution_profile': 'H03_MINIMAL_V1', 'raw_execution_profile': None, 'profile_source': 'LEGACY_H03_COMPATIBILITY'}
    return {'execution_profile': None, 'raw_execution_profile': None, 'profile_source': 'UNKNOWN', 'problem': 'PROFILE_UNAVAILABLE'}


def _time(value: str | None) -> float | None:
    try:
        parsed = datetime.fromisoformat(value or '')
        return parsed.timestamp() if parsed.tzinfo else None
    except (ValueError, OverflowError, OSError):
        return None


def select_profile(profile: str, catalog_records: list[dict], records: list[dict]) -> dict:
    candidates = [r for r in catalog_records if r.get('role') in ('final','repeat') and r.get('execution_profile', profile) == profile]
    result = {'execution_profile': profile, 'selected_run_id': None, 'catalog_role': None,
              'selection_problems': [], 'latest_temporally_confirmed': False, 'selected_verdict': None}
    if not candidates:
        result['selection_problems'] = ['NO_OFFICIAL_RESULT']
        return result
    selected = candidates[-1]
    result.update(selected_run_id=selected['run_id'], catalog_role=selected['role'])
    by_id = {r['run_id']:r for r in records}
    record = by_id.get(selected['run_id'], {})
    problems = result['selection_problems']
    if not record.get('present'):
        problems.append('RECORD_MISSING')
    elif record.get('integrity') != 'VERIFIED':
        problems.append('INTEGRITY_BLOCKED')
    else:
        if selected.get('result') and selected['result'] != record.get('verdict'):
            problems.append('CATALOG_RESULT_MISMATCH')
        if record.get('execution_profile') and record['execution_profile'] != profile:
            problems.append('PROFILE_MISMATCH')
        if record.get('run_state') in ('ABORTED','RESTORE_FAILED'):
            problems.append('EXECUTION_INCOMPLETE')
        result['selected_verdict'] = record.get('verdict')
    times = [_time(by_id.get(r['run_id'], {}).get('started_at')) for r in candidates]
    confirmed = bool(times) and all(t is not None for t in times) and times[-1] == max(t for t in times if t is not None)
    result['latest_temporally_confirmed'] = confirmed
    if not confirmed:
        problems.append('TEMPORAL_ORDER_UNCONFIRMED')
    return result


def _scope(raw: dict) -> dict:
    return {
        'partial': raw.get('scenario_id') == 'N-03' and bool(raw.get('unverified_scope_items')),
        'applicable_assertion_ids': list(raw.get('applicable_assertion_ids') or []),
        'target_access': list(raw.get('target_access') or []),
        'unverified_items': [{k:i.get(k) for k in ('id','text','follow_up')} for i in raw.get('unverified_scope_items') or [] if isinstance(i,dict)],
        'limitations': [{k:i.get(k) for k in ('id','text')} for i in raw.get('limitations') or [] if isinstance(i,dict)],
    }


def definition_document(path: Path, profile: str | None, source: str, source_ref: str, *, describe, run_id: str | None = None) -> dict:
    result = {'execution_profile':profile, 'source':source, 'source_ref':source_ref, 'run_id':run_id,
              'version':None, 'sha256':None, 'definition':None, 'scope':None, 'problem':None}
    try:
        payload = path.read_bytes()
        raw = yaml.safe_load(payload.decode('utf-8'))
        if not isinstance(raw,dict):
            raise TypeError('definition must be a mapping')
        raw = raw.get('definition', raw)
        if not isinstance(raw,dict):
            raise TypeError('nested definition must be a mapping')
        definition = describe(raw, source, run_id)
        definition.update(required_capabilities=raw.get('required_capabilities'), timing_policy=raw.get('timing_policy'))
        definition['steps'] = raw.get('steps') or []
        result.update(version=raw.get('version'), sha256=hashlib.sha256(payload).hexdigest(), definition=definition, scope=_scope(raw))
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        result['problem'] = 'DEFINITION_UNAVAILABLE'
    return result


def history_projection(reader, entry: dict, runs: list[dict]) -> list[dict]:
    approved = entry['official_status'].get('records', []) if reader.origin == 'ACTUAL' else []
    roles = {r['run_id']:r for r in approved}
    history = []
    for run in runs:
        raw = _json(reader.run_root / run['run_id'] / 'run.json', {})
        legacy = (raw.get('scenario_id') == 'H-03' and raw.get('scenario_version') == '1.0.0'
                  and run['integrity']=='VERIFIED' and not raw.get('execution_profile') and not raw.get('profile_contract'))
        if legacy:
            try:
                snapshot = yaml.safe_load((reader.run_root / run['run_id'] / 'scenario.snapshot.yaml').read_text(encoding='utf-8'))
                snapshot = snapshot.get('definition',snapshot)
                legacy = snapshot.get('scenario_id')=='H-03' and snapshot.get('version')=='1.0.0' and not snapshot.get('execution_profile')
            except (OSError,ValueError,AttributeError,yaml.YAMLError):
                legacy = False
        metadata = profile_metadata(raw.get('scenario_id'), raw.get('execution_profile'), legacy)
        history.append({**run, **metadata, 'present':True, 'catalog_role':roles.get(run['run_id'],{}).get('role'),
                        'problem':metadata.get('problem') or ('INTEGRITY_BLOCKED' if run['integrity'] != 'VERIFIED' else None)})
    present = {r['run_id'] for r in history}
    for record in approved:
        if record['run_id'] not in present:
            history.append({'run_id':record['run_id'], 'execution_profile':record.get('execution_profile'),
                            'raw_execution_profile':None, 'profile_source':'CATALOG_REFERENCE', 'catalog_role':record['role'],
                            'record_role':'OFFICIAL', 'parent_run_id':None, 'started_at':None, 'present':False,
                            'integrity':None, 'verdict':None, 'run_state':None, 'problem':'RECORD_MISSING'})
    # Stable ID order within time ties, with unconfirmed timestamps in a separate trailing group.
    history.sort(key=lambda r:r['run_id'])
    history.sort(key=lambda r:(_time(r.get('started_at')) is not None, _time(r.get('started_at')) or 0), reverse=True)
    for row in history:
        row['time_confirmed'] = _time(row.get('started_at')) is not None
    return history


def scenario_projection(reader, entry: dict, runs: list[dict], *, describe) -> dict:
    approved = entry['official_status'].get('records', []) if reader.origin == 'ACTUAL' else []
    history = history_projection(reader, entry, runs)
    profiles = []
    definitions = []
    for profile in entry['profiles']:
        key = profile['execution_profile']
        selected = select_profile(key, approved, history)
        if reader.origin == 'DEMO':
            selected['selection_problems'] = ['DEMO_HAS_NO_OFFICIAL_RESULT']
        document = definition_document(REPO / profile['scenario_file'], key, 'scenario_file', profile['scenario_file'], describe=describe)
        selected['display_purpose'] = PROFILE_PURPOSES.get(key, (document['definition'] or {}).get('intent'))
        selected['purpose_source'] = 'CURATED_PROFILE_DESCRIPTION' if key in PROFILE_PURPOSES else 'CURRENT_SCENARIO_FILE'
        profiles.append(selected)
        definitions.append(document)
    return {'profile_results':profiles, 'history':history, 'current_definitions':definitions,
            'default_profile':entry['profiles'][0]['execution_profile'] if entry['profiles'] else None}


def run_projection(bundle: Path, record: dict, *, describe, reader=None, strict_verified=False) -> dict:
    profile = profile_metadata(record.get('scenario_id'),record.get('execution_profile'),
                               record.get('scenario_id')=='H-03' and record.get('scenario_version')=='1.0.0' and not record.get('profile_contract'))
    sealed = definition_document(bundle / 'scenario.snapshot.yaml', profile['execution_profile'], 'sealed_snapshot',
                                 f'{bundle.name}/scenario.snapshot.yaml', describe=describe, run_id=bundle.name)
    lanes = []
    problems = []
    if record.get('scenario_id') == 'N-01':
        measured = _json(bundle / 'n01-measurements.json')
        policies = _json(bundle / 'n01-policy-identifiers.json')
        if not isinstance(measured,list) or not isinstance(policies,list):
            problems.append('NOTICE_MEASUREMENTS_UNAVAILABLE')
        else:
            by_lane = {p.get('lane'):p for p in policies if isinstance(p,dict)}
            for lane in measured:
                if not isinstance(lane,dict):
                    continue
                capture = lane.get('capture') or {}
                ref = f"file:{capture['file']}" if capture.get('file') else None
                shared = reader.shared_snapshot if reader and reader.origin=='ACTUAL' else None
                source = next((r for r in (shared or {}).get('records',[]) if r['run_id']==bundle.name),{})
                allowed = (bool(source) and source.get('files',{}).get(capture.get('file'))==capture.get('sha256')) if shared else (
                    (bundle.name,ref,capture.get('sha256')) in getattr(reader,'png_approvals',frozenset()))
                lanes.append({k:lane.get(k) for k in ('lane','measurement_version','viewport','items','measurement_error','step_reached')} | {
                    'capture_ref':ref, 'capture_available':bool(strict_verified and ref and allowed),
                    'capture_sha256':capture.get('sha256'), 'policy':by_lane.get(lane.get('lane')),
                    'measurement_display_version':lane.get('measurement_version') if lane.get('measurement_version') is not None else 1,
                    'measurement_version_source':'SEALED_FIELD' if lane.get('measurement_version') is not None else 'LEGACY_N01_COMPATIBILITY',
                    'source_ref':'n01-measurements.json', 'policy_source_ref':'n01-policy-identifiers.json',
                })
    entry = reader._catalog_entry(record.get('scenario_id')) if reader else None
    related = history_projection(reader, entry, reader._scenario_runs(record.get('scenario_id'))) if entry else []
    return {'sealed_definition':sealed, 'profile':profile, 'notice_measurements':lanes, 'problems':problems,
            'related_runs':related, 'condition_titles':CONDITION_TITLES, 'condition_setups':CONDITION_SETUPS,
            'evidence_titles':EVIDENCE_TITLES}
