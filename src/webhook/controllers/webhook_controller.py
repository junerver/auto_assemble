import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse

from common.err_code import format_error
from webhook.extensions.db import get_db, get_db_conn
from webhook.models.task import Task, TaskStatus
from webhook.config import API_TEST, TASK_TIMEOUT, MAX_RETRIES
from webhook.services.task_service import TaskService
from webhook.services.webhook_request_service import WebhookRequestService
from webhook.types import GitLabPushEventReq
from webhook.utils.notifications import show_build_toast, show_toast
from webhook.utils.task_manager import TaskManager, TaskType

# 添加调试日志
logging.info("正在注册webhook路由...")

router = APIRouter(tags=["webhook"])


def build_task_worker(task: Task):
    """
    执行构建任务
    这里由于通过Flask管理的数据库上下文给、app_context，所以直接将task传递到外部时将
    无法正确的更新数据，必须通过下面的方式才能正确执行
    """
    db = get_db_conn()
    try:
        task.started_at = datetime.now()
        task.status = TaskStatus.RUNNING
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
            cwd=Path(__file__).resolve().parent.parent,
            encoding="utf-8",
            env=os.environ.copy(),  # 传递当前环境变量
        )

        # 注册进程到 TaskManager
        TaskManager.register_process(task.id, process)

        def cleanup():
            _db = get_db_conn()
            current_task = None  # 初始化 current_task
            try:
                process.wait(timeout=TASK_TIMEOUT)
                # 重新查表检查任务是否被手动停止，任务有可能被服务器前端手动停止
                current_task = Task.get_by_id(task.id, _db)  # 这里获取到的是正确的任务对象
                logging.info(f"当前任务: {current_task}")
                if current_task and TaskStatus(current_task.status) == TaskStatus.STOPPED:
                    show_build_toast(task, False)  # 这里使用传入的task，可能需要考虑是否改为current_task
                    return

                # 对 current_task 进行状态和时间更新
                current_task.completed_at = datetime.now()
                current_task.status = TaskStatus.COMPLETED if process.returncode == 0 else TaskStatus.FAILED
                show_build_toast(current_task, process.returncode == 0)  # 建议改为current_task
                if process.returncode == 0:
                    current_task.error = None
                else:
                    current_task.error = format_error(process.returncode)
                    if current_task.retries < MAX_RETRIES:
                        current_task.retries += 1
                        current_task.priority += 1
                        TaskManager.add_task_to_queue(current_task, TaskType.BUILD)
            except subprocess.TimeoutExpired:
                # 如果是超时，也需要更新 current_task
                if current_task:  # 确保 current_task 已经被获取
                    process.kill()
                    current_task.status = TaskStatus.TIMEOUT
                    current_task.error = format_error(10002)
                    current_task.completed_at = datetime.now()
                    show_build_toast(current_task, False)
                else:
                    logging.error("Timeout occurred but current_task was not retrieved.")
                    # 针对未获取到 current_task 的情况进行处理，例如使用传入的 task
                    process.kill()
                    task.status = TaskStatus.TIMEOUT
                    task.error = format_error(10002)
                    task.completed_at = datetime.now()
                    show_build_toast(task, False)

            except Exception as _e:
                logging.error(f"执行 cleanup 时出错: {_e}", exc_info=True)
                # 如果出错，也尝试更新 current_task
                if current_task:
                    current_task.status = TaskStatus.FAILED  # 或者其他适当的状态
                    current_task.error = str(_e)
                    current_task.completed_at = datetime.now()
                    show_build_toast(current_task, False)
                else:
                    task.status = TaskStatus.FAILED  # 或者其他适当的状态
                    task.error = str(_e)
                    task.completed_at = datetime.now()
                    show_build_toast(task, False)

            finally:
                # 从 TaskManager 注销进程
                TaskManager.unregister_process(task.id)  # 这里使用task.id是没问题的

                # 使用最新的任务对象进行保存
                if current_task:
                    current_task.save(_db)
                else:
                    # 如果因为某种原因 current_task 没有被赋值，则使用传入的 task
                    task.save(_db)

                # 释放任务锁并获取下一个任务
                TaskManager.exec_next_task()
                _db.close()

        Thread(target=cleanup, daemon=True).start()
    except Exception as e:
        logging.error(f"执行 execute_task 时出错: {e}", exc_info=True)
        # 确保在发生异常时释放锁
        TaskManager.release_task_lock()
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
async def webhook(event: GitLabPushEventReq, request: Request, db=Depends(get_db)):
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

        # 保存webhook请求记录，任务创建成功则保存请求记录
        if not request.headers.get("X-Webhook-Request-Cache") and status_code == 200:
            logging.info("保存webhook请求记录")
            WebhookRequestService.save_webhook_requests(tasks, event, dict(request.headers), db=db)

        # 处理缓存请求
        if request.headers.get("X-Webhook-Request-Cache") and len(tasks) > 0:
            for task in tasks:
                logging.info(f"处理{task.id}缓存请求，replay计数+1")
                WebhookRequestService.update_replay_count(task.id, db=db)

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
    Thread(target=build_task_worker, args=(first_task,), daemon=True).start()

    # 如果有多个任务，将剩余任务加入队列
    if len(tasks) > 1:
        for task in tasks[1:]:
            TaskManager.add_task_to_queue(task, TaskType.BUILD)

    return {"message": "Build started successfully", "task": first_task.to_dict()}
