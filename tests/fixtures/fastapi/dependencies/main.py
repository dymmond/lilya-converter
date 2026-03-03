from typing import Annotated

from fastapi import Depends, FastAPI


def global_dep() -> str:
    return "global"


def router_dep() -> str:
    return "router"


app = FastAPI(dependencies=[Depends(global_dep)])


def nested_dep(token: str = Depends(global_dep)) -> str:
    return token


@app.get("/items", dependencies=[Depends(router_dep)])
async def items(
    user: str = Depends(global_dep),
    value: Annotated[int, Depends(global_dep)] = 1,
):
    return {"user": user, "value": value}
