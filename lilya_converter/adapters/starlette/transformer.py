"""AST transformation pipeline for Starlette-to-Lilya conversion."""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass
from pathlib import Path

from lilya_converter.models import Diagnostic, Severity

ROUTE_KWARGS = {
    "methods",
    "name",
    "include_in_schema",
    "middleware",
    "permissions",
    "exception_handlers",
    "dependencies",
    "before_request",
    "after_request",
    "deprecated",
}
WEBSOCKET_ROUTE_KWARGS = {
    "name",
    "include_in_schema",
    "middleware",
    "permissions",
    "exception_handlers",
    "dependencies",
    "before_request",
    "after_request",
}
MOUNT_KWARGS = {
    "app",
    "routes",
    "name",
    "middleware",
    "permissions",
    "exception_handlers",
    "dependencies",
    "before_request",
    "after_request",
    "namespace",
    "pattern",
    "include_in_schema",
    "redirect_slashes",
}


@dataclass
class TransformResult:
    """Represent the transformation result for one Python module.

    Args:
        content: Transformed Python source text.
        changed: Whether transformed content differs from source text.
        diagnostics: Ordered diagnostics emitted during transformation.
        applied_rules: Ordered list of applied rule identifiers.
        unified_diff: Unified diff between source and transformed content.
    """

    content: str
    changed: bool
    diagnostics: list[Diagnostic]
    applied_rules: list[str]
    unified_diff: str


def _get_kwarg(call: ast.Call, name: str) -> ast.keyword | None:
    """Find a keyword argument by name.

    Args:
        call: Call node to inspect.
        name: Keyword argument name.

    Returns:
        Matching keyword node when present.
    """
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword
    return None


def _normalize_path(path: str) -> str:
    """Normalize paths to Lilya path requirements.

    Args:
        path: Source path value.

    Returns:
        A non-empty path that starts with ``/``.
    """
    if not path:
        return "/"
    if not path.startswith("/"):
        return f"/{path}"
    return path


class _StarletteTransformer(ast.NodeTransformer):
    """Rule-driven AST transformer for one Starlette source module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize per-module transformation state.

        Args:
            relative_path: Project-relative path for diagnostics.
        """
        self.relative_path = relative_path
        self.diagnostics: list[Diagnostic] = []
        self.applied_rules: set[str] = set()

    def _diag(
        self,
        code: str,
        message: str,
        *,
        line: int | None = None,
        severity: Severity = "warning",
    ) -> None:
        """Append one transformation diagnostic.

        Args:
            code: Stable diagnostic identifier.
            message: Human-readable diagnostic message.
            line: Optional source line number.
            severity: Diagnostic severity.
        """
        self.diagnostics.append(
            Diagnostic(
                code=code,
                message=message,
                severity=severity,
                file=self.relative_path,
                line=line,
            )
        )

    def _normalize_path_expr(self, value: ast.expr, *, line: int) -> ast.expr:
        """Normalize path expression literals when possible.

        Args:
            value: Path expression.
            line: Source line for diagnostics.

        Returns:
            Normalized path expression.
        """
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            normalized = _normalize_path(value.value)
            if normalized != value.value:
                self.applied_rules.add("starlette_path_normalization")
            return ast.Constant(value=normalized)

        self._diag(
            code="convert.starlette.dynamic_path",
            message="Dynamic Starlette paths were kept as-is and may require manual review for Lilya.",
            line=line,
        )
        return value

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST | list[ast.stmt] | None:
        """Rewrite Starlette imports to Lilya imports.

        Args:
            node: Import-from statement node.

        Returns:
            Rewritten import statement(s) or original node.
        """
        if node.module not in {"starlette.applications", "starlette.routing"}:
            return node

        grouped: dict[str, list[ast.alias]] = {}
        remaining: list[ast.alias] = []

        def add(module: str, alias: ast.alias) -> None:
            grouped.setdefault(module, []).append(alias)

        for alias in node.names:
            if node.module == "starlette.applications" and alias.name == "Starlette":
                add("lilya.apps", ast.alias(name="Lilya", asname=alias.asname or "Starlette"))
            elif node.module == "starlette.routing" and alias.name == "Route":
                add("lilya.routing", ast.alias(name="Path", asname=alias.asname or "Route"))
            elif node.module == "starlette.routing" and alias.name == "Mount":
                add("lilya.routing", ast.alias(name="Include", asname=alias.asname or "Mount"))
            elif node.module == "starlette.routing" and alias.name == "WebSocketRoute":
                add(
                    "lilya.routing",
                    ast.alias(name="WebSocketPath", asname=alias.asname or "WebSocketRoute"),
                )
            elif node.module == "starlette.routing" and alias.name == "Router":
                add("lilya.routing", ast.alias(name="Router", asname=alias.asname))
            else:
                remaining.append(alias)

        statements: list[ast.stmt] = [
            ast.ImportFrom(
                module=module,
                names=sorted(aliases, key=lambda item: (item.name, item.asname or "")),
                level=0,
            )
            for module, aliases in sorted(grouped.items(), key=lambda item: item[0])
        ]
        if remaining:
            statements.append(ast.ImportFrom(module=node.module, names=remaining, level=node.level))

        if grouped:
            self.applied_rules.add("starlette_imports_to_lilya")

        return statements or None

    def _rewrite_route_call(self, node: ast.Call) -> ast.Call:
        """Rewrite ``Route(...)`` calls into Lilya ``Path(...)`` shape.

        Args:
            node: Route call node.

        Returns:
            Rewritten call node.
        """
        path_expr = node.args[0] if node.args else None
        endpoint_expr = node.args[1] if len(node.args) > 1 else None

        path_kw = _get_kwarg(node, "path")
        endpoint_kw = _get_kwarg(node, "endpoint")
        if path_expr is None and path_kw is not None:
            path_expr = path_kw.value
        if endpoint_expr is None and endpoint_kw is not None:
            endpoint_expr = endpoint_kw.value

        if path_expr is None or endpoint_expr is None:
            self._diag(
                code="convert.starlette.route_missing_values",
                message="Could not resolve Route(...) path/endpoint values; entry was left unchanged.",
                line=node.lineno,
                severity="error",
            )
            return node

        path_expr = self._normalize_path_expr(path_expr, line=node.lineno)

        keywords: list[ast.keyword] = []
        removed: list[str] = []
        for keyword in node.keywords:
            if keyword.arg in {"path", "endpoint"}:
                continue
            if keyword.arg is None:
                keywords.append(keyword)
                continue
            if keyword.arg in ROUTE_KWARGS:
                keywords.append(keyword)
            else:
                removed.append(keyword.arg)

        if removed:
            self._diag(
                code="convert.starlette.route_kwargs_removed",
                message="Removed unsupported Route kwargs: " + ", ".join(sorted(removed)),
                line=node.lineno,
            )

        node.args = [path_expr, endpoint_expr]
        node.keywords = keywords
        self.applied_rules.add("starlette_route_to_path")
        return node

    def _rewrite_websocket_route_call(self, node: ast.Call) -> ast.Call:
        """Rewrite ``WebSocketRoute(...)`` calls into Lilya websocket route shape.

        Args:
            node: WebSocketRoute call node.

        Returns:
            Rewritten call node.
        """
        path_expr = node.args[0] if node.args else None
        endpoint_expr = node.args[1] if len(node.args) > 1 else None

        path_kw = _get_kwarg(node, "path")
        endpoint_kw = _get_kwarg(node, "endpoint")
        if path_expr is None and path_kw is not None:
            path_expr = path_kw.value
        if endpoint_expr is None and endpoint_kw is not None:
            endpoint_expr = endpoint_kw.value

        if path_expr is None or endpoint_expr is None:
            self._diag(
                code="convert.starlette.websocket_route_missing_values",
                message="Could not resolve WebSocketRoute(...) path/endpoint values; entry was left unchanged.",
                line=node.lineno,
                severity="error",
            )
            return node

        path_expr = self._normalize_path_expr(path_expr, line=node.lineno)

        keywords: list[ast.keyword] = []
        removed: list[str] = []
        for keyword in node.keywords:
            if keyword.arg in {"path", "endpoint"}:
                continue
            if keyword.arg is None:
                keywords.append(keyword)
                continue
            if keyword.arg in WEBSOCKET_ROUTE_KWARGS:
                keywords.append(keyword)
            else:
                removed.append(keyword.arg)

        if removed:
            self._diag(
                code="convert.starlette.websocket_route_kwargs_removed",
                message="Removed unsupported WebSocketRoute kwargs: " + ", ".join(sorted(removed)),
                line=node.lineno,
            )

        node.args = [path_expr, endpoint_expr]
        node.keywords = keywords
        self.applied_rules.add("starlette_websocket_route_to_websocket_path")
        return node

    def _rewrite_mount_call(self, node: ast.Call) -> ast.Call:
        """Rewrite ``Mount(...)`` calls into Lilya ``Include(...)`` shape.

        Args:
            node: Mount call node.

        Returns:
            Rewritten call node.
        """
        path_expr = node.args[0] if node.args else None
        app_expr = node.args[1] if len(node.args) > 1 else None
        routes_expr = node.args[2] if len(node.args) > 2 else None

        path_kw = _get_kwarg(node, "path")
        app_kw = _get_kwarg(node, "app")
        routes_kw = _get_kwarg(node, "routes")

        if path_expr is None and path_kw is not None:
            path_expr = path_kw.value
        if app_expr is None and app_kw is not None:
            app_expr = app_kw.value
        if routes_expr is None and routes_kw is not None:
            routes_expr = routes_kw.value

        if path_expr is None:
            self._diag(
                code="convert.starlette.mount_missing_path",
                message="Could not resolve Mount(...) path value; entry was left unchanged.",
                line=node.lineno,
                severity="error",
            )
            return node

        if app_expr is None and routes_expr is None:
            self._diag(
                code="convert.starlette.mount_missing_target",
                message="Mount(...) requires app=... or routes=...; entry was left unchanged.",
                line=node.lineno,
                severity="error",
            )
            return node

        path_expr = self._normalize_path_expr(path_expr, line=node.lineno)

        keywords: list[ast.keyword] = []
        removed: list[str] = []
        if app_expr is not None:
            keywords.append(ast.keyword(arg="app", value=app_expr))
        if routes_expr is not None:
            keywords.append(ast.keyword(arg="routes", value=routes_expr))

        name_kw = _get_kwarg(node, "name")
        if name_kw is not None:
            keywords.append(ast.keyword(arg="name", value=name_kw.value))

        for keyword in node.keywords:
            if keyword.arg in {"path", "app", "routes", "name"}:
                continue
            if keyword.arg is None:
                keywords.append(keyword)
                continue
            if keyword.arg in MOUNT_KWARGS:
                keywords.append(keyword)
            else:
                removed.append(keyword.arg)

        if removed:
            self._diag(
                code="convert.starlette.mount_kwargs_removed",
                message="Removed unsupported Mount kwargs: " + ", ".join(sorted(removed)),
                line=node.lineno,
            )

        node.args = [path_expr]
        node.keywords = keywords
        self.applied_rules.add("starlette_mount_to_include")
        return node

    def _rewrite_mount_method_call(self, node: ast.Call) -> ast.Call:
        """Rewrite ``app.mount(...)`` calls into ``app.include(...)`` calls.

        Args:
            node: Method call node.

        Returns:
            Rewritten call node.
        """
        if not isinstance(node.func, ast.Attribute):
            return node

        path_expr = node.args[0] if node.args else None
        app_expr = node.args[1] if len(node.args) > 1 else None

        path_kw = _get_kwarg(node, "path")
        app_kw = _get_kwarg(node, "app")
        if path_expr is None and path_kw is not None:
            path_expr = path_kw.value
        if app_expr is None and app_kw is not None:
            app_expr = app_kw.value

        if path_expr is None or app_expr is None:
            self._diag(
                code="convert.starlette.mount_call_missing_values",
                message="Could not resolve mount(...) path/app values; call was left unchanged.",
                line=node.lineno,
                severity="error",
            )
            return node

        path_expr = self._normalize_path_expr(path_expr, line=node.lineno)
        node.func.attr = "include"

        keywords: list[ast.keyword] = [ast.keyword(arg="path", value=path_expr), ast.keyword(arg="app", value=app_expr)]
        removed: list[str] = []

        for keyword in node.keywords:
            if keyword.arg in {"path", "app"}:
                continue
            if keyword.arg is None:
                keywords.append(keyword)
                continue
            if keyword.arg in MOUNT_KWARGS:
                keywords.append(keyword)
            else:
                removed.append(keyword.arg)

        if removed:
            self._diag(
                code="convert.starlette.mount_call_kwargs_removed",
                message="Removed unsupported mount(...) kwargs: " + ", ".join(sorted(removed)),
                line=node.lineno,
            )

        node.args = []
        node.keywords = keywords
        self.applied_rules.add("starlette_mount_to_include")
        return node

    def _rewrite_add_route_call(self, node: ast.Call) -> ast.Call:
        """Normalize ``add_route`` keyword signatures for Lilya.

        Args:
            node: add_route call node.

        Returns:
            Rewritten call node.
        """
        path_expr = node.args[0] if node.args else None
        handler_expr = node.args[1] if len(node.args) > 1 else None

        path_kw = _get_kwarg(node, "path")
        handler_kw = _get_kwarg(node, "handler")
        route_kw = _get_kwarg(node, "route")

        if path_expr is None and path_kw is not None:
            path_expr = path_kw.value
        if handler_expr is None and handler_kw is not None:
            handler_expr = handler_kw.value
        if handler_expr is None and route_kw is not None:
            handler_expr = route_kw.value

        if path_expr is None or handler_expr is None:
            self._diag(
                code="convert.starlette.add_route_missing_values",
                message="Could not resolve add_route(...) path/handler values; call was left unchanged.",
                line=node.lineno,
                severity="error",
            )
            return node

        path_expr = self._normalize_path_expr(path_expr, line=node.lineno)

        keywords: list[ast.keyword] = [
            ast.keyword(arg="path", value=path_expr),
            ast.keyword(arg="handler", value=handler_expr),
        ]
        removed: list[str] = []

        for keyword in node.keywords:
            if keyword.arg in {"path", "route", "handler"}:
                continue
            if keyword.arg is None:
                keywords.append(keyword)
                continue
            if keyword.arg in ROUTE_KWARGS:
                keywords.append(keyword)
            else:
                removed.append(keyword.arg)

        if removed:
            self._diag(
                code="convert.starlette.add_route_kwargs_removed",
                message="Removed unsupported add_route(...) kwargs: " + ", ".join(sorted(removed)),
                line=node.lineno,
            )

        node.args = []
        node.keywords = keywords
        self.applied_rules.add("starlette_add_route_signature")
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        """Visit and rewrite Starlette call expressions.

        Args:
            node: Call node.

        Returns:
            Rewritten call node when applicable.
        """
        self.generic_visit(node)

        if isinstance(node.func, ast.Name):
            if node.func.id == "Route":
                return self._rewrite_route_call(node)
            if node.func.id == "WebSocketRoute":
                return self._rewrite_websocket_route_call(node)
            if node.func.id == "Mount":
                return self._rewrite_mount_call(node)
            return node

        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "mount":
                return self._rewrite_mount_method_call(node)
            if node.func.attr == "add_route":
                return self._rewrite_add_route_call(node)

        return node


def _apply_module_transformation(tree: ast.Module, relative_path: str) -> tuple[ast.Module, _StarletteTransformer]:
    """Apply Starlette conversion rules to one parsed module.

    Args:
        tree: Parsed module AST.
        relative_path: Project-relative module path.

    Returns:
        Tuple containing transformed AST and transformer state.
    """
    transformer = _StarletteTransformer(relative_path=relative_path)
    updated = transformer.visit(tree)
    assert isinstance(updated, ast.Module)
    ast.fix_missing_locations(updated)
    return updated, transformer


def transform_python_source(source: str, relative_path: str) -> TransformResult:
    """Transform Starlette source into Lilya-compatible source.

    Args:
        source: Source module text.
        relative_path: Project-relative path for diagnostics and diff labels.

    Returns:
        Per-module transformation result.
    """
    original_tree = ast.parse(source, filename=relative_path)
    updated_tree, transformer = _apply_module_transformation(original_tree, relative_path=relative_path)
    converted = ast.unparse(updated_tree) + "\n"
    changed = converted != source

    unified_diff = ""
    if changed:
        unified_diff = "".join(
            difflib.unified_diff(
                source.splitlines(keepends=True),
                converted.splitlines(keepends=True),
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
            )
        )

    diagnostics = sorted(transformer.diagnostics, key=lambda item: (item.file or "", item.line or 0, item.code))
    return TransformResult(
        content=converted,
        changed=changed,
        diagnostics=diagnostics,
        applied_rules=sorted(transformer.applied_rules),
        unified_diff=unified_diff,
    )


def transform_python_file(path: Path, source_root: Path) -> TransformResult:
    """Transform one Starlette source file from disk.

    Args:
        path: Source file path.
        source_root: Source root for relative diff labels.

    Returns:
        Per-file transformation result.
    """
    source = path.read_text(encoding="utf-8")
    relative_path = str(path.resolve().relative_to(source_root.resolve()))
    return transform_python_source(source=source, relative_path=relative_path)
