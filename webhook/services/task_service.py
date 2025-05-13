import json
import logging
from datetime import datetime
from typing import Any, Optional

from common.err_code import format_error
from webhook.types import Commit
from ..models.task import Task
from ..utils.validators import is_valid_build_task, parse_build_task


class TaskService:
    @staticmethod
    def handle_webhook_request(data: dict[str, Any]) -> tuple[Optional[list["Task"]], str, int]:
        """处理webhook请求并创建任务

        Args:
            data: webhook请求数据

        Returns:
            tuple: (tasks, message, status_code)
            - tasks: 创建的任务对象列表，如果没有创建则为None
            - message: 处理结果消息
            - status_code: HTTP状态码
        """
        # 验证提交信息
        commits: list[Commit] = data.get("commits", [])
        if not commits:
            return None, "No file changes in commit", 200

        logging.info(
            f"收到{len(commits)}个提交信息: {json.dumps(commits, ensure_ascii=False, indent=2)}"
        )
        valid_commits: list[Commit] = [commit for commit in commits if is_valid_build_task(commit)]
        if not valid_commits:
            return None, "No valid build task", 200

        def build_task(commit: Commit) -> Optional["Task"]:
            prod_name, task_name = parse_build_task(commit)
            return TaskService.create_task(
                prod_name=prod_name,
                task_name=task_name,
                commit_info=commit,
            )

        tasks = [build_task(vc) for vc in valid_commits]
        tasks = [task for task in tasks if task is not None]

        return tasks, "Task created successfully", 200

    @staticmethod
    def create_task(
            prod_name, task_name, commit_info: Commit = None, priority=0, retries=0
    ) -> Optional["Task"]:
        """创建任务

        首先检查任务是否存在，如果存在则根据状态决定是否创建新任务：
        - 如果状态为running/pending/completed/outdated，不创建新任务
        - 如果状态为failed，更新状态为pending并返回
        - 如果任务不存在，创建新任务

        Args:
            prod_name: 产品名称
            task_name: 任务名称
            commit_info: 提交信息
            priority: 优先级
            retries: 重试次数
        """
        task_id = f"{prod_name},{task_name}"
        task = Task.get_by_id(task_id)
        if task:
            if task.status == "failed":
                task.update_status("pending")
                return task
            else:
                return None

        task = Task(
            id=task_id,
            prod_name=prod_name,
            task_name=task_name,
            priority=priority,
            retries=retries,
            status="pending",
            created_at=datetime.now(),
        )

        if commit_info:
            task.author = commit_info.get("author", {}).get("name")
            task.commit_title = commit_info.get("title")
            task.commit_message = commit_info.get("message")
            task.commit_url = commit_info.get("url")
            task.commit_hash = commit_info.get("id")
            timestamp = None
            try:
                timestamp = commit_info.get("timestamp")
                if timestamp:
                    task.created_at = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")
            except (ValueError, TypeError):
                logging.error(f"解析时间戳失败: {timestamp}")
                pass

        task.save()
        return task

    @staticmethod
    def get_task(task_id: str) -> Optional["Task"]:
        """通过任务id获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            Optional[Task]: 任务对象，如果未找到则返回None
        """
        return Task.get_by_id(task_id)

    @staticmethod
    def get_running_task() -> Optional["Task"]:
        """获取正在执行的任务

        Returns:
            Optional[Task]: 正在执行的任务对象，如果未找到则返回None
        """
        return Task.get_running_task()

    @staticmethod
    def get_pending_tasks() -> list["Task"]:
        """获取待执行任务

        Returns:
            list[Task]: 待执行任务列表
        """
        return Task.get_pending_tasks()

    @staticmethod
    def get_recent_tasks(limit: int = 5) -> list["Task"]:
        """获取最近任务

        Args:
            limit: 返回的任务数量限制，默认为5

        Returns:
            list[Task]: 最近任务列表
        """
        return Task.get_recent_tasks(limit)

    @staticmethod
    def update_task_status(
            task_id: str, status: str, error: Optional[str] = None
    ) -> Optional["Task"]:
        """更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            error: 错误信息

        Returns:
            Optional[Task]: 更新后的任务对象，如果任务不存在则返回None
        """
        task = Task.get_by_id(task_id)
        if task:
            task.update_status(status, error)
            return task
        return None

    @staticmethod
    def get_queue_status(limit: int = 5, build_mode: str | None = None) -> dict[str, Any]:
        """
        获取队列状态

        Args:
            limit: 返回的任务数量限制
            build_mode: 构建模式，可选值为 dev/test/release，为 None 时不进行筛选
        """
        running_task = Task.get_running_task()
        pending_tasks = Task.get_pending_tasks()
        recent_tasks = Task.get_recent_tasks(limit=limit, build_mode=build_mode)

        return {
            "running_task": running_task.to_dict() if running_task else None,
            "pending_tasks": [task.to_dict() for task in pending_tasks],
            "queue_size": len(pending_tasks),
            "recent_tasks": [task.to_dict() for task in recent_tasks],
        }

    @staticmethod
    def stop_task(task_id):
        """停止运行中的任务

        Args:
            task_id: 任务ID

        Returns:
            tuple: (task, message, status_code)
            - task: 更新后的任务对象，如果任务不存在或不在运行中则为None
            - message: 处理结果消息
            - status_code: HTTP状态码
        """
        task = Task.get_by_id(task_id)
        if not task:
            return None, "Task not found", 404

        if task.status != "running":
            return None, "Task is not running", 400

        task.update_status("failed", format_error(10003))
        return task, "Task stopped successfully", 200

    @staticmethod
    def get_tasks_statistics():
        """获取所有任务的统计情况"""
        return Task.get_tasks_statistics()

    @staticmethod
    def get_packer_usage_statistics():
        """获取打包机使用人员统计情况"""
        return Task.get_packer_usage_statistics()
