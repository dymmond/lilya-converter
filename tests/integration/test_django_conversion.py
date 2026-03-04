from __future__ import annotations

from pathlib import Path

from lilya_converter.engine import convert_project

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
DJANGO_FIXTURES = FIXTURES_ROOT / "django"
DJANGO_GOLDEN_FIXTURES = FIXTURES_ROOT / "golden_django"


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


def test_django_conversion_matches_golden_output(tmp_path: Path) -> None:
    """Validate Django fixture conversion against expected Lilya output.

    Args:
        tmp_path: Temporary target workspace provided by pytest.
    """
    source = DJANGO_FIXTURES / "minimal"
    expected = DJANGO_GOLDEN_FIXTURES / "minimal"
    target = tmp_path / "minimal"

    report = convert_project(source, target, source_framework="django", dry_run=False)

    assert report.files_total == 3
    assert _read_tree(target) == _read_tree(expected)
    assert {
        "django_imports_to_lilya",
        "django_include_to_lilya_include",
        "django_path_to_lilya_path",
        "django_path_converter_normalization",
        "django_urlpatterns_to_app",
    }.issubset(set(report.applied_rules))
    converted_paths = {change.relative_path for change in report.file_changes}
    assert "project/directives/operations/rebuild.py" in converted_paths
