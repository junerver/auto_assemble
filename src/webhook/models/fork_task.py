import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from dataclasses_json import DataClassJsonMixin, config


@dataclass
class ForkTask(DataClassJsonMixin):
    """派生任务"""

    # 派生任务ID
    id: Optional[str] = None
    # 源任务ID
    source_task_id: Optional[str] = None
    # 源任务分支
    source_branch: Optional[str] = None
    # 目标分支
    target_branch: Optional[str] = None
    # 目标版本名称
    target_version_name: Optional[str] = None
    # 目标版本代码
    target_version_code: Optional[str] = None
    # 提交消息
    commit_message: Optional[str] = None
    # 创建时间
    created_at: Optional[datetime] = field(
        default=None,
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
        ),
    )
    # 操作人
    operator: Optional[str] = None

    def save(self, db: sqlite3.Connection) -> None:
        """保存派生任务"""
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO fork_tasks (id, source_task_id, source_branch, target_branch, target_version_name, target_version_code, commit_message, created_at, operator) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self.id,
                self.source_task_id,
                self.source_branch,
                self.target_branch,
                self.target_version_name,
                self.target_version_code,
                self.commit_message,
                self.created_at,
                self.operator,
            ),
        )
        db.commit()

    @staticmethod
    def get_by_id(fork_task_id: str, db: sqlite3.Connection) -> Optional["ForkTask"]:
        """根据ID获取派生任务"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM fork_tasks WHERE id = ?", (fork_task_id,))
        row = cursor.fetchone()
        if row:
            return ForkTask(**row)
        return None
