"""AST-based scanner for FastAPI source projects.

The scanner extracts conversion-relevant metadata (apps, routers, routes,
dependencies, middleware/events/exception decorators) without mutating code.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, Literal

from lilya_converter.models import (
    AppInstanceInfo,
    DependencyRef,
    Diagnostic,
    IncludeRouterInfo,
    ModuleScan,
    RouteInfo,
    ScanReport,
)

HTTP_DECORATOR_METHODS = {
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "head",
    "options",
    "trace",
    "api_route",
    "websocket",
}


def _expr_to_str(node: ast.AST | None) -> str:
    """Safely convert an AST node to a source-like string.

    Args:
        node: Node to render.

    Returns:
        A best-effort string form of the node.
    """
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def _call_kwarg(call: ast.Call, name: str) -> ast.AST | None:
    """Return a keyword argument value from a call node.

    Args:
        call: Call node to inspect.
        name: Keyword name to locate.

    Returns:
        The keyword value node if present; otherwise `None`.
    """
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _owner_and_attr(node: ast.AST) -> tuple[str | None, str | None]:
    """Resolve `owner.attr` from an attribute expression.

    Args:
        node: Expression node to inspect.

    Returns:
        A tuple `(owner_name, attr_name)` when resolvable; otherwise `(None, None)`.
    """
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id, node.attr
    return None, None


def _is_depends_call(node: ast.AST) -> bool:
    """Check whether a node represents `Depends(...)` invocation.

    Args:
        node: Node to inspect.

    Returns:
        `True` when the node is a direct `Depends` call.
    """
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name) and node.func.id == "Depends":
        return True
    if isinstance(node.func, ast.Attribute) and node.func.attr == "Depends":
        return True
    return False


def _iter_python_files(source_root: Path) -> Iterable[Path]:
    """Yield non-hidden Python files under `source_root` in sorted order.

    Args:
        source_root: Directory root to search.

    Yields:
        Python file paths in deterministic order.
    """
    for path in sorted(source_root.rglob("*.py")):
        if any(part.startswith(".") for part in path.parts):
            continue
        yield path


class _ModuleScanner(ast.NodeVisitor):
    """Visitor that collects scan metadata from a single AST module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize scanner state for one module.

        Args:
            relative_path: Project-relative module path.
        """
        self.module = ModuleScan(relative_path=relative_path)
        self._route_functions: set[str] = set()

    def _dependency_name(self, node: ast.AST) -> str:
        """Derive a stable dependency display name from an expression.

        Args:
            node: Dependency expression node.

        Returns:
            Best-effort dependency name.
        """
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return _expr_to_str(node) or "dependency"

    def _record_depends_list(
        self, node: ast.AST | None, source: Literal["decorator", "app", "router", "include"]
    ) -> None:
        """Record dependencies from list/tuple-style `Depends(...)` containers.

        Args:
            node: AST node expected to be a list/tuple of `Depends(...)` calls.
            source: Source context where dependencies were declared.
        """
        if node is None:
            return
        if not isinstance(node, (ast.List, ast.Tuple)):
            return
        for item in node.elts:
            if not _is_depends_call(item):
                continue
            assert isinstance(item, ast.Call)
            dependency_expr: ast.AST | None = item.args[0] if item.args else _call_kwarg(item, "dependency")
            self.module.dependency_refs.append(
                DependencyRef(
                    name=self._dependency_name(dependency_expr) if dependency_expr is not None else "dependency",
                    expression=_expr_to_str(item),
                    line=item.lineno,
                    source=source,
                )
            )

    def visit_Assign(self, node: ast.Assign) -> None:
        """Capture FastAPI/APIRouter constructor assignments."""
        if isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id in {"FastAPI", "APIRouter"}:
                source_kind = "app" if call.func.id == "FastAPI" else "router"
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.module.app_instances.append(
                            AppInstanceInfo(
                                name=target.id,
                                kind=call.func.id,  # type: ignore[arg-type]
                                line=node.lineno,
                                prefix_expr=_expr_to_str(_call_kwarg(call, "prefix")) or None,
                            )
                        )
                self._record_depends_list(_call_kwarg(call, "dependencies"), source=source_kind)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Capture include-router and middleware call-site metadata."""
        owner, attr = _owner_and_attr(node.func)
        if owner and attr == "include_router":
            router_arg: ast.AST | None = None
            if node.args:
                router_arg = node.args[0]
            else:
                router_arg = _call_kwarg(node, "router")
            self.module.include_routers.append(
                IncludeRouterInfo(
                    owner=owner,
                    router_expr=_expr_to_str(router_arg) or "<missing>",
                    prefix_expr=_expr_to_str(_call_kwarg(node, "prefix")) or None,
                    line=node.lineno,
                )
            )
            self._record_depends_list(_call_kwarg(node, "dependencies"), source="include")

        if owner and attr == "add_middleware":
            self.module.middleware_calls.append(node.lineno)

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Scan a synchronous function definition."""
        self._scan_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Scan an asynchronous function definition."""
        self._scan_function(node)
        self.generic_visit(node)

    def _scan_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Scan decorator and dependency information for one function.

        Args:
            node: Function definition node.
        """
        is_route = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                owner, attr = _owner_and_attr(decorator.func)
                if attr in HTTP_DECORATOR_METHODS and owner:
                    is_route = True
                    decorator_dependencies = _call_kwarg(decorator, "dependencies")
                    self._record_depends_list(decorator_dependencies, source="decorator")
                    route = RouteInfo(
                        function_name=node.name,
                        owner=owner,
                        method=attr,
                        path=_expr_to_str(decorator.args[0])
                        if decorator.args
                        else _expr_to_str(_call_kwarg(decorator, "path")) or None,
                        line=decorator.lineno,
                        has_dependencies_kw=_call_kwarg(decorator, "dependencies") is not None,
                        has_response_model_kw=_call_kwarg(decorator, "response_model") is not None,
                        has_response_class_kw=_call_kwarg(decorator, "response_class") is not None,
                        has_status_code_kw=_call_kwarg(decorator, "status_code") is not None,
                        has_responses_kw=_call_kwarg(decorator, "responses") is not None,
                    )
                    self.module.routes.append(route)
                elif attr == "middleware" and owner:
                    self.module.middleware_decorators.append(decorator.lineno)
                elif attr == "on_event" and owner:
                    self.module.event_decorators.append(decorator.lineno)
                elif attr == "exception_handler" and owner:
                    self.module.exception_handler_decorators.append(decorator.lineno)

        if is_route:
            self._route_functions.add(node.name)

        self._scan_depends(node, is_route=is_route)

    def _scan_depends(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_route: bool) -> None:
        """Extract dependency markers from function signatures.

        Args:
            node: Function definition node.
            is_route: Whether the function is route-decorated.
        """
        all_args = [*node.args.posonlyargs, *node.args.args]
        defaults = list(node.args.defaults)
        offset = len(all_args) - len(defaults)
        for index, arg in enumerate(all_args):
            default = defaults[index - offset] if index >= offset else None
            if default and _is_depends_call(default):
                self.module.dependency_refs.append(
                    DependencyRef(
                        name=arg.arg,
                        expression=_expr_to_str(default),
                        line=default.lineno,
                        source="param" if is_route else "router",
                    )
                )

        for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=False):
            if default and _is_depends_call(default):
                self.module.dependency_refs.append(
                    DependencyRef(
                        name=arg.arg,
                        expression=_expr_to_str(default),
                        line=default.lineno,
                        source="param" if is_route else "router",
                    )
                )

        for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
            annotation = arg.annotation
            if isinstance(annotation, ast.Subscript):
                expr = _expr_to_str(annotation)
                if "Depends(" in expr:
                    self.module.dependency_refs.append(
                        DependencyRef(
                            name=arg.arg,
                            expression=expr,
                            line=annotation.lineno,
                            source="param" if is_route else "router",
                        )
                    )


class FastAPIScanner:
    """High-level scanner for FastAPI projects."""

    def scan(self, source_root: str | Path) -> ScanReport:
        """Scan a project root and return FastAPI-oriented metadata.

        Args:
            source_root: Source project root path.

        Returns:
            A scan report containing per-module findings and diagnostics.
        """
        root = Path(source_root).resolve()
        modules: list[ModuleScan] = []
        diagnostics: list[Diagnostic] = []

        for file_path in _iter_python_files(root):
            relative_path = str(file_path.relative_to(root))
            try:
                tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=relative_path)
            except SyntaxError as exc:
                diagnostics.append(
                    Diagnostic(
                        code="scan.syntax_error",
                        severity="error",
                        message=f"Could not parse '{relative_path}': {exc.msg}",
                        file=relative_path,
                        line=exc.lineno,
                        column=exc.offset,
                    )
                )
                continue

            scanner = _ModuleScanner(relative_path=relative_path)
            scanner.visit(tree)

            for line in scanner.module.middleware_decorators:
                scanner.module.diagnostics.append(
                    Diagnostic(
                        code="scan.middleware.decorator_unsupported",
                        message=(
                            "FastAPI function middleware decorators use request/call_next signature "
                            "and require manual conversion to Lilya class-based middleware."
                        ),
                        severity="warning",
                        file=relative_path,
                        line=line,
                    )
                )

            modules.append(scanner.module)

        modules.sort(key=lambda item: item.relative_path)
        diagnostics.sort(key=lambda item: (item.file or "", item.line or 0, item.code))
        return ScanReport(source_root=str(root), modules=modules, diagnostics=diagnostics)
