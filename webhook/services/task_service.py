import sqlite3
from datetime import datetime

from ..config import DB_FILE


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
                # 保持原始时区信息
                self.created_at = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")
            else:
                # 使用本地时间
                self.created_at = datetime.now()
        except (ValueError, TypeError) as e:
            self.created_at = datetime.now()

        self.author = self.commit_info.get("author", {}).get("name")
        self.commit_title = self.commit_info.get("title")
        self.commit_message = self.commit_info.get("message")
        self.commit_url = self.commit_info.get("url")
        self.commit_hash = self.commit_info.get("id")

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


def save_task(task: BuildTask):
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

    if status == "running":
        cursor.execute(
            """
            UPDATE tasks 
            SET status = ?, started_at = datetime('now', 'localtime'), error = ?
            WHERE id = ?
        """,
            (status, error, task_id),
        )
    elif status in ["completed", "failed"]:
        cursor.execute(
            """
            UPDATE tasks 
            SET status = ?, completed_at = datetime('now', 'localtime'), error = ?
            WHERE id = ?
        """,
            (status, error, task_id),
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
