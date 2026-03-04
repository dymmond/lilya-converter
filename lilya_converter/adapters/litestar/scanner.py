"""AST-based scanner for Litestar source projects."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, Literal, cast

from lilya_converter.models import AppInstanceInfo, Diagnostic, ModuleScan, RouteInfo, ScanReport

HTTP_DECORATOR_METHODS = {"get", "post", "put", "delete", "patch", "head", "route"}


def _expr_to_str(node: ast.AST | None) -> str:
    """Safely convert an AST node to a source-like string.

    Args:
        node: AST node to render.

    Returns:
        Best-effort source expression string.
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
        name: Keyword name.

    Returns:
        Matching keyword value node when present.
    """
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _iter_python_files(source_root: Path) -> Iterable[Path]:
    """Yield non-hidden Python files under ``source_root``.

    Args:
        source_root: Source root path.

    Yields:
        Sorted Python file paths.
    """
    for path in sorted(source_root.rglob("*.py")):
        if any(part.startswith(".") for part in path.parts):
            continue
        yield path


class _ModuleScanner(ast.NodeVisitor):
    """Visitor that collects Litestar route metadata from one module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize scanner state.

        Args:
            relative_path: Project-relative file path.
        """
        self.module = ModuleScan(relative_path=relative_path)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Capture Litestar/Router constructor assignments.

        Args:
            node: Assignment node.
        """
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            constructor = node.value.func.id
            if constructor in {"Litestar", "Router"}:
                kind: Literal["Litestar", "Router"] = cast(Literal["Litestar", "Router"], constructor)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.module.app_instances.append(
                            AppInstanceInfo(name=target.id, kind=kind, line=node.lineno, prefix_expr=None)
                        )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Scan synchronous route decorators.

        Args:
            node: Function definition node.
        """
        self._scan_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Scan asynchronous route decorators.

        Args:
            node: Async function definition node.
        """
        self._scan_function(node)
        self.generic_visit(node)

    def _scan_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Scan one function for Litestar route decorators.

        Args:
            node: Function definition node.
        """
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if isinstance(decorator.func, ast.Name) and decorator.func.id in HTTP_DECORATOR_METHODS:
                path_node = decorator.args[0] if decorator.args else _call_kwarg(decorator, "path")
                self.module.routes.append(
                    RouteInfo(
                        function_name=node.name,
                        owner="litestar",
                        method=decorator.func.id,
                        path=_expr_to_str(path_node) or None,
                        line=decorator.lineno,
                    )
                )


class LitestarScanner:
    """High-level scanner for Litestar source projects."""

    def scan(self, source_root: str | Path) -> ScanReport:
        """Scan a Litestar project tree and return route metadata.

        Args:
            source_root: Source project root path.

        Returns:
            Scan report containing module-level findings.
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
