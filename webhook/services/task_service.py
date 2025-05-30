import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Optional

from common.err_code import format_error
from webhook.services.webhook_request_service import WebhookRequestService
from webhook.types import Commit, GitLabPushEventModel
from webhook.models.task import Task, TaskStatus
from webhook.utils.validators import (
    is_valid_assemble_response,
    is_valid_build_task,
    parse_build_task,
)
from webhook.utils.task_manager import TaskManager


class TaskService:
    @staticmethod
    def handle_webhook_request(
        data: GitLabPushEventModel, db: sqlite3.Connection
    ) -> tuple[Optional[list["Task"]], str, int]:
        """处理webhook请求并创建任务

        支持多任务构建，会遍历commits中的提交，过滤有效的提交任务，返回提交任务列表

        Args:
            data: webhook请求数据
            db:

        Returns:
            tuple: (tasks, message, status_code)
            - tasks: 创建的任务对象列表，如果没有创建则为None
            - message: 处理结果消息
            - status_code: HTTP状态码
        """
        # 验证提交信息
        commits: list[Commit] = data.commits or []
        if not commits:
            return None, "No file changes in commit", 403

        logging.info(
            f"收到{len(commits)}个提交信息: {json.dumps([c.model_dump() for c in commits], ensure_ascii=False, indent=2)}"
        )
        valid_commits: list[Commit] = [commit for commit in commits if is_valid_build_task(commit)]
        logging.info(
            f"有效提交（{len(valid_commits)}）：\n{json.dumps([c.model_dump() for c in valid_commits], ensure_ascii=False, indent=2)}"
        )
        if not valid_commits:
            is_resp, resp_hash = is_valid_assemble_response(commits[0])
            if is_resp:
                # 更新任务响应哈希
                logging.info(f"更新任务响应哈希: {resp_hash}")
                prod_name, task_name = parse_build_task(commits[0])
                task_id = f"{prod_name},{task_name}"
                TaskService.update_response_hash(task_id, resp_hash, db=db)
                WebhookRequestService.delete_webhook_request(task_id, db=db)
                return None, "This's a assemble response, not a build task", 201
            return None, "No valid build task", 404

        def build_task(commit: Commit) -> Optional["Task"]:
            prod, task = parse_build_task(commit)
            return TaskService.create_task(prod_name=prod, task_name=task, commit_info=commit, db=db)

        tasks = [build_task(vc) for vc in valid_commits]
        tasks = [task for task in tasks if task is not None]

        return tasks, "Task created successfully", 200

    @staticmethod
    def create_task(
        prod_name,
        task_name,
        commit_info: Commit = None,
        priority=0,
        retries=0,
        db: sqlite3.Connection = None,
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
            db:
        """
        task_id = f"{prod_name},{task_name}"
        task = Task.get_by_id(task_id, db)
        if task:
            if task.status in (TaskStatus.FAILED, TaskStatus.PENDING, TaskStatus.STOPPED, TaskStatus.TIMEOUT):
                if task.status in (TaskStatus.FAILED, TaskStatus.STOPPED, TaskStatus.TIMEOUT):
                    task.update_status(TaskStatus.PENDING, db=db)
                logging.warning(f"任务id：{task_id} 存在（失败/待执行），加入队列")
                return task
            else:
                logging.warning(f"任务id：{task_id} 已存在，跳过执行")
                return None

        task = Task(
            id=task_id,
            prod_name=prod_name,
            task_name=task_name,
            priority=priority,
            retries=retries,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
        )

        if commit_info:
            task.author = commit_info.author.name
            task.commit_title = commit_info.title
            task.commit_message = commit_info.message
            task.commit_url = commit_info.url
            task.commit_hash = commit_info.id
            timestamp = None
            try:
                timestamp = commit_info.timestamp
                if timestamp:
                    task.created_at = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")
            except (ValueError, TypeError):
                logging.error(f"解析时间戳失败: {timestamp}")
                pass

        task.save(db)
        return task

    @staticmethod
    def get_task(task_id: str, db: sqlite3.Connection = None) -> Optional["Task"]:
        """通过任务id获取任务详情

        Args:
            task_id: 任务ID
            db:

        Returns:
            Optional[Task]: 任务对象，如果未找到则返回None
        """
        return Task.get_by_id(task_id, db)

    @staticmethod
    def get_running_task(db: sqlite3.Connection = None) -> Optional["Task"]:
        """获取正在执行的任务

        Returns:
            Optional[Task]: 正在执行的任务对象，如果未找到则返回None
        """
        return Task.get_running_task(db)

    @staticmethod
    def get_pending_tasks(db: sqlite3.Connection = None) -> list["Task"]:
        """获取待执行任务

        Returns:
            list[Task]: 待执行任务列表
        """
        return Task.get_pending_tasks(db)

    @staticmethod
    def get_recent_tasks(limit: int = 5, db: sqlite3.Connection = None) -> list["Task"]:
        """获取最近任务

        Args:
            limit: 返回的任务数量限制，默认为5
            db: 数据库连接

        Returns:
            list[Task]: 最近任务列表
        """
        return Task.get_recent_tasks(limit, db=db)

    @staticmethod
    def update_response_hash(task_id: str, response_hash: str, db: sqlite3.Connection = None) -> Optional["Task"]:
        """更新任务响应哈希"""
        task = Task.get_by_id(task_id, db)
        if task:
            task.update_response_hash(response_hash, db)
            return task
        return None

    @staticmethod
    def update_task_status(
        task_id: str,
        status: TaskStatus,
        error: Optional[str] = None,
        db: sqlite3.Connection = None,
    ) -> Optional["Task"]:
        """更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            error: 错误信息
            db:

        Returns:
            Optional[Task]: 更新后的任务对象，如果任务不存在则返回None
        """
        task = Task.get_by_id(task_id, db)
        if task:
            task.update_status(status, error, db=db)
            return task
        return None

    @staticmethod
    def get_queue_status(
        limit: int = 5, build_mode: str | None = None, db: sqlite3.Connection = None
    ) -> dict[str, Any]:
        """
        获取队列状态

        Args:
            limit: 返回的任务数量限制
            build_mode: 构建模式，可选值为 dev/test/release，为 None 时不进行筛选
            db:
        """
        running_task = Task.get_running_task(db)
        pending_tasks = Task.get_pending_tasks(db)
        recent_tasks = Task.get_recent_tasks(limit=limit, build_mode=build_mode, db=db)

        return {
            "running_task": running_task.to_dict() if running_task else None,
            "pending_tasks": [task.to_dict() for task in pending_tasks],
            "queue_size": len(pending_tasks),
            "recent_tasks": [task.to_dict() for task in recent_tasks],
        }

    @staticmethod
    def stop_task(task_id, db: sqlite3.Connection = None):
        """停止运行中的任务

        Args:
            task_id: 任务ID
            db:

        Returns:
            tuple: (task, message, status_code)
            - task: 更新后的任务对象，如果任务不存在或不在运行中则为None
            - message: 处理结果消息
            - status_code: HTTP状态码
        """
        task = Task.get_by_id(task_id, db)
        if not task:
            return None, "Task not found", 404

        if task.status != TaskStatus.RUNNING:
            return None, "Task is not running", 400

        # 使用 TaskManager 终止进程
        process_killed = TaskManager.kill_process(task_id)

        # 更新任务状态为 stopped，服务器主动停止
        task.update_status(TaskStatus.STOPPED, format_error(10003), db=db)

        message = "Task stopped successfully"
        if not process_killed:
            message += " (process may have already finished)"

        return task, message, 200

    @staticmethod
    def get_tasks_statistics(db: sqlite3.Connection = None):
        """获取所有任务的统计情况"""
        return Task.get_tasks_statistics(db)

    @staticmethod
    def get_packer_usage_statistics(db: sqlite3.Connection = None):
        """获取打包机使用人员统计情况"""
        return Task.get_packer_usage_statistics(db)

    @staticmethod
    def get_other_normalized_tasks(current_task_id: str, db: sqlite3.Connection = None):
        """获取其他已完成归一化的任务信息"""
        return Task.get_other_normalized_tasks(current_task_id, db)
