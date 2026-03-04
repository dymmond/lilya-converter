"""Domain models used across scan, conversion, and verification flows.

The dataclasses in this module provide strongly-typed report payloads and
stable serialization helpers used by the CLI and tests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Severity = Literal["info", "warning", "error"]


@dataclass(order=True)
class Diagnostic:
    """Represents a single diagnostic emitted by scan/convert/verify phases.

    Attributes:
        code: Stable machine-readable diagnostic identifier.
        message: Human-readable explanation of the issue.
        severity: Severity level (`info`, `warning`, or `error`).
        file: Optional project-relative file path where the issue occurred.
        line: Optional 1-based line number.
        column: Optional 1-based column number.
    """

    code: str
    message: str
    severity: Severity = "warning"
    file: str | None = None
    line: int | None = None
    column: int | None = None


@dataclass
class DependencyRef:
    """A discovered FastAPI dependency reference during scan.

    Attributes:
        name: Best-effort dependency name.
        expression: Source expression as unparsable-safe string.
        line: 1-based source line number.
        source: Context where the dependency reference was found.
    """

    name: str
    expression: str
    line: int
    source: Literal["param", "decorator", "app", "router", "include"]


@dataclass
class RouteInfo:
    """Describes one detected route decorator in a module.

    Attributes:
        function_name: Decorated function name.
        owner: Owner symbol (`app`, `router`, etc.) used in the decorator.
        method: Route method/decorator attribute.
        path: Route path expression when resolvable.
        line: 1-based line number for the decorator.
        has_dependencies_kw: Whether `dependencies=` is present.
        has_response_model_kw: Whether `response_model=` is present.
        has_response_class_kw: Whether `response_class=` is present.
        has_status_code_kw: Whether `status_code=` is present.
        has_responses_kw: Whether `responses=` is present.
    """

    function_name: str
    owner: str
    method: str
    path: str | None
    line: int
    has_dependencies_kw: bool = False
    has_response_model_kw: bool = False
    has_response_class_kw: bool = False
    has_status_code_kw: bool = False
    has_responses_kw: bool = False


@dataclass
class IncludeRouterInfo:
    """Represents one include call discovered during source scan.

    Attributes:
        owner: Owning symbol receiving the include call.
        router_expr: String form of included app/router expression.
        prefix_expr: Optional string form of include prefix/path expression.
        line: 1-based line number for the call.
    """

    owner: str
    router_expr: str
    prefix_expr: str | None
    line: int


@dataclass
class AppInstanceInfo:
    """Metadata for a discovered source framework constructor assignment.

    Attributes:
        name: Assigned symbol name.
        kind: Constructor type (`FastAPI`, `APIRouter`, `Flask`, or `Blueprint`).
        line: 1-based assignment line.
        prefix_expr: Optional `prefix=` expression if present.
    """

    name: str
    kind: Literal["FastAPI", "APIRouter", "Flask", "Blueprint"]
    line: int
    prefix_expr: str | None = None


@dataclass
class ModuleScan:
    """Scan output for a single Python module.

    Attributes:
        relative_path: Project-relative module path.
        app_instances: Discovered app/router constructor assignments.
        routes: Discovered route decorators.
        include_routers: Discovered `include_router` call sites.
        dependency_refs: Discovered dependency references.
        middleware_calls: Line numbers for `.add_middleware(...)` calls.
        middleware_decorators: Line numbers for `@app.middleware(...)` decorators.
        event_decorators: Line numbers for `@app.on_event(...)` decorators.
        exception_handler_decorators: Line numbers for exception handler decorators.
        diagnostics: Module-scoped diagnostics.
    """

    relative_path: str
    app_instances: list[AppInstanceInfo] = field(default_factory=list)
    routes: list[RouteInfo] = field(default_factory=list)
    include_routers: list[IncludeRouterInfo] = field(default_factory=list)
    dependency_refs: list[DependencyRef] = field(default_factory=list)
    middleware_calls: list[int] = field(default_factory=list)
    middleware_decorators: list[int] = field(default_factory=list)
    event_decorators: list[int] = field(default_factory=list)
    exception_handler_decorators: list[int] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass
class ScanReport:
    """Top-level scan report for a source project.

    Attributes:
        source_root: Absolute normalized source root path.
        modules: Per-module scan payloads.
        diagnostics: Project-level diagnostics.
    """

    source_root: str
    modules: list[ModuleScan]
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def files_scanned(self) -> int:
        """Return the count of parsed Python modules."""
        return len(self.modules)

    @property
    def total_routes(self) -> int:
        """Return the total number of discovered route decorators."""
        return sum(len(module.routes) for module in self.modules)

    @property
    def total_diagnostics(self) -> int:
        """Return project-level plus module-level diagnostic count."""
        return len(self.diagnostics) + sum(len(module.diagnostics) for module in self.modules)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report into primitive JSON-compatible values.

        Returns:
            A dictionary representation of this report.
        """
        return asdict(self)


@dataclass
class FileChange:
    """Represents conversion status for one file path.

    Attributes:
        relative_path: Source-relative file path.
        original_path: Absolute path of source file.
        target_path: Absolute path of target file.
        changed: Whether transformed content differs from source content.
        unified_diff: Unified diff text for transformed Python files.
    """

    relative_path: str
    original_path: str
    target_path: str
    changed: bool
    unified_diff: str = ""


@dataclass
class ConversionReport:
    """Top-level conversion execution report.

    Attributes:
        source_root: Absolute source root path.
        target_root: Absolute target root path.
        dry_run: Whether writes were disabled.
        files_total: Number of files examined.
        files_changed: Number of files with transformed content changes.
        files_written: Number of files written/copied to target.
        applied_rules: Sorted list of applied conversion rule IDs.
        diagnostics: Ordered diagnostics collected during conversion.
        file_changes: Ordered file-level conversion records.
    """

    source_root: str
    target_root: str
    dry_run: bool
    files_total: int
    files_changed: int
    files_written: int
    applied_rules: list[str]
    diagnostics: list[Diagnostic] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report into primitive JSON-compatible values.

        Returns:
            A dictionary representation of this report.
        """
        return asdict(self)


@dataclass
class VerifyReport:
    """Verification report for a converted target tree.

    Attributes:
        target_root: Absolute target root path.
        diagnostics: Ordered diagnostics from verification checks.
    """

    target_root: str
    diagnostics: list[Diagnostic]

    @property
    def has_errors(self) -> bool:
        """Return whether at least one error-level diagnostic exists."""
        return any(item.severity == "error" for item in self.diagnostics)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report into primitive JSON-compatible values.

        Returns:
            A dictionary representation of this report.
        """
        return asdict(self)


def normalize_path(path: str | Path) -> str:
    """Normalize a path-like value to an absolute string path.

    Args:
        path: Input path value.

    Returns:
        Absolute normalized filesystem path.
    """
    return str(Path(path).resolve())
