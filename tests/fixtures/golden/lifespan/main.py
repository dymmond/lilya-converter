from contextlib import asynccontextmanager
from lilya.apps import Lilya as FastAPI

@asynccontextmanager
async def lifespan(app):
    yield
app = FastAPI(lifespan=lifespan)

@app.on_event('startup')
async def startup_event():
    pass

@app.on_event('shutdown')
async def shutdown_event():
    pass
