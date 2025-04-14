import logging
import sqlite3

from flask import jsonify

from . import task_bp
from ..config import DB_FILE


@task_bp.route("/task/<task_id>", methods=["GET"])
def get_task_info(task_id):
    """获取任务详细信息"""
    logging.info(f"获取任务详细信息: {task_id}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()
    if task:
        task_dict = {
            "id": task[0],
            "prod_name": task[1],
            "task_name": task[2],
            "author": task[3],
            "commit_title": task[4],
            "commit_message": task[5],
            "commit_date": task[9],
            "status": task[12],
        }
        logging.info(f"获取任务详细信息: {task_dict}")
        return jsonify({"task": task_dict}), 200
    else:
        return jsonify({"error": "Task not found"}), 404


@task_bp.route("/queue", methods=["GET"])
def get_queue_status():
    """获取队列状态"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 获取正在运行的任务
    cursor.execute("SELECT * FROM tasks WHERE status = 'running' ORDER BY started_at DESC LIMIT 1")
    running_task = cursor.fetchone()

    # 获取等待中的任务
    cursor.execute("SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at ASC")
    pending_tasks = cursor.fetchall()

    # 获取最近完成的任务
    cursor.execute(
        """
        SELECT * FROM tasks 
        WHERE status IN ('completed', 'failed') 
        ORDER BY 
            CASE 
                WHEN completed_at IS NULL THEN 1
                ELSE 0
            END,
            completed_at DESC
        LIMIT 5
    """
    )
    recent_tasks = cursor.fetchall()

    conn.close()

    def format_task(task):
        if not task:
            return None
        return {
            "id": task[0],
            "project": task[1],
            "task": task[2],
            "author": task[3],
            "commit_title": task[4],
            "commit_message": task[5],
            "commit_url": task[6],
            "created_at": task[9],
            "started_at": task[10],
            "completed_at": task[11],
            "status": task[12],
            "error": task[13],
        }

    return jsonify(
        {
            "running_task": format_task(running_task),
            "pending_tasks": [format_task(task) for task in pending_tasks],
            "queue_size": len(pending_tasks),
            "recent_tasks": [format_task(task) for task in recent_tasks],
        }
    )
