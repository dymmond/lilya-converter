"""AST-based scanner for Starlette source projects."""

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

ROUTE_BUILDERS = {"Route", "WebSocketRoute", "Mount"}


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
        name: Keyword argument name.

    Returns:
        Matching keyword value node when present.
    """
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _owner_and_attr(node: ast.AST) -> tuple[str | None, str | None]:
    """Resolve ``owner.attr`` names from an expression.

    Args:
        node: Expression node to inspect.

    Returns:
        Tuple containing owner symbol and attribute name.
    """
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id, node.attr
    return None, None


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
    """Visitor that collects Starlette scan metadata for one module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize scanner state.

        Args:
            relative_path: Project-relative module path.
        """
        self.module = ModuleScan(relative_path=relative_path)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Capture Starlette/Router constructor assignments.

        Args:
            node: Assignment node.
        """
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            constructor = node.value.func.id
            if constructor in {"Starlette", "Router"}:
                kind: Literal["Starlette", "Router"] = cast(Literal["Starlette", "Router"], constructor)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.module.app_instances.append(
                            AppInstanceInfo(name=target.id, kind=kind, line=node.lineno, prefix_expr=None)
                        )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Capture route/include call-site metadata.

        Args:
            node: Call node to inspect.
        """
        owner, attr = _owner_and_attr(node.func)
        if owner and attr in {"mount", "include"}:
            target_expr = node.args[1] if len(node.args) > 1 else _call_kwarg(node, "app")
            path_expr = node.args[0] if node.args else _call_kwarg(node, "path")
            self.module.include_routers.append(
                IncludeRouterInfo(
                    owner=owner,
                    router_expr=_expr_to_str(target_expr) or "<missing>",
                    prefix_expr=_expr_to_str(path_expr) or None,
                    line=node.lineno,
                )
            )

        if isinstance(node.func, ast.Name) and node.func.id in ROUTE_BUILDERS:
            path_expr = node.args[0] if node.args else _call_kwarg(node, "path")
            endpoint_expr = None
            if node.func.id == "Mount":
                endpoint_expr = _call_kwarg(node, "app") or _call_kwarg(node, "routes")
                method = "mount"
            elif node.func.id == "WebSocketRoute":
                endpoint_expr = node.args[1] if len(node.args) > 1 else _call_kwarg(node, "endpoint")
                method = "websocket"
            else:
                endpoint_expr = node.args[1] if len(node.args) > 1 else _call_kwarg(node, "endpoint")
                method = "route"

            self.module.routes.append(
                RouteInfo(
                    function_name=_expr_to_str(endpoint_expr) or "handler",
                    owner="starlette",
                    method=method,
                    path=_expr_to_str(path_expr) or None,
                    line=node.lineno,
                )
            )

        self.generic_visit(node)


class StarletteScanner:
    """High-level scanner for Starlette source projects."""

    def scan(self, source_root: str | Path) -> ScanReport:
        """Scan a Starlette source tree and return route metadata.

        Args:
            source_root: Source project root path.

        Returns:
            Scan report containing module findings and diagnostics.
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
