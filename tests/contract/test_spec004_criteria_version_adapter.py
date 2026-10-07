"""T052 — criteria-version and scoring-source adapters (contracts/whyyou-spec004-adapter.md, ID-004-20).

RED until T055 creates `engine/adapters/whyyou/criteria_versions.py`. The product API omits criterion IDs from its
version view, so criterion IDs and the other-positions digest come from a read-only DB connection.
"""

from __future__ import annotations

import json
from importlib import import_module
from uuid import uuid4

import httpx

from engine.adapters.base import AdapterResult
from engine.judges.e02_scoring import PINNED_SOURCES
from engine.models import CriteriaVersionSnapshot
from seeds.spec004_subjects import e02_version_body

POSITION, OTHER = str(uuid4()), str(uuid4())
V1, V2, V3 = str(uuid4()), str(uuid4()), str(uuid4())


def module():
    return import_module("engine.adapters.whyyou.criteria_versions")


def _view(version_id, number, status, key="v1"):
    body = e02_version_body(key)
    return body | {
        "competency_model_version_id": version_id,
        "position_id": POSITION,
        "version_number": number,
        "status": status,
        "row_version": 2 if status == "published" else 1,
        "published_at": "2026-10-07T09:00:00+00:00" if status == "published" else None,
    }


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return list(self._rows)


class _Read:
    def __init__(self, versions):
        self.versions = versions
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        self.statements.append(sql)
        if "FROM evaluation_criteria" in sql:
            version = str(params["version_id"])
            return _Result(
                [
                    {"criterion_id": str(uuid4()) if version == "x" else f"{version[:-2]}{index:02d}",
                     "code": code, "weight": weight}
                    for index, (code, weight) in enumerate((("E02-A", 25.0), ("E02-B", 75.0)))
                ]
            )
        if "FROM competency_model_versions" in sql:
            return _Result(self.versions)
        raise AssertionError(sql)


def _adapter(settings, handler, versions=()):
    client = httpx.Client(base_url="http://whyyou.test", transport=httpx.MockTransport(handler))
    read = _Read(list(versions))
    adapter = module().WhyYouCriteriaVersionAdapter(
        settings, http_client=client, read_factory=lambda: read
    )
    return adapter, read


def test_create_posts_the_body_with_idempotency_and_company_token(settings) -> None:
    seen = {}

    def handler(request):
        seen.update(
            path=request.url.path,
            body=json.loads(request.content),
            key=request.headers.get("Idempotency-Key"),
            auth=request.headers.get("Authorization"),
        )
        return httpx.Response(201, json=_view(V1, 1, "draft"))

    adapter, _ = _adapter(settings, handler)
    key = "controlproof-e02-v1-create"
    result = adapter.create_version(position_id=POSITION, body=e02_version_body("v1"), idempotency_key=key)
    assert result.ok and result.code == "VERSION_CREATED"
    assert result.data == {"version_id": V1, "row_version": 1, "version_number": 1}
    assert seen["path"] == f"/v1/positions/{POSITION}/competency-model-versions"
    assert seen["key"] == key and seen["auth"].startswith("Bearer ")
    body = seen["body"]
    assert body["interview_duration_minutes"] == 30 and body["job_requirements"]
    assert sum(item["weight"] for item in body["criteria"]) == 100
    assert sum(body["axis_weights"].values()) == 100
    assert all("[controlproof-spec004 mode=VALID" in item["description"] for item in body["criteria"])
    assert settings.whyyou_company_token not in repr(result)


def test_create_422_is_a_sanitized_rejection(settings) -> None:
    def handler(request):
        return httpx.Response(422, json={"detail": {"code": "CRITERION_WEIGHTS_INVALID", "message": "x"}})

    adapter, _ = _adapter(settings, handler)
    result = adapter.create_version(position_id=POSITION, body={}, idempotency_key="k" * 16)
    assert not result.ok and result.code == "VERSION_CREATE_REJECTED"
    assert result.data == {"status_code": 422, "detail_code": "CRITERION_WEIGHTS_INVALID"}


def test_publish_sends_if_match_version_and_maps_conflict(settings) -> None:
    seen = []

    def handler(request):
        seen.append((request.url.path, request.headers.get("If-Match-Version")))
        if len(seen) == 1:
            return httpx.Response(200, json=_view(V1, 1, "published"))
        return httpx.Response(409, json={"detail": "stale"})

    adapter, _ = _adapter(settings, handler)
    ok = adapter.publish_version(version_id=V1, row_version=1, idempotency_key="k" * 16)
    assert ok.ok and ok.code == "VERSION_PUBLISHED" and ok.data["row_version"] == 2
    assert seen[0] == (f"/v1/competency-model-versions/{V1}/publish", "1")
    conflict = adapter.publish_version(version_id=V1, row_version=1, idempotency_key="k" * 16)
    assert not conflict.ok and conflict.code == "VERSION_PUBLISH_CONFLICT"


def test_latest_published_is_the_highest_published_version(settings) -> None:
    def handler(request):
        return httpx.Response(
            200,
            json={"items": [_view(V1, 1, "published"), _view(V2, 2, "published", "v2"), _view(V3, 3, "draft", "v2")]},
        )

    rows = [{"position_id": OTHER, "competency_model_version_id": str(uuid4()), "version_number": 1,
             "status": "published", "row_version": 2}]
    adapter, read = _adapter(settings, handler, rows)
    snapshot = adapter.latest_published(position_id=POSITION, snapshot_phase="V2_PUBLISHED")
    assert isinstance(snapshot, CriteriaVersionSnapshot)
    assert str(snapshot.competency_model_version_id) == V2 and snapshot.version_number == 2
    assert {item.code: item.weight for item in snapshot.criteria} == {"E02-A": 25.0, "E02-B": 75.0}
    assert snapshot.axis_weights["correctness"] == 30.0
    assert any("FROM evaluation_criteria" in sql for sql in read.statements)


def test_other_positions_digest_ignores_excluded_positions(settings) -> None:
    def handler(request):
        raise AssertionError("no API call")

    base = [{"position_id": OTHER, "competency_model_version_id": "a", "version_number": 1,
             "status": "published", "row_version": 2}]
    mine = {"position_id": POSITION, "competency_model_version_id": "b", "version_number": 1,
            "status": "draft", "row_version": 1}
    first, _ = _adapter(settings, handler, base)
    second, _ = _adapter(settings, handler, [*base, mine])
    a = first.other_positions_digest(excluded_position_ids=(POSITION,))
    b = second.other_positions_digest(excluded_position_ids=(POSITION,))
    assert a.ok and a.data["digest"] == b.data["digest"]
    changed, _ = _adapter(settings, handler, [base[0] | {"row_version": 3}])
    assert changed.other_positions_digest(excluded_position_ids=(POSITION,)).data["digest"] != a.data["digest"]


def test_scoring_source_reads_pinned_blob_shas(settings) -> None:
    calls = []

    def git(args):
        calls.append(args)
        path = args[-1].split(":", 1)[1]
        return next(item["blob_sha"] for item in PINNED_SOURCES if item["path"] == path)

    adapter = module().WhyYouScoringSourceAdapter(settings, git=git)
    result = adapter.read_blob_shas()
    assert result.ok
    assert result.data["blob_shas"] == {item["path"]: item["blob_sha"] for item in PINNED_SOURCES}
    assert all(args[:2] == ["rev-parse", "--verify"] for args in calls)

    def broken(_args):
        raise OSError("git missing")

    failed = module().WhyYouScoringSourceAdapter(settings, git=broken).read_blob_shas()
    assert isinstance(failed, AdapterResult) and failed.code == "SCORING_SOURCE_UNAVAILABLE"
