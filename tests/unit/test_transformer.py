from __future__ import annotations

import ast

from lilya_converter.transformer import transform_python_source


def _transform(source: str):
    return transform_python_source(source, relative_path="main.py")


def test_non_route_depends_is_not_rewritten() -> None:
    source = (
        """
from fastapi import Depends, FastAPI

app = FastAPI()


def dep():
    return 1


def helper(x=Depends(dep)):
    return x


@app.get("/x")
def route(x=Depends(dep)):
    return x
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "def helper(x=Depends(dep))" in result.content
    assert "def route(x=Provides())" in result.content
    assert "dependencies={'x': Provide(dep)}" in result.content
    assert any(item.code == "convert.depends.non_route_untouched" for item in result.diagnostics)


def test_include_router_and_prefix_are_normalized() -> None:
    source = (
        """
from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix="/items")
app.include_router(router, prefix="/v1", tags=["ignored"])
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "app.include(path='/v1', app=router)" in result.content
    assert "include_router" not in result.content
    assert any(item.code == "convert.include_router.kwargs_removed" for item in result.diagnostics)


def test_router_prefix_is_merged_into_route_paths() -> None:
    source = (
        """
from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/hello")
async def hello():
    return {"ok": True}
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "router = APIRouter()" in result.content
    assert "@router.get('/api/hello')" in result.content
    assert "router_prefix_extracted" in result.applied_rules
    assert "router_prefix_to_route_path" in result.applied_rules


def test_dynamic_router_prefix_emits_manual_review_diagnostic() -> None:
    source = (
        """
from fastapi import APIRouter

prefix_value = "/api"
router = APIRouter(prefix=prefix_value)


@router.get("/hello")
async def hello():
    return {"ok": True}
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "@router.get('/hello')" in result.content
    assert any(item.code == "convert.router_prefix.dynamic_path" for item in result.diagnostics)


def test_api_route_and_trace_are_converted_to_route() -> None:
    source = (
        """
from fastapi import APIRouter

router = APIRouter()


@router.api_route("/payload", methods=["PATCH"])
async def payload():
    return {"ok": True}


@router.trace("/trace", include_in_schema=False)
async def trace_route():
    return {"ok": True}
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "@router.route('/payload', methods=['PATCH'])" in result.content
    assert "@router.route('/trace', include_in_schema=False, methods=['TRACE'])" in result.content
    assert "api_route" not in result.content


def test_websocket_include_in_schema_kwarg_is_removed() -> None:
    source = (
        """
from fastapi import APIRouter

router = APIRouter()


@router.websocket("/ws", include_in_schema=False)
async def ws(socket):
    await socket.accept()
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "@router.websocket('/ws')" in result.content
    assert any(item.code == "convert.route.kwargs_removed" for item in result.diagnostics)


def test_exception_handler_decorator_becomes_registration_call() -> None:
    source = (
        """
from fastapi import FastAPI

app = FastAPI()


@app.exception_handler(ValueError)
async def handle(request, exc):
    return None
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert "@app.exception_handler" not in result.content
    assert "app.add_exception_handler(ValueError, handle)" in result.content


def test_response_imports_are_mapped_to_lilya() -> None:
    source = (
        """
from fastapi.responses import ORJSONResponse, PlainTextResponse
""".strip()
        + "\n"
    )

    result = _transform(source)

    assert (
        "from lilya.responses import JSONResponse as ORJSONResponse, PlainText as PlainTextResponse" in result.content
    )
    assert any(item.code == "convert.response_class.orjson_ujson" for item in result.diagnostics)


def test_transformed_source_is_valid_python() -> None:
    source = (
        """
from fastapi import FastAPI

app = FastAPI(openapi_url=None)
""".strip()
        + "\n"
    )

    result = _transform(source)

    ast.parse(result.content)
    assert "enable_openapi=False" in result.content
