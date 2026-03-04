"""AST transformation pipeline for Litestar-to-Lilya conversion."""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass
from pathlib import Path

from lilya_converter.models import Diagnostic, Severity

HTTP_DECORATOR_TO_METHODS: dict[str, list[str]] = {
    "get": ["GET"],
    "post": ["POST"],
    "put": ["PUT"],
    "patch": ["PATCH"],
    "delete": ["DELETE"],
    "head": ["HEAD"],
}
SUPPORTED_DECORATORS = set(HTTP_DECORATOR_TO_METHODS) | {"route"}
SUPPORTED_LILYA_ROUTER_KWARGS = {
    "routes",
    "redirect_slashes",
    "default",
    "on_startup",
    "on_shutdown",
    "lifespan",
    "middleware",
    "permissions",
    "dependencies",
    "before_request",
    "after_request",
    "settings_module",
    "include_in_schema",
    "deprecated",
    "is_sub_router",
}


@dataclass
class _RouteSpec:
    """Hold extracted Litestar decorator metadata for one function.

    Args:
        path: Normalized path expression for the route.
        methods: HTTP methods expression for the route.
        name: Optional route name expression.
        include_in_schema: Optional include-in-schema expression.
        line: Source line for diagnostics.
    """

    path: ast.expr
    methods: ast.expr | None
    name: ast.expr | None
    include_in_schema: ast.expr | None
    line: int


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


def _expr_to_str(node: ast.AST | None) -> str:
    """Safely convert an AST node into a source-like string.

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


def _normalize_path(path: str) -> str:
    """Normalize a route/include path for Lilya requirements.

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


class _LitestarTransformer(ast.NodeTransformer):
    """Rule-driven AST transformer for one Litestar source module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize per-module transformation state.

        Args:
            relative_path: Project-relative path for diagnostics.
        """
        self.relative_path = relative_path
        self.diagnostics: list[Diagnostic] = []
        self.applied_rules: set[str] = set()
        self._route_specs: dict[str, list[_RouteSpec]] = {}
        self._router_prefix: dict[str, ast.expr] = {}
        self._routing_imports: set[str] = set()
        self._needs_lilya_app_import = False

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
        """Normalize path literal expressions when possible.

        Args:
            value: Input path expression.
            line: Source line for diagnostics.

        Returns:
            Normalized expression.
        """
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            normalized = _normalize_path(value.value)
            if normalized != value.value:
                self.applied_rules.add("litestar_path_normalization")
            return ast.Constant(value=normalized)

        self._diag(
            code="convert.litestar.dynamic_path",
            message=(
                "Dynamic Litestar path expressions were kept as-is and may require manual review "
                "to satisfy Lilya path requirements."
            ),
            line=line,
        )
        return value

    def _extract_route_spec(self, decorator: ast.Call, *, function_name: str) -> _RouteSpec | None:
        """Extract route metadata from a Litestar decorator call.

        Args:
            decorator: Decorator call node.
            function_name: Name of the decorated function.

        Returns:
            Extracted route specification when supported.
        """
        if not isinstance(decorator.func, ast.Name):
            return None
        name = decorator.func.id
        if name not in SUPPORTED_DECORATORS:
            return None

        path_expr: ast.expr
        if decorator.args:
            path_expr = decorator.args[0]
        else:
            path_kw = _get_kwarg(decorator, "path")
            if path_kw is None:
                path_expr = ast.Constant(value="/")
            else:
                path_expr = path_kw.value

        path_expr = self._normalize_path_expr(path_expr, line=decorator.lineno)

        methods_expr: ast.expr | None
        if name == "route":
            methods_kw = _get_kwarg(decorator, "http_method")
            if methods_kw is None:
                methods_kw = _get_kwarg(decorator, "methods")
            if methods_kw is None:
                self._diag(
                    code="convert.litestar.route_missing_http_method",
                    message=(
                        f"Litestar route decorator on '{function_name}' has no http_method; "
                        "manual method mapping may be required."
                    ),
                    line=decorator.lineno,
                    severity="error",
                )
                methods_expr = None
            else:
                methods_expr = methods_kw.value
                if isinstance(methods_expr, ast.Constant) and isinstance(methods_expr.value, str):
                    methods_expr = ast.List(
                        elts=[ast.Constant(value=methods_expr.value.upper())],
                        ctx=ast.Load(),
                    )
                elif isinstance(methods_expr, (ast.List, ast.Tuple)):
                    upper: list[ast.expr] = []
                    for item in methods_expr.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            upper.append(ast.Constant(value=item.value.upper()))
                        else:
                            upper.append(item)
                    methods_expr = ast.List(elts=upper, ctx=ast.Load())
        else:
            methods_expr = ast.List(
                elts=[ast.Constant(value=HTTP_DECORATOR_TO_METHODS[name][0])],
                ctx=ast.Load(),
            )

        name_kw = _get_kwarg(decorator, "name")
        include_in_schema_kw = _get_kwarg(decorator, "include_in_schema")

        return _RouteSpec(
            path=path_expr,
            methods=methods_expr,
            name=name_kw.value if name_kw is not None else None,
            include_in_schema=include_in_schema_kw.value if include_in_schema_kw is not None else None,
            line=decorator.lineno,
        )

    def _visit_function_node(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
        """Rewrite Litestar decorators on one function definition.

        Args:
            node: Function node to rewrite.

        Returns:
            Rewritten function node.
        """
        kept: list[ast.expr] = []
        collected: list[_RouteSpec] = []
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                kept.append(decorator)
                continue

            spec = self._extract_route_spec(decorator, function_name=node.name)
            if spec is None:
                kept.append(decorator)
                continue

            collected.append(spec)
            self.applied_rules.add("litestar_decorators_to_paths")
            self._routing_imports.add("Path")

        if collected:
            self._route_specs.setdefault(node.name, []).extend(collected)
            node.decorator_list = kept

        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        """Visit and rewrite synchronous function definitions.

        Args:
            node: Function definition node.

        Returns:
            Rewritten function node.
        """
        return self._visit_function_node(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        """Visit and rewrite async function definitions.

        Args:
            node: Async function definition node.

        Returns:
            Rewritten function node.
        """
        return self._visit_function_node(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST | list[ast.stmt] | None:
        """Rewrite Litestar imports into Lilya imports.

        Args:
            node: Import-from statement node.

        Returns:
            Rewritten import statement(s) or original node.
        """
        if node.module != "litestar":
            return node

        lilya_apps_aliases: list[ast.alias] = []
        lilya_routing_aliases: list[ast.alias] = []
        remaining_aliases: list[ast.alias] = []
        consumed_decorator_import = False

        for alias in node.names:
            if alias.name == "Litestar":
                lilya_apps_aliases.append(ast.alias(name="Lilya", asname=alias.asname or "Litestar"))
                self._needs_lilya_app_import = True
            elif alias.name == "Router":
                lilya_routing_aliases.append(ast.alias(name="Router", asname=alias.asname))
                self._routing_imports.add(alias.asname or "Router")
            elif alias.name in SUPPORTED_DECORATORS:
                consumed_decorator_import = True
            else:
                remaining_aliases.append(alias)

        if consumed_decorator_import:
            lilya_routing_aliases.append(ast.alias(name="Path", asname=None))
            self._routing_imports.add("Path")

        if any(alias.name == "Router" for alias in lilya_routing_aliases):
            lilya_routing_aliases.append(ast.alias(name="Include", asname=None))
            self._routing_imports.add("Include")

        dedup_routing: dict[tuple[str, str | None], ast.alias] = {}
        for alias in lilya_routing_aliases:
            dedup_routing[(alias.name, alias.asname)] = alias
        lilya_routing_aliases = list(dedup_routing.values())

        statements: list[ast.stmt] = []
        if lilya_apps_aliases:
            statements.append(ast.ImportFrom(module="lilya.apps", names=lilya_apps_aliases, level=0))
        if lilya_routing_aliases:
            statements.append(ast.ImportFrom(module="lilya.routing", names=lilya_routing_aliases, level=0))
        if remaining_aliases:
            statements.append(ast.ImportFrom(module=node.module, names=remaining_aliases, level=node.level))

        if lilya_apps_aliases or lilya_routing_aliases or consumed_decorator_import:
            self.applied_rules.add("litestar_imports_to_lilya")

        return statements or None

    def _build_path_call(self, function_name: str, spec: _RouteSpec) -> ast.Call:
        """Build a Lilya ``Path`` expression for one function route.

        Args:
            function_name: Route function name.
            spec: Extracted route metadata.

        Returns:
            A ``Path(...)`` call expression.
        """
        keywords: list[ast.keyword] = []
        if spec.methods is not None:
            keywords.append(ast.keyword(arg="methods", value=spec.methods))
        if spec.name is not None:
            keywords.append(ast.keyword(arg="name", value=spec.name))
        if spec.include_in_schema is not None:
            keywords.append(ast.keyword(arg="include_in_schema", value=spec.include_in_schema))

        self._routing_imports.add("Path")
        return ast.Call(
            func=ast.Name(id="Path", ctx=ast.Load()),
            args=[spec.path, ast.Name(id=function_name, ctx=ast.Load())],
            keywords=keywords,
        )

    def _normalize_prefix_expr(self, prefix: ast.expr, *, line: int) -> ast.expr:
        """Normalize include prefix expressions.

        Args:
            prefix: Prefix expression to normalize.
            line: Source line for diagnostics.

        Returns:
            Normalized prefix expression.
        """
        if isinstance(prefix, ast.Constant) and isinstance(prefix.value, str):
            return ast.Constant(value=_normalize_path(prefix.value))

        self._diag(
            code="convert.litestar.dynamic_router_path",
            message=(
                "Dynamic Litestar Router path values were kept as-is; ensure the generated Include path is valid "
                "for Lilya."
            ),
            line=line,
        )
        return prefix

    def _rewrite_router_call(self, call: ast.Call, *, owner_name: str | None) -> tuple[ast.Call, ast.expr]:
        """Rewrite a Litestar ``Router(...)`` call into Lilya-compatible kwargs.

        Args:
            call: Router constructor call.
            owner_name: Optional assigned name for prefix tracking.

        Returns:
            Tuple of rewritten call and extracted router path prefix expression.
        """
        prefix_expr: ast.expr | None = None
        route_handlers_expr: ast.expr | None = None

        positional = list(call.args)
        if positional:
            prefix_expr = positional.pop(0)
        if positional:
            self._diag(
                code="convert.litestar.router_positional_removed",
                message="Removed unsupported positional Router(...) arguments after path.",
                line=call.lineno,
            )

        kept_keywords: list[ast.keyword] = []
        removed_kwargs: list[str] = []
        for keyword in call.keywords:
            if keyword.arg == "path":
                prefix_expr = keyword.value
            elif keyword.arg == "route_handlers":
                route_handlers_expr = keyword.value
            elif keyword.arg is None:
                kept_keywords.append(keyword)
            elif keyword.arg in SUPPORTED_LILYA_ROUTER_KWARGS:
                kept_keywords.append(keyword)
            else:
                removed_kwargs.append(keyword.arg)

        if route_handlers_expr is not None:
            routes_expr = self._convert_route_handlers(route_handlers_expr, owner="Router", line=call.lineno)
            kept_keywords.append(ast.keyword(arg="routes", value=routes_expr))
            self.applied_rules.add("litestar_app_route_handlers_to_routes")

        if removed_kwargs:
            self._diag(
                code="convert.litestar.router_kwargs_removed",
                message=("Removed unsupported Litestar Router kwargs: " + ", ".join(sorted(removed_kwargs))),
                line=call.lineno,
            )
            self.applied_rules.add("litestar_constructor_kwargs_filtered")

        if prefix_expr is None:
            prefix_expr = ast.Constant(value="/")

        prefix_expr = self._normalize_prefix_expr(prefix_expr, line=call.lineno)

        call.args = []
        call.keywords = kept_keywords

        if owner_name is not None:
            self._router_prefix[owner_name] = prefix_expr

        return call, prefix_expr

    def _expand_route_handler(self, handler: ast.expr, *, owner: str, line: int) -> list[ast.expr]:
        """Expand one Litestar route handler entry to Lilya route/include entries.

        Args:
            handler: Route handler expression from ``route_handlers``.
            owner: Owning constructor kind (``Litestar`` or ``Router``).
            line: Source line for diagnostics.

        Returns:
            Expanded list of route/include expressions.
        """
        if isinstance(handler, ast.Name):
            if handler.id in self._route_specs:
                return [self._build_path_call(handler.id, spec) for spec in self._route_specs[handler.id]]

            if owner == "Litestar" and handler.id in self._router_prefix:
                self._routing_imports.add("Include")
                self.applied_rules.add("litestar_router_path_to_include")
                return [
                    ast.Call(
                        func=ast.Name(id="Include", ctx=ast.Load()),
                        args=[],
                        keywords=[
                            ast.keyword(arg="path", value=self._router_prefix[handler.id]),
                            ast.keyword(arg="app", value=handler),
                        ],
                    )
                ]

            return [handler]

        if owner == "Litestar" and isinstance(handler, ast.Call):
            if isinstance(handler.func, ast.Name) and handler.func.id == "Router":
                rewritten, prefix = self._rewrite_router_call(handler, owner_name=None)
                self._routing_imports.add("Include")
                self.applied_rules.add("litestar_router_path_to_include")
                return [
                    ast.Call(
                        func=ast.Name(id="Include", ctx=ast.Load()),
                        args=[],
                        keywords=[
                            ast.keyword(arg="path", value=prefix),
                            ast.keyword(arg="app", value=rewritten),
                        ],
                    )
                ]

        return [handler]

    def _convert_route_handlers(self, handlers_expr: ast.expr, *, owner: str, line: int) -> ast.expr:
        """Convert Litestar ``route_handlers`` expressions into Lilya ``routes``.

        Args:
            handlers_expr: Input route handlers expression.
            owner: Owning constructor kind.
            line: Source line for diagnostics.

        Returns:
            Converted routes expression.
        """
        if not isinstance(handlers_expr, (ast.List, ast.Tuple)):
            self._diag(
                code="convert.litestar.route_handlers_shape",
                message=(
                    "Litestar route_handlers was not a list/tuple and was kept unchanged; "
                    "manual route conversion may be required."
                ),
                line=line,
            )
            return handlers_expr

        expanded: list[ast.expr] = []
        for item in handlers_expr.elts:
            expanded.extend(self._expand_route_handler(item, owner=owner, line=line))

        return ast.List(elts=expanded, ctx=ast.Load())

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """Rewrite Litestar/Router constructor assignments.

        Args:
            node: Assignment node.

        Returns:
            Rewritten assignment node when applicable.
        """
        self.generic_visit(node)
        if not isinstance(node.value, ast.Call):
            return node

        if not isinstance(node.value.func, ast.Name):
            return node

        constructor = node.value.func.id
        if constructor not in {"Litestar", "Router"}:
            return node

        target_name: str | None = None
        if node.targets and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id

        if constructor == "Router":
            rewritten_call, _prefix = self._rewrite_router_call(node.value, owner_name=target_name)
            node.value = rewritten_call
            return node

        # Litestar app conversion.
        call = node.value
        route_handlers_expr: ast.expr | None = None
        positional = list(call.args)
        if positional:
            route_handlers_expr = positional.pop(0)
        if positional:
            self._diag(
                code="convert.litestar.app_positional_removed",
                message="Removed unsupported positional Litestar(...) arguments after route_handlers.",
                line=call.lineno,
            )

        kept_keywords: list[ast.keyword] = []
        removed_kwargs: list[str] = []
        for keyword in call.keywords:
            if keyword.arg == "route_handlers":
                route_handlers_expr = keyword.value
            elif keyword.arg == "path":
                removed_kwargs.append("path")
            else:
                kept_keywords.append(keyword)

        if route_handlers_expr is not None:
            routes_expr = self._convert_route_handlers(route_handlers_expr, owner="Litestar", line=call.lineno)
            kept_keywords.append(ast.keyword(arg="routes", value=routes_expr))
            self.applied_rules.add("litestar_app_route_handlers_to_routes")

        if removed_kwargs:
            self._diag(
                code="convert.litestar.app_kwargs_removed",
                message="Removed unsupported Litestar app kwargs: " + ", ".join(sorted(removed_kwargs)),
                line=call.lineno,
            )
            self.applied_rules.add("litestar_constructor_kwargs_filtered")

        call.args = []
        call.keywords = kept_keywords
        self._needs_lilya_app_import = True
        return node


def _imported_names(tree: ast.Module, module: str) -> set[str]:
    """Return imported symbol names for a module-level import target.

    Args:
        tree: Module AST.
        module: Import module name.

    Returns:
        Imported symbol names using aliases when present.
    """
    names: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module == module:
            names.update(alias.asname or alias.name for alias in statement.names)
    return names


def _insert_import(tree: ast.Module, statement: ast.ImportFrom) -> None:
    """Insert an import statement after docstring and future imports.

    Args:
        tree: Module AST.
        statement: Import statement to insert.
    """
    insertion_index = 0
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        insertion_index = 1

    while insertion_index < len(tree.body):
        candidate = tree.body[insertion_index]
        if not isinstance(candidate, ast.ImportFrom) or candidate.module != "__future__":
            break
        insertion_index += 1

    tree.body.insert(insertion_index, statement)


def _ensure_support_nodes(tree: ast.Module, transformer: _LitestarTransformer) -> None:
    """Ensure required Lilya imports are present in the module AST.

    Args:
        tree: Transformed module AST.
        transformer: Transformer state.
    """
    app_imported = _imported_names(tree, "lilya.apps")
    if transformer._needs_lilya_app_import and "Litestar" not in app_imported:
        _insert_import(
            tree,
            ast.ImportFrom(module="lilya.apps", names=[ast.alias(name="Lilya", asname="Litestar")], level=0),
        )

    required_routing = {name for name in transformer._routing_imports if name in {"Path", "Include", "Router"}}
    imported_routing = _imported_names(tree, "lilya.routing")
    missing_routing = sorted(required_routing - imported_routing)
    if missing_routing:
        aliases = [ast.alias(name=name, asname=None) for name in missing_routing]
        _insert_import(tree, ast.ImportFrom(module="lilya.routing", names=aliases, level=0))


def _apply_module_transformation(tree: ast.Module, relative_path: str) -> tuple[ast.Module, _LitestarTransformer]:
    """Apply Litestar conversion rules to one parsed AST module.

    Args:
        tree: Parsed module AST.
        relative_path: Project-relative path for diagnostics.

    Returns:
        Tuple of transformed AST and transformer state.
    """
    transformer = _LitestarTransformer(relative_path=relative_path)
    updated = transformer.visit(tree)
    assert isinstance(updated, ast.Module)
    _ensure_support_nodes(updated, transformer)
    ast.fix_missing_locations(updated)
    return updated, transformer


def transform_python_source(source: str, relative_path: str) -> TransformResult:
    """Transform Litestar source text into Lilya-compatible source text.

    Args:
        source: Source module text.
        relative_path: Project-relative path for diagnostics and diffs.

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
    """Transform one Litestar source file from disk.

    Args:
        path: Source file path.
        source_root: Source root for relative diff labels.

    Returns:
        Per-file transformation result.
    """
    source = path.read_text(encoding="utf-8")
    relative_path = str(path.resolve().relative_to(source_root.resolve()))
    return transform_python_source(source=source, relative_path=relative_path)
