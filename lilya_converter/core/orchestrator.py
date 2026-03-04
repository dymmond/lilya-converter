"""Framework-agnostic orchestration for analysis, conversion, and verification."""

from __future__ import annotations

import ast
from pathlib import Path

from lilya_converter.core.errors import ConversionPathError
from lilya_converter.core.plans import (
    AnalysisPlan,
    AnalysisResult,
    ConversionPlan,
    ConversionResult,
    ScaffoldPlan,
    ScaffoldResult,
    VerificationPlan,
    VerificationResult,
)
from lilya_converter.core.registry import AdapterRegistry
from lilya_converter.models import ConversionReport, Diagnostic, FileChange, VerifyReport
from lilya_converter.utils.filesystem import copy_file, iter_files, safe_write


class ConversionOrchestrator:
    """Coordinate framework adapters with filesystem/report workflows.

    Args:
        registry: Adapter registry used for source resolution.
        default_source: Source framework used when callers omit an explicit source.
    """

    def __init__(self, registry: AdapterRegistry, *, default_source: str = "fastapi") -> None:
        self.registry = registry
        self.default_source = default_source

    def supported_sources(self) -> tuple[str, ...]:
        """Return available source framework identifiers.

        Returns:
            Deterministically sorted source keys from the adapter registry.
        """
        return self.registry.supported_sources()

    def _resolve_source(self, source_framework: str | None) -> str:
        """Resolve optional source key to an explicit adapter source.

        Args:
            source_framework: Optional source identifier from caller.

        Returns:
            Resolved source identifier.
        """
        if source_framework is None:
            return self.default_source
        return source_framework

    def analyze(self, source_root: str | Path, *, source_framework: str | None = None) -> AnalysisResult:
        """Analyze a source project with a selected adapter.

        Args:
            source_root: Source project root path.
            source_framework: Optional source framework key.

        Returns:
            Analysis plan/result bundle.

        Raises:
            ConversionPathError: If ``source_root`` does not exist.
        """
        source = Path(source_root).resolve()
        if not source.exists():
            raise ConversionPathError(f"Source root does not exist: {source}")

        resolved_source = self._resolve_source(source_framework)
        adapter = self.registry.get(resolved_source)
        plan = AnalysisPlan(source_framework=resolved_source, source_root=source)
        report = adapter.analyze(source)
        return AnalysisResult(plan=plan, report=report)

    def convert(
        self,
        source_root: str | Path,
        target_root: str | Path,
        *,
        source_framework: str | None = None,
        dry_run: bool = False,
        copy_non_python: bool = True,
    ) -> ConversionResult:
        """Convert a source project into Lilya-compatible output.

        Args:
            source_root: Source project root path.
            target_root: Destination project root path.
            source_framework: Optional source framework key.
            dry_run: Whether to compute changes without writing files.
            copy_non_python: Whether non-Python files should be copied.

        Returns:
            Conversion plan/result bundle.

        Raises:
            ConversionPathError: If ``source_root`` does not exist.
        """
        source = Path(source_root).resolve()
        target = Path(target_root).resolve()
        if not source.exists():
            raise ConversionPathError(f"Source root does not exist: {source}")

        resolved_source = self._resolve_source(source_framework)
        adapter = self.registry.get(resolved_source)
        plan = ConversionPlan(
            source_framework=resolved_source,
            source_root=source,
            target_root=target,
            dry_run=dry_run,
            copy_non_python=copy_non_python,
        )

        diagnostics: list[Diagnostic] = []
        file_changes: list[FileChange] = []
        applied_rules: set[str] = set()
        files_total = 0
        files_changed = 0
        files_written = 0

        for file_path in iter_files(source):
            relative = file_path.relative_to(source)
            target_path = target / relative
            files_total += 1

            if file_path.suffix == ".py":
                result = adapter.transform_python_file(file_path, source)
                diagnostics.extend(result.diagnostics)
                applied_rules.update(result.applied_rules)
                if result.changed:
                    files_changed += 1
                if not dry_run and (result.changed or source != target):
                    safe_write(target_path, result.content)
                    files_written += 1
                file_changes.append(
                    FileChange(
                        relative_path=str(relative),
                        original_path=str(file_path),
                        target_path=str(target_path),
                        changed=result.changed,
                        unified_diff=result.unified_diff,
                    )
                )
                continue

            if copy_non_python and source != target:
                if not dry_run:
                    copy_file(file_path, target_path)
                    files_written += 1
                file_changes.append(
                    FileChange(
                        relative_path=str(relative),
                        original_path=str(file_path),
                        target_path=str(target_path),
                        changed=True,
                        unified_diff="",
                    )
                )
            else:
                file_changes.append(
                    FileChange(
                        relative_path=str(relative),
                        original_path=str(file_path),
                        target_path=str(target_path),
                        changed=False,
                        unified_diff="",
                    )
                )

        diagnostics.sort(key=lambda item: (item.file or "", item.line or 0, item.code))
        ordered_changes = sorted(file_changes, key=lambda item: item.relative_path)
        report = ConversionReport(
            source_root=str(source),
            target_root=str(target),
            dry_run=dry_run,
            files_total=files_total,
            files_changed=files_changed,
            files_written=files_written,
            applied_rules=sorted(applied_rules),
            diagnostics=diagnostics,
            file_changes=ordered_changes,
        )
        return ConversionResult(plan=plan, report=report)

    def scaffold(
        self,
        source_root: str | Path,
        target_root: str | Path,
        *,
        source_framework: str | None = None,
        dry_run: bool = False,
    ) -> ScaffoldResult:
        """Generate a source-informed minimal Lilya scaffold.

        Args:
            source_root: Source project root path.
            target_root: Destination scaffold root path.
            source_framework: Optional source framework key.
            dry_run: Whether to skip filesystem writes.

        Returns:
            Scaffold plan/result bundle.

        Raises:
            ConversionPathError: If ``source_root`` does not exist.
        """
        source = Path(source_root).resolve()
        target = Path(target_root).resolve()
        if not source.exists():
            raise ConversionPathError(f"Source root does not exist: {source}")

        resolved_source = self._resolve_source(source_framework)
        adapter = self.registry.get(resolved_source)
        plan = ScaffoldPlan(
            source_framework=resolved_source,
            source_root=source,
            target_root=target,
            dry_run=dry_run,
        )
        report = adapter.scaffold(source_root=source, target_root=target, dry_run=dry_run)
        return ScaffoldResult(plan=plan, report=report)

    def verify(self, target_root: str | Path, *, source_framework: str | None = None) -> VerificationResult:
        """Run structural and source-specific checks for a converted project.

        Args:
            target_root: Converted project root path.
            source_framework: Optional source framework key.

        Returns:
            Verification plan/result bundle.
        """
        target = Path(target_root).resolve()
        resolved_source = self._resolve_source(source_framework)
        adapter = self.registry.get(resolved_source)
        plan = VerificationPlan(source_framework=resolved_source, target_root=target)

        diagnostics: list[Diagnostic] = []
        if not target.exists():
            diagnostics.append(
                Diagnostic(
                    code="verify.missing_target",
                    severity="error",
                    message=f"Target root does not exist: {target}",
                )
            )
            return VerificationResult(plan=plan, report=VerifyReport(target_root=str(target), diagnostics=diagnostics))

        local_roots = _collect_local_roots(target)

        for file_path in iter_files(target):
            if file_path.suffix != ".py":
                continue
            relative = str(file_path.relative_to(target))
            source = file_path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=relative)
            except SyntaxError as exc:
                diagnostics.append(
                    Diagnostic(
                        code="verify.syntax_error",
                        severity="error",
                        message=f"Syntax error in '{relative}': {exc.msg}",
                        file=relative,
                        line=exc.lineno,
                        column=exc.offset,
                    )
                )
                continue

            for statement in tree.body:
                if isinstance(statement, ast.Import):
                    for alias in statement.names:
                        module_name = alias.name
                        top_level = module_name.split(".")[0]
                        if top_level in local_roots and not _module_exists(target, module_name):
                            diagnostics.append(
                                Diagnostic(
                                    code="verify.unresolved_local_import",
                                    severity="error",
                                    message=f"Unresolved local import '{module_name}' in '{relative}'.",
                                    file=relative,
                                    line=statement.lineno,
                                )
                            )
                elif isinstance(statement, ast.ImportFrom):
                    if not statement.module or statement.level != 0:
                        continue
                    module_name = statement.module
                    top_level = module_name.split(".")[0]
                    if top_level in local_roots and not _module_exists(target, module_name):
                        diagnostics.append(
                            Diagnostic(
                                code="verify.unresolved_local_import",
                                severity="error",
                                message=f"Unresolved local import '{module_name}' in '{relative}'.",
                                file=relative,
                                line=statement.lineno,
                            )
                        )

            diagnostics.extend(adapter.collect_verify_diagnostics(relative_path=relative, source=source))

        diagnostics.sort(key=lambda item: (item.file or "", item.line or 0, item.code))
        report = VerifyReport(target_root=str(target), diagnostics=diagnostics)
        return VerificationResult(plan=plan, report=report)

    def mapping_rules(self, *, source_framework: str | None = None) -> list[tuple[str, str]]:
        """Return adapter rule IDs and summaries.

        Args:
            source_framework: Optional source framework key.

        Returns:
            Ordered list of ``(rule_id, summary)`` tuples.
        """
        resolved_source = self._resolve_source(source_framework)
        adapter = self.registry.get(resolved_source)
        return [(rule.id, rule.summary) for rule in adapter.mapping_rules()]


def _module_exists(target: Path, module: str) -> bool:
    """Check whether a dotted local module exists under ``target``.

    Args:
        target: Project root to resolve imports against.
        module: Dotted module path, for example ``routers.items``.

    Returns:
        ``True`` if a matching module file or package exists, otherwise ``False``.
    """
    parts = module.split(".")
    file_candidate = target.joinpath(*parts).with_suffix(".py")
    dir_candidate = target.joinpath(*parts)
    if file_candidate.exists():
        return True
    if dir_candidate.exists() and dir_candidate.is_dir():
        return True
    init_candidate = dir_candidate / "__init__.py"
    return init_candidate.exists()


def _collect_local_roots(target: Path) -> set[str]:
    """Collect top-level local module/package names for import checks.

    Args:
        target: Converted project root.

    Returns:
        Set of top-level importable local root names.
    """
    roots: set[str] = set()
    for file_path in iter_files(target):
        if file_path.suffix != ".py":
            continue
        relative = file_path.relative_to(target)
        if relative.name == "__init__.py":
            if relative.parent.parts:
                roots.add(relative.parent.parts[0])
            continue
        roots.add(relative.parts[0] if len(relative.parts) > 1 else relative.stem)
    return roots
