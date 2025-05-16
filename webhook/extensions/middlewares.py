"""
Description:
Author: 侯文君
Date: 2025-05-15 17:02:29
LastEditors: 侯文君
LastEditTime: 2025-05-15 17:02:35
"""

# middlewares.py
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from webhook.extensions.db import get_db_conn


class DBSessionMiddleware(BaseHTTPMiddleware):
    """数据库会话中间件

    Args:
        BaseHTTPMiddleware (_type_): _description_
    """

    async def dispatch(self, request: Request, call_next):
        request.state.db = get_db_conn()
        try:
            response = await call_next(request)
        finally:
            request.state.db.close()
        return response


logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """服务器日志中间件

    Args:
        BaseHTTPMiddleware (_type_): _description_
    """

    async def dispatch(self, request: Request, call_next):
        logger.info(f"{request.client.host} - - [{request.method}] {request.url.path}")
        response = await call_next(request)
        return response
