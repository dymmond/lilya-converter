from lilya.apps import Lilya as FastAPI
from routers.items import router as items_router
app = FastAPI()
app.include(path='/v1', app=items_router)
