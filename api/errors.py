from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

class ErrorBody(BaseModel):
    code: str
    message: str
    detail: list | None = None


class ErrorOut(BaseModel):
    error: ErrorBody


class ApiError(Exception):
    status_code = 500
    code = 'INTERNAL_ERROR'

    def __init__(self, message: str, detail: list | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class FoodNotFound(ApiError):
    status_code = 404
    code = 'FOOD_NOT_FOUND'


class IntakeNotFound(ApiError):
    status_code = 404
    code = 'INTAKE_NOT_FOUND'


class InvalidParam(ApiError):
    status_code = 422
    code = 'VALIDATION_ERROR'


class AIUpstreamError(ApiError):
    status_code = 502
    code = 'AI_UPSTREAM_ERROR'


def _response(status_code: int, code: str, message: str, detail: list | None = None):
    body = ErrorOut(error=ErrorBody(code=code, message=message, detail=detail))
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body.model_dump()))


def register_error_handlers(app: FastAPI) -> None:
    # API错误处理
    @app.exception_handler(ApiError)
    def _handler_api_error(request: Request, exc: ApiError):
        return _response(exc.status_code, exc.code, exc.message, exc.detail)

    # 请求验证错误处理
    @app.exception_handler(RequestValidationError)
    def _handler_request_error(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {'loc': (), 'msg': '请求参数非法'}
        loc = first.get('loc') or ()
        field = loc[-1] if loc and isinstance(loc[-1], str) else 'body'
        return _response(422, 'VALIDATION_ERROR', f'{field}：{first["msg"]}', errors)

    # 运行时错误处理
    @app.exception_handler(RuntimeError)
    def _handler_runtime_error(request: Request, exc: RuntimeError):
        return _response(500, 'DATABASE_ERROR', '数据访问失败', [{'raw': str(exc)}])

    # 通用错误处理
    @app.exception_handler(Exception)
    def _handler_unhandled(request: Request, exc: Exception):
        return _response(500, 'INTERNAL_ERROR', '服务器错误')
