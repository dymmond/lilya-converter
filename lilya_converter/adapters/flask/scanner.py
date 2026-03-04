"""AST-based scanner for Flask source projects."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, Literal, cast

from lilya_converter.models import (
    AppInstanceInfo,
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
}


def _expr_to_str(node: ast.AST | None) -> str:
    """Safely convert an AST node to a source-like string.

    Args:
        node: Node to render.

    Returns:
        Best-effort source-style expression string.
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
        name: Keyword argument name.

    Returns:
        The matching keyword value node when present, otherwise ``None``.
    """
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _owner_and_attr(node: ast.AST) -> tuple[str | None, str | None]:
    """Resolve ``owner.attr`` names from a call/decorator expression.

    Args:
        node: Expression node to inspect.

    Returns:
        Tuple of ``(owner_name, attr_name)`` when resolvable.
    """
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id, node.attr
    return None, None


def _iter_python_files(source_root: Path) -> Iterable[Path]:
    """Yield non-hidden Python files under ``source_root``.

    Args:
        source_root: Root directory to scan.

    Yields:
        Sorted Python file paths.
    """
    for path in sorted(source_root.rglob("*.py")):
        if any(part.startswith(".") for part in path.parts):
            continue
        yield path


class _ModuleScanner(ast.NodeVisitor):
    """Visitor that collects Flask scan metadata for one module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize per-module scanner state.

        Args:
            relative_path: Project-relative module path.
        """
        self.module = ModuleScan(relative_path=relative_path)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Capture Flask/Blueprint constructor assignments.

        Args:
            node: Assignment node to inspect.
        """
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            constructor = node.value.func.id
            if constructor in {"Flask", "Blueprint"}:
                kind: Literal["Flask", "Blueprint"] = cast(Literal["Flask", "Blueprint"], constructor)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.module.app_instances.append(
                            AppInstanceInfo(
                                name=target.id,
                                kind=kind,
                                line=node.lineno,
                                prefix_expr=_expr_to_str(_call_kwarg(node.value, "url_prefix")) or None,
                            )
                        )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Capture blueprint registration call-site metadata.

        Args:
            node: Call node to inspect.
        """
        owner, attr = _owner_and_attr(node.func)
        if owner and attr == "register_blueprint":
            blueprint_expr: ast.AST | None = None
            if node.args:
                blueprint_expr = node.args[0]
            else:
                blueprint_expr = _call_kwarg(node, "blueprint")

            self.module.include_routers.append(
                IncludeRouterInfo(
                    owner=owner,
                    router_expr=_expr_to_str(blueprint_expr) or "<missing>",
                    prefix_expr=_expr_to_str(_call_kwarg(node, "url_prefix")) or None,
                    line=node.lineno,
                )
            )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Scan synchronous function decorators for route metadata.

        Args:
            node: Function definition node.
        """
        self._scan_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Scan asynchronous function decorators for route metadata.

        Args:
            node: Async function definition node.
        """
        self._scan_function(node)
        self.generic_visit(node)

    def _scan_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Collect route decorator metadata from one function.

        Args:
            node: Function definition node.
        """
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            owner, attr = _owner_and_attr(decorator.func)
            if owner is None:
                continue
            if attr == "route" or attr in HTTP_DECORATOR_METHODS:
                path_node = decorator.args[0] if decorator.args else _call_kwarg(decorator, "rule")
                self.module.routes.append(
                    RouteInfo(
                        function_name=node.name,
                        owner=owner,
                        method=attr,
                        path=_expr_to_str(path_node) or None,
                        line=decorator.lineno,
                    )
                )


class FlaskScanner:
    """High-level scanner for Flask projects."""

    def scan(self, source_root: str | Path) -> ScanReport:
        """Scan a Flask source tree and return typed scan metadata.

        Args:
            source_root: Source project root path.

        Returns:
            A scan report containing module-level findings.
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
            modules.append(scanner.module)

        modules.sort(key=lambda item: item.relative_path)
        diagnostics.sort(key=lambda item: (item.file or "", item.line or 0, item.code))
        return ScanReport(source_root=str(root), modules=modules, diagnostics=diagnostics)
