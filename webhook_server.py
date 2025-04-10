import logging
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import PriorityQueue
from threading import Thread, Lock, Event

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from win11toast import toast

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
            author TEXT,
            commit_title TEXT,
            commit_message TEXT,
            commit_url TEXT,
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


# 初始化数据库
init_db()

# 加载环境变量
load_dotenv()


def cleanup():
    """清理函数"""
    stop_event.set()
    # 等待队列处理线程结束
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join(timeout=5)


# 注册清理函数
import atexit

atexit.register(cleanup)


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
                        show_toast(current_task, False)
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
                            show_toast(current_task, True)
                            logging.info(f"任务 {current_task.task_id} 执行成功")
                        else:
                            current_task.status = "failed"
                            current_task.error = (
                                f"Build failed with return code {process.returncode}"
                            )
                            show_toast(current_task, False)
                            logging.error(
                                f"任务 {current_task.task_id} 执行失败: {current_task.error}"
                            )
                    except subprocess.TimeoutExpired:
                        process.kill()
                        current_task.status = "failed"
                        current_task.error = "Build process timeout"
                        show_toast(current_task, False)
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


# 启动任务队列处理线程
queue_thread = Thread(target=process_task_queue, daemon=True)
queue_thread.start()


class BuildTask:
    """构建任务类"""

    def __init__(self, project_name, task_name, commit_info=None, priority=0, retries=0):
        self.project_name = project_name
        self.task_name = task_name
        self.priority = priority
        self.retries = retries
        self.started_at = None
        self.completed_at = None
        self.status = "pending"  # pending, running, completed, failed
        self.error = None
        # 确保 commit_info 是字典类型
        self.commit_info = commit_info if isinstance(commit_info, dict) else {}
        try:
            # 创建时间依据push的timestamp，其格式是文本字符串，例如timestamp: "2025-04-07T09:06:56+08:00"
            timestamp = self.commit_info.get("timestamp")
            if timestamp:
                self.created_at = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")
            else:
                self.created_at = datetime.now()
        except (ValueError, TypeError) as e:
            logging.warning(f"解析时间戳失败: {str(e)}，使用当前时间")
            self.created_at = datetime.now()

        self.author = self.commit_info.get("author", {}).get("name")
        self.commit_title = self.commit_info.get("title")
        self.commit_message = self.commit_info.get("message")
        self.commit_url = self.commit_info.get("url")

    def __lt__(self, other):
        # 优先级高的先执行
        return self.priority > other.priority

    @property
    def task_id(self):
        return f"{self.project_name},{self.task_name}"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.task_id,
            "project_name": self.project_name,
            "task_name": self.task_name,
            "author": self.author,
            "commit_title": self.commit_title,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


def save_task(task):
    """保存任务到数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO tasks 
        (id, project_name, task_name, author, commit_title, commit_message, commit_url,
         priority, retries, created_at, started_at, completed_at, status, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            task.task_id,
            task.project_name,
            task.task_name,
            task.author,
            task.commit_title,
            task.commit_message,
            task.commit_url,
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
        task = BuildTask(row[1], row[2], row[3], row[4], row[5])
        task.started_at = row[6]
        task.status = row[8]
        return task
    return None


def is_valid_build_task(added_files):
    """验证是否是有效的构建任务"""
    if len(added_files) != 2:
        return False

    pattern = r"^([^/]+)/([^/]+)/([^/]+\.(zip|rar|7z|tar\.gz|tar\.bz2)|[^/]+\.md)$"
    paths = []
    for file_path in added_files:
        match = re.match(pattern, file_path)
        if not match:
            return False
        paths.append(match.groups())

    if paths[0][0] != paths[1][0] or paths[0][1] != paths[1][1]:
        return False

    # 检查是否包含压缩包和markdown文件
    has_archive = any(
        file_path.endswith((".zip", ".rar", ".7z", ".tar.gz", ".tar.bz2"))
        for file_path in added_files
    )
    has_md = any(file_path.endswith(".md") for file_path in added_files)

    return has_archive and has_md


def parse_build_task(added_files):
    """解析构建任务信息"""
    file_path = added_files[0]
    parts = file_path.split("/")
    project_name = parts[0]
    task_name = parts[1]
    return project_name, task_name


def show_toast(task, success=True):
    """显示构建结果通知"""
    status = "✅成功" if success else "❌失败"
    message = f"🗃️项目: {task.project_name}\n🏗️任务: {task.task_name}\n🧑‍💻作者: {task.author}\n📝标题: {task.commit_title}"
    if not success and task.error:
        message += f"\n错误: {task.error}"
    toast(f"🎉构建通知:{status}", message)


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

        # 获取提交信息
        commit_info = commits[0]
        project_name, task_name = parse_build_task(added_files)

        # 显示收到构建请求的toast提示
        toast(
            "📜收到构建请求",
            f"🗃️项目: {project_name}\n🏗️任务: {task_name}\n🧑‍💻作者: {commit_info.get('author', {}).get('name', '未知')}\n📝标题: {commit_info.get('title', '无标题')}",
        )

        task = BuildTask(project_name, task_name, commit_info)

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
                        show_toast(task, True)
                    else:
                        task.status = "failed"
                        task.error = f"Build failed with return code {process.returncode}"
                        show_toast(task, False)
                        if task.retries < MAX_RETRIES:
                            task.retries += 1
                            task.priority += 1
                            with queue_lock:
                                task_queue.put(task)
                except subprocess.TimeoutExpired:
                    process.kill()
                    task.status = "failed"
                    task.error = "Build process timeout"
                    show_toast(task, False)
                finally:
                    task.completed_at = datetime.now()
                    save_task(task)

            Thread(target=cleanup, daemon=True).start()

            return jsonify({"message": "Build started successfully", "task": task.to_dict()}), 200

    except Exception as e:
        logging.error(f"处理webhook请求时发生错误: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 添加一个接口，这个接口可以通过传递 task_id 来获取任务的详细信息
@app.route("/task/<task_id>", methods=["GET"])
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
            "project_name": task[1],
            "task_name": task[2],
            "author": task[3],
            "commit_title": task[4],
            "commit_message": task[5],
            "commit_date": task[9],
            "status": task[12],  # 构建状态
        }
        logging.info(f"获取任务详细信息: {task_dict}")
        return jsonify({"task": task_dict}), 200
    else:
        return jsonify({"error": "Task not found"}), 404


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
            "started_at": task[10],
            "status": task[12],
            "error": task[13],
        }

    return jsonify(
        {
            "running_task": format_task(running_task),
            "queue_size": pending_count,
            "recent_tasks": [format_task(task) for task in recent_tasks],
        }
    )


if __name__ == "__main__":
    # 从环境变量获取端口和调试模式
    port = int(os.getenv("PORT", 5005))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # 配置热更新
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    app.run(host="0.0.0.0", port=port, ssl_context=None, debug=debug, use_reloader=debug)
