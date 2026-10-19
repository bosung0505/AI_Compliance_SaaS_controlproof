from copy import deepcopy

from engine.h02_actual import assess


def facts():
    return {
        "inventory_complete": True,
        "source_identity_verified": True,
        "review": [{"id": "one", "effect": "READ_ONLY", "source_verified": True}],
        "inventory_ids": ["one"],
        "runtime_verified": True,
        "reader_cases": [
            {
                "name": name,
                "response_status": 200,
                "before": {"stage": None, "version": 1, "reviews": 0},
                "after": {"stage": None, "version": 1, "reviews": 0},
            }
            for name in ("search_legacy", "answer_legacy", "stream_legacy", "answer_assigned")
        ],
        "worker_effects_verified": True,
        "human_control": {
            "same_position": True,
            "same_version": True,
            "low_score": 35,
            "high_score": 90,
            "low_accepted": True,
            "high_rejected": True,
            "model_receipts_verified": True,
            "real_reviews_verified": True,
        },
        "cleanup_verified": True,
    }


def test_complete_facts_and_partial_or_unknown_cannot_pass():
    base = facts()
    assert assess(base) == ["PASS"] * 6
    for key in (
        "inventory_complete",
        "source_identity_verified",
        "runtime_verified",
        "worker_effects_verified",
        "cleanup_verified",
    ):
        changed = deepcopy(base)
        changed[key] = False
        assert "INCONCLUSIVE" in assess(changed)
    for changed_review in (
        [],
        [{"id": "one", "effect": "UNKNOWN", "source_verified": True}],
        [{"id": "one", "effect": "READ_ONLY", "source_verified": False}],
    ):
        assert "INCONCLUSIVE" in assess({**base, "review": changed_review})


def test_exposed_write_and_actual_reader_backfill_fail_even_if_other_controls_pass():
    changed = facts()
    changed["reader_cases"][0]["after"] = {"stage": "accepted", "version": 2, "reviews": 0}
    assert assess(changed)[1] == "FAIL"
    changed = facts()
    changed["review"][0]["effect"] = "HIRING_DECISION_WRITE"
    assert "FAIL" in assess(changed)


def test_bad_rank_control_or_missing_reader_condition_is_not_a_pass():
    base = facts()
    assert assess({**base, "reader_cases": base["reader_cases"][:1]})[1] == "INCONCLUSIVE"
    for key in (
        "same_position",
        "same_version",
        "low_accepted",
        "high_rejected",
        "model_receipts_verified",
        "real_reviews_verified",
    ):
        changed = deepcopy(base)
        changed["human_control"][key] = False
        assert assess(changed)[4] != "PASS"
    changed = deepcopy(base)
    changed["human_control"]["high_score"] = 10
    assert assess(changed)[4] == "INCONCLUSIVE"
