from __future__ import annotations

from pathlib import Path

from lilya_converter.engine import convert_project

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
FLASK_FIXTURES = FIXTURES_ROOT / "flask"
FLASK_GOLDEN_FIXTURES = FIXTURES_ROOT / "golden_flask"


def _read_tree(root: Path) -> dict[str, str]:
    """Read all files in a fixture tree into a relative-path map.

    Args:
        root: Root path for recursive file reads.

    Returns:
        Relative path to file content mapping.
    """
    content: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        rel = str(path.relative_to(root))
        content[rel] = path.read_text(encoding="utf-8")
    return content


def test_flask_conversion_matches_golden_output(tmp_path: Path) -> None:
    """Validate Flask fixture conversion against expected Lilya output.

    Args:
        tmp_path: Temporary target workspace provided by pytest.
    """
    source = FLASK_FIXTURES / "minimal"
    expected = FLASK_GOLDEN_FIXTURES / "minimal"
    target = tmp_path / "minimal"

    report = convert_project(source, target, source_framework="flask", dry_run=False)

    assert report.files_total == 1
    assert _read_tree(target) == _read_tree(expected)
    assert {
        "flask_imports_to_lilya",
        "flask_constructor_sanitized",
        "blueprint_prefix_extracted",
        "blueprint_prefix_to_route_path",
        "register_blueprint_to_include",
    }.issubset(set(report.applied_rules))
