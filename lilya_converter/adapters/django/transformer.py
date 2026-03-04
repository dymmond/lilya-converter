"""AST transformation pipeline for Django URLConf to Lilya conversion."""

from __future__ import annotations

import ast
import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from lilya_converter.models import Diagnostic

DJANGO_URL_FUNCS = {"path", "re_path"}
CONVERTER_PATTERN = re.compile(r"<(?:(?P<converter>[a-zA-Z_][a-zA-Z0-9_]*):)?(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>")


def _expr_to_str(node: ast.AST | None) -> str:
    """Safely convert an AST node to a source-like string.

    Args:
        node: AST node to render.

    Returns:
        Best-effort source-like representation.
    """
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def _get_kwarg(call: ast.Call, name: str) -> ast.keyword | None:
    """Locate a keyword argument in a call node.

    Args:
        call: Call node to inspect.
        name: Keyword name.

    Returns:
        Matching keyword node when present.
    """
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword
    return None


def _ensure_leading_slash(path: str) -> str:
    """Ensure URL path begins with `/` and is non-empty.

    Args:
        path: Input path string.

    Returns:
        Normalized path string.
    """
    if not path:
        return "/"
    if not path.startswith("/"):
        return f"/{path}"
    return path


def _normalize_django_path(path: str) -> str:
    """Normalize Django path converter syntax to Lilya syntax.

    Args:
        path: Django-style path string, for example ``items/<int:item_id>/``.

    Returns:
        Lilya-style path string, for example ``/items/{item_id:int}/``.
    """

    def replace(match: re.Match[str]) -> str:
        converter = match.group("converter")
        name = match.group("name")
        if converter:
            return f"{{{name}:{converter}}}"
        return f"{{{name}}}"

    normalized = CONVERTER_PATTERN.sub(replace, path)
    return _ensure_leading_slash(normalized)


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


class _DjangoTransformer(ast.NodeTransformer):
    """Rule-driven AST transformer for one Django URL module."""

    def __init__(self, relative_path: str) -> None:
        """Initialize per-module transformation state.

        Args:
            relative_path: Project-relative path used in diagnostics.
        """
        self.relative_path = relative_path
        self.diagnostics: list[Diagnostic] = []
        self.applied_rules: set[str] = set()
        self.requires_lilya_app_import = False
        self.requires_lilya_routing_import = False
        self.has_urlpatterns = False
        self.has_app_assignment = False

    def _diag(
        self,
        code: str,
        message: str,
        *,
        line: int | None = None,
        severity: str = "warning",
    ) -> None:
        """Append a transformer diagnostic.

        Args:
            code: Stable diagnostic identifier.
            message: Human-readable diagnostic message.
            line: Optional 1-based line number.
            severity: Diagnostic severity.
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

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST | list[ast.stmt] | None:
        """Rewrite Django URL imports to Lilya equivalents.

        Args:
            node: Import-from node.

        Returns:
            Rewritten import statements or original node.
        """
        if node.module != "django.urls":
            return node

        remaining: list[ast.alias] = []
        consumed = False
        for alias in node.names:
            if alias.name in {"path", "re_path", "include"}:
                consumed = True
                continue
            remaining.append(alias)

        statements: list[ast.stmt] = []
        if consumed:
            self.requires_lilya_app_import = True
            self.requires_lilya_routing_import = True
            self.applied_rules.add("django_imports_to_lilya")
        if remaining:
            statements.append(ast.ImportFrom(module=node.module, names=remaining, level=node.level))
        return statements or None

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """Track ``urlpatterns`` and existing ``app`` assignments.

        Args:
            node: Assignment node.

        Returns:
            Possibly rewritten assignment node.
        """
        target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "urlpatterns" in target_names:
            self.has_urlpatterns = True
        if "app" in target_names:
            self.has_app_assignment = True
        self.generic_visit(node)
        return node

    def _build_include_call(
        self,
        route_value: ast.expr,
        include_call: ast.Call,
        *,
        name_kw: ast.keyword | None,
        line: int,
    ) -> ast.Call:
        """Build a Lilya ``Include`` call from a Django ``include`` call.

        Args:
            route_value: Path expression from ``path(...)``.
            include_call: Inner ``include(...)`` call expression.
            name_kw: Optional ``name=`` keyword from outer ``path`` call.
            line: Source line for diagnostics.

        Returns:
            Rewritten ``Include(...)`` call expression.
        """
        include_arg: ast.expr | None = include_call.args[0] if include_call.args else None
        include_arg_kw = _get_kwarg(include_call, "arg")
        if include_arg is None and include_arg_kw is not None:
            include_arg = include_arg_kw.value
        if include_arg is None:
            self._diag(
                code="convert.django.include_missing_arg",
                message="Could not resolve include(...) argument in urlpatterns entry.",
                line=line,
                severity="error",
            )
            include_arg = ast.Constant(value="")

        namespace_kw = _get_kwarg(include_call, "namespace")
        if namespace_kw is not None:
            self._diag(
                code="convert.django.include_namespace_removed",
                message="Django include(namespace=...) has no direct Lilya equivalent and was removed.",
                line=line,
            )

        keywords = [
            ast.keyword(arg="path", value=route_value),
            ast.keyword(arg="app", value=include_arg),
        ]
        if name_kw is not None:
            keywords.append(ast.keyword(arg="name", value=name_kw.value))

        self.applied_rules.add("django_include_to_lilya_include")
        self.requires_lilya_routing_import = True
        return ast.Call(func=ast.Name(id="Include", ctx=ast.Load()), args=[], keywords=keywords)

    def _build_path_call(
        self,
        route_value: ast.expr,
        view_value: ast.expr,
        *,
        name_kw: ast.keyword | None,
    ) -> ast.Call:
        """Build a Lilya ``Path`` call from Django ``path`` entry values.

        Args:
            route_value: Normalized route path expression.
            view_value: Route view/callable expression.
            name_kw: Optional ``name=`` keyword from original path call.

        Returns:
            Rewritten ``Path(...)`` call expression.
        """
        keywords: list[ast.keyword] = []
        if name_kw is not None:
            keywords.append(ast.keyword(arg="name", value=name_kw.value))

        self.applied_rules.add("django_path_to_lilya_path")
        self.requires_lilya_routing_import = True
        return ast.Call(func=ast.Name(id="Path", ctx=ast.Load()), args=[route_value, view_value], keywords=keywords)

    def visit_Call(self, node: ast.Call) -> ast.AST:
        """Rewrite Django URL pattern calls into Lilya route/include calls.

        Args:
            node: Call node.

        Returns:
            Rewritten call node when applicable.
        """
        self.generic_visit(node)
        if not isinstance(node.func, ast.Name):
            return node
        if node.func.id not in DJANGO_URL_FUNCS:
            return node

        route_value: ast.expr | None = node.args[0] if node.args else None
        route_kw = _get_kwarg(node, "route")
        if route_value is None and route_kw is not None:
            route_value = route_kw.value

        view_value: ast.expr | None = node.args[1] if len(node.args) > 1 else None
        view_kw = _get_kwarg(node, "view")
        if view_value is None and view_kw is not None:
            view_value = view_kw.value

        name_kw = _get_kwarg(node, "name")

        if route_value is None or view_value is None:
            self._diag(
                code="convert.django.path_missing_values",
                message="Could not resolve path(...) route/view values; entry was left unchanged.",
                line=node.lineno,
                severity="error",
            )
            return node

        normalized_route = route_value
        if isinstance(route_value, ast.Constant) and isinstance(route_value.value, str):
            converted = _normalize_django_path(route_value.value)
            if converted != route_value.value:
                self.applied_rules.add("django_path_converter_normalization")
            normalized_route = ast.Constant(value=converted)
        elif isinstance(route_value, ast.Constant) and route_value.value == "":
            normalized_route = ast.Constant(value="/")
        else:
            self._diag(
                code="convert.django.dynamic_path",
                message="Dynamic Django path expressions were kept as-is and may need manual review.",
                line=node.lineno,
            )

        if node.func.id == "re_path":
            self._diag(
                code="convert.django.re_path_partial",
                message="re_path(...) was converted as a plain Path(...); regex semantics may differ.",
                line=node.lineno,
            )

        if (
            isinstance(view_value, ast.Call)
            and isinstance(view_value.func, ast.Name)
            and view_value.func.id == "include"
        ):
            return self._build_include_call(normalized_route, view_value, name_kw=name_kw, line=node.lineno)

        return self._build_path_call(normalized_route, view_value, name_kw=name_kw)


def _has_import(tree: ast.Module, module: str, names: set[str]) -> bool:
    """Check whether a module-level ``from ... import ...`` exists.

    Args:
        tree: Module AST.
        module: Target import module.
        names: Required imported symbols (by asname/name).

    Returns:
        ``True`` if all required names are imported from ``module``.
    """
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and statement.module == module:
            imported = {alias.asname or alias.name for alias in statement.names}
            if names.issubset(imported):
                return True
    return False


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


def _ensure_support_nodes(tree: ast.Module, transformer: _DjangoTransformer) -> None:
    """Ensure required Lilya imports and app assignment exist.

    Args:
        tree: Transformed module AST.
        transformer: Transformer state.
    """
    if transformer.requires_lilya_routing_import and not _has_import(tree, "lilya.routing", {"Path", "Include"}):
        _insert_import(
            tree,
            ast.ImportFrom(
                module="lilya.routing",
                names=[ast.alias(name="Include", asname=None), ast.alias(name="Path", asname=None)],
                level=0,
            ),
        )

    if transformer.requires_lilya_app_import and not _has_import(tree, "lilya.apps", {"Lilya"}):
        _insert_import(
            tree,
            ast.ImportFrom(module="lilya.apps", names=[ast.alias(name="Lilya", asname=None)], level=0),
        )

    if transformer.has_urlpatterns and not transformer.has_app_assignment:
        tree.body.append(
            ast.Assign(
                targets=[ast.Name(id="app", ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="Lilya", ctx=ast.Load()),
                    args=[],
                    keywords=[ast.keyword(arg="routes", value=ast.Name(id="urlpatterns", ctx=ast.Load()))],
                ),
            )
        )
        transformer.applied_rules.add("django_urlpatterns_to_app")
        transformer.requires_lilya_app_import = True


def _apply_module_transformation(tree: ast.Module, relative_path: str) -> tuple[ast.Module, _DjangoTransformer]:
    """Apply Django URL conversion rules to a parsed module AST.

    Args:
        tree: Parsed source module AST.
        relative_path: Project-relative path for diagnostics.

    Returns:
        Tuple containing transformed AST and transformer state.
    """
    transformer = _DjangoTransformer(relative_path=relative_path)
    updated = transformer.visit(tree)
    assert isinstance(updated, ast.Module)
    _ensure_support_nodes(updated, transformer)
    ast.fix_missing_locations(updated)
    return updated, transformer


def transform_python_source(source: str, relative_path: str) -> TransformResult:
    """Transform Django URLConf source into Lilya-compatible source.

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
    """Transform one Django source file from disk.

    Args:
        path: Source file path.
        source_root: Source root used to derive relative labels.

    Returns:
        Per-file transformation result.
    """
    source = path.read_text(encoding="utf-8")
    relative_path = str(path.resolve().relative_to(source_root.resolve()))
    return transform_python_source(source=source, relative_path=relative_path)
