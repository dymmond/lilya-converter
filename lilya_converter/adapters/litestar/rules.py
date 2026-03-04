"""Litestar conversion rule registry."""

from __future__ import annotations

from lilya_converter.core.rules import MappingRule

RULES: list[MappingRule] = [
    MappingRule(
        id="litestar_imports_to_lilya",
        summary="Litestar imports are mapped to Lilya app/routing imports where equivalents exist.",
    ),
    MappingRule(
        id="litestar_decorators_to_paths",
        summary="Litestar module-level HTTP decorators are converted into explicit Lilya Path declarations.",
    ),
    MappingRule(
        id="litestar_app_route_handlers_to_routes",
        summary="Litestar(route_handlers=...) and Router(route_handlers=...) are normalized to Lilya routes.",
    ),
    MappingRule(
        id="litestar_router_path_to_include",
        summary="Litestar Router(path=...) entries are materialized as Lilya Include(path=..., app=router).",
    ),
    MappingRule(
        id="litestar_constructor_kwargs_filtered",
        summary="Unsupported Litestar constructor kwargs are removed with explicit diagnostics.",
    ),
    MappingRule(
        id="litestar_path_normalization",
        summary="Litestar paths are normalized to non-empty, leading-slash Lilya paths.",
    ),
]
