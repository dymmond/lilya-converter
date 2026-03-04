"""AST transformation pipeline for FastAPI-to-Lilya conversion.

This module applies deterministic, repo-grounded rewriting rules and emits
diagnostics for unsupported or partial mappings.
"""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass
from pathlib import Path

from lilya_converter.models import Diagnostic

ROUTE_METHODS = {
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

LILYA_WEBSOCKET_ROUTE_KWARGS = {
    "name",
    "middleware",
    "permissions",
    "exception_handlers",
    "dependencies",
    "before_request",
    "after_request",
}

SUPPORTED_FASTAPI_KWARGS = {
    "debug",
    "routes",
    "middleware",
    "exception_handlers",
    "dependencies",
    "on_startup",
    "on_shutdown",
    "lifespan",
    "include_in_schema",
    "root_path",
    "enable_openapi",
    "openapi_config",
}

SUPPORTED_ROUTER_KWARGS = {
    "routes",
    "redirect_slashes",
    "on_startup",
    "on_shutdown",
    "lifespan",
}

FASTAPI_MIDDLEWARE_MODULE_MAP = {
    "fastapi.middleware.gzip": "lilya.middleware.compression",
    "fastapi.middleware.cors": "lilya.middleware.cors",
    "fastapi.middleware.httpsredirect": "lilya.middleware.httpsredirect",
    "fastapi.middleware.trustedhost": "lilya.middleware.trustedhost",
}


def _expr_to_str(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def _get_kwarg(call: ast.Call, name: str) -> ast.keyword | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw
    return None


def _is_name_or_attr(node: ast.AST, name: str) -> bool:
    return (isinstance(node, ast.Name) and node.id == name) or (isinstance(node, ast.Attribute) and node.attr == name)


def _is_depends_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and _is_name_or_attr(node.func, "Depends")


def _path_join(left: str, right: str) -> str:
    left = left.rstrip("/")
    right = right.lstrip("/")
    if not left and not right:
        return ""
    if not left:
        return f"/{right}" if not right.startswith("/") else right
    if not right:
        return left if left.startswith("/") else f"/{left}"
    return f"{left}/{right}"


def _sanitize_identifier(value: str) -> str:
    text = "".join(char if char.isalnum() else "_" for char in value)
    text = text.strip("_")
    if not text:
        text = "dependency"
    if text[0].isdigit():
        text = f"dep_{text}"
    return text


def _extract_annotated(node: ast.AST) -> tuple[ast.expr | None, list[ast.expr] | None]:
    if not isinstance(node, ast.Subscript):
        return None, None
    if not _is_name_or_attr(node.value, "Annotated"):
        return None, None
    if isinstance(node.slice, ast.Tuple) and node.slice.elts:
        return node.slice.elts[0], list(node.slice.elts[1:])
    return None, None


@dataclass
class _DependencyEntry:
    key: str
    provider: ast.expr
    requires_synthetic_param: bool


@dataclass
class TransformResult:
    """Represents the transformation result for one Python module.

    Attributes:
        content: Transformed Python source text.
        changed: Whether transformed content differs from input.
        diagnostics: Ordered diagnostics emitted during transformation.
        applied_rules: Ordered list of applied rule IDs.
        unified_diff: Unified diff between original and transformed source.
    """

    content: str
    changed: bool
    diagnostics: list[Diagnostic]
    applied_rules: list[str]
    unified_diff: str


class _CoreTransformer(ast.NodeTransformer):
    """Rule-driven AST transformer for a single source module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize per-module transformation state.

        Args:
            relative_path: Project-relative file path of the module being transformed.
        """
        self.relative_path = relative_path
        self.diagnostics: list[Diagnostic] = []
        self.applied_rules: set[str] = set()
        self.requires_dependency_import = False
        self.requires_add_exception_handler = False

        self._router_prefix: dict[str, ast.expr] = {}
        self._owner_dependencies: dict[str, list[_DependencyEntry]] = {}
        self._exception_handler_regs: list[tuple[str, ast.expr, str, int]] = []

    def _diag(
        self,
        code: str,
        message: str,
        line: int | None = None,
        severity: str = "warning",
    ) -> None:
        self.diagnostics.append(
            Diagnostic(
                code=code,
                message=message,
                severity=severity,  # type: ignore[arg-type]
                file=self.relative_path,
                line=line,
            )
        )

    def _build_provider_call(self, depends_call: ast.Call) -> ast.expr | None:
        dependency_expr: ast.expr | None = None
        use_cache_expr: ast.expr | None = None
        scope_expr: ast.expr | None = None

        if depends_call.args:
            dependency_expr = depends_call.args[0]

        for kw in depends_call.keywords:
            if kw.arg == "dependency":
                dependency_expr = kw.value
            elif kw.arg == "use_cache":
                use_cache_expr = kw.value
            elif kw.arg == "scope":
                scope_expr = kw.value

        if dependency_expr is None:
            self._diag(
                code="convert.depends.missing_dependency",
                message=(
                    "Found Depends() without an explicit dependency callable. This pattern requires manual conversion."
                ),
                line=depends_call.lineno,
            )
            return None

        if scope_expr is not None:
            self._diag(
                code="convert.depends.scope_partial",
                message=(
                    "FastAPI Depends(scope=...) does not have a direct Lilya equivalent; scope was not translated."
                ),
                line=depends_call.lineno,
            )

        keywords: list[ast.keyword] = []
        if use_cache_expr is not None:
            if not (isinstance(use_cache_expr, ast.Constant) and use_cache_expr.value is True):
                keywords.append(ast.keyword(arg="use_cache", value=use_cache_expr))

        self.requires_dependency_import = True
        self.applied_rules.add("depends_to_provide")
        return ast.Call(func=ast.Name(id="Provide", ctx=ast.Load()), args=[dependency_expr], keywords=keywords)

    def _dependency_key_from_expr(self, expr: ast.AST, fallback_prefix: str = "_dep") -> str:
        base = ""
        if isinstance(expr, ast.Name):
            base = expr.id
        elif isinstance(expr, ast.Attribute):
            base = expr.attr
        elif isinstance(expr, ast.Call):
            base = self._dependency_key_from_expr(expr.func, fallback_prefix=fallback_prefix)
        else:
            base = fallback_prefix
        return _sanitize_identifier(base)

    def _depends_list_to_entries(
        self,
        node: ast.AST,
        source: str,
    ) -> list[_DependencyEntry]:
        values: list[ast.AST] = []
        if isinstance(node, (ast.List, ast.Tuple)):
            values = list(node.elts)
        else:
            self._diag(
                code="convert.depends.list_shape",
                message=(
                    f"Expected '{source}' dependencies to be a list/tuple of Depends(...); manual conversion required."
                ),
                line=getattr(node, "lineno", None),
            )
            return []

        entries: list[_DependencyEntry] = []
        used_keys: set[str] = set()
        for value in values:
            if not _is_depends_call(value):
                self._diag(
                    code="convert.depends.non_depends_item",
                    message=f"Unsupported dependency item in '{source}': {_expr_to_str(value)}",
                    line=getattr(value, "lineno", None),
                )
                continue

            provider = self._build_provider_call(value)  # type: ignore[arg-type]
            if provider is None:
                continue
            assert isinstance(value, ast.Call)
            depends_call = value
            dep_expr = depends_call.args[0] if depends_call.args else _get_kwarg(depends_call, "dependency")
            dep_node = dep_expr if isinstance(dep_expr, ast.AST) else getattr(dep_expr, "value", None)
            key_base = self._dependency_key_from_expr(dep_node or depends_call)
            key = key_base
            index = 1
            while key in used_keys:
                index += 1
                key = f"{key_base}_{index}"
            used_keys.add(key)
            entries.append(
                _DependencyEntry(
                    key=f"_{key}",
                    provider=provider,
                    requires_synthetic_param=True,
                )
            )
        return entries

    def _entries_to_dict_expr(self, entries: list[_DependencyEntry]) -> ast.Dict:
        dedup: dict[str, _DependencyEntry] = {}
        for entry in entries:
            dedup[entry.key] = entry
        ordered = sorted(dedup.values(), key=lambda item: item.key)
        return ast.Dict(
            keys=[ast.Constant(value=item.key) for item in ordered],
            values=[item.provider for item in ordered],
        )

    def _add_synthetic_kwonly_param(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        key: str,
    ) -> None:
        existing = {arg.arg for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]}
        target_name = key
        if target_name in existing:
            return

        name = target_name
        index = 1
        while name in existing:
            index += 1
            name = f"{target_name}_{index}"
        node.args.kwonlyargs.append(ast.arg(arg=name, annotation=None, type_comment=None))
        node.args.kw_defaults.append(ast.Call(func=ast.Name(id="Provides", ctx=ast.Load()), args=[], keywords=[]))
        self.requires_dependency_import = True
        self.applied_rules.add("decorator_dependencies_to_provide")

    def _rewrite_function_depends(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[_DependencyEntry]:
        entries: list[_DependencyEntry] = []
        positional = [*node.args.posonlyargs, *node.args.args]
        defaults = list(node.args.defaults)
        offset = len(positional) - len(defaults)

        for idx, arg in enumerate(positional):
            default_index = idx - offset
            default = defaults[default_index] if default_index >= 0 else None
            if default is not None and _is_depends_call(default):
                provider = self._build_provider_call(default)  # type: ignore[arg-type]
                if provider is not None:
                    entries.append(
                        _DependencyEntry(
                            key=arg.arg,
                            provider=provider,
                            requires_synthetic_param=False,
                        )
                    )
                    defaults[default_index] = ast.Call(
                        func=ast.Name(id="Provides", ctx=ast.Load()),
                        args=[],
                        keywords=[],
                    )
                    self.requires_dependency_import = True
                    self.applied_rules.add("depends_default_to_provides")

            base_annotation, meta = _extract_annotated(arg.annotation) if arg.annotation else (None, None)
            if base_annotation is not None and meta is not None:
                next_meta: list[ast.expr] = []
                converted = False
                for item in meta:
                    if _is_depends_call(item):
                        provider = self._build_provider_call(item)  # type: ignore[arg-type]
                        if provider is not None:
                            entries.append(
                                _DependencyEntry(
                                    key=arg.arg,
                                    provider=provider,
                                    requires_synthetic_param=False,
                                )
                            )
                            converted = True
                            self.applied_rules.add("annotated_depends_to_provide")
                    else:
                        next_meta.append(item)

                if converted:
                    if next_meta:
                        arg.annotation = ast.Subscript(
                            value=ast.Name(id="Annotated", ctx=ast.Load()),
                            slice=ast.Tuple(elts=[base_annotation, *next_meta], ctx=ast.Load()),
                            ctx=ast.Load(),
                        )
                    else:
                        arg.annotation = base_annotation

        node.args.defaults = defaults

        for idx, (arg, default) in enumerate(zip(node.args.kwonlyargs, node.args.kw_defaults, strict=False)):
            if default is not None and _is_depends_call(default):
                provider = self._build_provider_call(default)
                if provider is not None:
                    entries.append(
                        _DependencyEntry(
                            key=arg.arg,
                            provider=provider,
                            requires_synthetic_param=False,
                        )
                    )
                    node.args.kw_defaults[idx] = ast.Call(
                        func=ast.Name(id="Provides", ctx=ast.Load()),
                        args=[],
                        keywords=[],
                    )
                    self.requires_dependency_import = True
                    self.applied_rules.add("depends_kwonly_to_provides")

        return entries

    def _warn_non_route_depends(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        positional = [*node.args.posonlyargs, *node.args.args]
        defaults = list(node.args.defaults)
        offset = len(positional) - len(defaults)
        depends_found = False
        for idx, arg in enumerate(positional):
            default_index = idx - offset
            default = defaults[default_index] if default_index >= 0 else None
            if default is not None and _is_depends_call(default):
                depends_found = True
            if arg.annotation is not None and "Depends(" in _expr_to_str(arg.annotation):
                depends_found = True

        for default in node.args.kw_defaults:
            if default is not None and _is_depends_call(default):
                depends_found = True

        if depends_found:
            self._diag(
                code="convert.depends.non_route_untouched",
                message=(
                    f"Non-route function '{node.name}' uses Depends(...). "
                    "Converter leaves it unchanged; review manually."
                ),
                line=node.lineno,
            )

    def _handle_route_decorators(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        param_entries: list[_DependencyEntry],
    ) -> None:
        def apply_router_prefix(decorator: ast.Call, owner: str) -> None:
            if owner not in self._router_prefix:
                return

            prefix_expr = self._router_prefix[owner]
            path_expr: ast.expr | None = None
            target = "missing"
            if decorator.args:
                target = "arg"
                path_expr = decorator.args[0]
            else:
                for keyword in decorator.keywords:
                    if keyword.arg == "path":
                        target = "kw"
                        path_expr = keyword.value
                        break

            if path_expr is None:
                self._diag(
                    code="convert.router_prefix.missing_path",
                    message=(f"Router '{owner}' had prefix but route decorator on '{node.name}' has no explicit path."),
                    line=decorator.lineno,
                )
                return

            if (
                isinstance(prefix_expr, ast.Constant)
                and isinstance(prefix_expr.value, str)
                and isinstance(path_expr, ast.Constant)
                and isinstance(path_expr.value, str)
            ):
                new_path = ast.Constant(value=_path_join(prefix_expr.value, path_expr.value))
                if target == "arg":
                    decorator.args[0] = new_path
                else:
                    for keyword in decorator.keywords:
                        if keyword.arg == "path":
                            keyword.value = new_path
                            break
                self.applied_rules.add("router_prefix_to_route_path")
                return

            self._diag(
                code="convert.router_prefix.dynamic_path",
                message=(
                    f"Router '{owner}' prefix could not be merged into dynamic route path for '{node.name}'. "
                    "Manual review required."
                ),
                line=decorator.lineno,
            )

        def normalize_method(decorator: ast.Call, method: str) -> str:
            if method == "api_route":
                decorator.func.attr = "route"  # type: ignore[attr-defined]
                if _get_kwarg(decorator, "methods") is None:
                    decorator.keywords.append(
                        ast.keyword(
                            arg="methods",
                            value=ast.List(elts=[ast.Constant(value="GET")], ctx=ast.Load()),
                        )
                    )
                self.applied_rules.add("api_route_to_route")
                return "route"

            if method == "trace":
                decorator.func.attr = "route"  # type: ignore[attr-defined]
                decorator.keywords = [kw for kw in decorator.keywords if kw.arg != "methods"]
                decorator.keywords.append(
                    ast.keyword(
                        arg="methods",
                        value=ast.List(elts=[ast.Constant(value="TRACE")], ctx=ast.Load()),
                    )
                )
                self.applied_rules.add("trace_to_route")
                return "route"

            return method

        function_param_names = {arg.arg for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]}
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue

            owner = decorator.func.value.id if isinstance(decorator.func.value, ast.Name) else None
            method = decorator.func.attr
            if owner is None or method not in ROUTE_METHODS:
                continue

            apply_router_prefix(decorator, owner)
            normalized_method = normalize_method(decorator, method)
            allowed_kwargs = (
                LILYA_WEBSOCKET_ROUTE_KWARGS if normalized_method == "websocket" else LILYA_HTTP_ROUTE_KWARGS
            )

            all_entries: list[_DependencyEntry] = list(param_entries)
            all_entries.extend(self._owner_dependencies.get(owner, []))

            dep_kw = _get_kwarg(decorator, "dependencies")
            if dep_kw is not None:
                all_entries.extend(self._depends_list_to_entries(dep_kw.value, source=f"{owner}.{method}"))
                decorator.keywords = [kw for kw in decorator.keywords if kw.arg != "dependencies"]

            removed_kwargs: list[str] = []
            kept_keywords: list[ast.keyword] = []
            for kw in decorator.keywords:
                if kw.arg is None:
                    kept_keywords.append(kw)
                    continue
                if kw.arg in allowed_kwargs:
                    kept_keywords.append(kw)
                else:
                    removed_kwargs.append(kw.arg)
            decorator.keywords = kept_keywords

            if removed_kwargs:
                self._diag(
                    code="convert.route.kwargs_removed",
                    message=(
                        f"Removed unsupported FastAPI decorator kwargs on '{node.name}': "
                        f"{', '.join(sorted(removed_kwargs))}"
                    ),
                    line=decorator.lineno,
                )

            if all_entries:
                dict_expr = self._entries_to_dict_expr(all_entries)
                decorator.keywords = [kw for kw in decorator.keywords if kw.arg not in {"dependencies"}]
                decorator.keywords.append(ast.keyword(arg="dependencies", value=dict_expr))
                self.applied_rules.add("route_dependencies_dict")
                for entry in all_entries:
                    if entry.requires_synthetic_param and entry.key not in function_param_names:
                        self._add_synthetic_kwonly_param(node, entry.key)
                        function_param_names.add(entry.key)

    def _collect_constructor_dependencies(
        self,
        owner: str,
        call: ast.Call,
    ) -> None:
        dep_kw = _get_kwarg(call, "dependencies")
        if dep_kw is None:
            return
        entries = self._depends_list_to_entries(dep_kw.value, source=f"{owner}.constructor")
        if not entries:
            return
        dep_kw.value = self._entries_to_dict_expr(entries)
        self._owner_dependencies[owner] = entries
        self.applied_rules.add("constructor_dependencies_to_dict")

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        self.generic_visit(node)
        if not isinstance(node.value, ast.Call):
            return node
        if not node.targets or not isinstance(node.targets[0], ast.Name):
            return node
        owner = node.targets[0].id
        call = node.value
        if isinstance(call.func, ast.Name) and call.func.id in {"FastAPI", "APIRouter"}:
            is_app = call.func.id == "FastAPI"
            supported = SUPPORTED_FASTAPI_KWARGS if is_app else SUPPORTED_ROUTER_KWARGS

            if not is_app:
                prefix_kw = _get_kwarg(call, "prefix")
                if prefix_kw is not None:
                    self._router_prefix[owner] = prefix_kw.value
                    call.keywords = [kw for kw in call.keywords if kw is not prefix_kw]
                    self.applied_rules.add("router_prefix_extracted")

            self._collect_constructor_dependencies(owner=owner, call=call)

            if is_app:
                openapi_kw = _get_kwarg(call, "openapi_url")
                if openapi_kw is not None:
                    value = openapi_kw.value
                    enabled = not (isinstance(value, ast.Constant) and value.value is None)
                    call.keywords = [kw for kw in call.keywords if kw is not openapi_kw]
                    if _get_kwarg(call, "enable_openapi") is None:
                        call.keywords.append(ast.keyword(arg="enable_openapi", value=ast.Constant(value=enabled)))
                    self.applied_rules.add("openapi_flag_conversion")

            kept: list[ast.keyword] = []
            removed: list[str] = []
            for kw in call.keywords:
                if kw.arg is None:
                    kept.append(kw)
                    continue
                if kw.arg in supported:
                    kept.append(kw)
                else:
                    removed.append(kw.arg)
            call.keywords = kept
            if removed:
                self._diag(
                    code="convert.constructor.kwargs_removed",
                    message=(f"Removed unsupported {call.func.id} kwargs for '{owner}': {', '.join(sorted(removed))}"),
                    line=node.lineno,
                )
        return node

    def _rewrite_include_router_call(self, node: ast.Call) -> ast.Call:
        if not isinstance(node.func, ast.Attribute):
            return node
        if node.func.attr != "include_router":
            return node

        owner = node.func.value.id if isinstance(node.func.value, ast.Name) else "<unknown>"
        router_expr: ast.expr | None = None
        prefix_expr: ast.expr | None = None
        include_in_schema_expr: ast.expr | None = None
        include_dep_expr: ast.expr | None = None

        if node.args:
            router_expr = node.args[0]
        for keyword in node.keywords:
            if keyword.arg == "router":
                router_expr = keyword.value
            elif keyword.arg == "prefix":
                prefix_expr = keyword.value
            elif keyword.arg == "include_in_schema":
                include_in_schema_expr = keyword.value
            elif keyword.arg == "dependencies":
                include_dep_expr = keyword.value

        if router_expr is None:
            self._diag(
                code="convert.include_router.missing_router",
                message="Could not resolve include_router() router argument.",
                line=node.lineno,
                severity="error",
            )
            return node

        path_expr: ast.expr
        if prefix_expr is not None:
            path_expr = prefix_expr
        else:
            path_expr = ast.Constant(value="/")

        if isinstance(path_expr, ast.Constant) and path_expr.value == "":
            path_expr = ast.Constant(value="/")

        keywords: list[ast.keyword] = [
            ast.keyword(arg="path", value=path_expr),
            ast.keyword(arg="app", value=router_expr),
        ]
        if include_in_schema_expr is not None:
            keywords.append(ast.keyword(arg="include_in_schema", value=include_in_schema_expr))

        if include_dep_expr is not None:
            entries = self._depends_list_to_entries(include_dep_expr, source=f"{owner}.include_router")
            if entries:
                keywords.append(ast.keyword(arg="dependencies", value=self._entries_to_dict_expr(entries)))

        dropped = []
        supported = {"router", "prefix", "dependencies", "include_in_schema"}
        for kw in node.keywords:
            if kw.arg and kw.arg not in supported:
                dropped.append(kw.arg)
        if dropped:
            self._diag(
                code="convert.include_router.kwargs_removed",
                message=(f"Removed unsupported include_router kwargs: {', '.join(sorted(dropped))}"),
                line=node.lineno,
            )

        self.applied_rules.add("include_router_to_include")
        node.func.attr = "include"
        node.args = []
        node.keywords = keywords
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "include_router":
            return self._rewrite_include_router_call(node)
        return node

    def _rewrite_function_decorators(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        decorators: list[ast.expr] = []
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                decorators.append(decorator)
                continue
            if not isinstance(decorator.func, ast.Attribute):
                decorators.append(decorator)
                continue

            owner = decorator.func.value.id if isinstance(decorator.func.value, ast.Name) else None
            attr = decorator.func.attr
            if owner is None:
                decorators.append(decorator)
                continue

            if attr == "exception_handler":
                if decorator.args:
                    self._exception_handler_regs.append((owner, decorator.args[0], node.name, decorator.lineno))
                    self.requires_add_exception_handler = True
                    self.applied_rules.add("exception_handler_decorator_to_call")
                else:
                    self._diag(
                        code="convert.exception_handler.missing_exception",
                        message="Found exception_handler decorator without exception type argument.",
                        line=decorator.lineno,
                    )
                continue

            if attr == "middleware":
                self._diag(
                    code="convert.middleware.decorator_removed",
                    message=(
                        "Removed FastAPI @app.middleware(...) decorator. "
                        "Manual conversion to Lilya class-based middleware is required."
                    ),
                    line=decorator.lineno,
                )
                continue

            decorators.append(decorator)

        node.decorator_list = decorators

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
        self._rewrite_function_decorators(node)
        has_route = any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr in ROUTE_METHODS
            for decorator in node.decorator_list
        )
        if has_route:
            param_entries = self._rewrite_function_depends(node)
            self._handle_route_decorators(node, param_entries)
        else:
            self._warn_non_route_depends(node)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._visit_function(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST | list[ast.stmt] | None:
        if node.module == "fastapi":
            grouped: dict[str, list[ast.alias]] = {}
            remaining: list[ast.alias] = []

            def add(module: str, alias: ast.alias) -> None:
                grouped.setdefault(module, []).append(alias)

            for alias in node.names:
                name = alias.name
                local_name = alias.asname
                if name == "FastAPI":
                    add("lilya.apps", ast.alias(name="Lilya", asname=local_name or "FastAPI"))
                elif name == "APIRouter":
                    add("lilya.routing", ast.alias(name="Router", asname=local_name or "APIRouter"))
                elif name in {"Query", "Header", "Cookie"}:
                    add("lilya.params", ast.alias(name=name, asname=local_name))
                elif name == "Request":
                    add("lilya.requests", ast.alias(name="Request", asname=local_name))
                elif name == "WebSocket":
                    add("lilya.websockets", ast.alias(name="WebSocket", asname=local_name))
                elif name == "HTTPException":
                    add("lilya.exceptions", ast.alias(name="HTTPException", asname=local_name))
                elif name == "status":
                    add("lilya", ast.alias(name="status", asname=local_name))
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
            return statements or None

        if node.module == "fastapi.responses":
            mapped: list[ast.alias] = []
            remaining: list[ast.alias] = []
            for alias in node.names:
                name = alias.name
                asname = alias.asname
                if name == "PlainTextResponse":
                    mapped.append(ast.alias(name="PlainText", asname=asname or "PlainTextResponse"))
                elif name in {
                    "JSONResponse",
                    "Response",
                    "RedirectResponse",
                    "StreamingResponse",
                    "FileResponse",
                    "HTMLResponse",
                }:
                    mapped.append(ast.alias(name=name, asname=asname))
                elif name in {"UJSONResponse", "ORJSONResponse"}:
                    mapped.append(ast.alias(name="JSONResponse", asname=asname or name))
                    self._diag(
                        code="convert.response_class.orjson_ujson",
                        message=(f"Mapped '{name}' to Lilya JSONResponse. Behavior can differ; verify manually."),
                        line=node.lineno,
                    )
                else:
                    remaining.append(alias)

            statements: list[ast.stmt] = []
            if mapped:
                statements.append(ast.ImportFrom(module="lilya.responses", names=mapped, level=0))
            if remaining:
                statements.append(ast.ImportFrom(module=node.module, names=remaining, level=node.level))
            return statements or None

        if node.module in FASTAPI_MIDDLEWARE_MODULE_MAP:
            return ast.ImportFrom(
                module=FASTAPI_MIDDLEWARE_MODULE_MAP[node.module],
                names=node.names,
                level=0,
            )

        return node

    def flush_exception_handler_registrations(self, tree: ast.Module) -> None:
        if not self._exception_handler_regs:
            return
        for owner, exception_expr, func_name, _line in self._exception_handler_regs:
            tree.body.append(
                ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id=owner, ctx=ast.Load()), attr="add_exception_handler", ctx=ast.Load()
                        ),
                        args=[
                            exception_expr,
                            ast.Name(id=func_name, ctx=ast.Load()),
                        ],
                        keywords=[],
                    )
                )
            )


def _has_import(tree: ast.Module, module: str, names: set[str]) -> bool:
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module == module:
            imported = {alias.asname or alias.name for alias in statement.names}
            if names.issubset(imported):
                return True
    return False


def _depends_symbol_used(tree: ast.Module) -> bool:
    class _Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.used = False

        def visit_Name(self, node: ast.Name) -> None:
            if node.id == "Depends":
                self.used = True
                return
            self.generic_visit(node)

        def visit_Attribute(self, node: ast.Attribute) -> None:
            if node.attr == "Depends":
                self.used = True
                return
            self.generic_visit(node)

    visitor = _Visitor()
    visitor.visit(tree)
    return visitor.used


def _prune_unused_fastapi_depends_import(tree: ast.Module) -> None:
    if _depends_symbol_used(tree):
        return
    next_body: list[ast.stmt] = []
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module == "fastapi":
            next_names = [name for name in statement.names if name.name != "Depends"]
            if next_names:
                statement.names = next_names
                next_body.append(statement)
            continue
        next_body.append(statement)
    tree.body = next_body


def _insert_import(tree: ast.Module, statement: ast.ImportFrom) -> None:
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


def _ensure_support_imports(tree: ast.Module, transformer: _CoreTransformer) -> None:
    if transformer.requires_dependency_import and not _has_import(tree, "lilya.dependencies", {"Provide", "Provides"}):
        _insert_import(
            tree,
            ast.ImportFrom(
                module="lilya.dependencies",
                names=[
                    ast.alias(name="Provide", asname=None),
                    ast.alias(name="Provides", asname=None),
                ],
                level=0,
            ),
        )


def _apply_module_transformation(tree: ast.Module, relative_path: str) -> tuple[ast.Module, _CoreTransformer]:
    """Apply all conversion rules to a parsed Python module.

    Args:
        tree: Parsed source module.
        relative_path: Project-relative file path used in diagnostics.

    Returns:
        A tuple with transformed module AST and transformer state.
    """
    transformer = _CoreTransformer(relative_path=relative_path)
    updated = transformer.visit(tree)
    assert isinstance(updated, ast.Module)
    transformer.flush_exception_handler_registrations(updated)
    _prune_unused_fastapi_depends_import(updated)
    _ensure_support_imports(updated, transformer)
    ast.fix_missing_locations(updated)
    return updated, transformer


def transform_python_source(source: str, relative_path: str) -> TransformResult:
    """Transform Python source text from FastAPI patterns to Lilya patterns.

    Args:
        source: Original Python source text.
        relative_path: Project-relative file path for diagnostics/diff labels.

    Returns:
        Transformation output including converted source and diagnostics.
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
        diagnostics=sorted(
            transformer.diagnostics,
            key=lambda item: (item.file or "", item.line or 0, item.code),
        ),
        applied_rules=sorted(transformer.applied_rules),
        unified_diff=diff,
    )


def transform_python_file(path: Path, source_root: Path) -> TransformResult:
    """Transform a Python file from disk.

    Args:
        path: Source file path.
        source_root: Source project root used to derive relative path labels.

    Returns:
        Transformation output for the file.
    """
    source = path.read_text(encoding="utf-8")
    relative_path = str(path.resolve().relative_to(source_root.resolve()))
    return transform_python_source(source=source, relative_path=relative_path)
