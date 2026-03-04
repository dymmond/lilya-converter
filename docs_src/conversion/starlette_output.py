from lilya.apps import Lilya as Starlette
from lilya.routing import Include as Mount, Path as Route


async def homepage(request):
    return None


async def users(request):
    return None


api = Starlette(routes=[Route('/users', users)])
routes = [Route('/', homepage), Mount('/api', app=api)]
app = Starlette(debug=True, routes=routes)
app.include(path='/', app=api)
app.add_route(path='/', handler=homepage, methods=['GET'])
