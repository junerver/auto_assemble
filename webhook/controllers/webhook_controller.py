import logging
import os
import subprocess
from datetime import datetime
from threading import Thread

from flask import jsonify, request, current_app

from common.err_code import format_error
from webhook.models.task import Task
from . import webhook_bp
from ..config import TASK_TIMEOUT, MAX_RETRIES
from ..services.task_service import TaskService
from ..services.webhook_request_service import WebhookRequestService
from ..utils.notifications import show_build_toast
from ..utils.task_lock import (
    acquire_task_lock,
    release_task_lock,
    add_task_to_queue,
    get_queue_size,
    TaskType,
)

# 添加调试日志
logging.info("正在注册webhook路由...")


def execute_task(task: Task, app):
    """
    执行构建任务
    这里由于通过Flask管理的数据库上下文给、app_context，所以直接将task传递到外部时将
    无法正确的更新数据，必须通过下面的方式才能正确执行
    """
    with app.app_context():
        task.started_at = datetime.now()
        task.status = "running"
        task.save()

        process = subprocess.Popen(
            ["auto-assemble", "--fn", "1", "--task", task.id],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            encoding="utf-8",
            env=os.environ.copy(),  # 传递当前环境变量
        )

        def cleanup():
            with app.app_context():
                try:
                    process.wait(timeout=TASK_TIMEOUT)
                    if process.returncode == 0:
                        task.status = "completed"
                        task.completed_at = datetime.now()
                        task.error = None
                        show_build_toast(task, True)
                        # 删除成功的webhook请求记录
                        # WebhookRequestService.delete_webhook_request(task.id)
                    else:
                        task.status = "failed"
                        # 使用错误码映射格式化错误信息
                        task.error = format_error(process.returncode)
                        task.completed_at = datetime.now()
                        show_build_toast(task, False)
                        if task.retries < MAX_RETRIES:
                            task.retries += 1
                            task.priority += 1
                            add_task_to_queue(task, TaskType.BUILD)
                except subprocess.TimeoutExpired:
                    process.kill()
                    task.status = "failed"
                    task.error = format_error(10002)  # 使用超时错误码
                    task.completed_at = datetime.now()
                    show_build_toast(task, False)
                finally:
                    task.save()
                    # 释放任务锁并获取下一个任务
                    next_task_info = release_task_lock()
                    if next_task_info:
                        next_task_type, next_task = next_task_info
                        if next_task_type == TaskType.BUILD:
                            Thread(target=execute_task, args=(next_task, app), daemon=True).start()
                        else:
                            from ..controllers.fork_task_controller import fork_task_worker

                            Thread(
                                target=fork_task_worker, args=(next_task, app), daemon=True
                            ).start()

        Thread(target=cleanup, daemon=True).start()


@webhook_bp.route("/webhook", methods=["POST"])
def webhook():
    """处理Gitlab的webhook请求"""
    logging.info("收到webhook请求")
    try:
        data = request.get_json()
        if not data:
            logging.warning("收到空的webhook请求")
            return jsonify({"error": "No JSON data received"}), 400

        event_type = request.headers.get("X-Gitlab-Event")
        if event_type != "Push Hook":
            logging.info(f"忽略非push事件: {event_type}")
            return jsonify({"message": f"Ignored non-push event: {event_type}"}), 200

        # 处理webhook请求
        tasks, message, status_code = TaskService.handle_webhook_request(data)

        if tasks is None:
            # 没有有效的构建任务
            return jsonify({"message": message}), status_code

        if not request.headers.get("X-Webhook-Request-Cache"):
            # 保存webhook请求记录
            WebhookRequestService.save_webhook_requests(tasks, data, dict(request.headers))

        if len(tasks) == 1:
            # 单条任务
            task = tasks[0]
            if request.headers.get("X-Webhook-Request-Cache"):
                # 如果请求头中包含X-Webhook-Request-Cache，则表示这是一个缓存的请求
                # 记录缓存请求 replay_count+1
                WebhookRequestService.update_replay_count(task.id)

            # 是否有正在执行的任务
            if not acquire_task_lock(TaskType.BUILD):
                # 将任务加入队列
                logging.info("无法获取任务锁，将任务加入队列")
                add_task_to_queue(task, TaskType.BUILD)
                return (
                    jsonify(
                        {
                            "message": "Task added to queue",
                            "task": task.to_dict(),
                            "position": get_queue_size(TaskType.BUILD),
                        }
                    ),
                    202,
                )
            else:
                # 直接执行构建
                Thread(
                    target=execute_task,
                    args=(task, current_app._get_current_object()),
                    daemon=True,
                ).start()
                return (
                    jsonify({"message": "Build started successfully", "task": task.to_dict()}),
                    200,
                )
        else:
            # 多条任务 需要将任务加入队列
            if not acquire_task_lock(TaskType.BUILD):
                # 将所有任务加入队列
                for task in tasks:
                    add_task_to_queue(task, TaskType.BUILD)
                return (
                    jsonify(
                        {
                            "message": "Tasks added to queue",
                            "tasks": [task.to_dict() for task in tasks],
                        }
                    ),
                    200,
                )
            else:
                # 构建第一个任务，其他任务加入队列
                task = tasks[0]
                Thread(
                    target=execute_task,
                    args=(task, current_app._get_current_object()),
                    daemon=True,
                ).start()
                for task in tasks[1:]:
                    add_task_to_queue(task, TaskType.BUILD)
                return (
                    jsonify({"message": "Build started successfully", "task": task.to_dict()}),
                    200,
                )
    except Exception as e:
        logging.error(f"处理webhook请求时发生错误: {str(e)}")
        return jsonify({"error": str(e)}), 500
