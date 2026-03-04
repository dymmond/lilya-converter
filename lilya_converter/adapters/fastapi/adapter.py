"""FastAPI source adapter implementation."""

from __future__ import annotations

from pathlib import Path

from lilya_converter.adapters.fastapi.rules import RULES
from lilya_converter.adapters.fastapi.scanner import FastAPIScanner
from lilya_converter.adapters.fastapi.transformer import TransformResult, transform_python_file
from lilya_converter.core.rules import MappingRule
from lilya_converter.models import ConversionReport, Diagnostic, FileChange, ScanReport
from lilya_converter.utils.filesystem import safe_write


class FastAPIAdapter:
    """Adapter that converts FastAPI source projects into Lilya output.

    Attributes:
        source: Stable adapter key for CLI and registry lookups.
        display_name: Human-readable framework name.
    """

    source = "fastapi"
    display_name = "FastAPI"

    def __init__(self) -> None:
        """Initialize adapter state."""
        self._scanner = FastAPIScanner()

    def analyze(self, source_root: str | Path) -> ScanReport:
        """Analyze a FastAPI project tree.

        Args:
            source_root: Root directory for source analysis.

        Returns:
            A typed scan report with per-module findings.
        """
        return self._scanner.scan(source_root)

    def transform_python_file(self, path: Path, source_root: Path) -> TransformResult:
        """Transform one Python file from FastAPI patterns to Lilya patterns.

        Args:
            path: Source file path.
            source_root: Source root used for relative diff labels.

        Returns:
            A per-file transformation result.
        """
        return transform_python_file(path=path, source_root=source_root)

    def mapping_rules(self) -> list[MappingRule]:
        """Return FastAPI conversion rule registry.

        Returns:
            Ordered list of FastAPI mapping rule metadata.
        """
        return list(RULES)

    def scaffold(self, source_root: str | Path, target_root: str | Path, *, dry_run: bool = False) -> ConversionReport:
        """Generate a minimal Lilya scaffold informed by FastAPI analysis.

        Args:
            source_root: Source project root path.
            target_root: Destination directory for scaffold output.
            dry_run: Whether to skip file writes.

        Returns:
            A conversion report describing scaffold artifacts.
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

    def collect_verify_diagnostics(self, *, relative_path: str, source: str) -> list[Diagnostic]:
        """Collect FastAPI-specific residual pattern diagnostics.

        Args:
            relative_path: Target-relative path for the checked file.
            source: File source code text.

        Returns:
            Ordered diagnostics for remaining FastAPI artifacts.
        """
        diagnostics: list[Diagnostic] = []
        if "from fastapi" in source or "import fastapi" in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.fastapi_import_remaining",
                    severity="warning",
                    message="FastAPI imports are still present after conversion.",
                    file=relative_path,
                )
            )
        if ".include_router(" in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.include_router_remaining",
                    severity="warning",
                    message="include_router() calls remain; Lilya expects include().",
                    file=relative_path,
                )
            )
        if ".middleware(" in source:
            diagnostics.append(
                Diagnostic(
                    code="verify.middleware_decorator_remaining",
                    severity="warning",
                    message="Function middleware decorator calls remain; verify manual middleware conversion.",
                    file=relative_path,
                )
            )
        return diagnostics
