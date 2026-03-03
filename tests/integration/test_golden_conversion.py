from __future__ import annotations

from pathlib import Path

import pytest

from lilya_converter.engine import convert_project

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
FASTAPI_FIXTURES = FIXTURES_ROOT / "fastapi"
GOLDEN_FIXTURES = FIXTURES_ROOT / "golden"


SCENARIOS = [
    "complex",
    "minimal",
    "dependencies",
    "routers",
    "middleware",
    "lifespan",
    "responses",
]

EXPECTED_DIAGNOSTICS = {
    "complex": {
        "convert.constructor.kwargs_removed",
        "convert.depends.non_route_untouched",
        "convert.include_router.kwargs_removed",
        "convert.response_class.orjson_ujson",
        "convert.route.kwargs_removed",
    },
    "minimal": set(),
    "dependencies": {"convert.depends.non_route_untouched"},
    "routers": {
        "convert.include_router.kwargs_removed",
        "convert.constructor.kwargs_removed",
        "convert.route.kwargs_removed",
    },
    "middleware": {"convert.middleware.decorator_removed"},
    "lifespan": set(),
    "responses": {"convert.response_class.orjson_ujson", "convert.route.kwargs_removed"},
}

EXPECTED_RULES = {
    "complex": {
        "annotated_depends_to_provide",
        "api_route_to_route",
        "constructor_dependencies_to_dict",
        "decorator_dependencies_to_provide",
        "depends_default_to_provides",
        "depends_to_provide",
        "exception_handler_decorator_to_call",
        "include_router_to_include",
        "openapi_flag_conversion",
        "route_dependencies_dict",
        "router_prefix_extracted",
        "router_prefix_to_route_path",
    },
    "minimal": set(),
    "dependencies": {
        "annotated_depends_to_provide",
        "constructor_dependencies_to_dict",
        "decorator_dependencies_to_provide",
        "depends_default_to_provides",
        "depends_to_provide",
        "route_dependencies_dict",
    },
    "routers": {
        "constructor_dependencies_to_dict",
        "decorator_dependencies_to_provide",
        "depends_default_to_provides",
        "depends_to_provide",
        "include_router_to_include",
        "route_dependencies_dict",
        "router_prefix_extracted",
        "router_prefix_to_route_path",
    },
    "middleware": set(),
    "lifespan": set(),
    "responses": {
        "api_route_to_route",
        "include_router_to_include",
        "openapi_flag_conversion",
        "trace_to_route",
    },
}


def _read_tree(root: Path) -> dict[str, str]:
    content: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        rel = str(path.relative_to(root))
        content[rel] = path.read_text(encoding="utf-8")
    return content


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_conversion_matches_golden_output(tmp_path: Path, scenario: str) -> None:
    source = FASTAPI_FIXTURES / scenario
    expected = GOLDEN_FIXTURES / scenario
    target = tmp_path / scenario

    report = convert_project(source, target, dry_run=False)

    assert report.files_total >= 1
    assert expected.exists(), f"Missing golden fixture: {expected}"
    assert _read_tree(target) == _read_tree(expected)
    assert set(report.applied_rules) == EXPECTED_RULES[scenario]
    assert EXPECTED_DIAGNOSTICS[scenario].issubset({item.code for item in report.diagnostics})


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_dry_run_writes_nothing(tmp_path: Path, scenario: str) -> None:
    source = FASTAPI_FIXTURES / scenario
    target = tmp_path / f"{scenario}-dry"

    report = convert_project(source, target, dry_run=True)

    assert report.dry_run is True
    assert report.files_total >= 1
    assert report.files_written == 0
    assert not target.exists()
