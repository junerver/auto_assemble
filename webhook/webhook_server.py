import logging
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from queue import PriorityQueue
from threading import Thread, Lock, Event

from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template
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

app = Flask(__name__, template_folder="templates")

# 数据库文件路径
DB_FILE = Path(__file__).parent / "webhook_server.db"
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

    # 创建原有的tasks表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            prod_name TEXT NOT NULL,
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

    # 创建项目配置表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS project_config (
            id TEXT PRIMARY KEY,
            project_url TEXT NOT NULL UNIQUE,
            prod_name TEXT NOT NULL,
            hbx_version TEXT,
            uniapp_id TEXT,
            uniapp_appkey TEXT,
            uniapp_is_cli BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # 创建第三方字典表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS third_party_dict (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            dict_key TEXT NOT NULL,
            dict_value TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(provider, dict_key)
        )
    """
    )

    # 创建第三方配置表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS third_party_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            dict_key TEXT NOT NULL,
            config_value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES project_config(id),
            FOREIGN KEY (dict_key) REFERENCES third_party_dict(dict_key),
            UNIQUE(project_id, dict_key)
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
                        current_task.completed_at = datetime.now()
                        save_task(current_task)
                        show_toast(current_task, False)
                        continue

                    # 如果是第一次执行，设置开始时间
                    if current_task.started_at is None:
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
                            current_task.completed_at = datetime.now()
                            show_toast(current_task, True)
                            logging.info(f"任务 {current_task.task_id} 执行成功")
                        else:
                            current_task.status = "failed"
                            current_task.error = (
                                f"Build failed with return code {process.returncode}"
                            )
                            current_task.completed_at = datetime.now()
                            show_toast(current_task, False)
                            logging.error(
                                f"任务 {current_task.task_id} 执行失败: {current_task.error}"
                            )
                    except subprocess.TimeoutExpired:
                        process.kill()
                        current_task.status = "failed"
                        current_task.error = "Build process timeout"
                        current_task.completed_at = datetime.now()
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
                    else:
                        # 保存任务状态（仅在不再重试时）
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

    def __init__(self, prod_name, task_name, commit_info=None, priority=0, retries=0):
        self.prod_name = prod_name
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
        return f"{self.prod_name},{self.task_name}"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.task_id,
            "prod_name": self.prod_name,
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
        (id, prod_name, task_name, author, commit_title, commit_message, commit_url,
         priority, retries, created_at, started_at, completed_at, status, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            task.task_id,
            task.prod_name,
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
    prod_name = parts[0]
    task_name = parts[1]
    return prod_name, task_name


def show_toast(task, success=True):
    """显示构建结果通知"""
    status = "✅成功" if success else "❌失败"
    message = f"🗃️项目: {task.prod_name}\n🏗️任务: {task.task_name}\n🧑‍💻作者: {task.author}\n📝标题: {task.commit_title}"
    if not success and task.error:
        message += f"\n错误: {task.error}"
    toast(f"🎉构建通知:{status}", message)


@app.route("/")
def index():
    """显示打包服务器状态页面"""
    return render_template("index.html")


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
        prod_name, task_name = parse_build_task(added_files)

        # 显示收到构建请求的toast提示
        toast(
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
                        task.completed_at = datetime.now()
                        show_toast(task, True)
                    else:
                        task.status = "failed"
                        task.error = f"Build failed with return code {process.returncode}"
                        task.completed_at = datetime.now()
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
                    task.completed_at = datetime.now()
                    show_toast(task, False)
                finally:
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
            "prod_name": task[1],
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
    cursor.execute("SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at ASC")
    pending_tasks = cursor.fetchall()

    # 获取最近完成的任务，确保按completed_at倒序排列
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


@app.route("/api/config/project", methods=["POST"])
def configure_project():
    """配置项目信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        # 生成UUID作为项目ID
        project_id = str(uuid.uuid4())

        # 提取项目基础配置
        project_config = {
            "id": project_id,
            "project_url": data.get("project_url"),
            "prod_name": data.get("prod_name"),
            "hbx_version": data.get("hbx_version"),
            "uniapp_id": data.get("uniapp_id"),
            "uniapp_appkey": data.get("uniapp_appkey"),
            "uniapp_is_cli": data.get("uniapp_is_cli", False),
        }

        # 提取第三方配置
        third_party_configs = data.get("third_party_configs", [])

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # 插入项目配置
            cursor.execute(
                """
                INSERT INTO project_config 
                (id, project_url, prod_name, hbx_version, uniapp_id, uniapp_appkey, uniapp_is_cli)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_config["id"],
                    project_config["project_url"],
                    project_config["prod_name"],
                    project_config["hbx_version"],
                    project_config["uniapp_id"],
                    project_config["uniapp_appkey"],
                    project_config["uniapp_is_cli"],
                ),
            )

            # 插入第三方配置
            for config in third_party_configs:
                cursor.execute(
                    """
                    INSERT INTO third_party_config 
                    (project_id, dict_key, config_value)
                    VALUES (?, ?, ?)
                    """,
                    (project_id, config["key"], config["value"]),
                )

            conn.commit()
            return (
                jsonify({"message": "Project configured successfully", "project_id": project_id}),
                200,
            )

        except sqlite3.IntegrityError as e:
            conn.rollback()
            return jsonify({"error": f"Database integrity error: {str(e)}"}), 400
        finally:
            conn.close()

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/config/project", methods=["GET"])
def get_project_config():
    """获取项目配置信息"""
    try:
        # 获取查询参数
        project_url = request.args.get("url")
        prod_name = request.args.get("name")

        if not project_url and not prod_name:
            return jsonify({"error": "Must provide either url or name parameter"}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 构建查询条件
        query_conditions = []
        query_params = []

        if project_url:
            query_conditions.append("project_url = ?")
            query_params.append(project_url)
        if prod_name:
            query_conditions.append("prod_name = ?")
            query_params.append(prod_name)

        # 获取项目基础配置
        query = f"""
            SELECT * FROM project_config 
            WHERE {' AND '.join(query_conditions)}
        """
        cursor.execute(query, query_params)
        project_config = cursor.fetchone()

        if not project_config:
            return jsonify({"error": "Project not found"}), 404

        # 获取项目ID
        project_id = project_config[0]

        # 获取第三方配置
        cursor.execute(
            """
            SELECT tpc.dict_key, tpc.config_value, tpd.provider, tpd.description
            FROM third_party_config tpc
            JOIN third_party_dict tpd ON tpc.dict_key = tpd.dict_key
            WHERE tpc.project_id = ?
            """,
            (project_id,),
        )
        third_party_configs = cursor.fetchall()

        # 构建响应数据
        response_data = {
            "project_config": {
                "id": project_config[0],
                "project_url": project_config[1],
                "prod_name": project_config[2],
                "hbx_version": project_config[3],
                "uniapp_id": project_config[4],
                "uniapp_appkey": project_config[5],
                "uniapp_is_cli": bool(project_config[6]),
            },
            "third_party_configs": [
                {
                    "key": config[0],
                    "value": config[1],
                    "provider": config[2],
                    "description": config[3],
                }
                for config in third_party_configs
            ],
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/config/project/<project_id>", methods=["PUT"])
def update_project_config(project_id):
    """更新项目配置信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # 检查项目是否存在
            cursor.execute("SELECT id FROM project_config WHERE id = ?", (project_id,))
            if not cursor.fetchone():
                return jsonify({"error": "Project not found"}), 404

            # 更新项目基础配置
            update_fields = []
            update_values = []

            # 构建更新字段和值
            for field in [
                "project_url",
                "prod_name",
                "hbx_version",
                "uniapp_id",
                "uniapp_appkey",
                "uniapp_is_cli",
            ]:
                if field in data:
                    update_fields.append(f"{field} = ?")
                    update_values.append(data[field])

            if update_fields:
                update_values.append(project_id)
                update_query = f"""
                    UPDATE project_config 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
                cursor.execute(update_query, update_values)

            # 处理第三方配置更新
            if "third_party_configs" in data:
                # 先删除现有的第三方配置
                cursor.execute("DELETE FROM third_party_config WHERE project_id = ?", (project_id,))

                # 插入新的第三方配置
                for config in data["third_party_configs"]:
                    cursor.execute(
                        """
                        INSERT INTO third_party_config 
                        (project_id, dict_key, config_value)
                        VALUES (?, ?, ?)
                        """,
                        (project_id, config["key"], config["value"]),
                    )

            conn.commit()
            return jsonify({"message": "Project configuration updated successfully"}), 200

        except sqlite3.IntegrityError as e:
            conn.rollback()
            return jsonify({"error": f"Database integrity error: {str(e)}"}), 400
        finally:
            conn.close()

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 从环境变量获取端口和调试模式
    port = int(os.getenv("PORT", 5005))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # 配置热更新
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    app.run(host="0.0.0.0", port=port, ssl_context=None, debug=debug, use_reloader=debug)
