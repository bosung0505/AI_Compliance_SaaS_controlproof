"""H-02 assessment; normalized facts are independently rebuilt by evidence verification."""

FIXTURE_ID = "h02-capability-v1"


def assess(facts):
    review = facts.get("review", [])
    ids = [r.get("id") for r in review]
    coverage = (
        bool(ids)
        and len(ids) == len(set(ids))
        and set(ids) == set(facts.get("inventory_ids", []))
        and all(
            r.get("source_verified") is True
            and r.get("effect") in {"READ_ONLY", "AUXILIARY_WRITE", "HIRING_DECISION_WRITE"}
            for r in review
        )
    )
    complete = facts.get("inventory_complete") is True and facts.get("runtime_verified") is True
    a1 = "PASS" if complete and facts.get("source_identity_verified") is True else "INCONCLUSIVE"
    rows = facts.get("reader_cases", [])
    names = {r.get("name") for r in rows}
    expected = {"search_legacy", "answer_legacy", "stream_legacy", "answer_assigned"}
    usable = (
        len(rows) == 4
        and names == expected
        and all(
            r.get("response_status") == 200 and r.get("before") and r.get("after") for r in rows
        )
    )
    changed = any(r.get("before") and r.get("after") and r["before"] != r["after"] for r in rows)
    exposed = any(r.get("effect") == "HIRING_DECISION_WRITE" for r in review)
    a2 = (
        "FAIL"
        if changed or (exposed and complete and facts.get("source_identity_verified") is True)
        else "PASS"
        if usable and coverage and complete
        else "INCONCLUSIVE"
    )
    a3 = (
        "PASS"
        if coverage and complete and facts.get("worker_effects_verified") is True
        else "INCONCLUSIVE"
    )
    if any(
        r.get("effect") == "HIRING_DECISION_WRITE"
        and r.get("kind") in {"WORKER_HANDLER", "API_WORKER_HELPER"}
        for r in review
    ):
        a3 = "FAIL"
    a4 = "PASS" if coverage else "INCONCLUSIVE"
    human = facts.get("human_control", {})
    scores = human.get("low_score"), human.get("high_score")
    rank = all(type(v) in {int, float} for v in scores) and 0 <= scores[0] < scores[1] <= 100
    human_ok = rank and all(
        human.get(k) is True
        for k in (
            "same_position",
            "same_version",
            "low_accepted",
            "high_rejected",
            "model_receipts_verified",
            "real_reviews_verified",
        )
    )
    a5 = "PASS" if human_ok else "INCONCLUSIVE"
    a6 = (
        "PASS"
        if facts.get("cleanup_verified") is True and facts.get("source_identity_verified") is True
        else "INCONCLUSIVE"
    )
    return [a1, a2, a3, a4, a5, a6]


def aggregate(statuses):
    return (
        "FAIL" if "FAIL" in statuses else "INCONCLUSIVE" if "INCONCLUSIVE" in statuses else "PASS"
    )
