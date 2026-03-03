from lilya.apps import Lilya as FastAPI
from lilya.responses import PlainText as PlainTextResponse
from lilya.routing import Router as APIRouter

app = FastAPI(enable_openapi=False)
router = APIRouter()


@router.route("/payload", methods=["PATCH"])
async def payload():
    return {"value": 1}


@router.route("/trace", include_in_schema=False, methods=["TRACE"])
async def trace_route():
    return PlainTextResponse("trace")


app.include(path="", app=router)
