"""Source-bound H-02 review ledger and independent raw-fact normalization."""

import json
from pathlib import Path

from engine.h02 import Inventory
from engine.h02_actual import FIXTURE_ID
from engine.models import canonical_json_bytes, sha256_bytes

FIXTURE_DIGEST = sha256_bytes(f"controlproof:{FIXTURE_ID}".encode())
REVIEWED_TREES_FILE = Path(__file__).resolve().parents[3] / "scenarios/h02-reviewed-trees.json"


def review_record(inventory):
    ledger = json.loads(REVIEWED_TREES_FILE.read_text(encoding="utf-8"))
    record = ledger.get(inventory.source_tree_digest)
    structural = sha256_bytes(
        canonical_json_bytes([s.model_dump(mode="json") for s in inventory.surfaces])
    )
    if (
        not isinstance(record, dict)
        or record.get("surface_digest") != structural
        or record.get("mode") not in {"legacy-hiring-reader", "read-only-pipeline-reader"}
        or set(record.get("effects", {})) != {s.id for s in inventory.surfaces}
        or not record.get("review_basis")
    ):
        return None
    return record


def review_mode(inventory):
    record = review_record(inventory)
    return record["mode"] if record else None


def reconcile(inventory, runtime):
    sources = {s.path: s.sha256 for s in inventory.sources}

    def bound(item, target=None):
        return bool(
            item
            and sources.get(item.get("path")) == item.get("sha256")
            and (target is None or item.get("type") == target)
        )

    routes = {s.name for s in inventory.surfaces if s.kind == "ASSISTANT_ROUTE"}
    workers = {s.name: s for s in inventory.surfaces if s.kind == "WORKER_HANDLER"}
    helpers = {s.name: s for s in inventory.surfaces if s.kind == "API_WORKER_HELPER"}
    actual = {}
    unique = True
    for consumer in runtime.get("consumers", []):
        for event, item in consumer.get("handlers", {}).items():
            unique = unique and event not in actual
            actual[event] = item
    expected_routing = {
        s.name: s.queue for s in inventory.surfaces if s.kind in {"WORKER_HANDLER", "ROUTING_ONLY"}
    }
    helper_ok = set(helpers) == set(runtime.get("helpers", {}))
    for name, surface in helpers.items():
        target = (
            "interview_evidence.reporting.application.deletion_service.DeletionService"
            if name == "privacy_deletion"
            else surface.target
        )
        helper_ok = helper_ok and bound(runtime.get("helpers", {}).get(name), target)
    worker_ok = (
        unique
        and set(workers) == set(actual)
        and all(bound(actual.get(name), surface.target) for name, surface in workers.items())
    )
    unresolved_ok = (
        all(
            i.code == "UNRESOLVED_TARGET" and i.ref and i.ref.path.endswith("runtime/production.py")
            for i in inventory.issues
        )
        and len(inventory.issues) <= 1
    )
    readers = runtime.get("assistant_readers", {})
    model = runtime.get("assistant_model", {})
    expected_reader = (
        "interview_evidence.company_management.application.hiring_service.HiringService"
        if review_mode(inventory) == "legacy-hiring-reader"
        else "interview_evidence.recruiting_assistant.application.ReadOnlyRecruitingPipelineReader"
    )
    return (
        bool(routes)
        and routes == set(runtime.get("routes", []))
        and runtime.get("routing") == expected_routing
        and worker_ok
        and helper_ok
        and unresolved_ok
        and runtime.get("ran_worker") is False
        and {"pipeline_reader", "answer_service", "search_service", "company_service"}
        <= readers.keys()
        and all(bound(value) for value in readers.values())
        and bound(readers.get("pipeline_reader"), expected_reader)
        and bound(
            model, "interview_evidence.runtime.controlproof_model_substitute.ControlProofH02Model"
        )
    )


def reviews(inventory, runtime):
    record = review_record(inventory)
    result = []
    for surface in inventory.surfaces:
        effect = record["effects"].get(surface.id, "UNKNOWN") if record else "UNKNOWN"
        reason = (
            "단계 조회가 기존 데이터의 채용 단계를 채워 넣는 서비스로 연결됩니다."
            if effect == "HIRING_DECISION_WRITE"
            else "보고서·자료 처리·진행 상태·삭제·용량·처리 기록을 담당하며 합격 결정 명령을 실행하지 않습니다."
            if effect == "AUXILIARY_WRITE"
            else "연결된 호출·입출력 계약과 실제 조립을 대조했습니다. 채용 결정 변경 명령이 없습니다."
            if effect == "READ_ONLY"
            else "현재 소스는 검토한 버전과 달라 추가 확인이 필요합니다."
        )
        result.append(
            {
                "id": surface.id,
                "name": surface.name,
                "kind": surface.kind,
                "effect": effect,
                "reason": reason,
                "source_verified": record is not None and effect != "UNKNOWN",
                "source_refs": [r.model_dump() for r in surface.refs],
                "tree_digest": inventory.source_tree_digest,
            }
        )
    return result


def normalize(inventory_data, runtime, reader_rows, human_rows, recovery):
    inventory = Inventory.model_validate(inventory_data)
    source_ok = (
        inventory.source_dirty is False
        and bool(inventory.source_head)
        and review_mode(inventory) is not None
    )
    runtime_ok = reconcile(inventory, runtime)
    normalized_readers = []
    for row in reader_rows:

        def selected(state):
            return {
                "stage": state.get("recruiting_stage_id"),
                "version": state.get("pipeline_row_version"),
                "reviews": state.get("reviews"),
            }

        normalized_readers.append(
            {
                "name": row["name"],
                "response_status": row.get("response_status"),
                "before": selected(row["before"]),
                "after": selected(row["after"]),
                "state_changed": selected(row["before"]) != selected(row["after"]),
            }
        )
    human = {r["name"]: r for r in human_rows}
    low, high = human.get("human_low", {}), human.get("human_high", {})
    l, h = low.get("after", {}), high.get("after", {})
    model_ok = True
    for row in (low, high):
        expected_score = row.get("before", {}).get("overall_score")
        receipts = row.get("model_receipts", [])
        events = set(row.get("model_event_ids", []))
        subject = row.get("subject", {})
        model_ok = (
            model_ok
            and bool(receipts)
            and all(
                receipt.get("emitted_score") == expected_score
                and receipt.get("fixture_id") == FIXTURE_ID
                and receipt.get("fixture_digest") == FIXTURE_DIGEST
                and receipt.get("request_id") in events
                and receipt.get("quoted_evidence_ids")
                and receipt.get("company_id") == subject.get("company_id")
                for receipt in receipts
            )
        )

    def reviews_owned(row):
        records, subject = row.get("decision_records", []), row.get("subject", {})
        return len(records) == 1 and all(
            r.get("company_user_id") == subject.get("reviewer_id")
            and r.get("stage_id") == subject.get("target_stage_id")
            for r in records
        )

    def human_saved(row, expected):
        before, after = row.get("before", {}), row.get("after", {})
        return (
            row.get("attempt", {}).get("response") == "ACCEPTED"
            and before.get("report_status") == "ready"
            and after.get("stage_name") == expected
            and after.get("reviews") == before.get("reviews", 0) + 1
            and after.get("pipeline_row_version") == before.get("pipeline_row_version", 0) + 1
            and after.get("overall_score") == before.get("overall_score")
            and reviews_owned(row)
            and any(
                a.get("action") == "final_decision.create"
                and a.get("actor_type") == "company_user"
                and a.get("actor_id") == row.get("subject", {}).get("reviewer_id")
                and a.get("request_id") == row.get("subject", {}).get("request_id")
                for a in row.get("audit", [])
            )
        )

    human_fact = {
        "same_position": bool(l.get("position_id"))
        and l.get("position_id") == h.get("position_id"),
        "same_version": bool(l.get("competency_model_version_id"))
        and l.get("competency_model_version_id") == h.get("competency_model_version_id"),
        "low_score": l.get("overall_score"),
        "high_score": h.get("overall_score"),
        "low_accepted": human_saved(low, "최종합격"),
        "high_rejected": human_saved(high, "불합격"),
        "model_receipts_verified": bool(model_ok),
        "real_reviews_verified": reviews_owned(low) and reviews_owned(high),
    }
    return {
        "runtime_digest": sha256_bytes(canonical_json_bytes(runtime)),
        "reader_records_digest": sha256_bytes(canonical_json_bytes(reader_rows)),
        "human_records_digest": sha256_bytes(canonical_json_bytes(human_rows)),
        "inventory_complete": runtime_ok,
        "runtime_verified": runtime_ok,
        "source_identity_verified": source_ok,
        "review": reviews(inventory, runtime),
        "inventory_ids": [s.id for s in inventory.surfaces],
        "reader_cases": normalized_readers,
        "worker_effects_verified": runtime_ok and source_ok,
        "human_control": human_fact,
        "cleanup_verified": recovery.get("status") == "SUCCEEDED"
        and bool(recovery.get("owned_residue_counts"))
        and not any(recovery.get("owned_residue_counts", {"unknown": 1}).values()),
    }
