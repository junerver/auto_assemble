import logging

import requests
from flask import jsonify, current_app, request

from . import task_bp
from ..services.task_service import TaskService
from ..services.webhook_request_service import WebhookRequestService


@task_bp.route("/task/<task_id>", methods=["GET"])
def get_task_info(task_id):
    """获取任务详细信息"""
    logging.info(f"获取任务详细信息: {task_id}")
    task = TaskService.get_task(task_id)
    if task:
        logging.info(f"获取任务详细信息: {task.to_dict()}")
        return jsonify({"task": format_task_info(task.to_dict())}), 200
    return jsonify({"error": "Task not found"}), 404


@task_bp.route("/task/<task_id>", methods=["DELETE"])
def outdated_task(task_id):
    """标记任务为过期"""
    TaskService.update_task_status(task_id, "outdated")
    return jsonify({"message": "Task outdated"}), 200


@task_bp.route("/tasks/statistics", methods=["GET"])
def get_tasks_statistics():
    """获取所有任务的统计情况"""
    tasks = TaskService.get_tasks_statistics()
    packer_usage = TaskService.get_packer_usage_statistics()
    return jsonify({"tasks": tasks, "packer_usage": packer_usage}), 200


@task_bp.route("/queue", methods=["GET"])
def get_queue_status():
    """获取队列状态"""
    build_mode = request.args.get("build_mode", "all")
    if build_mode == "all":
        build_mode = None
    queue_status = TaskService.get_queue_status(20, build_mode=build_mode)

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


@task_bp.route("/task/<task_id>/replay", methods=["POST"])
def replay_webhook(task_id):
    """重放webhook请求"""
    logging.info(f"重放webhook请求: {task_id}")

    # 获取原始请求数据
    request_data, headers, status_code = WebhookRequestService.replay_webhook_request(task_id)
    if not request_data:
        return jsonify({"error": headers}), status_code

    try:
        # 获取webhook接口的URL
        webhook_url = f"http://localhost:{current_app.config['PORT']}/webhook"

        # 发送请求到webhook接口
        response = requests.post(webhook_url, json=request_data, headers=headers, timeout=30)

        if response.status_code == 200:
            return jsonify({"message": "Webhook请求重放成功", "response": response.json()}), 200
        else:
            return (
                jsonify(
                    {
                        "error": "Webhook请求重放失败",
                        "status_code": response.status_code,
                        "response": response.json(),
                    }
                ),
                response.status_code,
            )

    except requests.exceptions.RequestException as e:
        logging.error(f"重放webhook请求时发生错误: {str(e)}")
        return jsonify({"error": f"请求发送失败: {str(e)}"}), 500


@task_bp.route("/task/<task_id>/stop", methods=["POST"])
def stop_task(task_id):
    """停止运行中的任务"""
    logging.info(f"停止任务: {task_id}")
    task, message, status_code = TaskService.stop_task(task_id)
    if task:
        return jsonify({"message": message, "task": format_task_info(task.to_dict())}), status_code
    return jsonify({"error": message}), status_code


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
        "commit_hash": task_dict["commit_hash"],
        "metadata": task_dict["metadata"],
        "source_task_id": task_dict["source_task_id"],
    }
