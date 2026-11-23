import datetime
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ai.agent import chat_stream
from api.schemas import ChatIn

router = APIRouter(prefix='/api/v1', tags=['ai'])


@router.post('/chat')
def chat(body: ChatIn):
    messages = [m.model_dump() for m in body.messages]
    target = body.target.model_dump()
    today = datetime.date.today().isoformat()

    def sse():
        try:
            for ev in chat_stream(messages, target, today, body.goal):
                yield f'data: {json.dumps(ev, ensure_ascii=False)}\n\n'
        except Exception as e:
            err = {'type': 'error', 'code': 'AI_UPSTREAM_ERROR', 'message': str(e)}
            yield f'data: {json.dumps(err, ensure_ascii=False)}\n\n'
            return
        # done 在 try 外：出错时不发，客户端才能区分「说完」和「断了」
        yield f'data: {json.dumps({"type": "done"})}\n\n'

    return StreamingResponse(
        sse(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
