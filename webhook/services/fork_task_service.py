"""
Description:
Author: 侯文君
Date: 2025-05-12 15:20:50
LastEditors: 侯文君
LastEditTime: 2025-05-15 18:06:00
"""

import sqlite3
from datetime import datetime

from webhook.models.fork_task import ForkTask


class ForkTaskService:
    @staticmethod
    def create_fork_task(
            source_task_id: str,
            source_branch: str,
            target_branch: str,
            target_version_name: str,
            target_version_code: str,
            commit_message: str,
            operator: str = "assemble_bot",
            db: sqlite3.Connection = None,
    ) -> ForkTask:
        """
        创建派生任务,从原始任务中获取项目名称，并生成任务名称，默认操作人为assemble_bot
        """
        prod_name = source_task_id.split(",")[0]
        task_name = datetime.now().strftime("%Y%m%d%H%M")
        fork_task = ForkTask(
            id=f"{prod_name},{task_name}",
            source_task_id=source_task_id,
            source_branch=source_branch,
            target_branch=target_branch,
            target_version_name=target_version_name,
            target_version_code=target_version_code,
            commit_message=commit_message,
            created_at=datetime.now(),
            operator=operator,
        )
        fork_task.save(db)
        return fork_task

    @staticmethod
    def get_fork_task(fork_task_id: str, db: sqlite3.Connection = None) -> ForkTask:
        """
        获取派生任务
        """
        return ForkTask.get_by_id(fork_task_id, db)
