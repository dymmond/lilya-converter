from __future__ import annotations

from pathlib import Path

from lilya_converter.scanner import FastAPIScanner


def test_scan_detects_apps_routes_and_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text(
        """
from fastapi import APIRouter, Depends, FastAPI

app = FastAPI()
router = APIRouter(prefix=\"/items\")


async def dep():
    return \"x\"


@app.get(\"/ok\", dependencies=[Depends(dep)])
async def ok(value=Depends(dep)):
    return value


app.include_router(router, prefix=\"/v1\")
app.add_middleware(object)


@app.middleware(\"http\")
async def middleware(request, call_next):
    return await call_next(request)


@app.on_event(\"startup\")
async def startup():
    pass


@app.exception_handler(ValueError)
async def handle_error(request, exc):
    return None
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = FastAPIScanner().scan(tmp_path)

    assert report.files_scanned == 1
    assert report.total_routes == 1
    module = report.modules[0]
    assert module.relative_path == "main.py"
    assert [instance.kind for instance in module.app_instances] == ["FastAPI", "APIRouter"]
    assert len(module.include_routers) == 1
    assert module.middleware_calls
    assert module.middleware_decorators
    assert module.event_decorators
    assert module.exception_handler_decorators
    assert {item.name for item in module.dependency_refs} == {"dep", "value"}
    assert any(item.code == "scan.middleware.decorator_unsupported" for item in module.diagnostics)


def test_scan_reports_syntax_errors(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def broken(:\n", encoding="utf-8")

    report = FastAPIScanner().scan(tmp_path)

    assert report.files_scanned == 0
    assert len(report.diagnostics) == 1
    assert report.diagnostics[0].code == "scan.syntax_error"
    assert report.diagnostics[0].file == "bad.py"


def test_scan_collects_constructor_and_include_dependencies(tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text(
        """
from fastapi import APIRouter, Depends, FastAPI


def dep_app():
    return "app"


def dep_router():
    return "router"


def dep_include():
    return "include"


app = FastAPI(dependencies=[Depends(dep_app)])
router = APIRouter(dependencies=[Depends(dep_router)])
app.include_router(router, dependencies=[Depends(dep_include)])
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = FastAPIScanner().scan(tmp_path)
    module = report.modules[0]
    refs = {(item.name, item.source) for item in module.dependency_refs}

    assert ("dep_app", "app") in refs
    assert ("dep_router", "router") in refs
    assert ("dep_include", "include") in refs
