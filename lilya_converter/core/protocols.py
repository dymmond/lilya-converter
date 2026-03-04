"""Protocols defining the adapter interface for source frameworks."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from lilya_converter.core.rules import MappingRule
from lilya_converter.models import ConversionReport, Diagnostic, ScanReport


class PythonTransformResult(Protocol):
    """Structural protocol for per-file transformation results.

    Attributes:
        content: Transformed source content.
        changed: Whether transformed content differs from input.
        diagnostics: Ordered diagnostics emitted during transformation.
        applied_rules: Applied mapping rule identifiers.
        unified_diff: Unified diff between original and transformed source.
    """

    content: str
    changed: bool
    diagnostics: list[Diagnostic]
    applied_rules: list[str]
    unified_diff: str


class SourceFrameworkAdapter(Protocol):
    """Protocol implemented by each source-framework adapter.

    Attributes:
        source: Stable source identifier used in CLI/registry lookups.
        display_name: Human-readable framework name.
    """

    source: str
    display_name: str

    def analyze(self, source_root: str | Path) -> ScanReport:
        """Analyze a source project tree.

        Args:
            source_root: Root directory for source project analysis.

        Returns:
            A typed scan report describing discovered conversion-relevant data.
        """

    def transform_python_file(self, path: Path, source_root: Path) -> PythonTransformResult:
        """Transform one Python source file.

        Args:
            path: Absolute file path to transform.
            source_root: Absolute source root used for relative labeling.

        Returns:
            A typed transformation result with content, diagnostics, and diff.
        """

    def mapping_rules(self) -> Sequence[MappingRule]:
        """Return this adapter's mapping rule registry.

        Returns:
            Deterministic sequence of rule metadata entries.
        """

    def scaffold(self, source_root: str | Path, target_root: str | Path, *, dry_run: bool = False) -> ConversionReport:
        """Generate a minimal Lilya scaffold informed by source analysis.

        Args:
            source_root: Root directory of the source project.
            target_root: Destination root where scaffold files are created.
            dry_run: Whether to skip filesystem writes.

        Returns:
            A conversion report describing generated scaffold files.
        """

    def collect_verify_diagnostics(self, *, relative_path: str, source: str) -> list[Diagnostic]:
        """Collect source-framework-specific verification diagnostics.

        Args:
            relative_path: Target-relative path for the file being verified.
            source: File source code text.

        Returns:
            Diagnostics for adapter-specific post-conversion checks.
        """
