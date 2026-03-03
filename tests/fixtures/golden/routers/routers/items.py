from lilya.dependencies import Provide, Provides
from lilya.routing import Router as APIRouter

def dep_router() -> str:
    return 'router'

def dep_extra() -> str:
    return 'extra'

def dep_item() -> str:
    return 'item'
router = APIRouter()

@router.get('/items', dependencies={'_dep_extra': Provide(dep_extra), '_dep_router': Provide(dep_router), 'dep': Provide(dep_item)})
async def list_items(dep: str=Provides(), *, _dep_router=Provides(), _dep_extra=Provides()):
    return {'dep': dep}
