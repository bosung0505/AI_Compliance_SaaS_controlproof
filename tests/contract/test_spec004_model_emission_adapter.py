"""T032 — fixture emission receipt reader (contracts/whyyou-spec004-fixture.md "Emission receipt").

RED until T038 creates `engine/adapters/whyyou/model_emission.py`.
"""

from __future__ import annotations

import json
from dataclasses import replace
from importlib import import_module

from engine.adapters.base import AdapterResult
from tests.fixtures import spec004 as fx


def _adapter(settings, root):
    module = import_module("engine.adapters.whyyou.model_emission")
    return module.WhyYouModelEmissionAdapter(replace(settings, observer_root=root))


def _write(root, receipt):
    directory = root / "model"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{receipt['receipt_id']}.json").write_text(json.dumps(receipt), encoding="utf-8")


def test_reads_only_the_requested_criteria(settings, tmp_path) -> None:
    mine, other = str(fx.sid("c", "mine")), str(fx.sid("c", "other"))
    _write(tmp_path, fx.emission_receipt(mine, mode="EMPTY", quoted=[]))
    _write(tmp_path, fx.emission_receipt(other))
    receipts = _adapter(settings, tmp_path).read_emissions(criterion_ids=(mine,))
    assert [str(item.criterion_id) for item in receipts] == [mine]
    assert receipts[0].mode.value == "EMPTY"


def test_absent_directory_is_an_empty_read(settings, tmp_path) -> None:
    assert _adapter(settings, tmp_path).read_emissions(criterion_ids=("x",)) == ()


def test_malformed_receipt_is_unavailable(settings, tmp_path) -> None:
    criterion = str(fx.sid("c", "bad"))
    _write(tmp_path, fx.emission_receipt(criterion, fixture_id="h03-report-v1"))
    result = _adapter(settings, tmp_path).read_emissions(criterion_ids=(criterion,))
    assert isinstance(result, AdapterResult) and result.code == "EMISSION_RECEIPTS_UNAVAILABLE"


def test_ignores_temporary_files(settings, tmp_path) -> None:
    criterion = str(fx.sid("c", "tmp"))
    (tmp_path / "model").mkdir()
    (tmp_path / "model" / "x.tmp").write_text("{", encoding="utf-8")
    _write(tmp_path, fx.emission_receipt(criterion))
    assert len(_adapter(settings, tmp_path).read_emissions(criterion_ids=(criterion,))) == 1
