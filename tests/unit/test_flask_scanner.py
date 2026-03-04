from __future__ import annotations

from pathlib import Path

from lilya_converter.adapters.flask.scanner import FlaskScanner


def test_scan_detects_flask_apps_routes_and_blueprint_includes(tmp_path: Path) -> None:
    """Detect Flask app/blueprint constructors, routes, and blueprint registration."""
    source = tmp_path / "main.py"
    source.write_text(
        """
from flask import Blueprint, Flask

app = Flask(__name__)
api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/items")
def list_items():
    return {"items": []}


app.register_blueprint(api, url_prefix="/v1")
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = FlaskScanner().scan(tmp_path)

    assert report.files_scanned == 1
    assert report.total_routes == 1
    module = report.modules[0]
    assert [instance.kind for instance in module.app_instances] == ["Flask", "Blueprint"]
    assert len(module.include_routers) == 1
    assert module.include_routers[0].prefix_expr == "'/v1'"


def test_scan_reports_syntax_errors(tmp_path: Path) -> None:
    """Report scanner syntax diagnostics for unparsable Flask modules."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def broken(:\n", encoding="utf-8")

    report = FlaskScanner().scan(tmp_path)

    assert report.files_scanned == 0
    assert len(report.diagnostics) == 1
    assert report.diagnostics[0].code == "scan.syntax_error"
    assert report.diagnostics[0].file == "bad.py"
