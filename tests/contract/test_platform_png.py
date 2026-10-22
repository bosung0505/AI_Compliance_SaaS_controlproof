"""Stage4 PNG policy. Tampering happens in temporary copies, never sealed originals."""
from __future__ import annotations

import hashlib
import json
import shutil
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.web import png_evidence as png
from engine.web.preflight import ReadinessStore
from engine.web.readmodel import WorkbenchReader, load_catalog

ROOT = Path(__file__).parents[2]
RUN = 'd3aac7d9-0a52-4f9a-9c8f-f6e1f7b6de18'


@pytest.mark.parametrize('query',['','ref=','ref=x&ref=x','ref=x&path=y','ref=%FF','ref=%GG','ref=%00','ref='+'x'*513])
def test_ref_query_is_strict(query):
    with pytest.raises(png.PNGRejected) as error:
        png.parse_ref(query)
    assert error.value.status == 400 and error.value.code == 'EVIDENCE_REF_INVALID'


def test_ref_decodes_once():
    assert png.parse_ref('ref=file%3An01-pc-capture.png') == 'file:n01-pc-capture.png'
    assert png.parse_ref('ref=%252e%252e') == '%2e%2e'


@pytest.fixture(scope='module')
def real_reader(tmp_path_factory):
    return WorkbenchReader(load_catalog(),ROOT/'review-data/bundles',readiness=ReadinessStore(tmp_path_factory.mktemp('png-state')),
                           shared_snapshot=json.loads((ROOT/'review-data/snapshot.json').read_text(encoding='utf-8')))


@pytest.mark.parametrize('run_id,name',[(RUN,'n01-pc-capture.png'),(RUN,'n01-mobile-capture.png'),('48a70f5e-aa62-41fc-bf58-3624a6102b4f','n01-pc-capture.png')])
def test_actual_reviewed_png_bytes_unchanged(real_reader,run_id,name):
    result = png.read_png(real_reader,run_id,f'file:{name}')
    assert result == (real_reader.run_root/run_id/name).read_bytes()
    assert result.startswith(png.PNG_SIGNATURE)


def test_real_invalid_unknown_and_non_png_are_blocked(real_reader):
    invalid = next(r['run_id'] for r in real_reader.shared_snapshot['records'] if r['verification']['bundle_status']=='INVALID')
    with pytest.raises(png.PNGRejected) as blocked:
        png.read_png(real_reader,invalid,'file:run.json')
    assert blocked.value.status == 422
    for run_id,ref,status in [(RUN,'file:run.json',403),(RUN,'file:unknown.png',404),('00000000-0000-0000-0000-000000000000','file:x.png',404)]:
        with pytest.raises(png.PNGRejected) as error:
            png.read_png(real_reader,run_id,ref)
        assert error.value.status == status


def test_local_and_demo_default_deny_and_shared_scope(real_reader):
    saved = real_reader.shared_snapshot
    try:
        real_reader.shared_snapshot = None
        for origin in ('ACTUAL','DEMO'):
            real_reader.origin = origin
            with pytest.raises(png.PNGRejected) as error:
                png.read_png(real_reader,RUN,'file:n01-pc-capture.png')
            assert error.value.status == 403
        real_reader.shared_snapshot = {**saved,'records':[]}
        real_reader.origin = 'ACTUAL'
        with pytest.raises(png.PNGRejected) as error:
            png.read_png(real_reader,RUN,'file:n01-pc-capture.png')
        assert error.value.status == 404
    finally:
        real_reader.shared_snapshot = saved
        real_reader.origin = 'ACTUAL'


def test_approved_local_file_is_reverified_after_read(tmp_path):
    run_root=tmp_path/'runs'; bundle=run_root/RUN
    shutil.copytree(ROOT/'review-data/bundles'/RUN,bundle)
    reader=WorkbenchReader(load_catalog(),run_root,readiness=ReadinessStore(tmp_path/'state'))
    ref='file:n01-pc-capture.png'; original=(bundle/'n01-pc-capture.png').read_bytes()
    approved={(RUN,ref,hashlib.sha256(original).hexdigest())}
    assert png.read_png(reader,RUN,ref,approved=approved)==original
    (bundle/'n01-pc-capture.png').write_bytes(original[:-1]+b'x')
    with pytest.raises(png.PNGRejected) as error:
        png.read_png(reader,RUN,ref,approved=approved)
    assert error.value.status == 422


@pytest.fixture
def synthetic(tmp_path,monkeypatch):
    """Isolate policy branches after strict verification using a labelled fake verifier/index."""
    root=tmp_path/'runs'; bundle=root/RUN; bundle.mkdir(parents=True)
    body=png.PNG_SIGNATURE+b'fixture'
    target=bundle/'capture.png'; target.write_bytes(body)
    item={'ref':'file:capture.png','relative_path':f'<run_root>/{RUN}/capture.png','mime_type':'image/png',
          'size_bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
    (bundle/'manifest.json').write_text(json.dumps({'files':[{'path':'capture.png',**{k:item[k] for k in ('mime_type','size_bytes','sha256')}}]}))
    reader=SimpleNamespace(run_root=root,shared_snapshot=None,origin='ACTUAL')
    monkeypatch.setattr(png,'verify_bundle',lambda p:{'bundle_status':'VERIFIED'})
    monkeypatch.setattr(png,'load_bundle_summary',lambda p:{'evidence_index':{'files':[item]}})
    return reader,bundle,item,{(RUN,item['ref'],item['sha256'])}


@pytest.mark.parametrize('field,value,status,code',[
    ('mime_type','text/html',403,'EVIDENCE_POLICY_BLOCKED'),
    ('relative_path',f'<run_root>/{RUN}/../outside.png',403,'EVIDENCE_POLICY_BLOCKED'),
    ('relative_path',f'<run_root>/{RUN}/C:secret.png',403,'EVIDENCE_POLICY_BLOCKED'),
    ('relative_path',f'<run_root>/{RUN}/folder\\capture.png',403,'EVIDENCE_POLICY_BLOCKED'),
    ('size_bytes',99,422,'INTEGRITY_FAILED'),
    ('sha256','0'*64,422,'INTEGRITY_FAILED'),
])
def test_invalid_metadata_fails_closed(synthetic,field,value,status,code):
    reader,bundle,item,approved=synthetic
    item[field]=value
    with pytest.raises(png.PNGRejected) as error:
        png.read_png(reader,RUN,item['ref'],approved=approved)
    assert (error.value.status,error.value.code)==(status,code)


def test_signature_and_exact_limit(synthetic,monkeypatch):
    reader,bundle,item,approved=synthetic
    target=bundle/'capture.png'
    for body in (b'not png', png.PNG_SIGNATURE+b'x'*(png.MAX_PNG_BYTES-len(png.PNG_SIGNATURE)), png.PNG_SIGNATURE+b'x'*png.MAX_PNG_BYTES):
        target.write_bytes(body)
        digest=hashlib.sha256(body).hexdigest()
        item.update(size_bytes=len(body),sha256=digest)
        manifest={'files':[{'path':'capture.png',**{k:item[k] for k in ('mime_type','size_bytes','sha256')}}]}
        (bundle/'manifest.json').write_text(json.dumps(manifest))
        approved={(RUN,item['ref'],digest)}
        if len(body)==png.MAX_PNG_BYTES:
            assert png.read_png(reader,RUN,item['ref'],approved=approved)==body
        else:
            with pytest.raises(png.PNGRejected) as error:
                png.read_png(reader,RUN,item['ref'],approved=approved)
            assert error.value.code=='PNG_CONTENT_INVALID'


def test_link_and_file_replacement_are_blocked(synthetic,monkeypatch):
    reader,bundle,item,approved=synthetic
    original = png._safe_read
    def replace_after_read(path,limit):
        payload=original(path,limit)
        if path.name=='capture.png':
            path.write_bytes(payload+b'x')
        return payload
    monkeypatch.setattr(png,'_safe_read',replace_after_read)
    with pytest.raises(png.PNGRejected) as error:
        png.read_png(reader,RUN,item['ref'],approved=approved)
    assert error.value.status==422


def test_shared_manifest_and_png_hash_context(synthetic):
    reader,bundle,item,approved=synthetic
    manifest_hash=hashlib.sha256((bundle/'manifest.json').read_bytes()).hexdigest()
    reader.shared_snapshot={'snapshot_id':'fixture','snapshot_digest':'a'*64,'records':[
        {'run_id':RUN,'files':{'capture.png':item['sha256'],'manifest.json':manifest_hash}}]}
    assert png.read_png(reader,RUN,item['ref'])==(bundle/'capture.png').read_bytes()
    reader.shared_snapshot['records'][0]['files'].pop('capture.png')
    with pytest.raises(png.PNGRejected) as error:
        png.read_png(reader,RUN,item['ref'])
    assert error.value.status==403
    reader.shared_snapshot['records'][0]['files']['capture.png']=item['sha256']
    (bundle/'manifest.json').write_text((bundle/'manifest.json').read_text()+' ')
    with pytest.raises(png.PNGRejected) as error:
        png.read_png(reader,RUN,item['ref'])
    assert error.value.status==422


def test_registered_file_missing_and_strict_verify_not_relaxed(synthetic,monkeypatch):
    reader,bundle,item,approved=synthetic
    monkeypatch.setattr(png,'verify_bundle',lambda path:{'bundle_status':'INVALID','missing_files':['evidence:EV9-03']})
    with pytest.raises(png.PNGRejected) as error:
        png.read_png(reader,RUN,item['ref'],approved=approved)
    assert error.value.status==422
    monkeypatch.setattr(png,'verify_bundle',lambda path:{'bundle_status':'VERIFIED'})
    (bundle/'capture.png').unlink()
    with pytest.raises(png.PNGRejected) as error:
        png.read_png(reader,RUN,item['ref'],approved=approved)
    assert error.value.status==422


def test_approval_never_crosses_mode_or_tuple(synthetic):
    reader,bundle,item,approved=synthetic
    for allowed in (set(),{('different-run',item['ref'],item['sha256'])},{(RUN,'different-ref',item['sha256'])}):
        with pytest.raises(png.PNGRejected) as error:
            png.read_png(reader,RUN,item['ref'],approved=allowed)
        assert error.value.status==403
    reader.origin='DEMO'
    reader.shared_snapshot={'records':[{'run_id':RUN,'files':{'capture.png':item['sha256']}}]}
    with pytest.raises(png.PNGRejected) as error:
        png.read_png(reader,RUN,item['ref'])
    assert error.value.status==403


def test_reparse_or_symlink_root_is_rejected(synthetic,tmp_path):
    reader,bundle,item,approved=synthetic
    outside=tmp_path/'outside'
    assert bundle.resolve().is_relative_to(tmp_path.resolve()) and outside.parent.resolve()==tmp_path.resolve()
    bundle.rename(outside)
    try:
        bundle.symlink_to(outside,target_is_directory=True)
    except OSError:
        if os.name!='nt':
            pytest.skip('Symlink permission unavailable')
        quoted_link=str(bundle).replace("'","''");quoted_target=str(outside).replace("'","''")
        command=f"New-Item -ItemType Junction -Path '{quoted_link}' -Value '{quoted_target}' | Out-Null"
        result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=20)
        if result.returncode:
            pytest.skip('Junction creation unavailable')
    with pytest.raises(png.PNGRejected) as error:
        png.read_png(reader,RUN,item['ref'],approved=approved)
    assert error.value.status==403
