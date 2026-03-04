from __future__ import annotations

import json
from pathlib import Path

from lilya_converter.engine import (
    analyze_project,
    convert_project,
    mapping_rules,
    save_conversion_report,
    save_scan_report,
    save_verify_report,
    scaffold_project,
    verify_project,
)


def test_convert_project_dry_run_does_not_write(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    (source / "README.txt").write_text("hello\n", encoding="utf-8")

    report = convert_project(source, target, dry_run=True)

    assert report.dry_run is True
    assert report.files_total == 2
    assert report.files_written == 0
    assert not target.exists()


def test_convert_project_writes_python_and_non_python_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    (source / "data.txt").write_text("data\n", encoding="utf-8")

    report = convert_project(source, target, dry_run=False)

    assert report.files_total == 2
    assert report.files_written == 2
    assert (target / "main.py").exists()
    assert (target / "data.txt").read_text(encoding="utf-8") == "data\n"


def test_scaffold_project_creates_main_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    report = scaffold_project(source, target)

    assert report.files_written == 1
    assert (target / "main.py").exists()
    assert "from lilya.apps import Lilya" in (target / "main.py").read_text(encoding="utf-8")


def test_verify_project_reports_common_remaining_patterns(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "app.include_router(router)\n"
        "@app.middleware('http')\n"
        "async def middleware(request, call_next):\n"
        "    return await call_next(request)\n",
        encoding="utf-8",
    )

    report = verify_project(target)

    codes = {item.code for item in report.diagnostics}
    assert "verify.fastapi_import_remaining" in codes
    assert "verify.include_router_remaining" in codes
    assert "verify.middleware_decorator_remaining" in codes


def test_verify_project_reports_flask_remaining_patterns(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "main.py").write_text(
        "from flask import Flask\napp = Flask(__name__)\napp.register_blueprint(router)\n",
        encoding="utf-8",
    )

    report = verify_project(target, source_framework="flask")

    codes = {item.code for item in report.diagnostics}
    assert "verify.flask_import_remaining" in codes
    assert "verify.register_blueprint_remaining" in codes


def test_verify_project_reports_django_remaining_patterns(tmp_path: Path) -> None:
    """Ensure Django verify diagnostics detect residual source patterns."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "urls.py").write_text(
        "from django.urls import path\nurlpatterns = [path('', view)]\n",
        encoding="utf-8",
    )

    report = verify_project(target, source_framework="django")

    codes = {item.code for item in report.diagnostics}
    assert "verify.django_import_remaining" in codes
    assert "verify.urlpatterns_remaining" in codes


def test_verify_project_reports_litestar_remaining_patterns(tmp_path: Path) -> None:
    """Ensure Litestar verify diagnostics detect residual source patterns."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "main.py").write_text(
        "from litestar import Litestar\napp = Litestar(route_handlers=[])\n",
        encoding="utf-8",
    )

    report = verify_project(target, source_framework="litestar")

    codes = {item.code for item in report.diagnostics}
    assert "verify.litestar_import_remaining" in codes


def test_verify_project_reports_starlette_remaining_patterns(tmp_path: Path) -> None:
    """Ensure Starlette verify diagnostics detect residual source patterns."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "main.py").write_text(
        "from starlette.applications import Starlette\napp = Starlette(routes=[])\napp.mount('/', app=sub)\n",
        encoding="utf-8",
    )

    report = verify_project(target, source_framework="starlette")

    codes = {item.code for item in report.diagnostics}
    assert "verify.starlette_import_remaining" in codes
    assert "verify.mount_remaining" in codes


def test_verify_project_reports_parse_errors(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "main.py").write_text("def broken(:\n", encoding="utf-8")

    report = verify_project(target)

    assert report.has_errors is True
    assert any(item.code == "verify.syntax_error" for item in report.diagnostics)


def test_verify_project_reports_unresolved_local_imports(tmp_path: Path) -> None:
    target = tmp_path / "target"
    (target / "routers").mkdir(parents=True)
    (target / "routers" / "items.py").write_text("value = 1\n", encoding="utf-8")
    (target / "main.py").write_text(
        "from routers.missing import value\nfrom routers.items import value as ok\n",
        encoding="utf-8",
    )

    report = verify_project(target)

    codes = {item.code for item in report.diagnostics}
    assert "verify.unresolved_local_import" in codes


def test_report_serializers_write_json(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    scan_report = analyze_project(source)
    conversion_report = convert_project(source, tmp_path / "target", dry_run=True)
    verify_report = verify_project(tmp_path / "target")

    scan_path = tmp_path / "reports" / "scan.json"
    conversion_path = tmp_path / "reports" / "convert.json"
    verify_path = tmp_path / "reports" / "verify.json"

    save_scan_report(scan_report, scan_path)
    save_conversion_report(conversion_report, conversion_path)
    save_verify_report(verify_report, verify_path)

    assert len(json.loads(scan_path.read_text(encoding="utf-8"))["modules"]) == 1
    assert json.loads(conversion_path.read_text(encoding="utf-8"))["dry_run"] is True
    assert json.loads(verify_path.read_text(encoding="utf-8"))["target_root"]


def test_mapping_rules_exposes_known_rules() -> None:
    ids = {rule_id for rule_id, _summary in mapping_rules()}
    assert "include_router_to_include" in ids
    assert "depends_default_to_provides" in ids
    assert "api_route_to_route" in ids


def test_convert_report_is_deterministically_sorted(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "z.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    (source / "a.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    (source / "b.txt").write_text("payload\n", encoding="utf-8")

    first = convert_project(source, tmp_path / "target1", dry_run=True)
    second = convert_project(source, tmp_path / "target2", dry_run=True)

    first_paths = [change.relative_path for change in first.file_changes]
    second_paths = [change.relative_path for change in second.file_changes]
    assert first_paths == ["a.py", "b.txt", "z.py"]
    assert first_paths == second_paths
    assert first.applied_rules == second.applied_rules


def test_django_management_command_paths_are_mapped(tmp_path: Path) -> None:
    """Map Django management command paths into Lilya directives operations."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    command_file = source / "app" / "management" / "commands" / "refresh.py"
    command_file.parent.mkdir(parents=True)
    command_file.write_text("value = 1\n", encoding="utf-8")

    report = convert_project(source, target, source_framework="django", dry_run=False)

    mapped_file = target / "app" / "directives" / "operations" / "refresh.py"
    assert mapped_file.exists()
    assert mapped_file.read_text(encoding="utf-8") == "value = 1\n"
    assert any(change.relative_path == "app/directives/operations/refresh.py" for change in report.file_changes)
