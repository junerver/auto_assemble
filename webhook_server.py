import logging
import os
import subprocess
import sys
import threading
import time
import json
import re
import sqlite3
from pathlib import Path
from queue import PriorityQueue
from threading import Thread, Lock, Event
from datetime import datetime
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("webhook.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

app = Flask(__name__)

# 数据库文件路径
DB_FILE = Path(__file__).parent / "tasks.db"
# 检查间隔（秒）
CHECK_INTERVAL = 1  # 减少检查间隔
# 任务超时时间（秒）
TASK_TIMEOUT = 1800  # 30分钟
# 最大重试次数
MAX_RETRIES = 3

# 任务队列（使用优先级队列）
task_queue = PriorityQueue()
# 队列锁
queue_lock = Lock()
# 停止事件
stop_event = Event()


class BuildTask:
    """构建任务类"""

    def __init__(self, project_name, task_name, priority=0, retries=0):
        self.project_name = project_name
        self.task_name = task_name
        self.priority = priority
        self.retries = retries
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.status = "pending"  # pending, running, completed, failed
        self.error = None

    def __lt__(self, other):
        # 优先级高的先执行
        return self.priority > other.priority

    @property
    def task_id(self):
        return f"{self.project_name},{self.task_name}"


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            task_name TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            retries INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT NOT NULL,
            error TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def save_task(task):
    """保存任务到数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO tasks 
        (id, project_name, task_name, priority, retries, created_at, started_at, completed_at, status, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            task.task_id,
            task.project_name,
            task.task_name,
            task.priority,
            task.retries,
            task.created_at,
            task.started_at,
            task.completed_at,
            task.status,
            task.error,
        ),
    )
    conn.commit()
    conn.close()


def update_task_status(task_id, status, error=None):
    """更新任务状态"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now()

    if status == "running":
        cursor.execute(
            """
            UPDATE tasks 
            SET status = ?, started_at = ?, error = ?
            WHERE id = ?
        """,
            (status, now, error, task_id),
        )
    elif status in ["completed", "failed"]:
        cursor.execute(
            """
            UPDATE tasks 
            SET status = ?, completed_at = ?, error = ?
            WHERE id = ?
        """,
            (status, now, error, task_id),
        )
    else:
        cursor.execute(
            """
            UPDATE tasks 
            SET status = ?, error = ?
            WHERE id = ?
        """,
            (status, error, task_id),
        )

    conn.commit()
    conn.close()


def get_running_task():
    """获取正在运行的任务"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM tasks 
        WHERE status = 'running' 
        ORDER BY started_at DESC 
        LIMIT 1
    """
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        task = BuildTask(row[1], row[2], row[3], row[4])
        task.started_at = row[6]
        task.status = row[8]
        return task
    return None


def process_task_queue():
    """处理任务队列"""
    while not stop_event.is_set():
        try:
            with queue_lock:
                if not task_queue.empty():
                    current_task = task_queue.get()

                    # 检查任务是否超时
                    if (
                        current_task.started_at
                        and (datetime.now() - current_task.started_at).total_seconds()
                        > TASK_TIMEOUT
                    ):
                        logging.warning(f"任务 {current_task.task_id} 执行超时")
                        current_task.status = "failed"
                        current_task.error = "Task timeout"
                        save_task(current_task)
                        continue

                    # 更新任务状态
                    current_task.started_at = datetime.now()
                    current_task.status = "running"
                    save_task(current_task)

                    logging.info(f"开始执行任务: {current_task.task_id}")

                    # 执行构建
                    process = subprocess.Popen(
                        ["auto-assemble", "--fn", "1", "--task", current_task.task_id],
                        cwd=os.path.dirname(os.path.abspath(__file__)),
                        encoding="utf-8",
                    )

                    # 等待进程完成
                    try:
                        process.wait(timeout=TASK_TIMEOUT)
                        if process.returncode == 0:
                            current_task.status = "completed"
                            logging.info(f"任务 {current_task.task_id} 执行成功")
                        else:
                            current_task.status = "failed"
                            current_task.error = (
                                f"Build failed with return code {process.returncode}"
                            )
                            logging.error(
                                f"任务 {current_task.task_id} 执行失败: {current_task.error}"
                            )
                    except subprocess.TimeoutExpired:
                        process.kill()
                        current_task.status = "failed"
                        current_task.error = "Build process timeout"
                        logging.error(f"任务 {current_task.task_id} 执行超时")

                    # 处理失败重试
                    if current_task.status == "failed" and current_task.retries < MAX_RETRIES:
                        current_task.retries += 1
                        current_task.priority += 1  # 增加重试任务的优先级
                        task_queue.put(current_task)
                        logging.info(
                            f"任务 {current_task.task_id} 加入重试队列，当前重试次数: {current_task.retries}"
                        )

                    # 保存任务状态
                    current_task.completed_at = datetime.now()
                    save_task(current_task)

            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logging.error(f"处理任务队列时发生错误: {str(e)}")
            time.sleep(CHECK_INTERVAL)


def is_valid_build_task(added_files):
    """验证是否是有效的构建任务"""
    if len(added_files) != 2:
        return False

    pattern = r"^([^/]+)/([^/]+)/([^/]+\.zip|[^/]+\.md)$"
    paths = []
    for file_path in added_files:
        match = re.match(pattern, file_path)
        if not match:
            return False
        paths.append(match.groups())

    if paths[0][0] != paths[1][0] or paths[0][1] != paths[1][1]:
        return False

    has_zip = any(file_path.endswith(".zip") for file_path in added_files)
    has_md = any(file_path.endswith(".md") for file_path in added_files)

    return has_zip and has_md


def parse_build_task(added_files):
    """解析构建任务信息"""
    file_path = added_files[0]
    parts = file_path.split("/")
    project_name = parts[0]
    task_name = parts[1]
    return project_name, task_name


@app.route("/webhook", methods=["POST"])
def webhook():
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

        project_name, task_name = parse_build_task(added_files)
        task = BuildTask(project_name, task_name)

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
                        "task": task.task_id,
                        "position": task_queue.qsize(),
                    }
                ),
                202,
            )
        else:
            # 直接执行构建
            task.started_at = datetime.now()
            task.status = "running"
            save_task(task)

            process = subprocess.Popen(
                ["auto-assemble", "--fn", "1", "--task", task.task_id],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                encoding="utf-8",
            )

            def cleanup():
                try:
                    process.wait(timeout=TASK_TIMEOUT)
                    if process.returncode == 0:
                        task.status = "completed"
                    else:
                        task.status = "failed"
                        task.error = f"Build failed with return code {process.returncode}"
                        if task.retries < MAX_RETRIES:
                            task.retries += 1
                            task.priority += 1
                            with queue_lock:
                                task_queue.put(task)
                except subprocess.TimeoutExpired:
                    process.kill()
                    task.status = "failed"
                    task.error = "Build process timeout"
                finally:
                    task.completed_at = datetime.now()
                    save_task(task)

            Thread(target=cleanup, daemon=True).start()

            return jsonify({"message": "Build started successfully", "task": task.task_id}), 200

    except Exception as e:
        logging.error(f"处理webhook请求时发生错误: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/queue", methods=["GET"])
def get_queue_status():
    """获取队列状态"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 获取正在运行的任务
    cursor.execute("SELECT * FROM tasks WHERE status = 'running' ORDER BY started_at DESC LIMIT 1")
    running_task = cursor.fetchone()

    # 获取等待中的任务
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    pending_count = cursor.fetchone()[0]

    # 获取最近完成的任务
    cursor.execute(
        "SELECT * FROM tasks WHERE status IN ('completed', 'failed') ORDER BY completed_at DESC LIMIT 5"
    )
    recent_tasks = cursor.fetchall()

    conn.close()

    return jsonify(
        {
            "running_task": {
                "id": running_task[0] if running_task else None,
                "project": running_task[1] if running_task else None,
                "task": running_task[2] if running_task else None,
                "started_at": running_task[6] if running_task else None,
            },
            "queue_size": pending_count,
            "recent_tasks": [
                {
                    "id": task[0],
                    "project": task[1],
                    "task": task[2],
                    "status": task[8],
                    "completed_at": task[7],
                    "error": task[9],
                }
                for task in recent_tasks
            ],
        }
    )


def cleanup():
    """清理函数"""
    stop_event.set()
    # 等待队列处理线程结束
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join(timeout=5)


if __name__ == "__main__":
    # 初始化数据库
    init_db()

    # 加载环境变量
    load_dotenv()

    # 启动任务队列处理线程
    queue_thread = Thread(target=process_task_queue, daemon=True)
    queue_thread.start()

    # 注册清理函数
    import atexit

    atexit.register(cleanup)

    # 从环境变量获取端口和调试模式
    port = int(os.getenv("PORT", 5005))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # 配置热更新
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    app.run(host="0.0.0.0", port=port, ssl_context=None, debug=debug, use_reloader=debug)
