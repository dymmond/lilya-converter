from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])


@app.middleware("http")
async def timing(request, call_next):
    response = await call_next(request)
    return response


@app.get("/ok")
async def ok():
    return {"ok": True}
