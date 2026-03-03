from fastapi import APIRouter, Depends


def dep_router() -> str:
    return "router"


def dep_extra() -> str:
    return "extra"


def dep_item() -> str:
    return "item"


router = APIRouter(prefix="/items", dependencies=[Depends(dep_router)])


@router.get("/", dependencies=[Depends(dep_extra)], response_model=dict)
async def list_items(dep: str = Depends(dep_item)):
    return {"dep": dep}
