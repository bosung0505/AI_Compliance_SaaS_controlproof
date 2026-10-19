import pytest

from engine.executors.h01_preparation import execute_preparation
from engine.h01 import H01Attempt, H01Case
from tests.unit.test_h01_preparation import state, subjects


class Lifecycle:
    def __init__(self, *, failed_at=None, cleanup_failure=False):
        self.failed_at = failed_at
        self.cleanup_failure = cleanup_failure
        self.cleaned = []

    def prepare(self, subject):
        if self.failed_at == "prepare":
            raise RuntimeError("private setup data")
        return True

    def observe(self, subject):
        return state(subject)

    def attempt(self, subject):
        if self.failed_at == "attempt":
            raise RuntimeError("private request data")
        return H01Attempt(
            case=subject.case,
            request_id=subject.request_id,
            response="UNAVAILABLE" if subject.case == H01Case.AI_ASSISTANT else "DENIED",
            identity_proven=subject.case != H01Case.AI_ASSISTANT,
            request_observed=subject.case != H01Case.AI_ASSISTANT,
            denial_record_present=False,
        )

    def cleanup(self, registered):
        self.cleaned = list(registered)
        if self.cleanup_failure:
            raise RuntimeError("private cleanup data")
        return True


@pytest.mark.parametrize("failed_at", ["prepare", "attempt", None])
def test_cleanup_happens_even_on_partial_setup_or_request_failure(failed_at):
    lifecycle = Lifecycle(failed_at=failed_at)
    result = execute_preparation(subjects(), lifecycle)
    assert lifecycle.cleaned == list(subjects())
    assert result.cleanup_succeeded is True
    assert result.actual_status == "NOT_RUN"
    assert len(result.observations) == 5
    assert "private" not in result.model_dump_json()
    assert result.assessment != "PASS"


def test_cleanup_failure_never_hides_original_failure_or_returns_pass():
    lifecycle = Lifecycle(failed_at="attempt", cleanup_failure=True)
    result = execute_preparation(subjects(), lifecycle)
    assert result.cleanup_succeeded is False and result.assessment == "INCONCLUSIVE"
    assert any("ATTEMPT" in code for code in result.errors)
    assert any("CLEANUP" in code for code in result.errors)


def test_foreign_or_repeated_subjects_rejected_before_lifecycle():
    lifecycle = Lifecycle()
    with pytest.raises(ValueError):
        execute_preparation(subjects()[:-1], lifecycle)
    with pytest.raises(ValueError):
        execute_preparation((subjects()[0],) * 5, lifecycle)
    assert lifecycle.cleaned == []


def test_missing_actual_ai_observation_cannot_be_relabelled_system_or_pass():
    result = execute_preparation(subjects(), Lifecycle())
    ai = next(obs for obs in result.observations if obs.subject.case == H01Case.AI_ASSISTANT)
    assert ai.response == "UNAVAILABLE" and ai.identity_proven is False
    assert result.assessment != "PASS"


def test_foreign_baseline_never_reaches_a_mutating_request():
    from uuid import UUID

    class ForeignState(Lifecycle):
        def observe(self, subject):
            return state(subject, company_id=UUID(int=500))

        def attempt(self, subject):
            pytest.fail("foreign baseline must not reach attempt")

    lifecycle = ForeignState()
    result = execute_preparation(subjects(), lifecycle)
    assert result.assessment == "INCONCLUSIVE" and len(lifecycle.cleaned) == 5


def test_attempt_case_request_mismatch_is_not_accepted_as_evidence():
    from uuid import UUID

    class WrongRequest(Lifecycle):
        def attempt(self, subject):
            return super().attempt(subject).model_copy(update={"request_id": UUID(int=999)})

    result = execute_preparation(subjects(), WrongRequest())
    assert result.assessment == "INCONCLUSIVE"
    assert len(result.errors) == 5
