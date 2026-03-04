"""CLI application for multi-framework conversion into Lilya.

This module exposes the Sayer application and all conversion-related commands:
``analyze``, ``convert``, ``scaffold``, ``map``, and ``verify``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import click
from sayer import Argument, Option, Sayer
from sayer.utils.ui import echo, error, info, success, warning

from lilya_converter.__init__ import __version__
from lilya_converter.engine import (
    analyze_project,
    convert_project,
    mapping_rules,
    save_conversion_report,
    save_scan_report,
    save_verify_report,
    scaffold_project,
    supported_sources,
    verify_project,
)
from lilya_converter.models import Diagnostic

SUPPORTED_SOURCES = supported_sources()
SOURCE_HELP = "Source framework to convert from. Supported: " + ", ".join(SUPPORTED_SOURCES)
SOURCE_CHOICE = click.Choice(list(SUPPORTED_SOURCES), case_sensitive=False)

app = Sayer(
    name="lilya-converter",
    help="Convert source framework projects into Lilya projects using source-grounded rules.",
    add_version_option=True,
    version=__version__,
    display_full_help=True,
)


def _print_diagnostics(prefix: str, diagnostics: list[Diagnostic]) -> None:
    """Render diagnostics in a stable, severity-aware format.

    Args:
        prefix: Prefix inserted before each rendered diagnostic line.
        diagnostics: Diagnostic objects to render.
    """
    for item in diagnostics:
        severity = item.severity
        code = item.code
        message = item.message
        file_name = item.file
        line = item.line
        location = ""
        if file_name:
            location = f" [{file_name}"
            if line:
                location += f":{line}"
            location += "]"
        rendered = f"{prefix}{severity.upper()} {code}{location}: {message}"
        normalized = str(severity).lower()
        if normalized == "error":
            error(rendered)
        elif normalized == "warning":
            warning(rendered)
        elif normalized == "info":
            info(rendered)
        else:
            echo(rendered)


@app.command(
    help=(
        "Analyze a source project and print conversion-relevant findings.\n\n"
        "Examples:\n"
        "  lilya-converter analyze ./fastapi_app\n"
        "  lilya-converter analyze ./flask_app --source flask --json\n"
        "  lilya-converter analyze ./fastapi_app --output ./reports/scan.json"
    ),
)
def analyze(
    source: Annotated[str, Argument(help="Source project root to scan.")],
    source_framework: Annotated[
        str,
        Option("fastapi", "--source", type=SOURCE_CHOICE, help=SOURCE_HELP),
    ] = "fastapi",
    output: Annotated[
        str | None,
        Option(None, "--output", "-o", type=str, help="Optional JSON report path."),
    ] = None,
    as_json: Annotated[
        bool,
        Option(False, "--json", help="Print full JSON report to stdout.", is_flag=True),
    ] = False,
) -> None:
    """Analyze a source project and emit a scan report.

    Args:
        source: Path to the source project root.
        source_framework: Source framework identifier.
        output: Optional path where the JSON scan report is written.
        as_json: If ``True``, print the full scan report JSON payload to stdout.
    """
    report = analyze_project(source, source_framework=source_framework)
    if output:
        save_scan_report(report, output)
        success(f"Scan report written to {output}")

    if as_json:
        echo(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return

    info(f"Source framework: {source_framework}")
    info(f"Source root: {report.source_root}")
    info(f"Files scanned: {report.files_scanned}")
    info(f"Routes detected: {report.total_routes}")
    info(f"Diagnostics: {report.total_diagnostics}")
    for module in report.modules:
        info(
            f"- {module.relative_path}: "
            f"apps={len(module.app_instances)} routes={len(module.routes)} "
            f"includes={len(module.include_routers)}"
        )
        _print_diagnostics("  ", module.diagnostics)
    _print_diagnostics("", report.diagnostics)


@app.command(
    help=(
        "Convert a source project into a Lilya project using deterministic AST rules.\n\n"
        "Examples:\n"
        "  lilya-converter convert ./fastapi_app ./lilya_app\n"
        "  lilya-converter convert ./flask_app ./lilya_app --source flask --dry-run --diff\n"
        "  lilya-converter convert ./fastapi_app ./lilya_app --report ./reports/convert.json"
    ),
)
def convert(
    source: Annotated[str, Argument(help="Source project root.")],
    target: Annotated[str, Argument(help="Output Lilya project root.")],
    source_framework: Annotated[
        str,
        Option("fastapi", "--source", type=SOURCE_CHOICE, help=SOURCE_HELP),
    ] = "fastapi",
    report: Annotated[
        str | None,
        Option(None, "--report", type=str, help="Optional JSON report output path."),
    ] = None,
    dry_run: Annotated[
        bool,
        Option(False, "--dry-run", help="Compute changes without writing files.", is_flag=True),
    ] = False,
    diff: Annotated[
        bool,
        Option(False, "--diff", help="Print unified diffs for changed Python files.", is_flag=True),
    ] = False,
    copy_assets: Annotated[
        bool,
        Option(
            True,
            "--copy-non-python/--no-copy-non-python",
            help="Copy non-Python files to target.",
        ),
    ] = True,
) -> None:
    """Convert a source tree into Lilya-compatible files.

    Args:
        source: Source project root.
        target: Destination Lilya project root.
        source_framework: Source framework identifier.
        report: Optional path where conversion report JSON is written.
        dry_run: If ``True``, compute/report changes without writing files.
        diff: If ``True``, print unified diffs for changed Python files.
        copy_assets: If ``True``, copy non-Python files into the target root.
    """
    conversion_report = convert_project(
        source_root=source,
        target_root=target,
        source_framework=source_framework,
        dry_run=dry_run,
        copy_non_python=copy_assets,
    )
    if report:
        save_conversion_report(conversion_report, report)
        success(f"Conversion report written to {report}")

    info(f"Source framework: {source_framework}")
    info(f"Source: {conversion_report.source_root}")
    info(f"Target: {conversion_report.target_root}")
    info(f"Dry-run: {conversion_report.dry_run}")
    info(f"Files total: {conversion_report.files_total}")
    info(f"Files changed: {conversion_report.files_changed}")
    info(f"Files written: {conversion_report.files_written}")
    info(
        f"Applied rules: {', '.join(conversion_report.applied_rules) if conversion_report.applied_rules else '(none)'}"
    )
    _print_diagnostics("", conversion_report.diagnostics)
    if not any(item.severity == "error" for item in conversion_report.diagnostics):
        success("Conversion completed.")

    if diff:
        for change in conversion_report.file_changes:
            if change.changed and change.unified_diff:
                echo(change.unified_diff.rstrip())


@app.command(
    help=(
        "Create a minimal Lilya scaffold informed by scanned source structure.\n\n"
        "Examples:\n"
        "  lilya-converter scaffold ./fastapi_app ./lilya_scaffold\n"
        "  lilya-converter scaffold ./flask_app ./lilya_scaffold --source flask"
    ),
)
def scaffold(
    source: Annotated[str, Argument(help="Source project root to inspect.")],
    target: Annotated[str, Argument(help="Destination root for Lilya scaffold.")],
    source_framework: Annotated[
        str,
        Option("fastapi", "--source", type=SOURCE_CHOICE, help=SOURCE_HELP),
    ] = "fastapi",
    dry_run: Annotated[
        bool,
        Option(False, "--dry-run", help="Show scaffold plan without writing files.", is_flag=True),
    ] = False,
) -> None:
    """Generate a minimal Lilya scaffold in the target directory.

    Args:
        source: Source project root used for structural detection.
        target: Destination directory for scaffolded Lilya files.
        source_framework: Source framework identifier.
        dry_run: If ``True``, report scaffold actions without writing files.
    """
    report = scaffold_project(
        source_root=source,
        target_root=target,
        source_framework=source_framework,
        dry_run=dry_run,
    )
    info(f"Source framework: {source_framework}")
    info(f"Source: {report.source_root}")
    info(f"Target: {report.target_root}")
    info(f"Dry-run: {report.dry_run}")
    info(f"Files written: {report.files_written}")
    _print_diagnostics("", report.diagnostics)
    success("Scaffold completed.")


map_app = Sayer(
    name="map",
    help="Inspect conversion mapping rules and report outcomes.",
    display_full_help=True,
)


@map_app.command(
    "rules",
    help=(
        "List all available conversion rule identifiers and summaries.\n\n"
        "Example:\n"
        "  lilya-converter map rules\n"
        "  lilya-converter map rules --source flask"
    ),
)
def map_rules(
    source_framework: Annotated[
        str,
        Option("fastapi", "--source", type=SOURCE_CHOICE, help=SOURCE_HELP),
    ] = "fastapi",
) -> None:
    """Print known conversion rules for one source framework.

    Args:
        source_framework: Source framework identifier.
    """
    info(f"Source framework: {source_framework}")
    for rule_id, summary in mapping_rules(source_framework=source_framework):
        info(f"- {rule_id}: {summary}")


@map_app.command(
    "applied",
    help=(
        "Display which rules were applied in a conversion report JSON file.\n\n"
        "Example:\n"
        "  lilya-converter map applied ./reports/convert.json"
    ),
)
def map_applied(
    report: Annotated[
        str,
        Argument(help="Path to a conversion report JSON file."),
    ],
) -> None:
    """Print applied rule IDs from a persisted conversion report.

    Args:
        report: Path to a conversion report JSON generated by ``convert``.

    Raises:
        click.ClickException: If ``report`` does not exist.
    """
    path = Path(report)
    if not path.exists():
        raise click.ClickException(f"Report file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rules = payload.get("applied_rules", [])
    info(f"Report: {path}")
    info(f"Applied rule count: {len(rules)}")
    for rule in rules:
        info(f"- {rule}")


app.add_app("map", map_app)


@app.command(
    help=(
        "Run post-conversion checks (syntax, residual source patterns, unresolved local imports) "
        "on a target Lilya project.\n\n"
        "Examples:\n"
        "  lilya-converter verify ./lilya_app\n"
        "  lilya-converter verify ./lilya_app --source flask --report ./reports/verify.json"
    ),
)
def verify(
    target: Annotated[str, Argument(help="Converted Lilya project root.")],
    source_framework: Annotated[
        str,
        Option("fastapi", "--source", type=SOURCE_CHOICE, help=SOURCE_HELP),
    ] = "fastapi",
    report: Annotated[
        str | None,
        Option(None, "--report", type=str, help="Optional JSON report output path."),
    ] = None,
) -> None:
    """Verify structural correctness of a converted Lilya project.

    Args:
        target: Root directory of the converted Lilya project.
        source_framework: Source framework identifier for residual checks.
        report: Optional path where verify report JSON is written.

    Raises:
        click.ClickException: If verification finds at least one error diagnostic.
    """
    verify_report = verify_project(target_root=target, source_framework=source_framework)
    if report:
        save_verify_report(verify_report, report)
        success(f"Verify report written to {report}")

    info(f"Source framework: {source_framework}")
    info(f"Target: {verify_report.target_root}")
    info(f"Diagnostics: {len(verify_report.diagnostics)}")
    _print_diagnostics("", verify_report.diagnostics)
    if verify_report.has_errors:
        raise click.ClickException("Verification failed with syntax or structural errors.")
    success("Verification completed.")
