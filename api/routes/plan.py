from fastapi import APIRouter

import service
from api.schemas import PlanOut, ProfileIn

router = APIRouter(prefix='/api/v1', tags=['plan'])


@router.post('/plan', response_model=PlanOut)
def create_plan(body: ProfileIn):
    return service.build_plan(
        gender=body.gender,
        weight_kg=body.weight_kg,
        height_cm=body.height_cm,
        age=body.age,
        activity_level=body.activity_level,
        goal=body.goal,
    )
