from lilya.apps import Lilya as FastAPI
app = FastAPI()

@app.get('/ping')
async def ping():
    return {'ping': 'pong'}
