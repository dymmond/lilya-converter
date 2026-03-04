from __future__ import annotations

from lilya_converter.adapters.flask.transformer import transform_python_source


def _transform(source: str):
    """Transform helper for Flask source snippets.

    Args:
        source: Source code string to transform.

    Returns:
        Flask transform result for ``main.py``.
    """
    return transform_python_source(source, relative_path="main.py")


def test_blueprint_prefix_and_register_blueprint_are_converted() -> None:
    """Convert blueprint prefix and registration into Lilya route/include semantics."""
    source = (
        """
from flask import Blueprint, Flask

app = Flask(__name__)
bp = Blueprint("items", __name__, url_prefix="/api")


@bp.route("/items")
def list_items():
    return {"items": []}


app.register_blueprint(bp)
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "from lilya.apps import Lilya as Flask" in result.content
    assert "from lilya.routing import Router as Blueprint" in result.content
    assert "@bp.route('/api/items', methods=['GET'])" in result.content
    assert "app.include(path='/', app=bp)" in result.content
    assert "blueprint_prefix_extracted" in result.applied_rules
    assert "blueprint_prefix_to_route_path" in result.applied_rules
    assert "register_blueprint_to_include" in result.applied_rules


def test_route_endpoint_and_unsupported_kwargs_are_normalized() -> None:
    """Map Flask endpoint to name and remove unsupported decorator kwargs."""
    source = (
        """
from flask import Flask

app = Flask(__name__)


@app.route("/x", methods=["POST"], endpoint="ep", strict_slashes=False)
def x():
    return "ok"
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "@app.route('/x', methods=['POST'], name='ep')" in result.content
    assert any(item.code == "convert.flask.route_kwargs_removed" for item in result.diagnostics)


def test_register_blueprint_empty_prefix_is_normalized_to_root() -> None:
    """Normalize empty blueprint include prefix to `/` for Lilya compatibility."""
    source = (
        """
from flask import Blueprint, Flask

app = Flask(__name__)
bp = Blueprint("items", __name__)
app.register_blueprint(bp, url_prefix="")
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "app.include(path='/', app=bp)" in result.content


def test_dynamic_blueprint_prefix_emits_diagnostic() -> None:
    """Emit manual-review diagnostic when blueprint prefix/path merge is dynamic."""
    source = (
        """
from flask import Blueprint

prefix = "/api"
bp = Blueprint("items", __name__, url_prefix=prefix)


@bp.route("/items")
def list_items():
    return {"items": []}
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "@bp.route('/items', methods=['GET'])" in result.content
    assert any(item.code == "convert.blueprint_prefix.dynamic_path" for item in result.diagnostics)
