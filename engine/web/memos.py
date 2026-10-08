"""Fix memos kept outside the sealed record (FR-024, R-008).

`<memo dir>/<run_id>.jsonl`, append only (no update or delete). A memo never touches the bundle or its verify result.
The strict (v2) scanner runs before anything is written.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.evidence import scan_bytes_strict

SCHEMA_VERSION = "controlproof.fix-memo.v1"
AUTHOR_MAX = 80
TEXT_MAX = 2000


class MemoRejected(ValueError):
    """The memo was not stored; the message never repeats the rejected content."""


class MemoStore:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self._lock = threading.Lock()

    def add(self, run_id: str, *, author: str, text: str) -> dict[str, Any]:
        run_id = _run_id(run_id)
        author, text = (author or "").strip(), (text or "").strip()
        if not 1 <= len(author) <= AUTHOR_MAX:
            raise MemoRejected(f"작성자는 1~{AUTHOR_MAX}자여야 합니다.")
        if not 1 <= len(text) <= TEXT_MAX:
            raise MemoRejected(f"메모는 1~{TEXT_MAX}자여야 합니다.")
        findings = scan_bytes_strict(json.dumps({"author": author, "text": text}, ensure_ascii=False).encode("utf-8"))
        if findings:
            rules = ", ".join(sorted(findings))
            raise MemoRejected(f"경로·토큰·개인정보로 보이는 내용이 있어 저장하지 않았습니다({rules}).")
        memo = {
            "schema_version": SCHEMA_VERSION,
            "memo_id": str(uuid.uuid4()),
            "run_id": run_id,
            "author": author,
            "created_at": datetime.now(UTC).isoformat(),
            "text": text,
        }
        line = json.dumps(memo, ensure_ascii=False, sort_keys=True) + "\n"
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            with (self.directory / f"{run_id}.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(line)
        return memo

    def list(self, run_id: str) -> list[dict[str, Any]]:
        try:
            path = self.directory / f"{_run_id(run_id)}.jsonl"
            lines = path.read_text(encoding="utf-8").splitlines()
        except (MemoRejected, OSError):
            return []
        return [json.loads(line) for line in lines if line.strip()]


def _run_id(value: str) -> str:
    try:
        parsed = uuid.UUID(str(value))
    except ValueError as exc:
        raise MemoRejected("대상 실행 ID가 올바르지 않습니다.") from exc
    if str(parsed) != str(value):
        raise MemoRejected("대상 실행 ID가 올바르지 않습니다.")
    return str(parsed)
