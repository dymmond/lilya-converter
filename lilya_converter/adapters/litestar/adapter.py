"""Litestar source adapter implementation."""

from __future__ import annotations

from pathlib import Path

from lilya_converter.adapters.litestar.rules import RULES
from lilya_converter.adapters.litestar.scanner import LitestarScanner
from lilya_converter.adapters.litestar.transformer import TransformResult, transform_python_file
from lilya_converter.core.rules import MappingRule
from lilya_converter.models import ConversionReport, Diagnostic, FileChange, ScanReport
from lilya_converter.utils.filesystem import safe_write


class LitestarAdapter:
    """Adapter that converts Litestar source projects into Lilya output.

    Attributes:
        source: Stable adapter key for CLI and registry lookups.
        display_name: Human-readable framework name.
    """

    source = "litestar"
    display_name = "Litestar"

    def __init__(self) -> None:
        """Initialize adapter state."""
        self._scanner = LitestarScanner()

    def analyze(self, source_root: str | Path) -> ScanReport:
        """Analyze a Litestar source project tree.

        Args:
            source_root: Source project root path.

        Returns:
            Typed scan report for discovered routes and constructors.
        """
        return self._scanner.scan(source_root)

    def transform_python_file(self, path: Path, source_root: Path) -> TransformResult:
        """Transform one Litestar source file.

        Args:
            path: Source file path.
            source_root: Source root for relative labels.

        Returns:
            Per-file transformation result.
        """
        return transform_python_file(path=path, source_root=source_root)

    def mapping_rules(self) -> list[MappingRule]:
        """Return Litestar adapter mapping rules.

        Returns:
            Ordered list of mapping rules.
        """
        return list(RULES)

    def scaffold(self, source_root: str | Path, target_root: str | Path, *, dry_run: bool = False) -> ConversionReport:
        """Generate a minimal Lilya scaffold informed by Litestar analysis.

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
                        message=f"Detected {len(module.routes)} route handlers in {module.relative_path}.",
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
        """Collect Litestar-specific residual pattern diagnostics.

        Args:
            relative_path: Target-relative file path.
            source: File source code text.

        Returns:
            Ordered diagnostics for remaining Litestar artifacts.
        """
        diagnostics: list[Diagnostic] = []
        if "from litestar" in source or "import litestar" in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.litestar_import_remaining",
                    severity="warning",
                    message="Litestar imports are still present after conversion.",
                    file=relative_path,
                )
            )
        if "route_handlers" in source and "routes=" not in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.route_handlers_remaining",
                    severity="warning",
                    message="Litestar route_handlers values remain without explicit Lilya routes mapping.",
                    file=relative_path,
                )
            )
        return diagnostics
