from starlette.applications import Starlette
from starlette.routing import Mount, Route


async def homepage(request):
    return None


async def users(request):
    return None


api = Starlette(routes=[Route("/users", users)])
routes = [Route("", homepage), Mount("/api", app=api)]
app = Starlette(debug=True, routes=routes)
app.mount("", app=api)
app.add_route("", route=homepage, methods=["GET"])
