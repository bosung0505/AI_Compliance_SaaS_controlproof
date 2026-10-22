"""Check a real browser PDF against its sanitized report API data. Run with the bundled PDF Python runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def compact(text):
    return re.sub(r'\s+', '', text).replace('`','')


def inspect(pdf_path: Path, report: dict):
    import pdfplumber
    from pypdf import PdfReader

    pdf = PdfReader(pdf_path)
    pages = [page.extract_text() or '' for page in pdf.pages]
    text = compact('\n'.join(pages))
    has = lambda value: bool(value) and compact(value) in text
    uris = set()
    for page in pdf.pages:
        for ref in page.get('/Annots', []):
            action = ref.get_object().get('/A', {})
            if action.get('/URI'):
                uris.add(str(action['/URI']))
    rows = report['ui']['records']
    versions = [row['versions'] for row in rows if row['versions']]
    full_ids = all(has(row['run_id']) for row in rows)
    sealed_versions = all(has(v['scenario']['sha256']) and has(v['target']['git_commit_sha']) for v in versions)
    linked_runs = all(any(f"/runs/{row['run_id']}" in uri for uri in uris) for row in rows if row['present'])
    missing_link_absent = all(not any(row['run_id'] in uri for uri in uris) for row in rows if not row['present'])
    linked_comparisons = all(any(f"/compare/{row['child_run_id']}" in uri for uri in uris) for row in report['ui']['comparisons'])
    partial = all(has(key) for key in ('N03-A1','N03-A2','N03-A3','N03-U1','N03-U2','N03-U3','N03-L1','후속 조건'))
    claims = {
        'R1':has('WhyYou 테스트 환경') and sealed_versions,
        'R2':has(report['purpose_and_scope']['text']) and has(report['fixed_scope_sentence']),
        'R3':has(report['synthetic_data_notice']['text']),
        'R4':all(has(row['id']) and has(row['title']) for row in report['catalog_status']),
        'R5':has('PASS 통과 9') and has('FAIL 실패 0') and has('판정 불가 3') and has('NOT_RUN 미실행 0'),
        'R6':all(has(row['summary']) for row in report['scenario_expectations']),
        'R7':all(has(row['impact']) for row in report['major_failures']),
        'R8':full_ids and linked_runs and missing_link_absent and has('INVALID'),
        'R9':sealed_versions and has('프롬프트 버전 기록 없음'),
        'R10':linked_comparisons and has('PASS→PASS') and has('ControlProof 측정 보강'),
        'R11':all(has(row['text']) for row in report['test_only_additions']),
        'R12':partial and has('D-019') and has('277d3f5a-766a-45ab-9f1d-28a3a30a82e6') and has('실제 AWS NOT_RUN'),
        'R13':has(report['legal_notice']['text']),
        'C1':has(report['fixed_scope_sentence']),
        'C2':linked_runs and sealed_versions,
        'C3':has(report['ai_score_principle']['text']),
        'C4':has(report['human_decision_location']['text']),
        'C5':has('최초 실패는 보존합니다') and linked_comparisons,
        'C6':all(has(s) for s in ('A-01','A-02','A-03','이의제기 기능이 없어 실행 대상이 없습니다')),
        'C7':all(has(s) for s in ('무엇을 확인했나요','시나리오별 확인 결과','발견한 문제와 다시 확인한 결과','근거와 보관 상태','방법과 검증의 경계')),
        'C8':has(report['ui']['reproduction_context']['text']),
        'C9':has(report['legal_notice']['text']),
    }
    bounds = []
    with pdfplumber.open(pdf_path) as document:
        for number,page in enumerate(document.pages,1):
            for char in page.chars:
                if char['x0'] < -1 or char['x1'] > page.width+1 or char['top'] < -1 or char['bottom'] > page.height+1:
                    bounds.append({'page':number,'x0':char['x0'],'x1':char['x1'],'top':char['top'],'bottom':char['bottom']})
    checks = {'all22_contents':all(claims.values()),'all29_record_ids':full_ids,
              'all27_verified_versions':sealed_versions,'original_missing_record_has_no_link':missing_link_absent,
              'all_actual_compare_links':linked_comparisons,'no_screen_skip_link':not has('본문으로 건너뛰기'),
              'no_replacement_glyph':not any('\ufffd' in page for page in pages),
              'no_empty_page':all(len(compact(page))>80 for page in pages),
              'page_footers':all(has_page_footer(page,i+1,len(pages)) for i,page in enumerate(pages)),
              'no_text_outside_page':not bounds,
              'A4':all(abs(float(page.mediabox.width)-595.276)<2 and abs(float(page.mediabox.height)-841.89)<2 for page in pdf.pages)}
    return {'pdf':str(pdf_path),'pdf_sha256':hashlib.sha256(pdf_path.read_bytes()).hexdigest(),'pages':len(pages),'items':claims,'checks':checks,
            'text_lengths':[len(page) for page in pages],'out_of_bounds':bounds[:30],
            'uri_count':len(uris),'visual_review_required':True}


def has_page_footer(text, page, total):
    return f'{page}/{total}' in compact(text) and 'ControlProof' in text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf',type=Path,required=True)
    parser.add_argument('--report-json',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=inspect(args.pdf,json.loads(args.report_json.read_text(encoding='utf-8')))
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'pages':result['pages'],'failed_items':[k for k,v in result['items'].items() if not v],
                      'failed_checks':[k for k,v in result['checks'].items() if not v]}))
    return 0 if all(result['checks'].values()) else 1


if __name__=='__main__':
    raise SystemExit(main())
