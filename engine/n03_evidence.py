"""N-03 semantic verification in addition to the common SHA/redaction/link scanner (evidence-bundle-v9.md)."""

from engine.executors.spec009 import COMMON_FILES
from engine.spec009_evidence import SemanticMismatch, verify_common
from engine.spec009_evidence import verify_links as _verify_links

REQUIRED_FILES = set(COMMON_FILES) | {
    "n03-scope.json",
    "n03-lanes.json",
    "n03-stale-attempt.json",
    "n03-stale-before.json",
    "n03-stale-after.json",
    "n03-latest-commit.json",
    "n03-past-before.json",
    "n03-past-after.json",
}


def verify_links(directory, evidence, registered, artifacts, result):
    from engine.executors.n03 import LINKS

    _verify_links(directory, evidence, registered, artifacts, result, LINKS)


def _rebuild(read, recovery):
    from engine import n03

    return n03.assertions_for(
        read("n03-stale-attempt.json"),
        read("n03-stale-before.json"),
        read("n03-stale-after.json"),
        read("n03-latest-commit.json"),
        read("n03-past-before.json"),
        read("n03-past-after.json"),
        recovery,
    )


def verify_facts(directory, manifest, result):
    from engine import n03
    from engine.executors.n03 import PROFILE, UNVERIFIED_SCOPE
    from engine.executors.spec009 import subject_identity

    try:
        facts = verify_common(
            directory,
            manifest,
            profile=PROFILE,
            judge=n03,
            unverified_scope=UNVERIFIED_SCOPE,
            scope_file="n03-scope.json",
            lane_ids=("stale", "past"),
            rebuild=_rebuild,
        )
        read, subjects = facts["read"], facts["subjects"]
        lanes = read("n03-lanes.json")
        if lanes["lanes"] != [lane.model_dump(mode="json") for lane in subjects]:
            raise SemanticMismatch("n03-lanes.json")
        stale = subject_identity(subjects[0].model_dump(mode="json"))
        attempt, latest = read("n03-stale-attempt.json"), read("n03-latest-commit.json")
        if attempt["subject"] != stale:
            raise SemanticMismatch("n03-stale-attempt.json")
        if latest["subject"] != stale:
            raise SemanticMismatch("n03-latest-commit.json")
        current, submitted = attempt["current"], attempt["submitted"]
        if (current is None) != (submitted is None) or (
            current is not None
            and (submitted["version"] == current["version"] or submitted["digest"] == current["digest"])
        ):
            raise SemanticMismatch("n03-stale-attempt.json")
    except SemanticMismatch as mismatch:
        result["mismatched_files"].append(f"{mismatch.name}:semantic-evidence")
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        result["mismatched_files"].append("n03-stale-attempt.json:semantic-evidence")
