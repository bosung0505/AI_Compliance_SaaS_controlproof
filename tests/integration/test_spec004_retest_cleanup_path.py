"""ID-004-37 — a Spec 004 RESTORE_FAILED parent is retestable after cleanup-confirm.

`RestoreBlockStore.confirm_cleanup` writes the confirmation to `run_root/blocks/maintenance/<run_id>.json`; Spec 004 retest
must read it from the same block store (as the Spec 003 path does), and must still refuse without that record.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from engine.lifecycle import RestoreBlockStore
from engine.retest import RetestError, prepare_retest
from tests.integration.test_spec004_retest_lineage import _environment, _runner

RESTORE_FAILURE = {
    "E-01": {"removal_indicator": "score_null", "restore_mismatch": True},
    "E-02": {"teardown_fails": True},
}
SUBJECT = {"E-01": "e01-citation-evidence", "E-02": "e02-scoring-freeze"}
TARGET = "whyyou-local"


def _restore_failed_parent(root, scenario):
    runner = _runner(root, scenario, RESTORE_FAILURE[scenario])
    run, _, bundle = runner.execute(runner.preflight(TARGET))
    assert run.state.value == "RESTORE_FAILED"
    assert RestoreBlockStore(root).blocked(TARGET, SUBJECT[scenario])
    return run, bundle


def _prepare(root, bundle, scenario):
    child = _runner(root, scenario, {}, commit="b" * 40)
    readiness = child.preflight(TARGET)
    return prepare_retest(
        bundle,
        child_run_id=uuid4(),
        child_target=readiness.target_snapshot,
        child_scenario_version=child.scenario.version,
        child_scenario_digest=child.scenario.snapshot().digest,
        child_profile=child.scenario.execution_profile,
        child_environment=_environment(child),
    )


@pytest.mark.parametrize("scenario", ["E-01", "E-02"])
def test_confirmed_cleanup_allows_retest_preparation(tmp_path, scenario) -> None:
    run, bundle = _restore_failed_parent(tmp_path, scenario)
    record = RestoreBlockStore(tmp_path).confirm_cleanup(
        TARGET, SUBJECT[scenario], evidence_sha256="0" * 64, target_safe=True
    )
    assert record["blocked_run_id"] == str(run.run_id)
    assert (tmp_path / "blocks" / "maintenance" / f"{run.run_id}.json").is_file()
    parent_run, _, records = _prepare(tmp_path, bundle, scenario)
    assert parent_run.run_id == run.run_id
    assert records["link"]["parent_run_id"] == str(run.run_id)


@pytest.mark.parametrize("scenario", ["E-01", "E-02"])
def test_retest_is_refused_without_a_block_store_confirmation(tmp_path, scenario) -> None:
    run, bundle = _restore_failed_parent(tmp_path, scenario)
    with pytest.raises(RetestError, match="unresolved restore block"):
        _prepare(tmp_path, bundle, scenario)
    # The block disappears without cleanup-confirm, and a record exists only at the old run_root/maintenance path.
    RestoreBlockStore(tmp_path).path_for(TARGET, SUBJECT[scenario]).unlink()
    legacy = tmp_path / "maintenance" / f"{run.run_id}.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"blocked_run_id": str(run.run_id)}), encoding="utf-8")
    with pytest.raises(RetestError, match="never confirmed"):
        _prepare(tmp_path, bundle, scenario)
