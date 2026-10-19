"""Read-only AST inventory, not a runtime attestation or a security verdict."""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
from pathlib import Path

from engine.h02 import (
    Inventory,
    Issue,
    PreparationError,
    SourceFile,
    SourceRef,
    Surface,
    source_digest,
)

PREFIX = "backend/src/interview_evidence/"
PACKAGE = "interview_evidence."
ANCHORS = (
    "runtime/production.py",
    "runtime/worker.py",
    "recruiting_assistant/api.py",
    "recruiting_assistant/application.py",
    "recruiting_assistant/prompt.py",
    "shared/aws_clients/production.py",
    "shared/messaging/worker.py",
    "worker.py",
)


def _linked(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _read_tree(repo: Path) -> tuple[dict[str, bytes], list[Issue]]:
    source = repo / PREFIX
    if not source.is_dir():
        raise PreparationError("SOURCE_ROOT_MISSING")
    if any(_linked(p) for p in (repo / "backend", repo / "backend/src", source)):
        raise PreparationError("SOURCE_PATH_ESCAPE")
    result: dict[str, bytes] = {}
    issues: list[Issue] = []
    for directory, subdirs, names in os.walk(
        source,
        followlinks=False,
        onerror=lambda _: issues.append(Issue(code="SOURCE_UNREADABLE")),
    ):
        for name in list(subdirs):
            candidate = Path(directory) / name
            if _linked(candidate):
                subdirs.remove(name)
                issues.append(Issue(code="SOURCE_PATH_ESCAPE"))
        for name in sorted(names):
            if not name.endswith(".py"):
                continue
            path = Path(directory) / name
            if _linked(path) or not path.resolve().is_relative_to(source):
                issues.append(Issue(code="SOURCE_PATH_ESCAPE"))
                continue
            try:
                if path.stat().st_size > 2_000_000 or len(result) >= 5000:
                    raise PreparationError("SOURCE_LIMIT_EXCEEDED")
                result[path.relative_to(repo).as_posix()] = path.read_bytes()
            except OSError:
                issues.append(Issue(code="SOURCE_UNREADABLE"))
    if not result:
        raise PreparationError("SOURCE_TREE_EMPTY")
    return result, issues


def _symbol(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _symbol(node.value) + "." + node.attr
    if isinstance(node, ast.Call):
        return _symbol(node.func)
    return "<dynamic>"


def _module(path: str) -> str:
    name = PACKAGE + path.removeprefix(PREFIX).removesuffix(".py").replace("/", ".")
    return name.removesuffix(".__init__")


class SourceInventory:
    def __init__(self, data: dict[str, bytes], issues: list[Issue]) -> None:
        self.data = data
        self.issues = issues
        self.trees: dict[str, ast.Module] = {}
        self.modules = {_module(path): path for path in data}
        self.surfaces: list[Surface] = []
        for path, content in sorted(data.items()):
            try:
                self.trees[path] = ast.parse(content.decode("utf-8-sig"))
            except (SyntaxError, UnicodeError, ValueError, RecursionError):
                self.issue("SOURCE_PARSE_ERROR", path)

    def ref(self, path: str, node: ast.AST | None = None) -> SourceRef:
        return SourceRef(
            path=path,
            sha256=hashlib.sha256(self.data[path]).hexdigest(),
            line=getattr(node, "lineno", 1),
            end_line=getattr(node, "end_lineno", 1),
        )

    def issue(self, code: str, path: str | None = None, node: ast.AST | None = None) -> None:
        self.issues.append(
            Issue(code=code, ref=self.ref(path, node) if path in self.data else None)
        )

    def definition(self, path: str, name: str) -> ast.AST | None:
        body = getattr(self.trees.get(path), "body", [])
        found = None
        for part in name.split("."):
            matches = [
                n
                for n in body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and n.name == part
            ]
            if len(matches) != 1:
                return None
            found = matches[0]
            body = found.body
        return found

    def require(self, short_path: str, name: str) -> tuple[str, ast.AST | None]:
        path = PREFIX + short_path
        node = self.definition(path, name)
        if node is None:
            self.issue("MISSING_ANCHOR", path)
        return path, node

    def imports(self, path: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for node in ast.walk(self.trees[path]):
            if isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = _module(path).split(".")
                    if not path.endswith("/__init__.py"):
                        parts.pop()
                    base = ".".join(parts[: len(parts) - node.level + 1] + ([base] if base else []))
                for alias in node.names:
                    result[alias.asname or alias.name] = base + "." + alias.name
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result[alias.asname or alias.name.split(".")[0]] = (
                        alias.name if alias.asname else alias.name.split(".")[0]
                    )
        return result

    def resolved(self, path: str, node: ast.AST, scope: ast.AST, seen: tuple[str, ...] = ()) -> str:
        if isinstance(node, ast.Call):
            return self.resolved(path, node.func, scope, seen)
        name = _symbol(node)
        if name in seen:
            return "<unresolved>"
        if isinstance(node, ast.Name):
            values = [
                n.value
                for n in ast.walk(scope)
                if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
            ]
            if len(values) == 1:
                return self.resolved(path, values[0], scope, (*seen, name))
            if len(values) > 1:
                return "<unresolved>"
        head, *tail = name.split(".")
        imported = self.imports(path).get(head)
        if imported:
            return ".".join([imported, *tail])
        if self.definition(path, name) is not None:
            return _module(path) + "." + name
        return "<unresolved>"

    def target_ref(self, target: str) -> tuple[str, ast.AST] | None:
        for module, path in sorted(self.modules.items(), key=lambda p: -len(p[0])):
            if target.startswith(module + "."):
                node = self.definition(path, target[len(module) + 1 :])
                return (path, node) if node is not None else None
        return None

    def add(
        self,
        kind: str,
        name: str,
        path: str,
        node: ast.AST,
        target: str = "",
        queue: str | None = None,
    ) -> None:
        refs = [self.ref(path, node)]
        definition = self.target_ref(target)
        calls = ()
        if definition:
            target_path, target_node = definition
            refs.append(self.ref(target_path, target_node))
            calls = tuple(
                sorted({_symbol(n.func) for n in ast.walk(target_node) if isinstance(n, ast.Call)})
            )
        else:
            calls = tuple(
                sorted({_symbol(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)})
            )
        bindings = ()
        if isinstance(node, ast.Call):
            bindings = tuple((k.arg or "<expanded>", _symbol(k.value)) for k in node.keywords)
        key = f"{kind}:{name}"
        if any(s.id == key for s in self.surfaces):
            self.issue("DUPLICATE_REGISTRATION", path, node)
            key += f":duplicate:{len(self.surfaces)}"
        self.surfaces.append(
            Surface(
                id=key,
                kind=kind,
                name=name,
                target=target,
                queue=queue,
                refs=tuple(refs),
                calls=calls,
                bindings=bindings,
            )
        )

    def literal_map(self, path: str, node: ast.AST | None) -> dict[str, ast.AST]:
        if not isinstance(node, ast.Dict):
            self.issue("DYNAMIC_REGISTRATION", path, node)
            return {}
        result = {}
        for key, value in zip(node.keys, node.values, strict=True):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                self.issue("DYNAMIC_REGISTRATION", path, node)
            elif key.value in result:
                self.issue("DUPLICATE_REGISTRATION", path, key)
            else:
                result[key.value] = value
        return result

    def maps_from_calls(
        self, path: str, scope: ast.AST, function: str, keyword: str
    ) -> dict[str, ast.AST]:
        calls = [
            n for n in ast.walk(scope) if isinstance(n, ast.Call) and _symbol(n.func) == function
        ]
        if len(calls) != 1:
            self.issue("MISSING_ANCHOR" if not calls else "DYNAMIC_REGISTRATION", path, scope)
        result = {}
        for call in calls:
            values = [k.value for k in call.keywords if k.arg == keyword]
            if len(values) != 1:
                self.issue("DYNAMIC_REGISTRATION", path, call)
            else:
                result.update(self.literal_map(path, values[0]))
        return result

    def assistant(self) -> None:
        path, scope = self.require("recruiting_assistant/api.py", "create_assistant_router")
        if scope is not None:
            prefixes = [
                k.value.value
                for n in ast.walk(scope)
                if isinstance(n, ast.Call) and _symbol(n.func) == "APIRouter"
                for k in n.keywords
                if k.arg == "prefix"
                and isinstance(k.value, ast.Constant)
                and isinstance(k.value.value, str)
            ]
            if len(prefixes) != 1:
                self.issue("DYNAMIC_REGISTRATION", path, scope)
            prefix = prefixes[0] if len(prefixes) == 1 else "<unknown>"
            routes = 0
            for node in ast.walk(scope):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        if not isinstance(decorator, ast.Call) or not _symbol(
                            decorator.func
                        ).startswith("router."):
                            continue
                        method = _symbol(decorator.func).removeprefix("router.").upper()
                        if (
                            method
                            not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
                            or not decorator.args
                            or not isinstance(decorator.args[0], ast.Constant)
                            or not isinstance(decorator.args[0].value, str)
                        ):
                            self.issue("DYNAMIC_REGISTRATION", path, decorator)
                            continue
                        self.add(
                            "ASSISTANT_ROUTE",
                            f"{method} {prefix}{decorator.args[0].value}",
                            path,
                            node,
                            _module(path) + ".create_assistant_router." + node.name,
                        )
                        routes += 1
                if isinstance(node, ast.Call) and _symbol(node.func).startswith("router.add_"):
                    self.issue("DYNAMIC_REGISTRATION", path, node)
            if not routes:
                self.issue("MISSING_REGISTRATION", path, scope)

        path, scope = self.require("runtime/production.py", "create_production_runtime")
        if scope is not None:
            expected = {"create_assistant_router", "AssistantAnswerService"}
            interesting = expected | {
                "AssistantSearchService",
                "ReportSearchProjector",
                "resolve_controlproof_assistant",
            }
            for node in ast.walk(scope):
                if isinstance(node, ast.Call) and _symbol(node.func) in interesting:
                    name = _symbol(node.func)
                    expected.discard(name)
                    target = self.resolved(path, node, scope)
                    if self.target_ref(target) is None:
                        self.issue("UNRESOLVED_TARGET", path, node)
                    self.add("ASSISTANT_BINDING", name, path, node, target)
            for _ in expected:
                self.issue("MISSING_ANCHOR", path, scope)
            helpers = self.maps_from_calls(path, scope, "Runtime", "worker_handlers")
            self.handler_surfaces("API_WORKER_HELPER", path, scope, helpers, None)

        path, scope = self.require("recruiting_assistant/prompt.py", "build_answer_prompt")
        if scope is not None:
            returns = [n for n in ast.walk(scope) if isinstance(n, ast.Return)]
            if len(returns) != 1:
                self.issue("DYNAMIC_REGISTRATION", path, scope)
            for node in returns:
                for key in self.literal_map(path, node.value):
                    self.add("MODEL_REQUEST_KEY", key, path, node, "build_answer_prompt")
        path, schema = self.require("recruiting_assistant/prompt.py", "AssistantAnswerVerdict")
        if schema is not None:
            fields = [
                n
                for n in schema.body
                if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
            ]
            if not fields:
                self.issue("MISSING_REGISTRATION", path, schema)
            for node in fields:
                self.add(
                    "MODEL_RESPONSE_FIELD", node.target.id, path, node, "AssistantAnswerVerdict"
                )

    def handler_surfaces(
        self,
        kind: str,
        path: str,
        scope: ast.AST,
        handlers: dict[str, ast.AST],
        routing: dict[str, str] | None,
    ) -> None:
        for name, node in handlers.items():
            target = self.resolved(path, node, scope)
            if self.target_ref(target) is None:
                self.issue("UNRESOLVED_TARGET", path, node)
            if routing is not None and name not in routing:
                self.issue("HANDLER_WITHOUT_ROUTE", path, node)
            self.add(kind, name, path, node, target, routing.get(name) if routing else None)
        if not handlers:
            self.issue("MISSING_REGISTRATION", path, scope)

    def workers(self) -> None:
        path = PREFIX + "runtime/worker.py"
        tree = self.trees.get(path)
        if tree is None:
            self.issue("MISSING_ANCHOR", path)
            return
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and _symbol(node.func.value) == "EVENT_QUEUE_ROUTING"
                and node.func.attr not in {"items", "keys", "values", "get"}
            ) or (
                isinstance(node, ast.Subscript)
                and _symbol(node.value) == "EVENT_QUEUE_ROUTING"
                and isinstance(node.ctx, (ast.Store, ast.Del))
            ):
                self.issue("DYNAMIC_REGISTRATION", path, node)
        values = [
            n.value
            for n in tree.body
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "EVENT_QUEUE_ROUTING" for t in n.targets)
        ]
        routing = {}
        if len(values) != 1:
            self.issue("MISSING_ANCHOR", path)
        else:
            for name, node in self.literal_map(path, values[0]).items():
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    routing[name] = node.value
                else:
                    self.issue("DYNAMIC_REGISTRATION", path, node)
        path, scope = self.require("runtime/worker.py", "create_production_worker_runtime")
        if scope is None:
            return
        handlers = self.maps_from_calls(path, scope, "create_worker_runtime", "handlers")
        self.handler_surfaces("WORKER_HANDLER", path, scope, handlers, routing)
        for name in sorted(routing.keys() - handlers.keys()):
            self.add(
                "ROUTING_ONLY", name, path, values[0], "<no registered handler>", routing[name]
            )

    def anchors(self) -> None:
        for short, name in (
            ("recruiting_assistant/api.py", "_pipeline_answer"),
            ("recruiting_assistant/application.py", "AssistantAnswerService.answer"),
            ("shared/aws_clients/production.py", "AwsBedrockModel.generate"),
            ("shared/messaging/worker.py", "MessageConsumer.consume_once"),
            ("runtime/worker.py", "create_worker_runtime"),
            ("worker.py", "main"),
        ):
            path, node = self.require(short, name)
            if node is not None:
                self.add("DISPATCH_ANCHOR", name, path, node, _module(path) + "." + name)

    def closure(self) -> tuple[str, ...]:
        pending = {PREFIX + p for p in ANCHORS if PREFIX + p in self.trees}
        pending.update(r.path for s in self.surfaces for r in s.refs if r.path in self.trees)
        visited: set[str] = set()
        while pending:
            path = pending.pop()
            visited.add(path)
            for target in self.imports(path).values():
                parts = target.split(".")
                while parts:
                    candidate = self.modules.get(".".join(parts))
                    if candidate in self.trees:
                        if candidate not in visited:
                            pending.add(candidate)
                        break
                    parts.pop()
        return tuple(sorted(visited))


def _git_identity(repo: Path) -> dict:
    def git(*args: str) -> str:
        return (
            subprocess.check_output(
                ["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL, timeout=10
            )
            .decode("utf-8")
            .strip()
        )

    try:
        if Path(git("rev-parse", "--show-toplevel")).resolve() != repo:
            return {}
        return {
            "source_head": git("rev-parse", "HEAD"),
            "source_branch": git("branch", "--show-current"),
            "source_dirty": bool(git("status", "--porcelain", "--untracked-files=normal")),
        }
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return {}


def collect_inventory(repo: Path) -> Inventory:
    repo = repo.resolve()
    data, issues = _read_tree(repo)
    scan = SourceInventory(data, issues)
    scan.assistant()
    scan.workers()
    scan.anchors()
    after, after_issues = _read_tree(repo)
    if after != data or after_issues:
        scan.issue("SOURCE_DRIFT")
    sources = tuple(
        SourceFile(path=p, sha256=hashlib.sha256(b).hexdigest()) for p, b in sorted(data.items())
    )
    return Inventory(
        **_git_identity(repo),
        sources=sources,
        source_tree_digest=source_digest(sources),
        surfaces=tuple(scan.surfaces),
        import_closure=scan.closure(),
        issues=tuple(scan.issues),
    )
