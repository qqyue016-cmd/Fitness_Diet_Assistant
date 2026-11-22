from fastapi import APIRouter, Depends ,Path

import db
from api.deps import get_date
from api.errors import FoodNotFound, IntakeNotFound
from api.schemas import IntakeCreate, IntakeCreateOut, IntakeRecordOut

router = APIRouter(prefix='/api/v1', tags=['intake'])


@router.post('/intake', response_model=IntakeCreateOut, status_code=201)
def create_intake(body: IntakeCreate):
    if db.query_food(body.food_name) is None:
        raise FoodNotFound(f'该食物不存在:{body.food_name}')
    intake_id = db.add_intake(body.date.isoformat(), body.food_name, body.grams)
    return {'id': intake_id, 'date': body.date, 'food_name': body.food_name, 'grams': body.grams}


@router.get('/intake', response_model=list[IntakeRecordOut])
def list_intake(date: str = Depends(get_date)):
    return db.list_intake_by_date(date)


@router.delete('/intake/{intake_id}', status_code=204)
def delete_intake(intake_id: int = Path(..., ge=1)):
    if db.delete_intake(intake_id) == 0:
        raise IntakeNotFound(f'该摄入记录不存在:{intake_id}')
    return None
