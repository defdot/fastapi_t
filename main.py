"""FastAPI 应用入口"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging import get_logger, setup_logging
from app.routers import auth, items, users
from app.schemas.schemas import ErrorResponse

logger = get_logger(__name__)

# ---------- lifespan：应用启动/关闭时执行 ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # 启动时：自动建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("%s started — DB tables created", settings.APP_NAME)
    yield
    # 关闭时：清理资源
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    description="FastAPI Demo — 用户认证与 CRUD 示例项目",
    swagger_ui_parameters={"persistAuthorization": True},
)

# ---------- 中间件 ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 生产环境请限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """记录请求处理耗时"""
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    response.headers["X-Process-Time"] = str(elapsed)
    logger.info(
        "%s %s -> %d (%.3fs)",
        request.method, request.url.path, response.status_code, elapsed,
    )
    return response


# ---------- 统一错误处理 ----------
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


# ---------- 注册路由 ----------
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(items.router)


# ---------- 健康检查 ----------
@app.get("/health", tags=["系统"])
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# 生产环境启动方式：
#   gunicorn -c gunicorn.conf.py main:app
