"""Starlette source adapter implementation."""

from __future__ import annotations

from pathlib import Path

from lilya_converter.adapters.starlette.rules import RULES
from lilya_converter.adapters.starlette.scanner import StarletteScanner
from lilya_converter.adapters.starlette.transformer import TransformResult, transform_python_file
from lilya_converter.core.rules import MappingRule
from lilya_converter.models import ConversionReport, Diagnostic, FileChange, ScanReport
from lilya_converter.utils.filesystem import safe_write


class StarletteAdapter:
    """Adapter that converts Starlette source projects into Lilya output.

    Attributes:
        source: Stable adapter key for CLI and registry lookups.
        display_name: Human-readable framework name.
    """

    source = "starlette"
    display_name = "Starlette"

    def __init__(self) -> None:
        """Initialize adapter state."""
        self._scanner = StarletteScanner()

    def analyze(self, source_root: str | Path) -> ScanReport:
        """Analyze a Starlette source project tree.

        Args:
            source_root: Source project root path.

        Returns:
            Typed scan report for discovered routes and includes.
        """
        return self._scanner.scan(source_root)

    def transform_python_file(self, path: Path, source_root: Path) -> TransformResult:
        """Transform one Starlette source file.

        Args:
            path: Source file path.
            source_root: Source root for relative labels.

        Returns:
            Per-file transformation result.
        """
        return transform_python_file(path=path, source_root=source_root)

    def mapping_rules(self) -> list[MappingRule]:
        """Return Starlette adapter mapping rules.

        Returns:
            Ordered list of mapping rules.
        """
        return list(RULES)

    def scaffold(self, source_root: str | Path, target_root: str | Path, *, dry_run: bool = False) -> ConversionReport:
        """Generate a minimal Lilya scaffold informed by Starlette analysis.

        Args:
            source_root: Source project root path.
            target_root: Destination scaffold directory.
            dry_run: Whether to skip filesystem writes.

        Returns:
            Conversion report describing scaffold artifacts.
        """
        source = Path(source_root).resolve()
        target = Path(target_root).resolve()
        report = self.analyze(source)

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
                        message=f"Detected {len(module.routes)} route entries in {module.relative_path}.",
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

    def collect_verify_diagnostics(self, *, relative_path: str, source: str) -> list[Diagnostic]:
        """Collect Starlette-specific residual pattern diagnostics.

        Args:
            relative_path: Target-relative file path.
            source: File source code text.

        Returns:
            Ordered diagnostics for remaining Starlette artifacts.
        """
        diagnostics: list[Diagnostic] = []
        if "from starlette" in source or "import starlette" in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.starlette_import_remaining",
                    severity="warning",
                    message="Starlette imports are still present after conversion.",
                    file=relative_path,
                )
            )
        if ".mount(" in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.mount_remaining",
                    severity="warning",
                    message="mount() calls remain; Lilya include() semantics may need manual review.",
                    file=relative_path,
                )
            )
        return diagnostics
