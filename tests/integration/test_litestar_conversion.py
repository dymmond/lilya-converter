from __future__ import annotations

from pathlib import Path

from lilya_converter.engine import convert_project

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
LITESTAR_FIXTURES = FIXTURES_ROOT / "litestar"
LITESTAR_GOLDEN_FIXTURES = FIXTURES_ROOT / "golden_litestar"


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


def test_litestar_conversion_matches_golden_output(tmp_path: Path) -> None:
    """Validate Litestar fixture conversion against expected Lilya output.

    Args:
        tmp_path: Temporary target workspace provided by pytest.
    """
    source = LITESTAR_FIXTURES / "minimal"
    expected = LITESTAR_GOLDEN_FIXTURES / "minimal"
    target = tmp_path / "minimal"

    report = convert_project(source, target, source_framework="litestar", dry_run=False)

    assert report.files_total == 1
    assert _read_tree(target) == _read_tree(expected)
    assert {
        "litestar_decorators_to_paths",
        "litestar_imports_to_lilya",
        "litestar_app_route_handlers_to_routes",
        "litestar_router_path_to_include",
        "litestar_path_normalization",
    }.issubset(set(report.applied_rules))
