"""Public orchestration API for analysis, conversion, scaffolding, and verification.

This module preserves the historical ``lilya_converter.engine`` API while
routing all operations through the framework-agnostic core orchestrator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lilya_converter.adapters import create_default_adapters
from lilya_converter.core.errors import ConversionPathError
from lilya_converter.core.orchestrator import ConversionOrchestrator
from lilya_converter.core.registry import AdapterRegistry
from lilya_converter.models import ConversionReport, ScanReport, VerifyReport

_REGISTRY = AdapterRegistry(create_default_adapters())
_ORCHESTRATOR = ConversionOrchestrator(_REGISTRY, default_source="fastapi")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Persist a JSON payload with stable formatting.

    Args:
        path: Output file path.
        payload: JSON-serializable dictionary payload.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supported_sources() -> tuple[str, ...]:
    """Return supported source frameworks.

    Returns:
        Deterministically sorted source framework identifiers.
    """
    return _ORCHESTRATOR.supported_sources()


def analyze_project(source_root: str | Path, *, source_framework: str = "fastapi") -> ScanReport:
    """Analyze a source project and return a structured scan report.

    Args:
        source_root: Source project root path.
        source_framework: Source framework identifier.

    Returns:
        A ``ScanReport`` with discovered modules and diagnostics.

    Raises:
        FileNotFoundError: If ``source_root`` does not exist.
    """
    try:
        result = _ORCHESTRATOR.analyze(source_root=source_root, source_framework=source_framework)
    except ConversionPathError as exc:
        raise FileNotFoundError(str(exc)) from exc
    return result.report


def convert_project(
    source_root: str | Path,
    target_root: str | Path,
    *,
    source_framework: str = "fastapi",
    dry_run: bool = False,
    copy_non_python: bool = True,
) -> ConversionReport:
    """Convert a source project into a Lilya-compatible target tree.

    Args:
        source_root: Source project root path.
        target_root: Destination project root path.
        source_framework: Source framework identifier.
        dry_run: If ``True``, compute/report changes without writing files.
        copy_non_python: If ``True``, copy non-Python files to target.

    Returns:
        A ``ConversionReport`` with changes, diagnostics, and applied rules.

    Raises:
        FileNotFoundError: If ``source_root`` does not exist.
    """
    try:
        result = _ORCHESTRATOR.convert(
            source_root=source_root,
            target_root=target_root,
            source_framework=source_framework,
            dry_run=dry_run,
            copy_non_python=copy_non_python,
        )
    except ConversionPathError as exc:
        raise FileNotFoundError(str(exc)) from exc
    return result.report


def scaffold_project(
    source_root: str | Path,
    target_root: str | Path,
    *,
    source_framework: str = "fastapi",
    dry_run: bool = False,
) -> ConversionReport:
    """Generate a minimal Lilya scaffold informed by source metadata.

    Args:
        source_root: Source project root path.
        target_root: Destination scaffold root path.
        source_framework: Source framework identifier.
        dry_run: If ``True``, skip file writes.

    Returns:
        A conversion report describing scaffold output.

    Raises:
        FileNotFoundError: If ``source_root`` does not exist.
    """
    try:
        result = _ORCHESTRATOR.scaffold(
            source_root=source_root,
            target_root=target_root,
            source_framework=source_framework,
            dry_run=dry_run,
        )
    except ConversionPathError as exc:
        raise FileNotFoundError(str(exc)) from exc
    return result.report


def verify_project(target_root: str | Path, *, source_framework: str = "fastapi") -> VerifyReport:
    """Run structural checks against a converted Lilya target tree.

    Args:
        target_root: Converted target root path.
        source_framework: Source framework identifier used for residual checks.

    Returns:
        A ``VerifyReport`` with ordered diagnostics.
    """
    result = _ORCHESTRATOR.verify(target_root=target_root, source_framework=source_framework)
    return result.report


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


def mapping_rules(*, source_framework: str = "fastapi") -> list[tuple[str, str]]:
    """Return conversion rule IDs and summaries for one source adapter.

    Args:
        source_framework: Source framework identifier.

    Returns:
        Ordered list of ``(rule_id, summary)`` tuples.
    """
    return _ORCHESTRATOR.mapping_rules(source_framework=source_framework)
