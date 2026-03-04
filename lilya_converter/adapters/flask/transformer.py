"""AST transformation pipeline for Flask-to-Lilya conversion."""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass
from pathlib import Path

from lilya_converter.models import Diagnostic

HTTP_DECORATOR_METHODS = {
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "head",
    "options",
}

LILYA_HTTP_ROUTE_KWARGS = {
    "methods",
    "name",
    "middleware",
    "permissions",
    "exception_handlers",
    "dependencies",
    "include_in_schema",
    "before_request",
    "after_request",
}


def _expr_to_str(node: ast.AST | None) -> str:
    """Safely convert an AST node to a source-like string.

    Args:
        node: Node to render.

    Returns:
        Best-effort expression string.
    """
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def _get_kwarg(call: ast.Call, name: str) -> ast.keyword | None:
    """Find a keyword argument by name.

    Args:
        call: Call node to inspect.
        name: Keyword name to find.

    Returns:
        Matching keyword node when present.
    """
    for kw in call.keywords:
        if kw.arg == name:
            return kw
    return None


def _owner_and_attr(node: ast.AST) -> tuple[str | None, str | None]:
    """Resolve owner and attribute name from ``owner.attr`` expressions.

    Args:
        node: AST node to inspect.

    Returns:
        Tuple containing owner symbol and attribute name.
    """
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id, node.attr
    return None, None


def _path_join(left: str, right: str) -> str:
    """Join URL path segments into a normalized path string.

    Args:
        left: Left/prefix path segment.
        right: Right/route path segment.

    Returns:
        Joined URL path.
    """
    left = left.rstrip("/")
    right = right.lstrip("/")
    if not left and not right:
        return ""
    if not left:
        return f"/{right}" if not right.startswith("/") else right
    if not right:
        return left if left.startswith("/") else f"/{left}"
    return f"{left}/{right}"


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


class _FlaskTransformer(ast.NodeTransformer):
    """Rule-driven AST transformer for a single Flask source module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize per-module transformation state.

        Args:
            relative_path: Project-relative path for diagnostics and diff labels.
        """
        self.relative_path = relative_path
        self.diagnostics: list[Diagnostic] = []
        self.applied_rules: set[str] = set()
        self._blueprint_prefix: dict[str, ast.expr] = {}

    def _diag(self, code: str, message: str, *, line: int | None = None, severity: str = "warning") -> None:
        """Append one transformation diagnostic.

        Args:
            code: Stable diagnostic identifier.
            message: Human-readable diagnostic message.
            line: Optional 1-based source line.
            severity: Diagnostic severity level.
        """
        self.diagnostics.append(
            Diagnostic(
                code=code,
                message=message,
                severity=severity,  # type: ignore[arg-type]
                file=self.relative_path,
                line=line,
            )
        )

    def _merge_prefix_into_decorator(self, decorator: ast.Call, owner: str, function_name: str) -> None:
        """Merge extracted blueprint prefix into a route decorator path.

        Args:
            decorator: Route decorator call node.
            owner: Decorator owner symbol.
            function_name: Function name for diagnostics.
        """
        if owner not in self._blueprint_prefix:
            return

        prefix_expr = self._blueprint_prefix[owner]
        path_expr: ast.expr | None = None
        target = "missing"
        if decorator.args:
            target = "arg"
            path_expr = decorator.args[0]
        else:
            rule_kw = _get_kwarg(decorator, "rule")
            if rule_kw is not None:
                target = "kw"
                path_expr = rule_kw.value

        if path_expr is None:
            self._diag(
                code="convert.blueprint_prefix.missing_rule",
                message=f"Blueprint '{owner}' has url_prefix but route decorator on '{function_name}' has no rule.",
                line=decorator.lineno,
            )
            return

        if (
            isinstance(prefix_expr, ast.Constant)
            and isinstance(prefix_expr.value, str)
            and isinstance(path_expr, ast.Constant)
            and isinstance(path_expr.value, str)
        ):
            joined = ast.Constant(value=_path_join(prefix_expr.value, path_expr.value))
            if target == "arg":
                decorator.args[0] = joined
            else:
                rule_kw = _get_kwarg(decorator, "rule")
                assert rule_kw is not None
                rule_kw.value = joined
            self.applied_rules.add("blueprint_prefix_to_route_path")
            return

        self._diag(
            code="convert.blueprint_prefix.dynamic_path",
            message=(
                f"Blueprint '{owner}' url_prefix could not be merged into dynamic route path for '{function_name}'. "
                "Manual review required."
            ),
            line=decorator.lineno,
        )

    def _normalize_route_decorator(self, decorator: ast.Call, function_name: str) -> None:
        """Normalize Flask route decorator kwargs for Lilya compatibility.

        Args:
            decorator: Route decorator call.
            function_name: Decorated function name.
        """
        endpoint_kw = _get_kwarg(decorator, "endpoint")
        if endpoint_kw is not None:
            endpoint_kw.arg = "name"
            self.applied_rules.add("flask_route_endpoint_to_name")

        if _get_kwarg(decorator, "methods") is None:
            decorator.keywords.append(
                ast.keyword(arg="methods", value=ast.List(elts=[ast.Constant(value="GET")], ctx=ast.Load()))
            )
            self.applied_rules.add("flask_route_default_methods")

        kept: list[ast.keyword] = []
        removed: list[str] = []
        for kw in decorator.keywords:
            if kw.arg is None:
                kept.append(kw)
                continue
            if kw.arg in LILYA_HTTP_ROUTE_KWARGS:
                kept.append(kw)
            else:
                removed.append(kw.arg)
        decorator.keywords = kept

        if removed:
            self._diag(
                code="convert.flask.route_kwargs_removed",
                message=(f"Removed unsupported Flask route kwargs on '{function_name}': {', '.join(sorted(removed))}"),
                line=decorator.lineno,
            )
            self.applied_rules.add("flask_route_kwargs_filtered")

    def _normalize_method_decorator(self, decorator: ast.Call, function_name: str) -> None:
        """Normalize Flask single-method decorators for Lilya compatibility.

        Args:
            decorator: Method decorator call.
            function_name: Decorated function name.
        """
        endpoint_kw = _get_kwarg(decorator, "endpoint")
        if endpoint_kw is not None:
            endpoint_kw.arg = "name"
            self.applied_rules.add("flask_route_endpoint_to_name")

        kept: list[ast.keyword] = []
        removed: list[str] = []
        for kw in decorator.keywords:
            if kw.arg is None:
                kept.append(kw)
                continue
            if kw.arg == "methods":
                removed.append("methods")
                continue
            if kw.arg in LILYA_HTTP_ROUTE_KWARGS and kw.arg != "methods":
                kept.append(kw)
            else:
                removed.append(kw.arg)
        decorator.keywords = kept

        if removed:
            self._diag(
                code="convert.flask.route_kwargs_removed",
                message=(f"Removed unsupported Flask route kwargs on '{function_name}': {', '.join(sorted(removed))}"),
                line=decorator.lineno,
            )
            self.applied_rules.add("flask_route_kwargs_filtered")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST | list[ast.stmt] | None:
        """Rewrite Flask imports to Lilya imports when possible.

        Args:
            node: Import-from statement node.

        Returns:
            Rewritten import statement(s) or original node.
        """
        if node.module != "flask":
            return node

        grouped: dict[str, list[ast.alias]] = {}
        remaining: list[ast.alias] = []

        def add(module: str, alias: ast.alias) -> None:
            grouped.setdefault(module, []).append(alias)

        for alias in node.names:
            name = alias.name
            local_name = alias.asname
            if name == "Flask":
                add("lilya.apps", ast.alias(name="Lilya", asname=local_name or "Flask"))
            elif name == "Blueprint":
                add("lilya.routing", ast.alias(name="Router", asname=local_name or "Blueprint"))
            else:
                remaining.append(alias)

        statements: list[ast.stmt] = [
            ast.ImportFrom(
                module=module, names=sorted(aliases, key=lambda item: (item.name, item.asname or "")), level=0
            )
            for module, aliases in sorted(grouped.items(), key=lambda item: item[0])
        ]
        if remaining:
            statements.append(ast.ImportFrom(module=node.module, names=remaining, level=node.level))
        if grouped:
            self.applied_rules.add("flask_imports_to_lilya")
        return statements or None

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """Rewrite Flask/Blueprint constructor assignments.

        Args:
            node: Assignment node.

        Returns:
            Possibly rewritten assignment node.
        """
        self.generic_visit(node)
        if not isinstance(node.value, ast.Call):
            return node
        if not node.targets or not isinstance(node.targets[0], ast.Name):
            return node
        owner = node.targets[0].id
        call = node.value
        if not isinstance(call.func, ast.Name) or call.func.id not in {"Flask", "Blueprint"}:
            return node

        if call.func.id == "Blueprint":
            prefix_kw = _get_kwarg(call, "url_prefix")
            if prefix_kw is not None:
                self._blueprint_prefix[owner] = prefix_kw.value
                call.keywords = [kw for kw in call.keywords if kw is not prefix_kw]
                self.applied_rules.add("blueprint_prefix_extracted")

        args_removed = bool(call.args)
        kwargs_removed: list[str] = [kw.arg for kw in call.keywords if kw.arg is not None]
        call.args = []
        call.keywords = [kw for kw in call.keywords if kw.arg is None]

        if args_removed:
            self._diag(
                code="convert.flask.constructor_args_removed",
                message=f"Removed constructor positional args for '{owner}' ({call.func.id}).",
                line=node.lineno,
            )
        if kwargs_removed:
            self._diag(
                code="convert.flask.constructor_kwargs_removed",
                message=(
                    f"Removed unsupported {call.func.id} kwargs for '{owner}': {', '.join(sorted(kwargs_removed))}"
                ),
                line=node.lineno,
            )
            self.applied_rules.add("flask_route_kwargs_filtered")

        if args_removed or kwargs_removed:
            self.applied_rules.add("flask_constructor_sanitized")
        return node

    def _rewrite_register_blueprint_call(self, node: ast.Call) -> ast.Call:
        """Rewrite ``register_blueprint`` calls to Lilya ``include`` calls.

        Args:
            node: Call node to rewrite.

        Returns:
            Rewritten call node.
        """
        if not isinstance(node.func, ast.Attribute):
            return node
        if node.func.attr != "register_blueprint":
            return node

        blueprint_expr: ast.expr | None = None
        url_prefix_expr: ast.expr = ast.Constant(value="/")

        if node.args:
            blueprint_expr = node.args[0]

        dropped: list[str] = []
        for keyword in node.keywords:
            if keyword.arg == "blueprint":
                blueprint_expr = keyword.value
            elif keyword.arg == "url_prefix":
                url_prefix_expr = keyword.value
            elif keyword.arg is not None:
                dropped.append(keyword.arg)

        if blueprint_expr is None:
            self._diag(
                code="convert.register_blueprint.missing_blueprint",
                message="Could not resolve register_blueprint() blueprint argument.",
                line=node.lineno,
                severity="error",
            )
            return node

        if dropped:
            self._diag(
                code="convert.register_blueprint.kwargs_removed",
                message=f"Removed unsupported register_blueprint kwargs: {', '.join(sorted(dropped))}",
                line=node.lineno,
            )
            self.applied_rules.add("flask_route_kwargs_filtered")

        if isinstance(url_prefix_expr, ast.Constant) and url_prefix_expr.value == "":
            url_prefix_expr = ast.Constant(value="/")

        node.func.attr = "include"
        node.args = []
        node.keywords = [
            ast.keyword(arg="path", value=url_prefix_expr),
            ast.keyword(arg="app", value=blueprint_expr),
        ]
        self.applied_rules.add("register_blueprint_to_include")
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        """Visit and rewrite relevant call expressions.

        Args:
            node: Call node.

        Returns:
            Rewritten call node when applicable.
        """
        self.generic_visit(node)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "register_blueprint":
            return self._rewrite_register_blueprint_call(node)
        return node

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
        """Normalize Flask route decorators on one function definition.

        Args:
            node: Function definition node.

        Returns:
            Updated function node.
        """
        decorators: list[ast.expr] = []
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                decorators.append(decorator)
                continue

            owner, attr = _owner_and_attr(decorator.func)
            if owner is None:
                decorators.append(decorator)
                continue

            if attr == "route":
                self._merge_prefix_into_decorator(decorator, owner, node.name)
                self._normalize_route_decorator(decorator, node.name)
            elif attr in HTTP_DECORATOR_METHODS:
                self._merge_prefix_into_decorator(decorator, owner, node.name)
                self._normalize_method_decorator(decorator, node.name)

            decorators.append(decorator)

        node.decorator_list = decorators
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        """Visit synchronous function definitions.

        Args:
            node: Function definition node.

        Returns:
            Updated function node.
        """
        return self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        """Visit asynchronous function definitions.

        Args:
            node: Async function definition node.

        Returns:
            Updated async function node.
        """
        return self._visit_function(node)


def _apply_module_transformation(tree: ast.Module, relative_path: str) -> tuple[ast.Module, _FlaskTransformer]:
    """Apply Flask conversion rules to a parsed module AST.

    Args:
        tree: Parsed source module AST.
        relative_path: Project-relative module path for diagnostics.

    Returns:
        Tuple containing transformed AST and transformer state.
    """
    transformer = _FlaskTransformer(relative_path=relative_path)
    updated = transformer.visit(tree)
    assert isinstance(updated, ast.Module)
    ast.fix_missing_locations(updated)
    return updated, transformer


def transform_python_source(source: str, relative_path: str) -> TransformResult:
    """Transform Flask Python source text into Lilya-compatible source text.

    Args:
        source: Source Python text.
        relative_path: Project-relative path used for diagnostics/diff labels.

    Returns:
        Transformation result with content, diagnostics, and diff.
    """
    original_tree = ast.parse(source, filename=relative_path)
    updated_tree, transformer = _apply_module_transformation(original_tree, relative_path=relative_path)
    converted = ast.unparse(updated_tree) + "\n"
    changed = converted != source
    diff = ""
    if changed:
        diff = "".join(
            difflib.unified_diff(
                source.splitlines(keepends=True),
                converted.splitlines(keepends=True),
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
            )
        )
    return TransformResult(
        content=converted,
        changed=changed,
        diagnostics=sorted(transformer.diagnostics, key=lambda item: (item.file or "", item.line or 0, item.code)),
        applied_rules=sorted(transformer.applied_rules),
        unified_diff=diff,
    )


def transform_python_file(path: Path, source_root: Path) -> TransformResult:
    """Transform one Flask source file from disk.

    Args:
        path: Source file path.
        source_root: Source root used to derive relative labels.

    Returns:
        Per-file transformation result.
    """
    source = path.read_text(encoding="utf-8")
    relative_path = str(path.resolve().relative_to(source_root.resolve()))
    return transform_python_source(source=source, relative_path=relative_path)
