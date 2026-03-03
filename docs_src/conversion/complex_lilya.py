from lilya.apps import Lilya as FastAPI
from lilya.dependencies import Provide, Provides
from lilya.routing import Router as APIRouter
from typing import Annotated


def app_dep() -> str:
    return "app"


def include_dep() -> str:
    return "include"


def router_dep() -> str:
    return "router"


def route_dep() -> str:
    return "route"


app = FastAPI(dependencies={"_app_dep": Provide(app_dep)}, enable_openapi=True)
router = APIRouter()


@router.route(
    "/api/items/{item_id}",
    methods=["GET", "POST"],
    dependencies={
        "_route_dep": Provide(route_dep),
        "_router_dep": Provide(router_dep),
        "token": Provide(route_dep),
        "extra": Provide(router_dep),
    },
)
async def item(
    item_id: int,
    token: str,
    extra: str = Provides(),
    *,
    _router_dep=Provides(),
    _route_dep=Provides(),
):
    return {"id": item_id, "token": token, "extra": extra}


app.include(path="/v1", app=router, dependencies={"_include_dep": Provide(include_dep)})
