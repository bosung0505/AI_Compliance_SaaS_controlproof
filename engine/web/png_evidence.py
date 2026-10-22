"""Strict, default-deny PNG evidence reads. No text redaction, conversion, proxy or disk-path input."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qsl

from engine.evidence import verify_bundle
from engine.presentation import load_bundle_summary

MAX_PNG_BYTES = 8_388_608
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


class PNGRejected(Exception):
    def __init__(self, status: int, kind: str, code: str):
        self.status, self.kind, self.code = status, kind, code
        super().__init__(code)


def _reject(status: int, code: str) -> None:
    kind = {400:'USAGE',403:'CONTRACT',404:'NOT_FOUND',422:'INTEGRITY'}[status]
    raise PNGRejected(status,kind,code)


def parse_ref(query: str) -> str:
    if re.search(r'%(?![0-9a-fA-F]{2})',query):
        _reject(400,'EVIDENCE_REF_INVALID')
    try:
        pairs=parse_qsl(query,keep_blank_values=True,encoding='utf-8',errors='strict')
    except (ValueError,UnicodeError):
        _reject(400,'EVIDENCE_REF_INVALID')
    if len(pairs)!=1 or pairs[0][0]!='ref':
        _reject(400,'EVIDENCE_REF_INVALID')
    value=pairs[0][1]
    if not value or len(value)>512 or any(ord(c)<32 or ord(c)==127 for c in value):
        _reject(400,'EVIDENCE_REF_INVALID')
    return value


def _guard(path: Path) -> None:
    """Reject every reparse/link component before resolving a server-selected path."""
    path=path.absolute()
    for component in (*reversed(path.parents),path):
        info=component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & 0x400:
            _reject(403,'EVIDENCE_POLICY_BLOCKED')


def _fingerprint(path: Path) -> tuple:
    value=path.stat()
    return value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns


def _safe_read(path: Path, limit: int) -> bytes:
    """Bounded single buffer. Windows handles prohibit writing/renaming and verify final DOS path."""
    path=path.absolute()
    _guard(path)
    if os.name == 'nt':
        import ctypes
        import msvcrt
        from ctypes import wintypes

        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        create=kernel.CreateFileW
        create.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        create.restype=wintypes.HANDLE
        handle=create(str(path),0x80000000,1,None,3,0x00200000|0x08000000,None)
        if handle == ctypes.c_void_p(-1).value:
            raise OSError(ctypes.get_last_error(),'Cannot open evidence')
        final=kernel.GetFinalPathNameByHandleW
        final.argtypes=[wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD]
        final.restype=wintypes.DWORD
        close=kernel.CloseHandle
        close.argtypes=[wintypes.HANDLE]
        try:
            buffer=ctypes.create_unicode_buffer(32768)
            size=final(handle,buffer,len(buffer),0)
            actual=buffer.value.removeprefix('\\\\?\\')
            if not size or size>=len(buffer) or os.path.normcase(actual)!=os.path.normcase(str(path)):
                _reject(403,'EVIDENCE_POLICY_BLOCKED')
            descriptor=msvcrt.open_osfhandle(int(handle),os.O_RDONLY|os.O_BINARY)
            handle=None  # descriptor now owns the handle
        finally:
            if handle is not None:
                close(handle)
    else:
        descriptor=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(descriptor,'rb') as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _reject(403,'EVIDENCE_POLICY_BLOCKED')
        body=stream.read(limit+1)
        after=os.fstat(stream.fileno())
        _guard(path)
        if ((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)
                != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
                # Windows path stat and handle fstat expose different ctime semantics. Compare their
                # common identity/size/mtime fields; compare ctime only within the same stat API.
                or _fingerprint(path)[:4]!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)):
            _reject(422,'INTEGRITY_FAILED')
        return body


def _relative(value: str) -> str:
    parts=PurePosixPath(value)
    if (not value or value!=parts.as_posix() or parts.is_absolute() or any(p in ('.','..') for p in value.split('/'))
            or '\\' in value or ':' in value or any(ord(c)<32 or ord(c)==127 for c in value)):
        _reject(403,'EVIDENCE_POLICY_BLOCKED')
    return value


def read_png(reader, run_id: str, ref: str, *, approved=frozenset()) -> bytes:
    """`approved` is a server-owned mode-specific tuple set, never input from a URL/form."""
    try:
        if str(uuid.UUID(run_id))!=run_id:
            _reject(404,'RUN_NOT_FOUND')
    except (ValueError,TypeError,AttributeError):
        _reject(404,'RUN_NOT_FOUND')
    root=Path(reader.run_root).absolute()
    bundle=root/run_id
    snapshot=reader.shared_snapshot if reader.origin=='ACTUAL' else None
    shared_record=None
    if snapshot is not None:
        shared_record=next((r for r in snapshot.get('records',[]) if r['run_id']==run_id),None)
        if shared_record is None:
            _reject(404,'RUN_NOT_FOUND')
    try:
        _guard(root)
        _guard(bundle)
        if not bundle.is_dir():
            _reject(404,'RUN_NOT_FOUND')
    except FileNotFoundError:
        _reject(404,'RUN_NOT_FOUND')
    try:
        manifest_path=bundle/'manifest.json'
        manifest_bytes=_safe_read(manifest_path,1_048_576)
        if len(manifest_bytes)>1_048_576:
            _reject(422,'INTEGRITY_FAILED')
        manifest=json.loads(manifest_bytes)
        files=manifest.get('files',[])
        for item in files:
            name=_relative(str(item['path']))
            _guard(bundle/name)
        # Always fresh strict verification; never use the relaxed ABORTED reader or its stat cache.
        if verify_bundle(bundle).get('bundle_status')!='VERIFIED':
            _reject(422,'INTEGRITY_FAILED')
        index=load_bundle_summary(bundle)['evidence_index']['files']
        item=next((i for i in index if i['ref']==ref),None)
        if item is None:
            _reject(404,'EVIDENCE_NOT_FOUND')
        indexed=str(item.get('relative_path') or '')
        prefix=f'<run_root>/{run_id}/'
        if not indexed.startswith(prefix):
            _reject(403,'EVIDENCE_POLICY_BLOCKED')
        relative=_relative(indexed[len(prefix):])
        metadata=next((f for f in files if f['path']==relative),None)
        if metadata is None:
            _reject(403,'EVIDENCE_POLICY_BLOCKED')
        if item.get('mime_type')!='image/png' or metadata.get('mime_type')!='image/png' or Path(relative).suffix!='.png':
            _reject(403,'EVIDENCE_POLICY_BLOCKED')
        if any(item.get(k)!=metadata.get(k) for k in ('sha256','size_bytes')):
            _reject(422,'INTEGRITY_FAILED')
        digest=metadata.get('sha256')
        if shared_record is not None:
            approved_digest=shared_record.get('files',{}).get(relative)
            if approved_digest!=digest:
                _reject(403,'EVIDENCE_POLICY_BLOCKED')
            if shared_record.get('files',{}).get('manifest.json')!=hashlib.sha256(manifest_bytes).hexdigest():
                _reject(422,'INTEGRITY_FAILED')
        elif (run_id,ref,digest) not in approved:
            _reject(403,'EVIDENCE_POLICY_BLOCKED')
        path=bundle/relative
        before=_fingerprint(path)
        body=_safe_read(path,MAX_PNG_BYTES)
        if len(body)>MAX_PNG_BYTES or not body.startswith(PNG_SIGNATURE):
            _reject(422,'PNG_CONTENT_INVALID')
        if len(body)!=metadata.get('size_bytes') or hashlib.sha256(body).hexdigest()!=digest:
            _reject(422,'INTEGRITY_FAILED')
        if before!=_fingerprint(path) or _safe_read(manifest_path,1_048_576)!=manifest_bytes:
            _reject(422,'INTEGRITY_FAILED')
        _guard(path)
        return body
    except PNGRejected:
        raise
    except (OSError,ValueError,KeyError,TypeError):
        _reject(422,'INTEGRITY_FAILED')
