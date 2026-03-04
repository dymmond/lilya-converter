"""AST-based scanner for Django URL configuration projects."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, Literal

from lilya_converter.models import (
    AppInstanceInfo,
    Diagnostic,
    IncludeRouterInfo,
    ModuleScan,
    RouteInfo,
    ScanReport,
)

DJANGO_URL_FUNCS = {"path", "re_path"}


def _expr_to_str(node: ast.AST | None) -> str:
    """Safely convert an AST node to a source-like string.

    Args:
        node: AST node to render.

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
        Matching keyword argument node when present.
    """
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _iter_python_files(source_root: Path) -> Iterable[Path]:
    """Yield non-hidden Python files under ``source_root``.

    Args:
        source_root: Project root path.

    Yields:
        Sorted Python file paths.
    """
    for path in sorted(source_root.rglob("*.py")):
        if any(part.startswith(".") for part in path.parts):
            continue
        yield path


class _ModuleScanner(ast.NodeVisitor):
    """Visitor that collects Django URL metadata from one module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize module scanner state.

        Args:
            relative_path: Project-relative file path.
        """
        self.module = ModuleScan(relative_path=relative_path)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Capture ``urlpatterns`` assignments and contained URL calls.

        Args:
            node: Assignment node.
        """
        target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "urlpatterns" in target_names:
            kind: Literal["DjangoURLConf"] = "DjangoURLConf"
            self.module.app_instances.append(
                AppInstanceInfo(name="urlpatterns", kind=kind, line=node.lineno, prefix_expr=None)
            )
            if isinstance(node.value, (ast.List, ast.Tuple)):
                for entry in node.value.elts:
                    self._scan_urlpattern_entry(entry)
        self.generic_visit(node)

    def _scan_urlpattern_entry(self, node: ast.AST) -> None:
        """Scan one URL pattern expression entry.

        Args:
            node: URL pattern expression.
        """
        if not isinstance(node, ast.Call):
            return
        if not isinstance(node.func, ast.Name) or node.func.id not in DJANGO_URL_FUNCS:
            return

        method = node.func.id
        route_expr: ast.AST | None = node.args[0] if node.args else _call_kwarg(node, "route")
        view_expr: ast.AST | None = node.args[1] if len(node.args) > 1 else _call_kwarg(node, "view")

        if isinstance(view_expr, ast.Call) and isinstance(view_expr.func, ast.Name) and view_expr.func.id == "include":
            included: ast.AST | None = view_expr.args[0] if view_expr.args else _call_kwarg(view_expr, "arg")
            self.module.include_routers.append(
                IncludeRouterInfo(
                    owner="urlpatterns",
                    router_expr=_expr_to_str(included) or "<missing>",
                    prefix_expr=_expr_to_str(route_expr) or None,
                    line=node.lineno,
                )
            )
            return

        self.module.routes.append(
            RouteInfo(
                function_name=_expr_to_str(view_expr) or "view",
                owner="urlpatterns",
                method=method,
                path=_expr_to_str(route_expr) or None,
                line=node.lineno,
            )
        )


class DjangoScanner:
    """High-level scanner for Django URL configuration projects."""

    def scan(self, source_root: str | Path) -> ScanReport:
        """Scan a Django project tree and return URL-oriented metadata.

        Args:
            source_root: Source project root path.

        Returns:
            Scan report with discovered modules and diagnostics.
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
