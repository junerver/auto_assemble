import logging
import os
import subprocess
from threading import Thread

from flask import Flask, current_app, request, jsonify

from webhook.config import TASK_TIMEOUT
from webhook.models.fork_task import ForkTask
from webhook.services.fork_task_service import ForkTaskService
from webhook.utils.notifications import show_toast
from webhook.utils.task_lock import (
    acquire_task_lock,
    release_task_lock,
    add_task_to_queue,
    get_queue_size,
    TaskType,
)
from . import fork_task_bp


def fork_task_worker(fork_task: ForkTask, app: Flask):
    """
    派生任务处理函数
    """
    with app.app_context():
        show_toast(
            "📜开始创建派生任务",
            f"操作人：{fork_task.operator}\n源任务: {fork_task.source_task_id}\n源分支: {fork_task.source_branch}\n目标分支: {fork_task.target_branch}\n目标版本名: {fork_task.target_version_name}\n目标版本号: {fork_task.target_version_code}\n提交信息: {fork_task.commit_message}",
        )

        process = subprocess.Popen(
            ["fork-task", "--fork", fork_task.id],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            encoding="utf-8",
            env=os.environ.copy(),  # 传递当前环境变量
        )

        def cleanup():
            with app.app_context():
                try:
                    process.wait(timeout=TASK_TIMEOUT)
                    if process.returncode == 0:
                        show_toast("派生任务创建成功")
                    else:
                        show_toast("派生任务创建失败")
                except subprocess.TimeoutExpired:
                    process.kill()
                finally:
                    # 释放任务锁并获取下一个任务
                    next_task_info = release_task_lock()
                    if next_task_info:
                        next_task_type, next_task = next_task_info
                        if next_task_type == TaskType.BUILD:
                            from webhook.controllers.webhook_controller import execute_task

                            Thread(target=execute_task, args=(next_task, app), daemon=True).start()
                        else:
                            Thread(
                                target=fork_task_worker, args=(next_task, app), daemon=True
                            ).start()

        Thread(target=cleanup, daemon=True).start()


@fork_task_bp.route("/fork_task", methods=["POST"])
def fork_task():
    """派生任务"""
    global is_task_running
    data = request.json
    source_task_id = data.get("source_task_id")
    source_branch = data.get("source_branch")
    target_branch = data.get("target_branch")
    target_version_name = data.get("target_version_name")
    target_version_code = data.get("target_version_code")
    commit_message_raw = data.get("commit_message")
    operator = data.get("operator") or "assemble_bot"

    if target_branch != "master":
        label = f"#{target_branch}_req#"
    else:
        label = "#dev_req#"

    commit_message = (
        f"{label} {commit_message_raw}\n\n源任务分支: {source_branch}\n源任务ID: {source_task_id}"
    )

    fork_task = ForkTaskService.create_fork_task(
        source_task_id,
        source_branch,
        target_branch,
        target_version_name,
        target_version_code,
        commit_message,
        operator,
    )

    # 尝试获取任务锁
    if not acquire_task_lock(TaskType.FORK):
        # 如果获取锁失败，将任务加入队列
        logging.info("无法获取任务锁，将任务加入队列")
        add_task_to_queue(fork_task, TaskType.FORK)
        return (
            jsonify(
                {
                    "message": "Task added to queue",
                    "fork_task": fork_task.to_dict(),
                    "position": get_queue_size(TaskType.FORK),
                }
            ),
            202,
        )
    else:
        Thread(
            target=fork_task_worker,
            args=(fork_task, current_app._get_current_object()),
            daemon=True,
        ).start()
        logging.info(f"派生任务 {fork_task.id} 开始执行")

    return jsonify({"message": "派生任务创建成功", "fork_task": fork_task.to_dict()})


@fork_task_bp.route("/fork_task/<string:fork_task_id>", methods=["GET"])
def get_fork_task(fork_task_id):
    """获取派生任务"""
    fork_task = ForkTaskService.get_fork_task(fork_task_id)

    return jsonify({"fork_task": fork_task.to_dict()}), 200
