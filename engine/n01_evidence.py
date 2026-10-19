"""N-01 semantic verification in addition to the common SHA/redaction/link scanner (evidence-bundle-v9.md).

Captures are not canonical files: a lane that never reached the consent step has none, which the judge reads
as INCONCLUSIVE. ``verify_facts`` instead checks that every capture record matches a sealed PNG and vice versa.
"""

from engine.executors.spec009 import COMMON_FILES
from engine.spec009_evidence import SemanticMismatch, verify_common
from engine.spec009_evidence import verify_links as _verify_links

REQUIRED_FILES = set(COMMON_FILES) | {
    "n01-scope.json",
    "n01-lanes.json",
    "n01-measurements.json",
    "n01-policy-identifiers.json",
}


def verify_links(directory, evidence, registered, artifacts, result):
    from engine.executors.n01 import LINKS

    _verify_links(directory, evidence, registered, artifacts, result, LINKS)


def _rebuild(read, recovery):
    from engine import n01

    return n01.assertions_for(read("n01-measurements.json"), read("n01-policy-identifiers.json"), recovery)


def verify_facts(directory, manifest, result):
    from engine import n01
    from engine.executors.n01 import PROFILE, UNVERIFIED_SCOPE, capture_name, lane_summary
    from engine.executors.spec009 import subject_identity

    try:
        facts = verify_common(
            directory,
            manifest,
            profile=PROFILE,
            judge=n01,
            unverified_scope=UNVERIFIED_SCOPE,
            scope_file="n01-scope.json",
            lane_ids=("pc", "mobile"),
            rebuild=_rebuild,
        )
        read, subjects = facts["read"], facts["subjects"]
        records = read("n01-measurements.json")
        if [record["lane"] for record in records] != ["pc", "mobile"]:
            raise SemanticMismatch("n01-measurements.json")
        for record, lane in zip(records, subjects, strict=True):
            items = [item["item_id"] for item in record["items"]]
            if record["subject"] != subject_identity(lane.model_dump(mode="json")) or (
                items and sorted(items) != sorted(n01.NOTICE_ITEMS)
            ):
                raise SemanticMismatch("n01-measurements.json")
        if read("n01-lanes.json") != [lane_summary(record) for record in records]:
            raise SemanticMismatch("n01-lanes.json")
        sealed = {row["path"]: row for row in manifest.get("files", []) if row.get("path", "").endswith(".png")}
        expected = {}
        for record in records:
            capture = record["capture"]
            if capture is None:
                continue
            name = capture_name(record["lane"])
            row = sealed.get(name)
            if (
                capture["file"] != name
                or row is None
                or row.get("mime_type") != "image/png"
                or row.get("sha256") != capture["sha256"]
                or row.get("size_bytes") != capture["bytes"]
                or not row.get("size_bytes")
                or not (directory / name).is_file()
            ):
                raise SemanticMismatch(name)
            expected[name] = row
        if set(sealed) != set(expected):
            raise SemanticMismatch("n01-measurements.json")
        identifiers = read("n01-policy-identifiers.json")
        if [(row["lane"], row["subject_ref"]) for row in identifiers] != [
            (lane.lane_id.value, lane.subject_ref) for lane in subjects
        ]:
            raise SemanticMismatch("n01-policy-identifiers.json")
    except SemanticMismatch as mismatch:
        result["mismatched_files"].append(f"{mismatch.name}:semantic-evidence")
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        result["mismatched_files"].append("n01-measurements.json:semantic-evidence")
