from fastapi import APIRouter

from ai.error import AIServiceError
from ai.pipeline import parse_and_validate
from api.errors import AIUpstreamError
from api.schemas import ParseIn, ParseOut

router = APIRouter(prefix='/api/v1', tags=['ai'])


@router.post('/parse', response_model=ParseOut)
def parse(body: ParseIn):
    try:
        return parse_and_validate(body.text)
    except AIServiceError as e:
        raise AIUpstreamError('AI 解析服务不可用', [{'raw': str(e)}]) from e
