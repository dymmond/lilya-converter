from fastapi import APIRouter, FastAPI
from fastapi.responses import ORJSONResponse, PlainTextResponse

app = FastAPI(openapi_url=None)
router = APIRouter()


@router.api_route(
    "/payload",
    methods=["PATCH"],
    response_class=ORJSONResponse,
    response_model=dict,
    responses={404: {"description": "missing"}},
    status_code=201,
)
async def payload():
    return {"value": 1}


@router.trace("/trace", include_in_schema=False)
async def trace_route():
    return PlainTextResponse("trace")


app.include_router(router)
