from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import ORJSONResponse


def app_dep() -> str:
    return "app"


def include_dep() -> str:
    return "include"


def router_dep() -> str:
    return "router"


def route_dep() -> str:
    return "route"


app = FastAPI(openapi_url="/openapi.json", dependencies=[Depends(app_dep)])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
router = APIRouter(prefix="/api", dependencies=[Depends(router_dep)], tags=["ignored"])


def helper(value: str = Depends(app_dep)) -> str:
    return value


@router.api_route(
    "/items/{item_id}",
    methods=["GET", "POST"],
    dependencies=[Depends(route_dep)],
    response_model=dict,
    status_code=201,
    response_class=ORJSONResponse,
    responses={404: {"description": "missing"}},
)
async def item(
    item_id: int,
    token: Annotated[str, Depends(route_dep)],
    extra: str = Depends(router_dep),
):
    if item_id < 0:
        raise HTTPException(status_code=404)
    return {"id": item_id, "token": token, "extra": extra}


@router.websocket("/ws", include_in_schema=False)
async def ws(socket):
    await socket.accept()


@app.exception_handler(ValueError)
async def handle_value_error(request, exc):
    return ORJSONResponse({"detail": "bad"}, status_code=400)


app.include_router(
    router,
    prefix="/v1",
    dependencies=[Depends(include_dep)],
    include_in_schema=False,
    tags=["ignored"],
)
