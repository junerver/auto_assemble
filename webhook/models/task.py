import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from common.time import safe_convert_datetime

# 任务状态，包含：pending（待处理）、running（运行中）、completed（已完成）、failed（失败）、outdated（过期）
TaskStatus = Literal["pending", "running", "completed", "failed", "outdated"]


@dataclass
class Task:
    """任务"""

    id: Optional[str] = None
    # 项目名称
    prod_name: Optional[str] = None
    # 任务名称（时间戳）
    task_name: Optional[str] = None
    # 作者
    author: Optional[str] = None
    # 提交标题
    commit_title: Optional[str] = None
    # 提交消息
    commit_message: Optional[str] = None
    # 提交URL
    commit_url: Optional[str] = None
    # 优先级
    priority: int = 0
    # 重试次数
    retries: int = 0
    # 创建时间
    created_at: Optional[datetime] = None
    # 开始时间
    started_at: Optional[datetime] = None
    # 完成时间
    completed_at: Optional[datetime] = None
    # 状态
    status: Optional[TaskStatus] = None
    # 错误信息
    error: Optional[str] = None
    # 提交哈希（前端任务提交哈希）
    commit_hash: Optional[str] = None
    # 响应哈希（后端构建响应哈希）
    response_hash: Optional[str] = None
    # 元数据
    metadata: Optional[dict] = None
    # 派生任务源任务ID
    source_task_id: Optional[str] = None

    def __post_init__(self):
        """在初始化后确保datetime字段的类型正确"""
        for field in ["created_at", "started_at", "completed_at"]:
            value = getattr(self, field)
            if value and isinstance(value, str):
                setattr(self, field, safe_convert_datetime(value))

    def __lt__(self, other):
        """比较两个任务的优先级
        优先级高的任务先执行，优先级相同时，创建时间早的任务先执行
        """
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.created_at < other.created_at

    def save(self, db: sqlite3.Connection) -> None:
        """保存任务"""
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO tasks 
            (id, prod_name, task_name, author, commit_title, commit_message, commit_url,
             priority, retries, created_at, started_at, completed_at, status, error, commit_hash, response_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                self.response_hash,
            ),
        )
        db.commit()

    @classmethod
    def _task_row_to_task(cls, row: sqlite3.Row):
        row_dict = dict(row)
        # 转换datetime字段
        for field in ["created_at", "started_at", "completed_at"]:
            if row_dict.get(field):
                row_dict[field] = safe_convert_datetime(row_dict[field])
        # 提取元数据字段
        metadata = None
        if row_dict.get("package_name"):
            metadata = {
                "package_name": row_dict.pop("package_name"),
                "version_name": row_dict.pop("version_name"),
                "version_code": row_dict.pop("version_code"),
                "build_type": row_dict.pop("build_type"),
                "flavor": row_dict.pop("flavor"),
                "build_date": row_dict.pop("build_date"),
                "file_size": row_dict.pop("file_size"),
                "md5": row_dict.pop("md5"),
                "is_normalized": bool(row_dict.pop("is_normalized")),
                "is_obfuscated": bool(row_dict.pop("is_obfuscated")),
            }
        else:
            row_dict.pop("package_name")
            row_dict.pop("version_name")
            row_dict.pop("version_code")
            row_dict.pop("build_type")
            row_dict.pop("flavor")
            row_dict.pop("build_date")
            row_dict.pop("file_size")
            row_dict.pop("md5")
            row_dict.pop("is_normalized")
            row_dict.pop("is_obfuscated")

        source_task_id = row_dict.pop("source_task_id")

        task = cls(**row_dict)
        task.metadata = metadata
        task.source_task_id = source_task_id
        return task

    # noinspection PyTypeChecker
    @classmethod
    def get_by_id(cls, task_id: str, db: sqlite3.Connection) -> Optional["Task"]:
        """根据ID获取任务"""
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT t.*,
                   btm.package_name,
                   btm.version_name,
                   btm.version_code,
                   btm.build_type,
                   btm.flavor,
                   btm.build_date,
                   btm.file_size,
                   btm.md5,
                   btm.is_normalized,
                   btm.is_obfuscated,
                   ft.source_task_id
            FROM tasks t
                     LEFT JOIN build_task_metadata btm ON t.id = btm.task_id
                     LEFT JOIN fork_tasks ft ON t.id = ft.source_task_id
            WHERE t.id = ?
            """,
            (task_id,),
        )
        row = cursor.fetchone()
        if row:
            return Task._task_row_to_task(row)
        return None

    # noinspection PyTypeChecker
    @classmethod
    def get_running_task(cls, db: sqlite3.Connection) -> Optional["Task"]:
        """获取正在运行的任务"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tasks WHERE status = 'running' ORDER BY started_at DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            row_dict = dict(row)
            # 转换datetime字段
            for field in ["created_at", "started_at", "completed_at"]:
                if row_dict.get(field):
                    row_dict[field] = safe_convert_datetime(row_dict[field])
            return cls(**row_dict)
        return None

    # noinspection PyTypeChecker
    @classmethod
    def get_pending_tasks(cls, db: sqlite3.Connection = None) -> list["Task"]:
        """获取待处理的任务"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at")
        tasks = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # 转换datetime字段
            for field in ["created_at", "started_at", "completed_at"]:
                if row_dict.get(field):
                    row_dict[field] = safe_convert_datetime(row_dict[field])
            tasks.append(cls(**row_dict))
        return tasks

    # noinspection PyTypeChecker
    @classmethod
    def get_recent_tasks(
        cls,
        limit: int = 5,
        build_mode: str | None = None,
        db: sqlite3.Connection = None,
    ) -> list["Task"]:
        """
        获取最近的任务（只检索未过期的任务，即 status 为 completed 或 failed 的任务），如果 build_mode 不为 None，则只返回 build_mode 对应的任务
        如果 build_mode 为 None，则返回所有任务。

        Args:
            limit: 返回的任务数量限制
            build_mode: 构建模式，可选值为 dev/test/release，为 None 时不进行筛选
            db: 数据库连接
        """
        cursor = db.cursor()

        if build_mode is not None and build_mode not in ["dev", "test", "release"]:
            raise ValueError("build_mode must be one of: dev, test, release")

        base_query = """
                     SELECT t.*,
                            btm.package_name,
                            btm.version_name,
                            btm.version_code,
                            btm.build_type,
                            btm.flavor,
                            btm.build_date,
                            btm.file_size,
                            btm.md5,
                            btm.is_normalized,
                            btm.is_obfuscated,
                            ft.source_task_id
                     FROM tasks t
                              LEFT JOIN build_task_metadata btm ON t.id = btm.task_id
                              LEFT JOIN fork_tasks ft ON t.id = ft.id
                     WHERE t.status IN ('completed', 'failed')
        """

        if build_mode:
            base_query += """
                AND t.commit_title LIKE ? || '%'
            """
            params = (f"#{build_mode}_req#", limit)
        else:
            params = (limit,)

        query = (
            base_query
            + """
            ORDER BY 
                CASE 
                    WHEN t.completed_at IS NULL THEN 1
                    ELSE 0
                END,
                t.completed_at DESC
            LIMIT ?
        """
        )

        cursor.execute(query, params)
        tasks = []
        for row in cursor.fetchall():
            tasks.append(Task._task_row_to_task(row))
        return tasks

    @classmethod
    def get_tasks_statistics(cls, db: sqlite3.Connection) -> list[dict]:
        """
        获取所有任务的统计情况，按照项目名称分组，最终返回一个数组，数组中每个元素是一个字典，字典中包含项目名称和任务数量
        """
        cursor = db.cursor()
        cursor.execute("SELECT prod_name, COUNT(*) FROM tasks GROUP BY prod_name")
        return [{"prod_name": row[0], "count": row[1]} for row in cursor.fetchall()]

    # 统计打包机使用人员
    @classmethod
    def get_packer_usage_statistics(cls, db: sqlite3.Connection) -> list[dict]:
        """
        统计打包机使用人员
        """
        cursor = db.cursor()
        cursor.execute("SELECT author, COUNT(*) FROM tasks GROUP BY author")
        return [{"author": row[0], "count": row[1]} for row in cursor.fetchall()]

    @classmethod
    def get_other_normalized_tasks(cls, current_task_id: str, db: sqlite3.Connection) -> list["Task"]:
        """
        获取除当前任务外的已执行归一化的任务列表
        """
        cursor = db.cursor()
        prod_name, _ = current_task_id.split(",")
        cursor.execute(
            """
            SELECT btm.task_id
            FROM build_task_metadata btm
            WHERE btm.is_normalized = 1
            AND btm.task_id != ?
            AND btm.task_id LIKE ? || '%'
            """,
            (current_task_id, prod_name),
        )
        return [Task.get_by_id(row[0], db) for row in cursor.fetchall()]

    def update_response_hash(self, response_hash: str, db: sqlite3.Connection) -> None:
        """更新任务响应哈希"""
        cursor = db.cursor()
        cursor.execute("UPDATE tasks SET response_hash = ? WHERE id = ?", (response_hash, self.id))
        db.commit()

    def update_status(self, status: TaskStatus, error: Optional[str] = None, db: sqlite3.Connection = None) -> None:
        """更新任务状态"""
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "error": self.error,
            "commit_hash": self.commit_hash,
            "response_hash": self.response_hash,
            "metadata": self.metadata,
            "source_task_id": self.source_task_id,
        }
