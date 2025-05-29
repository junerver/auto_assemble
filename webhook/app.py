"""
Description:
Author: 侯文君
Date: 2025-05-15 16:32:58
LastEditors: 侯文君
LastEditTime: 2025-05-15 16:54:26
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webhook.config import setup_logging
from webhook.controllers import (
    auth_controller,
    events_controller,
    fork_task_controller,
    metadata_controller,
    project_controller,
    task_controller,
    third_party_controller,
    webhook_controller,
    patch_controller,
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
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

logger.info(f"模板目录路径: {TEMPLATES_DIR}")
logger.info(f"静态文件目录路径: {STATIC_DIR}")

# 验证目录是否存在
if not TEMPLATES_DIR.exists():
    raise RuntimeError(f"模板目录不存在: {TEMPLATES_DIR}")
if not STATIC_DIR.exists():
    raise RuntimeError(f"静态文件目录不存在: {STATIC_DIR}")

# 配置静态文件服务
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 添加数据库、log中间件
app.add_middleware(DBSessionMiddleware)  # type: ignore
# app.add_middleware(RequestLoggingMiddleware)

# 引入路由
app.include_router(auth_controller.router)
app.include_router(events_controller.router)
app.include_router(fork_task_controller.router)
app.include_router(metadata_controller.router)
app.include_router(project_controller.router)
app.include_router(task_controller.router)
app.include_router(third_party_controller.router)
app.include_router(webhook_controller.router)
app.include_router(patch_controller.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"渲染模板时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"模板渲染失败: {str(e)}")


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}
