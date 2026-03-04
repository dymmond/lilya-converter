from __future__ import annotations

from pathlib import Path

from lilya_converter.adapters.litestar.scanner import LitestarScanner


def test_litestar_scanner_detects_routes_and_instances(tmp_path: Path) -> None:
    """Detect Litestar app/router constructors and route decorators."""
    source = tmp_path / "main.py"
    source.write_text(
        "\n".join(
            [
                "from litestar import Litestar, Router, get",
                "",
                "@get('/health')",
                "async def health():",
                "    return {'ok': True}",
                "",
                "router = Router(path='/api', route_handlers=[health])",
                "app = Litestar(route_handlers=[router])",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = LitestarScanner().scan(tmp_path)

    assert len(report.modules) == 1
    module = report.modules[0]
    assert len(module.app_instances) == 2
    assert {item.kind for item in module.app_instances} == {"Litestar", "Router"}
    assert len(module.routes) == 1
    assert module.routes[0].path == "'/health'"
