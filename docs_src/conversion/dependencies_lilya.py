from lilya.apps import Lilya as FastAPI
from lilya.dependencies import Provide, Provides


def global_dep() -> str:
    return "global"


app = FastAPI(dependencies={"_global_dep": Provide(global_dep)})


@app.get(
    "/items",
    dependencies={"_global_dep": Provide(global_dep), "user": Provide(global_dep), "value": Provide(global_dep)},
)
async def items(user: str = Provides(), value: int = 1, *, _global_dep=Provides()):
    return {"user": user, "value": value}
