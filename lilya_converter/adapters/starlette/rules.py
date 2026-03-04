"""Starlette conversion rule registry."""

from __future__ import annotations

from lilya_converter.core.rules import MappingRule

RULES: list[MappingRule] = [
    MappingRule(
        id="starlette_imports_to_lilya",
        summary="Starlette app/routing imports are mapped to Lilya app/routing imports.",
    ),
    MappingRule(
        id="starlette_route_to_path",
        summary="Starlette Route(...) calls are converted to Lilya Path(...) calls.",
    ),
    MappingRule(
        id="starlette_websocket_route_to_websocket_path",
        summary="Starlette WebSocketRoute(...) calls are converted to Lilya WebSocketPath(...) calls.",
    ),
    MappingRule(
        id="starlette_mount_to_include",
        summary="Starlette Mount(...) and mount(...) calls are converted to Lilya Include semantics.",
    ),
    MappingRule(
        id="starlette_add_route_signature",
        summary="Starlette add_route(route=...) calls are normalized to Lilya add_route(handler=...).",
    ),
    MappingRule(
        id="starlette_path_normalization",
        summary="Starlette paths are normalized to non-empty, leading-slash Lilya paths.",
    ),
]
