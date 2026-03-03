"""Core orchestration for analysis, conversion, scaffolding, and verification.

This module glues scanner, transformer, and writer components into deterministic
project-level workflows consumed by the CLI and tests.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from lilya_converter.models import (
    ConversionReport,
    Diagnostic,
    FileChange,
    ScanReport,
    VerifyReport,
)
from lilya_converter.rules import RULES
from lilya_converter.scanner import FastAPIScanner
from lilya_converter.transformer import transform_python_file
from lilya_converter.writer import copy_file, iter_files, safe_write


def _module_exists(target: Path, module: str) -> bool:
    """Check whether a dotted local module exists under `target`.

    Args:
        target: Project root to resolve imports against.
        module: Dotted module path, for example `routers.items`.

    Returns:
        `True` if a matching module file or package exists, otherwise `False`.
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
    """Collect top-level local module/package roots for import verification.

    Args:
        target: Target project root.

    Returns:
        A set of top-level importable local names.
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


def analyze_project(source_root: str | Path) -> ScanReport:
    """Analyze a FastAPI project and return a structured scan report.

    Args:
        source_root: Root directory of the source FastAPI project.

    Returns:
        A `ScanReport` with discovered modules and diagnostics.
    """
    scanner = FastAPIScanner()
    return scanner.scan(source_root)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Persist a JSON payload with stable indentation and key ordering.

    Args:
        path: Output file path.
        payload: JSON-serializable dictionary payload.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def convert_project(
    source_root: str | Path,
    target_root: str | Path,
    *,
    dry_run: bool = False,
    copy_non_python: bool = True,
) -> ConversionReport:
    """Convert a FastAPI project into a Lilya-compatible target tree.

    Args:
        source_root: Source FastAPI project root.
        target_root: Destination Lilya project root.
        dry_run: If `True`, compute and report changes without writing files.
        copy_non_python: If `True`, copy non-Python files into the target.

    Returns:
        A `ConversionReport` with file changes, diagnostics, and applied rules.

    Raises:
        FileNotFoundError: If `source_root` does not exist.
    """
    source = Path(source_root).resolve()
    target = Path(target_root).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source root does not exist: {source}")

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
            result = transform_python_file(file_path, source_root=source)
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
        else:
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
    return ConversionReport(
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


def scaffold_project(
    source_root: str | Path,
    target_root: str | Path,
    *,
    dry_run: bool = False,
) -> ConversionReport:
    """Generate a minimal Lilya scaffold informed by scan metadata.

    Args:
        source_root: Source project root to inspect.
        target_root: Destination directory where scaffold files are created.
        dry_run: If `True`, do not write files.

    Returns:
        A conversion report describing scaffold output.
    """
    source = Path(source_root).resolve()
    target = Path(target_root).resolve()
    report = analyze_project(source)

    app_file = target / "main.py"
    lines = [
        "from lilya.apps import Lilya",
        "",
        "app = Lilya(routes=[])",
        "",
    ]
    diagnostics: list[Diagnostic] = []
    for module in report.modules:
        if module.routes:
            diagnostics.append(
                Diagnostic(
                    code="scaffold.routes_detected",
                    severity="info",
                    message=f"Detected {len(module.routes)} route decorators in {module.relative_path}.",
                    file=module.relative_path,
                )
            )

    if not dry_run:
        safe_write(app_file, "\n".join(lines))

    return ConversionReport(
        source_root=str(source),
        target_root=str(target),
        dry_run=dry_run,
        files_total=1,
        files_changed=1,
        files_written=0 if dry_run else 1,
        applied_rules=[],
        diagnostics=diagnostics,
        file_changes=[
            FileChange(
                relative_path="main.py",
                original_path="",
                target_path=str(app_file),
                changed=True,
                unified_diff="",
            )
        ],
    )


def verify_project(target_root: str | Path) -> VerifyReport:
    """Run structural checks against a converted Lilya target tree.

    Checks include:
    - Python syntax validation.
    - Remaining FastAPI import/call patterns.
    - Unresolved local import modules.

    Args:
        target_root: Target project root to verify.

    Returns:
        A `VerifyReport` with ordered diagnostics.
    """
    target = Path(target_root).resolve()
    diagnostics: list[Diagnostic] = []
    if not target.exists():
        diagnostics.append(
            Diagnostic(
                code="verify.missing_target",
                severity="error",
                message=f"Target root does not exist: {target}",
            )
        )
        return VerifyReport(target_root=str(target), diagnostics=diagnostics)

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

        if "from fastapi" in source or "import fastapi" in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.fastapi_import_remaining",
                    severity="warning",
                    message="FastAPI imports are still present after conversion.",
                    file=relative,
                )
            )
        if ".include_router(" in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.include_router_remaining",
                    severity="warning",
                    message="include_router() calls remain; Lilya expects include().",
                    file=relative,
                )
            )
        if ".middleware(" in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.middleware_decorator_remaining",
                    severity="warning",
                    message="Function middleware decorator calls remain; verify manual middleware conversion.",
                    file=relative,
                )
            )

    diagnostics.sort(key=lambda item: (item.file or "", item.line or 0, item.code))
    return VerifyReport(target_root=str(target), diagnostics=diagnostics)


def save_scan_report(report: ScanReport, path: str | Path) -> None:
    """Persist a scan report to JSON.

    Args:
        report: Scan report to serialize.
        path: Destination file path.
    """
    _write_json(Path(path), report.to_dict())


def save_conversion_report(report: ConversionReport, path: str | Path) -> None:
    """Persist a conversion report to JSON.

    Args:
        report: Conversion report to serialize.
        path: Destination file path.
    """
    _write_json(Path(path), report.to_dict())


def save_verify_report(report: VerifyReport, path: str | Path) -> None:
    """Persist a verification report to JSON.

    Args:
        report: Verification report to serialize.
        path: Destination file path.
    """
    _write_json(Path(path), report.to_dict())


def mapping_rules() -> list[tuple[str, str]]:
    """Return conversion rule IDs and summaries.

    Returns:
        A list of `(rule_id, summary)` tuples in registry order.
    """
    return [(rule.id, rule.summary) for rule in RULES]
