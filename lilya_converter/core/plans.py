"""Typed plan and result objects for framework-agnostic orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lilya_converter.models import ConversionReport, ScanReport, VerifyReport


@dataclass(frozen=True)
class AnalysisPlan:
    """Describe one analysis execution.

    Args:
        source_framework: Source framework identifier (for example, ``fastapi``).
        source_root: Absolute source project root path.
    """

    source_framework: str
    source_root: Path


@dataclass(frozen=True)
class ConversionPlan:
    """Describe one conversion execution.

    Args:
        source_framework: Source framework identifier.
        source_root: Absolute source project root path.
        target_root: Absolute conversion output root path.
        dry_run: Whether file writes are disabled.
        copy_non_python: Whether non-Python files should be copied.
    """

    source_framework: str
    source_root: Path
    target_root: Path
    dry_run: bool
    copy_non_python: bool


@dataclass(frozen=True)
class ScaffoldPlan:
    """Describe one scaffold generation execution.

    Args:
        source_framework: Source framework identifier.
        source_root: Absolute source project root path.
        target_root: Absolute scaffold output root path.
        dry_run: Whether file writes are disabled.
    """

    source_framework: str
    source_root: Path
    target_root: Path
    dry_run: bool


@dataclass(frozen=True)
class VerificationPlan:
    """Describe one verification execution.

    Args:
        source_framework: Source framework identifier used for source-specific checks.
        target_root: Absolute converted project root path.
    """

    source_framework: str
    target_root: Path


@dataclass(frozen=True)
class AnalysisResult:
    """Bundle analysis plan and report output.

    Args:
        plan: Analysis plan used for execution.
        report: Resulting scan report.
    """

    plan: AnalysisPlan
    report: ScanReport


@dataclass(frozen=True)
class ConversionResult:
    """Bundle conversion plan and report output.

    Args:
        plan: Conversion plan used for execution.
        report: Resulting conversion report.
    """

    plan: ConversionPlan
    report: ConversionReport


@dataclass(frozen=True)
class ScaffoldResult:
    """Bundle scaffold plan and report output.

    Args:
        plan: Scaffold plan used for execution.
        report: Resulting scaffold conversion report.
    """

    plan: ScaffoldPlan
    report: ConversionReport


@dataclass(frozen=True)
class VerificationResult:
    """Bundle verification plan and report output.

    Args:
        plan: Verification plan used for execution.
        report: Resulting verification report.
    """

    plan: VerificationPlan
    report: VerifyReport
