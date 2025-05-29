# webhook/controllers/fork_task_controller.py

import logging
import os
import subprocess
from threading import Thread
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import JSONResponse

from webhook.config import API_TEST, TASK_TIMEOUT
from webhook.extensions.db import get_db
from webhook.models.fork_task import ForkTask
from webhook.services.fork_task_service import ForkTaskService
from webhook.types import (
    ForkTaskReq,
    ForkTaskResp,
    ForkTaskDetailResp,
)
from webhook.utils.notifications import show_toast
from webhook.utils.task_lock import (
    acquire_task_lock,
    release_task_lock,
    add_task_to_queue,
    get_queue_size,
    TaskType,
)

router = APIRouter(prefix="/api/fork_task", tags=["fork_task"])


def fork_task_worker(forked_task: ForkTask):
    """
    派生任务处理函数
    """
    show_toast(
        "📜开始创建派生任务",
        f"操作人：{forked_task.operator}\n源任务: {forked_task.source_task_id}\n源分支: {forked_task.source_branch}\n目标分支: {forked_task.target_branch}\n目标版本名: {forked_task.target_version_name}\n目标版本号: {forked_task.target_version_code}\n提交信息: {forked_task.commit_message}",
    )
    if API_TEST:
        # API 测试模式，不执行任务，直接释放锁，退出执行
        release_task_lock()
        return

    process = subprocess.Popen(
        ["fork-task", "--fork", forked_task.id],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        encoding="utf-8",
        env=os.environ.copy(),
    )

    def cleanup():
        try:
            process.wait(timeout=TASK_TIMEOUT)
            if process.returncode == 0:
                show_toast("派生任务创建成功", "")
            else:
                show_toast("派生任务创建失败", f"错误码：{process.returncode}")
        except subprocess.TimeoutExpired:
            process.kill()
        finally:
            next_task_info = release_task_lock()
            if next_task_info:
                next_task_type, next_task = next_task_info
                if next_task_type == TaskType.BUILD:
                    from webhook.controllers.webhook_controller import execute_task

                    Thread(target=execute_task, args=(next_task,), daemon=True).start()
                else:
                    Thread(target=fork_task_worker, args=(next_task,), daemon=True).start()

    Thread(target=cleanup, daemon=True).start()


@router.post("", response_model=ForkTaskResp)
async def fork_task(req: ForkTaskReq, db=Depends(get_db)):
    """派生任务"""
    label = f"#{req.target_branch}_req#" if req.target_branch != "master" else "#dev_req#"
    commit_message = f"{label} {req.commit_message}\n\n源任务分支: {req.source_branch}\n源任务ID: {req.source_task_id}"

    task = ForkTaskService.create_fork_task(
        req.source_task_id,
        req.source_branch,
        req.target_branch,
        req.target_version_name,
        req.target_version_code,
        commit_message,
        req.operator,
        db=db,
    )

    if not acquire_task_lock(TaskType.FORK):
        logging.info("无法获取任务锁，将任务加入队列")
        add_task_to_queue(task, TaskType.FORK)
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Task added to queue",
                "fork_task": task.to_dict(),
                "position": get_queue_size(TaskType.FORK),
            },
        )

    Thread(target=fork_task_worker, args=(task,), daemon=True).start()
    logging.info(f"派生任务 {task.id} 开始执行")

    return {"message": "派生任务创建成功", "fork_task": task.to_dict()}


@router.get("/{fork_task_id}", response_model=ForkTaskDetailResp)
async def get_fork_task(
    fork_task_id: Annotated[str, Path(..., title="fork_task_id", description="需要查询的派生任务id")],
    db=Depends(get_db),
):
    """获取派生任务"""
    task = ForkTaskService.get_fork_task(fork_task_id, db=db)
    return {"fork_task": task.to_dict()}
