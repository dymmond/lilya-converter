"""Flask conversion rule registry."""

from __future__ import annotations

from lilya_converter.core.rules import MappingRule

RULES: list[MappingRule] = [
    MappingRule(
        id="flask_imports_to_lilya",
        summary="Flask and Blueprint imports are mapped to Lilya app and router imports.",
    ),
    MappingRule(
        id="flask_constructor_sanitized",
        summary="Flask/Blueprint constructor call arguments are removed when unsupported by Lilya constructors.",
    ),
    MappingRule(
        id="blueprint_prefix_extracted",
        summary="Blueprint(url_prefix=...) is extracted because Lilya Router has no prefix constructor argument.",
    ),
    MappingRule(
        id="blueprint_prefix_to_route_path",
        summary="Extracted Blueprint url_prefix is merged into route decorator path strings.",
    ),
    MappingRule(
        id="register_blueprint_to_include",
        summary="register_blueprint(...) calls are converted to include(path=..., app=...).",
    ),
    MappingRule(
        id="flask_route_default_methods",
        summary="@app.route decorators without methods are normalized to methods=['GET'].",
    ),
    MappingRule(
        id="flask_route_endpoint_to_name",
        summary="Flask route endpoint=... is mapped to Lilya name=... for route decorators.",
    ),
    MappingRule(
        id="flask_route_kwargs_filtered",
        summary="Unsupported Flask route/register kwargs are removed with explicit diagnostics.",
    ),
]
