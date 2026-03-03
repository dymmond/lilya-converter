from lilya.dependencies import Provide, Provides
from typing import Annotated
from lilya.apps import Lilya as FastAPI
from fastapi import Depends

def global_dep() -> str:
    return 'global'

def router_dep() -> str:
    return 'router'
app = FastAPI(dependencies={'_global_dep': Provide(global_dep)})

def nested_dep(token: str=Depends(global_dep)) -> str:
    return token

@app.get('/items', dependencies={'_global_dep': Provide(global_dep), '_router_dep': Provide(router_dep), 'user': Provide(global_dep), 'value': Provide(global_dep)})
async def items(user: str=Provides(), value: int=1, *, _global_dep=Provides(), _router_dep=Provides()):
    return {'user': user, 'value': value}
