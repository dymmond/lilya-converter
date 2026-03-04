from lilya.apps import Lilya as Litestar
from lilya.routing import Router, Path, Include

async def health() -> dict[str, bool]:
    return {'ok': True}

async def list_items() -> dict[str, list[str]]:
    return {'items': []}
api = Router(routes=[Path('/', list_items, methods=['GET'])])
app = Litestar(routes=[Path('/health', health, methods=['GET']), Include(path='/api', app=api)])
