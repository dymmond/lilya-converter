from typing import Annotated

from fastapi import Depends, FastAPI


def global_dep() -> str:
    return "global"


app = FastAPI(dependencies=[Depends(global_dep)])


@app.get("/items")
async def items(
    user: str = Depends(global_dep),
    value: Annotated[int, Depends(global_dep)] = 1,
):
    return {"user": user, "value": value}
