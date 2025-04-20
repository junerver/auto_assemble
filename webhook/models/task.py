from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..extensions.context import get_db


@dataclass
class Task:
    """任务"""

    id: Optional[str] = None
    prod_name: Optional[str] = None
    task_name: Optional[str] = None
    author: Optional[str] = None
    commit_title: Optional[str] = None
    commit_message: Optional[str] = None
    commit_url: Optional[str] = None
    priority: int = 0
    retries: int = 0
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: Optional[str] = None
    error: Optional[str] = None
    commit_hash: Optional[str] = None

    def __lt__(self, other):
        """比较两个任务的优先级
        优先级高的任务先执行，优先级相同时，创建时间早的任务先执行
        """
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.created_at < other.created_at

    @classmethod
    def get_by_id(cls, task_id: str) -> Optional["Task"]:
        """根据ID获取任务"""
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_running_task(cls) -> Optional["Task"]:
        """获取正在运行的任务"""
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM tasks WHERE status = 'running' ORDER BY started_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_pending_tasks(cls) -> list["Task"]:
        """获取待处理的任务"""
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at ASC")
        return [cls(**dict(row)) for row in cursor.fetchall()]

    @classmethod
    def get_recent_tasks(cls, limit: int = 5, build_mode: str | None = None) -> list["Task"]:
        """获取最近的任务

        Args:
            limit: 返回的任务数量限制
            build_mode: 构建模式，可选值为 dev/test/release，为 None 时不进行筛选
        """
        db = get_db()
        cursor = db.cursor()

        if build_mode and build_mode not in ["dev", "test", "release"]:
            raise ValueError("build_mode must be one of: dev, test, release")

        base_query = """
            SELECT * FROM tasks 
            WHERE status IN ('completed', 'failed')
        """

        if build_mode:
            base_query += """
                AND commit_title LIKE ? || '%'
            """
            params = (f"#{build_mode}_req#", limit)
        else:
            params = (limit,)

        query = (
                base_query
                + """
            ORDER BY 
                CASE 
                    WHEN completed_at IS NULL THEN 1
                    ELSE 0
                END,
                completed_at DESC
            LIMIT ?
        """
        )

        cursor.execute(query, params)
        return [cls(**dict(row)) for row in cursor.fetchall()]

    def save(self) -> None:
        """保存任务"""
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO tasks 
            (id, prod_name, task_name, author, commit_title, commit_message, commit_url,
             priority, retries, created_at, started_at, completed_at, status, error, commit_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                self.id,
                self.prod_name,
                self.task_name,
                self.author,
                self.commit_title,
                self.commit_message,
                self.commit_url,
                self.priority,
                self.retries,
                self.created_at,
                self.started_at,
                self.completed_at,
                self.status,
                self.error,
                self.commit_hash,
            ),
        )
        db.commit()

    def update_status(self, status: str, error: Optional[str] = None) -> None:
        """更新任务状态"""
        db = get_db()
        cursor = db.cursor()

        if status == "running":
            self.started_at = datetime.now()
            cursor.execute(
                """
                UPDATE tasks 
                SET status = ?, started_at = ?, error = ?
                WHERE id = ?
            """,
                (status, self.started_at, error, self.id),
            )
        elif status in ["completed", "failed"]:
            self.completed_at = datetime.now()
            cursor.execute(
                """
                UPDATE tasks 
                SET status = ?, completed_at = ?, error = ?
                WHERE id = ?
            """,
                (status, self.completed_at, error, self.id),
            )
        else:
            cursor.execute(
                """
                UPDATE tasks 
                SET status = ?, error = ?
                WHERE id = ?
            """,
                (status, error, self.id),
            )

        self.status = status
        self.error = error
        db.commit()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "prod_name": self.prod_name,
            "task_name": self.task_name,
            "author": self.author,
            "commit_title": self.commit_title,
            "commit_message": self.commit_message,
            "commit_url": self.commit_url,
            "priority": self.priority,
            "retries": self.retries,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "error": self.error,
            "commit_hash": self.commit_hash,
        }
