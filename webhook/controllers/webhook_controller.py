import logging
import os
import subprocess
from datetime import datetime
from queue import PriorityQueue
from threading import Thread, Lock

from flask import jsonify, request

from auto_assemble.err_code import format_error
from . import webhook_bp
from ..config import TASK_TIMEOUT, MAX_RETRIES
from ..services.task_service import BuildTask, save_task, get_running_task
from ..utils.notifications import show_build_toast, show_toast
from ..utils.validators import is_valid_build_task, parse_build_task

# 任务队列（使用优先级队列）
task_queue = PriorityQueue()
# 队列锁
queue_lock = Lock()

# 添加调试日志
logging.info("正在注册webhook路由...")


def execute_task(task: BuildTask):
    """执行构建任务"""
    task.started_at = datetime.now()
    task.status = "running"
    save_task(task)

    process = subprocess.Popen(
        ["auto-assemble", "--fn", "1", "--task", task.task_id],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        encoding="utf-8",
        env=os.environ.copy(),  # 传递当前环境变量
    )

    def cleanup():
        try:
            process.wait(timeout=TASK_TIMEOUT)
            if process.returncode == 0:
                task.status = "completed"
                task.completed_at = datetime.now()
                task.error = None
                show_build_toast(task, True)
            else:
                task.status = "failed"
                # 使用错误码映射格式化错误信息
                task.error = format_error(process.returncode)
                task.completed_at = datetime.now()
                show_build_toast(task, False)
                if task.retries < MAX_RETRIES:
                    task.retries += 1
                    task.priority += 1
                    with queue_lock:
                        task_queue.put(task)
        except subprocess.TimeoutExpired:
            process.kill()
            task.status = "failed"
            task.error = format_error(10002)  # 使用超时错误码
            task.completed_at = datetime.now()
            show_build_toast(task, False)
        finally:
            save_task(task)
            # 检查队列中是否有下一个任务
            with queue_lock:
                if not task_queue.empty():
                    next_task = task_queue.get()
                    Thread(target=execute_task, args=(next_task,), daemon=True).start()

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

        commits = data.get("commits", [])
        if not commits:
            logging.warning("提交中没有文件变更")
            return jsonify({"message": "No file changes in commit"}), 200

        added_files = commits[0].get("added", [])
        if not is_valid_build_task(added_files):
            logging.info("不是有效的构建任务")
            return jsonify({"message": "Not a valid build task"}), 200

        # 获取提交信息，从添加文件中获取项目名和任务名
        commit_info = commits[0]
        prod_name, task_name = parse_build_task(added_files)

        # 显示收到构建请求的toast提示
        show_toast(
            "📜收到构建请求",
            f"🗃️项目: {prod_name}\n🏗️任务: {task_name}\n🧑‍💻作者: {commit_info.get('author', {}).get('name', '未知')}\n📝标题: {commit_info.get('title', '无标题')}",
        )

        task = BuildTask(prod_name, task_name, commit_info)

        # 检查是否有正在运行的任务
        running_task = get_running_task()
        if running_task:
            logging.info("检测到正在进行的构建，将任务加入队列")
            with queue_lock:
                task_queue.put(task)
                save_task(task)
            return (
                jsonify(
                    {
                        "message": "Task added to queue",
                        "task": task.to_dict(),
                        "position": task_queue.qsize(),
                    }
                ),
                202,
            )
        else:
            # 直接执行构建
            Thread(target=execute_task, args=(task,), daemon=True).start()
            return jsonify({"message": "Build started successfully", "task": task.to_dict()}), 200

    except Exception as e:
        logging.error(f"处理webhook请求时发生错误: {str(e)}")
        return jsonify({"error": str(e)}), 500
