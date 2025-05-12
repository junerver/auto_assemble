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
from ..utils.notifications import show_build_toast, show_toast
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
        show_toast(
            "📜开始执行构建",
            f"🗃️项目: {task.prod_name}\n🏗️任务: {task.task_name}\n🧑‍💻作者: {task.author}\n📝标题: {task.commit_title}",
        )
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
            return jsonify({"message": message}), status_code

        # 保存webhook请求记录
        if not request.headers.get("X-Webhook-Request-Cache"):
            WebhookRequestService.save_webhook_requests(tasks, data, dict(request.headers))

        # 处理缓存请求
        if request.headers.get("X-Webhook-Request-Cache") and len(tasks) == 1:
            WebhookRequestService.update_replay_count(tasks[0].id)

        # 处理任务执行
        return handle_tasks_execution(tasks)

    except Exception as e:
        logging.error(f"处理webhook请求时发生错误: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def handle_tasks_execution(tasks):
    """处理任务执行逻辑"""
    if not tasks:
        return jsonify({"message": "No tasks to execute"}), 200

    # 尝试获取任务锁
    if not acquire_task_lock(TaskType.BUILD):
        # 将所有任务加入队列
        for task in tasks:
            add_task_to_queue(task, TaskType.BUILD)
        return (
            jsonify(
                {
                    "message": "Tasks added to queue",
                    "tasks": [task.to_dict() for task in tasks],
                    "position": get_queue_size(TaskType.BUILD),
                }
            ),
            202,
        )

    # 执行第一个任务
    first_task = tasks[0]
    Thread(
        target=execute_task, args=(first_task, current_app._get_current_object()), daemon=True
    ).start()

    # 如果有多个任务，将剩余任务加入队列
    if len(tasks) > 1:
        for task in tasks[1:]:
            add_task_to_queue(task, TaskType.BUILD)

    return jsonify({"message": "Build started successfully", "task": first_task.to_dict()}), 200
