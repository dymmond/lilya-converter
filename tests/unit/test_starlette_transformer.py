from __future__ import annotations

from lilya_converter.adapters.starlette.transformer import transform_python_source


def _transform(source: str):
    """Transform helper for Starlette source snippets.

    Args:
        source: Source code string to transform.

    Returns:
        Starlette transform result for ``main.py``.
    """
    return transform_python_source(source, relative_path="main.py")


def test_starlette_route_mount_and_add_route_are_converted() -> None:
    """Convert Starlette Route/Mount/add_route into Lilya-compatible forms."""
    source = (
        """
from starlette.applications import Starlette
from starlette.routing import Mount, Route


async def home(request):
    return None


app = Starlette(routes=[Route("", home), Mount("/api", app=api)])
app.mount("", app=api)
app.add_route("", route=home, methods=["GET"])
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "from lilya.apps import Lilya as Starlette" in result.content
    assert "from lilya.routing import Include as Mount, Path as Route" in result.content
    assert "Route('/', home)" in result.content
    assert "Mount('/api', app=api)" in result.content
    assert "app.include(path='/', app=api)" in result.content
    assert "app.add_route(path='/', handler=home, methods=['GET'])" in result.content


def test_starlette_websocket_route_is_converted() -> None:
    """Convert WebSocketRoute import mapping and call shape."""
    source = (
        """
from starlette.routing import WebSocketRoute


async def ws(socket):
    return None


routes = [WebSocketRoute("", ws)]
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "from lilya.routing import WebSocketPath as WebSocketRoute" in result.content
    assert "WebSocketRoute('/', ws)" in result.content
