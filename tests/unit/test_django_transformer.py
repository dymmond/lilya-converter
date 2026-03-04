from __future__ import annotations

from lilya_converter.adapters.django.transformer import transform_python_source


def _transform(source: str):
    """Transform helper for Django source snippets.

    Args:
        source: Source code string to transform.

    Returns:
        Django transform result for ``main.py``.
    """
    return transform_python_source(source, relative_path="main.py")


def test_django_path_and_include_are_converted() -> None:
    """Convert Django urlpatterns into Lilya Path/Include entries."""
    source = (
        """
from django.urls import include, path

urlpatterns = [
    path("", view, name="index"),
    path("api/", include("api.urls")),
]
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "from lilya.apps import Lilya" in result.content
    assert "from lilya.routing import Include, Path" in result.content
    assert "Path('/', view, name='index')" in result.content
    assert "Include(path='/api/', app='api.urls')" in result.content
    assert "app = Lilya(routes=urlpatterns)" in result.content


def test_django_converter_syntax_is_normalized() -> None:
    """Normalize Django converter syntax to Lilya syntax."""
    source = (
        """
from django.urls import path

urlpatterns = [
    path("items/<int:item_id>/", view),
]
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "Path('/items/{item_id:int}/', view)" in result.content
    assert "django_path_converter_normalization" in result.applied_rules
