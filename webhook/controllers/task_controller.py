import logging

from flask import jsonify

from . import task_bp
from ..services.task_service import TaskService


@task_bp.route("/task/<task_id>", methods=["GET"])
def get_task_info(task_id):
    """获取任务详细信息"""
    logging.info(f"获取任务详细信息: {task_id}")
    task = TaskService.get_task(task_id)
    if task:
        logging.info(f"获取任务详细信息: {task.to_dict()}")
        return jsonify({"task": task.to_dict()}), 200
    return jsonify({"error": "Task not found"}), 404


@task_bp.route("/queue", methods=["GET"])
def get_queue_status():
    """获取队列状态"""
    queue_status = TaskService.get_queue_status()

    # 修正返回的数据格式
    formatted_status = {
        "running_task": (
            format_task_info(queue_status["running_task"]) if queue_status["running_task"] else None
        ),
        "pending_tasks": [format_task_info(task) for task in queue_status["pending_tasks"]],
        "queue_size": queue_status["queue_size"],
        "recent_tasks": [format_task_info(task) for task in queue_status["recent_tasks"]],
    }

    return jsonify(formatted_status), 200


def format_task_info(task_dict):
    """格式化任务信息，确保返回正确的字段名称"""
    if not task_dict:
        return None
    return {
        "id": task_dict["id"],
        "project": task_dict["prod_name"],  # 修改字段名以匹配前端期望
        "task": task_dict["task_name"],  # 修改字段名以匹配前端期望
        "author": task_dict["author"],
        "commit_title": task_dict["commit_title"],
        "commit_message": task_dict["commit_message"],
        "commit_url": task_dict["commit_url"],
        "created_at": task_dict["created_at"],
        "started_at": task_dict["started_at"],
        "completed_at": task_dict["completed_at"],
        "status": task_dict["status"],
        "error": task_dict["error"],
    }
