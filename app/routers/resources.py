from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from seed.load import EXERCISES


router = APIRouter(prefix="/resources", tags=["Practice resources"], dependencies=[Depends(get_current_user)])


@router.get("/exercises")
def exercises():
    return {"source": "curated_examples", "exercises": EXERCISES}
