import logging
from typing import Annotated

import requests
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse, FileResponse

from common.gitlab import FileType, download_task_files
from common.types import TaskInfo
from webhook.config import PORT
from webhook.extensions.db import get_db
from webhook.models.task import TaskStatus
from webhook.types import (
    BaseResp,
    QueueDetailResp,
    StatisticsResp,
    StopTaskResp,
    TaskDetailResp,
)
from webhook.services.task_service import TaskService
from webhook.services.webhook_request_service import WebhookRequestService

router = APIRouter(tags=["task"])


@router.get("/task/statistics", response_model=StatisticsResp)
@router.get("/api/task/statistics", response_model=StatisticsResp)
async def get_tasks_statistics(db=Depends(get_db)):
    """获取所有任务的统计情况"""
    tasks = TaskService.get_tasks_statistics(db)
    packer_usage = TaskService.get_packer_usage_statistics(db)
    return {"tasks": tasks, "packer_usage": packer_usage}


@router.get("/queue", response_model=QueueDetailResp)
@router.get("/api/task/queue", response_model=QueueDetailResp)
async def get_queue_status(
    build_mode: str = Query(default="all", description="构建模式"),
    db=Depends(get_db),
):
    """获取队列状态"""
    if build_mode == "all":
        build_mode = None
    queue_status = TaskService.get_queue_status(20, build_mode=build_mode, db=db)

    # 修正返回的数据格式
    formatted_status = {
        "running_task": (format_task_info(queue_status["running_task"]) if queue_status["running_task"] else None),
        "pending_tasks": [format_task_info(task) for task in queue_status["pending_tasks"]],
        "queue_size": queue_status["queue_size"],
        "recent_tasks": [format_task_info(task) for task in queue_status["recent_tasks"]],
    }

    return formatted_status


@router.get("/task/{task_id}", response_model=TaskDetailResp)
@router.get("/api/task/{task_id}", response_model=TaskDetailResp)
async def get_task_info(task_id: Annotated[str, Path(..., description="任务id")], db=Depends(get_db)):
    """获取任务详细信息

    注意，该接口同时被cbr、auto_assemble程序调用，不能轻易修改
    """
    task = TaskService.get_task(task_id, db=db)
    if task:
        return {"task": format_task_info(task.to_dict())}
    raise HTTPException(status_code=404, detail="Task not found")


@router.get("/api/task", response_model=TaskDetailResp)
async def get_task_by_fp(
    res_fp: str = Query(default=None, description="资源包指纹"),
    db=Depends(get_db),
):
    """获取正在运行的任务"""
    task = TaskService.get_task_by_fp(res_fp, db=db)
    if task:
        return {"task": format_task_info(task.to_dict())}
    raise HTTPException(status_code=404, detail="Task not found")


@router.delete("/api/task/{task_id}", response_model=BaseResp)
async def outdated_task(task_id: Annotated[str, Path(..., description="任务id")], db=Depends(get_db)):
    """标记任务为过期"""
    if TaskService.update_task_status(task_id, TaskStatus.OUTDATED, db=db) is not None:
        return {"message": "Task outdated"}
    raise HTTPException(status_code=404, detail="Task not found")


@router.put("/api/task/{task_id}", response_model=BaseResp)
async def update_task(
    task_id: Annotated[str, Path(..., description="任务id")],
    request: Request,
    db=Depends(get_db),
):
    """更新任务接口，通过请求体中指定的键值，更新对应任务的指定字段"""
    data = await request.json()
    if data.get("response_hash"):
        TaskService.update_response_hash(task_id, data.get("response_hash"), db=db)
    if data.get("res_fp"):
        TaskService.update_res_fp(task_id, data.get("res_fp"), db=db)
    return {"message": "Task updated"}


@router.post("/api/task/{task_id}/replay")
async def replay_webhook(task_id: Annotated[str, Path(..., description="任务id")], db=Depends(get_db)):
    """重放webhook请求"""

    # 获取原始请求数据
    request_data, headers, status_code = WebhookRequestService.replay_webhook_request(task_id, db=db)
    if not request_data:
        raise HTTPException(status_code=404, detail="task request don't exists")

    try:
        # 获取webhook接口的URL
        webhook_url = f"http://localhost:{PORT}/webhook"

        # 发送请求到webhook接口
        response = requests.post(webhook_url, json=request_data, headers=headers, timeout=30)

        if response.status_code == 200:
            return {"message": "Webhook请求重放成功", "response": response.json()}
        else:
            return JSONResponse(
                status_code=response.status_code,
                content={
                    "message": "Webhook请求重放失败",
                    "response": response.json(),
                },
            )

    except requests.exceptions.RequestException as e:
        logging.error(f"重放webhook请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/task/{task_id}/stop", response_model=StopTaskResp)
async def stop_task(task_id: Annotated[str, Path(..., description="任务id")], db=Depends(get_db)):
    """停止运行中的任务"""
    logging.info(f"停止任务: {task_id}")
    task, message, status_code = TaskService.stop_task(task_id, db=db)
    if task:
        return JSONResponse(
            status_code=status_code,
            content={"message": message, "task": format_task_info(task.to_dict())},
        )
    return JSONResponse(status_code=status_code, content={"error": message})


@router.get("/api/task/{task_id}/download")
async def download(
    task_id: Annotated[str, Path(..., description="任务id")],
    file_type: FileType = Query(default="apk", description="文件类型"),
    db=Depends(get_db),
):
    """下载任务文件，由服务器首先从gitlab lfs上下载到缓存目录中，然后再传递给前端

    Args:
        task_id: 任务id
        file_type: 下载文件类型
        db:
    """
    task = TaskService.get_task(task_id, db=db)
    if task is None:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    task_info: TaskInfo = TaskInfo.from_dict(format_task_info(task.to_dict()))
    file_path = download_task_files(task_info, file_type)
    if file_path is not None:
        return FileResponse(file_path, filename=file_path.name)
    return JSONResponse(status_code=404, content={"error": "File not found"})


def format_task_info(task_dict):
    """格式化任务信息，确保返回正确的字段名称"""
    if not task_dict:
        return None

    field_mapping = {"prod_name": "project", "task_name": "task"}

    result = task_dict.copy()
    for old_key, new_key in field_mapping.items():
        if old_key in result:
            result[new_key] = result.pop(old_key)

    return result
