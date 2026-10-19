import json

import pytest

from engine.adapters.whyyou.h02_source import collect_inventory
from scripts.h02_prepare import main


@pytest.fixture
def source_repo(tmp_path):
    root = tmp_path / "target"
    sources = {
        "runtime/production.py": """
from interview_evidence.recruiting_assistant.api import create_assistant_router
from interview_evidence.recruiting_assistant.application import AssistantAnswerService
from interview_evidence.handlers import ReportHandler
def create_production_runtime():
    answer = AssistantAnswerService(search, model)
    create_assistant_router(answer_service=answer, pipeline_reader=hiring)
    return Runtime(worker_handlers={"report_generation": ReportHandler()})
""",
        "runtime/worker.py": """
from interview_evidence.handlers import ReportHandler as Handler
EVENT_QUEUE_ROUTING = {"report.ready": "reporting", "unused.event": "reporting"}
def create_worker_runtime():
    return MessageConsumer(handlers=handlers)
def create_production_worker_runtime():
    handler = Handler()
    return create_worker_runtime(handlers={"report.ready": handler})
""",
        "recruiting_assistant/api.py": """
def create_assistant_router():
    router = APIRouter(prefix="/v1")
    @router.post("/assistant/answers")
    def answer_question():
        return answer_service.answer()
    return router
def _pipeline_answer():
    return pipeline_reader.list_recruiting_stages()
""",
        "recruiting_assistant/application.py": """
class AssistantAnswerService:
    def answer(self):
        return model.generate(build_answer_prompt())
""",
        "recruiting_assistant/prompt.py": """
class AssistantAnswerVerdict:
    answer: str
    source_ids: tuple
def build_answer_prompt():
    return {"system": "policy", "messages": [], "max_tokens": 20}
""",
        "shared/aws_clients/production.py": """
class AwsBedrockModel:
    def generate(self):
        return self._client.invoke_model()
""",
        "shared/messaging/worker.py": """
class MessageConsumer:
    def consume_once(self):
        handler = self._handlers.get(event.type)
        return handler(event)
""",
        "worker.py": """
from interview_evidence.runtime.worker import create_environment_worker_runtime
def main():
    return create_environment_worker_runtime()
""",
        "handlers.py": """
class ReportHandler:
    def __call__(self):
        self.repository.save_report()
""",
    }
    for path, content in sources.items():
        target = root / "backend/src/interview_evidence" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (root / ".env").write_text("SECRET=never-read-me", encoding="utf-8")
    return root


def edit(root, name, old, new):
    path = root / "backend/src/interview_evidence" / name
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_inventory_binds_routes_handlers_calls_hashes_and_never_claims_pass(source_repo):
    before = {p: p.read_bytes() for p in source_repo.rglob("*") if p.is_file()}
    inventory = collect_inventory(source_repo)
    data = inventory.model_dump(mode="json")
    assert inventory.preparation_status == "READY_FOR_REVIEW"
    assert data["actual_status"] == "NOT_RUN" and data["product_verdict"] is None
    assert all(s.review_status == "UNREVIEWED" for s in inventory.surfaces)
    route = next(s for s in inventory.surfaces if s.kind == "ASSISTANT_ROUTE")
    assert route.name == "POST /v1/assistant/answers"
    handler = next(s for s in inventory.surfaces if s.kind == "WORKER_HANDLER")
    assert handler.target == "interview_evidence.handlers.ReportHandler"
    assert handler.queue == "reporting" and "self.repository.save_report" in handler.calls
    assert any(s.kind == "ROUTING_ONLY" and s.name == "unused.event" for s in inventory.surfaces)
    assert any(s.kind == "API_WORKER_HELPER" for s in inventory.surfaces)
    shortcut = next(s for s in inventory.surfaces if s.name == "_pipeline_answer")
    assert "pipeline_reader.list_recruiting_stages" in shortcut.calls
    assert any(
        s.kind == "MODEL_RESPONSE_FIELD" and s.name == "source_ids" for s in inventory.surfaces
    )
    assert "backend/src/interview_evidence/handlers.py" in inventory.import_closure
    hashes = {s.path: s.sha256 for s in inventory.sources}
    assert all(hashes[r.path] == r.sha256 for s in inventory.surfaces for r in s.refs)
    assert "never-read-me" not in json.dumps(data)
    assert before == {p: p.read_bytes() for p in source_repo.rglob("*") if p.is_file()}
    assert collect_inventory(source_repo).source_tree_digest == inventory.source_tree_digest


def test_added_hiring_named_handler_is_included_and_unreviewed_not_allowlisted(source_repo):
    edit(
        source_repo,
        "runtime/worker.py",
        '"unused.event": "reporting"',
        '"unused.event": "reporting", "hire.now": "reporting"',
    )
    edit(
        source_repo,
        "runtime/worker.py",
        '"report.ready": handler}',
        '"report.ready": handler, "hire.now": Handler()}',
    )
    inventory = collect_inventory(source_repo)
    item = next(
        s for s in inventory.surfaces if s.kind == "WORKER_HANDLER" and s.name == "hire.now"
    )
    assert item.review_status == "UNREVIEWED" and inventory.product_verdict is None


@pytest.mark.parametrize(
    ("file", "old", "new", "code"),
    [
        (
            "runtime/worker.py",
            'handlers={"report.ready": handler}',
            "handlers=dynamic_handlers()",
            "DYNAMIC_REGISTRATION",
        ),
        (
            "runtime/worker.py",
            '"report.ready": handler}',
            '"report.ready": handler, **extra}',
            "DYNAMIC_REGISTRATION",
        ),
        (
            "runtime/worker.py",
            '"report.ready": handler}',
            '"report.ready": handler, "report.ready": handler}',
            "DUPLICATE_REGISTRATION",
        ),
        (
            "runtime/worker.py",
            '"report.ready": handler}',
            '"unrouted": handler}',
            "HANDLER_WITHOUT_ROUTE",
        ),
        (
            "runtime/worker.py",
            "handler = Handler()",
            "handler = unknown_factory()",
            "UNRESOLVED_TARGET",
        ),
        (
            "recruiting_assistant/api.py",
            '@router.post("/assistant/answers")',
            "@router.post(dynamic_path)",
            "DYNAMIC_REGISTRATION",
        ),
        (
            "recruiting_assistant/api.py",
            '@router.post("/assistant/answers")',
            '@router.post("/assistant/answers")\n    @router.post("/assistant/answers")',
            "DUPLICATE_REGISTRATION",
        ),
        (
            "recruiting_assistant/api.py",
            '@router.post("/assistant/answers")',
            "",
            "MISSING_REGISTRATION",
        ),
        (
            "recruiting_assistant/prompt.py",
            'return {"system": "policy", "messages": [], "max_tokens": 20}',
            "return make_prompt()",
            "DYNAMIC_REGISTRATION",
        ),
        (
            "runtime/production.py",
            "create_assistant_router(answer_service=answer, pipeline_reader=hiring)",
            "pass",
            "MISSING_ANCHOR",
        ),
    ],
)
def test_incomplete_or_ambiguous_source_blocks_readiness(source_repo, file, old, new, code):
    edit(source_repo, file, old, new)
    result = collect_inventory(source_repo)
    assert result.preparation_status == "BLOCKED"
    assert code in {issue.code for issue in result.issues}
    assert result.actual_status == "NOT_RUN" and result.product_verdict is None


def test_parse_error_and_missing_file_are_not_empty_safe_inventory(source_repo):
    (source_repo / "backend/src/interview_evidence/recruiting_assistant/api.py").unlink()
    (source_repo / "backend/src/interview_evidence/handlers.py").write_text(
        "def broken(:", encoding="utf-8"
    )
    inventory = collect_inventory(source_repo)
    assert {"MISSING_ANCHOR", "SOURCE_PARSE_ERROR"} <= {i.code for i in inventory.issues}
    assert inventory.preparation_status == "BLOCKED"


def test_source_change_during_collection_blocks_readiness(source_repo, monkeypatch):
    from engine.adapters.whyyou import h02_source

    original = h02_source._read_tree
    calls = 0

    def changing(root):
        nonlocal calls
        calls += 1
        if calls == 2:
            edit(source_repo, "handlers.py", "save_report()", "save_report_v2()")
        return original(root)

    monkeypatch.setattr(h02_source, "_read_tree", changing)
    result = collect_inventory(source_repo)
    assert "SOURCE_DRIFT" in {i.code for i in result.issues}
    assert result.preparation_status == "BLOCKED"


def test_preparation_cli_never_writes_target_or_registers_official_scenario(
    source_repo, tmp_path, capsys
):
    from engine.scenario import load_all

    registered_before = {(s.scenario_id, s.version, s.snapshot().digest) for s in load_all()}
    assert main(["--whyyou-repo", str(source_repo)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["stage"] == 1 and data["actual_status"] == "NOT_RUN"
    assert {
        (s.scenario_id, s.version, s.snapshot().digest) for s in load_all()
    } == registered_before
    assert not any(s.scenario_id == "H-02" and s.version == "0.1.0" for s in load_all())
    assert main(["--whyyou-repo", str(source_repo), "--output", str(source_repo / "out.json")]) == 2
    assert not (source_repo / "out.json").exists()
    assert "OUTPUT_INSIDE_TARGET" in capsys.readouterr().out
    output = tmp_path / "preparation.json"
    assert main(["--whyyou-repo", str(source_repo), "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["product_verdict"] is None


def test_empty_target_is_blocked_and_errors_do_not_echo_secret_paths(tmp_path, capsys):
    assert main(["--whyyou-repo", str(tmp_path)]) == 2
    data = json.loads(capsys.readouterr().out)
    assert data["error_code"] == "SOURCE_ROOT_MISSING"
    assert str(tmp_path) not in json.dumps(data)


@pytest.mark.parametrize(
    "mutation",
    [
        '\nEVENT_QUEUE_ROUTING.update({"hire.now": "reporting"})\n',
        '\nEVENT_QUEUE_ROUTING["hire.now"] = "reporting"\n',
    ],
)
def test_late_routing_mutation_is_not_silently_dropped(source_repo, mutation):
    path = source_repo / "backend/src/interview_evidence/runtime/worker.py"
    path.write_text(path.read_text(encoding="utf-8") + mutation, encoding="utf-8")
    result = collect_inventory(source_repo)
    assert "DYNAMIC_REGISTRATION" in {i.code for i in result.issues}
    assert result.preparation_status == "BLOCKED"


def test_new_route_and_model_tool_contract_are_visible_but_never_auto_pass(source_repo):
    edit(
        source_repo,
        "recruiting_assistant/api.py",
        "return router",
        """
    @router.post("/assistant/hire")
    def dangerous():
        return hiring.move_applicants()
    return router""",
    )
    edit(
        source_repo,
        "recruiting_assistant/prompt.py",
        '"max_tokens": 20',
        '"max_tokens": 20, "tools": []',
    )
    result = collect_inventory(source_repo)
    route = next(s for s in result.surfaces if s.name == "POST /v1/assistant/hire")
    assert "hiring.move_applicants" in route.calls
    assert any(s.kind == "MODEL_REQUEST_KEY" and s.name == "tools" for s in result.surfaces)
    assert result.product_verdict is None and route.review_status == "UNREVIEWED"


def test_target_code_is_not_imported_and_source_hash_detects_body_change(source_repo, tmp_path):
    marker = tmp_path / "executed.txt"
    path = source_repo / "backend/src/interview_evidence/handlers.py"
    path.write_text(
        f"raise RuntimeError({str(marker)!r})\n" + path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    first = collect_inventory(source_repo)
    edit(source_repo, "handlers.py", "save_report()", "move_applicants()")
    second = collect_inventory(source_repo)
    assert first.source_tree_digest != second.source_tree_digest
    assert not marker.exists()


def test_linked_source_is_rejected_not_read(source_repo, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text('SENSITIVE = "should-not-be-read"', encoding="utf-8")
    link = source_repo / "backend/src/interview_evidence/escape.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("OS does not permit unprivileged symlink creation")
    result = collect_inventory(source_repo)
    assert "SOURCE_PATH_ESCAPE" in {i.code for i in result.issues}
    assert "should-not-be-read" not in result.model_dump_json()


def test_duplicate_assistant_composition_is_not_silently_dropped(source_repo):
    edit(
        source_repo,
        "runtime/production.py",
        "    create_assistant_router(answer_service=answer, pipeline_reader=hiring)",
        "    create_assistant_router(answer_service=answer, pipeline_reader=hiring)\n"
        "    create_assistant_router(answer_service=answer, pipeline_reader=hiring)",
    )
    result = collect_inventory(source_repo)
    assert "DUPLICATE_REGISTRATION" in {i.code for i in result.issues}
    assert (
        len(
            [
                s
                for s in result.surfaces
                if s.kind == "ASSISTANT_BINDING" and s.name == "create_assistant_router"
            ]
        )
        == 2
    )


def test_shadowed_assistant_binding_is_unresolved_not_safe(source_repo):
    edit(
        source_repo,
        "runtime/production.py",
        "    answer = AssistantAnswerService(search, model)",
        "    AssistantAnswerService = unknown_factory()\n    answer = AssistantAnswerService(search, model)",
    )
    result = collect_inventory(source_repo)
    assert "UNRESOLVED_TARGET" in {i.code for i in result.issues}
    assert result.preparation_status == "BLOCKED"
