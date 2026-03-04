from __future__ import annotations

from pathlib import Path

from lilya_converter.adapters.starlette.scanner import StarletteScanner


def test_starlette_scanner_detects_routes_and_mount_calls(tmp_path: Path) -> None:
    """Detect Starlette constructors plus Route/Mount call metadata."""
    source = tmp_path / "main.py"
    source.write_text(
        "\n".join(
            [
                "from starlette.applications import Starlette",
                "from starlette.routing import Mount, Route",
                "",
                "async def home(request):",
                "    return None",
                "",
                "api = Starlette(routes=[Route('/users', home)])",
                "app = Starlette(routes=[Mount('/api', app=api)])",
                "app.mount('', app=api)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = StarletteScanner().scan(tmp_path)

    assert len(report.modules) == 1
    module = report.modules[0]
    assert len(module.app_instances) == 2
    assert {item.kind for item in module.app_instances} == {"Starlette"}
    assert len(module.routes) >= 2
    assert len(module.include_routers) == 1
    assert module.include_routers[0].prefix_expr == "''"
