import json
import logging
import os
import subprocess
from datetime import datetime
from threading import Thread

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse

from common.err_code import format_error
from webhook.extensions.db import get_db, get_db_conn
from webhook.models.task import Task
from webhook.config import API_TEST, TASK_TIMEOUT, MAX_RETRIES
from webhook.services.task_service import TaskService
from webhook.services.webhook_request_service import WebhookRequestService
from webhook.types import GitLabPushEventModel
from webhook.utils.notifications import show_build_toast, show_toast
from webhook.utils.task_manager import (
    TaskManager,
    TaskType,
)

# 添加调试日志
logging.info("正在注册webhook路由...")

router = APIRouter(tags=["webhook"])


def execute_task(task: Task):
    """
    执行构建任务
    这里由于通过Flask管理的数据库上下文给、app_context，所以直接将task传递到外部时将
    无法正确的更新数据，必须通过下面的方式才能正确执行
    """
    db = get_db_conn()
    try:
        task.started_at = datetime.now()
        task.status = "running"
        task.save(db=db)
        show_toast(
            "📜开始执行构建",
            f"🗃️项目: {task.prod_name}\n🏗️任务: {task.task_name}\n🧑‍💻作者: {task.author}\n📝标题: {task.commit_title}",
        )
        if API_TEST:
            # API 测试模式，不执行任务，直接释放锁，退出执行
            TaskManager.release_task_lock()
            return

        process = subprocess.Popen(
            ["auto-assemble", "--fn", "1", "--task", task.id],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            encoding="utf-8",
            env=os.environ.copy(),  # 传递当前环境变量
        )

        def cleanup():
            _db = get_db_conn()
            try:
                process.wait(timeout=TASK_TIMEOUT)
                task.completed_at = datetime.now()
                task.status = "completed" if process.returncode == 0 else "failed"
                show_build_toast(task, process.returncode == 0)
                if process.returncode == 0:
                    task.error = None
                    # 删除成功的webhook请求记录
                    # WebhookRequestService.delete_webhook_request(task.id)
                else:
                    # 使用错误码映射格式化错误信息
                    task.error = format_error(process.returncode)
                    if task.retries < MAX_RETRIES:
                        task.retries += 1
                        task.priority += 1
                        TaskManager.add_task_to_queue(task, TaskType.BUILD)
            except subprocess.TimeoutExpired:
                process.kill()
                task.status = "failed"
                task.error = format_error(10002)  # 使用超时错误码
                task.completed_at = datetime.now()
                show_build_toast(task, False)
            except Exception as _e:
                logging.error(f"执行 cleanup 时出错: {_e}", exc_info=True)
            finally:
                task.save(_db)
                # 释放任务锁并获取下一个任务
                next_task_info = TaskManager.release_task_lock()
                if next_task_info:
                    next_task_type, next_task = next_task_info
                    if next_task_type == TaskType.BUILD:
                        Thread(target=execute_task, args=(next_task,), daemon=True).start()
                    else:
                        from webhook.controllers.fork_task_controller import fork_task_worker

                        Thread(target=fork_task_worker, args=(next_task,), daemon=True).start()
                _db.close()

        Thread(target=cleanup, daemon=True).start()
    except Exception as e:
        logging.error(f"执行 execute_task 时出错: {e}", exc_info=True)
    finally:
        db.close()


@router.post(
    "/webhook",
    responses={
        200: {"description": "任务创建成功，立即开始执行"},
        201: {"description": "构建任务执行完毕，记录提交产物的信息"},
        202: {"description": "任务创建成功，当前有正在执行的任务，已加入队列"},
        403: {"description": "hook中不包含任何提交内容"},
        404: {"description": "提交信息不是有效的构建任务请求"},
        500: {"description": "处理webhook请求时发生错误"},
    },
)
async def webhook(event: GitLabPushEventModel, request: Request, db=Depends(get_db)):
    """处理Gitlab的webhook请求"""
    logging.info("收到webhook请求")
    try:
        if not event:
            logging.warning("收到空的webhook请求")
            raise HTTPException(status_code=400, detail="No JSON data received")

        event_type = request.headers.get("X-Gitlab-Event")
        if event_type != "Push Hook":
            logging.info(f"忽略非push事件: {event_type}")
            return {"message": f"Ignored non-push event: {event_type}"}

        # 处理webhook请求，提取构建任务
        tasks, message, status_code = TaskService.handle_webhook_request(event, db=db)
        if tasks is None:
            return JSONResponse(content={"message": message}, status_code=status_code)

        logging.info(
            f"过滤后的任务（{len(tasks)}）：\n{json.dumps([task.to_dict() for task in tasks], ensure_ascii=False, indent=2)}"
        )

        # 保存webhook请求记录
        if not request.headers.get("X-Webhook-Request-Cache"):
            WebhookRequestService.save_webhook_requests(tasks, event, dict(request.headers), db=db)

        # 处理缓存请求
        if request.headers.get("X-Webhook-Request-Cache") and len(tasks) == 1:
            WebhookRequestService.update_replay_count(tasks[0].id, db=db)

        # 处理任务执行
        return handle_tasks_execution(tasks)

    except Exception as e:
        logging.error(f"处理webhook请求时发生错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def handle_tasks_execution(tasks: list["Task"]):
    """处理任务执行逻辑"""
    if not tasks:
        return {"message": "No tasks to execute"}

    # 尝试获取任务锁
    if not TaskManager.acquire_task_lock(TaskType.BUILD):
        # 将所有任务加入队列
        for task in tasks:
            TaskManager.add_task_to_queue(task, TaskType.BUILD)
        return JSONResponse(
            content={
                "message": "Tasks added to queue",
                "tasks": [task.to_dict() for task in tasks],
                "position": TaskManager.get_queue_size(TaskType.BUILD),
            },
            status_code=202,
        )

    # 执行第一个任务
    first_task = tasks[0]
    Thread(target=execute_task, args=(first_task,), daemon=True).start()

    # 如果有多个任务，将剩余任务加入队列
    if len(tasks) > 1:
        for task in tasks[1:]:
            TaskManager.add_task_to_queue(task, TaskType.BUILD)

    return {"message": "Build started successfully", "task": first_task.to_dict()}
