from __future__ import annotations

from lilya_converter.adapters.litestar.transformer import transform_python_source


def _transform(source: str):
    """Transform helper for Litestar source snippets.

    Args:
        source: Source code string to transform.

    Returns:
        Litestar transform result for ``main.py``.
    """
    return transform_python_source(source, relative_path="main.py")


def test_litestar_route_handlers_convert_to_routes_and_include() -> None:
    """Convert Litestar decorators and router path to Lilya routes/includes."""
    source = (
        """
from litestar import Litestar, Router, get


@get("/health")
async def health():
    return {"ok": True}


@get("")
async def items():
    return {"items": []}


api = Router(path="/api", route_handlers=[items])
app = Litestar(route_handlers=[health, api])
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "from lilya.apps import Lilya as Litestar" in result.content
    assert "from lilya.routing import Router, Path, Include" in result.content
    assert "Path('/health', health, methods=['GET'])" in result.content
    assert "Path('/', items, methods=['GET'])" in result.content
    assert "Include(path='/api', app=api)" in result.content
    assert "route_handlers" not in result.content


def test_litestar_route_decorator_requires_methods() -> None:
    """Emit a diagnostic when route decorator omits http_method."""
    source = (
        """
from litestar import Litestar, route


@route("/health")
async def health():
    return {"ok": True}


app = Litestar(route_handlers=[health])
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert any(item.code == "convert.litestar.route_missing_http_method" for item in result.diagnostics)
