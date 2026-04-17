"""中间件"""

import json
import time
import traceback

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.schemas.schemas import ErrorResponse

logger = get_logger(__name__)

# 敏感参数名，记录日志时脱敏
_SENSITIVE_KEYS = {"password", "token", "secret", "authorization"}


def _mask_sensitive(params: dict) -> dict:
    """对敏感参数脱敏"""
    return {k: "***" if k.lower() in _SENSITIVE_KEYS else v for k, v in params.items()}


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP（支持反向代理）"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


async def _build_params(request: Request) -> dict:
    """合并所有请求参数：query + path + body"""
    params: dict = {}

    if request.query_params:
        params.update(dict(request.query_params))

    if hasattr(request, "path_params") and request.path_params:
        params.update(dict(request.path_params))

    raw = await request.body()
    print("raw body:", raw)
    if raw:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = json.loads(raw)
            params.update(body)
        elif "application/x-www-form-urlencoded" in content_type:
            from urllib.parse import parse_qs
            form = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(raw.decode()).items()}
            params.update(form)

    params = _mask_sensitive(params)
    return params


async def access_log_middleware(request: Request, call_next) -> Response:
    """访问日志中间件：记录来源 IP、URL path、请求参数、状态、耗时、错误信息、异常堆栈"""
    start = time.time()
    client_ip = _get_client_ip(request)
    path = request.url.path

    # 合并 query + path_params + body 参数，并脱敏敏感信息
    params = _build_params(request)
    response = await call_next(request)
    
    elapsed = time.time() - start
    status_code = response.status_code
    response.headers["X-Process-Time"] = f"{elapsed:.3f}"

    # 错误响应：读取 body 获取错误信息，并统一格式化
    if status_code >= 400 and "application/json" in response.headers.get("content-type", ""):
        try:
            resp_body = b""
            async for chunk in response.body_iterator:
                resp_body += chunk
            raw = json.loads(resp_body)

            if isinstance(raw, dict) and "code" in raw and "msg" in raw:
                resp = JSONResponse(status_code=status_code, content=raw)
                error_msg = raw.get("msg")
            else:
                error_msg = raw.get("detail", str(raw)) if isinstance(raw, dict) else str(raw)
                resp = JSONResponse(
                    status_code=status_code,
                    content=ErrorResponse(code=status_code, msg=error_msg).model_dump(),
                )

            resp.headers["X-Process-Time"] = f"{elapsed:.3f}"
            log_fn = logger.error if status_code >= 500 else logger.warning
            log_fn(
                "%s %s %s %s -> %d (%.3fs) error=%s",
                client_ip, request.method, path, params_str,
                status_code, elapsed, error_msg,
            )
            return resp
        except Exception:
            pass

    logger.info(
        "%s %s %s %s -> %d (%.3fs)",
        client_ip, request.method, path, params,
        status_code, elapsed,
    )
    return response
