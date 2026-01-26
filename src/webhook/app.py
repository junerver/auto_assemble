"""
Description:
Author: 侯文君
Date: 2025-05-15 16:32:58
LastEditors: 侯文君
LastEditTime: 2025-05-15 16:54:26
"""

import logging

from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webhook.config import setup_logging

from webhook.controllers import (
    auth_controller,
    events_controller,
    fork_task_controller,
    metadata_controller,
    obfuscate_controller,
    project_controller,
    task_controller,
    third_party_controller,
    webhook_controller,
    patch_controller,
    maintain_controller,
    cbr_controller,
)
from webhook.extensions.middlewares import DBSessionMiddleware
from webhook.models.database import init_db

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 初始化数据库
init_db()
app = FastAPI()

# 使用绝对路径配置模板目录
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

logger.info(f"静态文件目录路径: {STATIC_DIR}")

# 验证目录是否存在
if not STATIC_DIR.exists():
    raise RuntimeError(f"静态文件目录不存在: {STATIC_DIR}")

# 配置静态文件服务
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(STATIC_DIR))

# 添加数据库、log中间件
app.add_middleware(DBSessionMiddleware)  # type: ignore
# app.add_middleware(RequestLoggingMiddleware)

# 遍历 controllers 包下所有模块（动态导入）
# from webhook import controllers
# import importlib
# import pkgutil
# for _, module_name, _ in pkgutil.iter_modules(controllers.__path__):
#     module = importlib.import_module(f"webhook.controllers.{module_name}")
#     if hasattr(module, "router"):
#         # 引入路由
#         app.include_router(module.router)

# 手动导入（可以被 pycharm 识别路由下的端点）
app.include_router(auth_controller.router)
app.include_router(cbr_controller.router)
app.include_router(events_controller.router)
app.include_router(fork_task_controller.router)
app.include_router(maintain_controller.router)
app.include_router(metadata_controller.router)
app.include_router(obfuscate_controller.router)
app.include_router(patch_controller.router)
app.include_router(project_controller.router)
app.include_router(task_controller.router)
app.include_router(third_party_controller.router)
app.include_router(webhook_controller.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.exception(f"渲染模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"模板渲染失败: {str(e)}")


@app.api_route("/health", methods=["HEAD"])
async def health():
    return Response(status_code=200)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )
