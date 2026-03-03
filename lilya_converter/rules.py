"""Conversion rule registry.

Each rule entry exposes a stable ID and summary that can be shown via
`lilya-converter map rules` and recorded in conversion reports.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MappingRule:
    """Describes one named conversion rule.

    Attributes:
        id: Stable machine-readable rule identifier.
        summary: Human-readable description of the rule behavior.
    """

    id: str
    summary: str


RULES: list[MappingRule] = [
    MappingRule(
        id="router_prefix_extracted",
        summary="APIRouter(prefix=...) is extracted because Lilya Router has no prefix constructor argument.",
    ),
    MappingRule(
        id="router_prefix_to_route_path",
        summary="Extracted APIRouter(prefix=...) is merged into route decorator path strings.",
    ),
    MappingRule(
        id="include_router_to_include",
        summary="include_router(...) calls are converted to include(path=..., app=...).",
    ),
    MappingRule(
        id="api_route_to_route",
        summary="FastAPI .api_route(...) decorators are normalized to Lilya .route(..., methods=[...]).",
    ),
    MappingRule(
        id="trace_to_route",
        summary="FastAPI .trace(...) decorators are normalized to Lilya .route(..., methods=['TRACE']).",
    ),
    MappingRule(
        id="depends_default_to_provides",
        summary="Function parameter defaults Depends(...) are converted to Provides() with route dependencies map.",
    ),
    MappingRule(
        id="depends_kwonly_to_provides",
        summary="Keyword-only Depends(...) defaults are converted to Provides().",
    ),
    MappingRule(
        id="annotated_depends_to_provide",
        summary="Annotated[..., Depends(...)] metadata is converted into Lilya dependency mappings.",
    ),
    MappingRule(
        id="decorator_dependencies_to_provide",
        summary="Decorator dependencies=[Depends(...)] are converted to dependencies={...} + synthetic params.",
    ),
    MappingRule(
        id="route_dependencies_dict",
        summary="Route decorator dependencies become Lilya dependencies dicts.",
    ),
    MappingRule(
        id="constructor_dependencies_to_dict",
        summary="FastAPI/APIRouter dependencies lists are converted to Lilya dependency maps.",
    ),
    MappingRule(
        id="exception_handler_decorator_to_call",
        summary="FastAPI @app.exception_handler(...) decorators are converted to app.add_exception_handler(...) calls.",
    ),
    MappingRule(
        id="openapi_flag_conversion",
        summary="FastAPI openapi_url semantics are normalized to Lilya enable_openapi flag.",
    ),
]
