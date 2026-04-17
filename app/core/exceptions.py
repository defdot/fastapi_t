"""统一错误处理"""

import json

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.schemas.schemas import ErrorResponse

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """拦截 HTTPException（如 401/403/404 等）"""
        logger.warning("%s %s -> %d: %s", request.method, request.url.path, exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(code=exc.status_code, msg=str(exc.detail)).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """拦截请求参数校验错误（422）"""
        errors = exc.errors()
        detail = "; ".join(f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}" for e in errors)
        logger.warning("%s %s -> 422: %s", request.method, request.url.path, detail)
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(code=422, msg="参数校验失败", detail=detail).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """拦截未预期的服务端异常（500）"""
        logger.error("%s %s -> 500: %s", request.method, request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(code=500, msg="服务器内部错误").model_dump(),
        )
