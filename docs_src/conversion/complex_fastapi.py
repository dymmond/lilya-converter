from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI


def app_dep() -> str:
    return "app"


def include_dep() -> str:
    return "include"


def router_dep() -> str:
    return "router"


def route_dep() -> str:
    return "route"


app = FastAPI(openapi_url="/openapi.json", dependencies=[Depends(app_dep)])
router = APIRouter(prefix="/api", dependencies=[Depends(router_dep)], tags=["ignored"])


@router.api_route(
    "/items/{item_id}",
    methods=["GET", "POST"],
    dependencies=[Depends(route_dep)],
    response_model=dict,
)
async def item(
    item_id: int,
    token: Annotated[str, Depends(route_dep)],
    extra: str = Depends(router_dep),
):
    return {"id": item_id, "token": token, "extra": extra}


app.include_router(router, prefix="/v1", dependencies=[Depends(include_dep)], tags=["ignored"])
