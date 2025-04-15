import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..config import DB_FILE


@dataclass
class WebhookRequest:
    id: Optional[int] = None
    task_id: Optional[str] = None
    request_body: Optional[str] = None
    headers: Optional[dict] = None
    created_at: Optional[datetime] = None

    def __init__(self, task_id, request_body, headers=None):
        self.id = None
        self.task_id = task_id
        self.request_body = request_body
        self.headers = headers
        self.created_at = datetime.now()

    def save(self):
        """保存webhook请求记录"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO webhook_requests (task_id, request_body, headers, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (self.task_id, self.request_body, self.headers, self.created_at),
        )
        self.id = cursor.lastrowid
        conn.commit()
        conn.close()

    @staticmethod
    def get_by_task_id(task_id):
        """根据task_id获取webhook请求记录"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, task_id, request_body, headers, created_at
            FROM webhook_requests
            WHERE task_id = ?
            """,
            (task_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            request = WebhookRequest(row[1], row[2], row[3])
            request.id = row[0]
            request.created_at = row[4]
            return request
        return None

    @staticmethod
    def delete_by_task_id(task_id):
        """根据task_id删除webhook请求记录"""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM webhook_requests
            WHERE task_id = ?
            """,
            (task_id,),
        )
        conn.commit()
        conn.close()

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "request_body": self.request_body,
            "headers": self.headers,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
