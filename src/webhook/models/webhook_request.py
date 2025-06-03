import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from dataclasses_json import config, DataClassJsonMixin


@dataclass
class WebhookRequest(DataClassJsonMixin):
    """webhook请求记录"""

    # 主键
    id: Optional[int] = None
    # 任务id
    task_id: Optional[str] = None
    # 请求体
    request_body: Optional[str] = None
    # 请求头
    headers: Optional[dict] = None
    # 创建时间
    created_at: Optional[datetime] = field(
        default=None,
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
        ),
    )
    # 重放次数
    replay_count: Optional[int] = None

    def __init__(self, task_id, request_body, headers=None):
        self.id = None
        self.task_id = task_id
        self.request_body = request_body
        self.headers = headers
        self.created_at = datetime.now()
        self.replay_count = 0

    def save(self, db: sqlite3.Connection):
        """保存webhook请求记录"""
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO webhook_requests (task_id, request_body, headers, created_at, replay_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.task_id,
                self.request_body,
                self.headers,
                self.created_at,
                self.replay_count,
            ),
        )
        self.id = cursor.lastrowid
        db.commit()

    @staticmethod
    def get_by_task_id(task_id, db: sqlite3.Connection):
        """根据task_id获取webhook请求记录"""
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT id, task_id, request_body, headers, created_at
            FROM webhook_requests
            WHERE task_id = ?
            """,
            (task_id,),
        )
        row = cursor.fetchone()
        if row:
            request = WebhookRequest(row[1], row[2], row[3])
            request.id = row[0]
            request.created_at = row[4]
            return request
        return None

    @staticmethod
    def delete_by_task_id(task_id, db: sqlite3.Connection):
        """根据task_id删除webhook请求记录"""
        cursor = db.cursor()
        cursor.execute(
            """
            DELETE FROM webhook_requests
            WHERE task_id = ?
            """,
            (task_id,),
        )
        db.commit()

    @staticmethod
    def update_replay_count(task_id, db: sqlite3.Connection):
        """更新webhook请求记录的replay_count"""
        cursor = db.cursor()
        cursor.execute(
            """
            UPDATE webhook_requests SET replay_count = replay_count + 1 WHERE task_id = ?
            """,
            (task_id,),
        )
        db.commit()
