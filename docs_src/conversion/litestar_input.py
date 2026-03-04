from litestar import Litestar, Router, get


@get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@get("")
async def list_items() -> dict[str, list[str]]:
    return {"items": []}


api = Router(path="/api", route_handlers=[list_items])
app = Litestar(route_handlers=[health, api])
