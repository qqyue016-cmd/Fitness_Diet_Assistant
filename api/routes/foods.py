from fastapi import APIRouter, Query
from api.schemas import FoodOut
from api.errors import FoodNotFound,InvalidParam
import db

router = APIRouter(prefix='/api/v1', tags=['foods'])

@router.get('/foods', response_model=FoodOut)
def get_foods(name: str = Query(..., min_length=1)):
    food = db.query_food(name)
    if food is None:
        raise FoodNotFound(f'食物不存在：{name}')
    return food

@router.get('/foods/search', response_model=list[FoodOut])
def search(keyword: str = Query(..., min_length=1, max_length=20),
           limit: int = Query(10, ge=1, le=50)):
    kw = keyword.strip()
    if not kw:
        raise InvalidParam('keyword 不能为空白')
    return db.search_foods(kw)[:limit]
