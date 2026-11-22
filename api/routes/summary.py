from fastapi import APIRouter

import service
from api.schemas import DailySummaryIn, DailySummaryOut

router = APIRouter(prefix='/api/v1', tags=['summary'])


@router.post('/summary', response_model=DailySummaryOut)
def daily_summary(body: DailySummaryIn):
    return service.build_daily_report(body.date.isoformat(), body.target.model_dump())
