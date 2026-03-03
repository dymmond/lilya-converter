from lilya.dependencies import Provide, Provides
from typing import Annotated
from lilya.apps import Lilya as FastAPI
from lilya.exceptions import HTTPException
from lilya.routing import Router as APIRouter
from fastapi import Depends
from lilya.middleware.trustedhost import TrustedHostMiddleware
from lilya.responses import JSONResponse as ORJSONResponse

def app_dep() -> str:
    return 'app'

def include_dep() -> str:
    return 'include'

def router_dep() -> str:
    return 'router'

def route_dep() -> str:
    return 'route'
app = FastAPI(dependencies={'_app_dep': Provide(app_dep)}, enable_openapi=True)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['*'])
router = APIRouter()

def helper(value: str=Depends(app_dep)) -> str:
    return value

@router.route('/api/items/{item_id}', methods=['GET', 'POST'], dependencies={'_route_dep': Provide(route_dep), '_router_dep': Provide(router_dep), 'extra': Provide(router_dep), 'token': Provide(route_dep)})
async def item(item_id: int, token: str, extra: str=Provides(), *, _router_dep=Provides(), _route_dep=Provides()):
    if item_id < 0:
        raise HTTPException(status_code=404)
    return {'id': item_id, 'token': token, 'extra': extra}

@router.websocket('/api/ws', dependencies={'_router_dep': Provide(router_dep)})
async def ws(socket, *, _router_dep=Provides()):
    await socket.accept()

async def handle_value_error(request, exc):
    return ORJSONResponse({'detail': 'bad'}, status_code=400)
app.include(path='/v1', app=router, include_in_schema=False, dependencies={'_include_dep': Provide(include_dep)})
app.add_exception_handler(ValueError, handle_value_error)
