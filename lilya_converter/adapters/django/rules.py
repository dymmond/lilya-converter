"""Django conversion rule registry."""

from __future__ import annotations

from lilya_converter.core.rules import MappingRule

RULES: list[MappingRule] = [
    MappingRule(
        id="django_imports_to_lilya",
        summary="Django URL routing imports are mapped to Lilya app/routing imports.",
    ),
    MappingRule(
        id="django_path_to_lilya_path",
        summary="django.urls.path(...) calls are converted to Lilya Path(..., handler=...).",
    ),
    MappingRule(
        id="django_include_to_lilya_include",
        summary="django.urls.include(...) entries are converted to Lilya Include(path=..., app=...).",
    ),
    MappingRule(
        id="django_urlpatterns_to_app",
        summary="A Lilya app is materialized from urlpatterns via Lilya(routes=urlpatterns).",
    ),
    MappingRule(
        id="django_path_converter_normalization",
        summary="Django route converters like <int:id> are normalized to Lilya-style {id:int} syntax.",
    ),
]
